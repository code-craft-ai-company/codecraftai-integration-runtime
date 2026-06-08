"""
    .. module:: ccai.tests.singlehost.integrationruntime.results.streaming.test_streamingresultrecorder
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Integration tests for StreamingResultRecorder.

    This module contains integration tests for the StreamingResultRecorder class
    that combines local file recording with real-time streaming to external services.

    Requirements: 28.1-28.6

    .. moduleauthor:: CodeCraftX
"""

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


class StreamingTestEnv:
    """Container for the per-test fixtures established by :func:`_establish_env`."""

    def __init__(self) -> None:
        """
            Initialize all fixture slots to ``None`` so they are explicit and
            available for teardown even when establishment fails partway.
        """
        self.temp_dir = None
        self.render_info = None
        self.runid = None
        self.start_time = None
        self.build_info = None
        self.pipeline_info = None
        self.job_info = None
        self.mock_service = None
        self.actual_port = None
        self.streaming_url = None
        self.streaming_info = None
        self.recorder = None
        return


def _establish_env() -> StreamingTestEnv:
    """
        Establish the per-test fixtures originally created by the unittest
        ``setUp`` method. This builds the temp directory, render/build/pipeline/
        job info objects, starts the mock streaming service and assembles the
        streaming info.

        :returns: A :class:`StreamingTestEnv` populated with the test fixtures.
    """
    env = StreamingTestEnv()

    env.temp_dir = tempfile.mkdtemp()

    # Create render info
    env.render_info = RenderInfo(
        title="Streaming Test Run",
        summary_filename=os.path.join(env.temp_dir, "summary.json"),
        summary_template=os.path.join(env.temp_dir, "template.html"),
        stream_results_filename=os.path.join(env.temp_dir, "results.jsos"),
        consolidated_results_filename=os.path.join(env.temp_dir, "consolidated.json"),
        static_resource_source=None,
        static_resource_destination=env.temp_dir
    )

    # Create template file
    with open(env.render_info.summary_template, 'w') as f:
        f.write("<html></html>")

    env.runid = str(uuid.uuid4())
    env.start_time = datetime.now()

    env.build_info = BuildInfo(
        branch="main",
        build="build-streaming-test",
        flavor="release",
        release="1.0.0",
        url="https://ci.example.com/build/streaming"
    )

    env.pipeline_info = PipelineInfo(
        id="pipeline-streaming",
        name="Streaming Pipeline",
        instance="instance-streaming"
    )

    env.job_info = JobInfo(
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
    env.mock_service = MockStreamingService(("127.0.0.1", 0))
    env.mock_service.start()
    env.actual_port = env.mock_service.server_address[1]
    env.streaming_url = f"http://127.0.0.1:{env.actual_port}/api/results"

    env.streaming_info = StreamingInfo(
        protocol=StreamingProtocol.REST,
        streaming_url=env.streaming_url,
        stream_previews=True,
        stream_results=True
    )

    env.recorder = None

    return env


def _teardown_env(env: StreamingTestEnv) -> None:
    """
        Replicate the per-test cleanup originally performed by the unittest
        ``tearDown`` method. Stops any active streamer, stops the mock service
        and removes the temp directory.

        :param env: The :class:`StreamingTestEnv` to clean up.
    """
    if env.recorder is not None:
        try:
            if hasattr(env.recorder, '_streamer') and env.recorder._streamer is not None:
                env.recorder._streamer.stop()
        except Exception:
            pass

    if env.mock_service is not None:
        try:
            env.mock_service.stop()
        except Exception:
            pass

    if env.temp_dir is not None and os.path.exists(env.temp_dir):
        shutil.rmtree(env.temp_dir)

    return


def _create_test_result(name: str, result_code: ResultCode = ResultCode.PASSED) -> TestResult:
    """
        Create a test result for testing.

        :param name: The name to assign to the test result.
        :param result_code: The result code to stamp onto the test result.

        :returns: A populated :class:`TestResult` instance.
    """
    result = TestResult(
        inst_id=str(uuid.uuid4()),
        name=name,
        parent_inst=str(uuid.uuid4()),
        monikers=[],
        pivots={}
    )
    result._result_code = result_code
    return result


def test_recorder_context_manager() -> None:
    """Test that the recorder works as a context manager."""
    env = _establish_env()
    try:
        with StreamingResultRecorder(
            runid=env.runid,
            start=env.start_time,
            render_info=env.render_info,
            streaming_info=env.streaming_info,
            build_info=env.build_info,
            pipeline_info=env.pipeline_info,
            job_info=env.job_info
        ) as recorder:
            env.recorder = recorder
            assert recorder.is_streaming

        # After context exit, streaming should be stopped
        assert not env.recorder.is_streaming
    finally:
        _teardown_env(env)

    return


def test_recorder_writes_local_files() -> None:
    """Test that the recorder writes to local files."""
    env = _establish_env()
    try:
        with StreamingResultRecorder(
            runid=env.runid,
            start=env.start_time,
            render_info=env.render_info,
            streaming_info=env.streaming_info,
            build_info=env.build_info,
            pipeline_info=env.pipeline_info,
            job_info=env.job_info
        ) as recorder:
            env.recorder = recorder

            # Record a test result
            test_result = _create_test_result("test_function")
            recorder.preview(test_result)
            test_result.finalize()
            recorder.record(test_result)

        # Verify local files were created
        assert os.path.exists(env.render_info.summary_filename)
        assert os.path.exists(env.render_info.stream_results_filename)
    finally:
        _teardown_env(env)

    return


def test_preview_streamed_to_service() -> None:
    """Test that previews are streamed to the external service.

    Requirement: 28.1 - Real-time result posting to REST endpoints
    """
    env = _establish_env()
    try:
        with StreamingResultRecorder(
            runid=env.runid,
            start=env.start_time,
            render_info=env.render_info,
            streaming_info=env.streaming_info,
            build_info=env.build_info,
            pipeline_info=env.pipeline_info,
            job_info=env.job_info
        ) as recorder:
            env.recorder = recorder

            # Record a preview
            test_result = _create_test_result("test_streaming_preview")
            recorder.preview(test_result)

            # Wait for streaming
            time.sleep(0.2)

        # Verify preview was streamed
        received = env.mock_service.get_received_results()

        found_preview = False
        for entry in received:
            if entry['data'].get('type') == 'preview':
                found_preview = True
                assert entry['data']['data']['name'] == "test_streaming_preview"
                break

        assert found_preview, "Preview should be streamed to service"
    finally:
        _teardown_env(env)

    return


def test_result_streamed_to_service() -> None:
    """Test that results are streamed to the external service.

    Requirement: 28.1 - Real-time result posting to REST endpoints
    """
    env = _establish_env()
    try:
        with StreamingResultRecorder(
            runid=env.runid,
            start=env.start_time,
            render_info=env.render_info,
            streaming_info=env.streaming_info,
            build_info=env.build_info,
            pipeline_info=env.pipeline_info,
            job_info=env.job_info
        ) as recorder:
            env.recorder = recorder

            # Record a result
            test_result = _create_test_result("test_streaming_result")
            recorder.preview(test_result)
            test_result.finalize()
            recorder.record(test_result)

            # Wait for streaming
            time.sleep(0.2)

        # Verify result was streamed
        received = env.mock_service.get_received_results()

        found_result = False
        for entry in received:
            if entry['data'].get('type') == 'result':
                found_result = True
                assert entry['data']['data']['name'] == "test_streaming_result"
                break

        assert found_result, "Result should be streamed to service"
    finally:
        _teardown_env(env)

    return


def test_multiple_results_streamed() -> None:
    """Test that multiple results are streamed correctly.

    Requirement: 28.1 - Real-time result posting to REST endpoints
    """
    env = _establish_env()
    try:
        with StreamingResultRecorder(
            runid=env.runid,
            start=env.start_time,
            render_info=env.render_info,
            streaming_info=env.streaming_info,
            build_info=env.build_info,
            pipeline_info=env.pipeline_info,
            job_info=env.job_info
        ) as recorder:
            env.recorder = recorder

            # Record multiple results
            for i in range(5):
                test_result = _create_test_result(f"test_multi_{i}")
                recorder.preview(test_result)
                test_result.finalize()
                recorder.record(test_result)

            # Wait for streaming
            time.sleep(0.3)

        # Verify all results were streamed
        received = env.mock_service.get_received_results()

        # Should have 5 previews + 5 results = 10 entries
        assert len(received) >= 10
    finally:
        _teardown_env(env)

    return


def test_streaming_stats_available() -> None:
    """Test that streaming statistics are available.

    Requirement: 28.1-28.6
    """
    env = _establish_env()
    try:
        with StreamingResultRecorder(
            runid=env.runid,
            start=env.start_time,
            render_info=env.render_info,
            streaming_info=env.streaming_info,
            build_info=env.build_info,
            pipeline_info=env.pipeline_info,
            job_info=env.job_info
        ) as recorder:
            env.recorder = recorder

            # Record some results
            for i in range(3):
                test_result = _create_test_result(f"test_stats_{i}")
                recorder.preview(test_result)
                test_result.finalize()
                recorder.record(test_result)

            # Wait for streaming
            time.sleep(0.3)

            # Check stats
            stats = recorder.streaming_stats
            assert stats["previews_sent"] == 3
            assert stats["results_sent"] == 3
            assert stats["errors"] == 0
    finally:
        _teardown_env(env)

    return


def test_custom_callback_invoked() -> None:
    """Test that custom callbacks are invoked during streaming."""
    env = _establish_env()
    try:
        callback_invocations = []

        def on_result(result_dict, is_preview):
            callback_invocations.append((result_dict['name'], is_preview))
            return True

        callback = StreamingCallback(on_result=on_result)

        with StreamingResultRecorder(
            runid=env.runid,
            start=env.start_time,
            render_info=env.render_info,
            streaming_info=env.streaming_info,
            build_info=env.build_info,
            pipeline_info=env.pipeline_info,
            job_info=env.job_info,
            streaming_callback=callback
        ) as recorder:
            env.recorder = recorder

            # Record a result
            test_result = _create_test_result("test_callback")
            recorder.preview(test_result)
            test_result.finalize()
            recorder.record(test_result)

            # Wait for streaming
            time.sleep(0.2)

        # Verify callback was invoked
        assert len(callback_invocations) == 2
        assert callback_invocations[0] == ("test_callback", True)  # preview
        assert callback_invocations[1] == ("test_callback", False)  # result
    finally:
        _teardown_env(env)

    return
