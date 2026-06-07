"""
    .. module:: ccai.tests.singlehost.integrationruntime.results.templates.test_split_test_fullname
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


def _establish_env() -> dict:
    """
        Establish the per-test fixtures originally created by ``setUpClass``.

        This creates a temporary directory that the generated Node.js scripts
        are written into.

        :returns: A dictionary of the fixtures the tests need (``tempdir`` and
                  ``temp_path``).
    """
    tempdir = tempfile.TemporaryDirectory()
    temp_path = tempdir.name

    env = {
        "tempdir": tempdir,
        "temp_path": temp_path,
    }
    return env


def _teardown_env(env: dict) -> None:
    """
        Replicate the cleanup originally performed by ``tearDownClass``.

        :param env: The fixture dictionary returned by :func:`_establish_env`.

        :returns: Nothing.
    """
    tempdir = env["tempdir"]

    tempdir.cleanup()

    return


def _create_split_test_fullname_test_script(testname_full: str) -> str:
    """
        Create a Node.js test script that tests the split_test_fullname function.

        This replicates the split_test_fullname function from testsummary.js.

        :param testname_full: The full test name the generated Node.js script
                              should split.

        :returns: The generated Node.js script as a string.
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


def test_split_test_fullname_extracts_package_and_test_name() -> None:
    """
        Test that split_test_fullname correctly extracts package and test name.

        Requirement 16.2: THE split_test_fullname function SHALL extract package_name
        and test_name from the full test name.

        This test verifies that when a full test name with '#' separator is provided,
        the function returns the package name and test name as separate values.
    """
    env = _establish_env()
    try:
        test_script = _create_split_test_fullname_test_script(
            testname_full="ccai.tests.singlehost.interop.protocols.dns.test_dnsaddress#test_write_passes_address"
        )

        result = _run_node_script(temp_path=env["temp_path"], script=test_script)

        assert result["status"] == "success"
        assert result["package_name"] == "ccai.tests.singlehost.interop.protocols.dns.test_dnsaddress"
        assert result["test_name"] == "test_write_passes_address"
    finally:
        _teardown_env(env=env)

    return


def test_split_test_fullname_handles_simple_package_name() -> None:
    """
        Test that split_test_fullname handles simple package names.

        Requirement 16.2: THE split_test_fullname function SHALL extract package_name
        and test_name from the full test name.

        This test verifies that the function works with shorter package names.
    """
    env = _establish_env()
    try:
        test_script = _create_split_test_fullname_test_script(
            testname_full="mypackage.mymodule#test_function"
        )

        result = _run_node_script(temp_path=env["temp_path"], script=test_script)

        assert result["status"] == "success"
        assert result["package_name"] == "mypackage.mymodule"
        assert result["test_name"] == "test_function"
    finally:
        _teardown_env(env=env)

    return


def test_split_test_fullname_handles_no_separator() -> None:
    """
        Test that split_test_fullname handles names without '#' separator.

        Requirement 16.2: THE split_test_fullname function SHALL extract package_name
        and test_name from the full test name.

        This test verifies that when no '#' separator is present, the function
        returns null for both package_name and test_name.
    """
    env = _establish_env()
    try:
        test_script = _create_split_test_fullname_test_script(
            testname_full="test_without_separator"
        )

        result = _run_node_script(temp_path=env["temp_path"], script=test_script)

        assert result["status"] == "success"
        assert result["package_name"] is None
        assert result["test_name"] is None
    finally:
        _teardown_env(env=env)

    return


def test_split_test_fullname_handles_class_method_format() -> None:
    """
        Test that split_test_fullname handles class::method format in test name.

        Requirement 16.2: THE split_test_fullname function SHALL extract package_name
        and test_name from the full test name.

        This test verifies that the function correctly handles test names that
        include class and method names (common in Python test frameworks).
    """
    env = _establish_env()
    try:
        test_script = _create_split_test_fullname_test_script(
            testname_full="package.module#TestClass::test_method"
        )

        result = _run_node_script(temp_path=env["temp_path"], script=test_script)

        assert result["status"] == "success"
        assert result["package_name"] == "package.module"
        assert result["test_name"] == "TestClass::test_method"
    finally:
        _teardown_env(env=env)

    return


def test_split_test_fullname_handles_empty_test_name() -> None:
    """
        Test that split_test_fullname handles empty test name after separator.

        Requirement 16.2: THE split_test_fullname function SHALL extract package_name
        and test_name from the full test name.

        This test verifies that when the test name portion is empty, the function
        returns an empty string for test_name.
    """
    env = _establish_env()
    try:
        test_script = _create_split_test_fullname_test_script(
            testname_full="package.module#"
        )

        result = _run_node_script(temp_path=env["temp_path"], script=test_script)

        assert result["status"] == "success"
        assert result["package_name"] == "package.module"
        assert result["test_name"] == ""
    finally:
        _teardown_env(env=env)

    return


def test_split_test_fullname_handles_empty_package_name() -> None:
    """
        Test that split_test_fullname handles empty package name before separator.

        Requirement 16.2: THE split_test_fullname function SHALL extract package_name
        and test_name from the full test name.

        This test verifies that when the package name portion is empty, the function
        returns an empty string for package_name.
    """
    env = _establish_env()
    try:
        test_script = _create_split_test_fullname_test_script(
            testname_full="#test_function"
        )

        result = _run_node_script(temp_path=env["temp_path"], script=test_script)

        assert result["status"] == "success"
        assert result["package_name"] == ""
        assert result["test_name"] == "test_function"
    finally:
        _teardown_env(env=env)

    return
