"""
    .. module:: ccai.tests.singlehost.integrationruntime.results.concentrators.test_progressconcentratorserver_startup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Unit tests for ProgressConcentratorServer startup.

    .. moduleauthor:: CodeCraftX
"""

import tempfile
import os
import shutil
import threading
import time

from typing import Any, Dict, List

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


def _establish_env() -> Dict[str, Any]:
    """
        Replicates the original ``setUp`` for each test by building the temporary directory,
        the render/build/pipeline/job fixtures, the recorder, the server address and the
        forwarding info needed by the tests.

        :returns: A dictionary carrying all of the fixtures the tests require, including the
                  ``servers_to_cleanup`` list used to mirror the original ``tearDown``.
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

    # Create a dummy template file
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

    server_address = ("127.0.0.1", 0)  # Port 0 lets OS assign available port

    forwarding_info = ForwardingInfo(
        forwarding_interval=5.0,
        forwarding_url="https://monitoring.example.com/api/progress",
        forwarding_headers={"Authorization": "Bearer token123"}
    )

    servers_to_cleanup: List[Any] = []

    env: Dict[str, Any] = {
        "temp_dir": temp_dir,
        "render_info": render_info,
        "runid": runid,
        "start_time": start_time,
        "build_info": build_info,
        "pipeline_info": pipeline_info,
        "job_info": job_info,
        "recorder": recorder,
        "server_address": server_address,
        "forwarding_info": forwarding_info,
        "servers_to_cleanup": servers_to_cleanup
    }
    return env


def _cleanup_env(env: Dict[str, Any]) -> None:
    """
        Replicates the original ``tearDown`` for each test by shutting down any servers that
        were registered for cleanup and removing the temporary directory.

        :param env: The environment dictionary produced by :func:`_establish_env`.
    """
    servers_to_cleanup = env["servers_to_cleanup"]
    temp_dir = env["temp_dir"]

    for server in servers_to_cleanup:
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

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    return


def test_start_method_exists() -> None:
    """
        Test that ProgressConcentratorServer provides a start method (Requirement 2.1).
    """
    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=env["server_address"],
            bind_and_activate=False
        )

        assert hasattr(server, 'start')
        assert callable(server.start)

        server.server_close()
    finally:
        _cleanup_env(env=env)
    return


def test_start_creates_server_thread() -> None:
    """
        Test that start method creates a server thread (Requirement 2.2).
    """
    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=env["server_address"]
        )
        env["servers_to_cleanup"].append(server)

        server.start()

        assert server._server_thread is not None
        assert isinstance(server._server_thread, threading.Thread)
    finally:
        _cleanup_env(env=env)
    return


def test_server_thread_is_daemon() -> None:
    """
        Test that server thread is created as a daemon thread (Requirement 2.2).
    """
    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=env["server_address"]
        )
        env["servers_to_cleanup"].append(server)

        server.start()

        assert server._server_thread.daemon
    finally:
        _cleanup_env(env=env)
    return


def test_server_thread_is_named_prog_concentrator() -> None:
    """
        Test that server thread is named 'prog-concentrator' (Requirement 3.3).
    """
    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=env["server_address"]
        )
        env["servers_to_cleanup"].append(server)

        server.start()

        assert server._server_thread.name == 'prog-concentrator'
    finally:
        _cleanup_env(env=env)
    return


def test_server_thread_is_alive_after_start() -> None:
    """
        Test that server thread is running after start returns (Requirement 2.3, 2.4).
    """
    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=env["server_address"]
        )
        env["servers_to_cleanup"].append(server)

        server.start()

        assert server._server_thread.is_alive()
    finally:
        _cleanup_env(env=env)
    return


def test_server_running_flag_is_true_after_start() -> None:
    """
        Test that server_running flag is True after start (Requirement 3.6).
    """
    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=env["server_address"]
        )
        env["servers_to_cleanup"].append(server)

        server.start()

        assert server._server_running
    finally:
        _cleanup_env(env=env)
    return


def test_start_returns_after_gate_synchronization() -> None:
    """
        Test that start method uses gate Event for synchronization (Requirement 2.3, 2.4).
    """
    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=env["server_address"]
        )
        env["servers_to_cleanup"].append(server)

        # Record time before start
        start_time = time.time()

        server.start()

        # Record time after start returns
        end_time = time.time()

        # The start method should return quickly after the gate is set
        # If gate synchronization wasn't working, the method might hang or return prematurely
        elapsed = end_time - start_time

        # Start should complete within a reasonable time (not hang indefinitely)
        assert elapsed < 5.0

        # Server thread should be alive, confirming gate was set
        assert server._server_thread.is_alive()
    finally:
        _cleanup_env(env=env)
    return


def test_start_creates_forwarding_thread_when_forwarding_info_provided() -> None:
    """
        Test that forwarding thread is created when forwarding_info is provided (Requirement 2.5).
    """
    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=env["server_address"],
            forwarding_info=env["forwarding_info"]
        )
        env["servers_to_cleanup"].append(server)

        server.start()

        assert server._forward_thread is not None
        assert isinstance(server._forward_thread, threading.Thread)
    finally:
        _cleanup_env(env=env)
    return


def test_forwarding_thread_is_daemon() -> None:
    """
        Test that forwarding thread is created as a daemon thread (Requirement 3.2).
    """
    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=env["server_address"],
            forwarding_info=env["forwarding_info"]
        )
        env["servers_to_cleanup"].append(server)

        server.start()

        assert server._forward_thread.daemon
    finally:
        _cleanup_env(env=env)
    return


def test_forwarding_thread_is_named_prog_forwarder() -> None:
    """
        Test that forwarding thread is named 'prog-forwarder' (Requirement 3.4).
    """
    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=env["server_address"],
            forwarding_info=env["forwarding_info"]
        )
        env["servers_to_cleanup"].append(server)

        server.start()

        assert server._forward_thread.name == 'prog-forwarder'
    finally:
        _cleanup_env(env=env)
    return


def test_forwarding_thread_is_alive_after_start() -> None:
    """
        Test that forwarding thread is running after start returns (Requirement 2.6).
    """
    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=env["server_address"],
            forwarding_info=env["forwarding_info"]
        )
        env["servers_to_cleanup"].append(server)

        server.start()

        assert server._forward_thread.is_alive()
    finally:
        _cleanup_env(env=env)
    return


def test_no_forwarding_thread_when_forwarding_info_is_none() -> None:
    """
        Test that no forwarding thread is created when forwarding_info is None (Requirement 2.5).
    """
    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=env["server_address"],
            forwarding_info=None
        )
        env["servers_to_cleanup"].append(server)

        server.start()

        assert server._forward_thread is None
    finally:
        _cleanup_env(env=env)
    return


def test_start_waits_for_both_threads_when_forwarding_enabled() -> None:
    """
        Test that start method waits for both threads when forwarding_info is provided (Requirement 2.7).
    """
    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=env["server_address"],
            forwarding_info=env["forwarding_info"]
        )
        env["servers_to_cleanup"].append(server)

        server.start()

        # Both threads should be alive after start returns
        assert server._server_thread.is_alive()
        assert server._forward_thread.is_alive()

        # Both threads should have been started
        assert server._server_thread is not None
        assert server._forward_thread is not None
    finally:
        _cleanup_env(env=env)
    return
