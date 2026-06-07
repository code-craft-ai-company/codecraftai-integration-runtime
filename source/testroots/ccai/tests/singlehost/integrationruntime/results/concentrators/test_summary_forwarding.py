"""
    .. module:: ccai.tests.singlehost.integrationruntime.results.concentrators.test_summary_forwarding
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Unit tests for ProgressConcentratorServer summary forwarding.

    .. moduleauthor:: CodeCraftX
"""

import tempfile
import os
import shutil
import threading
import time
import json
import requests

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


def _establish_env() -> dict:
    """
        Establish the per-test fixtures used by the summary forwarding tests,
        mirroring the original ``setUp``.

        :returns: A mapping of the fixture objects required by each test.
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

    servers_to_cleanup = []

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
        "servers_to_cleanup": servers_to_cleanup
    }
    return env


def _cleanup_env(env: dict) -> None:
    """
        Clean up the per-test fixtures, mirroring the original ``tearDown``.

        :param env: The mapping of fixture objects returned by ``_establish_env``.
    """
    servers_to_cleanup = env["servers_to_cleanup"]
    for server in servers_to_cleanup:
        try:
            server._forwarding_running = False
            server.shutdown()
            server.server_close()
            if hasattr(server, '_forward_thread') and server._forward_thread is not None:
                try:
                    server._forward_thread.join(timeout=2.0)
                except Exception:
                    pass
        except Exception:
            pass

    temp_dir = env["temp_dir"]
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    return


def test_forwarding_running_flag_is_true_during_loop() -> None:
    """
        Test that forwarding_running is True while loop is running (Requirement 9.1).
    """
    env = _establish_env()
    try:
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
                recorder=env["recorder"],
                server_address=env["server_address"],
                forwarding_info=forwarding_info
            )
            env["servers_to_cleanup"].append(server)

            server.start()

            assert server._forwarding_running
    finally:
        _cleanup_env(env=env)
    return


def test_forwarding_retrieves_summary_from_recorder() -> None:
    """
        Test that forwarding loop retrieves summary from recorder (Requirement 9.2).
    """
    env = _establish_env()
    try:
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url="https://monitoring.example.com/api/progress",
            forwarding_headers=None
        )

        posted_summaries = []

        def capture_post(url, data=None, headers=None):
            if data is not None:
                posted_summaries.append(json.loads(data))
            mock_response = Mock()
            return mock_response

        with create_module_patch(pcs_module.requests, "post", recursive=True) as mock_post:
            mock_post.configure(side_effect=capture_post)

            server = ProgressConcentratorServer(
                recorder=env["recorder"],
                server_address=env["server_address"],
                forwarding_info=forwarding_info
            )
            env["servers_to_cleanup"].append(server)

            server.start()

            time.sleep(0.15)

            assert len(posted_summaries) > 0

            summary = posted_summaries[0]
            assert "version" in summary
            assert "runid" in summary
            assert summary["runid"] == env["runid"]
    finally:
        _cleanup_env(env=env)
    return


def test_forwarding_posts_to_forwarding_url() -> None:
    """
        Test that forwarding loop POSTs to forwarding_url (Requirement 9.3).
    """
    env = _establish_env()
    try:
        expected_url = "https://monitoring.example.com/api/progress"
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url=expected_url,
            forwarding_headers=None
        )

        posted_urls = []

        def capture_post(url, data=None, headers=None):
            posted_urls.append(url)
            mock_response = Mock()
            return mock_response

        with create_module_patch(pcs_module.requests, "post", recursive=True) as mock_post:
            mock_post.configure(side_effect=capture_post)

            server = ProgressConcentratorServer(
                recorder=env["recorder"],
                server_address=env["server_address"],
                forwarding_info=forwarding_info
            )
            env["servers_to_cleanup"].append(server)

            server.start()

            time.sleep(0.15)

            assert len(posted_urls) > 0
            assert posted_urls[0] == expected_url
    finally:
        _cleanup_env(env=env)
    return


def test_forwarding_sleeps_for_interval() -> None:
    """
        Test that forwarding loop sleeps for forwarding_interval seconds (Requirement 9.4).
    """
    env = _establish_env()
    try:
        forwarding_interval = 0.1
        forwarding_info = ForwardingInfo(
            forwarding_interval=forwarding_interval,
            forwarding_url="https://monitoring.example.com/api/progress",
            forwarding_headers=None
        )

        post_times = []

        def capture_post(url, data=None, headers=None):
            post_times.append(time.time())
            mock_response = Mock()
            return mock_response

        with create_module_patch(pcs_module.requests, "post", recursive=True) as mock_post:
            mock_post.configure(side_effect=capture_post)

            server = ProgressConcentratorServer(
                recorder=env["recorder"],
                server_address=env["server_address"],
                forwarding_info=forwarding_info
            )
            env["servers_to_cleanup"].append(server)

            server.start()

            time.sleep(0.35)

            assert len(post_times) >= 2

            if len(post_times) >= 2:
                interval = post_times[1] - post_times[0]
                assert interval >= forwarding_interval * 0.8
    finally:
        _cleanup_env(env=env)
    return


def test_forwarding_includes_content_type_json_header() -> None:
    """
        Test that forwarding includes Content-Type: application/json header (Requirement 9.5).
    """
    env = _establish_env()
    try:
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url="https://monitoring.example.com/api/progress",
            forwarding_headers=None
        )

        captured_headers = []

        def capture_post(url, data=None, headers=None):
            if headers is not None:
                captured_headers.append(headers.copy())
            mock_response = Mock()
            return mock_response

        with create_module_patch(pcs_module.requests, "post", recursive=True) as mock_post:
            mock_post.configure(side_effect=capture_post)

            server = ProgressConcentratorServer(
                recorder=env["recorder"],
                server_address=env["server_address"],
                forwarding_info=forwarding_info
            )
            env["servers_to_cleanup"].append(server)

            server.start()

            time.sleep(0.15)

            assert len(captured_headers) > 0

            headers = captured_headers[0]
            assert "Content-Type" in headers
            assert headers["Content-Type"] == "application/json"
    finally:
        _cleanup_env(env=env)
    return


def test_forwarding_merges_custom_headers() -> None:
    """
        Test that forwarding merges forwarding_headers with default headers (Requirement 9.6).
    """
    env = _establish_env()
    try:
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

        def capture_post(url, data=None, headers=None):
            if headers is not None:
                captured_headers.append(headers.copy())
            mock_response = Mock()
            return mock_response

        with create_module_patch(pcs_module.requests, "post", recursive=True) as mock_post:
            mock_post.configure(side_effect=capture_post)

            server = ProgressConcentratorServer(
                recorder=env["recorder"],
                server_address=env["server_address"],
                forwarding_info=forwarding_info
            )
            env["servers_to_cleanup"].append(server)

            server.start()

            time.sleep(0.15)

            assert len(captured_headers) > 0

            headers = captured_headers[0]
            assert "Content-Type" in headers
            assert headers["Content-Type"] == "application/json"
            assert "Authorization" in headers
            assert headers["Authorization"] == "Bearer token123"
            assert "X-Job-Id" in headers
            assert headers["X-Job-Id"] == "job-456"
    finally:
        _cleanup_env(env=env)
    return


def test_forwarding_uses_only_default_header_when_forwarding_headers_is_none() -> None:
    """
        Test that only default Content-Type header is used when forwarding_headers is None (Requirement 8.4).
    """
    env = _establish_env()
    try:
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url="https://monitoring.example.com/api/progress",
            forwarding_headers=None
        )

        captured_headers = []

        def capture_post(url, data=None, headers=None):
            if headers is not None:
                captured_headers.append(headers.copy())
            mock_response = Mock()
            return mock_response

        with create_module_patch(pcs_module.requests, "post", recursive=True) as mock_post:
            mock_post.configure(side_effect=capture_post)

            server = ProgressConcentratorServer(
                recorder=env["recorder"],
                server_address=env["server_address"],
                forwarding_info=forwarding_info
            )
            env["servers_to_cleanup"].append(server)

            server.start()

            time.sleep(0.15)

            assert len(captured_headers) > 0

            headers = captured_headers[0]
            assert len(headers) == 1
            assert "Content-Type" in headers
    finally:
        _cleanup_env(env=env)
    return


def test_forwarding_catches_exceptions() -> None:
    """
        Test that forwarding catches exceptions from requests (Requirement 10.1).
    """
    env = _establish_env()
    try:
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url="https://monitoring.example.com/api/progress",
            forwarding_headers=None
        )

        exception_raised = threading.Event()

        def raise_exception(url, data=None, headers=None):
            exception_raised.set()
            raise requests.exceptions.ConnectionError("Network error")

        with create_module_patch(pcs_module.requests, "post", recursive=True) as mock_post:
            mock_post.configure(side_effect=raise_exception)

            server = ProgressConcentratorServer(
                recorder=env["recorder"],
                server_address=env["server_address"],
                forwarding_info=forwarding_info
            )
            env["servers_to_cleanup"].append(server)

            server.start()

            exception_raised.wait(timeout=0.5)

            assert exception_raised.is_set()
            assert server._forward_thread.is_alive()
    finally:
        _cleanup_env(env=env)
    return


def test_forwarding_logs_errors() -> None:
    """
        Test that forwarding logs errors using the logger (Requirement 10.2).
    """
    env = _establish_env()
    try:
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url="https://monitoring.example.com/api/progress",
            forwarding_headers=None
        )

        logged_errors = []

        def capture_error(msg):
            logged_errors.append(msg)

        def raise_exception(url, data=None, headers=None):
            raise requests.exceptions.ConnectionError("Network error")

        with create_module_patch(pcs_module.requests, "post", recursive=True) as mock_post:
            mock_post.configure(side_effect=raise_exception)

            server = ProgressConcentratorServer(
                recorder=env["recorder"],
                server_address=env["server_address"],
                forwarding_info=forwarding_info
            )
            env["servers_to_cleanup"].append(server)

            original_warning = server._logger.warning
            server._logger.warning = capture_error

            try:
                server.start()

                time.sleep(0.15)

                assert len(logged_errors) > 0

                assert any("Connection error" in err for err in logged_errors)
            finally:
                server._logger.warning = original_warning
    finally:
        _cleanup_env(env=env)
    return


def test_forwarding_continues_after_exception() -> None:
    """
        Test that forwarding loop continues after catching exception (Requirement 10.3).
    """
    env = _establish_env()
    try:
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url="https://monitoring.example.com/api/progress",
            forwarding_headers=None
        )

        call_count = [0]

        def count_calls(url, data=None, headers=None):
            call_count[0] += 1
            if call_count[0] <= 2:
                raise requests.exceptions.ConnectionError("Network error")
            mock_response = Mock()
            return mock_response

        with create_module_patch(pcs_module.requests, "post", recursive=True) as mock_post:
            mock_post.configure(side_effect=count_calls)

            server = ProgressConcentratorServer(
                recorder=env["recorder"],
                server_address=env["server_address"],
                forwarding_info=forwarding_info
            )
            env["servers_to_cleanup"].append(server)

            server.start()

            time.sleep(0.3)

            assert call_count[0] > 2
    finally:
        _cleanup_env(env=env)
    return


def test_forwarding_thread_does_not_terminate_on_network_error() -> None:
    """
        Test that forwarding thread does not terminate due to network errors (Requirement 10.4).
    """
    env = _establish_env()
    try:
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url="https://monitoring.example.com/api/progress",
            forwarding_headers=None
        )

        def raise_exception(url, data=None, headers=None):
            raise requests.exceptions.ConnectionError("Network error")

        with create_module_patch(pcs_module.requests, "post", recursive=True) as mock_post:
            mock_post.configure(side_effect=raise_exception)

            server = ProgressConcentratorServer(
                recorder=env["recorder"],
                server_address=env["server_address"],
                forwarding_info=forwarding_info
            )
            env["servers_to_cleanup"].append(server)

            server.start()

            time.sleep(0.2)

            assert server._forward_thread.is_alive()
            assert server._forwarding_running
    finally:
        _cleanup_env(env=env)
    return
