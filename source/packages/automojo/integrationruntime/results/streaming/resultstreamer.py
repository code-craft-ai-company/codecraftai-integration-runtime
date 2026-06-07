"""
    .. module:: automojo.testbase.results.streaming.resultstreamer
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Module for result streaming to external services.

    This module provides classes for streaming test results to external services
    in real-time. It supports both REST endpoint streaming and WebSocket-based
    streaming.

    The streaming functionality allows test results to be sent to external
    monitoring services as they are generated, enabling real-time dashboards
    and alerting systems.

    .. moduleauthor:: AutomationX
"""



__author__ = "AutomationX"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from typing import Optional, List, Any
from abc import ABC, abstractmethod

import json
import queue
import threading
import time
import traceback

from datetime import datetime

from automojo.xmodules.xlogging.enhancedloggers import getEnhancedLogger

from automojo.testbase.results.model.streaminginfo import (
    StreamingInfo,
    StreamingProtocol,
    StreamingCallback
)


class StreamingJsonEncoder(json.JSONEncoder):
    """
        A custom JSON encoder for streaming result data.
        
        This encoder handles datetime serialization and other non-standard
        types that may appear in result data.
    """
    
    def default(self, obj) -> Any:
        """
            Converts non-serializable objects to JSON-compatible representations.
            
            :param obj: The object to serialize.
            :returns: A JSON-compatible representation of the object.
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


class ResultStreamer(ABC):
    """
        Abstract base class for result streaming implementations.
        
        This class defines the interface for streaming test results to external
        services. Concrete implementations handle specific protocols (REST, WebSocket).
        
        The streamer operates in a background thread to avoid blocking test execution.
        Results are queued and sent asynchronously.
        
        Thread Safety:
            The streamer is designed for concurrent access from multiple threads.
            Results can be queued from any thread, and the streaming thread handles
            delivery to the external service.
    """
    
    def __init__(self, streaming_info: StreamingInfo, 
                 callback: Optional[StreamingCallback] = None):
        """
            Initializes the result streamer.
            
            :param streaming_info: Configuration for the streaming connection.
            :param callback: Optional callback for custom result handling.
        """
        self._streaming_info = streaming_info
        self._callback = callback
        self._logger = getEnhancedLogger()
        
        self._result_queue: queue.Queue = queue.Queue()
        self._streaming_thread: Optional[threading.Thread] = None
        self._running = False
        self._connected = False
        
        self._lock = threading.Lock()
        self._stats = {
            "previews_sent": 0,
            "results_sent": 0,
            "errors": 0,
            "reconnects": 0
        }
    
    @property
    def is_running(self) -> bool:
        """Returns True if the streaming thread is running."""
        return self._running
    
    @property
    def is_connected(self) -> bool:
        """Returns True if connected to the external service."""
        return self._connected
    
    @property
    def stats(self) -> dict:
        """Returns a copy of streaming statistics."""
        with self._lock:
            return dict(self._stats)
    
    def start(self):
        """
            Starts the streaming thread.
            
            This method initializes the connection to the external service
            and starts the background thread that processes the result queue.
        """
        if self._running:
            return
        
        self._running = True
        
        # Create and start the streaming thread
        self._streaming_thread = threading.Thread(
            target=self._streaming_thread_entry,
            name="result-streamer",
            daemon=True
        )
        self._streaming_thread.start()
        
        # Wait for connection to be established
        start_time = time.time()
        while not self._connected and time.time() - start_time < 5.0:
            time.sleep(0.05)
    
    def stop(self):
        """
            Stops the streaming thread.
            
            This method signals the streaming thread to stop and waits for
            it to complete. Any remaining queued results are discarded.
        """
        self._running = False
        
        # Put a sentinel value to wake up the thread
        self._result_queue.put(None)
        
        if self._streaming_thread is not None:
            self._streaming_thread.join(timeout=5.0)
            self._streaming_thread = None
        
        self._disconnect()
    
    def stream_preview(self, result_dict: dict):
        """
            Queues a preview result for streaming.
            
            :param result_dict: The result dictionary to stream.
        """
        if not self._streaming_info.stream_previews:
            return
        
        self._result_queue.put(("preview", result_dict))
    
    def stream_result(self, result_dict: dict):
        """
            Queues a final result for streaming.
            
            :param result_dict: The result dictionary to stream.
        """
        if not self._streaming_info.stream_results:
            return
        
        self._result_queue.put(("result", result_dict))
    
    def _streaming_thread_entry(self):
        """
            Entry point for the streaming thread.
            
            This method runs the main streaming loop, processing queued
            results and sending them to the external service.
        """
        # Establish initial connection
        self._connect()
        
        batch: List[tuple] = []
        last_batch_time = time.time()
        
        while self._running:
            try:
                # Get next item from queue with timeout
                timeout = self._streaming_info.batch_timeout
                try:
                    item = self._result_queue.get(timeout=timeout)
                except queue.Empty:
                    item = None
                
                # Check for stop signal
                if item is None:
                    # Send any remaining batch items
                    if batch:
                        self._send_batch(batch)
                        batch = []
                    
                    if not self._running:
                        break
                    continue
                
                # Add to batch
                batch.append(item)
                
                # Check if batch should be sent
                batch_size = self._streaming_info.batch_size
                batch_timeout = self._streaming_info.batch_timeout
                time_since_batch = time.time() - last_batch_time
                
                if len(batch) >= batch_size or time_since_batch >= batch_timeout:
                    self._send_batch(batch)
                    batch = []
                    last_batch_time = time.time()
                    
            except Exception:
                errmsg = traceback.format_exc()
                self._logger.error(f"Error in streaming thread: {errmsg}")
                
                with self._lock:
                    self._stats["errors"] += 1
                
                # Attempt reconnection if configured
                if self._streaming_info.reconnect_on_failure:
                    self._reconnect()
        
        # Final disconnect
        self._disconnect()
    
    def _send_batch(self, batch: List[tuple]):
        """
            Sends a batch of results to the external service.
            
            :param batch: List of (type, result_dict) tuples to send.
        """
        for item_type, result_dict in batch:
            is_preview = item_type == "preview"
            
            try:
                # Call custom callback if provided
                if self._callback is not None:
                    success = self._callback.on_result(result_dict, is_preview)
                    if not success:
                        continue
                
                # Send via protocol-specific implementation
                self._send_result(result_dict, is_preview)
                
                # Update stats
                with self._lock:
                    if is_preview:
                        self._stats["previews_sent"] += 1
                    else:
                        self._stats["results_sent"] += 1
                        
            except Exception as err:
                with self._lock:
                    self._stats["errors"] += 1
                
                if self._callback is not None and self._callback.on_error is not None:
                    self._callback.on_error(err)
                
                self._logger.error(f"Error sending result: {traceback.format_exc()}")
    
    def _reconnect(self):
        """
            Attempts to reconnect to the external service.
        """
        self._disconnect()
        
        with self._lock:
            self._stats["reconnects"] += 1
        
        time.sleep(self._streaming_info.reconnect_interval)
        self._connect()
    
    @abstractmethod
    def _connect(self):
        """
            Establishes connection to the external service.
            
            This method must be implemented by concrete subclasses.
        """
        pass
    
    @abstractmethod
    def _disconnect(self):
        """
            Closes connection to the external service.
            
            This method must be implemented by concrete subclasses.
        """
        pass
    
    @abstractmethod
    def _send_result(self, result_dict: dict, is_preview: bool):
        """
            Sends a single result to the external service.
            
            :param result_dict: The result dictionary to send.
            :param is_preview: True if this is a preview, False for final result.
        """
        pass



class RestResultStreamer(ResultStreamer):
    """
        Result streamer that sends results to REST endpoints via HTTP POST.
        
        This streamer sends each result as a JSON payload to the configured
        REST endpoint. It supports custom headers for authentication and
        other purposes.
        
        Example Usage::
        
            streaming_info = StreamingInfo(
                protocol=StreamingProtocol.REST,
                streaming_url="https://monitoring.example.com/api/results",
                streaming_headers={"Authorization": "Bearer token123"},
                stream_previews=True,
                stream_results=True
            )
            
            streamer = RestResultStreamer(streaming_info)
            streamer.start()
            
            # Stream results
            streamer.stream_preview(preview_dict)
            streamer.stream_result(result_dict)
            
            # Stop when done
            streamer.stop()
    """
    
    def __init__(self, streaming_info: StreamingInfo,
                 callback: Optional[StreamingCallback] = None):
        """
            Initializes the REST result streamer.
            
            :param streaming_info: Configuration for the REST endpoint.
            :param callback: Optional callback for custom result handling.
        """
        super().__init__(streaming_info, callback)
        self._session = None
    
    def _connect(self):
        """
            Establishes connection to the REST endpoint.
            
            For REST streaming, this creates a requests session for
            connection pooling and sets up default headers.
        """
        try:
            import requests
            
            self._session = requests.Session()
            
            # Set default headers
            self._session.headers.update({
                "Content-Type": "application/json"
            })
            
            # Add custom headers if configured
            if self._streaming_info.streaming_headers:
                self._session.headers.update(self._streaming_info.streaming_headers)
            
            self._connected = True
            
            if self._callback is not None and self._callback.on_connect is not None:
                self._callback.on_connect()
                
        except Exception:
            self._connected = False
            self._logger.error(f"Failed to initialize REST session: {traceback.format_exc()}")
    
    def _disconnect(self):
        """
            Closes the REST session.
        """
        if self._session is not None:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = None
        
        self._connected = False
        
        if self._callback is not None and self._callback.on_disconnect is not None:
            self._callback.on_disconnect()
    
    def _send_result(self, result_dict: dict, is_preview: bool):
        """
            Sends a result to the REST endpoint via HTTP POST.
            
            :param result_dict: The result dictionary to send.
            :param is_preview: True if this is a preview, False for final result.
        """
        if self._session is None:
            raise RuntimeError("REST session not initialized")
        
        # Prepare payload
        payload = {
            "type": "preview" if is_preview else "result",
            "data": result_dict,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send POST request
        json_data = json.dumps(payload, cls=StreamingJsonEncoder)
        response = self._session.post(
            self._streaming_info.streaming_url,
            data=json_data
        )
        
        # Check response
        if response.status_code >= 400:
            raise RuntimeError(
                f"REST endpoint returned error: {response.status_code} - {response.text}"
            )


class WebSocketResultStreamer(ResultStreamer):
    """
        Result streamer that sends results over a WebSocket connection.
        
        This streamer maintains a persistent WebSocket connection to the
        external service and sends results as JSON messages. It supports
        automatic reconnection on connection failure.
        
        Example Usage::
        
            streaming_info = StreamingInfo(
                protocol=StreamingProtocol.WEBSOCKET,
                streaming_url="wss://monitoring.example.com/ws/results",
                streaming_headers={"Authorization": "Bearer token123"},
                stream_previews=True,
                stream_results=True,
                reconnect_on_failure=True,
                reconnect_interval=5.0
            )
            
            streamer = WebSocketResultStreamer(streaming_info)
            streamer.start()
            
            # Stream results
            streamer.stream_preview(preview_dict)
            streamer.stream_result(result_dict)
            
            # Stop when done
            streamer.stop()
    """
    
    def __init__(self, streaming_info: StreamingInfo,
                 callback: Optional[StreamingCallback] = None):
        """
            Initializes the WebSocket result streamer.
            
            :param streaming_info: Configuration for the WebSocket connection.
            :param callback: Optional callback for custom result handling.
        """
        super().__init__(streaming_info, callback)
        self._websocket = None
    
    def _connect(self):
        """
            Establishes WebSocket connection to the external service.
        """
        try:
            # Import websocket-client library
            try:
                import websocket
            except ImportError:
                self._logger.error(
                    "websocket-client library not installed. "
                    "Install with: pip install websocket-client"
                )
                self._connected = False
                return
            
            # Prepare headers
            headers = {}
            if self._streaming_info.streaming_headers:
                headers = self._streaming_info.streaming_headers
            
            # Create WebSocket connection
            self._websocket = websocket.create_connection(
                self._streaming_info.streaming_url,
                header=headers
            )
            
            self._connected = True
            
            if self._callback is not None and self._callback.on_connect is not None:
                self._callback.on_connect()
                
        except Exception:
            self._connected = False
            self._logger.error(f"Failed to connect WebSocket: {traceback.format_exc()}")
    
    def _disconnect(self):
        """
            Closes the WebSocket connection.
        """
        if self._websocket is not None:
            try:
                self._websocket.close()
            except Exception:
                pass
            self._websocket = None
        
        self._connected = False
        
        if self._callback is not None and self._callback.on_disconnect is not None:
            self._callback.on_disconnect()
    
    def _send_result(self, result_dict: dict, is_preview: bool):
        """
            Sends a result over the WebSocket connection.
            
            :param result_dict: The result dictionary to send.
            :param is_preview: True if this is a preview, False for final result.
        """
        if self._websocket is None:
            raise RuntimeError("WebSocket not connected")
        
        # Prepare message
        message = {
            "type": "preview" if is_preview else "result",
            "data": result_dict,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send message
        json_data = json.dumps(message, cls=StreamingJsonEncoder)
        self._websocket.send(json_data)


def create_result_streamer(streaming_info: StreamingInfo,
                           callback: Optional[StreamingCallback] = None) -> ResultStreamer:
    """
        Factory function to create the appropriate result streamer.
        
        This function creates a result streamer based on the protocol
        specified in the streaming configuration.
        
        :param streaming_info: Configuration for the streaming connection.
        :param callback: Optional callback for custom result handling.
        :returns: A ResultStreamer instance for the specified protocol.
        :raises: ValueError if the protocol is not supported.
    """
    if streaming_info.protocol == StreamingProtocol.REST:
        return RestResultStreamer(streaming_info, callback)
    elif streaming_info.protocol == StreamingProtocol.WEBSOCKET:
        return WebSocketResultStreamer(streaming_info, callback)
    else:
        raise ValueError(f"Unsupported streaming protocol: {streaming_info.protocol}")
