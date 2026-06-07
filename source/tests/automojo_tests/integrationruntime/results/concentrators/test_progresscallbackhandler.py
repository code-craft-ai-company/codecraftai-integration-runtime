"""
    .. module:: automojo_tests.testbase.results.concentrators.test_progresscallbackhandler
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Unit tests for ProgressCallbackHandler request processing.

    .. moduleauthor:: AutomationX
"""

import unittest
import tempfile
import os
import shutil
import json
import io
import http.client

from datetime import datetime
from http.server import BaseHTTPRequestHandler

from automojo.testbase.results.model.buildinfo import BuildInfo
from automojo.testbase.results.model.pipelineinfo import PipelineInfo
from automojo.testbase.results.model.jobinfo import JobInfo
from automojo.testbase.results.model.renderinfo import RenderInfo
from automojo.testbase.results.model.progressinfo import ProgressInfo
from automojo.testbase.results.model.progresscode import ProgressCode
from automojo.testbase.results.model.progresstype import ProgressType

from automojo.testbase.results.recorders.jsonresultrecorder import JsonResultRecorder
from automojo.integrationruntime.results.concentrators.progressconcentratorservice import (
    ProgressConcentratorServer,
    ProgressCallbackHandler
)


class MockRequest:
    """Mock request object for testing the handler."""
    
    def __init__(self, content: bytes = b''):
        self._content = content
        self._rfile = io.BytesIO(content)
    
    def makefile(self, mode, buffering=-1):
        if 'r' in mode:
            return io.BytesIO(self._content)
        return io.BytesIO()


class MockWfile:
    """Mock write file for capturing response output."""
    
    def __init__(self):
        self._buffer = io.BytesIO()
    
    def write(self, data):
        if isinstance(data, str):
            data = data.encode('utf-8')
        self._buffer.write(data)
    
    def flush(self):
        pass
    
    def get_value(self):
        return self._buffer.getvalue()


class ProgressCallbackHandlerTests(unittest.TestCase):
    """Tests for ProgressCallbackHandler (Requirements 5.1-5.6, 6.1-6.5, 7.1-7.5)."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        self.render_info = RenderInfo(
            title="Test Run",
            summary_filename=os.path.join(self.temp_dir, "summary.json"),
            summary_template=os.path.join(self.temp_dir, "template.html"),
            stream_results_filename=os.path.join(self.temp_dir, "results.json"),
            consolidated_results_filename=os.path.join(self.temp_dir, "consolidated.json"),
            static_resource_source=None,
            static_resource_destination=self.temp_dir
        )
        
        with open(self.render_info.summary_template, 'w') as f:
            f.write("<html></html>")
        
        self.runid = "test-run-uuid-123"
        self.start_time = datetime.now()
        
        self.build_info = BuildInfo(
            branch="main",
            build="build-123",
            flavor="release",
            release="1.0.0",
            url="https://ci.example.com/build/123"
        )
        
        self.pipeline_info = PipelineInfo(
            id="pipeline-uuid-456",
            name="CI Pipeline",
            instance="instance-uuid-789"
        )
        
        self.job_info = JobInfo(
            id="job-uuid-012",
            name="Integration Tests",
            type="TestRun",
            owner="QA Team",
            label="nightly",
            initiator="user@example.com",
            venue="staging",
            seed="12345",
            tag="correlation-tag"
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
        
        self.server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address
        )
        
        self.valid_progress_data = {
            "id": "task-uuid-123",
            "category": "test-execution",
            "moniker": "test_module.test_function",
            "ptype": "Sequential",
            "range_min": "0",
            "range_max": "10",
            "position": "5",
            "status": "Running",
            "when": "2025-02-20T10:30:00.000000",
            "data": {"worker_id": "worker-1"}
        }

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            self.server.server_close()
        except Exception:
            pass
        
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _create_handler_with_request(self, content: bytes, headers: dict = None):
        """Helper to create a handler with a mock request."""
        if headers is None:
            headers = {}
        
        # Build HTTP request string
        request_line = "POST /progress HTTP/1.1\r\n"
        header_lines = ""
        for key, value in headers.items():
            header_lines += f"{key}: {value}\r\n"
        header_lines += "\r\n"
        
        full_request = (request_line + header_lines).encode('utf-8') + content
        
        # Create mock socket-like objects
        rfile = io.BytesIO(full_request)
        wfile = MockWfile()
        
        # Create a mock client address
        client_address = ("127.0.0.1", 12345)
        
        # Create handler - we need to bypass the normal initialization
        handler = ProgressCallbackHandler.__new__(ProgressCallbackHandler)
        handler.server = self.server
        handler.client_address = client_address
        handler.rfile = io.BytesIO(content)
        handler.wfile = wfile
        handler.requestline = "POST /progress HTTP/1.1"
        handler.command = "POST"
        handler.path = "/progress"
        handler.request_version = "HTTP/1.1"
        handler.headers = http.client.HTTPMessage()
        
        for key, value in headers.items():
            handler.headers[key] = value
        
        return handler, wfile

    def test_handler_inherits_from_simple_http_request_handler(self):
        """Test that ProgressCallbackHandler inherits from SimpleHTTPRequestHandler (Requirement 5.1)."""
        from http.server import SimpleHTTPRequestHandler
        self.assertTrue(issubclass(ProgressCallbackHandler, SimpleHTTPRequestHandler))

    def test_handler_has_do_post_method(self):
        """Test that ProgressCallbackHandler implements do_POST method (Requirement 5.2)."""
        self.assertTrue(hasattr(ProgressCallbackHandler, 'do_POST'))
        self.assertTrue(callable(getattr(ProgressCallbackHandler, 'do_POST')))

    def test_do_post_with_valid_json_payload_returns_200(self):
        """Test that do_POST with valid JSON payload returns 200 OK (Requirements 5.3-5.6, 6.1)."""
        content = json.dumps(self.valid_progress_data).encode('utf-8')
        headers = {"content-length": str(len(content))}
        
        handler, wfile = self._create_handler_with_request(content, headers)
        
        handler.do_POST()
        
        response = wfile.get_value().decode('utf-8')
        self.assertIn("200", response)

    def test_do_post_with_valid_json_calls_update_task_progress(self):
        """Test that do_POST creates ProgressInfo and calls update_task_progress (Requirements 5.5, 5.6)."""
        content = json.dumps(self.valid_progress_data).encode('utf-8')
        headers = {"content-length": str(len(content))}
        
        handler, wfile = self._create_handler_with_request(content, headers)
        
        # Track if update_task_progress was called
        update_called = []
        original_update = self.server.update_task_progress
        
        def mock_update(progress):
            update_called.append(progress)
            original_update(progress)
        
        self.server.update_task_progress = mock_update
        
        handler.do_POST()
        
        self.assertEqual(len(update_called), 1)
        self.assertIsInstance(update_called[0], ProgressInfo)
        self.assertEqual(update_called[0].id, "task-uuid-123")

    def test_do_post_with_invalid_json_returns_500(self):
        """Test that do_POST with invalid JSON returns 500 error (Requirements 6.2, 7.1)."""
        content = b"not valid json {"
        headers = {"content-length": str(len(content))}
        
        handler, wfile = self._create_handler_with_request(content, headers)
        
        handler.do_POST()
        
        response = wfile.get_value().decode('utf-8')
        self.assertIn("500", response)

    def test_do_post_with_invalid_json_includes_error_message(self):
        """Test that 500 error includes error message (Requirements 6.3, 7.3, 7.4)."""
        content = b"not valid json {"
        headers = {"content-length": str(len(content))}
        
        handler, wfile = self._create_handler_with_request(content, headers)
        
        handler.do_POST()
        
        response = wfile.get_value().decode('utf-8')
        self.assertIn("Error processing progress postback", response)

    def test_do_post_with_missing_content_length_returns_200(self):
        """Test that do_POST with missing content-length header returns 200 OK (Requirement 7.5)."""
        handler, wfile = self._create_handler_with_request(b"", {})
        
        handler.do_POST()
        
        response = wfile.get_value().decode('utf-8')
        self.assertIn("200", response)

    def test_do_post_with_zero_content_length_returns_200(self):
        """Test that do_POST with zero content-length returns 200 OK."""
        headers = {"content-length": "0"}
        
        handler, wfile = self._create_handler_with_request(b"", headers)
        
        handler.do_POST()
        
        response = wfile.get_value().decode('utf-8')
        self.assertIn("200", response)

    def test_do_post_sets_content_type_header(self):
        """Test that do_POST sets Content-Type header to text/html (Requirement 6.4)."""
        content = json.dumps(self.valid_progress_data).encode('utf-8')
        headers = {"content-length": str(len(content))}
        
        handler, wfile = self._create_handler_with_request(content, headers)
        
        handler.do_POST()
        
        response = wfile.get_value().decode('utf-8')
        self.assertIn("Content-Type", response)
        self.assertIn("text/html", response)

    def test_do_post_with_malformed_progress_data_returns_500(self):
        """Test that do_POST with malformed progress data returns 500 (Requirement 7.2)."""
        # Missing required fields
        malformed_data = {"id": "task-123"}
        content = json.dumps(malformed_data).encode('utf-8')
        headers = {"content-length": str(len(content))}
        
        handler, wfile = self._create_handler_with_request(content, headers)
        
        handler.do_POST()
        
        response = wfile.get_value().decode('utf-8')
        self.assertIn("500", response)

    def test_do_post_error_message_includes_exception_marker(self):
        """Test that error message includes EXCEPTION: marker (Requirement 7.4)."""
        content = b"invalid json"
        headers = {"content-length": str(len(content))}
        
        handler, wfile = self._create_handler_with_request(content, headers)
        
        handler.do_POST()
        
        response = wfile.get_value().decode('utf-8')
        self.assertIn("EXCEPTION:", response)


class ProgressCallbackHandlerIntegrationTests(unittest.TestCase):
    """Integration tests for ProgressCallbackHandler with actual HTTP requests."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        self.render_info = RenderInfo(
            title="Test Run",
            summary_filename=os.path.join(self.temp_dir, "summary.json"),
            summary_template=os.path.join(self.temp_dir, "template.html"),
            stream_results_filename=os.path.join(self.temp_dir, "results.json"),
            consolidated_results_filename=os.path.join(self.temp_dir, "consolidated.json"),
            static_resource_source=None,
            static_resource_destination=self.temp_dir
        )
        
        with open(self.render_info.summary_template, 'w') as f:
            f.write("<html></html>")
        
        self.runid = "test-run-uuid-123"
        self.start_time = datetime.now()
        
        self.build_info = BuildInfo(
            branch="main",
            build="build-123",
            flavor="release",
            release="1.0.0",
            url="https://ci.example.com/build/123"
        )
        
        self.pipeline_info = PipelineInfo(
            id="pipeline-uuid-456",
            name="CI Pipeline",
            instance="instance-uuid-789"
        )
        
        self.job_info = JobInfo(
            id="job-uuid-012",
            name="Integration Tests",
            type="TestRun",
            owner="QA Team",
            label="nightly",
            initiator="user@example.com",
            venue="staging",
            seed="12345",
            tag="correlation-tag"
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
        
        self.server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address
        )
        self.server.start()
        
        self.actual_port = self.server.server_address[1]
        
        self.valid_progress_data = {
            "id": "task-uuid-456",
            "category": "test-execution",
            "moniker": "test_module.test_function",
            "ptype": "Sequential",
            "range_min": "0",
            "range_max": "10",
            "position": "5",
            "status": "Running",
            "when": "2025-02-20T10:30:00.000000",
            "data": {"worker_id": "worker-1"}
        }

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            self.server.shutdown()
            self.server.server_close()
        except Exception:
            pass
        
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_http_post_with_valid_json_returns_200(self):
        """Test actual HTTP POST with valid JSON returns 200."""
        import urllib.request
        
        content = json.dumps(self.valid_progress_data).encode('utf-8')
        
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.actual_port}/progress",
            data=content,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        response = urllib.request.urlopen(req)
        
        self.assertEqual(response.status, 200)

    def test_http_post_with_invalid_json_returns_500(self):
        """Test actual HTTP POST with invalid JSON returns 500."""
        import urllib.request
        import urllib.error
        
        content = b"not valid json"
        
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.actual_port}/progress",
            data=content,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(req)
        
        self.assertEqual(context.exception.code, 500)

    def test_http_post_updates_recorder_running_tasks(self):
        """Test that HTTP POST updates the recorder's running tasks."""
        import urllib.request
        
        content = json.dumps(self.valid_progress_data).encode('utf-8')
        
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.actual_port}/progress",
            data=content,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        urllib.request.urlopen(req)
        
        # Check that the task was added to running_tasks
        summary = self.recorder.summary
        self.assertIn("running", summary)


if __name__ == "__main__":
    unittest.main()
