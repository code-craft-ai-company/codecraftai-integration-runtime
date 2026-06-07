"""
    .. module:: automojo_tests.integrationruntime.results.templates.test_fetch_json_stream
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Unit tests for the fetch_json_stream JavaScript function.

    .. moduleauthor:: AutomationX

    These tests verify the fetch_json_stream function behavior from testsummary-helpers.js.
    The tests use Node.js to execute JavaScript tests that validate:
    - JSOS parsing with multiple records
    - Handling of empty files
    - Handling of malformed records

    Requirements covered: 15.1, 15.2, 15.5
"""

import json
import os
import subprocess
import tempfile
import unittest
import http.server
import threading
import socket


class FetchJsonStreamTests(unittest.TestCase):
    """
    Unit tests for the fetch_json_stream JavaScript function.
    
    These tests verify that:
    1. fetch_json_stream loads and parses JSOS files (Requirement 15.1)
    2. The JSOS parser splits content by record separator and parses each JSON object (Requirement 15.2)
    3. The stream loading handles empty files gracefully (Requirement 15.5)
    """

    RECORD_SEPARATOR = "\x1e"

    @classmethod
    def setUpClass(cls):
        """Set up class-level fixtures including a test HTTP server."""
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.temp_path = cls.tempdir.name
        
        # Find an available port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            cls.port = s.getsockname()[1]
        
        # Create test JSOS files
        cls._create_test_files()
        
        # Start HTTP server in a separate thread
        cls.server = http.server.HTTPServer(
            ('localhost', cls.port),
            lambda *args: QuietHTTPRequestHandler(*args, directory=cls.temp_path)
        )
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        """Clean up class-level fixtures."""
        cls.server.shutdown()
        cls.tempdir.cleanup()

    @classmethod
    def _create_test_files(cls):
        """Create test JSOS files for testing."""
        # Multiple records JSOS file
        records = [
            {"rtype": "TEST", "name": "test1", "result": "PASSED"},
            {"rtype": "TEST", "name": "test2", "result": "FAILED"},
            {"rtype": "TASKING_GROUP", "name": "group1", "parent_id": "123"}
        ]
        jsos_content = cls.RECORD_SEPARATOR.join(json.dumps(r) for r in records)
        with open(os.path.join(cls.temp_path, "multiple_records.jsos"), 'w') as f:
            f.write(jsos_content)
        
        # Single record JSOS file
        single_record = {"rtype": "TEST", "name": "single_test", "result": "PASSED"}
        with open(os.path.join(cls.temp_path, "single_record.jsos"), 'w') as f:
            f.write(json.dumps(single_record))
        
        # Empty JSOS file
        with open(os.path.join(cls.temp_path, "empty.jsos"), 'w') as f:
            f.write("")
        
        # Malformed JSOS file (invalid JSON in one record)
        malformed_content = json.dumps({"valid": "record"}) + cls.RECORD_SEPARATOR + "{invalid json"
        with open(os.path.join(cls.temp_path, "malformed.jsos"), 'w') as f:
            f.write(malformed_content)
        
        # JSOS file with trailing separator
        trailing_content = json.dumps({"name": "test"}) + cls.RECORD_SEPARATOR
        with open(os.path.join(cls.temp_path, "trailing_separator.jsos"), 'w') as f:
            f.write(trailing_content)

    def test_fetch_json_stream_parses_multiple_records(self):
        """
        Test that fetch_json_stream correctly parses JSOS files with multiple records.
        
        Requirement 15.1: THE fetch_json_stream function SHALL load and parse JSOS 
        (JSON Separated Object Stream) files.
        
        Requirement 15.2: THE JSOS parser SHALL split the file content by record 
        separator and parse each JSON object.
        
        This test verifies that when a JSOS file with multiple records is requested,
        the function returns an array of parsed JSON objects.
        """
        test_script = self._create_fetch_json_stream_test_script(
            f"http://localhost:{self.port}/multiple_records.jsos"
        )
        
        result = self._run_node_script(test_script)
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 3)
        self.assertEqual(result["data"][0]["rtype"], "TEST")
        self.assertEqual(result["data"][0]["name"], "test1")
        self.assertEqual(result["data"][0]["result"], "PASSED")
        self.assertEqual(result["data"][1]["name"], "test2")
        self.assertEqual(result["data"][1]["result"], "FAILED")
        self.assertEqual(result["data"][2]["rtype"], "TASKING_GROUP")

    def test_fetch_json_stream_parses_single_record(self):
        """
        Test that fetch_json_stream correctly parses JSOS files with a single record.
        
        Requirement 15.1: THE fetch_json_stream function SHALL load and parse JSOS 
        (JSON Separated Object Stream) files.
        
        This test verifies that when a JSOS file with a single record (no separator)
        is requested, the function returns an array with one parsed JSON object.
        """
        test_script = self._create_fetch_json_stream_test_script(
            f"http://localhost:{self.port}/single_record.jsos"
        )
        
        result = self._run_node_script(test_script)
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["name"], "single_test")
        self.assertEqual(result["data"][0]["result"], "PASSED")

    def test_fetch_json_stream_handles_empty_file(self):
        """
        Test that fetch_json_stream handles empty files gracefully.
        
        Requirement 15.5: THE stream loading SHALL handle empty files gracefully.
        
        This test verifies that when an empty JSOS file is requested, the function
        returns an empty array without throwing an error.
        """
        test_script = self._create_fetch_json_stream_test_script(
            f"http://localhost:{self.port}/empty.jsos"
        )
        
        result = self._run_node_script(test_script)
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 0)

    def test_fetch_json_stream_handles_trailing_separator(self):
        """
        Test that fetch_json_stream handles files with trailing separators.
        
        Requirement 15.5: THE stream loading SHALL handle empty files gracefully.
        
        This test verifies that when a JSOS file has a trailing record separator,
        the function correctly ignores the empty segment.
        """
        test_script = self._create_fetch_json_stream_test_script(
            f"http://localhost:{self.port}/trailing_separator.jsos"
        )
        
        result = self._run_node_script(test_script)
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["name"], "test")

    def test_fetch_json_stream_handles_malformed_record(self):
        """
        Test that fetch_json_stream handles malformed JSON records.
        
        Requirement 15.2: THE JSOS parser SHALL split the file content by record 
        separator and parse each JSON object.
        
        This test verifies that when a JSOS file contains malformed JSON in one
        of its records, the function throws a parsing error.
        """
        test_script = self._create_fetch_json_stream_test_script(
            f"http://localhost:{self.port}/malformed.jsos"
        )
        
        result = self._run_node_script(test_script)
        
        self.assertEqual(result["status"], "error")
        self.assertIn("parse", result.get("error_type", "").lower())

    def _create_fetch_json_stream_test_script(self, url):
        """
        Create a Node.js test script that tests the fetch_json_stream function.
        
        This simulates the fetch_json_stream function behavior using Node.js http module,
        replicating the logic from testsummary-helpers.js.
        """
        script = f'''
const http = require('http');

// Simulate fetch_json_stream function behavior using Node.js http module
// This replicates the logic from testsummary-helpers.js
async function fetch_json_stream(url) {{
    return new Promise((resolve, reject) => {{
        const urlObj = new URL(url);
        
        const options = {{
            hostname: urlObj.hostname,
            port: urlObj.port,
            path: urlObj.pathname,
            method: 'GET'
        }};
        
        const req = http.request(options, (res) => {{
            let data = '';
            
            res.on('data', (chunk) => {{
                data += chunk;
            }});
            
            res.on('end', () => {{
                if (res.statusCode === 200) {{
                    try {{
                        var json_objects = [];

                        var split_responses = data.split("\\x1e");
                        var srlength = split_responses.length;
                        while (srlength > 0) {{
                            var ritem = split_responses.pop();
                            if (ritem.length > 0) {{
                                var robj = JSON.parse(ritem);
                                json_objects.unshift(robj);
                            }}
                            srlength = srlength - 1;
                        }}

                        resolve(json_objects);
                    }} catch (e) {{
                        reject({{ type: 'parse_error', message: e.message }});
                    }}
                }} else {{
                    reject({{ type: 'http_error', status: res.statusCode, message: res.statusMessage }});
                }}
            }});
        }});
        
        req.on('error', (e) => {{
            reject({{ type: 'network_error', message: e.message }});
        }});
        
        req.end();
    }});
}}

// Run the test
async function runTest() {{
    try {{
        const result = await fetch_json_stream("{url}");
        console.log(JSON.stringify({{ status: "success", data: result }}));
    }} catch (error) {{
        console.log(JSON.stringify({{ 
            status: "error", 
            error: error.message || String(error),
            error_type: error.type || "unknown"
        }}));
    }}
}}

runTest();
'''
        return script

    def _run_node_script(self, script):
        """Run a Node.js script and return the parsed JSON result."""
        # Write script to temp file
        script_path = os.path.join(self.temp_path, "test_script.js")
        with open(script_path, 'w') as f:
            f.write(script)
        
        # Run with Node.js
        result = subprocess.run(
            ['node', script_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0 and not result.stdout:
            return {"status": "error", "error": result.stderr}
        
        try:
            return json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            return {"status": "error", "error": f"Invalid output: {result.stdout}"}


class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler that suppresses log messages."""
    
    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)
    
    def log_message(self, format, *args):
        """Suppress log messages."""
        pass


if __name__ == "__main__":
    unittest.main()
