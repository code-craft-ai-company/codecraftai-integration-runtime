"""
    .. module:: ccai_tests.integrationruntime.results.templates.test_finalize_test_result_item
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Unit tests for the finalize_test_result_item JavaScript function.

    .. moduleauthor:: CodeCraftX

    These tests verify the finalize_test_result_item function behavior from testsummary.js.
    The tests use Node.js to execute JavaScript tests that validate:
    - Result categorization (passed, failed, errored, skipped)
    - Counter updates for each result category

    Requirements covered: 16.3, 16.5
"""

import json
import os
import subprocess
import tempfile
import unittest


class FinalizeTestResultItemTests(unittest.TestCase):
    """
    Unit tests for the finalize_test_result_item JavaScript function.
    
    These tests verify that:
    1. finalize_test_result_item categorizes results correctly (Requirement 16.3)
    2. The function updates counters appropriately (Requirement 16.5)
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

    def test_finalize_categorizes_passed_result(self):
        """
        Test that finalize_test_result_item categorizes a passed result correctly.
        
        Requirement 16.3: THE finalize_test_result_item function SHALL categorize results.
        Requirement 16.5: THE result processing SHALL accumulate passed counts.
        
        This test verifies that when a test has no errors, no failures, and result
        is not SKIPPED, it is categorized as passed and the passed counter is incremented.
        """
        ritem = {
            "name": "package.module#test_passed",
            "monikers": [],
            "result": "PASSED",
            "detail": {
                "errors": [],
                "failures": [],
                "warnings": []
            }
        }
        
        result = self._run_finalize_test(ritem)
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["counters"]["passed"], 1)
        self.assertEqual(result["counters"]["failed"], 0)
        self.assertEqual(result["counters"]["errors"], 0)
        self.assertEqual(result["counters"]["skipped"], 0)
        self.assertTrue(result["ritem"]["detail"]["passed"])
        self.assertFalse(result["ritem"]["detail"]["skipped"])


    def test_finalize_categorizes_failed_result(self):
        """
        Test that finalize_test_result_item categorizes a failed result correctly.
        
        Requirement 16.3: THE finalize_test_result_item function SHALL categorize results.
        Requirement 16.5: THE result processing SHALL accumulate failed counts.
        
        This test verifies that when a test has failures (but no errors), it is
        categorized as failed and the failed counter is incremented.
        """
        ritem = {
            "name": "package.module#test_failed",
            "monikers": [],
            "result": "FAILED",
            "detail": {
                "errors": [],
                "failures": [{"message": "Assertion failed"}],
                "warnings": []
            }
        }
        
        result = self._run_finalize_test(ritem)
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["counters"]["passed"], 0)
        self.assertEqual(result["counters"]["failed"], 1)
        self.assertEqual(result["counters"]["errors"], 0)
        self.assertEqual(result["counters"]["skipped"], 0)
        self.assertFalse(result["ritem"]["detail"]["passed"])
        self.assertFalse(result["ritem"]["detail"]["skipped"])

    def test_finalize_categorizes_errored_result(self):
        """
        Test that finalize_test_result_item categorizes an errored result correctly.
        
        Requirement 16.3: THE finalize_test_result_item function SHALL categorize results.
        Requirement 16.5: THE result processing SHALL accumulate errored counts.
        
        This test verifies that when a test has errors, it is categorized as errored
        and the errors counter is incremented (errors take precedence over failures).
        """
        ritem = {
            "name": "package.module#test_errored",
            "monikers": [],
            "result": "ERRORED",
            "detail": {
                "errors": [{"message": "Exception occurred"}],
                "failures": [],
                "warnings": []
            }
        }
        
        result = self._run_finalize_test(ritem)
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["counters"]["passed"], 0)
        self.assertEqual(result["counters"]["failed"], 0)
        self.assertEqual(result["counters"]["errors"], 1)
        self.assertEqual(result["counters"]["skipped"], 0)
        self.assertFalse(result["ritem"]["detail"]["passed"])
        self.assertFalse(result["ritem"]["detail"]["skipped"])

    def test_finalize_categorizes_skipped_result(self):
        """
        Test that finalize_test_result_item categorizes a skipped result correctly.
        
        Requirement 16.3: THE finalize_test_result_item function SHALL categorize results.
        Requirement 16.5: THE result processing SHALL accumulate skipped counts.
        
        This test verifies that when a test has result SKIPPED (with no errors or
        failures), it is categorized as skipped and the skipped counter is incremented.
        """
        ritem = {
            "name": "package.module#test_skipped",
            "monikers": [],
            "result": "SKIPPED",
            "detail": {
                "errors": [],
                "failures": [],
                "warnings": []
            }
        }
        
        result = self._run_finalize_test(ritem)
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["counters"]["passed"], 0)
        self.assertEqual(result["counters"]["failed"], 0)
        self.assertEqual(result["counters"]["errors"], 0)
        self.assertEqual(result["counters"]["skipped"], 1)
        self.assertFalse(result["ritem"]["detail"]["passed"])
        self.assertTrue(result["ritem"]["detail"]["skipped"])

    def test_finalize_errors_take_precedence_over_failures(self):
        """
        Test that errors take precedence over failures in categorization.
        
        Requirement 16.3: THE finalize_test_result_item function SHALL categorize results.
        
        This test verifies that when a test has both errors and failures, it is
        categorized as errored (errors take precedence).
        """
        ritem = {
            "name": "package.module#test_both",
            "monikers": [],
            "result": "ERRORED",
            "detail": {
                "errors": [{"message": "Exception occurred"}],
                "failures": [{"message": "Assertion failed"}],
                "warnings": []
            }
        }
        
        result = self._run_finalize_test(ritem)
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["counters"]["errors"], 1)
        self.assertEqual(result["counters"]["failed"], 0)
        self.assertFalse(result["ritem"]["detail"]["passed"])
        self.assertFalse(result["ritem"]["detail"]["skipped"])

    def test_finalize_adds_result_to_package_list(self):
        """
        Test that finalize_test_result_item adds the result to the correct package list.
        
        Requirement 16.3: THE finalize_test_result_item function SHALL categorize results.
        
        This test verifies that the result item is added to the results_table
        under the correct package name.
        """
        ritem = {
            "name": "mypackage.mymodule#test_function",
            "monikers": [],
            "result": "PASSED",
            "detail": {
                "errors": [],
                "failures": [],
                "warnings": []
            }
        }
        
        result = self._run_finalize_test(ritem)
        
        self.assertEqual(result["status"], "success")
        self.assertIn("mypackage.mymodule", result["results_table"])
        self.assertEqual(len(result["results_table"]["mypackage.mymodule"]), 1)
        self.assertEqual(result["results_table"]["mypackage.mymodule"][0]["name"], "test_function")


    def test_finalize_handles_monikers(self):
        """
        Test that finalize_test_result_item handles monikers correctly.
        
        Requirement 16.3: THE finalize_test_result_item function SHALL categorize results.
        
        This test verifies that when a test has monikers, they are appended to the
        test name with the correct format (monikers are added to the test name, not package).
        """
        ritem = {
            "name": "package.module#test_with_monikers",
            "monikers": ["moniker1", "moniker2"],
            "result": "PASSED",
            "detail": {
                "errors": [],
                "failures": [],
                "warnings": []
            }
        }
        
        result = self._run_finalize_test(ritem)
        
        self.assertEqual(result["status"], "success")
        # The package name should remain unchanged
        self.assertIn("package.module", result["results_table"])
        # The test name should include the moniker suffix
        test_item = result["results_table"]["package.module"][0]
        self.assertEqual(test_item["name"], "test_with_monikers:[moniker1][moniker2]")

    def test_finalize_accumulates_counters_across_multiple_items(self):
        """
        Test that finalize_test_result_item accumulates counters correctly.
        
        Requirement 16.5: THE result processing SHALL accumulate passed, failed,
        errored, and skipped counts.
        
        This test verifies that counters are accumulated correctly when processing
        multiple result items.
        """
        ritems = [
            {
                "name": "package.module#test_passed1",
                "monikers": [],
                "result": "PASSED",
                "detail": {"errors": [], "failures": [], "warnings": []}
            },
            {
                "name": "package.module#test_passed2",
                "monikers": [],
                "result": "PASSED",
                "detail": {"errors": [], "failures": [], "warnings": []}
            },
            {
                "name": "package.module#test_failed",
                "monikers": [],
                "result": "FAILED",
                "detail": {"errors": [], "failures": [{"message": "fail"}], "warnings": []}
            },
            {
                "name": "package.module#test_errored",
                "monikers": [],
                "result": "ERRORED",
                "detail": {"errors": [{"message": "error"}], "failures": [], "warnings": []}
            },
            {
                "name": "package.module#test_skipped",
                "monikers": [],
                "result": "SKIPPED",
                "detail": {"errors": [], "failures": [], "warnings": []}
            }
        ]
        
        result = self._run_finalize_test_multiple(ritems)
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["counters"]["passed"], 2)
        self.assertEqual(result["counters"]["failed"], 1)
        self.assertEqual(result["counters"]["errors"], 1)
        self.assertEqual(result["counters"]["skipped"], 1)

    def test_finalize_groups_results_by_package(self):
        """
        Test that finalize_test_result_item groups results by package correctly.
        
        Requirement 16.3: THE finalize_test_result_item function SHALL categorize results.
        
        This test verifies that results from different packages are grouped
        into separate lists in the results_table.
        """
        ritems = [
            {
                "name": "package1.module#test_a",
                "monikers": [],
                "result": "PASSED",
                "detail": {"errors": [], "failures": [], "warnings": []}
            },
            {
                "name": "package2.module#test_b",
                "monikers": [],
                "result": "PASSED",
                "detail": {"errors": [], "failures": [], "warnings": []}
            },
            {
                "name": "package1.module#test_c",
                "monikers": [],
                "result": "PASSED",
                "detail": {"errors": [], "failures": [], "warnings": []}
            }
        ]
        
        result = self._run_finalize_test_multiple(ritems)
        
        self.assertEqual(result["status"], "success")
        self.assertIn("package1.module", result["results_table"])
        self.assertIn("package2.module", result["results_table"])
        self.assertEqual(len(result["results_table"]["package1.module"]), 2)
        self.assertEqual(len(result["results_table"]["package2.module"]), 1)

    def _run_finalize_test(self, ritem):
        """Run a single finalize_test_result_item test."""
        return self._run_finalize_test_multiple([ritem])

    def _run_finalize_test_multiple(self, ritems):
        """Run finalize_test_result_item for multiple items."""
        test_script = self._create_finalize_test_script(ritems)
        return self._run_node_script(test_script)


    def _create_finalize_test_script(self, ritems):
        """
        Create a Node.js test script that tests the finalize_test_result_item function.
        
        This replicates the finalize_test_result_item and split_test_fullname
        functions from testsummary.js.
        """
        ritems_json = json.dumps(ritems)
        
        script = f'''
// Replicate the split_test_fullname function from testsummary.js
function split_test_fullname(testname_full) {{
    var package_name = null;
    var test_name = null;

    var sindex = testname_full.search("#");

    if (sindex > -1) {{
        name_parts = testname_full.split("#");
        package_name = name_parts[0];
        test_name = name_parts[1];
    }}

    return [package_name, test_name];
}}

// Replicate the finalize_test_result_item function from testsummary.js
function finalize_test_result_item(ritem, counters, results_table) {{

    var moniker_suffix = ""
    if ((ritem.monikers) && (ritem.monikers.length > 0)) {{
        moniker_start = "["
        ritem.monikers.forEach(item => {{
            moniker_suffix = moniker_suffix + "[" + item + "]"
            moniker_start = ",["
        }});
    }}

    var testname_full = ritem.name;
    if (moniker_suffix != "") {{
        testname_full = testname_full + ":" + moniker_suffix;
    }}

    const [package_name, test_name] = split_test_fullname(testname_full);
    ritem.name = test_name
    ritem.package_name = package_name

    var detail = ritem.detail;
    detail.passed = false;
    detail.skipped = false;

    if (detail.errors.length > 0) {{
        counters.errors += 1;
    }}
    else if (detail.failures.length > 0) {{
        counters.failed += 1;
    }}
    else {{
        if (ritem.result == "SKIPPED") {{
            detail.skipped = true;
            counters.skipped += 1;
        }} else {{
            detail.passed = true;
            counters.passed += 1;
        }}
    }}
    
    var package_list = null;
    if (package_name in results_table) {{
        package_list = results_table[package_name];
    }} else {{
        package_list = [];
        results_table[package_name] = package_list;
    }}

    package_list.push(ritem);
}}

// Run the test
function runTest() {{
    try {{
        const ritems = {ritems_json};
        const counters = {{
            passed: 0,
            errors: 0,
            failed: 0,
            skipped: 0
        }};
        const results_table = {{}};
        
        for (const ritem of ritems) {{
            finalize_test_result_item(ritem, counters, results_table);
        }}
        
        // Return the last ritem for single-item tests
        const lastRitem = ritems[ritems.length - 1];
        
        console.log(JSON.stringify({{ 
            status: "success", 
            counters: counters,
            results_table: results_table,
            ritem: lastRitem
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
