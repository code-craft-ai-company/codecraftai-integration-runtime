"""
    .. module:: debug_summary_forwarding
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Example demonstrating how to configure summary forwarding.

    This example shows how to configure a ProgressConcentratorServer to periodically
    forward aggregated summaries to external monitoring services via HTTP POST.

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
from ccai.testbase.results.model.forwardinginfo import ForwardingInfo
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


def debug_configure_basic_forwarding():
    """
        Demonstrates basic summary forwarding configuration.

        This example shows how to configure the concentrator server to forward
        summaries to an external monitoring service at regular intervals.
    """

    print("\n--- debug_configure_basic_forwarding ---")

    # Create a temporary directory for output files
    output_dir = tempfile.mkdtemp(prefix="forwarding_basic_")
    print(f"Output directory: {output_dir}")

    # Create a placeholder summary template file
    template_path = os.path.join(output_dir, "testsummary.html")
    with open(template_path, 'w') as f:
        f.write("<html><body>Test Summary</body></html>")

    # Create the recorder
    recorder = create_example_recorder(output_dir)

    # Configure forwarding to an external monitoring service
    # The forwarding thread will POST the summary as JSON at the specified interval
    forwarding_info = ForwardingInfo(
        forwarding_interval=5.0,  # Forward every 5 seconds
        forwarding_url="https://monitoring.example.com/api/progress",
        forwarding_headers=None  # No custom headers
    )

    print(f"Forwarding interval: {forwarding_info.forwarding_interval} seconds")
    print(f"Forwarding URL: {forwarding_info.forwarding_url}")

    # Create the concentrator server with forwarding enabled
    server_address = ("127.0.0.1", 8081)

    server = ProgressConcentratorServer(
        recorder=recorder,
        server_address=server_address,
        forwarding_info=forwarding_info,
        bind_and_activate=True
    )

    print(f"\nCreated ProgressConcentratorServer with forwarding enabled")
    print(f"Server address: {server_address[0]}:{server_address[1]}")

    # Note: We don't start the server in this example because the forwarding
    # URL is not a real endpoint. In a real application, you would call:
    # server.start()

    print("\nNote: Server not started because forwarding URL is not real.")
    print("In a real application, call server.start() to begin forwarding.")

    return


def debug_configure_forwarding_with_auth():
    """
        Demonstrates summary forwarding with authentication headers.

        This example shows how to configure custom HTTP headers for forwarding,
        such as authentication tokens or correlation IDs.
    """

    print("\n--- debug_configure_forwarding_with_auth ---")

    # Create a temporary directory for output files
    output_dir = tempfile.mkdtemp(prefix="forwarding_auth_")
    print(f"Output directory: {output_dir}")

    # Create a placeholder summary template file
    template_path = os.path.join(output_dir, "testsummary.html")
    with open(template_path, 'w') as f:
        f.write("<html><body>Test Summary</body></html>")

    # Create the recorder
    recorder = create_example_recorder(output_dir)

    # Configure forwarding with authentication headers
    # Custom headers are merged with the default Content-Type header
    forwarding_info = ForwardingInfo(
        forwarding_interval=10.0,  # Forward every 10 seconds
        forwarding_url="https://monitoring.example.com/api/progress",
        forwarding_headers={
            "Authorization": "Bearer your-api-token-here",
            "X-Job-Id": "job-456",
            "X-Correlation-Id": str(uuid.uuid4())
        }
    )

    print(f"Forwarding interval: {forwarding_info.forwarding_interval} seconds")
    print(f"Forwarding URL: {forwarding_info.forwarding_url}")
    print(f"Custom headers:")
    for key, value in forwarding_info.forwarding_headers.items():
        # Mask the authorization token for security
        if key.lower() == "authorization":
            print(f"  {key}: Bearer ***")
        else:
            print(f"  {key}: {value}")

    # Create the concentrator server with forwarding enabled
    server_address = ("127.0.0.1", 8082)

    server = ProgressConcentratorServer(
        recorder=recorder,
        server_address=server_address,
        forwarding_info=forwarding_info,
        bind_and_activate=True
    )

    print(f"\nCreated ProgressConcentratorServer with authenticated forwarding")

    # The forwarding thread will include these headers in every POST request:
    # - Content-Type: application/json (default)
    # - Authorization: Bearer your-api-token-here
    # - X-Job-Id: job-456
    # - X-Correlation-Id: <uuid>

    print("\nNote: Server not started because forwarding URL is not real.")

    return


def debug_configure_high_frequency_forwarding():
    """
        Demonstrates high-frequency summary forwarding for real-time monitoring.

        This example shows how to configure more frequent forwarding for
        scenarios that require near real-time progress updates.
    """

    print("\n--- debug_configure_high_frequency_forwarding ---")

    # Create a temporary directory for output files
    output_dir = tempfile.mkdtemp(prefix="forwarding_highfreq_")
    print(f"Output directory: {output_dir}")

    # Create a placeholder summary template file
    template_path = os.path.join(output_dir, "testsummary.html")
    with open(template_path, 'w') as f:
        f.write("<html><body>Test Summary</body></html>")

    # Create the recorder
    recorder = create_example_recorder(output_dir)

    # Configure high-frequency forwarding for real-time monitoring
    # Use a shorter interval for more responsive dashboards
    forwarding_info = ForwardingInfo(
        forwarding_interval=1.0,  # Forward every 1 second
        forwarding_url="https://realtime-dashboard.example.com/api/progress",
        forwarding_headers={
            "X-Priority": "high",
            "X-Stream-Type": "realtime"
        }
    )

    print(f"Forwarding interval: {forwarding_info.forwarding_interval} second (high frequency)")
    print(f"Forwarding URL: {forwarding_info.forwarding_url}")

    # Create the concentrator server
    server_address = ("127.0.0.1", 8083)

    server = ProgressConcentratorServer(
        recorder=recorder,
        server_address=server_address,
        forwarding_info=forwarding_info,
        bind_and_activate=True
    )

    print(f"\nCreated ProgressConcentratorServer with high-frequency forwarding")

    # Note: High-frequency forwarding increases network traffic
    # Consider the trade-off between responsiveness and resource usage

    print("\nNote: High-frequency forwarding increases network traffic.")
    print("Consider the trade-off between responsiveness and resource usage.")

    return


def debug_forwarding_info_dataclass():
    """
        Demonstrates the ForwardingInfo dataclass structure.

        This example shows the fields available in ForwardingInfo and
        how to create instances with different configurations.
    """

    print("\n--- debug_forwarding_info_dataclass ---")

    # ForwardingInfo is a dataclass with three fields:
    # - forwarding_interval: float - seconds between forwards
    # - forwarding_url: str - destination URL for POST requests
    # - forwarding_headers: Optional[dict] - custom HTTP headers

    # Example 1: Minimal configuration
    minimal_config = ForwardingInfo(
        forwarding_interval=30.0,
        forwarding_url="https://api.example.com/progress"
    )
    print(f"Minimal config:")
    print(f"  interval: {minimal_config.forwarding_interval}")
    print(f"  url: {minimal_config.forwarding_url}")
    print(f"  headers: {minimal_config.forwarding_headers}")

    # Example 2: Full configuration
    full_config = ForwardingInfo(
        forwarding_interval=5.0,
        forwarding_url="https://api.example.com/progress",
        forwarding_headers={
            "Authorization": "Bearer token123",
            "X-Custom-Header": "custom-value"
        }
    )
    print(f"\nFull config:")
    print(f"  interval: {full_config.forwarding_interval}")
    print(f"  url: {full_config.forwarding_url}")
    print(f"  headers: {full_config.forwarding_headers}")

    # Example 3: Configuration for different environments
    dev_config = ForwardingInfo(
        forwarding_interval=2.0,  # More frequent in dev
        forwarding_url="http://localhost:3000/api/progress",
        forwarding_headers={"X-Environment": "development"}
    )

    prod_config = ForwardingInfo(
        forwarding_interval=30.0,  # Less frequent in prod
        forwarding_url="https://monitoring.prod.example.com/api/progress",
        forwarding_headers={
            "Authorization": "Bearer prod-token",
            "X-Environment": "production"
        }
    )

    print(f"\nDev config interval: {dev_config.forwarding_interval}s")
    print(f"Prod config interval: {prod_config.forwarding_interval}s")

    return


def main_debug_summary_forwarding():
    """
        Main entry point for the summary forwarding examples.
    """

    debug_configure_basic_forwarding()
    debug_configure_forwarding_with_auth()
    debug_configure_high_frequency_forwarding()
    debug_forwarding_info_dataclass()

    print("\n--- All summary forwarding examples completed ---")

    return


if __name__ == "__main__":
    main_debug_summary_forwarding()
