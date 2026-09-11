"""
    .. module:: ccai.tests.singlehost.integrationruntime.results.concentrators.test_progress_forwarding_integration
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Integration tests for progress forwarding functionality.

    This module contains integration tests that verify the complete flow of:
    1. Remote task progress reception via HTTP POST
    2. Summary forwarding to external services

    These tests validate Requirements 40.1-40.6 for the progress forwarding thread.

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
import socket
import concurrent.futures

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

from ccai.waiting import wait_for_it

# Bounded-wait parameters used when polling for work done by the concentrator's background
# threads. The timeout is generous so slow or coarse-clock runners (Windows and macOS CI)
# never fail on scheduling latency, while the short polling interval keeps fast runners fast.
WAIT_TIMEOUT = 5.0
WAIT_INTERVAL = 0.02


class MockExternalServiceHandler(BaseHTTPRequestHandler):
    """Handler for mock external monitoring service that receives forwarded summaries."""

    def do_POST(self):
        """Handle POST requests containing forwarded summaries."""
        content_length = int(self.headers.get('Content-Length', 0))

        if content_length > 0:
            body = self.rfile.read(content_length)
            try:
                summary = json.loads(body)

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
        # No start-up pause is needed: the listening socket was bound and activated in the
        # constructor, so connections are queued for serve_forever() from that point on.

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


class ProgressForwardingTestEnv:
    """
        Mutable per-test environment holder that replaces the unittest ``TestCase``
        instance state. It carries the fixtures established by ``_establish_env`` and
        the servers that the tests stand up so that ``_cleanup_env`` can tear them down.
    """

    def __init__(self) -> None:
        """
            Initializes all per-test fixture slots to their starting values.
        """
        self.temp_dir = None
        self.render_info = None
        self.runid = None
        self.start_time = None
        self.build_info = None
        self.pipeline_info = None
        self.job_info = None
        self.recorder = None
        self.concentrator_address = None
        self.external_service_address = None
        self.concentrator_server = None
        self.external_service = None
        return


def _establish_env() -> ProgressForwardingTestEnv:
    """
        Replicates the original ``setUp`` for each test by building all the fixtures
        the tests depend on and packaging them into a :class:`ProgressForwardingTestEnv`.

        :returns: A fully populated per-test environment holder.
    """
    env = ProgressForwardingTestEnv()

    env.temp_dir = tempfile.mkdtemp()

    env.render_info = RenderInfo(
        title="Progress Forwarding Integration Test",
        summary_filename=os.path.join(env.temp_dir, "summary.json"),
        summary_template=os.path.join(env.temp_dir, "template.html"),
        stream_results_filename=os.path.join(env.temp_dir, "results.json"),
        consolidated_results_filename=os.path.join(env.temp_dir, "consolidated.json"),
        static_resource_source=None,
        static_resource_destination=env.temp_dir
    )

    with open(env.render_info.summary_template, 'w') as f:
        f.write("<html></html>")

    env.runid = str(uuid.uuid4())
    env.start_time = datetime.now()

    env.build_info = BuildInfo(
        branch="main",
        build="build-progress-forwarding",
        flavor="release",
        release="1.0.0",
        url="https://ci.example.com/build/progress-forwarding"
    )

    env.pipeline_info = PipelineInfo(
        id="pipeline-progress-forwarding",
        name="Progress Forwarding Pipeline",
        instance="instance-progress-forwarding"
    )

    env.job_info = JobInfo(
        id="job-progress-forwarding",
        name="Progress Forwarding Tests",
        type="IntegrationTest",
        owner="QA Team",
        label="progress-forwarding",
        initiator="test@example.com",
        venue="test",
        seed="progress-forwarding-seed",
        tag="progress-forwarding-tag"
    )

    env.recorder = JsonResultRecorder(
        runid=env.runid,
        start=env.start_time,
        render_info=env.render_info,
        build_info=env.build_info,
        pipeline_info=env.pipeline_info,
        job_info=env.job_info
    )

    env.concentrator_address = ("127.0.0.1", 0)
    env.external_service_address = ("127.0.0.1", 0)

    env.concentrator_server = None
    env.external_service = None

    return env


def _cleanup_env(env: ProgressForwardingTestEnv) -> None:
    """
        Replicates the original ``tearDown`` for each test by shutting down the
        concentrator server and the external service and removing the temp directory.

        :param env: The per-test environment holder to clean up.
    """
    if env.concentrator_server is not None:
        try:
            env.concentrator_server._forwarding_running = False
            env.concentrator_server.shutdown()
            env.concentrator_server.server_close()
            if hasattr(env.concentrator_server, '_forward_thread') and env.concentrator_server._forward_thread is not None:
                try:
                    env.concentrator_server._forward_thread.join(timeout=2.0)
                except Exception:
                    pass
        except Exception:
            pass

    if env.external_service is not None:
        try:
            env.external_service.stop()
        except Exception:
            pass

    if os.path.exists(env.temp_dir):
        shutil.rmtree(env.temp_dir)

    return


def _start_external_service(env: ProgressForwardingTestEnv) -> str:
    """
        Start the mock external service and return its URL.

        :param env: The per-test environment holder.

        :returns: The forwarding URL for the started external service.
    """
    env.external_service = MockExternalService(env.external_service_address)
    env.external_service.start()
    actual_port = env.external_service.server_address[1]
    rtnval = f"http://127.0.0.1:{actual_port}/api/progress"
    return rtnval


def _start_concentrator_with_forwarding(env: ProgressForwardingTestEnv, forwarding_url: str,
                                        forwarding_interval: float = 0.1,
                                        forwarding_headers: dict = None) -> int:
    """
        Start the concentrator server with forwarding configured.

        :param env: The per-test environment holder.
        :param forwarding_url: The URL the concentrator forwards summaries to.
        :param forwarding_interval: The interval between forwarding posts.
        :param forwarding_headers: Optional custom headers for the forwarding posts.

        :returns: The port the concentrator server is bound to.
    """
    forwarding_info = ForwardingInfo(
        forwarding_interval=forwarding_interval,
        forwarding_url=forwarding_url,
        forwarding_headers=forwarding_headers
    )

    env.concentrator_server = ProgressConcentratorServer(
        recorder=env.recorder,
        server_address=env.concentrator_address,
        forwarding_info=forwarding_info
    )
    env.concentrator_server.start()
    rtnval = env.concentrator_server.server_address[1]
    return rtnval


def _create_progress_payload(task_id: str, worker_id: str,
                             status: str, position: str = "5") -> dict:
    """
        Create a progress update payload for HTTP POST.

        :param task_id: The identifier for the task.
        :param worker_id: The identifier for the worker submitting progress.
        :param status: The task status string.
        :param position: The current position within the task range.

        :returns: A dictionary representing the progress update payload.
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
        Send a progress update via HTTP POST and return the status code.

        :param port: The concentrator server port to send the update to.
        :param payload: The progress update payload to send.

        :returns: The HTTP status code returned by the concentrator.
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


def _find_unused_port() -> int:
    """
        Find an unused port for testing.

        :returns: A port number that is currently unused.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        rtnval = s.getsockname()[1]
        return rtnval


def _received_summary_count(env: ProgressForwardingTestEnv) -> int:
    """
        Return the number of summaries the mock external service has received so far.

        :param env: The per-test environment holder.

        :returns: The count of forwarded summaries received.
    """
    rtnval = len(env.external_service.get_received_summaries())
    return rtnval


def _wait_for_summaries(env: ProgressForwardingTestEnv, minimum: int = 1) -> None:
    """
        Wait, with a bounded timeout, until the mock external service has received at least
        ``minimum`` forwarded summaries.

        :param env: The per-test environment holder.
        :param minimum: The minimum number of summaries that must have been received.
    """
    wait_for_it(lambda wctx: _received_summary_count(env) >= minimum,
                what_for=f"at least {minimum} forwarded summaries to be received",
                interval=WAIT_INTERVAL, timeout=WAIT_TIMEOUT)
    return


def _wait_for_fresh_summary(env: ProgressForwardingTestEnv) -> None:
    """
        Wait, with a bounded timeout, until the mock external service has received a summary
        whose snapshot was taken *after* this call was made.

        The forwarder may already have snapshotted a summary (but not yet delivered it) at the
        moment this function is called, so the next summary to arrive can be stale. The summary
        after that is only snapshotted once the stale one has been delivered, so it necessarily
        reflects every recorder update made before this call. Waiting for two more summaries
        than are currently recorded therefore guarantees that the most recent summary is fresh.

        :param env: The per-test environment holder.
    """
    baseline = _received_summary_count(env)
    wait_for_it(lambda wctx: _received_summary_count(env) >= baseline + 2,
                what_for="a forwarded summary snapshotted after the latest progress update",
                interval=WAIT_INTERVAL, timeout=WAIT_TIMEOUT)
    return


def _wait_for_failed_forwarding_attempts(env: ProgressForwardingTestEnv, minimum: int = 2) -> None:
    """
        Wait, with a bounded timeout, until the running concentrator has logged at least
        ``minimum`` connection-error warnings from its forwarding thread, counted from the
        moment this function is called.

        :param env: The per-test environment holder whose concentrator server is running.
        :param minimum: The minimum number of failed forwarding attempts to wait for.
    """
    failed_attempts = []
    original_warning = env.concentrator_server._logger.warning

    def count_failure(msg):
        failed_attempts.append(msg)
        original_warning(msg)

    env.concentrator_server._logger.warning = count_failure
    try:
        wait_for_it(lambda wctx: len(failed_attempts) >= minimum,
                    what_for=f"at least {minimum} failed forwarding attempts",
                    interval=WAIT_INTERVAL, timeout=WAIT_TIMEOUT)
    finally:
        env.concentrator_server._logger.warning = original_warning
    return


def test_remote_worker_progress_received_and_forwarded() -> None:
    """
        Test that progress from remote workers is received and forwarded to external service.

        This test validates the complete flow:
        1. Remote worker sends progress update to concentrator (Req 39.1-39.6)
        2. Concentrator aggregates progress in recorder (Req 39.5)
        3. Forwarding thread sends summary to external service (Req 40.2, 40.3)

        Requirements: 39.1-39.6, 40.2, 40.3
    """
    env = _establish_env()
    try:
        forwarding_url = _start_external_service(env=env)
        concentrator_port = _start_concentrator_with_forwarding(
            env=env,
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )

        # Simulate remote worker sending progress updates
        task_id = "remote-worker-task-1"
        worker_id = "remote-worker-001"

        payload = _create_progress_payload(
            task_id=task_id,
            worker_id=worker_id,
            status="Running",
            position="3"
        )

        status_code = _send_progress_update(port=concentrator_port, payload=payload)
        assert status_code == 200, "Progress update should be accepted"

        # Wait for a summary snapshotted after the update to be forwarded
        _wait_for_fresh_summary(env=env)

        # Verify progress was forwarded to external service
        received = env.external_service.get_received_summaries()
        assert len(received) > 0, "External service should receive forwarded summaries"

        # Find a summary containing our task
        found_task = False
        for entry in received:
            running = entry['summary'].get('running', {})
            if task_id in running:
                found_task = True
                assert running[task_id]['position'] == "3"
                assert running[task_id]['status'] == "Running"
                break

        assert found_task, "Remote worker's task should appear in forwarded summary"
    finally:
        _cleanup_env(env=env)
    return


def test_multiple_remote_workers_progress_aggregated() -> None:
    """
        Test that progress from multiple remote workers is aggregated and forwarded.

        Requirements: 39.5, 40.2, 40.3
    """
    env = _establish_env()
    try:
        forwarding_url = _start_external_service(env=env)
        concentrator_port = _start_concentrator_with_forwarding(
            env=env,
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )

        # Simulate multiple remote workers
        num_workers = 5
        worker_tasks = {}

        for i in range(num_workers):
            task_id = f"multi-worker-task-{i}"
            worker_id = f"remote-worker-{i:03d}"
            worker_tasks[task_id] = worker_id

            payload = _create_progress_payload(
                task_id=task_id,
                worker_id=worker_id,
                status="Running",
                position=str(i * 2)
            )

            status_code = _send_progress_update(port=concentrator_port, payload=payload)
            assert status_code == 200

        # Wait for a summary snapshotted after the updates to be forwarded
        _wait_for_fresh_summary(env=env)

        # Verify all workers' progress is in forwarded summary
        received = env.external_service.get_received_summaries()
        assert len(received) > 0

        # Find a summary with all tasks
        found_all = False
        for entry in received:
            running = entry['summary'].get('running', {})
            if all(tid in running for tid in worker_tasks.keys()):
                found_all = True
                # Verify each task's data
                for i, (task_id, worker_id) in enumerate(worker_tasks.items()):
                    assert running[task_id]['position'] == str(i * 2)
                break

        assert found_all, "All remote workers' tasks should be in forwarded summary"
    finally:
        _cleanup_env(env=env)
    return


def test_concurrent_remote_workers_progress_reception() -> None:
    """
        Test concurrent progress reception from multiple remote workers.

        Requirements: 39.1-39.6, 40.2, 40.3
    """
    env = _establish_env()
    try:
        forwarding_url = _start_external_service(env=env)
        concentrator_port = _start_concentrator_with_forwarding(
            env=env,
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )

        num_workers = 10
        updates_per_worker = 5
        results = []
        errors = []
        lock = threading.Lock()

        def simulate_remote_worker(worker_num: int):
            """Simulate a remote worker sending progress updates."""
            worker_results = []
            for i in range(updates_per_worker):
                task_id = f"concurrent-task-{worker_num}-{i}"
                payload = _create_progress_payload(
                    task_id=task_id,
                    worker_id=f"concurrent-worker-{worker_num}",
                    status="Running",
                    position=str(i)
                )
                try:
                    status_code = _send_progress_update(port=concentrator_port, payload=payload)
                    worker_results.append((task_id, status_code))
                except Exception as e:
                    with lock:
                        errors.append((worker_num, i, str(e)))
            return worker_results

        # Execute workers concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(simulate_remote_worker, w) for w in range(num_workers)]
            for future in concurrent.futures.as_completed(futures):
                results.extend(future.result())

        # Verify no errors
        assert len(errors) == 0, f"Errors during concurrent reception: {errors}"

        # Verify all updates succeeded
        assert len(results) == num_workers * updates_per_worker
        for task_id, status_code in results:
            assert status_code == 200, f"Task {task_id} should succeed"

        # Wait for forwarding
        _wait_for_summaries(env=env)

        # Verify external service received summaries
        received = env.external_service.get_received_summaries()
        assert len(received) > 0, "External service should receive forwarded summaries"
    finally:
        _cleanup_env(env=env)
    return


def test_forwarding_thread_is_daemon() -> None:
    """
        Test that the forwarding thread runs as a daemon thread.

        Requirement: 40.1 - THE forwarding thread SHALL run as a daemon thread
    """
    env = _establish_env()
    try:
        forwarding_url = _start_external_service(env=env)
        _start_concentrator_with_forwarding(
            env=env,
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )

        # Verify forwarding thread is a daemon
        assert env.concentrator_server._forward_thread is not None
        assert env.concentrator_server._forward_thread.daemon, \
            "Forwarding thread should be a daemon thread"
    finally:
        _cleanup_env(env=env)
    return


def test_server_thread_is_daemon() -> None:
    """
        Test that the server thread also runs as a daemon thread.

        Requirement: 40.1 (related)
    """
    env = _establish_env()
    try:
        forwarding_url = _start_external_service(env=env)
        _start_concentrator_with_forwarding(
            env=env,
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )

        # Verify server thread is a daemon
        assert env.concentrator_server._server_thread is not None
        assert env.concentrator_server._server_thread.daemon, \
            "Server thread should be a daemon thread"
    finally:
        _cleanup_env(env=env)
    return


def test_forwarding_uses_configured_interval() -> None:
    """
        Test that forwarding uses the configured interval between posts.

        Requirement: 40.4 - THE forwarding thread SHALL use the configured
        forwarding_interval between posts
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
        _wait_for_summaries(env=env, minimum=4)

        received = env.external_service.get_received_summaries()

        # Should have received at least 4 summaries
        assert len(received) >= 4, \
            f"Expected at least 4 summaries, got {len(received)}"

        # Verify timing between summaries
        if len(received) >= 2:
            for i in range(1, len(received)):
                interval = received[i]['timestamp'] - received[i-1]['timestamp']
                # Allow 50% tolerance for timing variations
                assert interval >= forwarding_interval * 0.5, \
                    f"Interval {interval} too short, expected ~{forwarding_interval}"
                assert interval <= forwarding_interval * 2.0, \
                    f"Interval {interval} too long, expected ~{forwarding_interval}"
    finally:
        _cleanup_env(env=env)
    return


def test_different_forwarding_intervals() -> None:
    """
        Test that different forwarding intervals work correctly.

        Requirement: 40.4
    """
    env = _establish_env()
    try:
        forwarding_url = _start_external_service(env=env)

        # Test with a shorter interval
        short_interval = 0.08
        _start_concentrator_with_forwarding(
            env=env,
            forwarding_url=forwarding_url,
            forwarding_interval=short_interval
        )

        # Wait for multiple forwarding cycles
        _wait_for_summaries(env=env, minimum=4)

        received = env.external_service.get_received_summaries()

        # With a 0.08s interval, at least 4 summaries arrive well within the wait timeout
        assert len(received) >= 4, \
            f"Expected at least 4 summaries with short interval, got {len(received)}"
    finally:
        _cleanup_env(env=env)
    return


def test_forwarding_includes_custom_headers() -> None:
    """
        Test that forwarding includes configured custom headers.

        Requirement: 40.5 - THE forwarding thread SHALL include forwarding_headers
        in the POST request if configured
    """
    env = _establish_env()
    try:
        forwarding_url = _start_external_service(env=env)

        custom_headers = {
            "Authorization": "Bearer test-token-12345",
            "X-Correlation-Id": "correlation-abc-123",
            "X-Worker-Pool": "integration-test-pool"
        }

        _start_concentrator_with_forwarding(
            env=env,
            forwarding_url=forwarding_url,
            forwarding_interval=0.1,
            forwarding_headers=custom_headers
        )

        _wait_for_summaries(env=env)

        received = env.external_service.get_received_summaries()
        assert len(received) > 0

        headers = received[0]['headers']

        # Verify all custom headers are present
        for key, value in custom_headers.items():
            assert key in headers, f"Header {key} should be present"
            assert headers[key] == value, f"Header {key} should have correct value"
    finally:
        _cleanup_env(env=env)
    return


def test_forwarding_includes_content_type_header() -> None:
    """
        Test that forwarding always includes Content-Type header.

        Requirement: 40.5 (implicit - JSON content type)
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

        _wait_for_summaries(env=env)

        received = env.external_service.get_received_summaries()
        assert len(received) > 0

        headers = received[0]['headers']
        assert 'Content-Type' in headers
        assert headers['Content-Type'] == 'application/json'
    finally:
        _cleanup_env(env=env)
    return


def test_forwarding_continues_after_network_error() -> None:
    """
        Test that forwarding continues after network errors.

        Requirement: 40.6 - THE forwarding thread SHALL log errors and continue on failure
    """
    env = _establish_env()
    try:
        # Use a port that nothing is listening on
        unused_port = _find_unused_port()
        forwarding_url = f"http://127.0.0.1:{unused_port}/api/progress"

        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url=forwarding_url,
            forwarding_headers=None
        )

        env.concentrator_server = ProgressConcentratorServer(
            recorder=env.recorder,
            server_address=env.concentrator_address,
            forwarding_info=forwarding_info
        )
        env.concentrator_server.start()

        # Wait for multiple failed forwarding attempts
        _wait_for_failed_forwarding_attempts(env=env)

        # Verify forwarding thread is still running
        assert env.concentrator_server._forwarding_running, \
            "Forwarding should still be running after errors"
        assert env.concentrator_server._forward_thread.is_alive(), \
            "Forwarding thread should still be alive after errors"
    finally:
        _cleanup_env(env=env)
    return


def test_forwarding_logs_errors() -> None:
    """
        Test that forwarding errors are logged.

        Requirement: 40.6 - THE forwarding thread SHALL log errors
    """
    env = _establish_env()
    try:
        unused_port = _find_unused_port()
        forwarding_url = f"http://127.0.0.1:{unused_port}/api/progress"

        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url=forwarding_url,
            forwarding_headers=None
        )

        env.concentrator_server = ProgressConcentratorServer(
            recorder=env.recorder,
            server_address=env.concentrator_address,
            forwarding_info=forwarding_info
        )

        # Capture logged errors
        logged_errors = []
        original_warning = env.concentrator_server._logger.warning

        def capture_error(msg):
            logged_errors.append(msg)

        env.concentrator_server._logger.warning = capture_error

        try:
            env.concentrator_server.start()

            # Wait for a forwarding attempt to fail and be logged
            wait_for_it(lambda wctx: len(logged_errors) > 0,
                        what_for="a forwarding error to be logged",
                        interval=WAIT_INTERVAL, timeout=WAIT_TIMEOUT)

            # Verify errors were logged
            assert len(logged_errors) > 0, \
                "Forwarding errors should be logged"
        finally:
            env.concentrator_server._logger.warning = original_warning
    finally:
        _cleanup_env(env=env)
    return


def test_progress_reception_unaffected_by_forwarding_errors() -> None:
    """
        Test that progress reception continues during forwarding errors.

        Requirement: 40.6 (related - system stability)
    """
    env = _establish_env()
    try:
        unused_port = _find_unused_port()
        forwarding_url = f"http://127.0.0.1:{unused_port}/api/progress"

        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url=forwarding_url,
            forwarding_headers=None
        )

        env.concentrator_server = ProgressConcentratorServer(
            recorder=env.recorder,
            server_address=env.concentrator_address,
            forwarding_info=forwarding_info
        )
        env.concentrator_server.start()
        concentrator_port = env.concentrator_server.server_address[1]

        # Send progress updates while forwarding is failing
        for i in range(5):
            payload = _create_progress_payload(
                task_id=f"during-error-{i}",
                worker_id="error-test-worker",
                status="Running"
            )
            status_code = _send_progress_update(port=concentrator_port, payload=payload)
            assert status_code == 200, \
                "Progress reception should work during forwarding errors"

        # Verify tasks were recorded
        for i in range(5):
            assert f"during-error-{i}" in env.recorder._running_tasks
    finally:
        _cleanup_env(env=env)
    return


def test_complete_progress_lifecycle_forwarded() -> None:
    """
        Test that complete task lifecycle (start, update, complete) is forwarded.

        Requirements: 39.1-39.6, 40.1-40.6
    """
    env = _establish_env()
    try:
        forwarding_url = _start_external_service(env=env)
        concentrator_port = _start_concentrator_with_forwarding(
            env=env,
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )

        task_id = "lifecycle-task"
        worker_id = "lifecycle-worker"

        # Start task
        start_payload = _create_progress_payload(
            task_id=task_id,
            worker_id=worker_id,
            status="Running",
            position="0"
        )
        _send_progress_update(port=concentrator_port, payload=start_payload)

        # Wait for a summary snapshotted after the start update was recorded
        _wait_for_fresh_summary(env=env)

        # Verify task appears in forwarded summary
        received = env.external_service.get_received_summaries()
        found_running = False
        for entry in received:
            running = entry['summary'].get('running', {})
            if task_id in running and running[task_id]['status'] == "Running":
                found_running = True
                break
        assert found_running, "Running task should appear in forwarded summary"

        # Update task progress
        update_payload = _create_progress_payload(
            task_id=task_id,
            worker_id=worker_id,
            status="Running",
            position="5"
        )
        _send_progress_update(port=concentrator_port, payload=update_payload)

        # Wait for a summary snapshotted after the position update was recorded and
        # verify the update was forwarded
        _wait_for_fresh_summary(env=env)

        received = env.external_service.get_received_summaries()
        running = received[-1]['summary'].get('running', {})
        assert task_id in running and running[task_id]['position'] == "5", \
            "Updated task position should appear in forwarded summary"

        # Complete task
        complete_payload = _create_progress_payload(
            task_id=task_id,
            worker_id=worker_id,
            status="Completed",
            position="10"
        )
        _send_progress_update(port=concentrator_port, payload=complete_payload)

        # Wait for a summary snapshotted after the completion was recorded; only then is
        # the absence of the task in the latest summary a meaningful check
        _wait_for_fresh_summary(env=env)

        # Verify completed task is removed from forwarded summary
        received = env.external_service.get_received_summaries()
        assert len(received) > 0

        latest_summary = received[-1]['summary']
        running = latest_summary.get('running', {})
        assert task_id not in running, \
            "Completed task should not appear in forwarded summary"
    finally:
        _cleanup_env(env=env)
    return


def test_high_volume_progress_forwarding() -> None:
    """
        Test forwarding under high volume of progress updates.

        Requirements: 39.1-39.6, 40.1-40.6
    """
    env = _establish_env()
    try:
        forwarding_url = _start_external_service(env=env)
        concentrator_port = _start_concentrator_with_forwarding(
            env=env,
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )

        num_tasks = 50

        # Send many progress updates rapidly
        for i in range(num_tasks):
            payload = _create_progress_payload(
                task_id=f"high-volume-{i}",
                worker_id=f"worker-{i % 5}",
                status="Running",
                position=str(i)
            )
            status_code = _send_progress_update(port=concentrator_port, payload=payload)
            assert status_code == 200

        # Wait for a summary snapshotted after every update was recorded
        _wait_for_fresh_summary(env=env)

        # Verify external service received summaries
        received = env.external_service.get_received_summaries()
        assert len(received) > 0

        # Verify tasks are in the latest summary
        latest_summary = received[-1]['summary']
        running = latest_summary.get('running', {})

        # Should have all tasks
        assert len(running) == num_tasks, \
            f"Expected {num_tasks} tasks in summary, got {len(running)}"
    finally:
        _cleanup_env(env=env)
    return


def test_summary_metadata_forwarded_correctly() -> None:
    """
        Test that summary metadata is forwarded correctly.

        Requirements: 40.2, 40.3
    """
    env = _establish_env()
    try:
        forwarding_url = _start_external_service(env=env)
        _start_concentrator_with_forwarding(
            env=env,
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )

        _wait_for_summaries(env=env)

        received = env.external_service.get_received_summaries()
        assert len(received) > 0

        summary = received[0]['summary']

        # Verify metadata fields
        assert summary['runid'] == env.runid
        assert 'build' in summary
        assert summary['build']['branch'] == 'main'
        assert summary['build']['build'] == 'build-progress-forwarding'

        assert 'pipeline' in summary
        assert summary['pipeline']['name'] == 'Progress Forwarding Pipeline'

        assert 'job' in summary
        assert summary['job']['name'] == 'Progress Forwarding Tests'
    finally:
        _cleanup_env(env=env)
    return
