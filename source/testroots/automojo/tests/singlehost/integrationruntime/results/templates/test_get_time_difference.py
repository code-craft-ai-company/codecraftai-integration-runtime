"""
    .. module:: automojo.tests.singlehost.integrationruntime.results.templates.test_get_time_difference
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Unit tests for the get_time_difference JavaScript function.

    .. moduleauthor:: AutomationX

    These tests verify the get_time_difference function behavior from testsummary-helpers.js.
    The tests use Node.js to execute JavaScript tests that validate:
    - Duration calculation between start and stop times
    - Formatting of hours, minutes, and seconds

    Requirements covered: 29.1, 29.2
"""

import json
import os
import subprocess
import tempfile

from typing import Any, Dict


def _create_get_time_difference_test_script(start: str, stop: str) -> str:
    """
        Create a Node.js test script that tests the get_time_difference function.

        This replicates the get_time_difference function from testsummary-helpers.js.

        :param start: The start timestamp string to feed to the JavaScript function.
        :param stop: The stop timestamp string to feed to the JavaScript function.

        :returns: The generated Node.js test script source.
    """
    script = f'''
// Replicate the get_time_difference function from testsummary-helpers.js
const DATETIME_FORMAT = "yyyy-MM-ddTHH:mm:ss.ssssss";

function get_time_difference(start, stop) {{
    var startTimeStamp = Date.parse(start, DATETIME_FORMAT) / 1000;
    var stopTimeStamp = Date.parse(stop, DATETIME_FORMAT) / 1000;

    var elapsedTime = stopTimeStamp - startTimeStamp;

    var diff = "";

    if (elapsedTime > 1) {{
        var seconds = elapsedTime;
        var minutes = null;
        var hours = null;
        var days = null;

        if (seconds > 60) {{
            var minutes = Math.floor(seconds / 60);
            seconds = seconds - (minutes * 60);

            if (minutes > 60) {{
                var hours = Math.floor(minutes / 60);
                minutes = minutes % 60;

                if (hours > 24) {{
                    var days = Math.floor(hours / 20);
                    hours = hours % 24;
                    diff = days.toString() + "d";
                }}

                diff += hours.toString() + "h";
            }}

            diff += minutes.toString() + "m";
        }}

        diff += seconds.toFixed(4) + "s";
    }} else {{
        diff = elapsedTime.toFixed(4) + "s";
    }}

    return diff;
}}

// Run the test
function runTest() {{
    try {{
        const diff = get_time_difference("{start}", "{stop}");
        console.log(JSON.stringify({{
            status: "success",
            diff: diff
        }}));
    }} catch (error) {{
        console.log(JSON.stringify({{
            status: "error",
            error: error.message || String(error)
        }}));
    }}
}}

runTest();
'''
    return script


def _run_node_script(temp_path: str, script: str) -> Dict[str, Any]:
    """
        Run a Node.js script and return the parsed JSON result.

        :param temp_path: The temporary directory used to host the script file.
        :param script: The Node.js script source to execute.

        :returns: The parsed JSON result produced by the script.
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
        error_result = {"status": "error", "error": result.stderr}
        return error_result

    try:
        parsed_result = json.loads(result.stdout.strip())
        return parsed_result
    except json.JSONDecodeError:
        decode_result = {"status": "error", "error": f"Invalid output: {result.stdout}"}
        return decode_result


def _establish_env() -> tempfile.TemporaryDirectory:
    """
        Establish the per-test temporary directory fixture.

        This replicates the original ``setUpClass`` behavior (which created a
        ``tempfile.TemporaryDirectory``) on a per-test basis to preserve
        isolation between tests.

        :returns: The created temporary directory handle.
    """
    tempdir = tempfile.TemporaryDirectory()
    return tempdir


def test_get_time_difference_calculates_seconds_only() -> None:
    """
        Test that get_time_difference correctly calculates duration in seconds.

        Requirement 29.1: THE get_time_difference function SHALL calculate the duration
        between start and stop times.
        Requirement 29.2: THE time formatting SHALL display hours, minutes, and seconds
        as appropriate.

        This test verifies that when the duration is less than 60 seconds,
        the function returns only seconds with decimal precision.
    """
    tempdir = _establish_env()
    try:
        temp_path = tempdir.name

        # 30 seconds difference
        start = "2024-01-15T10:30:00.000000"
        stop = "2024-01-15T10:30:30.000000"

        test_script = _create_get_time_difference_test_script(start=start, stop=stop)
        result = _run_node_script(temp_path=temp_path, script=test_script)

        assert result["status"] == "success"
        assert "30" in result["diff"]
        assert result["diff"].endswith("s")
        assert "m" not in result["diff"]
        assert "h" not in result["diff"]
    finally:
        tempdir.cleanup()

    return


def test_get_time_difference_calculates_minutes_and_seconds() -> None:
    """
        Test that get_time_difference correctly formats minutes and seconds.

        Requirement 29.1: THE get_time_difference function SHALL calculate the duration
        between start and stop times.
        Requirement 29.2: THE time formatting SHALL display hours, minutes, and seconds
        as appropriate.

        This test verifies that when the duration is between 1 and 60 minutes,
        the function returns minutes and seconds.
    """
    tempdir = _establish_env()
    try:
        temp_path = tempdir.name

        # 2 minutes and 30 seconds difference
        start = "2024-01-15T10:30:00.000000"
        stop = "2024-01-15T10:32:30.000000"

        test_script = _create_get_time_difference_test_script(start=start, stop=stop)
        result = _run_node_script(temp_path=temp_path, script=test_script)

        assert result["status"] == "success"
        assert "2m" in result["diff"]
        assert "30" in result["diff"]
        assert result["diff"].endswith("s")
        assert "h" not in result["diff"]
    finally:
        tempdir.cleanup()

    return


def test_get_time_difference_calculates_hours_minutes_seconds() -> None:
    """
        Test that get_time_difference correctly formats hours, minutes, and seconds.

        Requirement 29.1: THE get_time_difference function SHALL calculate the duration
        between start and stop times.
        Requirement 29.2: THE time formatting SHALL display hours, minutes, and seconds
        as appropriate.

        This test verifies that when the duration is more than 1 hour,
        the function returns hours, minutes, and seconds.
    """
    tempdir = _establish_env()
    try:
        temp_path = tempdir.name

        # 1 hour, 15 minutes, and 30 seconds difference
        start = "2024-01-15T10:30:00.000000"
        stop = "2024-01-15T11:45:30.000000"

        test_script = _create_get_time_difference_test_script(start=start, stop=stop)
        result = _run_node_script(temp_path=temp_path, script=test_script)

        assert result["status"] == "success"
        assert "1h" in result["diff"]
        assert "15m" in result["diff"]
        assert "30" in result["diff"]
        assert result["diff"].endswith("s")
    finally:
        tempdir.cleanup()

    return


def test_get_time_difference_handles_sub_second_duration() -> None:
    """
        Test that get_time_difference handles sub-second durations.

        Requirement 29.1: THE get_time_difference function SHALL calculate the duration
        between start and stop times.
        Requirement 29.2: THE time formatting SHALL display hours, minutes, and seconds
        as appropriate.

        This test verifies that when the duration is less than 1 second,
        the function returns the fractional seconds.
    """
    tempdir = _establish_env()
    try:
        temp_path = tempdir.name

        # 0.5 seconds difference
        start = "2024-01-15T10:30:00.000000"
        stop = "2024-01-15T10:30:00.500000"

        test_script = _create_get_time_difference_test_script(start=start, stop=stop)
        result = _run_node_script(temp_path=temp_path, script=test_script)

        assert result["status"] == "success"
        assert result["diff"].endswith("s")
        # Should be a small decimal value
        assert "m" not in result["diff"]
        assert "h" not in result["diff"]
    finally:
        tempdir.cleanup()

    return


def test_get_time_difference_handles_over_one_minute() -> None:
    """
        Test that get_time_difference handles durations over one minute.

        Requirement 29.1: THE get_time_difference function SHALL calculate the duration
        between start and stop times.
        Requirement 29.2: THE time formatting SHALL display hours, minutes, and seconds
        as appropriate.

        This test verifies that when the duration is over 1 minute,
        the function formats it with minutes and seconds.
    """
    tempdir = _establish_env()
    try:
        temp_path = tempdir.name

        # 1 minute and 1 second difference (61 seconds triggers minute formatting)
        start = "2024-01-15T10:30:00.000000"
        stop = "2024-01-15T10:31:01.000000"

        test_script = _create_get_time_difference_test_script(start=start, stop=stop)
        result = _run_node_script(temp_path=temp_path, script=test_script)

        assert result["status"] == "success"
        assert "1m" in result["diff"]
        assert result["diff"].endswith("s")
    finally:
        tempdir.cleanup()

    return


def test_get_time_difference_handles_over_one_hour() -> None:
    """
        Test that get_time_difference handles durations over one hour.

        Requirement 29.1: THE get_time_difference function SHALL calculate the duration
        between start and stop times.
        Requirement 29.2: THE time formatting SHALL display hours, minutes, and seconds
        as appropriate.

        This test verifies that when the duration is over 1 hour,
        the function formats it with hours, minutes, and seconds.
    """
    tempdir = _establish_env()
    try:
        temp_path = tempdir.name

        # 1 hour and 1 minute difference (61 minutes triggers hour formatting)
        start = "2024-01-15T10:30:00.000000"
        stop = "2024-01-15T11:31:00.000000"

        test_script = _create_get_time_difference_test_script(start=start, stop=stop)
        result = _run_node_script(temp_path=temp_path, script=test_script)

        assert result["status"] == "success"
        assert "1h" in result["diff"]
        assert result["diff"].endswith("s")
    finally:
        tempdir.cleanup()

    return
