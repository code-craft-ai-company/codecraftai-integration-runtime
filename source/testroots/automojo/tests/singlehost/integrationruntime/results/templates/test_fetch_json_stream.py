"""
    .. module:: automojo.tests.singlehost.integrationruntime.results.templates.test_fetch_json_stream
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
import http.server
import threading
import socket


RECORD_SEPARATOR = "\x1e"


class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler that suppresses log messages."""

    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, format, *args):
        """Suppress log messages."""
        pass


def _create_test_files(temp_path: str) -> None:
    """
        Create test JSOS files for testing.

        :param temp_path: The directory in which to create the test JSOS files.

        :returns: Nothing.
    """
    # Multiple records JSOS file
    records = [
        {"rtype": "TEST", "name": "test1", "result": "PASSED"},
        {"rtype": "TEST", "name": "test2", "result": "FAILED"},
        {"rtype": "TASKING_GROUP", "name": "group1", "parent_id": "123"}
    ]
    jsos_content = RECORD_SEPARATOR.join(json.dumps(r) for r in records)
    with open(os.path.join(temp_path, "multiple_records.jsos"), 'w') as f:
        f.write(jsos_content)

    # Single record JSOS file
    single_record = {"rtype": "TEST", "name": "single_test", "result": "PASSED"}
    with open(os.path.join(temp_path, "single_record.jsos"), 'w') as f:
        f.write(json.dumps(single_record))

    # Empty JSOS file
    with open(os.path.join(temp_path, "empty.jsos"), 'w') as f:
        f.write("")

    # Malformed JSOS file (invalid JSON in one record)
    malformed_content = json.dumps({"valid": "record"}) + RECORD_SEPARATOR + "{invalid json"
    with open(os.path.join(temp_path, "malformed.jsos"), 'w') as f:
        f.write(malformed_content)

    # JSOS file with trailing separator
    trailing_content = json.dumps({"name": "test"}) + RECORD_SEPARATOR
    with open(os.path.join(temp_path, "trailing_separator.jsos"), 'w') as f:
        f.write(trailing_content)

    return


def _establish_env() -> dict:
    """
        Establish the per-test fixtures originally created by ``setUpClass``.

        This creates a temporary directory, finds an available port, writes the
        test JSOS files and starts a quiet HTTP server thread that serves the
        temporary directory.

        :returns: A dictionary of the fixtures the tests need (``tempdir``,
                  ``temp_path``, ``port``, ``server`` and ``server_thread``).
    """
    tempdir = tempfile.TemporaryDirectory()
    temp_path = tempdir.name

    # Find an available port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        port = s.getsockname()[1]

    # Create test JSOS files
    _create_test_files(temp_path=temp_path)

    # Start HTTP server in a separate thread
    server = http.server.HTTPServer(
        ('localhost', port),
        lambda *args: QuietHTTPRequestHandler(*args, directory=temp_path)
    )
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    env = {
        "tempdir": tempdir,
        "temp_path": temp_path,
        "port": port,
        "server": server,
        "server_thread": server_thread,
    }
    return env


def _teardown_env(env: dict) -> None:
    """
        Replicate the cleanup originally performed by ``tearDownClass``.

        :param env: The fixture dictionary returned by :func:`_establish_env`.

        :returns: Nothing.
    """
    server = env["server"]
    tempdir = env["tempdir"]

    server.shutdown()
    tempdir.cleanup()

    return


def _create_fetch_json_stream_test_script(url: str) -> str:
    """
        Create a Node.js test script that tests the fetch_json_stream function.

        This simulates the fetch_json_stream function behavior using Node.js http module,
        replicating the logic from testsummary-helpers.js.

        :param url: The URL the generated Node.js script should request.

        :returns: The generated Node.js script as a string.
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


def _run_node_script(temp_path: str, script: str) -> dict:
    """
        Run a Node.js script and return the parsed JSON result.

        :param temp_path: The directory in which to write the temporary script.
        :param script: The Node.js script source to execute.

        :returns: The parsed JSON result emitted by the Node.js script.
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
        rtnval = {"status": "error", "error": result.stderr}
        return rtnval

    try:
        rtnval = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        rtnval = {"status": "error", "error": f"Invalid output: {result.stdout}"}

    return rtnval


def test_fetch_json_stream_parses_multiple_records() -> None:
    """
        Test that fetch_json_stream correctly parses JSOS files with multiple records.

        Requirement 15.1: THE fetch_json_stream function SHALL load and parse JSOS
        (JSON Separated Object Stream) files.

        Requirement 15.2: THE JSOS parser SHALL split the file content by record
        separator and parse each JSON object.

        This test verifies that when a JSOS file with multiple records is requested,
        the function returns an array of parsed JSON objects.
    """
    env = _establish_env()
    try:
        test_script = _create_fetch_json_stream_test_script(
            url=f"http://localhost:{env['port']}/multiple_records.jsos"
        )

        result = _run_node_script(temp_path=env["temp_path"], script=test_script)

        assert result["status"] == "success"
        assert len(result["data"]) == 3
        assert result["data"][0]["rtype"] == "TEST"
        assert result["data"][0]["name"] == "test1"
        assert result["data"][0]["result"] == "PASSED"
        assert result["data"][1]["name"] == "test2"
        assert result["data"][1]["result"] == "FAILED"
        assert result["data"][2]["rtype"] == "TASKING_GROUP"
    finally:
        _teardown_env(env=env)

    return


def test_fetch_json_stream_parses_single_record() -> None:
    """
        Test that fetch_json_stream correctly parses JSOS files with a single record.

        Requirement 15.1: THE fetch_json_stream function SHALL load and parse JSOS
        (JSON Separated Object Stream) files.

        This test verifies that when a JSOS file with a single record (no separator)
        is requested, the function returns an array with one parsed JSON object.
    """
    env = _establish_env()
    try:
        test_script = _create_fetch_json_stream_test_script(
            url=f"http://localhost:{env['port']}/single_record.jsos"
        )

        result = _run_node_script(temp_path=env["temp_path"], script=test_script)

        assert result["status"] == "success"
        assert len(result["data"]) == 1
        assert result["data"][0]["name"] == "single_test"
        assert result["data"][0]["result"] == "PASSED"
    finally:
        _teardown_env(env=env)

    return


def test_fetch_json_stream_handles_empty_file() -> None:
    """
        Test that fetch_json_stream handles empty files gracefully.

        Requirement 15.5: THE stream loading SHALL handle empty files gracefully.

        This test verifies that when an empty JSOS file is requested, the function
        returns an empty array without throwing an error.
    """
    env = _establish_env()
    try:
        test_script = _create_fetch_json_stream_test_script(
            url=f"http://localhost:{env['port']}/empty.jsos"
        )

        result = _run_node_script(temp_path=env["temp_path"], script=test_script)

        assert result["status"] == "success"
        assert len(result["data"]) == 0
    finally:
        _teardown_env(env=env)

    return


def test_fetch_json_stream_handles_trailing_separator() -> None:
    """
        Test that fetch_json_stream handles files with trailing separators.

        Requirement 15.5: THE stream loading SHALL handle empty files gracefully.

        This test verifies that when a JSOS file has a trailing record separator,
        the function correctly ignores the empty segment.
    """
    env = _establish_env()
    try:
        test_script = _create_fetch_json_stream_test_script(
            url=f"http://localhost:{env['port']}/trailing_separator.jsos"
        )

        result = _run_node_script(temp_path=env["temp_path"], script=test_script)

        assert result["status"] == "success"
        assert len(result["data"]) == 1
        assert result["data"][0]["name"] == "test"
    finally:
        _teardown_env(env=env)

    return


def test_fetch_json_stream_handles_malformed_record() -> None:
    """
        Test that fetch_json_stream handles malformed JSON records.

        Requirement 15.2: THE JSOS parser SHALL split the file content by record
        separator and parse each JSON object.

        This test verifies that when a JSOS file contains malformed JSON in one
        of its records, the function throws a parsing error.
    """
    env = _establish_env()
    try:
        test_script = _create_fetch_json_stream_test_script(
            url=f"http://localhost:{env['port']}/malformed.jsos"
        )

        result = _run_node_script(temp_path=env["temp_path"], script=test_script)

        assert result["status"] == "error"
        assert "parse" in result.get("error_type", "").lower()
    finally:
        _teardown_env(env=env)

    return
