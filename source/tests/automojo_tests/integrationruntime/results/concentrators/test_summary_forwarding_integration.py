"""
    .. module:: automojo_tests.testbase.results.concentrators.test_summary_forwarding_integration
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Integration tests for summary forwarding functionality.

    .. moduleauthor:: AutomationX
"""

import unittest
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

from automojo.testbase.results.model.buildinfo import BuildInfo
from automojo.testbase.results.model.pipelineinfo import PipelineInfo
from automojo.testbase.results.model.jobinfo import JobInfo
from automojo.testbase.results.model.renderinfo import RenderInfo
from automojo.testbase.results.model.forwardinginfo import ForwardingInfo

from automojo.testbase.results.recorders.jsonresultrecorder import JsonResultRecorder
from automojo.integrationruntime.results.concentrators.progressconcentratorservice import (
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



class SummaryForwardingIntegrationTestBase(unittest.TestCase):
    """Base class for summary forwarding integration tests."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        self.render_info = RenderInfo(
            title="Summary Forwarding Integration Test",
            summary_filename=os.path.join(self.temp_dir, "summary.json"),
            summary_template=os.path.join(self.temp_dir, "template.html"),
            stream_results_filename=os.path.join(self.temp_dir, "results.json"),
            consolidated_results_filename=os.path.join(self.temp_dir, "consolidated.json"),
            static_resource_source=None,
            static_resource_destination=self.temp_dir
        )
        
        # Create a dummy template file
        with open(self.render_info.summary_template, 'w') as f:
            f.write("<html></html>")
        
        self.runid = str(uuid.uuid4())
        self.start_time = datetime.now()

        self.build_info = BuildInfo(
            branch="main",
            build="build-forwarding-integration",
            flavor="release",
            release="1.0.0",
            url="https://ci.example.com/build/forwarding"
        )
        
        self.pipeline_info = PipelineInfo(
            id="pipeline-forwarding",
            name="Forwarding Pipeline",
            instance="instance-forwarding"
        )
        
        self.job_info = JobInfo(
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
        
        self.recorder = JsonResultRecorder(
            runid=self.runid,
            start=self.start_time,
            render_info=self.render_info,
            build_info=self.build_info,
            pipeline_info=self.pipeline_info,
            job_info=self.job_info
        )
        
        # Use port 0 to let OS assign available ports
        self.concentrator_address = ("127.0.0.1", 0)
        self.external_service_address = ("127.0.0.1", 0)
        
        self.concentrator_server = None
        self.external_service = None

    def tearDown(self):
        """Clean up test fixtures."""
        if self.concentrator_server is not None:
            try:
                self.concentrator_server._forwarding_running = False
                self.concentrator_server.shutdown()
                self.concentrator_server.server_close()
                if hasattr(self.concentrator_server, '_forward_thread') and self.concentrator_server._forward_thread is not None:
                    try:
                        self.concentrator_server._forward_thread.join(timeout=2.0)
                    except Exception:
                        pass
            except Exception:
                pass
        
        if self.external_service is not None:
            try:
                self.external_service.stop()
            except Exception:
                pass
        
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _start_external_service(self):
        """Start the mock external service and return its URL."""
        self.external_service = MockExternalService(self.external_service_address)
        self.external_service.start()
        actual_port = self.external_service.server_address[1]
        return f"http://127.0.0.1:{actual_port}/api/progress"

    def _start_concentrator_with_forwarding(self, forwarding_url, forwarding_interval=0.1, 
                                             forwarding_headers=None):
        """Start the concentrator server with forwarding configured."""
        forwarding_info = ForwardingInfo(
            forwarding_interval=forwarding_interval,
            forwarding_url=forwarding_url,
            forwarding_headers=forwarding_headers
        )
        
        self.concentrator_server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.concentrator_address,
            forwarding_info=forwarding_info
        )
        self.concentrator_server.start()
        return self.concentrator_server.server_address[1]

    def _create_progress_payload(self, task_id: str, worker_id: str, 
                                  status: str, position: str = "5") -> dict:
        """Create a progress update payload for HTTP POST."""
        return {
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

    def _send_progress_update(self, port: int, payload: dict) -> int:
        """Send a progress update via HTTP POST and return the status code."""
        conn = http.client.HTTPConnection("127.0.0.1", port)
        try:
            body = json.dumps(payload)
            headers = {"Content-Type": "application/json", "Content-Length": str(len(body))}
            conn.request("POST", "/progress", body=body, headers=headers)
            response = conn.getresponse()
            return response.status
        finally:
            conn.close()



class PeriodicSummaryForwardingTimingTests(SummaryForwardingIntegrationTestBase):
    """Integration tests for periodic summary forwarding timing (Requirement 9.1-9.4)."""

    def test_summary_forwarded_at_configured_interval(self):
        """Test that summaries are forwarded at the configured interval (Requirement 9.4)."""
        forwarding_url = self._start_external_service()
        forwarding_interval = 0.15
        
        self._start_concentrator_with_forwarding(
            forwarding_url=forwarding_url,
            forwarding_interval=forwarding_interval
        )
        
        # Wait for multiple forwarding cycles
        time.sleep(forwarding_interval * 4 + 0.1)
        
        received = self.external_service.get_received_summaries()
        
        # Should have received at least 3 summaries
        self.assertGreaterEqual(len(received), 3, 
            f"Expected at least 3 summaries, got {len(received)}")
        
        # Verify timing between summaries is approximately the configured interval
        if len(received) >= 2:
            for i in range(1, len(received)):
                interval = received[i]['timestamp'] - received[i-1]['timestamp']
                # Allow 50% tolerance for timing variations
                self.assertGreaterEqual(interval, forwarding_interval * 0.5,
                    f"Interval {interval} too short, expected ~{forwarding_interval}")
                self.assertLessEqual(interval, forwarding_interval * 2.0,
                    f"Interval {interval} too long, expected ~{forwarding_interval}")

    def test_forwarding_continues_while_server_running(self):
        """Test that forwarding continues while the server is running (Requirement 9.1)."""
        forwarding_url = self._start_external_service()
        forwarding_interval = 0.1
        
        self._start_concentrator_with_forwarding(
            forwarding_url=forwarding_url,
            forwarding_interval=forwarding_interval
        )
        
        # Verify forwarding is running
        self.assertTrue(self.concentrator_server._forwarding_running)
        
        # Wait and collect summaries
        time.sleep(0.35)
        first_count = len(self.external_service.get_received_summaries())
        
        # Wait more and verify more summaries arrive
        time.sleep(0.35)
        second_count = len(self.external_service.get_received_summaries())
        
        self.assertGreater(second_count, first_count,
            "Forwarding should continue sending summaries")

    def test_summary_contains_current_recorder_state(self):
        """Test that forwarded summary contains current recorder state (Requirement 9.2)."""
        forwarding_url = self._start_external_service()
        
        concentrator_port = self._start_concentrator_with_forwarding(
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )
        
        # Add some progress updates
        for i in range(3):
            payload = self._create_progress_payload(
                task_id=f"state-task-{i}",
                worker_id="state-worker",
                status="Running",
                position=str(i)
            )
            self._send_progress_update(concentrator_port, payload)
        
        # Wait for forwarding to occur
        time.sleep(0.25)
        
        received = self.external_service.get_received_summaries()
        self.assertGreater(len(received), 0)
        
        # Find a summary that contains our tasks
        found_tasks = False
        for entry in received:
            summary = entry['summary']
            running = summary.get('running', {})
            if all(f"state-task-{i}" in running for i in range(3)):
                found_tasks = True
                break
        
        self.assertTrue(found_tasks, 
            "Forwarded summary should contain the current running tasks")



class ExternalServiceIntegrationTests(SummaryForwardingIntegrationTestBase):
    """Integration tests for external service integration (Requirement 9.3)."""

    def test_summary_posted_to_external_service(self):
        """Test that summary is POSTed to the external service URL (Requirement 9.3)."""
        forwarding_url = self._start_external_service()
        
        self._start_concentrator_with_forwarding(
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )
        
        # Wait for at least one forwarding cycle
        time.sleep(0.25)
        
        received = self.external_service.get_received_summaries()
        
        self.assertGreater(len(received), 0, 
            "External service should receive at least one summary")

    def test_summary_json_structure_is_valid(self):
        """Test that the forwarded summary has valid JSON structure."""
        forwarding_url = self._start_external_service()
        
        self._start_concentrator_with_forwarding(
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )
        
        # Wait for forwarding
        time.sleep(0.25)
        
        received = self.external_service.get_received_summaries()
        self.assertGreater(len(received), 0)
        
        summary = received[0]['summary']
        
        # Verify expected summary fields
        self.assertIn('version', summary)
        self.assertIn('runid', summary)
        self.assertIn('running', summary)
        self.assertEqual(summary['runid'], self.runid)

    def test_summary_includes_build_info(self):
        """Test that forwarded summary includes build information."""
        forwarding_url = self._start_external_service()
        
        self._start_concentrator_with_forwarding(
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )
        
        time.sleep(0.25)
        
        received = self.external_service.get_received_summaries()
        self.assertGreater(len(received), 0)
        
        summary = received[0]['summary']
        
        # Verify build info is present
        self.assertIn('build', summary)
        build = summary['build']
        self.assertEqual(build['branch'], 'main')
        self.assertEqual(build['build'], 'build-forwarding-integration')

    def test_summary_includes_job_info(self):
        """Test that forwarded summary includes job information."""
        forwarding_url = self._start_external_service()
        
        self._start_concentrator_with_forwarding(
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )
        
        time.sleep(0.25)
        
        received = self.external_service.get_received_summaries()
        self.assertGreater(len(received), 0)
        
        summary = received[0]['summary']
        
        # Verify job info is present
        self.assertIn('job', summary)
        job = summary['job']
        self.assertEqual(job['name'], 'Forwarding Tests')
        self.assertEqual(job['type'], 'IntegrationTest')

    def test_running_tasks_reflected_in_forwarded_summary(self):
        """Test that running tasks are reflected in forwarded summaries."""
        forwarding_url = self._start_external_service()
        
        concentrator_port = self._start_concentrator_with_forwarding(
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )
        
        # Add running tasks
        task_ids = []
        for i in range(5):
            task_id = f"running-task-{i}"
            task_ids.append(task_id)
            payload = self._create_progress_payload(
                task_id=task_id,
                worker_id="integration-worker",
                status="Running",
                position=str(i * 2)
            )
            self._send_progress_update(concentrator_port, payload)
        
        # Wait for forwarding
        time.sleep(0.25)
        
        received = self.external_service.get_received_summaries()
        
        # Find a summary with our tasks
        found_all_tasks = False
        for entry in received:
            running = entry['summary'].get('running', {})
            if all(tid in running for tid in task_ids):
                found_all_tasks = True
                # Verify task details
                for i, tid in enumerate(task_ids):
                    self.assertEqual(running[tid]['position'], str(i * 2))
                break
        
        self.assertTrue(found_all_tasks, 
            "All running tasks should be in forwarded summary")

    def test_completed_tasks_removed_from_forwarded_summary(self):
        """Test that completed tasks are removed from forwarded summaries."""
        forwarding_url = self._start_external_service()
        
        concentrator_port = self._start_concentrator_with_forwarding(
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )
        
        # Add a running task
        task_id = "complete-test-task"
        payload = self._create_progress_payload(
            task_id=task_id,
            worker_id="integration-worker",
            status="Running"
        )
        self._send_progress_update(concentrator_port, payload)
        
        # Wait for forwarding
        time.sleep(0.15)
        
        # Complete the task
        payload = self._create_progress_payload(
            task_id=task_id,
            worker_id="integration-worker",
            status="Completed"
        )
        self._send_progress_update(concentrator_port, payload)
        
        # Clear previous summaries and wait for new ones
        self.external_service.clear_received_summaries()
        time.sleep(0.25)
        
        received = self.external_service.get_received_summaries()
        self.assertGreater(len(received), 0)
        
        # Verify task is not in the latest summary
        latest_summary = received[-1]['summary']
        running = latest_summary.get('running', {})
        self.assertNotIn(task_id, running,
            "Completed task should not be in forwarded summary")



class HeaderPropagationIntegrationTests(SummaryForwardingIntegrationTestBase):
    """Integration tests for header propagation (Requirement 9.5-9.6)."""

    def test_content_type_header_propagated(self):
        """Test that Content-Type: application/json header is propagated (Requirement 9.5)."""
        forwarding_url = self._start_external_service()
        
        self._start_concentrator_with_forwarding(
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )
        
        # Wait for forwarding
        time.sleep(0.25)
        
        received = self.external_service.get_received_summaries()
        self.assertGreater(len(received), 0)
        
        headers = received[0]['headers']
        
        # Verify Content-Type header
        self.assertIn('Content-Type', headers)
        self.assertEqual(headers['Content-Type'], 'application/json')

    def test_custom_headers_propagated(self):
        """Test that custom forwarding headers are propagated (Requirement 9.6)."""
        forwarding_url = self._start_external_service()
        
        custom_headers = {
            "Authorization": "Bearer integration-test-token",
            "X-Job-Id": "job-integration-123",
            "X-Custom-Header": "custom-value"
        }
        
        self._start_concentrator_with_forwarding(
            forwarding_url=forwarding_url,
            forwarding_interval=0.1,
            forwarding_headers=custom_headers
        )
        
        # Wait for forwarding
        time.sleep(0.25)
        
        received = self.external_service.get_received_summaries()
        self.assertGreater(len(received), 0)
        
        headers = received[0]['headers']
        
        # Verify custom headers are present
        self.assertIn('Authorization', headers)
        self.assertEqual(headers['Authorization'], 'Bearer integration-test-token')
        
        self.assertIn('X-Job-Id', headers)
        self.assertEqual(headers['X-Job-Id'], 'job-integration-123')
        
        self.assertIn('X-Custom-Header', headers)
        self.assertEqual(headers['X-Custom-Header'], 'custom-value')

    def test_custom_headers_merged_with_default_content_type(self):
        """Test that custom headers are merged with default Content-Type header."""
        forwarding_url = self._start_external_service()
        
        custom_headers = {
            "Authorization": "Bearer merge-test-token"
        }
        
        self._start_concentrator_with_forwarding(
            forwarding_url=forwarding_url,
            forwarding_interval=0.1,
            forwarding_headers=custom_headers
        )
        
        # Wait for forwarding
        time.sleep(0.25)
        
        received = self.external_service.get_received_summaries()
        self.assertGreater(len(received), 0)
        
        headers = received[0]['headers']
        
        # Verify both default and custom headers are present
        self.assertIn('Content-Type', headers)
        self.assertEqual(headers['Content-Type'], 'application/json')
        
        self.assertIn('Authorization', headers)
        self.assertEqual(headers['Authorization'], 'Bearer merge-test-token')

    def test_headers_consistent_across_multiple_forwards(self):
        """Test that headers are consistent across multiple forwarding cycles."""
        forwarding_url = self._start_external_service()
        
        custom_headers = {
            "X-Consistent-Header": "consistent-value"
        }
        
        self._start_concentrator_with_forwarding(
            forwarding_url=forwarding_url,
            forwarding_interval=0.1,
            forwarding_headers=custom_headers
        )
        
        # Wait for multiple forwarding cycles
        time.sleep(0.45)
        
        received = self.external_service.get_received_summaries()
        self.assertGreaterEqual(len(received), 3)
        
        # Verify headers are consistent across all received summaries
        for entry in received:
            headers = entry['headers']
            self.assertIn('Content-Type', headers)
            self.assertEqual(headers['Content-Type'], 'application/json')
            self.assertIn('X-Consistent-Header', headers)
            self.assertEqual(headers['X-Consistent-Header'], 'consistent-value')

    def test_no_custom_headers_only_default_content_type(self):
        """Test that only default Content-Type is sent when no custom headers configured."""
        forwarding_url = self._start_external_service()
        
        self._start_concentrator_with_forwarding(
            forwarding_url=forwarding_url,
            forwarding_interval=0.1,
            forwarding_headers=None
        )
        
        # Wait for forwarding
        time.sleep(0.25)
        
        received = self.external_service.get_received_summaries()
        self.assertGreater(len(received), 0)
        
        headers = received[0]['headers']
        
        # Verify Content-Type is present
        self.assertIn('Content-Type', headers)
        self.assertEqual(headers['Content-Type'], 'application/json')


if __name__ == "__main__":
    unittest.main()
