"""
    .. module:: automojo_tests.testbase.results.streaming.test_resultstreamer
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Unit tests for ResultStreamer classes.

    This module contains unit tests for the ResultStreamer base class and
    its concrete implementations (RestResultStreamer, WebSocketResultStreamer).

    .. moduleauthor:: AutomationX
"""

import unittest
import threading
import time
import json
import tempfile
import os
import shutil

from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

from automojo.testbase.results.model.streaminginfo import (
    StreamingInfo,
    StreamingProtocol,
    StreamingCallback
)
from automojo.integrationruntime.results.streaming.resultstreamer import (
    ResultStreamer,
    RestResultStreamer,
    WebSocketResultStreamer,
    create_result_streamer,
    StreamingJsonEncoder
)


class StreamingJsonEncoderTests(unittest.TestCase):
    """Tests for the StreamingJsonEncoder class."""

    def test_datetime_encoding(self):
        """Test that datetime objects are encoded as ISO format strings."""
        dt = datetime(2025, 2, 20, 10, 30, 0)
        data = {"timestamp": dt}
        
        result = json.dumps(data, cls=StreamingJsonEncoder)
        parsed = json.loads(result)
        
        self.assertEqual(parsed["timestamp"], "2025-02-20T10:30:00")

    def test_regular_types_encoding(self):
        """Test that regular types are encoded normally."""
        data = {
            "string": "test",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "list": [1, 2, 3],
            "dict": {"nested": "value"}
        }
        
        result = json.dumps(data, cls=StreamingJsonEncoder)
        parsed = json.loads(result)
        
        self.assertEqual(parsed, data)


class MockStreamingServiceHandler(BaseHTTPRequestHandler):
    """Handler for mock streaming service that receives results."""

    def do_POST(self):
        """Handle POST requests containing streamed results."""
        content_length = int(self.headers.get('Content-Length', 0))
        
        if content_length > 0:
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body)
                
                with self.server.lock:
                    self.server.received_results.append({
                        'data': data,
                        'headers': dict(self.headers),
                        'timestamp': time.time()
                    })
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "ok"}')
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress logging to keep test output clean."""
        pass


class MockStreamingService(ThreadingMixIn, HTTPServer):
    """Mock streaming service for testing REST streaming."""

    def __init__(self, server_address):
        super().__init__(server_address, MockStreamingServiceHandler)
        self.received_results = []
        self.lock = threading.Lock()
        self._server_thread = None

    def start(self):
        """Start the mock service in a background thread."""
        self._server_thread = threading.Thread(
            target=self.serve_forever,
            daemon=True
        )
        self._server_thread.start()
        time.sleep(0.05)

    def stop(self):
        """Stop the mock service."""
        self.shutdown()
        self.server_close()

    def get_received_results(self):
        """Get a copy of received results in a thread-safe manner."""
        with self.lock:
            return list(self.received_results)

    def clear_received_results(self):
        """Clear received results in a thread-safe manner."""
        with self.lock:
            self.received_results.clear()


class CreateResultStreamerTests(unittest.TestCase):
    """Tests for the create_result_streamer factory function."""

    def test_create_rest_streamer(self):
        """Test creating a REST result streamer."""
        info = StreamingInfo(
            protocol=StreamingProtocol.REST,
            streaming_url="https://example.com/api/results"
        )
        
        streamer = create_result_streamer(info)
        
        self.assertIsInstance(streamer, RestResultStreamer)

    def test_create_websocket_streamer(self):
        """Test creating a WebSocket result streamer."""
        info = StreamingInfo(
            protocol=StreamingProtocol.WEBSOCKET,
            streaming_url="wss://example.com/ws/results"
        )
        
        streamer = create_result_streamer(info)
        
        self.assertIsInstance(streamer, WebSocketResultStreamer)


class RestResultStreamerTests(unittest.TestCase):
    """Tests for the RestResultStreamer class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_service = MockStreamingService(("127.0.0.1", 0))
        self.mock_service.start()
        self.actual_port = self.mock_service.server_address[1]
        self.streaming_url = f"http://127.0.0.1:{self.actual_port}/api/results"
        
        self.streaming_info = StreamingInfo(
            protocol=StreamingProtocol.REST,
            streaming_url=self.streaming_url,
            stream_previews=True,
            stream_results=True
        )
        
        self.streamer = None

    def tearDown(self):
        """Clean up test fixtures."""
        if self.streamer is not None:
            try:
                self.streamer.stop()
            except Exception:
                pass
        
        if self.mock_service is not None:
            try:
                self.mock_service.stop()
            except Exception:
                pass

    def test_streamer_starts_and_stops(self):
        """Test that the streamer can start and stop."""
        self.streamer = RestResultStreamer(self.streaming_info)
        
        self.assertFalse(self.streamer.is_running)
        
        self.streamer.start()
        self.assertTrue(self.streamer.is_running)
        
        self.streamer.stop()
        self.assertFalse(self.streamer.is_running)

    def test_streamer_connects_to_service(self):
        """Test that the streamer connects to the REST service."""
        self.streamer = RestResultStreamer(self.streaming_info)
        self.streamer.start()
        
        # Give time for connection
        time.sleep(0.1)
        
        self.assertTrue(self.streamer.is_connected)

    def test_stream_preview_sends_to_service(self):
        """Test that streaming a preview sends it to the service."""
        self.streamer = RestResultStreamer(self.streaming_info)
        self.streamer.start()
        
        # Stream a preview
        preview_dict = {
            "name": "test_function",
            "instance": "test-uuid-123",
            "result": "UNSET"
        }
        self.streamer.stream_preview(preview_dict)
        
        # Wait for delivery
        time.sleep(0.2)
        
        received = self.mock_service.get_received_results()
        self.assertGreater(len(received), 0)
        
        # Verify the preview was received
        found_preview = False
        for entry in received:
            if entry['data'].get('type') == 'preview':
                found_preview = True
                self.assertEqual(entry['data']['data']['name'], "test_function")
                break
        
        self.assertTrue(found_preview, "Preview should be received by service")

    def test_stream_result_sends_to_service(self):
        """Test that streaming a result sends it to the service."""
        self.streamer = RestResultStreamer(self.streaming_info)
        self.streamer.start()
        
        # Stream a result
        result_dict = {
            "name": "test_function",
            "instance": "test-uuid-123",
            "result": "PASSED",
            "detail": {"errors": [], "failures": [], "warnings": []}
        }
        self.streamer.stream_result(result_dict)
        
        # Wait for delivery
        time.sleep(0.2)
        
        received = self.mock_service.get_received_results()
        self.assertGreater(len(received), 0)
        
        # Verify the result was received
        found_result = False
        for entry in received:
            if entry['data'].get('type') == 'result':
                found_result = True
                self.assertEqual(entry['data']['data']['name'], "test_function")
                self.assertEqual(entry['data']['data']['result'], "PASSED")
                break
        
        self.assertTrue(found_result, "Result should be received by service")

    def test_streaming_stats_updated(self):
        """Test that streaming statistics are updated."""
        self.streamer = RestResultStreamer(self.streaming_info)
        self.streamer.start()
        
        # Stream some results
        for i in range(3):
            self.streamer.stream_preview({"name": f"test_{i}", "result": "UNSET"})
            self.streamer.stream_result({"name": f"test_{i}", "result": "PASSED"})
        
        # Wait for delivery
        time.sleep(0.3)
        
        stats = self.streamer.stats
        self.assertEqual(stats["previews_sent"], 3)
        self.assertEqual(stats["results_sent"], 3)
        self.assertEqual(stats["errors"], 0)

    def test_custom_headers_sent(self):
        """Test that custom headers are sent with requests."""
        custom_headers = {
            "Authorization": "Bearer test-token",
            "X-Custom-Header": "custom-value"
        }
        
        streaming_info = StreamingInfo(
            protocol=StreamingProtocol.REST,
            streaming_url=self.streaming_url,
            streaming_headers=custom_headers
        )
        
        self.streamer = RestResultStreamer(streaming_info)
        self.streamer.start()
        
        # Stream a result
        self.streamer.stream_result({"name": "test", "result": "PASSED"})
        
        # Wait for delivery
        time.sleep(0.2)
        
        received = self.mock_service.get_received_results()
        self.assertGreater(len(received), 0)
        
        headers = received[0]['headers']
        self.assertEqual(headers.get('Authorization'), "Bearer test-token")
        self.assertEqual(headers.get('X-Custom-Header'), "custom-value")

    def test_stream_previews_disabled(self):
        """Test that previews are not sent when disabled."""
        streaming_info = StreamingInfo(
            protocol=StreamingProtocol.REST,
            streaming_url=self.streaming_url,
            stream_previews=False,
            stream_results=True
        )
        
        self.streamer = RestResultStreamer(streaming_info)
        self.streamer.start()
        
        # Stream a preview (should be ignored)
        self.streamer.stream_preview({"name": "test", "result": "UNSET"})
        
        # Stream a result (should be sent)
        self.streamer.stream_result({"name": "test", "result": "PASSED"})
        
        # Wait for delivery
        time.sleep(0.2)
        
        received = self.mock_service.get_received_results()
        
        # Should only have the result, not the preview
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]['data']['type'], 'result')


class StreamingCallbackTests(unittest.TestCase):
    """Tests for streaming with custom callbacks."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_service = MockStreamingService(("127.0.0.1", 0))
        self.mock_service.start()
        self.actual_port = self.mock_service.server_address[1]
        self.streaming_url = f"http://127.0.0.1:{self.actual_port}/api/results"
        
        self.streamer = None

    def tearDown(self):
        """Clean up test fixtures."""
        if self.streamer is not None:
            try:
                self.streamer.stop()
            except Exception:
                pass
        
        if self.mock_service is not None:
            try:
                self.mock_service.stop()
            except Exception:
                pass

    def test_callback_invoked_for_results(self):
        """Test that the callback is invoked for each result."""
        callback_invocations = []
        
        def on_result(result_dict, is_preview):
            callback_invocations.append((result_dict.copy(), is_preview))
            return True
        
        callback = StreamingCallback(on_result=on_result)
        
        streaming_info = StreamingInfo(
            protocol=StreamingProtocol.REST,
            streaming_url=self.streaming_url
        )
        
        self.streamer = RestResultStreamer(streaming_info, callback)
        self.streamer.start()
        
        # Stream results
        self.streamer.stream_preview({"name": "test", "result": "UNSET"})
        self.streamer.stream_result({"name": "test", "result": "PASSED"})
        
        # Wait for processing
        time.sleep(0.2)
        
        self.assertEqual(len(callback_invocations), 2)
        self.assertTrue(callback_invocations[0][1])  # is_preview = True
        self.assertFalse(callback_invocations[1][1])  # is_preview = False

    def test_callback_can_filter_results(self):
        """Test that the callback can filter results by returning False."""
        def on_result(result_dict, is_preview):
            # Only allow results, not previews
            return not is_preview
        
        callback = StreamingCallback(on_result=on_result)
        
        streaming_info = StreamingInfo(
            protocol=StreamingProtocol.REST,
            streaming_url=self.streaming_url
        )
        
        self.streamer = RestResultStreamer(streaming_info, callback)
        self.streamer.start()
        
        # Stream results
        self.streamer.stream_preview({"name": "test", "result": "UNSET"})
        self.streamer.stream_result({"name": "test", "result": "PASSED"})
        
        # Wait for processing
        time.sleep(0.2)
        
        received = self.mock_service.get_received_results()
        
        # Should only have the result, not the preview
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]['data']['type'], 'result')

    def test_connect_callback_invoked(self):
        """Test that the on_connect callback is invoked."""
        connect_called = []
        
        def on_result(result_dict, is_preview):
            return True
        
        def on_connect():
            connect_called.append(True)
        
        callback = StreamingCallback(
            on_result=on_result,
            on_connect=on_connect
        )
        
        streaming_info = StreamingInfo(
            protocol=StreamingProtocol.REST,
            streaming_url=self.streaming_url
        )
        
        self.streamer = RestResultStreamer(streaming_info, callback)
        self.streamer.start()
        
        # Wait for connection
        time.sleep(0.1)
        
        self.assertEqual(len(connect_called), 1)


if __name__ == "__main__":
    unittest.main()
