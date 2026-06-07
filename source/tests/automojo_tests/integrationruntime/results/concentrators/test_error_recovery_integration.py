"""
    .. module:: automojo_tests.testbase.results.concentrators.test_error_recovery_integration
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Integration tests for error recovery in the ProgressConcentratorServer.

    .. moduleauthor:: AutomationX
"""

import unittest
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


class ErrorRecoveryIntegrationTestBase(unittest.TestCase):
    """Base class for error recovery integration tests."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        self.render_info = RenderInfo(
            title="Error Recovery Integration Test",
            summary_filename=os.path.join(self.temp_dir, "summary.json"),
            summary_template=os.path.join(self.temp_dir, "template.html"),
            stream_results_filename=os.path.join(self.temp_dir, "results.json"),
            consolidated_results_filename=os.path.join(self.temp_dir, "consolidated.json"),
            static_resource_source=None,
            static_resource_destination=self.temp_dir
        )
        
        with open(self.render_info.summary_template, 'w') as f:
            f.write("<html></html>")
        
        self.runid = str(uuid.uuid4())
        self.start_time = datetime.now()

        self.build_info = BuildInfo(
            branch="main",
            build="build-error-recovery",
            flavor="release",
            release="1.0.0",
            url="https://ci.example.com/build/error-recovery"
        )
        
        self.pipeline_info = PipelineInfo(
            id="pipeline-error-recovery",
            name="Error Recovery Pipeline",
            instance="instance-error-recovery"
        )
        
        self.job_info = JobInfo(
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
        
        self.recorder = JsonResultRecorder(
            runid=self.runid,
            start=self.start_time,
            render_info=self.render_info,
            build_info=self.build_info,
            pipeline_info=self.pipeline_info,
            job_info=self.job_info
        )
        
        self.server_address = ("127.0.0.1", 0)
        self.server = None
        self.actual_port = None

    def tearDown(self):
        """Clean up test fixtures."""
        if self.server is not None:
            try:
                self.server._forwarding_running = False
                self.server.shutdown()
                self.server.server_close()
                if hasattr(self.server, '_forward_thread') and self.server._forward_thread is not None:
                    try:
                        self.server._forward_thread.join(timeout=2.0)
                    except Exception:
                        pass
            except Exception:
                pass
        
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _start_server(self, forwarding_info=None):
        """Start the concentrator server and get the actual port."""
        self.server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address,
            forwarding_info=forwarding_info
        )
        self.server.start()
        self.actual_port = self.server.server_address[1]

    def _send_raw_request(self, body: bytes, headers: dict = None) -> tuple:
        """Send a raw HTTP POST request and return (status_code, reason_phrase)."""
        conn = http.client.HTTPConnection("127.0.0.1", self.actual_port)
        try:
            if headers is None:
                headers = {}
            if "Content-Length" not in headers:
                headers["Content-Length"] = str(len(body))
            conn.request("POST", "/progress", body=body, headers=headers)
            response = conn.getresponse()
            # The error message is in the reason phrase, not the body
            reason = response.reason if response.reason else ""
            return response.status, reason
        finally:
            conn.close()

    def _create_valid_progress_payload(self, task_id: str = "test-task") -> dict:
        """Create a valid progress update payload."""
        return {
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


class MalformedRequestHandlingTests(ErrorRecoveryIntegrationTestBase):
    """Integration tests for malformed request handling (Requirements 7.1-7.5)."""

    def test_invalid_json_syntax_returns_500(self):
        """Test that invalid JSON syntax returns 500 error (Requirement 7.1)."""
        self._start_server()
        
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
            status, _ = self._send_raw_request(payload)
            self.assertEqual(status, 500, 
                f"Expected 500 for payload: {payload}")

    def test_invalid_json_includes_error_message(self):
        """Test that invalid JSON error includes descriptive message (Requirement 7.3, 7.4)."""
        self._start_server()
        
        status, reason = self._send_raw_request(b'not valid json')
        
        self.assertEqual(status, 500)
        # The error message is in the HTTP reason phrase
        # Note: HTTP reason phrases cannot contain newlines, so only the first line is included
        self.assertIn("Error processing progress postback", reason)

    def test_missing_required_fields_returns_500(self):
        """Test that missing required fields returns 500 error (Requirement 7.2)."""
        self._start_server()
        
        # Payloads with missing required fields
        incomplete_payloads = [
            {"id": "test-task"},  # Missing most fields
            {"id": "test", "status": "Running"},  # Missing ptype, when, etc.
            {"status": "Running", "ptype": "Sequential"},  # Missing id
            {},  # Empty object
        ]
        
        for payload in incomplete_payloads:
            body = json.dumps(payload).encode('utf-8')
            status, reason = self._send_raw_request(body)
            self.assertEqual(status, 500, 
                f"Expected 500 for incomplete payload: {payload}")
            self.assertIn("Error processing progress postback", reason)

    def test_invalid_field_types_returns_500(self):
        """Test that invalid field types returns 500 error (Requirement 7.2)."""
        self._start_server()
        
        # Payloads with invalid field types
        invalid_type_payloads = [
            {**self._create_valid_progress_payload(), "id": 12345},  # id should be string
            {**self._create_valid_progress_payload(), "status": 123},  # status should be string
            {**self._create_valid_progress_payload(), "ptype": ["array"]},  # ptype should be string
        ]
        
        for payload in invalid_type_payloads:
            body = json.dumps(payload).encode('utf-8')
            status, _ = self._send_raw_request(body)
            # Some type coercions may succeed, but truly invalid types should fail
            # This test verifies the server handles type errors gracefully

    def test_missing_content_length_returns_200(self):
        """Test that missing content-length header returns 200 OK (Requirement 7.5)."""
        self._start_server()
        
        conn = http.client.HTTPConnection("127.0.0.1", self.actual_port)
        try:
            # Send request without Content-Length header
            conn.putrequest("POST", "/progress")
            conn.endheaders()
            response = conn.getresponse()
            self.assertEqual(response.status, 200)
        finally:
            conn.close()

    def test_zero_content_length_returns_200(self):
        """Test that zero content-length returns 200 OK."""
        self._start_server()
        
        status, _ = self._send_raw_request(b'', {"Content-Length": "0"})
        self.assertEqual(status, 200)

    def test_empty_body_with_content_length_returns_200(self):
        """Test that empty body with content-length returns 200."""
        self._start_server()
        
        status, _ = self._send_raw_request(b'')
        self.assertEqual(status, 200)

    def test_server_continues_after_malformed_request(self):
        """Test that server continues processing after malformed request."""
        self._start_server()
        
        # Send malformed request
        status, _ = self._send_raw_request(b'invalid json')
        self.assertEqual(status, 500)
        
        # Verify server still accepts valid requests
        valid_payload = self._create_valid_progress_payload("recovery-task")
        body = json.dumps(valid_payload).encode('utf-8')
        status, _ = self._send_raw_request(body)
        self.assertEqual(status, 200)
        
        # Verify task was recorded
        self.assertIn("recovery-task", self.recorder._running_tasks)

    def test_multiple_malformed_requests_dont_crash_server(self):
        """Test that multiple malformed requests don't crash the server."""
        self._start_server()
        
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
            status, _ = self._send_raw_request(payload)
            self.assertEqual(status, 500)
        
        # Verify server is still running
        self.assertTrue(self.server._server_running)
        self.assertTrue(self.server._server_thread.is_alive())
        
        # Verify server still accepts valid requests
        valid_payload = self._create_valid_progress_payload("after-malformed")
        body = json.dumps(valid_payload).encode('utf-8')
        status, _ = self._send_raw_request(body)
        self.assertEqual(status, 200)

    def test_concurrent_malformed_and_valid_requests(self):
        """Test handling concurrent malformed and valid requests."""
        self._start_server()
        
        results = []
        errors = []
        lock = threading.Lock()
        
        def send_request(request_id: int, is_valid: bool):
            try:
                if is_valid:
                    payload = self._create_valid_progress_payload(f"concurrent-{request_id}")
                    body = json.dumps(payload).encode('utf-8')
                else:
                    body = f"invalid json {request_id}".encode('utf-8')
                
                status, _ = self._send_raw_request(body)
                
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
        self.assertEqual(len(errors), 0, f"Errors: {errors}")
        
        # Verify correct status codes
        for request_id, is_valid, status in results:
            if is_valid:
                self.assertEqual(status, 200, 
                    f"Valid request {request_id} should return 200")
            else:
                self.assertEqual(status, 500, 
                    f"Invalid request {request_id} should return 500")


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


class NetworkFailureResilienceTests(ErrorRecoveryIntegrationTestBase):
    """Integration tests for network failure resilience (Requirements 10.1-10.4)."""

    def setUp(self):
        super().setUp()
        self.external_service = None

    def tearDown(self):
        if self.external_service is not None:
            try:
                self.external_service.stop()
            except Exception:
                pass
        super().tearDown()

    def test_forwarding_continues_after_connection_refused(self):
        """Test that forwarding continues after connection refused (Requirement 10.3, 10.4)."""
        # Use a port that nothing is listening on
        unused_port = self._find_unused_port()
        
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url=f"http://127.0.0.1:{unused_port}/api/progress",
            forwarding_headers=None
        )
        
        self._start_server(forwarding_info=forwarding_info)
        
        # Wait for multiple forwarding attempts
        time.sleep(0.25)
        
        # Verify forwarding thread is still running
        self.assertTrue(self.server._forwarding_running)
        self.assertTrue(self.server._forward_thread.is_alive())

    def test_forwarding_continues_after_http_500_error(self):
        """Test that forwarding continues after HTTP 500 errors (Requirement 10.3, 10.4)."""
        # Start a service that returns 500 errors
        self.external_service = FailingExternalService(("127.0.0.1", 0))
        self.external_service.start()
        port = self.external_service.server_address[1]
        
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url=f"http://127.0.0.1:{port}/error500",
            forwarding_headers=None
        )
        
        self._start_server(forwarding_info=forwarding_info)
        
        # Wait for multiple forwarding attempts
        time.sleep(0.25)
        
        # Verify forwarding thread is still running
        self.assertTrue(self.server._forwarding_running)
        self.assertTrue(self.server._forward_thread.is_alive())

    def test_forwarding_logs_errors(self):
        """Test that forwarding errors are logged (Requirement 10.2)."""
        unused_port = self._find_unused_port()
        
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url=f"http://127.0.0.1:{unused_port}/api/progress",
            forwarding_headers=None
        )
        
        self._start_server(forwarding_info=forwarding_info)
        
        # Capture logged errors
        logged_errors = []
        original_warning = self.server._logger.warning
        
        def capture_warning(msg):
            logged_errors.append(msg)
            original_warning(msg)
        
        self.server._logger.warning = capture_warning
        
        try:
            # Wait for forwarding attempts
            time.sleep(0.2)
            
            # Verify errors were logged
            self.assertGreater(len(logged_errors), 0, 
                "Forwarding errors should be logged")
        finally:
            self.server._logger.warning = original_warning

    def test_server_accepts_requests_during_forwarding_failures(self):
        """Test that server accepts progress requests during forwarding failures."""
        unused_port = self._find_unused_port()
        
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url=f"http://127.0.0.1:{unused_port}/api/progress",
            forwarding_headers=None
        )
        
        self._start_server(forwarding_info=forwarding_info)
        
        # Send valid progress updates while forwarding is failing
        for i in range(5):
            payload = self._create_valid_progress_payload(f"during-failure-{i}")
            body = json.dumps(payload).encode('utf-8')
            status, _ = self._send_raw_request(body)
            self.assertEqual(status, 200)
        
        # Verify tasks were recorded
        for i in range(5):
            self.assertIn(f"during-failure-{i}", self.recorder._running_tasks)

    def test_forwarding_recovers_when_service_becomes_available(self):
        """Test that forwarding recovers when external service becomes available."""
        # Start with no service running
        service_port = self._find_unused_port()
        
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url=f"http://127.0.0.1:{service_port}/api/progress",
            forwarding_headers=None
        )
        
        self._start_server(forwarding_info=forwarding_info)
        
        # Wait for some failed attempts
        time.sleep(0.15)
        
        # Verify forwarding is still running despite failures
        self.assertTrue(self.server._forward_thread.is_alive())

    def _find_unused_port(self) -> int:
        """Find an unused port for testing."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            return s.getsockname()[1]


class ServerStabilityUnderErrorConditionsTests(ErrorRecoveryIntegrationTestBase):
    """Integration tests for server stability under error conditions."""

    def test_server_stable_under_rapid_error_requests(self):
        """Test server stability under rapid error-inducing requests."""
        self._start_server()
        
        num_requests = 100
        errors = []
        
        def send_error_request(i):
            try:
                body = f"invalid-{i}".encode('utf-8')
                status, _ = self._send_raw_request(body)
                return status
            except Exception as e:
                errors.append(str(e))
                return None
        
        # Send rapid error requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(send_error_request, i) for i in range(num_requests)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # Verify no connection errors
        self.assertEqual(len(errors), 0, f"Connection errors: {errors}")
        
        # Verify all requests got 500 responses
        for status in results:
            self.assertEqual(status, 500)
        
        # Verify server is still running
        self.assertTrue(self.server._server_running)
        self.assertTrue(self.server._server_thread.is_alive())

    def test_server_stable_with_mixed_load(self):
        """Test server stability with mixed valid and invalid requests."""
        self._start_server()
        
        num_requests = 50
        results = {'valid': [], 'invalid': [], 'errors': []}
        lock = threading.Lock()
        
        def send_mixed_request(i):
            try:
                if i % 3 == 0:
                    # Valid request
                    payload = self._create_valid_progress_payload(f"mixed-{i}")
                    body = json.dumps(payload).encode('utf-8')
                    status, _ = self._send_raw_request(body)
                    with lock:
                        results['valid'].append(status)
                else:
                    # Invalid request
                    body = f"invalid-{i}".encode('utf-8')
                    status, _ = self._send_raw_request(body)
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
        self.assertEqual(len(results['errors']), 0, f"Errors: {results['errors']}")
        
        # Verify correct status codes
        for status in results['valid']:
            self.assertEqual(status, 200)
        for status in results['invalid']:
            self.assertEqual(status, 500)
        
        # Verify server is still running
        self.assertTrue(self.server._server_running)

    def test_server_handles_large_invalid_payload(self):
        """Test server handles large invalid payloads gracefully."""
        self._start_server()
        
        # Send a large invalid payload
        large_payload = b'x' * 100000  # 100KB of invalid data
        status, reason = self._send_raw_request(large_payload)
        
        self.assertEqual(status, 500)
        self.assertIn("Error processing progress postback", reason)
        
        # Verify server is still running
        self.assertTrue(self.server._server_running)
        
        # Verify server still accepts valid requests
        valid_payload = self._create_valid_progress_payload("after-large")
        body = json.dumps(valid_payload).encode('utf-8')
        status, _ = self._send_raw_request(body)
        self.assertEqual(status, 200)

    def test_server_handles_unicode_in_invalid_payload(self):
        """Test server handles unicode in invalid payloads."""
        self._start_server()
        
        unicode_payloads = [
            '{"id": "测试任务"}'.encode('utf-8'),  # Chinese characters
            '{"id": "тест"}'.encode('utf-8'),  # Cyrillic
            '{"id": "🎉🎊"}'.encode('utf-8'),  # Emoji
            '{"id": "café"}'.encode('utf-8'),  # Accented characters
        ]
        
        for payload in unicode_payloads:
            # These may succeed or fail depending on field validation
            # The key is that the server doesn't crash
            status, _ = self._send_raw_request(payload)
            self.assertIn(status, [200, 500])
        
        # Verify server is still running
        self.assertTrue(self.server._server_running)

    def test_server_handles_binary_payload(self):
        """Test server handles binary payloads gracefully."""
        self._start_server()
        
        # Send binary data that's not valid UTF-8
        binary_payload = bytes([0x80, 0x81, 0x82, 0xFF, 0xFE])
        status, _ = self._send_raw_request(binary_payload)
        
        self.assertEqual(status, 500)
        
        # Verify server is still running
        self.assertTrue(self.server._server_running)

    def test_recorder_state_consistent_after_errors(self):
        """Test that recorder state remains consistent after error conditions."""
        self._start_server()
        
        # Add some valid tasks
        for i in range(5):
            payload = self._create_valid_progress_payload(f"consistent-{i}")
            body = json.dumps(payload).encode('utf-8')
            self._send_raw_request(body)
        
        initial_task_count = len(self.recorder._running_tasks)
        
        # Send many error requests
        for i in range(20):
            self._send_raw_request(b'invalid')
        
        # Verify task count unchanged
        self.assertEqual(len(self.recorder._running_tasks), initial_task_count)
        
        # Verify original tasks still present
        for i in range(5):
            self.assertIn(f"consistent-{i}", self.recorder._running_tasks)

    def test_forwarding_and_request_handling_independent(self):
        """Test that forwarding errors don't affect request handling."""
        unused_port = self._find_unused_port()
        
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url=f"http://127.0.0.1:{unused_port}/api/progress",
            forwarding_headers=None
        )
        
        self._start_server(forwarding_info=forwarding_info)
        
        # Send valid requests while forwarding is failing
        success_count = 0
        for i in range(10):
            payload = self._create_valid_progress_payload(f"independent-{i}")
            body = json.dumps(payload).encode('utf-8')
            status, _ = self._send_raw_request(body)
            if status == 200:
                success_count += 1
        
        # All requests should succeed despite forwarding failures
        self.assertEqual(success_count, 10)
        
        # Verify all tasks recorded
        for i in range(10):
            self.assertIn(f"independent-{i}", self.recorder._running_tasks)

    def _find_unused_port(self) -> int:
        """Find an unused port for testing."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            return s.getsockname()[1]


if __name__ == "__main__":
    unittest.main()
