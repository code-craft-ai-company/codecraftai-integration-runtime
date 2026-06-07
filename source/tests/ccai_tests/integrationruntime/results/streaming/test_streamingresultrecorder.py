"""
    .. module:: ccai_tests.testbase.results.streaming.test_streamingresultrecorder
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Integration tests for StreamingResultRecorder.

    This module contains integration tests for the StreamingResultRecorder class
    that combines local file recording with real-time streaming to external services.

    Requirements: 28.1-28.6

    .. moduleauthor:: CodeCraftX
"""

import unittest
import tempfile
import os
import shutil
import threading
import time
import json
import uuid

from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

from ccai.testbase.results.model.buildinfo import BuildInfo
from ccai.testbase.results.model.pipelineinfo import PipelineInfo
from ccai.testbase.results.model.jobinfo import JobInfo
from ccai.testbase.results.model.renderinfo import RenderInfo
from ccai.testbase.results.model.streaminginfo import (
    StreamingInfo,
    StreamingProtocol,
    StreamingCallback
)
from ccai.testbase.results.model.resultcode import ResultCode
from ccai.testbase.results.model.testresult import TestResult

from ccai.integrationruntime.results.recorders.streamingresultrecorder import StreamingResultRecorder


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
    """Mock streaming service for testing."""

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


class StreamingResultRecorderTestBase(unittest.TestCase):
    """Base class for StreamingResultRecorder tests."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create render info
        self.render_info = RenderInfo(
            title="Streaming Test Run",
            summary_filename=os.path.join(self.temp_dir, "summary.json"),
            summary_template=os.path.join(self.temp_dir, "template.html"),
            stream_results_filename=os.path.join(self.temp_dir, "results.jsos"),
            consolidated_results_filename=os.path.join(self.temp_dir, "consolidated.json"),
            static_resource_source=None,
            static_resource_destination=self.temp_dir
        )
        
        # Create template file
        with open(self.render_info.summary_template, 'w') as f:
            f.write("<html></html>")
        
        self.runid = str(uuid.uuid4())
        self.start_time = datetime.now()
        
        self.build_info = BuildInfo(
            branch="main",
            build="build-streaming-test",
            flavor="release",
            release="1.0.0",
            url="https://ci.example.com/build/streaming"
        )
        
        self.pipeline_info = PipelineInfo(
            id="pipeline-streaming",
            name="Streaming Pipeline",
            instance="instance-streaming"
        )
        
        self.job_info = JobInfo(
            id="job-streaming",
            name="Streaming Tests",
            type="IntegrationTest",
            owner="QA Team",
            label="streaming",
            initiator="test@example.com",
            venue="test",
            seed="streaming-seed",
            tag="streaming-tag"
        )
        
        # Start mock streaming service
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
        
        self.recorder = None

    def tearDown(self):
        """Clean up test fixtures."""
        if self.recorder is not None:
            try:
                if hasattr(self.recorder, '_streamer') and self.recorder._streamer is not None:
                    self.recorder._streamer.stop()
            except Exception:
                pass
        
        if self.mock_service is not None:
            try:
                self.mock_service.stop()
            except Exception:
                pass
        
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _create_test_result(self, name: str, result_code: ResultCode = ResultCode.PASSED) -> TestResult:
        """Create a test result for testing."""
        result = TestResult(
            inst_id=str(uuid.uuid4()),
            name=name,
            parent_inst=str(uuid.uuid4()),
            monikers=[],
            pivots={}
        )
        result._result_code = result_code
        return result


class StreamingResultRecorderBasicTests(StreamingResultRecorderTestBase):
    """Basic tests for StreamingResultRecorder."""

    def test_recorder_context_manager(self):
        """Test that the recorder works as a context manager."""
        with StreamingResultRecorder(
            runid=self.runid,
            start=self.start_time,
            render_info=self.render_info,
            streaming_info=self.streaming_info,
            build_info=self.build_info,
            pipeline_info=self.pipeline_info,
            job_info=self.job_info
        ) as recorder:
            self.recorder = recorder
            self.assertTrue(recorder.is_streaming)
        
        # After context exit, streaming should be stopped
        self.assertFalse(self.recorder.is_streaming)

    def test_recorder_writes_local_files(self):
        """Test that the recorder writes to local files."""
        with StreamingResultRecorder(
            runid=self.runid,
            start=self.start_time,
            render_info=self.render_info,
            streaming_info=self.streaming_info,
            build_info=self.build_info,
            pipeline_info=self.pipeline_info,
            job_info=self.job_info
        ) as recorder:
            self.recorder = recorder
            
            # Record a test result
            test_result = self._create_test_result("test_function")
            recorder.preview(test_result)
            test_result.finalize()
            recorder.record(test_result)
        
        # Verify local files were created
        self.assertTrue(os.path.exists(self.render_info.summary_filename))
        self.assertTrue(os.path.exists(self.render_info.stream_results_filename))


class StreamingResultRecorderStreamingTests(StreamingResultRecorderTestBase):
    """Tests for streaming functionality of StreamingResultRecorder.
    
    Requirements: 28.1-28.6
    """

    def test_preview_streamed_to_service(self):
        """Test that previews are streamed to the external service.
        
        Requirement: 28.1 - Real-time result posting to REST endpoints
        """
        with StreamingResultRecorder(
            runid=self.runid,
            start=self.start_time,
            render_info=self.render_info,
            streaming_info=self.streaming_info,
            build_info=self.build_info,
            pipeline_info=self.pipeline_info,
            job_info=self.job_info
        ) as recorder:
            self.recorder = recorder
            
            # Record a preview
            test_result = self._create_test_result("test_streaming_preview")
            recorder.preview(test_result)
            
            # Wait for streaming
            time.sleep(0.2)
        
        # Verify preview was streamed
        received = self.mock_service.get_received_results()
        
        found_preview = False
        for entry in received:
            if entry['data'].get('type') == 'preview':
                found_preview = True
                self.assertEqual(entry['data']['data']['name'], "test_streaming_preview")
                break
        
        self.assertTrue(found_preview, "Preview should be streamed to service")

    def test_result_streamed_to_service(self):
        """Test that results are streamed to the external service.
        
        Requirement: 28.1 - Real-time result posting to REST endpoints
        """
        with StreamingResultRecorder(
            runid=self.runid,
            start=self.start_time,
            render_info=self.render_info,
            streaming_info=self.streaming_info,
            build_info=self.build_info,
            pipeline_info=self.pipeline_info,
            job_info=self.job_info
        ) as recorder:
            self.recorder = recorder
            
            # Record a result
            test_result = self._create_test_result("test_streaming_result")
            recorder.preview(test_result)
            test_result.finalize()
            recorder.record(test_result)
            
            # Wait for streaming
            time.sleep(0.2)
        
        # Verify result was streamed
        received = self.mock_service.get_received_results()
        
        found_result = False
        for entry in received:
            if entry['data'].get('type') == 'result':
                found_result = True
                self.assertEqual(entry['data']['data']['name'], "test_streaming_result")
                break
        
        self.assertTrue(found_result, "Result should be streamed to service")

    def test_multiple_results_streamed(self):
        """Test that multiple results are streamed correctly.
        
        Requirement: 28.1 - Real-time result posting to REST endpoints
        """
        with StreamingResultRecorder(
            runid=self.runid,
            start=self.start_time,
            render_info=self.render_info,
            streaming_info=self.streaming_info,
            build_info=self.build_info,
            pipeline_info=self.pipeline_info,
            job_info=self.job_info
        ) as recorder:
            self.recorder = recorder
            
            # Record multiple results
            for i in range(5):
                test_result = self._create_test_result(f"test_multi_{i}")
                recorder.preview(test_result)
                test_result.finalize()
                recorder.record(test_result)
            
            # Wait for streaming
            time.sleep(0.3)
        
        # Verify all results were streamed
        received = self.mock_service.get_received_results()
        
        # Should have 5 previews + 5 results = 10 entries
        self.assertGreaterEqual(len(received), 10)

    def test_streaming_stats_available(self):
        """Test that streaming statistics are available.
        
        Requirement: 28.1-28.6
        """
        with StreamingResultRecorder(
            runid=self.runid,
            start=self.start_time,
            render_info=self.render_info,
            streaming_info=self.streaming_info,
            build_info=self.build_info,
            pipeline_info=self.pipeline_info,
            job_info=self.job_info
        ) as recorder:
            self.recorder = recorder
            
            # Record some results
            for i in range(3):
                test_result = self._create_test_result(f"test_stats_{i}")
                recorder.preview(test_result)
                test_result.finalize()
                recorder.record(test_result)
            
            # Wait for streaming
            time.sleep(0.3)
            
            # Check stats
            stats = recorder.streaming_stats
            self.assertEqual(stats["previews_sent"], 3)
            self.assertEqual(stats["results_sent"], 3)
            self.assertEqual(stats["errors"], 0)


class StreamingResultRecorderCallbackTests(StreamingResultRecorderTestBase):
    """Tests for streaming callbacks in StreamingResultRecorder."""

    def test_custom_callback_invoked(self):
        """Test that custom callbacks are invoked during streaming."""
        callback_invocations = []
        
        def on_result(result_dict, is_preview):
            callback_invocations.append((result_dict['name'], is_preview))
            return True
        
        callback = StreamingCallback(on_result=on_result)
        
        with StreamingResultRecorder(
            runid=self.runid,
            start=self.start_time,
            render_info=self.render_info,
            streaming_info=self.streaming_info,
            build_info=self.build_info,
            pipeline_info=self.pipeline_info,
            job_info=self.job_info,
            streaming_callback=callback
        ) as recorder:
            self.recorder = recorder
            
            # Record a result
            test_result = self._create_test_result("test_callback")
            recorder.preview(test_result)
            test_result.finalize()
            recorder.record(test_result)
            
            # Wait for streaming
            time.sleep(0.2)
        
        # Verify callback was invoked
        self.assertEqual(len(callback_invocations), 2)
        self.assertEqual(callback_invocations[0], ("test_callback", True))  # preview
        self.assertEqual(callback_invocations[1], ("test_callback", False))  # result


if __name__ == "__main__":
    unittest.main()
