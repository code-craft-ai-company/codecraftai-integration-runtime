"""
    .. module:: ccai_tests.testbase.results.concentrators.test_progressconcentratorserver_shutdown
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Unit tests for ProgressConcentratorServer shutdown.

    .. moduleauthor:: CodeCraftX
"""

import unittest
import tempfile
import os
import shutil
import time

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

from ccai.testbase.mocking import create_module_patch

import ccai.integrationruntime.results.concentrators.progressconcentratorservice as pcs_module


class ProgressConcentratorServerShutdownTests(unittest.TestCase):
    """Tests for ProgressConcentratorServer shutdown (Requirements 38.1-38.5)."""

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

    def test_shutdown_method_exists(self):
        """Test that ProgressConcentratorServer has shutdown method from HTTPServer."""
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address,
            bind_and_activate=False
        )
        
        self.assertTrue(hasattr(server, 'shutdown'))
        self.assertTrue(callable(server.shutdown))
        
        server.server_close()

    def test_server_close_method_exists(self):
        """Test that ProgressConcentratorServer has server_close method from HTTPServer."""
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address,
            bind_and_activate=False
        )
        
        self.assertTrue(hasattr(server, 'server_close'))
        self.assertTrue(callable(server.server_close))
        
        server.server_close()

    def test_shutdown_stops_server_thread(self):
        """Test that shutdown stops the server thread."""
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address
        )
        
        server.start()
        
        self.assertTrue(server._server_thread.is_alive())
        
        server.shutdown()
        
        server._server_thread.join(timeout=2.0)
        
        self.assertFalse(server._server_thread.is_alive())
        
        server.server_close()

    def test_shutdown_allows_server_close(self):
        """Test that shutdown followed by server_close completes without error."""
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address
        )
        
        server.start()
        
        server.shutdown()
        server.server_close()

    def test_forwarding_thread_stops_when_flag_cleared(self):
        """Test that forwarding thread stops when _forwarding_running is set to False."""
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url="https://monitoring.example.com/api/progress",
            forwarding_headers=None
        )
        
        with create_module_patch(pcs_module.requests, "post", recursive=True) as mock_post:
            mock_post.configure(return_value=None)
            
            server = ProgressConcentratorServer(
                recorder=self.recorder,
                server_address=self.server_address,
                forwarding_info=forwarding_info
            )
            
            server.start()
            
            self.assertTrue(server._forward_thread.is_alive())
            self.assertTrue(server._forwarding_running)
            
            server._forwarding_running = False
            
            server._forward_thread.join(timeout=2.0)
            
            self.assertFalse(server._forward_thread.is_alive())
            
            server.shutdown()
            server.server_close()

    def test_full_shutdown_sequence(self):
        """Test complete shutdown sequence with both server and forwarding threads."""
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url="https://monitoring.example.com/api/progress",
            forwarding_headers=None
        )
        
        with create_module_patch(pcs_module.requests, "post", recursive=True) as mock_post:
            mock_post.configure(return_value=None)
            
            server = ProgressConcentratorServer(
                recorder=self.recorder,
                server_address=self.server_address,
                forwarding_info=forwarding_info
            )
            
            server.start()
            
            self.assertTrue(server._server_thread.is_alive())
            self.assertTrue(server._forward_thread.is_alive())
            
            server._forwarding_running = False
            server.shutdown()
            
            server._server_thread.join(timeout=2.0)
            server._forward_thread.join(timeout=2.0)
            
            self.assertFalse(server._server_thread.is_alive())
            self.assertFalse(server._forward_thread.is_alive())
            
            server.server_close()

    def test_server_accepts_no_connections_after_shutdown(self):
        """Test that server does not accept connections after shutdown."""
        import urllib.request
        import urllib.error
        
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address
        )
        
        server.start()
        actual_port = server.server_address[1]
        
        server.shutdown()
        server.server_close()
        
        time.sleep(0.1)
        
        with self.assertRaises((urllib.error.URLError, ConnectionRefusedError, OSError)):
            req = urllib.request.Request(
                f"http://127.0.0.1:{actual_port}/progress",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            urllib.request.urlopen(req, timeout=1.0)


if __name__ == "__main__":
    unittest.main()
