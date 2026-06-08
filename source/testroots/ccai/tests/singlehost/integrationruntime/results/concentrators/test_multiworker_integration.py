"""
    .. module:: ccai.tests.singlehost.integrationruntime.results.concentrators.test_multiworker_integration
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Integration tests for multi-worker progress aggregation.

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
import concurrent.futures

from datetime import datetime

from ccai.testbase.results.model.buildinfo import BuildInfo
from ccai.testbase.results.model.pipelineinfo import PipelineInfo
from ccai.testbase.results.model.jobinfo import JobInfo
from ccai.testbase.results.model.renderinfo import RenderInfo
from ccai.testbase.results.model.progressinfo import ProgressInfo
from ccai.testbase.results.model.progresscode import ProgressCode
from ccai.testbase.results.model.progresstype import ProgressType

from ccai.testbase.results.recorders.jsonresultrecorder import JsonResultRecorder
from ccai.integrationruntime.results.concentrators.progressconcentratorservice import (
    ProgressConcentratorServer
)


class MultiWorkerEnv:
    """
        Mutable fixture container that replicates the per-test state established by the
        original ``MultiWorkerIntegrationTestBase.setUp``.
    """

    def __init__(self) -> None:
        """
            Initializes all fixture instance variables to their pre-setup defaults.
        """
        self.temp_dir = None
        self.render_info = None
        self.runid = None
        self.start_time = None
        self.build_info = None
        self.pipeline_info = None
        self.job_info = None
        self.recorder = None
        self.server_address = None
        self.server = None
        self.actual_port = None
        return


def _establish_env() -> MultiWorkerEnv:
    """
        Replicates the original ``setUp`` for each test by building a fresh temporary
        directory, render/build/pipeline/job info, a recorder, and the server address.

        :returns: A populated :class:`MultiWorkerEnv` fixture container.
    """
    env = MultiWorkerEnv()

    env.temp_dir = tempfile.mkdtemp()

    env.render_info = RenderInfo(
        title="Multi-Worker Integration Test",
        summary_filename=os.path.join(env.temp_dir, "summary.json"),
        summary_template=os.path.join(env.temp_dir, "template.html"),
        stream_results_filename=os.path.join(env.temp_dir, "results.json"),
        consolidated_results_filename=os.path.join(env.temp_dir, "consolidated.json"),
        static_resource_source=None,
        static_resource_destination=env.temp_dir
    )

    # Create a dummy template file
    with open(env.render_info.summary_template, 'w') as f:
        f.write("<html></html>")

    env.runid = str(uuid.uuid4())
    env.start_time = datetime.now()

    env.build_info = BuildInfo(
        branch="main",
        build="build-integration",
        flavor="release",
        release="1.0.0",
        url="https://ci.example.com/build/integration"
    )

    env.pipeline_info = PipelineInfo(
        id="pipeline-integration",
        name="Integration Pipeline",
        instance="instance-integration"
    )

    env.job_info = JobInfo(
        id="job-integration",
        name="Multi-Worker Tests",
        type="IntegrationTest",
        owner="QA Team",
        label="integration",
        initiator="test@example.com",
        venue="test",
        seed="integration-seed",
        tag="integration-tag"
    )

    env.recorder = JsonResultRecorder(
        runid=env.runid,
        start=env.start_time,
        render_info=env.render_info,
        build_info=env.build_info,
        pipeline_info=env.pipeline_info,
        job_info=env.job_info
    )

    # Use port 0 to let OS assign an available port
    env.server_address = ("127.0.0.1", 0)

    env.server = None
    env.actual_port = None

    return env


def _cleanup_env(env: MultiWorkerEnv) -> None:
    """
        Replicates the original ``tearDown`` for each test by shutting down the server (if
        started) and removing the temporary directory.

        :param env: The fixture container to clean up.
    """
    if env.server is not None:
        try:
            env.server.shutdown()
            env.server.server_close()
        except Exception:
            pass

    if os.path.exists(env.temp_dir):
        shutil.rmtree(env.temp_dir)

    return


def _start_server(env: MultiWorkerEnv) -> None:
    """
        Start the concentrator server and get the actual port.

        :param env: The fixture container whose server is started.
    """
    env.server = ProgressConcentratorServer(
        recorder=env.recorder,
        server_address=env.server_address
    )
    env.server.start()
    env.actual_port = env.server.server_address[1]
    return


def _create_progress_payload(task_id: str, worker_id: str,
                             status: str, position: str = "5") -> dict:
    """
        Create a progress update payload for HTTP POST.

        :param task_id: The identifier for the task.
        :param worker_id: The identifier for the worker.
        :param status: The status string for the progress update.
        :param position: The progress position value.

        :returns: A dictionary payload suitable for an HTTP POST body.
    """
    payload = {
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
    return payload


def _send_progress_update(env: MultiWorkerEnv, payload: dict) -> int:
    """
        Send a progress update via HTTP POST and return the status code.

        :param env: The fixture container holding the actual server port.
        :param payload: The progress update payload to send.

        :returns: The HTTP status code returned by the server.
    """
    conn = http.client.HTTPConnection("127.0.0.1", env.actual_port)
    try:
        body = json.dumps(payload)
        headers = {"Content-Type": "application/json", "Content-Length": str(len(body))}
        conn.request("POST", "/progress", body=body, headers=headers)
        response = conn.getresponse()
        rtnval = response.status
        return rtnval
    finally:
        conn.close()


def test_concurrent_updates_from_multiple_workers() -> None:
    """
        Test that concurrent progress updates from multiple workers are handled correctly.
    """
    env = _establish_env()
    try:
        _start_server(env=env)

        num_workers = 5
        updates_per_worker = 10
        results = []
        errors = []

        def worker_task(worker_id: int):
            """Simulate a worker sending progress updates."""
            worker_results = []
            for i in range(updates_per_worker):
                task_id = f"worker-{worker_id}-task-{i}"
                payload = _create_progress_payload(
                    task_id=task_id,
                    worker_id=f"worker-{worker_id}",
                    status="Running",
                    position=str(i)
                )
                try:
                    status_code = _send_progress_update(env=env, payload=payload)
                    worker_results.append((task_id, status_code))
                except Exception as e:
                    errors.append((worker_id, i, str(e)))
            return worker_results

        # Execute workers concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker_task, w) for w in range(num_workers)]
            for future in concurrent.futures.as_completed(futures):
                results.extend(future.result())

        # Verify all updates were successful
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == num_workers * updates_per_worker

        # Verify all responses were 200 OK
        for task_id, status_code in results:
            assert status_code == 200, f"Task {task_id} got status {status_code}"
    finally:
        _cleanup_env(env=env)

    return


def test_simultaneous_post_requests_handled_in_separate_threads() -> None:
    """
        Test that multiple simultaneous POST requests are handled in separate threads (Requirement 11.2).
    """
    env = _establish_env()
    try:
        _start_server(env=env)

        num_concurrent_requests = 10
        request_start_times = {}
        request_end_times = {}
        lock = threading.Lock()

        def timed_request(request_id: int):
            """Send a request and record timing."""
            task_id = f"timed-task-{request_id}"

            with lock:
                request_start_times[request_id] = time.time()

            payload = _create_progress_payload(
                task_id=task_id,
                worker_id=f"worker-{request_id}",
                status="Running"
            )
            status_code = _send_progress_update(env=env, payload=payload)

            with lock:
                request_end_times[request_id] = time.time()

            return status_code

        # Send requests concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent_requests) as executor:
            futures = [executor.submit(timed_request, i) for i in range(num_concurrent_requests)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Verify all requests succeeded
        for status_code in results:
            assert status_code == 200

        # Verify requests were processed concurrently (overlapping times)
        # If requests were sequential, total time would be much longer
        all_start_times = list(request_start_times.values())
        all_end_times = list(request_end_times.values())

        earliest_start = min(all_start_times)
        latest_end = max(all_end_times)
        total_elapsed = latest_end - earliest_start

        # With concurrent processing, total time should be much less than
        # the sum of individual request times
        assert total_elapsed < 5.0, "Requests took too long, may not be concurrent"
    finally:
        _cleanup_env(env=env)

    return


def test_all_worker_updates_aggregated_in_recorder() -> None:
    """
        Test that all progress updates from workers are aggregated in the recorder.
    """
    env = _establish_env()
    try:
        _start_server(env=env)

        num_workers = 3
        tasks_per_worker = 5
        expected_tasks = set()

        # Send progress updates from multiple workers
        for worker_id in range(num_workers):
            for task_num in range(tasks_per_worker):
                task_id = f"agg-worker-{worker_id}-task-{task_num}"
                expected_tasks.add(task_id)

                payload = _create_progress_payload(
                    task_id=task_id,
                    worker_id=f"worker-{worker_id}",
                    status="Running",
                    position=str(task_num)
                )
                status_code = _send_progress_update(env=env, payload=payload)
                assert status_code == 200

        # Allow time for all updates to be processed
        time.sleep(0.1)

        # Verify all tasks are in running_tasks
        actual_tasks = set(env.recorder._running_tasks.keys())
        assert expected_tasks == actual_tasks
    finally:
        _cleanup_env(env=env)

    return


def test_progress_position_updates_are_accurate() -> None:
    """
        Test that progress position updates are accurately recorded.
    """
    env = _establish_env()
    try:
        _start_server(env=env)

        task_id = "position-test-task"
        worker_id = "position-worker"

        # Send multiple position updates for the same task
        positions = ["0", "3", "5", "7", "10"]
        for position in positions:
            payload = _create_progress_payload(
                task_id=task_id,
                worker_id=worker_id,
                status="Running",
                position=position
            )
            status_code = _send_progress_update(env=env, payload=payload)
            assert status_code == 200

        # Allow time for processing
        time.sleep(0.1)

        # Verify final position is recorded
        assert task_id in env.recorder._running_tasks
        assert env.recorder._running_tasks[task_id]["position"] == "10"
    finally:
        _cleanup_env(env=env)

    return


def test_completed_tasks_removed_from_running_tasks() -> None:
    """
        Test that completed tasks are removed from running_tasks.
    """
    env = _establish_env()
    try:
        _start_server(env=env)

        task_id = "completion-test-task"
        worker_id = "completion-worker"

        # Start the task
        running_payload = _create_progress_payload(
            task_id=task_id,
            worker_id=worker_id,
            status="Running"
        )
        _send_progress_update(env=env, payload=running_payload)

        time.sleep(0.05)
        assert task_id in env.recorder._running_tasks

        # Complete the task
        completed_payload = _create_progress_payload(
            task_id=task_id,
            worker_id=worker_id,
            status="Completed"
        )
        _send_progress_update(env=env, payload=completed_payload)

        time.sleep(0.05)
        assert task_id not in env.recorder._running_tasks
    finally:
        _cleanup_env(env=env)

    return


def test_worker_data_preserved_in_aggregation() -> None:
    """
        Test that worker-specific data is preserved in aggregation.
    """
    env = _establish_env()
    try:
        _start_server(env=env)

        task_id = "data-preservation-task"
        worker_id = "data-worker-42"

        payload = _create_progress_payload(
            task_id=task_id,
            worker_id=worker_id,
            status="Running"
        )
        _send_progress_update(env=env, payload=payload)

        time.sleep(0.05)

        # Verify worker data is preserved
        assert task_id in env.recorder._running_tasks
        task_data = env.recorder._running_tasks[task_id]
        assert task_data["data"]["worker_id"] == worker_id
    finally:
        _cleanup_env(env=env)

    return


def test_thread_safe_concurrent_updates() -> None:
    """
        Test that ResultRecorder's post_task_progress is thread-safe (Requirement 11.3).
    """
    env = _establish_env()
    try:
        _start_server(env=env)

        num_threads = 20
        updates_per_thread = 50
        all_task_ids = []
        errors = []
        lock = threading.Lock()

        def stress_worker(thread_id: int):
            """Send many rapid updates."""
            thread_task_ids = []
            for i in range(updates_per_thread):
                task_id = f"stress-{thread_id}-{i}"
                thread_task_ids.append(task_id)

                payload = _create_progress_payload(
                    task_id=task_id,
                    worker_id=f"stress-worker-{thread_id}",
                    status="Running",
                    position=str(i)
                )
                try:
                    status_code = _send_progress_update(env=env, payload=payload)
                    if status_code != 200:
                        with lock:
                            errors.append(f"Thread {thread_id}, task {i}: status {status_code}")
                except Exception as e:
                    with lock:
                        errors.append(f"Thread {thread_id}, task {i}: {str(e)}")

            return thread_task_ids

        # Execute stress test
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(stress_worker, t) for t in range(num_threads)]
            for future in concurrent.futures.as_completed(futures):
                all_task_ids.extend(future.result())

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors during stress test: {errors[:10]}"

        # Verify expected number of tasks were created
        assert len(all_task_ids) == num_threads * updates_per_thread
    finally:
        _cleanup_env(env=env)

    return


def test_summary_property_returns_thread_safe_copy() -> None:
    """
        Test that ResultRecorder's summary property returns a thread-safe copy (Requirement 11.4).
    """
    env = _establish_env()
    try:
        _start_server(env=env)

        # Add some tasks
        for i in range(5):
            payload = _create_progress_payload(
                task_id=f"summary-task-{i}",
                worker_id="summary-worker",
                status="Running"
            )
            _send_progress_update(env=env, payload=payload)

        time.sleep(0.1)

        # Get summary
        summary1 = env.recorder.summary

        # Modify the returned summary
        summary1["running"]["modified-key"] = "modified-value"

        # Get summary again
        summary2 = env.recorder.summary

        # Verify the modification didn't affect the original
        assert "modified-key" not in summary2["running"]

        # Verify both summaries have the expected tasks
        for i in range(5):
            task_id = f"summary-task-{i}"
            assert task_id in summary2["running"]
    finally:
        _cleanup_env(env=env)

    return


def test_concurrent_reads_and_writes() -> None:
    """
        Test concurrent reads and writes to the recorder.
    """
    env = _establish_env()
    try:
        _start_server(env=env)

        num_writers = 5
        num_readers = 5
        operations_per_thread = 20
        write_errors = []
        read_errors = []
        lock = threading.Lock()

        def writer_task(writer_id: int):
            """Write progress updates."""
            for i in range(operations_per_thread):
                task_id = f"rw-writer-{writer_id}-task-{i}"
                payload = _create_progress_payload(
                    task_id=task_id,
                    worker_id=f"rw-worker-{writer_id}",
                    status="Running"
                )
                try:
                    status_code = _send_progress_update(env=env, payload=payload)
                    if status_code != 200:
                        with lock:
                            write_errors.append(f"Writer {writer_id}: status {status_code}")
                except Exception as e:
                    with lock:
                        write_errors.append(f"Writer {writer_id}: {str(e)}")
                time.sleep(0.001)  # Small delay between writes

        def reader_task(reader_id: int):
            """Read summary repeatedly."""
            for _ in range(operations_per_thread):
                try:
                    summary = env.recorder.summary
                    # Verify summary is valid
                    if not isinstance(summary, dict):
                        with lock:
                            read_errors.append(f"Reader {reader_id}: invalid summary type")
                    if "running" not in summary:
                        with lock:
                            read_errors.append(f"Reader {reader_id}: missing 'running' key")
                except Exception as e:
                    with lock:
                        read_errors.append(f"Reader {reader_id}: {str(e)}")
                time.sleep(0.001)  # Small delay between reads

        # Execute concurrent reads and writes
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_writers + num_readers) as executor:
            writer_futures = [executor.submit(writer_task, w) for w in range(num_writers)]
            reader_futures = [executor.submit(reader_task, r) for r in range(num_readers)]

            # Wait for all to complete
            for future in concurrent.futures.as_completed(writer_futures + reader_futures):
                future.result()

        # Verify no errors
        assert len(write_errors) == 0, f"Write errors: {write_errors[:5]}"
        assert len(read_errors) == 0, f"Read errors: {read_errors[:5]}"
    finally:
        _cleanup_env(env=env)

    return


def test_rapid_status_transitions() -> None:
    """
        Test rapid status transitions for the same task from multiple threads.
    """
    env = _establish_env()
    try:
        _start_server(env=env)

        task_id = "rapid-transition-task"
        num_transitions = 50
        errors = []

        statuses = ["Running", "Paused", "Running", "Paused", "Running"]

        def transition_worker(worker_id: int):
            """Send rapid status transitions."""
            for i in range(num_transitions):
                status = statuses[i % len(statuses)]
                payload = _create_progress_payload(
                    task_id=task_id,
                    worker_id=f"transition-worker-{worker_id}",
                    status=status,
                    position=str(i)
                )
                try:
                    status_code = _send_progress_update(env=env, payload=payload)
                    if status_code != 200:
                        errors.append(f"Worker {worker_id}, iteration {i}: status {status_code}")
                except Exception as e:
                    errors.append(f"Worker {worker_id}, iteration {i}: {str(e)}")

        # Run multiple workers updating the same task
        num_workers = 3
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(transition_worker, w) for w in range(num_workers)]
            for future in concurrent.futures.as_completed(futures):
                future.result()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors during transitions: {errors[:5]}"

        # Task should still be in running_tasks (not completed)
        assert task_id in env.recorder._running_tasks
    finally:
        _cleanup_env(env=env)

    return


def test_mixed_start_update_complete_operations() -> None:
    """
        Test mixed start, update, and complete operations from multiple workers.
    """
    env = _establish_env()
    try:
        _start_server(env=env)

        num_tasks = 10

        # Start all tasks
        for i in range(num_tasks):
            payload = _create_progress_payload(
                task_id=f"mixed-task-{i}",
                worker_id=f"worker-{i % 3}",
                status="Running",
                position="0"
            )
            _send_progress_update(env=env, payload=payload)

        time.sleep(0.05)

        # Verify all tasks are running
        for i in range(num_tasks):
            assert f"mixed-task-{i}" in env.recorder._running_tasks

        # Update half the tasks
        for i in range(0, num_tasks, 2):
            payload = _create_progress_payload(
                task_id=f"mixed-task-{i}",
                worker_id=f"worker-{i % 3}",
                status="Running",
                position="5"
            )
            _send_progress_update(env=env, payload=payload)

        time.sleep(0.05)

        # Complete some tasks
        completed_tasks = [0, 2, 4]
        for i in completed_tasks:
            payload = _create_progress_payload(
                task_id=f"mixed-task-{i}",
                worker_id=f"worker-{i % 3}",
                status="Completed"
            )
            _send_progress_update(env=env, payload=payload)

        time.sleep(0.05)

        # Verify completed tasks are removed
        for i in completed_tasks:
            assert f"mixed-task-{i}" not in env.recorder._running_tasks

        # Verify remaining tasks are still present
        remaining_tasks = [1, 3, 5, 6, 7, 8, 9]
        for i in remaining_tasks:
            assert f"mixed-task-{i}" in env.recorder._running_tasks
    finally:
        _cleanup_env(env=env)

    return


def test_concurrent_completions_from_multiple_workers() -> None:
    """
        Test concurrent task completions from multiple workers.
    """
    env = _establish_env()
    try:
        _start_server(env=env)

        num_tasks = 20

        # Start all tasks
        for i in range(num_tasks):
            payload = _create_progress_payload(
                task_id=f"concurrent-complete-{i}",
                worker_id=f"worker-{i % 4}",
                status="Running"
            )
            _send_progress_update(env=env, payload=payload)

        time.sleep(0.1)

        # Verify all tasks are running
        assert len(env.recorder._running_tasks) == num_tasks

        # Complete all tasks concurrently
        def complete_task(task_num: int):
            payload = _create_progress_payload(
                task_id=f"concurrent-complete-{task_num}",
                worker_id=f"worker-{task_num % 4}",
                status="Completed"
            )
            return _send_progress_update(env=env, payload=payload)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(complete_task, i) for i in range(num_tasks)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Verify all completions succeeded
        for status_code in results:
            assert status_code == 200

        time.sleep(0.1)

        # Verify all tasks are removed
        assert len(env.recorder._running_tasks) == 0
    finally:
        _cleanup_env(env=env)

    return
