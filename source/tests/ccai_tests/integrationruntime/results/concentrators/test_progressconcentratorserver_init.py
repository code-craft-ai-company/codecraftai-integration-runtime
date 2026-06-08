"""
    .. module:: ccai_tests.testbase.results.concentrators.test_progressconcentratorserver_init
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Unit tests for ProgressConcentratorServer initialization.

    .. moduleauthor:: CodeCraftX
"""

import unittest
import tempfile
import os
import shutil

from datetime import datetime
from http.server import HTTPServer
from socketserver import ThreadingMixIn

from ccai.testbase.results.model.buildinfo import BuildInfo
from ccai.testbase.results.model.pipelineinfo import PipelineInfo
from ccai.testbase.results.model.jobinfo import JobInfo
from ccai.testbase.results.model.renderinfo import RenderInfo
from ccai.testbase.results.model.forwardinginfo import ForwardingInfo

from ccai.testbase.results.recorders.jsonresultrecorder import JsonResultRecorder
from ccai.integrationruntime.results.concentrators.progressconcentratorservice import (
    ProgressConcentratorServer
)


class ProgressConcentratorServerInitializationTests(unittest.TestCase):
    """Tests for ProgressConcentratorServer initialization (Requirements 1.1-1.7)."""

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
        self.start = datetime.now()
        
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
            start=self.start,
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

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_constructor_accepts_recorder_parameter(self):
        """Test that constructor accepts recorder parameter of type ResultRecorder (Requirement 1.1)."""
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address,
            bind_and_activate=False
        )
        
        self.assertIsNotNone(server._recorder)
        self.assertIs(server._recorder, self.recorder)
        
        server.server_close()

    def test_constructor_accepts_server_address_parameter(self):
        """Test that constructor accepts server_address parameter as tuple of (host, port) (Requirement 1.2)."""
        test_address = ("127.0.0.1", 0)
        
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=test_address,
            bind_and_activate=False
        )
        
        # The server_address attribute is set by HTTPServer
        self.assertIsNotNone(server.server_address)
        
        server.server_close()

    def test_constructor_accepts_optional_forwarding_info_parameter(self):
        """Test that constructor accepts optional forwarding_info parameter of type ForwardingInfo (Requirement 1.3)."""
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address,
            forwarding_info=self.forwarding_info,
            bind_and_activate=False
        )
        
        self.assertIsNotNone(server._forwarding_info)
        self.assertIs(server._forwarding_info, self.forwarding_info)
        
        server.server_close()

    def test_constructor_accepts_none_forwarding_info(self):
        """Test that constructor accepts None for forwarding_info parameter (Requirement 1.3)."""
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address,
            forwarding_info=None,
            bind_and_activate=False
        )
        
        self.assertIsNone(server._forwarding_info)
        
        server.server_close()

    def test_constructor_bind_and_activate_defaults_to_true(self):
        """Test that bind_and_activate parameter defaults to True (Requirement 1.4)."""
        # Create server with bind_and_activate=True (default)
        # Using port 0 to let OS assign an available port
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=("127.0.0.1", 0)
        )
        
        # When bind_and_activate is True, the server should be bound to an address
        # The server_address will be updated with the actual port assigned
        self.assertIsNotNone(server.server_address)
        self.assertNotEqual(server.server_address[1], 0)  # Port should be assigned
        
        server.server_close()

    def test_constructor_bind_and_activate_false_does_not_bind(self):
        """Test that bind_and_activate=False does not bind immediately (Requirement 1.4)."""
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=("127.0.0.1", 0),
            bind_and_activate=False
        )
        
        # When bind_and_activate is False, the socket should not be bound yet
        # The server_address will still be the original tuple
        self.assertEqual(server.server_address, ("127.0.0.1", 0))
        
        server.server_close()

    def test_class_inherits_from_threading_mixin(self):
        """Test that ProgressConcentratorServer inherits from ThreadingMixIn (Requirement 1.5)."""
        self.assertTrue(issubclass(ProgressConcentratorServer, ThreadingMixIn))

    def test_class_inherits_from_http_server(self):
        """Test that ProgressConcentratorServer inherits from HTTPServer (Requirement 1.5)."""
        self.assertTrue(issubclass(ProgressConcentratorServer, HTTPServer))

    def test_constructor_stores_recorder_reference(self):
        """Test that server stores recorder reference for progress aggregation (Requirement 1.6)."""
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address,
            bind_and_activate=False
        )
        
        # Verify the recorder reference is stored and accessible
        self.assertIs(server._recorder, self.recorder)
        
        server.server_close()

    def test_constructor_initializes_server_running_to_false(self):
        """Test that server_running flag is initialized to False (Requirement 1.7)."""
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address,
            bind_and_activate=False
        )
        
        self.assertFalse(server._server_running)
        
        server.server_close()

    def test_constructor_initializes_forwarding_running_to_false(self):
        """Test that forwarding_running flag is initialized to False (Requirement 1.7)."""
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address,
            forwarding_info=self.forwarding_info,
            bind_and_activate=False
        )
        
        self.assertFalse(server._forwarding_running)
        
        server.server_close()

    def test_constructor_initializes_logger(self):
        """Test that constructor initializes an EnhancedLogger instance (Requirement 15.1)."""
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address,
            bind_and_activate=False
        )
        
        self.assertIsNotNone(server._logger)
        
        server.server_close()

    def test_constructor_initializes_thread_references_to_none(self):
        """Test that constructor initializes thread references to None."""
        server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.server_address,
            bind_and_activate=False
        )
        
        self.assertIsNone(server._server_thread)
        self.assertIsNone(server._forward_thread)
        
        server.server_close()


if __name__ == "__main__":
    unittest.main()
