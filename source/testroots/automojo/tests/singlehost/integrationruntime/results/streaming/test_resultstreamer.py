"""
    .. module:: automojo.tests.singlehost.integrationruntime.results.streaming.test_resultstreamer
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Unit tests for ResultStreamer classes.

    This module contains unit tests for the ResultStreamer base class and
    its concrete implementations (RestResultStreamer, WebSocketResultStreamer).

    .. moduleauthor:: AutomationX
"""

import threading
import time
import json

from typing import Any, Dict, List

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


def _establish_rest_env() -> Dict[str, Any]:
    """
        Replicates the ``RestResultStreamerTests.setUp`` fixture for each test by
        starting a mock streaming service, capturing its bound port, building the
        streaming URL and the REST ``StreamingInfo`` (with previews and results
        enabled) and seeding the per-test streamer slot used by the teardown.

        :returns: A dictionary carrying the mock service, the actual port, the
                  streaming URL, the streaming info and the ``streamer`` slot that
                  mirrors the original ``self.streamer`` attribute used by teardown.
    """
    mock_service = MockStreamingService(("127.0.0.1", 0))
    mock_service.start()
    actual_port = mock_service.server_address[1]
    streaming_url = f"http://127.0.0.1:{actual_port}/api/results"

    streaming_info = StreamingInfo(
        protocol=StreamingProtocol.REST,
        streaming_url=streaming_url,
        stream_previews=True,
        stream_results=True
    )

    env: Dict[str, Any] = {
        "mock_service": mock_service,
        "actual_port": actual_port,
        "streaming_url": streaming_url,
        "streaming_info": streaming_info,
        "streamer": None
    }
    return env


def _establish_callback_env() -> Dict[str, Any]:
    """
        Replicates the ``StreamingCallbackTests.setUp`` fixture for each test by
        starting a mock streaming service, capturing its bound port and building the
        streaming URL. Unlike the REST fixture, this fixture does NOT pre-build a
        ``StreamingInfo`` because the callback tests construct their own.

        :returns: A dictionary carrying the mock service, the actual port, the
                  streaming URL and the ``streamer`` slot that mirrors the original
                  ``self.streamer`` attribute used by teardown.
    """
    mock_service = MockStreamingService(("127.0.0.1", 0))
    mock_service.start()
    actual_port = mock_service.server_address[1]
    streaming_url = f"http://127.0.0.1:{actual_port}/api/results"

    env: Dict[str, Any] = {
        "mock_service": mock_service,
        "actual_port": actual_port,
        "streaming_url": streaming_url,
        "streamer": None
    }
    return env


def _cleanup_env(env: Dict[str, Any]) -> None:
    """
        Replicates the ``tearDown`` shared by ``RestResultStreamerTests`` and
        ``StreamingCallbackTests`` for each test by stopping the streamer (if one
        was created) and then stopping the mock streaming service, swallowing any
        exception raised during cleanup exactly as the original did.

        :param env: The environment dictionary produced by one of the
                    ``_establish_*_env`` helpers.
    """
    streamer = env["streamer"]
    mock_service = env["mock_service"]

    if streamer is not None:
        try:
            streamer.stop()
        except Exception:
            pass

    if mock_service is not None:
        try:
            mock_service.stop()
        except Exception:
            pass
    return


def test_datetime_encoding() -> None:
    """
        Test that datetime objects are encoded as ISO format strings.
    """
    dt = datetime(2025, 2, 20, 10, 30, 0)
    data = {"timestamp": dt}

    result = json.dumps(data, cls=StreamingJsonEncoder)
    parsed = json.loads(result)

    assert parsed["timestamp"] == "2025-02-20T10:30:00"
    return


def test_regular_types_encoding() -> None:
    """
        Test that regular types are encoded normally.
    """
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

    assert parsed == data
    return


def test_create_rest_streamer() -> None:
    """
        Test creating a REST result streamer.
    """
    info = StreamingInfo(
        protocol=StreamingProtocol.REST,
        streaming_url="https://example.com/api/results"
    )

    streamer = create_result_streamer(info)

    assert isinstance(streamer, RestResultStreamer)
    return


def test_create_websocket_streamer() -> None:
    """
        Test creating a WebSocket result streamer.
    """
    info = StreamingInfo(
        protocol=StreamingProtocol.WEBSOCKET,
        streaming_url="wss://example.com/ws/results"
    )

    streamer = create_result_streamer(info)

    assert isinstance(streamer, WebSocketResultStreamer)
    return


def test_streamer_starts_and_stops() -> None:
    """
        Test that the streamer can start and stop.
    """
    env = _establish_rest_env()
    try:
        env["streamer"] = RestResultStreamer(env["streaming_info"])
        streamer = env["streamer"]

        assert not streamer.is_running

        streamer.start()
        assert streamer.is_running

        streamer.stop()
        assert not streamer.is_running
    finally:
        _cleanup_env(env=env)
    return


def test_streamer_connects_to_service() -> None:
    """
        Test that the streamer connects to the REST service.
    """
    env = _establish_rest_env()
    try:
        env["streamer"] = RestResultStreamer(env["streaming_info"])
        streamer = env["streamer"]
        streamer.start()

        # Give time for connection
        time.sleep(0.1)

        assert streamer.is_connected
    finally:
        _cleanup_env(env=env)
    return


def test_stream_preview_sends_to_service() -> None:
    """
        Test that streaming a preview sends it to the service.
    """
    env = _establish_rest_env()
    try:
        env["streamer"] = RestResultStreamer(env["streaming_info"])
        streamer = env["streamer"]
        streamer.start()

        # Stream a preview
        preview_dict = {
            "name": "test_function",
            "instance": "test-uuid-123",
            "result": "UNSET"
        }
        streamer.stream_preview(preview_dict)

        # Wait for delivery
        time.sleep(0.2)

        received = env["mock_service"].get_received_results()
        assert len(received) > 0

        # Verify the preview was received
        found_preview = False
        for entry in received:
            if entry['data'].get('type') == 'preview':
                found_preview = True
                assert entry['data']['data']['name'] == "test_function"
                break

        assert found_preview, "Preview should be received by service"
    finally:
        _cleanup_env(env=env)
    return


def test_stream_result_sends_to_service() -> None:
    """
        Test that streaming a result sends it to the service.
    """
    env = _establish_rest_env()
    try:
        env["streamer"] = RestResultStreamer(env["streaming_info"])
        streamer = env["streamer"]
        streamer.start()

        # Stream a result
        result_dict = {
            "name": "test_function",
            "instance": "test-uuid-123",
            "result": "PASSED",
            "detail": {"errors": [], "failures": [], "warnings": []}
        }
        streamer.stream_result(result_dict)

        # Wait for delivery
        time.sleep(0.2)

        received = env["mock_service"].get_received_results()
        assert len(received) > 0

        # Verify the result was received
        found_result = False
        for entry in received:
            if entry['data'].get('type') == 'result':
                found_result = True
                assert entry['data']['data']['name'] == "test_function"
                assert entry['data']['data']['result'] == "PASSED"
                break

        assert found_result, "Result should be received by service"
    finally:
        _cleanup_env(env=env)
    return


def test_streaming_stats_updated() -> None:
    """
        Test that streaming statistics are updated.
    """
    env = _establish_rest_env()
    try:
        env["streamer"] = RestResultStreamer(env["streaming_info"])
        streamer = env["streamer"]
        streamer.start()

        # Stream some results
        for i in range(3):
            streamer.stream_preview({"name": f"test_{i}", "result": "UNSET"})
            streamer.stream_result({"name": f"test_{i}", "result": "PASSED"})

        # Wait for delivery
        time.sleep(0.3)

        stats = streamer.stats
        assert stats["previews_sent"] == 3
        assert stats["results_sent"] == 3
        assert stats["errors"] == 0
    finally:
        _cleanup_env(env=env)
    return


def test_custom_headers_sent() -> None:
    """
        Test that custom headers are sent with requests.
    """
    env = _establish_rest_env()
    try:
        custom_headers = {
            "Authorization": "Bearer test-token",
            "X-Custom-Header": "custom-value"
        }

        streaming_info = StreamingInfo(
            protocol=StreamingProtocol.REST,
            streaming_url=env["streaming_url"],
            streaming_headers=custom_headers
        )

        env["streamer"] = RestResultStreamer(streaming_info)
        streamer = env["streamer"]
        streamer.start()

        # Stream a result
        streamer.stream_result({"name": "test", "result": "PASSED"})

        # Wait for delivery
        time.sleep(0.2)

        received = env["mock_service"].get_received_results()
        assert len(received) > 0

        headers = received[0]['headers']
        assert headers.get('Authorization') == "Bearer test-token"
        assert headers.get('X-Custom-Header') == "custom-value"
    finally:
        _cleanup_env(env=env)
    return


def test_stream_previews_disabled() -> None:
    """
        Test that previews are not sent when disabled.
    """
    env = _establish_rest_env()
    try:
        streaming_info = StreamingInfo(
            protocol=StreamingProtocol.REST,
            streaming_url=env["streaming_url"],
            stream_previews=False,
            stream_results=True
        )

        env["streamer"] = RestResultStreamer(streaming_info)
        streamer = env["streamer"]
        streamer.start()

        # Stream a preview (should be ignored)
        streamer.stream_preview({"name": "test", "result": "UNSET"})

        # Stream a result (should be sent)
        streamer.stream_result({"name": "test", "result": "PASSED"})

        # Wait for delivery
        time.sleep(0.2)

        received = env["mock_service"].get_received_results()

        # Should only have the result, not the preview
        assert len(received) == 1
        assert received[0]['data']['type'] == 'result'
    finally:
        _cleanup_env(env=env)
    return


def test_callback_invoked_for_results() -> None:
    """
        Test that the callback is invoked for each result.
    """
    env = _establish_callback_env()
    try:
        callback_invocations = []

        def on_result(result_dict, is_preview):
            callback_invocations.append((result_dict.copy(), is_preview))
            return True

        callback = StreamingCallback(on_result=on_result)

        streaming_info = StreamingInfo(
            protocol=StreamingProtocol.REST,
            streaming_url=env["streaming_url"]
        )

        env["streamer"] = RestResultStreamer(streaming_info, callback)
        streamer = env["streamer"]
        streamer.start()

        # Stream results
        streamer.stream_preview({"name": "test", "result": "UNSET"})
        streamer.stream_result({"name": "test", "result": "PASSED"})

        # Wait for processing
        time.sleep(0.2)

        assert len(callback_invocations) == 2
        assert callback_invocations[0][1]  # is_preview = True
        assert not callback_invocations[1][1]  # is_preview = False
    finally:
        _cleanup_env(env=env)
    return


def test_callback_can_filter_results() -> None:
    """
        Test that the callback can filter results by returning False.
    """
    env = _establish_callback_env()
    try:
        def on_result(result_dict, is_preview):
            # Only allow results, not previews
            return not is_preview

        callback = StreamingCallback(on_result=on_result)

        streaming_info = StreamingInfo(
            protocol=StreamingProtocol.REST,
            streaming_url=env["streaming_url"]
        )

        env["streamer"] = RestResultStreamer(streaming_info, callback)
        streamer = env["streamer"]
        streamer.start()

        # Stream results
        streamer.stream_preview({"name": "test", "result": "UNSET"})
        streamer.stream_result({"name": "test", "result": "PASSED"})

        # Wait for processing
        time.sleep(0.2)

        received = env["mock_service"].get_received_results()

        # Should only have the result, not the preview
        assert len(received) == 1
        assert received[0]['data']['type'] == 'result'
    finally:
        _cleanup_env(env=env)
    return


def test_connect_callback_invoked() -> None:
    """
        Test that the on_connect callback is invoked.
    """
    env = _establish_callback_env()
    try:
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
            streaming_url=env["streaming_url"]
        )

        env["streamer"] = RestResultStreamer(streaming_info, callback)
        streamer = env["streamer"]
        streamer.start()

        # Wait for connection
        time.sleep(0.1)

        assert len(connect_called) == 1
    finally:
        _cleanup_env(env=env)
    return
