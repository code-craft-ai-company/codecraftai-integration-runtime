"""
    .. module:: ccai.tests.singlehost.integrationruntime.results.concentrators.test_summary_forwarding_integration
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Integration tests for summary forwarding functionality.

    .. moduleauthor:: CodeCraftX
"""

import tempfile
import os
import shutil
import threading
import time
import json
import http.client
import uuid

from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
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


class MockExternalServiceHandler(BaseHTTPRequestHandler):
    """Handler for mock external monitoring service that receives forwarded summaries."""

    def do_POST(self):
        """Handle POST requests containing forwarded summaries."""
        content_length = int(self.headers.get('Content-Length', 0))

        if content_length > 0:
            body = self.rfile.read(content_length)
            try:
                summary = json.loads(body)

                # Store the received summary and headers in the server
                with self.server.lock:
                    self.server.received_summaries.append({
                        'summary': summary,
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


class MockExternalService(ThreadingMixIn, HTTPServer):
    """Mock external monitoring service for integration testing."""

    def __init__(self, server_address):
        super().__init__(server_address, MockExternalServiceHandler)
        self.received_summaries = []
        self.lock = threading.Lock()
        self._server_thread = None

    def start(self):
        """Start the mock service in a background thread."""
        self._server_thread = threading.Thread(
            target=self.serve_forever,
            daemon=True
        )
        self._server_thread.start()
        # Give the server time to start
        time.sleep(0.05)

    def stop(self):
        """Stop the mock service."""
        self.shutdown()
        self.server_close()

    def get_received_summaries(self):
        """Get a copy of received summaries in a thread-safe manner."""
        with self.lock:
            return list(self.received_summaries)

    def clear_received_summaries(self):
        """Clear received summaries in a thread-safe manner."""
        with self.lock:
            self.received_summaries.clear()


def _establish_env() -> dict:
    """
        Establish the per-test fixtures used by the summary forwarding
        integration tests, mirroring the original ``setUp``.

        :returns: A mapping of the fixture objects required by each test.
    """
    temp_dir = tempfile.mkdtemp()

    render_info = RenderInfo(
        title="Summary Forwarding Integration Test",
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

    runid = str(uuid.uuid4())
    start_time = datetime.now()

    build_info = BuildInfo(
        branch="main",
        build="build-forwarding-integration",
        flavor="release",
        release="1.0.0",
        url="https://ci.example.com/build/forwarding"
    )

    pipeline_info = PipelineInfo(
        id="pipeline-forwarding",
        name="Forwarding Pipeline",
        instance="instance-forwarding"
    )

    job_info = JobInfo(
        id="job-forwarding",
        name="Forwarding Tests",
        type="IntegrationTest",
        owner="QA Team",
        label="forwarding",
        initiator="test@example.com",
        venue="test",
        seed="forwarding-seed",
        tag="forwarding-tag"
    )

    recorder = JsonResultRecorder(
        runid=runid,
        start=start_time,
        render_info=render_info,
        build_info=build_info,
        pipeline_info=pipeline_info,
        job_info=job_info
    )

    # Use port 0 to let OS assign available ports
    concentrator_address = ("127.0.0.1", 0)
    external_service_address = ("127.0.0.1", 0)

    env = {
        "temp_dir": temp_dir,
        "render_info": render_info,
        "runid": runid,
        "start_time": start_time,
        "build_info": build_info,
        "pipeline_info": pipeline_info,
        "job_info": job_info,
        "recorder": recorder,
        "concentrator_address": concentrator_address,
        "external_service_address": external_service_address,
        "concentrator_server": None,
        "external_service": None
    }
    return env


def _cleanup_env(env: dict) -> None:
    """
        Clean up the per-test fixtures, mirroring the original ``tearDown``.

        :param env: The mapping of fixture objects returned by ``_establish_env``.
    """
    concentrator_server = env["concentrator_server"]
    if concentrator_server is not None:
        try:
            concentrator_server._forwarding_running = False
            concentrator_server.shutdown()
            concentrator_server.server_close()
            if hasattr(concentrator_server, '_forward_thread') and concentrator_server._forward_thread is not None:
                try:
                    concentrator_server._forward_thread.join(timeout=2.0)
                except Exception:
                    pass
        except Exception:
            pass

    external_service = env["external_service"]
    if external_service is not None:
        try:
            external_service.stop()
        except Exception:
            pass

    temp_dir = env["temp_dir"]
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    return


def _start_external_service(env: dict) -> str:
    """
        Start the mock external service and return its URL, mirroring the
        original ``_start_external_service`` helper.

        :param env: The mapping of fixture objects returned by ``_establish_env``.

        :returns: The URL of the started mock external service.
    """
    external_service = MockExternalService(env["external_service_address"])
    external_service.start()
    env["external_service"] = external_service
    actual_port = external_service.server_address[1]
    rtnval = f"http://127.0.0.1:{actual_port}/api/progress"
    return rtnval


def _start_concentrator_with_forwarding(env: dict, forwarding_url: str, forwarding_interval: float = 0.1,
                                        forwarding_headers=None) -> int:
    """
        Start the concentrator server with forwarding configured, mirroring the
        original ``_start_concentrator_with_forwarding`` helper.

        :param env: The mapping of fixture objects returned by ``_establish_env``.
        :param forwarding_url: The URL to which summaries are forwarded.
        :param forwarding_interval: The interval between forwarding cycles.
        :param forwarding_headers: Optional custom headers for forwarding.

        :returns: The port the concentrator server is listening on.
    """
    forwarding_info = ForwardingInfo(
        forwarding_interval=forwarding_interval,
        forwarding_url=forwarding_url,
        forwarding_headers=forwarding_headers
    )

    concentrator_server = ProgressConcentratorServer(
        recorder=env["recorder"],
        server_address=env["concentrator_address"],
        forwarding_info=forwarding_info
    )
    concentrator_server.start()
    env["concentrator_server"] = concentrator_server
    rtnval = concentrator_server.server_address[1]
    return rtnval


def _create_progress_payload(task_id: str, worker_id: str,
                             status: str, position: str = "5") -> dict:
    """
        Create a progress update payload for HTTP POST, mirroring the original
        ``_create_progress_payload`` helper.

        :param task_id: The task identifier.
        :param worker_id: The worker identifier.
        :param status: The status value for the progress update.
        :param position: The position value for the progress update.

        :returns: The progress update payload dictionary.
    """
    rtnval = {
        "id": task_id,
        "category": "test-execution",
        "moniker": f"test_module.test_{task_id}",
        "ptype": "Sequential",
        "range_min": "0",
        "range_max": "10",
        "position": position,
        "status": status,
        "when": datetime.now().isoformat(),
        "data": {"worker_id": worker_id}
    }
    return rtnval


def _send_progress_update(port: int, payload: dict) -> int:
    """
        Send a progress update via HTTP POST and return the status code,
        mirroring the original ``_send_progress_update`` helper.

        :param port: The port the concentrator server is listening on.
        :param payload: The progress update payload to send.

        :returns: The HTTP status code of the response.
    """
    conn = http.client.HTTPConnection("127.0.0.1", port)
    try:
        body = json.dumps(payload)
        headers = {"Content-Type": "application/json", "Content-Length": str(len(body))}
        conn.request("POST", "/progress", body=body, headers=headers)
        response = conn.getresponse()
        rtnval = response.status
        return rtnval
    finally:
        conn.close()


def test_summary_forwarded_at_configured_interval() -> None:
    """
        Test that summaries are forwarded at the configured interval (Requirement 9.4).
    """
    env = _establish_env()
    try:
        forwarding_url = _start_external_service(env=env)
        forwarding_interval = 0.15

        _start_concentrator_with_forwarding(
            env=env,
            forwarding_url=forwarding_url,
            forwarding_interval=forwarding_interval
        )

        # Wait for multiple forwarding cycles
        time.sleep(forwarding_interval * 4 + 0.1)

        received = env["external_service"].get_received_summaries()

        # Should have received at least 3 summaries
        assert len(received) >= 3, f"Expected at least 3 summaries, got {len(received)}"

        # Verify timing between summaries is approximately the configured interval
        if len(received) >= 2:
            for i in range(1, len(received)):
                interval = received[i]['timestamp'] - received[i-1]['timestamp']
                # Allow 50% tolerance for timing variations
                assert interval >= forwarding_interval * 0.5, f"Interval {interval} too short, expected ~{forwarding_interval}"
                assert interval <= forwarding_interval * 2.0, f"Interval {interval} too long, expected ~{forwarding_interval}"
    finally:
        _cleanup_env(env=env)
    return


def test_forwarding_continues_while_server_running() -> None:
    """
        Test that forwarding continues while the server is running (Requirement 9.1).
    """
    env = _establish_env()
    try:
        forwarding_url = _start_external_service(env=env)
        forwarding_interval = 0.1

        _start_concentrator_with_forwarding(
            env=env,
            forwarding_url=forwarding_url,
            forwarding_interval=forwarding_interval
        )

        # Verify forwarding is running
        assert env["concentrator_server"]._forwarding_running

        # Wait and collect summaries
        time.sleep(0.35)
        first_count = len(env["external_service"].get_received_summaries())

        # Wait more and verify more summaries arrive
        time.sleep(0.35)
        second_count = len(env["external_service"].get_received_summaries())

        assert second_count > first_count, "Forwarding should continue sending summaries"
    finally:
        _cleanup_env(env=env)
    return


def test_summary_contains_current_recorder_state() -> None:
    """
        Test that forwarded summary contains current recorder state (Requirement 9.2).
    """
    env = _establish_env()
    try:
        forwarding_url = _start_external_service(env=env)

        concentrator_port = _start_concentrator_with_forwarding(
            env=env,
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )

        # Add some progress updates
        for i in range(3):
            payload = _create_progress_payload(
                task_id=f"state-task-{i}",
                worker_id="state-worker",
                status="Running",
                position=str(i)
            )
            _send_progress_update(port=concentrator_port, payload=payload)

        # Wait for forwarding to occur
        time.sleep(0.25)

        received = env["external_service"].get_received_summaries()
        assert len(received) > 0

        # Find a summary that contains our tasks
        found_tasks = False
        for entry in received:
            summary = entry['summary']
            running = summary.get('running', {})
            if all(f"state-task-{i}" in running for i in range(3)):
                found_tasks = True
                break

        assert found_tasks, "Forwarded summary should contain the current running tasks"
    finally:
        _cleanup_env(env=env)
    return


def test_summary_posted_to_external_service() -> None:
    """
        Test that summary is POSTed to the external service URL (Requirement 9.3).
    """
    env = _establish_env()
    try:
        forwarding_url = _start_external_service(env=env)

        _start_concentrator_with_forwarding(
            env=env,
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )

        # Wait for at least one forwarding cycle
        time.sleep(0.25)

        received = env["external_service"].get_received_summaries()

        assert len(received) > 0, "External service should receive at least one summary"
    finally:
        _cleanup_env(env=env)
    return


def test_summary_json_structure_is_valid() -> None:
    """
        Test that the forwarded summary has valid JSON structure.
    """
    env = _establish_env()
    try:
        forwarding_url = _start_external_service(env=env)

        _start_concentrator_with_forwarding(
            env=env,
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )

        # Wait for forwarding
        time.sleep(0.25)

        received = env["external_service"].get_received_summaries()
        assert len(received) > 0

        summary = received[0]['summary']

        # Verify expected summary fields
        assert 'version' in summary
        assert 'runid' in summary
        assert 'running' in summary
        assert summary['runid'] == env["runid"]
    finally:
        _cleanup_env(env=env)
    return


def test_summary_includes_build_info() -> None:
    """
        Test that forwarded summary includes build information.
    """
    env = _establish_env()
    try:
        forwarding_url = _start_external_service(env=env)

        _start_concentrator_with_forwarding(
            env=env,
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )

        time.sleep(0.25)

        received = env["external_service"].get_received_summaries()
        assert len(received) > 0

        summary = received[0]['summary']

        # Verify build info is present
        assert 'build' in summary
        build = summary['build']
        assert build['branch'] == 'main'
        assert build['build'] == 'build-forwarding-integration'
    finally:
        _cleanup_env(env=env)
    return


def test_summary_includes_job_info() -> None:
    """
        Test that forwarded summary includes job information.
    """
    env = _establish_env()
    try:
        forwarding_url = _start_external_service(env=env)

        _start_concentrator_with_forwarding(
            env=env,
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )

        time.sleep(0.25)

        received = env["external_service"].get_received_summaries()
        assert len(received) > 0

        summary = received[0]['summary']

        # Verify job info is present
        assert 'job' in summary
        job = summary['job']
        assert job['name'] == 'Forwarding Tests'
        assert job['type'] == 'IntegrationTest'
    finally:
        _cleanup_env(env=env)
    return


def test_running_tasks_reflected_in_forwarded_summary() -> None:
    """
        Test that running tasks are reflected in forwarded summaries.
    """
    env = _establish_env()
    try:
        forwarding_url = _start_external_service(env=env)

        concentrator_port = _start_concentrator_with_forwarding(
            env=env,
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )

        # Add running tasks
        task_ids = []
        for i in range(5):
            task_id = f"running-task-{i}"
            task_ids.append(task_id)
            payload = _create_progress_payload(
                task_id=task_id,
                worker_id="integration-worker",
                status="Running",
                position=str(i * 2)
            )
            _send_progress_update(port=concentrator_port, payload=payload)

        # Wait for forwarding
        time.sleep(0.25)

        received = env["external_service"].get_received_summaries()

        # Find a summary with our tasks
        found_all_tasks = False
        for entry in received:
            running = entry['summary'].get('running', {})
            if all(tid in running for tid in task_ids):
                found_all_tasks = True
                # Verify task details
                for i, tid in enumerate(task_ids):
                    assert running[tid]['position'] == str(i * 2)
                break

        assert found_all_tasks, "All running tasks should be in forwarded summary"
    finally:
        _cleanup_env(env=env)
    return


def test_completed_tasks_removed_from_forwarded_summary() -> None:
    """
        Test that completed tasks are removed from forwarded summaries.
    """
    env = _establish_env()
    try:
        forwarding_url = _start_external_service(env=env)

        concentrator_port = _start_concentrator_with_forwarding(
            env=env,
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )

        # Add a running task
        task_id = "complete-test-task"
        payload = _create_progress_payload(
            task_id=task_id,
            worker_id="integration-worker",
            status="Running"
        )
        _send_progress_update(port=concentrator_port, payload=payload)

        # Wait for forwarding
        time.sleep(0.15)

        # Complete the task
        payload = _create_progress_payload(
            task_id=task_id,
            worker_id="integration-worker",
            status="Completed"
        )
        _send_progress_update(port=concentrator_port, payload=payload)

        # Clear previous summaries and wait for new ones
        env["external_service"].clear_received_summaries()
        time.sleep(0.25)

        received = env["external_service"].get_received_summaries()
        assert len(received) > 0

        # Verify task is not in the latest summary
        latest_summary = received[-1]['summary']
        running = latest_summary.get('running', {})
        assert task_id not in running, "Completed task should not be in forwarded summary"
    finally:
        _cleanup_env(env=env)
    return


def test_content_type_header_propagated() -> None:
    """
        Test that Content-Type: application/json header is propagated (Requirement 9.5).
    """
    env = _establish_env()
    try:
        forwarding_url = _start_external_service(env=env)

        _start_concentrator_with_forwarding(
            env=env,
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )

        # Wait for forwarding
        time.sleep(0.25)

        received = env["external_service"].get_received_summaries()
        assert len(received) > 0

        headers = received[0]['headers']

        # Verify Content-Type header
        assert 'Content-Type' in headers
        assert headers['Content-Type'] == 'application/json'
    finally:
        _cleanup_env(env=env)
    return


def test_custom_headers_propagated() -> None:
    """
        Test that custom forwarding headers are propagated (Requirement 9.6).
    """
    env = _establish_env()
    try:
        forwarding_url = _start_external_service(env=env)

        custom_headers = {
            "Authorization": "Bearer integration-test-token",
            "X-Job-Id": "job-integration-123",
            "X-Custom-Header": "custom-value"
        }

        _start_concentrator_with_forwarding(
            env=env,
            forwarding_url=forwarding_url,
            forwarding_interval=0.1,
            forwarding_headers=custom_headers
        )

        # Wait for forwarding
        time.sleep(0.25)

        received = env["external_service"].get_received_summaries()
        assert len(received) > 0

        headers = received[0]['headers']

        # Verify custom headers are present
        assert 'Authorization' in headers
        assert headers['Authorization'] == 'Bearer integration-test-token'

        assert 'X-Job-Id' in headers
        assert headers['X-Job-Id'] == 'job-integration-123'

        assert 'X-Custom-Header' in headers
        assert headers['X-Custom-Header'] == 'custom-value'
    finally:
        _cleanup_env(env=env)
    return


def test_custom_headers_merged_with_default_content_type() -> None:
    """
        Test that custom headers are merged with default Content-Type header.
    """
    env = _establish_env()
    try:
        forwarding_url = _start_external_service(env=env)

        custom_headers = {
            "Authorization": "Bearer merge-test-token"
        }

        _start_concentrator_with_forwarding(
            env=env,
            forwarding_url=forwarding_url,
            forwarding_interval=0.1,
            forwarding_headers=custom_headers
        )

        # Wait for forwarding
        time.sleep(0.25)

        received = env["external_service"].get_received_summaries()
        assert len(received) > 0

        headers = received[0]['headers']

        # Verify both default and custom headers are present
        assert 'Content-Type' in headers
        assert headers['Content-Type'] == 'application/json'

        assert 'Authorization' in headers
        assert headers['Authorization'] == 'Bearer merge-test-token'
    finally:
        _cleanup_env(env=env)
    return


def test_headers_consistent_across_multiple_forwards() -> None:
    """
        Test that headers are consistent across multiple forwarding cycles.
    """
    env = _establish_env()
    try:
        forwarding_url = _start_external_service(env=env)

        custom_headers = {
            "X-Consistent-Header": "consistent-value"
        }

        _start_concentrator_with_forwarding(
            env=env,
            forwarding_url=forwarding_url,
            forwarding_interval=0.1,
            forwarding_headers=custom_headers
        )

        # Wait for multiple forwarding cycles
        time.sleep(0.45)

        received = env["external_service"].get_received_summaries()
        assert len(received) >= 3

        # Verify headers are consistent across all received summaries
        for entry in received:
            headers = entry['headers']
            assert 'Content-Type' in headers
            assert headers['Content-Type'] == 'application/json'
            assert 'X-Consistent-Header' in headers
            assert headers['X-Consistent-Header'] == 'consistent-value'
    finally:
        _cleanup_env(env=env)
    return


def test_no_custom_headers_only_default_content_type() -> None:
    """
        Test that only default Content-Type is sent when no custom headers configured.
    """
    env = _establish_env()
    try:
        forwarding_url = _start_external_service(env=env)

        _start_concentrator_with_forwarding(
            env=env,
            forwarding_url=forwarding_url,
            forwarding_interval=0.1,
            forwarding_headers=None
        )

        # Wait for forwarding
        time.sleep(0.25)

        received = env["external_service"].get_received_summaries()
        assert len(received) > 0

        headers = received[0]['headers']

        # Verify Content-Type is present
        assert 'Content-Type' in headers
        assert headers['Content-Type'] == 'application/json'
    finally:
        _cleanup_env(env=env)
    return
