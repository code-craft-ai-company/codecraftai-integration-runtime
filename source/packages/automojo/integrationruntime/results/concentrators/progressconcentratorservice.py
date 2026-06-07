"""
    .. module:: automojo.testbase.results.concentrators.progressconcentratorservice
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Module for progressconcentratorservice.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""



__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []

from typing import Any, Optional, Tuple, Union

import json
import requests
import os
import threading
import time
import traceback

from datetime import datetime
from socketserver import ThreadingMixIn
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Type alias for server address - compatible with all Python versions
ServerAddress = Tuple[str, int]

from automojo.xmodules.xlogging.enhancedloggers import getEnhancedLogger

from automojo.testbase.results.model.forwardinginfo import ForwardingInfo
from automojo.testbase.results.model.progressinfo import ProgressInfo
from automojo.testbase.results.recorders.resultrecorder import ResultRecorder


class SummaryJsonEncoder(json.JSONEncoder):
    """
        A custom JSON encoder that extends :class:`json.JSONEncoder` to handle datetime
        serialization for summary forwarding operations.

        This encoder converts datetime objects to ISO 8601 formatted strings, enabling
        proper JSON serialization of summary data that contains timestamp fields.

        The encoder is used internally by the :class:`ProgressConcentratorServer` when
        forwarding aggregated summaries to external monitoring services.
    """

    def default(self, obj) -> Any:
        """
            Converts non-serializable objects to JSON-compatible representations.

            This method overrides the base :class:`json.JSONEncoder.default` method to
            provide custom serialization for datetime objects. All other object types
            are delegated to the parent class implementation.

            :param obj: The object to serialize to a JSON-compatible format.

            :returns: An ISO 8601 formatted string if obj is a datetime, otherwise
                      delegates to the parent class default method.

            :raises: TypeError if the object is not serializable and the parent
                     class cannot handle it.
        """

        cval = None

        if isinstance(obj, datetime):
            cval = obj.isoformat()
        else:
            cval = json.JSONEncoder.default(self, obj)

        return cval


class ProgressCallbackHandler(SimpleHTTPRequestHandler):
    """
        An HTTP request handler that processes incoming POST requests containing progress
        information from remote test workers.

        The :class:`ProgressCallbackHandler` inherits from :class:`SimpleHTTPRequestHandler`
        and implements the do_POST method to receive JSON-encoded progress updates. Each
        progress update is deserialized into a :class:`ProgressInfo` object and forwarded
        to the parent :class:`ProgressConcentratorServer` for aggregation.

        This handler is designed to be used with the :class:`ProgressConcentratorServer`
        which provides concurrent request handling through the :class:`ThreadingMixIn`.
        Multiple workers can submit progress updates simultaneously, with each request
        being processed in a separate thread.

        Response Codes:
            - 200 OK: Progress update was successfully processed or no content was provided
            - 500 Internal Server Error: An exception occurred during processing

        Expected JSON Payload Format::

            {
                "id": "task-uuid-123",
                "category": "test-execution",
                "moniker": "test_module.test_function",
                "ptype": "Sequential",
                "range_min": "0",
                "range_max": "10",
                "position": "5",
                "status": "Running",
                "when": "2025-02-20T10:30:00.000000",
                "data": {...}
            }
    """

    def do_POST(self):
        """
            Handles incoming HTTP POST requests containing progress update data.

            This method reads the request body when a content-length header is present,
            parses the JSON payload, creates a :class:`ProgressInfo` object from the
            data, and delegates the progress update to the server's update_task_progress
            method.

            The method implements robust error handling to ensure the server remains
            stable even when receiving malformed requests. All exceptions during
            processing are caught and returned as 500 error responses with detailed
            traceback information.

            Response Behavior:
                - If content-length is missing: Returns 200 OK without processing
                - If JSON parsing succeeds: Returns 200 OK after updating progress
                - If any exception occurs: Returns 500 with error message and traceback

            :returns: None. Response is sent directly to the client via inherited methods.
        """

        # ERROR HANDLING PATTERN:
        # We use a sentinel variable (errmsg) to track error state throughout processing.
        # This allows us to attempt all processing steps and collect error information
        # before deciding on the response code. If errmsg remains None, processing succeeded.
        errmsg = None

        # Only process requests that have a content-length header.
        # Requests without content-length are treated as no-ops and return 200 OK.
        # This handles edge cases like health checks or empty POST requests gracefully.
        if 'content-length' in self.headers:

            content_length = self.headers["content-length"]
            length = int(content_length) if content_length else 0

            if length:
                # ERROR HANDLING: Wrap all processing in try/except to ensure server stability.
                # Any exception during JSON parsing, ProgressInfo creation, or progress update
                # is caught and converted to a 500 error response with full traceback.
                # This prevents malformed requests from crashing the server thread.
                try:
                    # Step 1: Read raw bytes from request body
                    content = self.rfile.read(length)
                    
                    # Step 2: Parse JSON - may raise json.JSONDecodeError for malformed JSON
                    data = json.loads(content)

                    # Step 3: Deserialize to ProgressInfo - may raise if required fields missing
                    progress = ProgressInfo.from_dict(data)
                    
                    # Step 4: Delegate to server for thread-safe aggregation
                    # The server's update_task_progress method handles concurrent access
                    server: ProgressConcentratorServer = self.server
                    server.update_task_progress(progress)

                except Exception as perr:
                    # ERROR HANDLING: Capture full exception context for debugging.
                    # Include a human-readable prefix and the complete traceback
                    # to help diagnose issues with malformed progress payloads.
                    errmsg_msg_lines = [
                        "Error processing progress postback.",
                        "EXCEPTION:",
                        traceback.format_exc()
                    ]
                    errmsg = os.linesep.join(errmsg_msg_lines)

        # RESPONSE HANDLING: Send appropriate HTTP response based on processing outcome.
        # Success (errmsg is None) returns 200 OK; failure returns 500 with error details.
        if not errmsg:
            self.send_response(200, message=None)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
        else:
            # Include error message in 500 response for client-side debugging.
            # Only use the first line of the error message to avoid HTTP header injection
            # Make sure it only contains latin-1 characters or encode it safely
            safe_msg = errmsg_msg_lines[0].encode('latin-1', 'replace').decode('latin-1')
            self.send_response(500, message=safe_msg)
            self.send_header("Content-Type", "text/plain")
            
            # Send the full error message in the response body
            body_bytes = errmsg.encode('utf-8')
            self.send_header("Content-Length", str(len(body_bytes)))
            self.end_headers()
            self.wfile.write(body_bytes)

        return


class ProgressConcentratorServer(ThreadingMixIn, HTTPServer):
    """
        A threaded HTTP server that receives progress callbacks from remote test workers
        and aggregates them into a central :class:`ResultRecorder`.

        The :class:`ProgressConcentratorServer` combines :class:`ThreadingMixIn` with
        :class:`HTTPServer` to provide concurrent request handling capabilities. This
        allows multiple remote workers to submit progress updates simultaneously without
        blocking each other.

        The server provides two main functions:

        1. **Progress Collection**: Accepts HTTP POST requests containing JSON-encoded
           progress updates from remote workers and routes them to the ResultRecorder
           for aggregation.

        2. **Summary Forwarding**: Optionally runs a background thread that periodically
           retrieves the aggregated summary from the ResultRecorder and forwards it to
           external monitoring services via HTTP POST.

        Thread Architecture:
            - Server Thread ('prog-concentrator'): Daemon thread running serve_forever()
              to accept incoming connections
            - Forwarding Thread ('prog-forwarder'): Optional daemon thread that periodically
              forwards summaries to external services
            - Request Threads: Spawned by ThreadingMixIn for each incoming request

        The server uses gate events for thread synchronization to ensure the start()
        method does not return until all threads are ready to process requests.

        Example Usage::

            from automojo.testbase.results.model.forwardinginfo import ForwardingInfo
            from automojo.testbase.results.concentrators.progressconcentratorservice import (
                ProgressConcentratorServer
            )

            # Configure forwarding (optional)
            forwarding_info = ForwardingInfo(
                forwarding_interval=5.0,
                forwarding_url="https://monitoring.example.com/api/progress",
                forwarding_headers={"Authorization": "Bearer token123"}
            )

            # Create and start concentrator
            server = ProgressConcentratorServer(
                recorder=result_recorder,
                server_address=("0.0.0.0", 8080),
                forwarding_info=forwarding_info
            )
            server.start()
    """

    # Increase the listen backlog to handle high concurrency and prevent 'Connection reset by peer'
    request_queue_size = 128


    def __init__(self, recorder: ResultRecorder, server_address: ServerAddress, forwarding_info: Optional[ForwardingInfo] = None,
                bind_and_activate: bool = True) -> None:
        """
            Initializes a new ProgressConcentratorServer instance.

            :param recorder: The :class:`ResultRecorder` instance to aggregate progress into.
                             All progress updates received by this server will be forwarded
                             to this recorder's post_task_progress method.
            :param server_address: A tuple of (host, port) specifying the address to bind to.
                                   Use "0.0.0.0" to listen on all interfaces or "127.0.0.1"
                                   for loopback only.
            :param forwarding_info: Optional :class:`ForwardingInfo` configuration for periodic
                                    summary forwarding. If provided, a forwarding thread will
                                    be started when start() is called.
            :param bind_and_activate: If True (default), the server will bind to the address
                                      and activate immediately upon construction.

            :returns: None
        """

        self._recorder = recorder
        self._forwarding_info = forwarding_info

        super().__init__(server_address, ProgressCallbackHandler, bind_and_activate)

        self._forward_thread = None
        self._forwarding_running = False

        self._server_thread = None
        self._server_running = False

        self._logger = getEnhancedLogger()

        return

    def start(self):
        """
            Starts the server and optional forwarding threads.

            This method initiates the server's request handling thread and, if forwarding
            configuration was provided, also starts the summary forwarding thread. The
            method uses gate events to synchronize thread startup and does not return
            until all threads signal readiness.

            Thread Startup Order:
                1. If forwarding_info is configured, start the forwarding thread first
                   and wait for it to signal readiness via its gate event
                2. Start the server thread and wait for it to signal readiness
                3. Return to caller once all threads are running

            Both threads are created as daemon threads, meaning they will be automatically
            terminated when the main process exits.

            :returns: None
        """
        
        # THREAD SYNCHRONIZATION - GATE PATTERN:
        # We use threading.Event objects as "gates" to synchronize thread startup.
        # The pattern ensures the start() method does not return until child threads
        # are fully initialized and ready to process work. This prevents race conditions
        # where callers might try to use the server before it's ready.
        #
        # Gate Pattern Flow:
        # 1. Create Event and clear it (gate is "closed")
        # 2. Pass gate to child thread
        # 3. Child thread performs initialization
        # 4. Child thread calls gate.set() to "open" the gate
        # 5. Parent thread's gate.wait() returns, confirming child is ready

        # Start forwarding thread first if forwarding is configured.
        # This ensures summary forwarding is operational before we start accepting
        # progress updates from workers.
        if self._forwarding_info is not None:
            # Create gate event for forwarding thread synchronization
            fwd_gate = threading.Event()
            fwd_gate.clear()  # Ensure gate starts in "closed" state
            
            # Create forwarding thread as daemon so it auto-terminates on process exit.
            # Thread name 'prog-forwarder' aids in debugging and thread identification.
            self._forward_thread = threading.Thread(target=self._forwarding_thread_entry, name='prog-forwarder', args=(fwd_gate,), daemon=True)
            self._forward_thread.start()

            # SYNCHRONIZATION POINT: Block until forwarding thread signals ready.
            # This ensures the forwarding loop is running before we proceed.
            fwd_gate.wait()

        # Create gate event for server thread synchronization
        svr_gate = threading.Event()
        svr_gate.clear()  # Ensure gate starts in "closed" state

        # Set running flag before starting thread to indicate intent to run
        self._server_running = True
        
        # Create server thread as daemon so it auto-terminates on process exit.
        # Thread name 'prog-concentrator' aids in debugging and thread identification.
        self._server_thread = threading.Thread(target=self._service_thread_entry, name='prog-concentrator', args=(svr_gate,), daemon=True)
        self._server_thread.start()

        # SYNCHRONIZATION POINT: Block until server thread signals ready.
        # This ensures serve_forever() is running and accepting connections
        # before we return to the caller.
        svr_gate.wait()

        return
    
    def _forwarding_thread_entry(self, start_gate: threading.Event):
        """
            Entry point for the summary forwarding thread.

            This method runs the forwarding loop that periodically retrieves the summary
            from the recorder and POSTs it to the configured forwarding URL. The loop
            continues while _forwarding_running is True.

            The method handles exceptions gracefully to ensure the forwarding thread
            continues operating even when network errors or HTTP failures occur. All
            exceptions are logged but do not terminate the thread.

            :param start_gate: A :class:`threading.Event` used to signal to the caller
                               that the forwarding thread has started and is ready.

            :returns: None
        """
        
        # FORWARDING LOOP INITIALIZATION:
        # Set the running flag to True to enable the forwarding loop.
        # This flag can be set to False externally to gracefully stop forwarding.
        self._forwarding_running = True

        # HEADER CONFIGURATION:
        # Build the HTTP headers for forwarding requests. Start with the required
        # Content-Type header for JSON payloads, then merge any custom headers
        # provided in the forwarding configuration (e.g., Authorization tokens).
        headers = {
            "Content-Type": "application/json"
        }

        # Extract forwarding configuration for use in the loop.
        # These values are read once at startup for efficiency.
        forwarding_interval = self._forwarding_info.forwarding_interval
        forwarding_url = self._forwarding_info.forwarding_url
        forwarding_headers = self._forwarding_info.forwarding_headers

        # Merge custom headers if provided. This allows callers to add
        # authentication headers, correlation IDs, or other custom headers.
        if forwarding_headers is not None:
            headers.update(forwarding_headers)

        # GATE PATTERN - SIGNAL READY:
        # Signal to the parent thread (start() method) that initialization is complete
        # and the forwarding loop is about to begin. This allows start() to return
        # knowing that forwarding is operational.
        start_gate.set()

        # FORWARDING LOOP:
        # Continuously forward summaries to the external service at the configured interval.
        # The loop runs until _forwarding_running is set to False (e.g., during shutdown).
        while self._forwarding_running:

            # ERROR HANDLING - RESILIENT LOOP:
            # Wrap the entire loop iteration in try/except to ensure the forwarding
            # thread never terminates due to transient errors. Network failures,
            # HTTP errors, or serialization issues are logged but don't stop forwarding.
            # This is critical for maintaining monitoring connectivity during test runs.
            try:
                # THREAD-SAFE SUMMARY ACCESS:
                # Retrieve a deep copy of the current summary from the recorder.
                # The recorder's summary property uses locking to ensure we get
                # a consistent snapshot even while other threads update progress.
                summary = self._recorder.summary

                # SERIALIZATION AND FORWARDING:
                # Serialize the summary to JSON using our custom encoder that handles
                # datetime objects, then POST to the configured monitoring endpoint.
                summary_json = json.dumps(summary, cls=SummaryJsonEncoder)
                requests.post(forwarding_url, data=summary_json, headers=headers)

            except (requests.exceptions.ConnectionError, requests.exceptions.RetryError) as err:
                # ERROR HANDLING - LOG AND CONTINUE:
                # Log connection errors as warnings without full tracebacks to avoid spamming
                # the console, particularly during integration tests that simulate failures.
                self._logger.warning(f"Connection error while forwarding progress: {err}")
                
            except Exception:
                # ERROR HANDLING - LOG AND CONTINUE:
                # Log the full exception traceback for debugging other types of errors, but don't re-raise.
                # The loop continues to the next iteration, ensuring forwarding
                # resumes after transient failures (network issues, service outages, etc.).
                errmsg = traceback.format_exc()
                self._logger.error(errmsg)

            finally:
                # INTERVAL SLEEP:
                # Wait for the configured interval before the next forward.
                # This controls the frequency of summary updates to external services.
                if self._forwarding_running:
                    time.sleep(forwarding_interval)

        return

    def _service_thread_entry(self, start_gate: threading.Event):
        """
            Entry point for the HTTP server thread.

            This method sets the server_running flag, signals readiness via the gate
            event, and then enters the serve_forever loop to accept and handle incoming
            HTTP connections.

            :param start_gate: A :class:`threading.Event` used to signal to the caller
                               that the server thread has started and is ready to accept
                               connections.

            :returns: None
        """
        
        # SERVER THREAD INITIALIZATION:
        # Set the running flag to indicate the server is operational.
        # This flag can be checked by other components to verify server status.
        self._server_running = True

        # GATE PATTERN - SIGNAL READY:
        # Signal to the parent thread (start() method) that the server thread
        # has initialized and is about to enter serve_forever(). This allows
        # start() to return knowing the server is ready to accept connections.
        # Note: We signal BEFORE serve_forever() because serve_forever() blocks.
        start_gate.set()

        # HTTP SERVER LOOP:
        # Enter the blocking serve_forever() loop provided by HTTPServer.
        # This method handles incoming connections and spawns handler threads
        # (via ThreadingMixIn) for each request. The loop runs until
        # shutdown() is called on the server.
        self.serve_forever()

        return

    def update_task_progress(self, progress: ProgressInfo):
        """
            Updates the task progress in the associated ResultRecorder.

            This method is called by :class:`ProgressCallbackHandler` instances when
            they receive valid progress updates from remote workers. The method
            delegates to the recorder's post_task_progress method, which handles
            thread-safe updates to the running tasks dictionary.

            This method is thread-safe and can be called concurrently from multiple
            request handler threads.

            :param progress: A :class:`ProgressInfo` object containing the progress
                             update data received from a remote worker.

            :returns: None
        """
        # THREAD-SAFE DELEGATION:
        # Delegate to the recorder's post_task_progress method, which uses
        # internal locking to ensure thread-safe updates to the running_tasks
        # dictionary. Multiple request handler threads can call this method
        # concurrently without data corruption.
        # 
        # The progress is wrapped in a list because post_task_progress accepts
        # a list of ProgressInfo objects for batch processing efficiency.
        self._recorder.post_task_progress([progress])
        return


