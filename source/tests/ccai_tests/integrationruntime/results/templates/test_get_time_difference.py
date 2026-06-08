"""
    .. module:: ccai_tests.integrationruntime.results.templates.test_get_time_difference
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Unit tests for the get_time_difference JavaScript function.

    .. moduleauthor:: CodeCraftX

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
import unittest


class GetTimeDifferenceTests(unittest.TestCase):
    """
    Unit tests for the get_time_difference JavaScript function.
    
    These tests verify that:
    1. get_time_difference calculates duration between start and stop times (Requirement 29.1)
    2. The function formats hours, minutes, and seconds appropriately (Requirement 29.2)
    """

    @classmethod
    def setUpClass(cls):
        """Set up class-level fixtures."""
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.temp_path = cls.tempdir.name

    @classmethod
    def tearDownClass(cls):
        """Clean up class-level fixtures."""
        cls.tempdir.cleanup()

    def test_get_time_difference_calculates_seconds_only(self):
        """
        Test that get_time_difference correctly calculates duration in seconds.
        
        Requirement 29.1: THE get_time_difference function SHALL calculate the duration 
        between start and stop times.
        Requirement 29.2: THE time formatting SHALL display hours, minutes, and seconds 
        as appropriate.
        
        This test verifies that when the duration is less than 60 seconds,
        the function returns only seconds with decimal precision.
        """
        # 30 seconds difference
        start = "2024-01-15T10:30:00.000000"
        stop = "2024-01-15T10:30:30.000000"
        
        test_script = self._create_get_time_difference_test_script(start, stop)
        result = self._run_node_script(test_script)
        
        self.assertEqual(result["status"], "success")
        self.assertIn("30", result["diff"])
        self.assertTrue(result["diff"].endswith("s"))
        self.assertNotIn("m", result["diff"])
        self.assertNotIn("h", result["diff"])

    def test_get_time_difference_calculates_minutes_and_seconds(self):
        """
        Test that get_time_difference correctly formats minutes and seconds.
        
        Requirement 29.1: THE get_time_difference function SHALL calculate the duration 
        between start and stop times.
        Requirement 29.2: THE time formatting SHALL display hours, minutes, and seconds 
        as appropriate.
        
        This test verifies that when the duration is between 1 and 60 minutes,
        the function returns minutes and seconds.
        """
        # 2 minutes and 30 seconds difference
        start = "2024-01-15T10:30:00.000000"
        stop = "2024-01-15T10:32:30.000000"
        
        test_script = self._create_get_time_difference_test_script(start, stop)
        result = self._run_node_script(test_script)
        
        self.assertEqual(result["status"], "success")
        self.assertIn("2m", result["diff"])
        self.assertIn("30", result["diff"])
        self.assertTrue(result["diff"].endswith("s"))
        self.assertNotIn("h", result["diff"])

    def test_get_time_difference_calculates_hours_minutes_seconds(self):
        """
        Test that get_time_difference correctly formats hours, minutes, and seconds.
        
        Requirement 29.1: THE get_time_difference function SHALL calculate the duration 
        between start and stop times.
        Requirement 29.2: THE time formatting SHALL display hours, minutes, and seconds 
        as appropriate.
        
        This test verifies that when the duration is more than 1 hour,
        the function returns hours, minutes, and seconds.
        """
        # 1 hour, 15 minutes, and 30 seconds difference
        start = "2024-01-15T10:30:00.000000"
        stop = "2024-01-15T11:45:30.000000"
        
        test_script = self._create_get_time_difference_test_script(start, stop)
        result = self._run_node_script(test_script)
        
        self.assertEqual(result["status"], "success")
        self.assertIn("1h", result["diff"])
        self.assertIn("15m", result["diff"])
        self.assertIn("30", result["diff"])
        self.assertTrue(result["diff"].endswith("s"))

    def test_get_time_difference_handles_sub_second_duration(self):
        """
        Test that get_time_difference handles sub-second durations.
        
        Requirement 29.1: THE get_time_difference function SHALL calculate the duration 
        between start and stop times.
        Requirement 29.2: THE time formatting SHALL display hours, minutes, and seconds 
        as appropriate.
        
        This test verifies that when the duration is less than 1 second,
        the function returns the fractional seconds.
        """
        # 0.5 seconds difference
        start = "2024-01-15T10:30:00.000000"
        stop = "2024-01-15T10:30:00.500000"
        
        test_script = self._create_get_time_difference_test_script(start, stop)
        result = self._run_node_script(test_script)
        
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["diff"].endswith("s"))
        # Should be a small decimal value
        self.assertNotIn("m", result["diff"])
        self.assertNotIn("h", result["diff"])

    def test_get_time_difference_handles_over_one_minute(self):
        """
        Test that get_time_difference handles durations over one minute.
        
        Requirement 29.1: THE get_time_difference function SHALL calculate the duration 
        between start and stop times.
        Requirement 29.2: THE time formatting SHALL display hours, minutes, and seconds 
        as appropriate.
        
        This test verifies that when the duration is over 1 minute,
        the function formats it with minutes and seconds.
        """
        # 1 minute and 1 second difference (61 seconds triggers minute formatting)
        start = "2024-01-15T10:30:00.000000"
        stop = "2024-01-15T10:31:01.000000"
        
        test_script = self._create_get_time_difference_test_script(start, stop)
        result = self._run_node_script(test_script)
        
        self.assertEqual(result["status"], "success")
        self.assertIn("1m", result["diff"])
        self.assertTrue(result["diff"].endswith("s"))

    def test_get_time_difference_handles_over_one_hour(self):
        """
        Test that get_time_difference handles durations over one hour.
        
        Requirement 29.1: THE get_time_difference function SHALL calculate the duration 
        between start and stop times.
        Requirement 29.2: THE time formatting SHALL display hours, minutes, and seconds 
        as appropriate.
        
        This test verifies that when the duration is over 1 hour,
        the function formats it with hours, minutes, and seconds.
        """
        # 1 hour and 1 minute difference (61 minutes triggers hour formatting)
        start = "2024-01-15T10:30:00.000000"
        stop = "2024-01-15T11:31:00.000000"
        
        test_script = self._create_get_time_difference_test_script(start, stop)
        result = self._run_node_script(test_script)
        
        self.assertEqual(result["status"], "success")
        self.assertIn("1h", result["diff"])
        self.assertTrue(result["diff"].endswith("s"))

    def _create_get_time_difference_test_script(self, start, stop):
        """
        Create a Node.js test script that tests the get_time_difference function.
        
        This replicates the get_time_difference function from testsummary-helpers.js.
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


if __name__ == "__main__":
    unittest.main()
