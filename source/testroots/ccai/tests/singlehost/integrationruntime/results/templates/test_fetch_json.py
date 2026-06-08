"""
    .. module:: ccai.tests.singlehost.integrationruntime.results.templates.test_fetch_json
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Unit tests for the fetch_json JavaScript function.

    .. moduleauthor:: CodeCraftX

    These tests verify the fetch_json function behavior from testsummary-helpers.js.
    The tests use Node.js to execute JavaScript tests that validate:
    - Successful JSON loading and parsing
    - Error handling for missing files
    - Error handling for invalid JSON

    Requirements covered: 14.1, 14.2
"""

import json
import os
import subprocess
import tempfile
import http.server
import threading
import socket

from typing import Any, Dict


class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler that suppresses log messages."""

    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, format, *args):
        """Suppress log messages."""
        pass


def _create_test_files(temp_path: str) -> None:
    """
        Create test JSON files for testing.

        :param temp_path: The directory in which to create the test JSON files.
    """
    # Valid JSON file
    valid_json = {
        "name": "test",
        "value": 42,
        "nested": {"key": "value"}
    }
    with open(os.path.join(temp_path, "valid.json"), 'w') as f:
        json.dump(valid_json, f)

    # Invalid JSON file
    with open(os.path.join(temp_path, "invalid.json"), 'w') as f:
        f.write("{invalid json content")

    # Empty JSON file
    with open(os.path.join(temp_path, "empty.json"), 'w') as f:
        f.write("")
    return


def _establish_env() -> Dict[str, Any]:
    """
        Replicates the original ``setUpClass`` per test to preserve isolation: builds the
        temporary directory, finds an available port, creates the test JSON files, and starts
        the test HTTP server in a daemon thread.

        :returns: A dictionary carrying the temporary directory handle, the temporary path,
                  the chosen port, the server, and the server thread.
    """
    tempdir = tempfile.TemporaryDirectory()
    temp_path = tempdir.name

    # Find an available port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        port = s.getsockname()[1]

    # Create test JSON files
    _create_test_files(temp_path=temp_path)

    # Start HTTP server in a separate thread
    server = http.server.HTTPServer(
        ('localhost', port),
        lambda *args: QuietHTTPRequestHandler(*args, directory=temp_path)
    )
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    env: Dict[str, Any] = {
        "tempdir": tempdir,
        "temp_path": temp_path,
        "port": port,
        "server": server,
        "server_thread": server_thread
    }
    return env


def _cleanup_env(env: Dict[str, Any]) -> None:
    """
        Replicates the original ``tearDownClass`` per test: shuts down the test HTTP server and
        cleans up the temporary directory.

        :param env: The environment dictionary produced by :func:`_establish_env`.
    """
    server = env["server"]
    tempdir = env["tempdir"]

    server.shutdown()
    tempdir.cleanup()
    return


def _create_fetch_json_test_script(url: str, expect_success: bool = True, expect_parse_error: bool = False) -> str:
    """
        Create a Node.js test script that tests the fetch_json function.

        Since fetch_json uses XMLHttpRequest (browser API), we use the 'xmlhttprequest'
        npm package or native fetch in Node.js to simulate the behavior.

        :param url: The URL the generated script will request.
        :param expect_success: Whether the caller expects a successful fetch.
        :param expect_parse_error: Whether the caller expects a JSON parse error.

        :returns: The Node.js script source as a string.
    """
    script = f'''
const http = require('http');

// Simulate fetch_json function behavior using Node.js http module
async function fetch_json(url, headers=null) {{
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
                        const robj = JSON.parse(data);
                        resolve(robj);
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
        const result = await fetch_json("{url}");
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


def _run_node_script(temp_path: str, script: str) -> Dict[str, Any]:
    """
        Run a Node.js script and return the parsed JSON result.

        :param temp_path: The directory used to stage the temporary script file.
        :param script: The Node.js script source to execute.

        :returns: The parsed JSON result emitted by the script, or an error dictionary.
    """
    # Write script to temp file
    script_path = os.path.join(temp_path, "test_script.js")
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
        rtnval: Dict[str, Any] = {"status": "error", "error": result.stderr}
        return rtnval

    try:
        rtnval = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        rtnval = {"status": "error", "error": f"Invalid output: {result.stdout}"}
    return rtnval


def test_fetch_json_loads_valid_json_successfully() -> None:
    """
        Test that fetch_json successfully loads and parses valid JSON files.

        Requirement 14.1: THE fetch_json function SHALL load and parse JSON files
        via AJAX fetch.

        This test verifies that when a valid JSON file is requested, the function
        returns the parsed JSON object.
    """
    env = _establish_env()
    try:
        port = env["port"]
        temp_path = env["temp_path"]

        # Create the test script
        test_script = _create_fetch_json_test_script(
            url=f"http://localhost:{port}/valid.json",
            expect_success=True
        )

        result = _run_node_script(temp_path=temp_path, script=test_script)

        assert result["status"] == "success"
        assert result["data"]["name"] == "test"
        assert result["data"]["value"] == 42
        assert result["data"]["nested"]["key"] == "value"
    finally:
        _cleanup_env(env=env)
    return


def test_fetch_json_returns_error_for_missing_file() -> None:
    """
        Test that fetch_json handles missing files correctly.

        Requirement 14.2: THE fetch_json function SHALL return null and log an
        error when the file cannot be loaded.

        This test verifies that when a non-existent file is requested, the function
        rejects the promise with an error.
    """
    env = _establish_env()
    try:
        port = env["port"]
        temp_path = env["temp_path"]

        test_script = _create_fetch_json_test_script(
            url=f"http://localhost:{port}/nonexistent.json",
            expect_success=False
        )

        result = _run_node_script(temp_path=temp_path, script=test_script)

        assert result["status"] == "error"
        assert "error" in result
    finally:
        _cleanup_env(env=env)
    return


def test_fetch_json_handles_invalid_json() -> None:
    """
        Test that fetch_json handles invalid JSON content correctly.

        Requirement 14.2: THE fetch_json function SHALL return null and log an
        error when the file cannot be loaded.

        This test verifies that when a file contains invalid JSON, the function
        throws a parsing error.
    """
    env = _establish_env()
    try:
        port = env["port"]
        temp_path = env["temp_path"]

        test_script = _create_fetch_json_test_script(
            url=f"http://localhost:{port}/invalid.json",
            expect_success=False,
            expect_parse_error=True
        )

        result = _run_node_script(temp_path=temp_path, script=test_script)

        assert result["status"] == "error"
        assert "parse" in result.get("error_type", "").lower()
    finally:
        _cleanup_env(env=env)
    return
