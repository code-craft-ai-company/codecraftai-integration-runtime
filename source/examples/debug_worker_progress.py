"""
    .. module:: debug_worker_progress
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Example demonstrating how workers submit progress updates.

    This example shows how remote test workers can submit progress updates
    to a ProgressConcentratorServer via HTTP POST requests.

    .. moduleauthor:: CodeCraftX
"""

__author__ = "CodeCraftX"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


import json
import os
import tempfile
import threading
import time
import uuid

from datetime import datetime

import requests

from ccai.testbase.results.model.buildinfo import BuildInfo
from ccai.testbase.results.model.jobinfo import JobInfo
from ccai.testbase.results.model.pipelineinfo import PipelineInfo
from ccai.testbase.results.model.progresscode import ProgressCode
from ccai.testbase.results.model.progressinfo import ProgressInfo
from ccai.testbase.results.model.progresstype import ProgressType
from ccai.testbase.results.model.renderinfo import RenderInfo

from ccai.testbase.results.recorders.jsonresultrecorder import JsonResultRecorder
from ccai.integrationruntime.results.concentrators.progressconcentratorservice import (
    ProgressConcentratorServer
)


def create_example_recorder(output_dir: str) -> JsonResultRecorder:
    """
        Creates a JsonResultRecorder with example configuration for demonstration.

        :param output_dir: The directory where result files will be written.

        :returns: A configured JsonResultRecorder instance.
    """

    build_info = BuildInfo(
        branch="main",
        build="1.0.0",
        flavor="release",
        release="v1.0",
        url="https://example.com/builds/1.0.0"
    )

    pipeline_info = PipelineInfo(
        id="pipeline-001",
        name="example-pipeline",
        instance="instance-001"
    )

    job_info = JobInfo(
        id="job-001",
        name="example-job",
        type="test",
        owner="example-user",
        label="example-label"
    )

    render_info = RenderInfo(
        title="Example Test Run",
        summary_filename=os.path.join(output_dir, "testrun_summary.json"),
        summary_template=os.path.join(output_dir, "testsummary.html"),
        stream_results_filename=os.path.join(output_dir, "testrun_results_stream.jsos"),
        consolidated_results_filename=os.path.join(output_dir, "testrun_results.json"),
        static_resource_source=None,
        static_resource_destination=output_dir
    )

    recorder = JsonResultRecorder(
        runid=str(uuid.uuid4()),
        start=datetime.now(),
        render_info=render_info,
        apod="example-pod",
        build_info=build_info,
        pipeline_info=pipeline_info,
        job_info=job_info
    )

    return recorder


def debug_create_progress_info():
    """
        Demonstrates how to create ProgressInfo objects.

        This example shows the structure of progress updates that workers
        send to the concentrator server.
    """

    print("\n--- debug_create_progress_info ---")

    # Create a ProgressInfo object representing a running task
    progress = ProgressInfo(
        id=str(uuid.uuid4()),  # Unique task identifier
        category="test-execution",  # Category of the task
        moniker="test_module.test_function",  # Human-readable task name
        ptype=ProgressType.Sequential,  # Progress tracking mode
        range_min="0",  # Minimum progress value
        range_max="10",  # Maximum progress value
        position="5",  # Current progress position
        status=ProgressCode.Running,  # Current status
        when=datetime.now(),  # Timestamp of the update
        data={  # Optional additional data
            "worker_id": "worker-1",
            "additional_info": "Processing step 5 of 10"
        }
    )

    print(f"Created ProgressInfo:")
    print(f"  id: {progress.id}")
    print(f"  category: {progress.category}")
    print(f"  moniker: {progress.moniker}")
    print(f"  ptype: {progress.ptype.name}")
    print(f"  range: {progress.range_min} - {progress.range_max}")
    print(f"  position: {progress.position}")
    print(f"  status: {progress.status.name}")
    print(f"  when: {progress.when.isoformat()}")
    print(f"  data: {progress.data}")

    # Convert to dictionary for JSON serialization
    progress_dict = progress.as_dict()
    print(f"\nAs dictionary (for JSON):")
    print(json.dumps(progress_dict, indent=2))

    return


def debug_progress_status_codes():
    """
        Demonstrates the different progress status codes.

        This example shows all available ProgressCode values and when
        to use each one.
    """

    print("\n--- debug_progress_status_codes ---")

    task_id = str(uuid.uuid4())
    base_progress = {
        "id": task_id,
        "category": "test-execution",
        "moniker": "test_module.test_function",
        "ptype": ProgressType.Sequential,
        "range_min": "0",
        "range_max": "10",
        "position": "0",
        "when": datetime.now(),
        "data": None
    }

    # NotStarted - Task is queued but not yet running
    not_started = ProgressInfo(**base_progress, status=ProgressCode.NotStarted)
    print(f"NotStarted: Task is queued but not yet running")
    print(f"  status: {not_started.status.name}")

    # Running - Task is actively executing
    running = ProgressInfo(**{**base_progress, "position": "5"}, status=ProgressCode.Running)
    print(f"\nRunning: Task is actively executing")
    print(f"  status: {running.status.name}")
    print(f"  position: {running.position}")

    # Paused - Task execution is temporarily suspended
    paused = ProgressInfo(**{**base_progress, "position": "5"}, status=ProgressCode.Paused)
    print(f"\nPaused: Task execution is temporarily suspended")
    print(f"  status: {paused.status.name}")

    # Completed - Task finished successfully
    completed = ProgressInfo(**{**base_progress, "position": "10"}, status=ProgressCode.Completed)
    print(f"\nCompleted: Task finished successfully")
    print(f"  status: {completed.status.name}")
    print(f"  Note: Completed tasks are removed from running_tasks")

    # Failed - Task failed due to assertion failure
    failed = ProgressInfo(**{**base_progress, "position": "7"}, status=ProgressCode.Failed)
    print(f"\nFailed: Task failed due to assertion failure")
    print(f"  status: {failed.status.name}")

    # Errored - Task failed due to unexpected exception
    errored = ProgressInfo(**{**base_progress, "position": "3"}, status=ProgressCode.Errored)
    print(f"\nErrored: Task failed due to unexpected exception")
    print(f"  status: {errored.status.name}")

    return


def debug_progress_types():
    """
        Demonstrates the different progress tracking types.

        This example shows all available ProgressType values and when
        to use each one.
    """

    print("\n--- debug_progress_types ---")

    # Sequential - For multi-step operations
    sequential = ProgressInfo(
        id=str(uuid.uuid4()),
        category="test-execution",
        moniker="test_suite.run_all",
        ptype=ProgressType.Sequential,
        range_min="1",
        range_max="5",
        position="3",  # Step 3 of 5
        status=ProgressCode.Running,
        when=datetime.now(),
        data={"current_step": "Running test 3"}
    )
    print(f"Sequential: For multi-step operations")
    print(f"  ptype: {sequential.ptype.name}")
    print(f"  Example: Step {sequential.position} of {sequential.range_max}")

    # NumericRange - For batch processing with known count
    numeric_range = ProgressInfo(
        id=str(uuid.uuid4()),
        category="data-processing",
        moniker="batch_processor.process_items",
        ptype=ProgressType.NumericRange,
        range_min="0",
        range_max="1000",
        position="450",  # 450 of 1000 items processed
        status=ProgressCode.Running,
        when=datetime.now(),
        data={"items_processed": 450}
    )
    print(f"\nNumericRange: For batch processing with known count")
    print(f"  ptype: {numeric_range.ptype.name}")
    print(f"  Example: {numeric_range.position} of {numeric_range.range_max} items")

    # TimeSpan - For duration-based tasks
    time_span = ProgressInfo(
        id=str(uuid.uuid4()),
        category="stress-test",
        moniker="stress_test.run_for_duration",
        ptype=ProgressType.TimeSpan,
        range_min="0",
        range_max="3600",  # 1 hour in seconds
        position="1800",  # 30 minutes elapsed
        status=ProgressCode.Running,
        when=datetime.now(),
        data={"elapsed_seconds": 1800}
    )
    print(f"\nTimeSpan: For duration-based tasks")
    print(f"  ptype: {time_span.ptype.name}")
    print(f"  Example: {time_span.position}s of {time_span.range_max}s elapsed")

    return


def debug_submit_progress_to_server():
    """
        Demonstrates submitting progress updates to a running server.

        This example starts a concentrator server and shows how workers
        can submit progress updates via HTTP POST.
    """

    print("\n--- debug_submit_progress_to_server ---")

    # Create a temporary directory for output files
    output_dir = tempfile.mkdtemp(prefix="worker_progress_")
    print(f"Output directory: {output_dir}")

    # Create a placeholder summary template file
    template_path = os.path.join(output_dir, "testsummary.html")
    with open(template_path, 'w') as f:
        f.write("<html><body>Test Summary</body></html>")

    # Create the recorder
    recorder = create_example_recorder(output_dir)

    # Create and start the concentrator server
    server_address = ("127.0.0.1", 8084)
    server = ProgressConcentratorServer(
        recorder=recorder,
        server_address=server_address,
        forwarding_info=None,
        bind_and_activate=True
    )
    server.start()

    print(f"Server started on {server_address[0]}:{server_address[1]}")

    # Create a progress update
    task_id = str(uuid.uuid4())
    progress = ProgressInfo(
        id=task_id,
        category="test-execution",
        moniker="test_module.test_function",
        ptype=ProgressType.Sequential,
        range_min="0",
        range_max="10",
        position="0",
        status=ProgressCode.Running,
        when=datetime.now(),
        data={"worker_id": "worker-1"}
    )

    # Submit progress via HTTP POST
    url = f"http://{server_address[0]}:{server_address[1]}/"
    headers = {"Content-Type": "application/json"}
    payload = progress.as_dict()

    print(f"\nSubmitting progress update to {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    response = requests.post(url, json=payload, headers=headers)
    print(f"Response status: {response.status_code}")

    # Check the running tasks in the recorder
    summary = recorder.summary
    print(f"\nRunning tasks after submission: {len(summary['running'])}")
    if task_id in summary['running']:
        print(f"Task {task_id} is now tracked in running_tasks")

    # Submit a completion update
    progress.status = ProgressCode.Completed
    progress.position = "10"
    progress.when = datetime.now()

    print(f"\nSubmitting completion update...")
    response = requests.post(url, json=progress.as_dict(), headers=headers)
    print(f"Response status: {response.status_code}")

    # Check that the task was removed from running tasks
    summary = recorder.summary
    print(f"Running tasks after completion: {len(summary['running'])}")
    if task_id not in summary['running']:
        print(f"Task {task_id} was removed from running_tasks (completed)")

    return


def debug_simulate_multiple_workers():
    """
        Demonstrates multiple workers submitting progress concurrently.

        This example simulates multiple workers submitting progress updates
        to the same concentrator server simultaneously.
    """

    print("\n--- debug_simulate_multiple_workers ---")

    # Create a temporary directory for output files
    output_dir = tempfile.mkdtemp(prefix="multi_worker_")
    print(f"Output directory: {output_dir}")

    # Create a placeholder summary template file
    template_path = os.path.join(output_dir, "testsummary.html")
    with open(template_path, 'w') as f:
        f.write("<html><body>Test Summary</body></html>")

    # Create the recorder
    recorder = create_example_recorder(output_dir)

    # Create and start the concentrator server
    server_address = ("127.0.0.1", 8085)
    server = ProgressConcentratorServer(
        recorder=recorder,
        server_address=server_address,
        forwarding_info=None,
        bind_and_activate=True
    )
    server.start()

    print(f"Server started on {server_address[0]}:{server_address[1]}")

    # Define a worker function that submits progress updates
    def worker_task(worker_id: str, task_count: int):
        url = f"http://{server_address[0]}:{server_address[1]}/"
        headers = {"Content-Type": "application/json"}

        for i in range(task_count):
            task_id = str(uuid.uuid4())

            # Submit running status
            progress = ProgressInfo(
                id=task_id,
                category="test-execution",
                moniker=f"worker_{worker_id}.task_{i}",
                ptype=ProgressType.Sequential,
                range_min="0",
                range_max="5",
                position="0",
                status=ProgressCode.Running,
                when=datetime.now(),
                data={"worker_id": worker_id}
            )
            requests.post(url, json=progress.as_dict(), headers=headers)

            # Simulate work
            time.sleep(0.1)

            # Submit completion
            progress.status = ProgressCode.Completed
            progress.position = "5"
            progress.when = datetime.now()
            requests.post(url, json=progress.as_dict(), headers=headers)

        print(f"  Worker {worker_id} completed {task_count} tasks")

    # Start multiple worker threads
    num_workers = 3
    tasks_per_worker = 5
    threads = []

    print(f"\nStarting {num_workers} workers, each processing {tasks_per_worker} tasks...")

    for i in range(num_workers):
        worker_id = f"worker-{i+1}"
        thread = threading.Thread(target=worker_task, args=(worker_id, tasks_per_worker))
        threads.append(thread)
        thread.start()

    # Wait for all workers to complete
    for thread in threads:
        thread.join()

    print(f"\nAll workers completed!")

    # Check final state
    summary = recorder.summary
    print(f"Final running tasks: {len(summary['running'])}")
    print(f"Total tasks processed: {num_workers * tasks_per_worker}")

    return


def main_debug_worker_progress():
    """
        Main entry point for the worker progress examples.
    """

    debug_create_progress_info()
    debug_progress_status_codes()
    debug_progress_types()
    debug_submit_progress_to_server()
    debug_simulate_multiple_workers()

    print("\n--- All worker progress examples completed ---")

    return


if __name__ == "__main__":
    main_debug_worker_progress()
