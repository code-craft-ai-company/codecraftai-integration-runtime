"""
    .. module:: ccai_tests.testbase.results.concentrators.test_progressconcentratorserver_startup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Unit tests for ProgressConcentratorServer startup.

    .. moduleauthor:: CodeCraftX
"""

import unittest
import tempfile
import os
import shutil
import threading
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


class ProgressConcentratorServerStartupTests(unittest.TestCase):
    """Tests for ProgressConcentratorServer startup (Requirements 2.1-2.7)."""

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
        
        # Create a dummy template file
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
        
        self.server_address = ("127.0.0.1", 0)  # Port 0 lets OS assign available port
        
        self.forwarding_info = ForwardingInfo(
            forwarding_interval=5.0,
            forwarding_url="https://monitoring.example.com/api/progress",
            forwarding_headers={"Authorization": "Bearer token123"}
        )
        
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

    def test_start_method_exists(self):
        """Test that ProgressConcentratorServer provides a start method (Requirement 2.1)."""
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address,
            bind_and_activate=False
        )
        
        self.assertTrue(hasattr(server, 'start'))
        self.assertTrue(callable(server.start))
        
        server.server_close()

    def test_start_creates_server_thread(self):
        """Test that start method creates a server thread (Requirement 2.2)."""
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address
        )
        self.servers_to_cleanup.append(server)
        
        server.start()
        
        self.assertIsNotNone(server._server_thread)
        self.assertIsInstance(server._server_thread, threading.Thread)

    def test_server_thread_is_daemon(self):
        """Test that server thread is created as a daemon thread (Requirement 2.2)."""
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address
        )
        self.servers_to_cleanup.append(server)
        
        server.start()
        
        self.assertTrue(server._server_thread.daemon)

    def test_server_thread_is_named_prog_concentrator(self):
        """Test that server thread is named 'prog-concentrator' (Requirement 3.3)."""
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address
        )
        self.servers_to_cleanup.append(server)
        
        server.start()
        
        self.assertEqual(server._server_thread.name, 'prog-concentrator')

    def test_server_thread_is_alive_after_start(self):
        """Test that server thread is running after start returns (Requirement 2.3, 2.4)."""
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address
        )
        self.servers_to_cleanup.append(server)
        
        server.start()
        
        self.assertTrue(server._server_thread.is_alive())

    def test_server_running_flag_is_true_after_start(self):
        """Test that server_running flag is True after start (Requirement 3.6)."""
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address
        )
        self.servers_to_cleanup.append(server)
        
        server.start()
        
        self.assertTrue(server._server_running)


    def test_start_returns_after_gate_synchronization(self):
        """Test that start method uses gate Event for synchronization (Requirement 2.3, 2.4)."""
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address
        )
        self.servers_to_cleanup.append(server)
        
        # Record time before start
        start_time = time.time()
        
        server.start()
        
        # Record time after start returns
        end_time = time.time()
        
        # The start method should return quickly after the gate is set
        # If gate synchronization wasn't working, the method might hang or return prematurely
        elapsed = end_time - start_time
        
        # Start should complete within a reasonable time (not hang indefinitely)
        self.assertLess(elapsed, 5.0)
        
        # Server thread should be alive, confirming gate was set
        self.assertTrue(server._server_thread.is_alive())

    def test_start_creates_forwarding_thread_when_forwarding_info_provided(self):
        """Test that forwarding thread is created when forwarding_info is provided (Requirement 2.5)."""
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address,
            forwarding_info=self.forwarding_info
        )
        self.servers_to_cleanup.append(server)
        
        server.start()
        
        self.assertIsNotNone(server._forward_thread)
        self.assertIsInstance(server._forward_thread, threading.Thread)

    def test_forwarding_thread_is_daemon(self):
        """Test that forwarding thread is created as a daemon thread (Requirement 3.2)."""
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address,
            forwarding_info=self.forwarding_info
        )
        self.servers_to_cleanup.append(server)
        
        server.start()
        
        self.assertTrue(server._forward_thread.daemon)

    def test_forwarding_thread_is_named_prog_forwarder(self):
        """Test that forwarding thread is named 'prog-forwarder' (Requirement 3.4)."""
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address,
            forwarding_info=self.forwarding_info
        )
        self.servers_to_cleanup.append(server)
        
        server.start()
        
        self.assertEqual(server._forward_thread.name, 'prog-forwarder')

    def test_forwarding_thread_is_alive_after_start(self):
        """Test that forwarding thread is running after start returns (Requirement 2.6)."""
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address,
            forwarding_info=self.forwarding_info
        )
        self.servers_to_cleanup.append(server)
        
        server.start()
        
        self.assertTrue(server._forward_thread.is_alive())

    def test_no_forwarding_thread_when_forwarding_info_is_none(self):
        """Test that no forwarding thread is created when forwarding_info is None (Requirement 2.5)."""
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address,
            forwarding_info=None
        )
        self.servers_to_cleanup.append(server)
        
        server.start()
        
        self.assertIsNone(server._forward_thread)

    def test_start_waits_for_both_threads_when_forwarding_enabled(self):
        """Test that start method waits for both threads when forwarding_info is provided (Requirement 2.7)."""
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address,
            forwarding_info=self.forwarding_info
        )
        self.servers_to_cleanup.append(server)
        
        server.start()
        
        # Both threads should be alive after start returns
        self.assertTrue(server._server_thread.is_alive())
        self.assertTrue(server._forward_thread.is_alive())
        
        # Both threads should have been started
        self.assertIsNotNone(server._server_thread)
        self.assertIsNotNone(server._forward_thread)


if __name__ == "__main__":
    unittest.main()
