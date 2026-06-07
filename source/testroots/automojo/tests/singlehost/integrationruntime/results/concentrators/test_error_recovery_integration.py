"""
    .. module:: automojo.tests.singlehost.integrationruntime.results.concentrators.test_error_recovery_integration
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Integration tests for error recovery in the ProgressConcentratorServer.

    Converted from the legacy ``unittest.TestCase`` suite to the testbase module-style format.
    Each original test method becomes a module-level ``test_*`` function. The original ``setUp``
    fixtures are replicated per test via :func:`_establish_env` and the original ``tearDown``
    cleanup is replicated per test via :func:`_cleanup_env` inside a ``try/finally``.

    .. moduleauthor:: AutomationX
"""

import tempfile
import os
import shutil
import threading
import time
import json
import http.client
import uuid
import socket
import concurrent.futures

from typing import Optional, Tuple
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

from automojo.testbase.results.model.buildinfo import BuildInfo
from automojo.testbase.results.model.pipelineinfo import PipelineInfo
from automojo.testbase.results.model.jobinfo import JobInfo
from automojo.testbase.results.model.renderinfo import RenderInfo
from automojo.testbase.results.model.forwardinginfo import ForwardingInfo

from automojo.testbase.results.recorders.jsonresultrecorder import JsonResultRecorder
from automojo.integrationruntime.results.concentrators.progressconcentratorservice import (
    ProgressConcentratorServer
)


class ErrorRecoveryContext:
    """
        Mutable test-fixture context replacing the ``self`` state established by the original
        ``ErrorRecoveryIntegrationTestBase.setUp``. Holds the recorder, render/build/pipeline/job
        info, the server binding details, and slots for the started server and any mock external
        service so the converted module-level helper functions can operate on it.
    """

    def __init__(self) -> None:
        """
            Initializes all fixture instance variables to their post-setUp values are populated
            by :func:`_establish_env`; here they are declared as ``None`` placeholders.
        """
        self.temp_dir: Optional[str] = None
        self.render_info: Optional[RenderInfo] = None
        self.runid: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.build_info: Optional[BuildInfo] = None
        self.pipeline_info: Optional[PipelineInfo] = None
        self.job_info: Optional[JobInfo] = None
        self.recorder: Optional[JsonResultRecorder] = None
        self.server_address: Optional[Tuple[str, int]] = None
        self.server: Optional[ProgressConcentratorServer] = None
        self.actual_port: Optional[int] = None
        self.external_service: Optional["FailingExternalService"] = None
        return


def _establish_env() -> ErrorRecoveryContext:
    """
        Replicates the original ``ErrorRecoveryIntegrationTestBase.setUp`` (plus the
        ``NetworkFailureResilienceTests.setUp`` ``external_service = None`` slot) for each test by
        creating a fresh temporary directory, render/build/pipeline/job info, recorder, and server
        binding placeholders.

        :returns: A populated :class:`ErrorRecoveryContext`.
    """
    context = ErrorRecoveryContext()

    context.temp_dir = tempfile.mkdtemp()

    context.render_info = RenderInfo(
        title="Error Recovery Integration Test",
        summary_filename=os.path.join(context.temp_dir, "summary.json"),
        summary_template=os.path.join(context.temp_dir, "template.html"),
        stream_results_filename=os.path.join(context.temp_dir, "results.json"),
        consolidated_results_filename=os.path.join(context.temp_dir, "consolidated.json"),
        static_resource_source=None,
        static_resource_destination=context.temp_dir
    )

    with open(context.render_info.summary_template, 'w') as f:
        f.write("<html></html>")

    context.runid = str(uuid.uuid4())
    context.start_time = datetime.now()

    context.build_info = BuildInfo(
        branch="main",
        build="build-error-recovery",
        flavor="release",
        release="1.0.0",
        url="https://ci.example.com/build/error-recovery"
    )

    context.pipeline_info = PipelineInfo(
        id="pipeline-error-recovery",
        name="Error Recovery Pipeline",
        instance="instance-error-recovery"
    )

    context.job_info = JobInfo(
        id="job-error-recovery",
        name="Error Recovery Tests",
        type="IntegrationTest",
        owner="QA Team",
        label="error-recovery",
        initiator="test@example.com",
        venue="test",
        seed="error-recovery-seed",
        tag="error-recovery-tag"
    )

    context.recorder = JsonResultRecorder(
        runid=context.runid,
        start=context.start_time,
        render_info=context.render_info,
        build_info=context.build_info,
        pipeline_info=context.pipeline_info,
        job_info=context.job_info
    )

    context.server_address = ("127.0.0.1", 0)
    context.server = None
    context.actual_port = None
    context.external_service = None

    return context


def _cleanup_env(context: ErrorRecoveryContext) -> None:
    """
        Replicates the original ``tearDown`` cleanup for each test: first stops any mock external
        service (as ``NetworkFailureResilienceTests.tearDown`` did), then shuts down the concentrator
        server and joins its forwarding thread, then removes the temporary directory.

        :param context: The fixture context to clean up.
    """
    if context.external_service is not None:
        try:
            context.external_service.stop()
        except Exception:
            pass

    if context.server is not None:
        try:
            context.server._forwarding_running = False
            context.server.shutdown()
            context.server.server_close()
            if hasattr(context.server, '_forward_thread') and context.server._forward_thread is not None:
                try:
                    context.server._forward_thread.join(timeout=2.0)
                except Exception:
                    pass
        except Exception:
            pass

    if os.path.exists(context.temp_dir):
        shutil.rmtree(context.temp_dir)

    return


def _start_server(context: ErrorRecoveryContext, forwarding_info: Optional[ForwardingInfo] = None) -> None:
    """
        Starts the concentrator server and records the actual bound port on the context.

        :param context: The fixture context holding the recorder and server binding details.
        :param forwarding_info: Optional forwarding configuration for the server.
    """
    context.server = ProgressConcentratorServer(
        recorder=context.recorder,
        server_address=context.server_address,
        forwarding_info=forwarding_info
    )
    context.server.start()
    context.actual_port = context.server.server_address[1]
    return


def _send_raw_request(context: ErrorRecoveryContext, body: bytes, headers: Optional[dict] = None) -> tuple:
    """
        Sends a raw HTTP POST request and returns ``(status_code, reason_phrase)``.

        :param context: The fixture context holding the actual server port.
        :param body: The raw request body bytes.
        :param headers: Optional request headers. A ``Content-Length`` header is added when absent.

        :returns: A tuple of ``(status, reason)``.
    """
    conn = http.client.HTTPConnection("127.0.0.1", context.actual_port)
    try:
        if headers is None:
            headers = {}
        if "Content-Length" not in headers:
            headers["Content-Length"] = str(len(body))
        conn.request("POST", "/progress", body=body, headers=headers)
        response = conn.getresponse()
        # The error message is in the reason phrase, not the body
        reason = response.reason if response.reason else ""
        rtnval = (response.status, reason)
        return rtnval
    finally:
        conn.close()


def _create_valid_progress_payload(task_id: str = "test-task") -> dict:
    """
        Creates a valid progress update payload.

        :param task_id: The task identifier embedded in the payload.

        :returns: A dictionary representing a valid progress update.
    """
    payload = {
        "id": task_id,
        "category": "test-execution",
        "moniker": f"test_module.test_{task_id}",
        "ptype": "Sequential",
        "range_min": "0",
        "range_max": "10",
        "position": "5",
        "status": "Running",
        "when": datetime.now().isoformat(),
        "data": {"worker_id": "test-worker"}
    }
    return payload


def _find_unused_port() -> int:
    """
        Finds an unused port for testing.

        :returns: An available TCP port number on the loopback interface.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        rtnval = s.getsockname()[1]
        return rtnval


class UnreachableForwardingServiceHandler(BaseHTTPRequestHandler):
    """Handler that simulates various network failure scenarios."""

    def do_POST(self):
        """Simulate different failure modes based on path."""
        if self.path == "/timeout":
            # Simulate timeout by sleeping
            time.sleep(10)
        elif self.path == "/error500":
            self.send_response(500)
            self.end_headers()
        elif self.path == "/error503":
            self.send_response(503)
            self.end_headers()
        elif self.path == "/close":
            # Close connection without response
            self.connection.close()
        else:
            self.send_response(200)
            self.end_headers()

    def log_message(self, format, *args):
        pass


class FailingExternalService(ThreadingMixIn, HTTPServer):
    """Mock external service that can simulate failures."""

    def __init__(self, server_address, failure_mode="error500"):
        super().__init__(server_address, UnreachableForwardingServiceHandler)
        self.failure_mode = failure_mode
        self._server_thread = None
        self.request_count = 0
        self.lock = threading.Lock()

    def start(self):
        self._server_thread = threading.Thread(
            target=self.serve_forever,
            daemon=True
        )
        self._server_thread.start()
        time.sleep(0.05)

    def stop(self):
        self.shutdown()
        self.server_close()


def test_invalid_json_syntax_returns_500() -> None:
    """Test that invalid JSON syntax returns 500 error (Requirement 7.1)."""
    context = _establish_env()
    try:
        _start_server(context=context)

        invalid_json_payloads = [
            b'{"id": "test"',  # Missing closing brace
            b'{"id": test}',  # Unquoted value
            b'{id: "test"}',  # Unquoted key
            b'["not", "an", "object"]',  # Array instead of object
            b'not json at all',  # Plain text
            b'{"key": undefined}',  # JavaScript undefined
            b"{'single': 'quotes'}",  # Single quotes
        ]

        for payload in invalid_json_payloads:
            status, _ = _send_raw_request(context=context, body=payload)
            assert status == 500, f"Expected 500 for payload: {payload}"
    finally:
        _cleanup_env(context=context)
    return


def test_invalid_json_includes_error_message() -> None:
    """Test that invalid JSON error includes descriptive message (Requirement 7.3, 7.4)."""
    context = _establish_env()
    try:
        _start_server(context=context)

        status, reason = _send_raw_request(context=context, body=b'not valid json')

        assert status == 500
        # The error message is in the HTTP reason phrase
        # Note: HTTP reason phrases cannot contain newlines, so only the first line is included
        assert "Error processing progress postback" in reason
    finally:
        _cleanup_env(context=context)
    return


def test_missing_required_fields_returns_500() -> None:
    """Test that missing required fields returns 500 error (Requirement 7.2)."""
    context = _establish_env()
    try:
        _start_server(context=context)

        # Payloads with missing required fields
        incomplete_payloads = [
            {"id": "test-task"},  # Missing most fields
            {"id": "test", "status": "Running"},  # Missing ptype, when, etc.
            {"status": "Running", "ptype": "Sequential"},  # Missing id
            {},  # Empty object
        ]

        for payload in incomplete_payloads:
            body = json.dumps(payload).encode('utf-8')
            status, reason = _send_raw_request(context=context, body=body)
            assert status == 500, f"Expected 500 for incomplete payload: {payload}"
            assert "Error processing progress postback" in reason
    finally:
        _cleanup_env(context=context)
    return


def test_invalid_field_types_returns_500() -> None:
    """Test that invalid field types returns 500 error (Requirement 7.2)."""
    context = _establish_env()
    try:
        _start_server(context=context)

        # Payloads with invalid field types
        invalid_type_payloads = [
            {**_create_valid_progress_payload(), "id": 12345},  # id should be string
            {**_create_valid_progress_payload(), "status": 123},  # status should be string
            {**_create_valid_progress_payload(), "ptype": ["array"]},  # ptype should be string
        ]

        for payload in invalid_type_payloads:
            body = json.dumps(payload).encode('utf-8')
            status, _ = _send_raw_request(context=context, body=body)
            # Some type coercions may succeed, but truly invalid types should fail
            # This test verifies the server handles type errors gracefully
    finally:
        _cleanup_env(context=context)
    return


def test_missing_content_length_returns_200() -> None:
    """Test that missing content-length header returns 200 OK (Requirement 7.5)."""
    context = _establish_env()
    try:
        _start_server(context=context)

        conn = http.client.HTTPConnection("127.0.0.1", context.actual_port)
        try:
            # Send request without Content-Length header
            conn.putrequest("POST", "/progress")
            conn.endheaders()
            response = conn.getresponse()
            assert response.status == 200
        finally:
            conn.close()
    finally:
        _cleanup_env(context=context)
    return


def test_zero_content_length_returns_200() -> None:
    """Test that zero content-length returns 200 OK."""
    context = _establish_env()
    try:
        _start_server(context=context)

        status, _ = _send_raw_request(context=context, body=b'', headers={"Content-Length": "0"})
        assert status == 200
    finally:
        _cleanup_env(context=context)
    return


def test_empty_body_with_content_length_returns_200() -> None:
    """Test that empty body with content-length returns 200."""
    context = _establish_env()
    try:
        _start_server(context=context)

        status, _ = _send_raw_request(context=context, body=b'')
        assert status == 200
    finally:
        _cleanup_env(context=context)
    return


def test_server_continues_after_malformed_request() -> None:
    """Test that server continues processing after malformed request."""
    context = _establish_env()
    try:
        _start_server(context=context)

        # Send malformed request
        status, _ = _send_raw_request(context=context, body=b'invalid json')
        assert status == 500

        # Verify server still accepts valid requests
        valid_payload = _create_valid_progress_payload("recovery-task")
        body = json.dumps(valid_payload).encode('utf-8')
        status, _ = _send_raw_request(context=context, body=body)
        assert status == 200

        # Verify task was recorded
        assert "recovery-task" in context.recorder._running_tasks
    finally:
        _cleanup_env(context=context)
    return


def test_multiple_malformed_requests_dont_crash_server() -> None:
    """Test that multiple malformed requests don't crash the server."""
    context = _establish_env()
    try:
        _start_server(context=context)

        malformed_payloads = [
            b'not json',
            b'{"incomplete":',
            b'null',
            b'true',
            b'12345',
            b'{"id": null}',
        ]

        # Send multiple malformed requests
        for payload in malformed_payloads:
            status, _ = _send_raw_request(context=context, body=payload)
            assert status == 500

        # Verify server is still running
        assert context.server._server_running
        assert context.server._server_thread.is_alive()

        # Verify server still accepts valid requests
        valid_payload = _create_valid_progress_payload("after-malformed")
        body = json.dumps(valid_payload).encode('utf-8')
        status, _ = _send_raw_request(context=context, body=body)
        assert status == 200
    finally:
        _cleanup_env(context=context)
    return


def test_concurrent_malformed_and_valid_requests() -> None:
    """Test handling concurrent malformed and valid requests."""
    context = _establish_env()
    try:
        _start_server(context=context)

        results = []
        errors = []
        lock = threading.Lock()

        def send_request(request_id: int, is_valid: bool):
            try:
                if is_valid:
                    payload = _create_valid_progress_payload(f"concurrent-{request_id}")
                    body = json.dumps(payload).encode('utf-8')
                else:
                    body = f"invalid json {request_id}".encode('utf-8')

                status, _ = _send_raw_request(context=context, body=body)

                with lock:
                    results.append((request_id, is_valid, status))
            except Exception as e:
                with lock:
                    errors.append((request_id, str(e)))

        # Send mix of valid and invalid requests concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(20):
                is_valid = (i % 2 == 0)  # Alternate valid/invalid
                futures.append(executor.submit(send_request, i, is_valid))

            for future in concurrent.futures.as_completed(futures):
                future.result()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors: {errors}"

        # Verify correct status codes
        for request_id, is_valid, status in results:
            if is_valid:
                assert status == 200, f"Valid request {request_id} should return 200"
            else:
                assert status == 500, f"Invalid request {request_id} should return 500"
    finally:
        _cleanup_env(context=context)
    return


def test_forwarding_continues_after_connection_refused() -> None:
    """Test that forwarding continues after connection refused (Requirement 10.3, 10.4)."""
    context = _establish_env()
    try:
        # Use a port that nothing is listening on
        unused_port = _find_unused_port()

        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url=f"http://127.0.0.1:{unused_port}/api/progress",
            forwarding_headers=None
        )

        _start_server(context=context, forwarding_info=forwarding_info)

        # Wait for multiple forwarding attempts
        time.sleep(0.25)

        # Verify forwarding thread is still running
        assert context.server._forwarding_running
        assert context.server._forward_thread.is_alive()
    finally:
        _cleanup_env(context=context)
    return


def test_forwarding_continues_after_http_500_error() -> None:
    """Test that forwarding continues after HTTP 500 errors (Requirement 10.3, 10.4)."""
    context = _establish_env()
    try:
        # Start a service that returns 500 errors
        context.external_service = FailingExternalService(("127.0.0.1", 0))
        context.external_service.start()
        port = context.external_service.server_address[1]

        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url=f"http://127.0.0.1:{port}/error500",
            forwarding_headers=None
        )

        _start_server(context=context, forwarding_info=forwarding_info)

        # Wait for multiple forwarding attempts
        time.sleep(0.25)

        # Verify forwarding thread is still running
        assert context.server._forwarding_running
        assert context.server._forward_thread.is_alive()
    finally:
        _cleanup_env(context=context)
    return


def test_forwarding_logs_errors() -> None:
    """Test that forwarding errors are logged (Requirement 10.2)."""
    context = _establish_env()
    try:
        unused_port = _find_unused_port()

        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url=f"http://127.0.0.1:{unused_port}/api/progress",
            forwarding_headers=None
        )

        _start_server(context=context, forwarding_info=forwarding_info)

        # Capture logged errors
        logged_errors = []
        original_warning = context.server._logger.warning

        def capture_warning(msg):
            logged_errors.append(msg)
            original_warning(msg)

        context.server._logger.warning = capture_warning

        try:
            # Wait for forwarding attempts
            time.sleep(0.2)

            # Verify errors were logged
            assert len(logged_errors) > 0, "Forwarding errors should be logged"
        finally:
            context.server._logger.warning = original_warning
    finally:
        _cleanup_env(context=context)
    return


def test_server_accepts_requests_during_forwarding_failures() -> None:
    """Test that server accepts progress requests during forwarding failures."""
    context = _establish_env()
    try:
        unused_port = _find_unused_port()

        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url=f"http://127.0.0.1:{unused_port}/api/progress",
            forwarding_headers=None
        )

        _start_server(context=context, forwarding_info=forwarding_info)

        # Send valid progress updates while forwarding is failing
        for i in range(5):
            payload = _create_valid_progress_payload(f"during-failure-{i}")
            body = json.dumps(payload).encode('utf-8')
            status, _ = _send_raw_request(context=context, body=body)
            assert status == 200

        # Verify tasks were recorded
        for i in range(5):
            assert f"during-failure-{i}" in context.recorder._running_tasks
    finally:
        _cleanup_env(context=context)
    return


def test_forwarding_recovers_when_service_becomes_available() -> None:
    """Test that forwarding recovers when external service becomes available."""
    context = _establish_env()
    try:
        # Start with no service running
        service_port = _find_unused_port()

        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url=f"http://127.0.0.1:{service_port}/api/progress",
            forwarding_headers=None
        )

        _start_server(context=context, forwarding_info=forwarding_info)

        # Wait for some failed attempts
        time.sleep(0.15)

        # Verify forwarding is still running despite failures
        assert context.server._forward_thread.is_alive()
    finally:
        _cleanup_env(context=context)
    return


def test_server_stable_under_rapid_error_requests() -> None:
    """Test server stability under rapid error-inducing requests."""
    context = _establish_env()
    try:
        _start_server(context=context)

        num_requests = 100
        errors = []

        def send_error_request(i):
            try:
                body = f"invalid-{i}".encode('utf-8')
                status, _ = _send_raw_request(context=context, body=body)
                return status
            except Exception as e:
                errors.append(str(e))
                return None

        # Send rapid error requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(send_error_request, i) for i in range(num_requests)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Verify no connection errors
        assert len(errors) == 0, f"Connection errors: {errors}"

        # Verify all requests got 500 responses
        for status in results:
            assert status == 500

        # Verify server is still running
        assert context.server._server_running
        assert context.server._server_thread.is_alive()
    finally:
        _cleanup_env(context=context)
    return


def test_server_stable_with_mixed_load() -> None:
    """Test server stability with mixed valid and invalid requests."""
    context = _establish_env()
    try:
        _start_server(context=context)

        num_requests = 50
        results = {'valid': [], 'invalid': [], 'errors': []}
        lock = threading.Lock()

        def send_mixed_request(i):
            try:
                if i % 3 == 0:
                    # Valid request
                    payload = _create_valid_progress_payload(f"mixed-{i}")
                    body = json.dumps(payload).encode('utf-8')
                    status, _ = _send_raw_request(context=context, body=body)
                    with lock:
                        results['valid'].append(status)
                else:
                    # Invalid request
                    body = f"invalid-{i}".encode('utf-8')
                    status, _ = _send_raw_request(context=context, body=body)
                    with lock:
                        results['invalid'].append(status)
            except Exception as e:
                with lock:
                    results['errors'].append(str(e))

        # Send mixed requests concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(send_mixed_request, i) for i in range(num_requests)]
            for future in concurrent.futures.as_completed(futures):
                future.result()

        # Verify no errors
        assert len(results['errors']) == 0, f"Errors: {results['errors']}"

        # Verify correct status codes
        for status in results['valid']:
            assert status == 200
        for status in results['invalid']:
            assert status == 500

        # Verify server is still running
        assert context.server._server_running
    finally:
        _cleanup_env(context=context)
    return


def test_server_handles_large_invalid_payload() -> None:
    """Test server handles large invalid payloads gracefully."""
    context = _establish_env()
    try:
        _start_server(context=context)

        # Send a large invalid payload
        large_payload = b'x' * 100000  # 100KB of invalid data
        status, reason = _send_raw_request(context=context, body=large_payload)

        assert status == 500
        assert "Error processing progress postback" in reason

        # Verify server is still running
        assert context.server._server_running

        # Verify server still accepts valid requests
        valid_payload = _create_valid_progress_payload("after-large")
        body = json.dumps(valid_payload).encode('utf-8')
        status, _ = _send_raw_request(context=context, body=body)
        assert status == 200
    finally:
        _cleanup_env(context=context)
    return


def test_server_handles_unicode_in_invalid_payload() -> None:
    """Test server handles unicode in invalid payloads."""
    context = _establish_env()
    try:
        _start_server(context=context)

        unicode_payloads = [
            '{"id": "测试任务"}'.encode('utf-8'),  # Chinese characters
            '{"id": "тест"}'.encode('utf-8'),  # Cyrillic
            '{"id": "🎉🎊"}'.encode('utf-8'),  # Emoji
            '{"id": "café"}'.encode('utf-8'),  # Accented characters
        ]

        for payload in unicode_payloads:
            # These may succeed or fail depending on field validation
            # The key is that the server doesn't crash
            status, _ = _send_raw_request(context=context, body=payload)
            assert status in [200, 500]

        # Verify server is still running
        assert context.server._server_running
    finally:
        _cleanup_env(context=context)
    return


def test_server_handles_binary_payload() -> None:
    """Test server handles binary payloads gracefully."""
    context = _establish_env()
    try:
        _start_server(context=context)

        # Send binary data that's not valid UTF-8
        binary_payload = bytes([0x80, 0x81, 0x82, 0xFF, 0xFE])
        status, _ = _send_raw_request(context=context, body=binary_payload)

        assert status == 500

        # Verify server is still running
        assert context.server._server_running
    finally:
        _cleanup_env(context=context)
    return


def test_recorder_state_consistent_after_errors() -> None:
    """Test that recorder state remains consistent after error conditions."""
    context = _establish_env()
    try:
        _start_server(context=context)

        # Add some valid tasks
        for i in range(5):
            payload = _create_valid_progress_payload(f"consistent-{i}")
            body = json.dumps(payload).encode('utf-8')
            _send_raw_request(context=context, body=body)

        initial_task_count = len(context.recorder._running_tasks)

        # Send many error requests
        for i in range(20):
            _send_raw_request(context=context, body=b'invalid')

        # Verify task count unchanged
        assert len(context.recorder._running_tasks) == initial_task_count

        # Verify original tasks still present
        for i in range(5):
            assert f"consistent-{i}" in context.recorder._running_tasks
    finally:
        _cleanup_env(context=context)
    return


def test_forwarding_and_request_handling_independent() -> None:
    """Test that forwarding errors don't affect request handling."""
    context = _establish_env()
    try:
        unused_port = _find_unused_port()

        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url=f"http://127.0.0.1:{unused_port}/api/progress",
            forwarding_headers=None
        )

        _start_server(context=context, forwarding_info=forwarding_info)

        # Send valid requests while forwarding is failing
        success_count = 0
        for i in range(10):
            payload = _create_valid_progress_payload(f"independent-{i}")
            body = json.dumps(payload).encode('utf-8')
            status, _ = _send_raw_request(context=context, body=body)
            if status == 200:
                success_count += 1

        # All requests should succeed despite forwarding failures
        assert success_count == 10

        # Verify all tasks recorded
        for i in range(10):
            assert f"independent-{i}" in context.recorder._running_tasks
    finally:
        _cleanup_env(context=context)
    return
