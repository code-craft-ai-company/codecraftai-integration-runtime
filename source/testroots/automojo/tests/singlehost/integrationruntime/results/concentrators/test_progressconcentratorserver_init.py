"""
    .. module:: automojo.tests.singlehost.integrationruntime.results.concentrators.test_progressconcentratorserver_init
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Unit tests for ProgressConcentratorServer initialization.

    .. moduleauthor:: AutomationX
"""

import tempfile
import os
import shutil

from datetime import datetime
from http.server import HTTPServer
from socketserver import ThreadingMixIn

from automojo.testbase.results.model.buildinfo import BuildInfo
from automojo.testbase.results.model.pipelineinfo import PipelineInfo
from automojo.testbase.results.model.jobinfo import JobInfo
from automojo.testbase.results.model.renderinfo import RenderInfo
from automojo.testbase.results.model.forwardinginfo import ForwardingInfo

from automojo.testbase.results.recorders.jsonresultrecorder import JsonResultRecorder
from automojo.integrationruntime.results.concentrators.progressconcentratorservice import (
    ProgressConcentratorServer
)


def _establish_env() -> dict:
    """
        Establish the per-test fixtures used by the ProgressConcentratorServer
        initialization tests, mirroring the original ``setUp``.

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

    # Create a dummy template file
    with open(render_info.summary_template, 'w') as f:
        f.write("<html></html>")

    runid = "test-run-uuid-123"
    start = datetime.now()

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
        start=start,
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

    env = {
        "temp_dir": temp_dir,
        "render_info": render_info,
        "runid": runid,
        "start": start,
        "build_info": build_info,
        "pipeline_info": pipeline_info,
        "job_info": job_info,
        "recorder": recorder,
        "server_address": server_address,
        "forwarding_info": forwarding_info
    }
    return env


def _cleanup_env(env: dict) -> None:
    """
        Clean up the per-test fixtures, mirroring the original ``tearDown``.

        :param env: The mapping of fixture objects returned by ``_establish_env``.
    """
    temp_dir = env["temp_dir"]
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    return


def test_constructor_accepts_recorder_parameter() -> None:
    """
        Test that constructor accepts recorder parameter of type ResultRecorder (Requirement 1.1).
    """
    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=env["server_address"],
            bind_and_activate=False
        )

        assert server._recorder is not None
        assert server._recorder is env["recorder"]

        server.server_close()
    finally:
        _cleanup_env(env=env)
    return


def test_constructor_accepts_server_address_parameter() -> None:
    """
        Test that constructor accepts server_address parameter as tuple of (host, port) (Requirement 1.2).
    """
    env = _establish_env()
    try:
        test_address = ("127.0.0.1", 0)

        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=test_address,
            bind_and_activate=False
        )

        # The server_address attribute is set by HTTPServer
        assert server.server_address is not None

        server.server_close()
    finally:
        _cleanup_env(env=env)
    return


def test_constructor_accepts_optional_forwarding_info_parameter() -> None:
    """
        Test that constructor accepts optional forwarding_info parameter of type ForwardingInfo (Requirement 1.3).
    """
    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=env["server_address"],
            forwarding_info=env["forwarding_info"],
            bind_and_activate=False
        )

        assert server._forwarding_info is not None
        assert server._forwarding_info is env["forwarding_info"]

        server.server_close()
    finally:
        _cleanup_env(env=env)
    return


def test_constructor_accepts_none_forwarding_info() -> None:
    """
        Test that constructor accepts None for forwarding_info parameter (Requirement 1.3).
    """
    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=env["server_address"],
            forwarding_info=None,
            bind_and_activate=False
        )

        assert server._forwarding_info is None

        server.server_close()
    finally:
        _cleanup_env(env=env)
    return


def test_constructor_bind_and_activate_defaults_to_true() -> None:
    """
        Test that bind_and_activate parameter defaults to True (Requirement 1.4).
    """
    env = _establish_env()
    try:
        # Create server with bind_and_activate=True (default)
        # Using port 0 to let OS assign an available port
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=("127.0.0.1", 0)
        )

        # When bind_and_activate is True, the server should be bound to an address
        # The server_address will be updated with the actual port assigned
        assert server.server_address is not None
        assert server.server_address[1] != 0  # Port should be assigned

        server.server_close()
    finally:
        _cleanup_env(env=env)
    return


def test_constructor_bind_and_activate_false_does_not_bind() -> None:
    """
        Test that bind_and_activate=False does not bind immediately (Requirement 1.4).
    """
    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=("127.0.0.1", 0),
            bind_and_activate=False
        )

        # When bind_and_activate is False, the socket should not be bound yet
        # The server_address will still be the original tuple
        assert server.server_address == ("127.0.0.1", 0)

        server.server_close()
    finally:
        _cleanup_env(env=env)
    return


def test_class_inherits_from_threading_mixin() -> None:
    """
        Test that ProgressConcentratorServer inherits from ThreadingMixIn (Requirement 1.5).
    """
    env = _establish_env()
    try:
        assert issubclass(ProgressConcentratorServer, ThreadingMixIn)
    finally:
        _cleanup_env(env=env)
    return


def test_class_inherits_from_http_server() -> None:
    """
        Test that ProgressConcentratorServer inherits from HTTPServer (Requirement 1.5).
    """
    env = _establish_env()
    try:
        assert issubclass(ProgressConcentratorServer, HTTPServer)
    finally:
        _cleanup_env(env=env)
    return


def test_constructor_stores_recorder_reference() -> None:
    """
        Test that server stores recorder reference for progress aggregation (Requirement 1.6).
    """
    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=env["server_address"],
            bind_and_activate=False
        )

        # Verify the recorder reference is stored and accessible
        assert server._recorder is env["recorder"]

        server.server_close()
    finally:
        _cleanup_env(env=env)
    return


def test_constructor_initializes_server_running_to_false() -> None:
    """
        Test that server_running flag is initialized to False (Requirement 1.7).
    """
    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=env["server_address"],
            bind_and_activate=False
        )

        assert not server._server_running

        server.server_close()
    finally:
        _cleanup_env(env=env)
    return


def test_constructor_initializes_forwarding_running_to_false() -> None:
    """
        Test that forwarding_running flag is initialized to False (Requirement 1.7).
    """
    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=env["server_address"],
            forwarding_info=env["forwarding_info"],
            bind_and_activate=False
        )

        assert not server._forwarding_running

        server.server_close()
    finally:
        _cleanup_env(env=env)
    return


def test_constructor_initializes_logger() -> None:
    """
        Test that constructor initializes an EnhancedLogger instance (Requirement 15.1).
    """
    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=env["server_address"],
            bind_and_activate=False
        )

        assert server._logger is not None

        server.server_close()
    finally:
        _cleanup_env(env=env)
    return


def test_constructor_initializes_thread_references_to_none() -> None:
    """
        Test that constructor initializes thread references to None.
    """
    env = _establish_env()
    try:
        server = ProgressConcentratorServer(
            recorder=env["recorder"],
            server_address=env["server_address"],
            bind_and_activate=False
        )

        assert server._server_thread is None
        assert server._forward_thread is None

        server.server_close()
    finally:
        _cleanup_env(env=env)
    return
