"""
    .. module:: ccai.tests.singlehost.integrationruntime.results.concentrators.test_progresscallbackhandler
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Unit tests for ProgressCallbackHandler request processing.

    .. moduleauthor:: CodeCraftX
"""

import tempfile
import os
import shutil
import json
import io
import http.client

from datetime import datetime

from ccai.testbase.results.model.buildinfo import BuildInfo
from ccai.testbase.results.model.pipelineinfo import PipelineInfo
from ccai.testbase.results.model.jobinfo import JobInfo
from ccai.testbase.results.model.renderinfo import RenderInfo
from ccai.testbase.results.model.progressinfo import ProgressInfo

from ccai.testbase.results.recorders.jsonresultrecorder import JsonResultRecorder
from ccai.integrationruntime.results.concentrators.progressconcentratorservice import (
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


def _establish_handler_env() -> dict:
    """
        Establish the per-test fixtures used by the ProgressCallbackHandler unit
        tests (the original ProgressCallbackHandlerTests.setUp).

        :returns: A dictionary carrying the temp dir, recorder, server and the
                  valid progress data sample used by the handler unit tests.
    """
    temp_dir = tempfile.mkdtemp()

    render_info = RenderInfo(
        title="Test Run",
        summary_filename=os.path.join(temp_dir, "summary.json"),
        summary_template=os.path.join(temp_dir, "template.html"),
        stream_results_filename=os.path.join(temp_dir, "results.json"),
        consolidated_results_filename=os.path.join(temp_dir, "consolidated.json"),
        static_resource_source=None,
        static_resource_destination=temp_dir
    )

    with open(render_info.summary_template, 'w') as f:
        f.write("<html></html>")

    runid = "test-run-uuid-123"
    start_time = datetime.now()

    build_info = BuildInfo(
        branch="main",
        build="build-123",
        flavor="release",
        release="1.0.0",
        url="https://ci.example.com/build/123"
    )

    pipeline_info = PipelineInfo(
        id="pipeline-uuid-456",
        name="CI Pipeline",
        instance="instance-uuid-789"
    )

    job_info = JobInfo(
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

    recorder = JsonResultRecorder(
        runid=runid,
        start=start_time,
        render_info=render_info,
        build_info=build_info,
        pipeline_info=pipeline_info,
        job_info=job_info
    )

    server_address = ("127.0.0.1", 0)

    server = ProgressConcentratorServer(
        recorder=recorder,
        server_address=server_address
    )

    valid_progress_data = {
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

    env = {
        "temp_dir": temp_dir,
        "render_info": render_info,
        "runid": runid,
        "start_time": start_time,
        "build_info": build_info,
        "pipeline_info": pipeline_info,
        "job_info": job_info,
        "recorder": recorder,
        "server_address": server_address,
        "server": server,
        "valid_progress_data": valid_progress_data
    }
    return env


def _teardown_handler_env(env: dict) -> None:
    """
        Replicate the ProgressCallbackHandlerTests.tearDown cleanup for the
        handler unit tests.

        :param env: The fixture dictionary returned by ``_establish_handler_env``.
    """
    server = env["server"]
    temp_dir = env["temp_dir"]

    try:
        server.server_close()
    except Exception:
        pass

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    return


def _establish_integration_env() -> dict:
    """
        Establish the per-test fixtures used by the ProgressCallbackHandler
        integration tests (the original ProgressCallbackHandlerIntegrationTests.setUp).

        :returns: A dictionary carrying the temp dir, recorder, started server,
                  actual port and the valid progress data sample used by the
                  integration tests.
    """
    temp_dir = tempfile.mkdtemp()

    render_info = RenderInfo(
        title="Test Run",
        summary_filename=os.path.join(temp_dir, "summary.json"),
        summary_template=os.path.join(temp_dir, "template.html"),
        stream_results_filename=os.path.join(temp_dir, "results.json"),
        consolidated_results_filename=os.path.join(temp_dir, "consolidated.json"),
        static_resource_source=None,
        static_resource_destination=temp_dir
    )

    with open(render_info.summary_template, 'w') as f:
        f.write("<html></html>")

    runid = "test-run-uuid-123"
    start_time = datetime.now()

    build_info = BuildInfo(
        branch="main",
        build="build-123",
        flavor="release",
        release="1.0.0",
        url="https://ci.example.com/build/123"
    )

    pipeline_info = PipelineInfo(
        id="pipeline-uuid-456",
        name="CI Pipeline",
        instance="instance-uuid-789"
    )

    job_info = JobInfo(
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

    recorder = JsonResultRecorder(
        runid=runid,
        start=start_time,
        render_info=render_info,
        build_info=build_info,
        pipeline_info=pipeline_info,
        job_info=job_info
    )

    server_address = ("127.0.0.1", 0)

    server = ProgressConcentratorServer(
        recorder=recorder,
        server_address=server_address
    )
    server.start()

    actual_port = server.server_address[1]

    valid_progress_data = {
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

    env = {
        "temp_dir": temp_dir,
        "render_info": render_info,
        "runid": runid,
        "start_time": start_time,
        "build_info": build_info,
        "pipeline_info": pipeline_info,
        "job_info": job_info,
        "recorder": recorder,
        "server_address": server_address,
        "server": server,
        "actual_port": actual_port,
        "valid_progress_data": valid_progress_data
    }
    return env


def _teardown_integration_env(env: dict) -> None:
    """
        Replicate the ProgressCallbackHandlerIntegrationTests.tearDown cleanup
        for the integration tests.

        :param env: The fixture dictionary returned by ``_establish_integration_env``.
    """
    server = env["server"]
    temp_dir = env["temp_dir"]

    try:
        server.shutdown()
        server.server_close()
    except Exception:
        pass

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    return


def _create_handler_with_request(env: dict, content: bytes, headers: dict = None):
    """
        Helper to create a handler with a mock request.

        :param env: The handler fixture dictionary carrying the active server.
        :param content: The request body bytes.
        :param headers: Optional mapping of request header names to values.

        :returns: A two-tuple of the configured handler and the MockWfile used
                  to capture response output.
    """
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
    handler.server = env["server"]
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

    rtnval = (handler, wfile)
    return rtnval


def test_handler_inherits_from_simple_http_request_handler() -> None:
    """Test that ProgressCallbackHandler inherits from SimpleHTTPRequestHandler (Requirement 5.1)."""
    env = _establish_handler_env()
    try:
        from http.server import SimpleHTTPRequestHandler
        assert issubclass(ProgressCallbackHandler, SimpleHTTPRequestHandler)
    finally:
        _teardown_handler_env(env)
    return


def test_handler_has_do_post_method() -> None:
    """Test that ProgressCallbackHandler implements do_POST method (Requirement 5.2)."""
    env = _establish_handler_env()
    try:
        assert hasattr(ProgressCallbackHandler, 'do_POST')
        assert callable(getattr(ProgressCallbackHandler, 'do_POST'))
    finally:
        _teardown_handler_env(env)
    return


def test_do_post_with_valid_json_payload_returns_200() -> None:
    """Test that do_POST with valid JSON payload returns 200 OK (Requirements 5.3-5.6, 6.1)."""
    env = _establish_handler_env()
    try:
        content = json.dumps(env["valid_progress_data"]).encode('utf-8')
        headers = {"content-length": str(len(content))}

        handler, wfile = _create_handler_with_request(env=env, content=content, headers=headers)

        handler.do_POST()

        response = wfile.get_value().decode('utf-8')
        assert "200" in response
    finally:
        _teardown_handler_env(env)
    return


def test_do_post_with_valid_json_calls_update_task_progress() -> None:
    """Test that do_POST creates ProgressInfo and calls update_task_progress (Requirements 5.5, 5.6)."""
    env = _establish_handler_env()
    try:
        content = json.dumps(env["valid_progress_data"]).encode('utf-8')
        headers = {"content-length": str(len(content))}

        handler, wfile = _create_handler_with_request(env=env, content=content, headers=headers)

        # Track if update_task_progress was called
        update_called = []
        original_update = env["server"].update_task_progress

        def mock_update(progress):
            update_called.append(progress)
            original_update(progress)

        env["server"].update_task_progress = mock_update

        handler.do_POST()

        assert len(update_called) == 1
        assert isinstance(update_called[0], ProgressInfo)
        assert update_called[0].id == "task-uuid-123"
    finally:
        _teardown_handler_env(env)
    return


def test_do_post_with_invalid_json_returns_500() -> None:
    """Test that do_POST with invalid JSON returns 500 error (Requirements 6.2, 7.1)."""
    env = _establish_handler_env()
    try:
        content = b"not valid json {"
        headers = {"content-length": str(len(content))}

        handler, wfile = _create_handler_with_request(env=env, content=content, headers=headers)

        handler.do_POST()

        response = wfile.get_value().decode('utf-8')
        assert "500" in response
    finally:
        _teardown_handler_env(env)
    return


def test_do_post_with_invalid_json_includes_error_message() -> None:
    """Test that 500 error includes error message (Requirements 6.3, 7.3, 7.4)."""
    env = _establish_handler_env()
    try:
        content = b"not valid json {"
        headers = {"content-length": str(len(content))}

        handler, wfile = _create_handler_with_request(env=env, content=content, headers=headers)

        handler.do_POST()

        response = wfile.get_value().decode('utf-8')
        assert "Error processing progress postback" in response
    finally:
        _teardown_handler_env(env)
    return


def test_do_post_with_missing_content_length_returns_200() -> None:
    """Test that do_POST with missing content-length header returns 200 OK (Requirement 7.5)."""
    env = _establish_handler_env()
    try:
        handler, wfile = _create_handler_with_request(env=env, content=b"", headers={})

        handler.do_POST()

        response = wfile.get_value().decode('utf-8')
        assert "200" in response
    finally:
        _teardown_handler_env(env)
    return


def test_do_post_with_zero_content_length_returns_200() -> None:
    """Test that do_POST with zero content-length returns 200 OK."""
    env = _establish_handler_env()
    try:
        headers = {"content-length": "0"}

        handler, wfile = _create_handler_with_request(env=env, content=b"", headers=headers)

        handler.do_POST()

        response = wfile.get_value().decode('utf-8')
        assert "200" in response
    finally:
        _teardown_handler_env(env)
    return


def test_do_post_sets_content_type_header() -> None:
    """Test that do_POST sets Content-Type header to text/html (Requirement 6.4)."""
    env = _establish_handler_env()
    try:
        content = json.dumps(env["valid_progress_data"]).encode('utf-8')
        headers = {"content-length": str(len(content))}

        handler, wfile = _create_handler_with_request(env=env, content=content, headers=headers)

        handler.do_POST()

        response = wfile.get_value().decode('utf-8')
        assert "Content-Type" in response
        assert "text/html" in response
    finally:
        _teardown_handler_env(env)
    return


def test_do_post_with_malformed_progress_data_returns_500() -> None:
    """Test that do_POST with malformed progress data returns 500 (Requirement 7.2)."""
    env = _establish_handler_env()
    try:
        # Missing required fields
        malformed_data = {"id": "task-123"}
        content = json.dumps(malformed_data).encode('utf-8')
        headers = {"content-length": str(len(content))}

        handler, wfile = _create_handler_with_request(env=env, content=content, headers=headers)

        handler.do_POST()

        response = wfile.get_value().decode('utf-8')
        assert "500" in response
    finally:
        _teardown_handler_env(env)
    return


def test_do_post_error_message_includes_exception_marker() -> None:
    """Test that error message includes EXCEPTION: marker (Requirement 7.4)."""
    env = _establish_handler_env()
    try:
        content = b"invalid json"
        headers = {"content-length": str(len(content))}

        handler, wfile = _create_handler_with_request(env=env, content=content, headers=headers)

        handler.do_POST()

        response = wfile.get_value().decode('utf-8')
        assert "EXCEPTION:" in response
    finally:
        _teardown_handler_env(env)
    return


def test_http_post_with_valid_json_returns_200() -> None:
    """Test actual HTTP POST with valid JSON returns 200."""
    env = _establish_integration_env()
    try:
        import urllib.request

        content = json.dumps(env["valid_progress_data"]).encode('utf-8')

        req = urllib.request.Request(
            f"http://127.0.0.1:{env['actual_port']}/progress",
            data=content,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        response = urllib.request.urlopen(req)

        assert response.status == 200
    finally:
        _teardown_integration_env(env)
    return


def test_http_post_with_invalid_json_returns_500() -> None:
    """Test actual HTTP POST with invalid JSON returns 500."""
    env = _establish_integration_env()
    try:
        import urllib.request
        import urllib.error

        content = b"not valid json"

        req = urllib.request.Request(
            f"http://127.0.0.1:{env['actual_port']}/progress",
            data=content,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        raised = False
        caught_exception = None
        try:
            urllib.request.urlopen(req)
        except urllib.error.HTTPError as http_error:
            raised = True
            caught_exception = http_error

        assert raised
        assert caught_exception.code == 500
    finally:
        _teardown_integration_env(env)
    return


def test_http_post_updates_recorder_running_tasks() -> None:
    """Test that HTTP POST updates the recorder's running tasks."""
    env = _establish_integration_env()
    try:
        import urllib.request

        content = json.dumps(env["valid_progress_data"]).encode('utf-8')

        req = urllib.request.Request(
            f"http://127.0.0.1:{env['actual_port']}/progress",
            data=content,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        urllib.request.urlopen(req)

        # Check that the task was added to running_tasks
        summary = env["recorder"].summary
        assert "running" in summary
    finally:
        _teardown_integration_env(env)
    return
