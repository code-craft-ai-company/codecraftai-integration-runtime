"""
    .. module:: ccai_tests.testbase.results.concentrators.test_progress_forwarding_integration
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Integration tests for progress forwarding functionality.

    This module contains integration tests that verify the complete flow of:
    1. Remote task progress reception via HTTP POST
    2. Summary forwarding to external services

    These tests validate Requirements 40.1-40.6 for the progress forwarding thread.

    .. moduleauthor:: CodeCraftX
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


class ProgressForwardingIntegrationTestBase(unittest.TestCase):
    """Base class for progress forwarding integration tests."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        self.render_info = RenderInfo(
            title="Progress Forwarding Integration Test",
            summary_filename=os.path.join(self.temp_dir, "summary.json"),
            summary_template=os.path.join(self.temp_dir, "template.html"),
            stream_results_filename=os.path.join(self.temp_dir, "results.json"),
            consolidated_results_filename=os.path.join(self.temp_dir, "consolidated.json"),
            static_resource_source=None,
            static_resource_destination=self.temp_dir
        )
        
        with open(self.render_info.summary_template, 'w') as f:
            f.write("<html></html>")
        
        self.runid = str(uuid.uuid4())
        self.start_time = datetime.now()

        self.build_info = BuildInfo(
            branch="main",
            build="build-progress-forwarding",
            flavor="release",
            release="1.0.0",
            url="https://ci.example.com/build/progress-forwarding"
        )
        
        self.pipeline_info = PipelineInfo(
            id="pipeline-progress-forwarding",
            name="Progress Forwarding Pipeline",
            instance="instance-progress-forwarding"
        )
        
        self.job_info = JobInfo(
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
        
        self.recorder = JsonResultRecorder(
            runid=self.runid,
            start=self.start_time,
            render_info=self.render_info,
            build_info=self.build_info,
            pipeline_info=self.pipeline_info,
            job_info=self.job_info
        )
        
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
                        # Best-effort teardown; the forwarding thread is a daemon, so a failed join must not block the remaining cleanup.
                        pass
            except Exception:
                # Best-effort teardown; a server that never started or is already closed must not block the remaining cleanup.
                pass
        
        if self.external_service is not None:
            try:
                self.external_service.stop()
            except Exception:
                # Best-effort teardown; a mock service that is already stopped must not block the remaining cleanup.
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

    def _find_unused_port(self) -> int:
        """Find an unused port for testing."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            return s.getsockname()[1]




class RemoteTaskProgressReceptionTests(ProgressForwardingIntegrationTestBase):
    """Integration tests for remote task progress reception (Requirements 39.1-39.7, 40.1-40.6).
    
    These tests verify that remote workers can send progress updates to the concentrator
    server and that these updates are properly aggregated and forwarded to external services.
    """

    def test_remote_worker_progress_received_and_forwarded(self):
        """Test that progress from remote workers is received and forwarded to external service.
        
        This test validates the complete flow:
        1. Remote worker sends progress update to concentrator (Req 39.1-39.6)
        2. Concentrator aggregates progress in recorder (Req 39.5)
        3. Forwarding thread sends summary to external service (Req 40.2, 40.3)
        
        Requirements: 39.1-39.6, 40.2, 40.3
        """
        forwarding_url = self._start_external_service()
        concentrator_port = self._start_concentrator_with_forwarding(
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )
        
        # Simulate remote worker sending progress updates
        task_id = "remote-worker-task-1"
        worker_id = "remote-worker-001"
        
        payload = self._create_progress_payload(
            task_id=task_id,
            worker_id=worker_id,
            status="Running",
            position="3"
        )
        
        status_code = self._send_progress_update(concentrator_port, payload)
        self.assertEqual(status_code, 200, "Progress update should be accepted")
        
        # Wait for forwarding to occur
        time.sleep(0.25)
        
        # Verify progress was forwarded to external service
        received = self.external_service.get_received_summaries()
        self.assertGreater(len(received), 0, "External service should receive forwarded summaries")
        
        # Find a summary containing our task
        found_task = False
        for entry in received:
            running = entry['summary'].get('running', {})
            if task_id in running:
                found_task = True
                self.assertEqual(running[task_id]['position'], "3")
                self.assertEqual(running[task_id]['status'], "Running")
                break
        
        self.assertTrue(found_task, "Remote worker's task should appear in forwarded summary")

    def test_multiple_remote_workers_progress_aggregated(self):
        """Test that progress from multiple remote workers is aggregated and forwarded.
        
        Requirements: 39.5, 40.2, 40.3
        """
        forwarding_url = self._start_external_service()
        concentrator_port = self._start_concentrator_with_forwarding(
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
            
            payload = self._create_progress_payload(
                task_id=task_id,
                worker_id=worker_id,
                status="Running",
                position=str(i * 2)
            )
            
            status_code = self._send_progress_update(concentrator_port, payload)
            self.assertEqual(status_code, 200)
        
        # Wait for forwarding
        time.sleep(0.25)
        
        # Verify all workers' progress is in forwarded summary
        received = self.external_service.get_received_summaries()
        self.assertGreater(len(received), 0)
        
        # Find a summary with all tasks
        found_all = False
        for entry in received:
            running = entry['summary'].get('running', {})
            if all(tid in running for tid in worker_tasks.keys()):
                found_all = True
                # Verify each task's data
                for i, (task_id, worker_id) in enumerate(worker_tasks.items()):
                    self.assertEqual(running[task_id]['position'], str(i * 2))
                break
        
        self.assertTrue(found_all, "All remote workers' tasks should be in forwarded summary")

    def test_concurrent_remote_workers_progress_reception(self):
        """Test concurrent progress reception from multiple remote workers.
        
        Requirements: 39.1-39.6, 40.2, 40.3
        """
        forwarding_url = self._start_external_service()
        concentrator_port = self._start_concentrator_with_forwarding(
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
                payload = self._create_progress_payload(
                    task_id=task_id,
                    worker_id=f"concurrent-worker-{worker_num}",
                    status="Running",
                    position=str(i)
                )
                try:
                    status_code = self._send_progress_update(concentrator_port, payload)
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
        self.assertEqual(len(errors), 0, f"Errors during concurrent reception: {errors}")
        
        # Verify all updates succeeded
        self.assertEqual(len(results), num_workers * updates_per_worker)
        for task_id, status_code in results:
            self.assertEqual(status_code, 200, f"Task {task_id} should succeed")
        
        # Wait for forwarding
        time.sleep(0.25)
        
        # Verify external service received summaries
        received = self.external_service.get_received_summaries()
        self.assertGreater(len(received), 0, "External service should receive forwarded summaries")


class ForwardingThreadDaemonTests(ProgressForwardingIntegrationTestBase):
    """Integration tests for forwarding thread daemon behavior (Requirement 40.1)."""

    def test_forwarding_thread_is_daemon(self):
        """Test that the forwarding thread runs as a daemon thread.
        
        Requirement: 40.1 - THE forwarding thread SHALL run as a daemon thread
        """
        forwarding_url = self._start_external_service()
        self._start_concentrator_with_forwarding(
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )
        
        # Verify forwarding thread is a daemon
        self.assertIsNotNone(self.concentrator_server._forward_thread)
        self.assertTrue(self.concentrator_server._forward_thread.daemon,
            "Forwarding thread should be a daemon thread")

    def test_server_thread_is_daemon(self):
        """Test that the server thread also runs as a daemon thread.
        
        Requirement: 40.1 (related)
        """
        forwarding_url = self._start_external_service()
        self._start_concentrator_with_forwarding(
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )
        
        # Verify server thread is a daemon
        self.assertIsNotNone(self.concentrator_server._server_thread)
        self.assertTrue(self.concentrator_server._server_thread.daemon,
            "Server thread should be a daemon thread")


class ForwardingIntervalTests(ProgressForwardingIntegrationTestBase):
    """Integration tests for forwarding interval behavior (Requirement 40.4)."""

    def test_forwarding_uses_configured_interval(self):
        """Test that forwarding uses the configured interval between posts.
        
        Requirement: 40.4 - THE forwarding thread SHALL use the configured 
        forwarding_interval between posts
        """
        forwarding_url = self._start_external_service()
        forwarding_interval = 0.15
        
        self._start_concentrator_with_forwarding(
            forwarding_url=forwarding_url,
            forwarding_interval=forwarding_interval
        )
        
        # Wait for multiple forwarding cycles
        time.sleep(forwarding_interval * 5 + 0.1)
        
        received = self.external_service.get_received_summaries()
        
        # Should have received at least 4 summaries
        self.assertGreaterEqual(len(received), 4,
            f"Expected at least 4 summaries, got {len(received)}")
        
        # Verify timing between summaries
        if len(received) >= 2:
            for i in range(1, len(received)):
                interval = received[i]['timestamp'] - received[i-1]['timestamp']
                # Allow 50% tolerance for timing variations
                self.assertGreaterEqual(interval, forwarding_interval * 0.5,
                    f"Interval {interval} too short, expected ~{forwarding_interval}")
                self.assertLessEqual(interval, forwarding_interval * 2.0,
                    f"Interval {interval} too long, expected ~{forwarding_interval}")

    def test_different_forwarding_intervals(self):
        """Test that different forwarding intervals work correctly.
        
        Requirement: 40.4
        """
        forwarding_url = self._start_external_service()
        
        # Test with a shorter interval
        short_interval = 0.08
        self._start_concentrator_with_forwarding(
            forwarding_url=forwarding_url,
            forwarding_interval=short_interval
        )
        
        time.sleep(0.4)
        
        received = self.external_service.get_received_summaries()
        
        # With 0.08s interval over 0.4s, should have at least 4 summaries
        self.assertGreaterEqual(len(received), 4,
            f"Expected at least 4 summaries with short interval, got {len(received)}")


class ForwardingHeadersTests(ProgressForwardingIntegrationTestBase):
    """Integration tests for forwarding headers (Requirement 40.5)."""

    def test_forwarding_includes_custom_headers(self):
        """Test that forwarding includes configured custom headers.
        
        Requirement: 40.5 - THE forwarding thread SHALL include forwarding_headers 
        in the POST request if configured
        """
        forwarding_url = self._start_external_service()
        
        custom_headers = {
            "Authorization": "Bearer test-token-12345",
            "X-Correlation-Id": "correlation-abc-123",
            "X-Worker-Pool": "integration-test-pool"
        }
        
        self._start_concentrator_with_forwarding(
            forwarding_url=forwarding_url,
            forwarding_interval=0.1,
            forwarding_headers=custom_headers
        )
        
        time.sleep(0.25)
        
        received = self.external_service.get_received_summaries()
        self.assertGreater(len(received), 0)
        
        headers = received[0]['headers']
        
        # Verify all custom headers are present
        for key, value in custom_headers.items():
            self.assertIn(key, headers, f"Header {key} should be present")
            self.assertEqual(headers[key], value, f"Header {key} should have correct value")

    def test_forwarding_includes_content_type_header(self):
        """Test that forwarding always includes Content-Type header.
        
        Requirement: 40.5 (implicit - JSON content type)
        """
        forwarding_url = self._start_external_service()
        
        self._start_concentrator_with_forwarding(
            forwarding_url=forwarding_url,
            forwarding_interval=0.1,
            forwarding_headers=None
        )
        
        time.sleep(0.25)
        
        received = self.external_service.get_received_summaries()
        self.assertGreater(len(received), 0)
        
        headers = received[0]['headers']
        self.assertIn('Content-Type', headers)
        self.assertEqual(headers['Content-Type'], 'application/json')


class ForwardingErrorRecoveryTests(ProgressForwardingIntegrationTestBase):
    """Integration tests for forwarding error recovery (Requirement 40.6)."""

    def test_forwarding_continues_after_network_error(self):
        """Test that forwarding continues after network errors.
        
        Requirement: 40.6 - THE forwarding thread SHALL log errors and continue on failure
        """
        # Use a port that nothing is listening on
        unused_port = self._find_unused_port()
        forwarding_url = f"http://127.0.0.1:{unused_port}/api/progress"
        
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url=forwarding_url,
            forwarding_headers=None
        )
        
        self.concentrator_server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.concentrator_address,
            forwarding_info=forwarding_info
        )
        self.concentrator_server.start()
        
        # Wait for multiple failed forwarding attempts
        time.sleep(0.25)
        
        # Verify forwarding thread is still running
        self.assertTrue(self.concentrator_server._forwarding_running,
            "Forwarding should still be running after errors")
        self.assertTrue(self.concentrator_server._forward_thread.is_alive(),
            "Forwarding thread should still be alive after errors")

    def test_forwarding_logs_errors(self):
        """Test that forwarding errors are logged.
        
        Requirement: 40.6 - THE forwarding thread SHALL log errors
        """
        unused_port = self._find_unused_port()
        forwarding_url = f"http://127.0.0.1:{unused_port}/api/progress"
        
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url=forwarding_url,
            forwarding_headers=None
        )
        
        self.concentrator_server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.concentrator_address,
            forwarding_info=forwarding_info
        )
        
        # Capture logged errors
        logged_errors = []
        original_warning = self.concentrator_server._logger.warning
        
        def capture_error(msg):
            logged_errors.append(msg)
        
        self.concentrator_server._logger.warning = capture_error
        
        try:
            self.concentrator_server.start()
            
            # Wait for forwarding attempts
            time.sleep(0.2)
            
            # Verify errors were logged
            self.assertGreater(len(logged_errors), 0,
                "Forwarding errors should be logged")
        finally:
            self.concentrator_server._logger.warning = original_warning

    def test_progress_reception_unaffected_by_forwarding_errors(self):
        """Test that progress reception continues during forwarding errors.
        
        Requirement: 40.6 (related - system stability)
        """
        unused_port = self._find_unused_port()
        forwarding_url = f"http://127.0.0.1:{unused_port}/api/progress"
        
        forwarding_info = ForwardingInfo(
            forwarding_interval=0.05,
            forwarding_url=forwarding_url,
            forwarding_headers=None
        )
        
        self.concentrator_server = ProgressConcentratorServer(
            recorder=self.recorder,
            server_address=self.concentrator_address,
            forwarding_info=forwarding_info
        )
        self.concentrator_server.start()
        concentrator_port = self.concentrator_server.server_address[1]
        
        # Send progress updates while forwarding is failing
        for i in range(5):
            payload = self._create_progress_payload(
                task_id=f"during-error-{i}",
                worker_id="error-test-worker",
                status="Running"
            )
            status_code = self._send_progress_update(concentrator_port, payload)
            self.assertEqual(status_code, 200,
                "Progress reception should work during forwarding errors")
        
        # Verify tasks were recorded
        for i in range(5):
            self.assertIn(f"during-error-{i}", self.recorder._running_tasks)


class EndToEndProgressForwardingTests(ProgressForwardingIntegrationTestBase):
    """End-to-end integration tests for the complete progress forwarding flow."""

    def test_complete_progress_lifecycle_forwarded(self):
        """Test that complete task lifecycle (start, update, complete) is forwarded.
        
        Requirements: 39.1-39.6, 40.1-40.6
        """
        forwarding_url = self._start_external_service()
        concentrator_port = self._start_concentrator_with_forwarding(
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )
        
        task_id = "lifecycle-task"
        worker_id = "lifecycle-worker"
        
        # Start task
        start_payload = self._create_progress_payload(
            task_id=task_id,
            worker_id=worker_id,
            status="Running",
            position="0"
        )
        self._send_progress_update(concentrator_port, start_payload)
        
        time.sleep(0.15)
        
        # Verify task appears in forwarded summary
        received = self.external_service.get_received_summaries()
        found_running = False
        for entry in received:
            running = entry['summary'].get('running', {})
            if task_id in running and running[task_id]['status'] == "Running":
                found_running = True
                break
        self.assertTrue(found_running, "Running task should appear in forwarded summary")
        
        # Update task progress
        update_payload = self._create_progress_payload(
            task_id=task_id,
            worker_id=worker_id,
            status="Running",
            position="5"
        )
        self._send_progress_update(concentrator_port, update_payload)
        
        time.sleep(0.15)
        
        # Complete task
        complete_payload = self._create_progress_payload(
            task_id=task_id,
            worker_id=worker_id,
            status="Completed",
            position="10"
        )
        self._send_progress_update(concentrator_port, complete_payload)
        
        # Clear and wait for new summaries
        self.external_service.clear_received_summaries()
        time.sleep(0.25)
        
        # Verify completed task is removed from forwarded summary
        received = self.external_service.get_received_summaries()
        self.assertGreater(len(received), 0)
        
        latest_summary = received[-1]['summary']
        running = latest_summary.get('running', {})
        self.assertNotIn(task_id, running,
            "Completed task should not appear in forwarded summary")

    def test_high_volume_progress_forwarding(self):
        """Test forwarding under high volume of progress updates.
        
        Requirements: 39.1-39.6, 40.1-40.6
        """
        forwarding_url = self._start_external_service()
        concentrator_port = self._start_concentrator_with_forwarding(
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )
        
        num_tasks = 50
        
        # Send many progress updates rapidly
        for i in range(num_tasks):
            payload = self._create_progress_payload(
                task_id=f"high-volume-{i}",
                worker_id=f"worker-{i % 5}",
                status="Running",
                position=str(i)
            )
            status_code = self._send_progress_update(concentrator_port, payload)
            self.assertEqual(status_code, 200)
        
        # Wait for forwarding
        time.sleep(0.3)
        
        # Verify external service received summaries
        received = self.external_service.get_received_summaries()
        self.assertGreater(len(received), 0)
        
        # Verify tasks are in the latest summary
        latest_summary = received[-1]['summary']
        running = latest_summary.get('running', {})
        
        # Should have all tasks
        self.assertEqual(len(running), num_tasks,
            f"Expected {num_tasks} tasks in summary, got {len(running)}")

    def test_summary_metadata_forwarded_correctly(self):
        """Test that summary metadata is forwarded correctly.
        
        Requirements: 40.2, 40.3
        """
        forwarding_url = self._start_external_service()
        self._start_concentrator_with_forwarding(
            forwarding_url=forwarding_url,
            forwarding_interval=0.1
        )
        
        time.sleep(0.25)
        
        received = self.external_service.get_received_summaries()
        self.assertGreater(len(received), 0)
        
        summary = received[0]['summary']
        
        # Verify metadata fields
        self.assertEqual(summary['runid'], self.runid)
        self.assertIn('build', summary)
        self.assertEqual(summary['build']['branch'], 'main')
        self.assertEqual(summary['build']['build'], 'build-progress-forwarding')
        
        self.assertIn('pipeline', summary)
        self.assertEqual(summary['pipeline']['name'], 'Progress Forwarding Pipeline')
        
        self.assertIn('job', summary)
        self.assertEqual(summary['job']['name'], 'Progress Forwarding Tests')


if __name__ == "__main__":
    unittest.main()
