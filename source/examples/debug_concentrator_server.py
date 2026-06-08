"""
    .. module:: debug_concentrator_server
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Example demonstrating how to start a ProgressConcentratorServer.

    This example shows how to create and start a ProgressConcentratorServer that
    receives progress callbacks from remote test workers and aggregates them into
    a central ResultRecorder.

    .. moduleauthor:: CodeCraftX
"""

__author__ = "CodeCraftX"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


import os
import tempfile
import time
import uuid

from datetime import datetime

from ccai.testbase.results.model.buildinfo import BuildInfo
from ccai.testbase.results.model.jobinfo import JobInfo
from ccai.testbase.results.model.pipelineinfo import PipelineInfo
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

    # Create required info objects for the recorder
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

    # Create render info with paths in the output directory
    render_info = RenderInfo(
        title="Example Test Run",
        summary_filename=os.path.join(output_dir, "testrun_summary.json"),
        summary_template=os.path.join(output_dir, "testsummary.html"),
        stream_results_filename=os.path.join(output_dir, "testrun_results_stream.jsos"),
        consolidated_results_filename=os.path.join(output_dir, "testrun_results.json"),
        static_resource_source=None,
        static_resource_destination=output_dir
    )

    # Create the recorder
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


def debug_start_concentrator_server():
    """
        Demonstrates how to start a ProgressConcentratorServer.

        This example creates a concentrator server that listens on localhost:8080
        and aggregates progress updates from remote workers into a ResultRecorder.
    """

    print("\n--- debug_start_concentrator_server ---")

    # Create a temporary directory for output files
    output_dir = tempfile.mkdtemp(prefix="concentrator_example_")
    print(f"Output directory: {output_dir}")

    # Create a placeholder summary template file (required by recorder)
    template_path = os.path.join(output_dir, "testsummary.html")
    with open(template_path, 'w') as f:
        f.write("<html><body>Test Summary</body></html>")

    # Create the recorder
    recorder = create_example_recorder(output_dir)

    # Create the concentrator server
    # The server will listen on localhost:8080 for progress callbacks
    server_address = ("127.0.0.1", 8080)

    server = ProgressConcentratorServer(
        recorder=recorder,
        server_address=server_address,
        forwarding_info=None,  # No forwarding in this example
        bind_and_activate=True
    )

    print(f"Created ProgressConcentratorServer on {server_address[0]}:{server_address[1]}")

    # Start the server
    # This creates a daemon thread that handles incoming requests
    server.start()

    print("Server started successfully!")
    print("The server is now ready to receive progress callbacks via HTTP POST")
    print(f"Workers can POST progress updates to: http://{server_address[0]}:{server_address[1]}/")

    # In a real application, the server would run until shutdown
    # For this example, we'll just wait a moment to demonstrate it's running
    print("\nServer is running... (waiting 2 seconds for demonstration)")
    time.sleep(2)

    # Check the server state
    print(f"Server running: {server._server_running}")

    # Get the current summary from the recorder
    summary = recorder.summary
    print(f"\nCurrent summary result: {summary['result']}")
    print(f"Running tasks: {len(summary['running'])}")

    print("\nNote: In a real application, the server would continue running")
    print("until the process exits or shutdown() is called.")

    return


def debug_start_concentrator_server_custom_port():
    """
        Demonstrates starting a concentrator server on a custom port.

        This example shows how to configure the server to listen on a different
        port and on all network interfaces.
    """

    print("\n--- debug_start_concentrator_server_custom_port ---")

    # Create a temporary directory for output files
    output_dir = tempfile.mkdtemp(prefix="concentrator_custom_port_")
    print(f"Output directory: {output_dir}")

    # Create a placeholder summary template file
    template_path = os.path.join(output_dir, "testsummary.html")
    with open(template_path, 'w') as f:
        f.write("<html><body>Test Summary</body></html>")

    # Create the recorder
    recorder = create_example_recorder(output_dir)

    # Configure server to listen on all interfaces on port 9090
    # Using "0.0.0.0" allows connections from any network interface
    server_address = ("0.0.0.0", 9090)

    server = ProgressConcentratorServer(
        recorder=recorder,
        server_address=server_address,
        forwarding_info=None,
        bind_and_activate=True
    )

    print(f"Created ProgressConcentratorServer on {server_address[0]}:{server_address[1]}")
    print("Server will accept connections from any network interface")

    # Start the server
    server.start()

    print("Server started successfully!")
    print(f"Workers can POST progress updates to: http://<server-ip>:{server_address[1]}/")

    # Wait briefly for demonstration
    time.sleep(1)

    print(f"\nServer running: {server._server_running}")

    return


def main_debug_concentrator_server():
    """
        Main entry point for the concentrator server examples.
    """

    debug_start_concentrator_server()
    debug_start_concentrator_server_custom_port()

    print("\n--- All concentrator server examples completed ---")

    return


if __name__ == "__main__":
    main_debug_concentrator_server()
