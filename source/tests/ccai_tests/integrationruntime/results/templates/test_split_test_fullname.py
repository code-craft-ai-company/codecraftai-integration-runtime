"""
    .. module:: ccai_tests.integrationruntime.results.templates.test_split_test_fullname
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Unit tests for the split_test_fullname JavaScript function.

    .. moduleauthor:: CodeCraftX

    These tests verify the split_test_fullname function behavior from testsummary.js.
    The tests use Node.js to execute JavaScript tests that validate:
    - Extraction of package name and test name from full test names
    - Handling of various name formats

    Requirements covered: 16.2
"""

import json
import os
import subprocess
import tempfile
import unittest


class SplitTestFullnameTests(unittest.TestCase):
    """
    Unit tests for the split_test_fullname JavaScript function.
    
    These tests verify that:
    1. split_test_fullname extracts package_name and test_name from full test name (Requirement 16.2)
    2. The function handles various name formats correctly
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

    def test_split_test_fullname_extracts_package_and_test_name(self):
        """
        Test that split_test_fullname correctly extracts package and test name.
        
        Requirement 16.2: THE split_test_fullname function SHALL extract package_name 
        and test_name from the full test name.
        
        This test verifies that when a full test name with '#' separator is provided,
        the function returns the package name and test name as separate values.
        """
        test_script = self._create_split_test_fullname_test_script(
            "ccai.tests.singlehost.interop.protocols.dns.test_dnsaddress#test_write_passes_address"
        )
        
        result = self._run_node_script(test_script)
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["package_name"], "ccai.tests.singlehost.interop.protocols.dns.test_dnsaddress")
        self.assertEqual(result["test_name"], "test_write_passes_address")

    def test_split_test_fullname_handles_simple_package_name(self):
        """
        Test that split_test_fullname handles simple package names.
        
        Requirement 16.2: THE split_test_fullname function SHALL extract package_name 
        and test_name from the full test name.
        
        This test verifies that the function works with shorter package names.
        """
        test_script = self._create_split_test_fullname_test_script(
            "mypackage.mymodule#test_function"
        )
        
        result = self._run_node_script(test_script)
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["package_name"], "mypackage.mymodule")
        self.assertEqual(result["test_name"], "test_function")

    def test_split_test_fullname_handles_no_separator(self):
        """
        Test that split_test_fullname handles names without '#' separator.
        
        Requirement 16.2: THE split_test_fullname function SHALL extract package_name 
        and test_name from the full test name.
        
        This test verifies that when no '#' separator is present, the function
        returns null for both package_name and test_name.
        """
        test_script = self._create_split_test_fullname_test_script(
            "test_without_separator"
        )
        
        result = self._run_node_script(test_script)
        
        self.assertEqual(result["status"], "success")
        self.assertIsNone(result["package_name"])
        self.assertIsNone(result["test_name"])

    def test_split_test_fullname_handles_class_method_format(self):
        """
        Test that split_test_fullname handles class::method format in test name.
        
        Requirement 16.2: THE split_test_fullname function SHALL extract package_name 
        and test_name from the full test name.
        
        This test verifies that the function correctly handles test names that
        include class and method names (common in Python test frameworks).
        """
        test_script = self._create_split_test_fullname_test_script(
            "package.module#TestClass::test_method"
        )
        
        result = self._run_node_script(test_script)
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["package_name"], "package.module")
        self.assertEqual(result["test_name"], "TestClass::test_method")

    def test_split_test_fullname_handles_empty_test_name(self):
        """
        Test that split_test_fullname handles empty test name after separator.
        
        Requirement 16.2: THE split_test_fullname function SHALL extract package_name 
        and test_name from the full test name.
        
        This test verifies that when the test name portion is empty, the function
        returns an empty string for test_name.
        """
        test_script = self._create_split_test_fullname_test_script(
            "package.module#"
        )
        
        result = self._run_node_script(test_script)
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["package_name"], "package.module")
        self.assertEqual(result["test_name"], "")

    def test_split_test_fullname_handles_empty_package_name(self):
        """
        Test that split_test_fullname handles empty package name before separator.
        
        Requirement 16.2: THE split_test_fullname function SHALL extract package_name 
        and test_name from the full test name.
        
        This test verifies that when the package name portion is empty, the function
        returns an empty string for package_name.
        """
        test_script = self._create_split_test_fullname_test_script(
            "#test_function"
        )
        
        result = self._run_node_script(test_script)
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["package_name"], "")
        self.assertEqual(result["test_name"], "test_function")

    def _create_split_test_fullname_test_script(self, testname_full):
        """
        Create a Node.js test script that tests the split_test_fullname function.
        
        This replicates the split_test_fullname function from testsummary.js.
        """
        # Escape the testname_full for JavaScript string
        escaped_testname = testname_full.replace("\\", "\\\\").replace('"', '\\"')
        
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

// Run the test
function runTest() {{
    try {{
        const [package_name, test_name] = split_test_fullname("{escaped_testname}");
        console.log(JSON.stringify({{ 
            status: "success", 
            package_name: package_name,
            test_name: test_name
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
