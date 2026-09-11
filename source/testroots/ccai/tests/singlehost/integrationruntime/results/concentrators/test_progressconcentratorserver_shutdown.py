"""
    .. module:: ccai.tests.singlehost.integrationruntime.results.concentrators.test_progressconcentratorserver_shutdown
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Unit tests for ProgressConcentratorServer shutdown.

    .. moduleauthor:: CodeCraftX
"""

import tempfile
import os
import shutil

from datetime import datetime
from typing import Any, Dict

from ccai.testbase.results.model.buildinfo import BuildInfo
from ccai.testbase.results.model.pipelineinfo import PipelineInfo
from ccai.testbase.results.model.jobinfo import JobInfo
from ccai.testbase.results.model.renderinfo import RenderInfo
from ccai.testbase.results.model.forwardinginfo import ForwardingInfo

from ccai.testbase.results.recorders.jsonresultrecorder import JsonResultRecorder
from ccai.integrationruntime.results.concentrators.progressconcentratorservice import (
    ProgressConcentratorServer
)

from ccai.waiting import wait_for_it

# Bounded-wait parameters used when polling for work done by the concentrator's background
# threads. The timeout is generous so slow or coarse-clock runners (Windows and macOS CI)
# never fail on scheduling latency, while the short polling interval keeps fast runners fast.
WAIT_TIMEOUT = 5.0
WAIT_INTERVAL = 0.02

from ccai.testbase.mocking import create_module_patch

import ccai.integrationruntime.results.concentrators.progressconcentratorservice as pcs_module


def _establish_env() -> Dict[str, Any]:
    """
        Set up the per-test fixtures used by the ProgressConcentratorServer
        shutdown tests.

        :returns: A mapping containing the temp directory, render info, run
                  identifier, start time, build/pipeline/job info, the result
                  recorder, the server address tuple, and the list of servers
                  scheduled for cleanup.
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
        "servers_to_cleanup": servers_to_cleanup,
    }
    return env


def _teardown_env(env: Dict[str, Any]) -> None:
    """
        Clean up the per-test fixtures created by :func:`_establish_env`.

        :param env: The environment mapping returned by :func:`_establish_env`.
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


def test_shutdown_method_exists() -> None:
    """
        Test that ProgressConcentratorServer has shutdown method from HTTPServer.
    """
    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=env["server_address"],
            bind_and_activate=False
        )

        assert hasattr(server, 'shutdown')
        assert callable(server.shutdown)

        server.server_close()
    finally:
        _teardown_env(env)

    return


def test_server_close_method_exists() -> None:
    """
        Test that ProgressConcentratorServer has server_close method from HTTPServer.
    """
    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=env["server_address"],
            bind_and_activate=False
        )

        assert hasattr(server, 'server_close')
        assert callable(server.server_close)

        server.server_close()
    finally:
        _teardown_env(env)

    return


def test_shutdown_stops_server_thread() -> None:
    """
        Test that shutdown stops the server thread.
    """
    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=env["server_address"]
        )

        server.start()

        assert server._server_thread.is_alive()

        server.shutdown()

        server._server_thread.join(timeout=2.0)

        assert not server._server_thread.is_alive()

        server.server_close()
    finally:
        _teardown_env(env)

    return


def test_shutdown_allows_server_close() -> None:
    """
        Test that shutdown followed by server_close completes without error.
    """
    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=env["server_address"]
        )

        server.start()

        server.shutdown()
        server.server_close()
    finally:
        _teardown_env(env)

    return


def test_forwarding_thread_stops_when_flag_cleared() -> None:
    """
        Test that forwarding thread stops when _forwarding_running is set to False.
    """
    env = _establish_env()
    try:
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url="https://monitoring.example.com/api/progress",
            forwarding_headers=None
        )

        with create_module_patch(pcs_module.requests, "post", recursive=True) as mock_post:
            mock_post.configure(return_value=None)

            server = ProgressConcentratorServer(
                recorder=env["recorder"],
                server_address=env["server_address"],
                forwarding_info=forwarding_info
            )

            server.start()

            assert server._forward_thread.is_alive()
            assert server._forwarding_running

            server._forwarding_running = False

            server._forward_thread.join(timeout=2.0)

            assert not server._forward_thread.is_alive()

            server.shutdown()
            server.server_close()
    finally:
        _teardown_env(env)

    return


def test_full_shutdown_sequence() -> None:
    """
        Test complete shutdown sequence with both server and forwarding threads.
    """
    env = _establish_env()
    try:
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url="https://monitoring.example.com/api/progress",
            forwarding_headers=None
        )

        with create_module_patch(pcs_module.requests, "post", recursive=True) as mock_post:
            mock_post.configure(return_value=None)

            server = ProgressConcentratorServer(
                recorder=env["recorder"],
                server_address=env["server_address"],
                forwarding_info=forwarding_info
            )

            server.start()

            assert server._server_thread.is_alive()
            assert server._forward_thread.is_alive()

            server._forwarding_running = False
            server.shutdown()

            server._server_thread.join(timeout=2.0)
            server._forward_thread.join(timeout=2.0)

            assert not server._server_thread.is_alive()
            assert not server._forward_thread.is_alive()

            server.server_close()
    finally:
        _teardown_env(env)

    return


def test_server_accepts_no_connections_after_shutdown() -> None:
    """
        Test that server does not accept connections after shutdown.
    """
    import urllib.request
    import urllib.error

    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=env["server_address"]
        )

        server.start()
        actual_port = server.server_address[1]

        server.shutdown()
        server.server_close()

        # Wait for the server thread to exit before probing. The listening socket is
        # closed synchronously by server_close(), so connections must be refused after that.
        wait_for_it(lambda wctx: not server._server_thread.is_alive(),
                    what_for="the server thread to exit after shutdown",
                    interval=WAIT_INTERVAL, timeout=WAIT_TIMEOUT)

        raised = False
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{actual_port}/progress",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            urllib.request.urlopen(req, timeout=1.0)
        except (urllib.error.URLError, ConnectionRefusedError, OSError):
            raised = True

        assert raised
    finally:
        _teardown_env(env)

    return
