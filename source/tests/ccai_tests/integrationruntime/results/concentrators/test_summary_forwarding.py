"""
    .. module:: ccai_tests.testbase.results.concentrators.test_summary_forwarding
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Unit tests for ProgressConcentratorServer summary forwarding.

    .. moduleauthor:: CodeCraftX
"""

import unittest
import tempfile
import os
import shutil
import threading
import time
import json
import requests # Added import

from datetime import datetime

from ccai.testbase.results.model.buildinfo import BuildInfo
from ccai.testbase.results.model.pipelineinfo import PipelineInfo
from ccai.testbase.results.model.jobinfo import JobInfo
from ccai.testbase.results.model.renderinfo import RenderInfo
from ccai.testbase.results.model.forwardinginfo import ForwardingInfo

from ccai.testbase.results.recorders.jsonresultrecorder import JsonResultRecorder
from ccai.integrationruntime.results.concentrators.progressconcentratorservice import (
    ProgressConcentratorServer
)

from ccai.testbase.mocking import Mock, create_module_patch

import ccai.integrationruntime.results.concentrators.progressconcentratorservice as pcs_module


class SummaryForwardingLoopTests(unittest.TestCase):
    """Tests for summary forwarding loop execution (Requirements 9.1-9.4)."""

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
        
        self.servers_to_cleanup = []

    def tearDown(self):
        """Clean up test fixtures."""
        for server in self.servers_to_cleanup:
            try:
                server._forwarding_running = False
                server.shutdown()
                server.server_close()
                if hasattr(server, '_forward_thread') and server._forward_thread is not None:
                    try:
                        server._forward_thread.join(timeout=2.0)
                    except Exception:
                        # Best-effort teardown; the forwarding thread is a daemon, so a failed join must not block the remaining cleanup.
                        pass
            except Exception:
                # Best-effort teardown; a server that never started or is already closed must not block the remaining cleanup.
                pass
        
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_forwarding_running_flag_is_true_during_loop(self):
        """Test that forwarding_running is True while loop is running (Requirement 9.1)."""
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.1,
            forwarding_url="https://monitoring.example.com/api/progress",
            forwarding_headers=None
        )
        
        with create_module_patch(pcs_module.requests, "post", recursive=True) as mock_post:
            mock_response = Mock()
            mock_response.configure(return_value=mock_response)
            mock_post.configure(return_value=mock_response)
            
            server = ProgressConcentratorServer(
                recorder=self.recorder,
                server_address=self.server_address,
                forwarding_info=forwarding_info
            )
            self.servers_to_cleanup.append(server)
            
            server.start()
            
            self.assertTrue(server._forwarding_running)

    def test_forwarding_retrieves_summary_from_recorder(self):
        """Test that forwarding loop retrieves summary from recorder (Requirement 9.2)."""
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url="https://monitoring.example.com/api/progress",
            forwarding_headers=None
        )
        
        posted_summaries = []
        
        def capture_post(url, data=None, headers=None, timeout=None):
            if data is not None:
                posted_summaries.append(json.loads(data))
            mock_response = Mock()
            return mock_response
        
        with create_module_patch(pcs_module.requests, "post", recursive=True) as mock_post:
            mock_post.configure(side_effect=capture_post)
            
            server = ProgressConcentratorServer(
                recorder=self.recorder,
                server_address=self.server_address,
                forwarding_info=forwarding_info
            )
            self.servers_to_cleanup.append(server)
            
            server.start()
            
            time.sleep(0.15)
            
            self.assertGreater(len(posted_summaries), 0)
            
            summary = posted_summaries[0]
            self.assertIn("version", summary)
            self.assertIn("runid", summary)
            self.assertEqual(summary["runid"], self.runid)

    def test_forwarding_posts_to_forwarding_url(self):
        """Test that forwarding loop POSTs to forwarding_url (Requirement 9.3)."""
        expected_url = "https://monitoring.example.com/api/progress"
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url=expected_url,
            forwarding_headers=None
        )
        
        posted_urls = []
        
        def capture_post(url, data=None, headers=None, timeout=None):
            posted_urls.append(url)
            mock_response = Mock()
            return mock_response
        
        with create_module_patch(pcs_module.requests, "post", recursive=True) as mock_post:
            mock_post.configure(side_effect=capture_post)
            
            server = ProgressConcentratorServer(
                recorder=self.recorder,
                server_address=self.server_address,
                forwarding_info=forwarding_info
            )
            self.servers_to_cleanup.append(server)
            
            server.start()
            
            time.sleep(0.15)
            
            self.assertGreater(len(posted_urls), 0)
            self.assertEqual(posted_urls[0], expected_url)

    def test_forwarding_sleeps_for_interval(self):
        """Test that forwarding loop sleeps for forwarding_interval seconds (Requirement 9.4)."""
        forwarding_interval = 0.1
        forwarding_info = ForwardingInfo(
            forwarding_interval=forwarding_interval,
            forwarding_url="https://monitoring.example.com/api/progress",
            forwarding_headers=None
        )
        
        post_times = []
        
        def capture_post(url, data=None, headers=None, timeout=None):
            post_times.append(time.time())
            mock_response = Mock()
            return mock_response
        
        with create_module_patch(pcs_module.requests, "post", recursive=True) as mock_post:
            mock_post.configure(side_effect=capture_post)
            
            server = ProgressConcentratorServer(
                recorder=self.recorder,
                server_address=self.server_address,
                forwarding_info=forwarding_info
            )
            self.servers_to_cleanup.append(server)
            
            server.start()
            
            time.sleep(0.35)
            
            self.assertGreaterEqual(len(post_times), 2)
            
            if len(post_times) >= 2:
                interval = post_times[1] - post_times[0]
                self.assertGreaterEqual(interval, forwarding_interval * 0.8)


class SummaryForwardingHeaderTests(unittest.TestCase):
    """Tests for summary forwarding header handling (Requirements 9.5-9.6)."""

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
        
        self.servers_to_cleanup = []

    def tearDown(self):
        """Clean up test fixtures."""
        for server in self.servers_to_cleanup:
            try:
                server._forwarding_running = False
                server.shutdown()
                server.server_close()
                if hasattr(server, '_forward_thread') and server._forward_thread is not None:
                    try:
                        server._forward_thread.join(timeout=2.0)
                    except Exception:
                        # Best-effort teardown; the forwarding thread is a daemon, so a failed join must not block the remaining cleanup.
                        pass
            except Exception:
                # Best-effort teardown; a server that never started or is already closed must not block the remaining cleanup.
                pass
        
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_forwarding_includes_content_type_json_header(self):
        """Test that forwarding includes Content-Type: application/json header (Requirement 9.5)."""
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url="https://monitoring.example.com/api/progress",
            forwarding_headers=None
        )
        
        captured_headers = []
        
        def capture_post(url, data=None, headers=None, timeout=None):
            if headers is not None:
                captured_headers.append(headers.copy())
            mock_response = Mock()
            return mock_response
        
        with create_module_patch(pcs_module.requests, "post", recursive=True) as mock_post:
            mock_post.configure(side_effect=capture_post)
            
            server = ProgressConcentratorServer(
                recorder=self.recorder,
                server_address=self.server_address,
                forwarding_info=forwarding_info
            )
            self.servers_to_cleanup.append(server)
            
            server.start()
            
            time.sleep(0.15)
            
            self.assertGreater(len(captured_headers), 0)
            
            headers = captured_headers[0]
            self.assertIn("Content-Type", headers)
            self.assertEqual(headers["Content-Type"], "application/json")

    def test_forwarding_merges_custom_headers(self):
        """Test that forwarding merges forwarding_headers with default headers (Requirement 9.6)."""
        custom_headers = {
            "Authorization": "Bearer token123",
            "X-Job-Id": "job-456"
        }
        
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url="https://monitoring.example.com/api/progress",
            forwarding_headers=custom_headers
        )
        
        captured_headers = []
        
        def capture_post(url, data=None, headers=None, timeout=None):
            if headers is not None:
                captured_headers.append(headers.copy())
            mock_response = Mock()
            return mock_response
        
        with create_module_patch(pcs_module.requests, "post", recursive=True) as mock_post:
            mock_post.configure(side_effect=capture_post)
            
            server = ProgressConcentratorServer(
                recorder=self.recorder,
                server_address=self.server_address,
                forwarding_info=forwarding_info
            )
            self.servers_to_cleanup.append(server)
            
            server.start()
            
            time.sleep(0.15)
            
            self.assertGreater(len(captured_headers), 0)
            
            headers = captured_headers[0]
            self.assertIn("Content-Type", headers)
            self.assertEqual(headers["Content-Type"], "application/json")
            self.assertIn("Authorization", headers)
            self.assertEqual(headers["Authorization"], "Bearer token123")
            self.assertIn("X-Job-Id", headers)
            self.assertEqual(headers["X-Job-Id"], "job-456")

    def test_forwarding_uses_only_default_header_when_forwarding_headers_is_none(self):
        """Test that only default Content-Type header is used when forwarding_headers is None (Requirement 8.4)."""
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url="https://monitoring.example.com/api/progress",
            forwarding_headers=None
        )
        
        captured_headers = []
        
        def capture_post(url, data=None, headers=None, timeout=None):
            if headers is not None:
                captured_headers.append(headers.copy())
            mock_response = Mock()
            return mock_response
        
        with create_module_patch(pcs_module.requests, "post", recursive=True) as mock_post:
            mock_post.configure(side_effect=capture_post)
            
            server = ProgressConcentratorServer(
                recorder=self.recorder,
                server_address=self.server_address,
                forwarding_info=forwarding_info
            )
            self.servers_to_cleanup.append(server)
            
            server.start()
            
            time.sleep(0.15)
            
            self.assertGreater(len(captured_headers), 0)
            
            headers = captured_headers[0]
            self.assertEqual(len(headers), 1)
            self.assertIn("Content-Type", headers)


class SummaryForwardingErrorHandlingTests(unittest.TestCase):
    """Tests for summary forwarding error handling (Requirements 10.1-10.4)."""

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
        
        self.servers_to_cleanup = []

    def tearDown(self):
        """Clean up test fixtures."""
        for server in self.servers_to_cleanup:
            try:
                server._forwarding_running = False
                server.shutdown()
                server.server_close()
                if hasattr(server, '_forward_thread') and server._forward_thread is not None:
                    try:
                        server._forward_thread.join(timeout=2.0)
                    except Exception:
                        # Best-effort teardown; the forwarding thread is a daemon, so a failed join must not block the remaining cleanup.
                        pass
            except Exception:
                # Best-effort teardown; a server that never started or is already closed must not block the remaining cleanup.
                pass
        
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_forwarding_catches_exceptions(self):
        """Test that forwarding catches exceptions from requests (Requirement 10.1)."""
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url="https://monitoring.example.com/api/progress",
            forwarding_headers=None
        )
        
        exception_raised = threading.Event()
        
        def raise_exception(url, data=None, headers=None, timeout=None):
            exception_raised.set()
            raise requests.exceptions.ConnectionError("Network error")
        
        with create_module_patch(pcs_module.requests, "post", recursive=True) as mock_post:
            mock_post.configure(side_effect=raise_exception)
            
            server = ProgressConcentratorServer(
                recorder=self.recorder,
                server_address=self.server_address,
                forwarding_info=forwarding_info
            )
            self.servers_to_cleanup.append(server)
            
            server.start()
            
            exception_raised.wait(timeout=0.5)
            
            self.assertTrue(exception_raised.is_set())
            self.assertTrue(server._forward_thread.is_alive())

    def test_forwarding_logs_errors(self):
        """Test that forwarding logs errors using the logger (Requirement 10.2)."""
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url="https://monitoring.example.com/api/progress",
            forwarding_headers=None
        )
        
        logged_errors = []
        
        def capture_error(msg):
            logged_errors.append(msg)
        
        def raise_exception(url, data=None, headers=None, timeout=None):
            raise requests.exceptions.ConnectionError("Network error")
        
        with create_module_patch(pcs_module.requests, "post", recursive=True) as mock_post:
            mock_post.configure(side_effect=raise_exception)
            
            server = ProgressConcentratorServer(
                recorder=self.recorder,
                server_address=self.server_address,
                forwarding_info=forwarding_info
            )
            self.servers_to_cleanup.append(server)
            
            original_warning = server._logger.warning
            server._logger.warning = capture_error
            
            try:
                server.start()
                
                time.sleep(0.15)
                
                self.assertGreater(len(logged_errors), 0)
                
                self.assertTrue(any("Connection error" in err for err in logged_errors))
            finally:
                server._logger.warning = original_warning

    def test_forwarding_continues_after_exception(self):
        """Test that forwarding loop continues after catching exception (Requirement 10.3)."""
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url="https://monitoring.example.com/api/progress",
            forwarding_headers=None
        )
        
        call_count = [0]
        
        def count_calls(url, data=None, headers=None, timeout=None):
            call_count[0] += 1
            if call_count[0] <= 2:
                raise requests.exceptions.ConnectionError("Network error")
            mock_response = Mock()
            return mock_response
        
        with create_module_patch(pcs_module.requests, "post", recursive=True) as mock_post:
            mock_post.configure(side_effect=count_calls)
            
            server = ProgressConcentratorServer(
                recorder=self.recorder,
                server_address=self.server_address,
                forwarding_info=forwarding_info
            )
            self.servers_to_cleanup.append(server)
            
            server.start()
            
            time.sleep(0.3)
            
            self.assertGreater(call_count[0], 2)

    def test_forwarding_thread_does_not_terminate_on_network_error(self):
        """Test that forwarding thread does not terminate due to network errors (Requirement 10.4)."""
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url="https://monitoring.example.com/api/progress",
            forwarding_headers=None
        )
        
        def raise_exception(url, data=None, headers=None, timeout=None):
            raise requests.exceptions.ConnectionError("Network error")
        
        with create_module_patch(pcs_module.requests, "post", recursive=True) as mock_post:
            mock_post.configure(side_effect=raise_exception)
            
            server = ProgressConcentratorServer(
                recorder=self.recorder,
                server_address=self.server_address,
                forwarding_info=forwarding_info
            )
            self.servers_to_cleanup.append(server)
            
            server.start()
            
            time.sleep(0.2)
            
            self.assertTrue(server._forward_thread.is_alive())
            self.assertTrue(server._forwarding_running)


if __name__ == "__main__":
    unittest.main()
