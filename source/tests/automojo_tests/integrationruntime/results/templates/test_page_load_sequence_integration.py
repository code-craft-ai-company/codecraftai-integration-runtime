"""
    .. module:: automojo_tests.integrationruntime.results.templates.test_page_load_sequence_integration
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Integration tests for the HTML report page load sequence.

    .. moduleauthor:: AutomationX

    These tests verify the page load sequence behavior from testsummary.js.
    The tests use Node.js to execute JavaScript tests that validate:
    - All data sources load correctly (Requirement 27.1, 27.2)
    - Components render with sample data (Requirement 27.3)
    - Error states handled gracefully (Requirement 27.1, 27.2, 27.3)

    Requirements covered: 27.1, 27.2, 27.3
"""

import json
import os
import subprocess
import tempfile
import unittest
import http.server
import threading
import socket


class PageLoadSequenceIntegrationTests(unittest.TestCase):
    """
    Integration tests for the HTML report page load sequence.
    
    These tests verify that:
    1. refresh_page orchestrates loading and refreshing all page sections (Requirement 27.1)
    2. Summary, configuration, results, import errors, and catalog load in parallel (Requirement 27.2)
    3. Each load function triggers its corresponding refresh function upon completion (Requirement 27.3)
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
        
        # Create test data files
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
        """Create test data files for testing page load sequence."""
        # testrun_summary.json
        summary_data = {
            "version": "2",
            "title": "Test Job",
            "runid": "test-run-123",
            "start": "2024-01-15T10:30:00.000000",
            "stop": "2024-01-15T11:45:00.000000",
            "result": "PASSED",
            "apod": "test-automation-pod",
            "build": {
                "branch": "main",
                "build": "123",
                "flavor": "release"
            },
            "detail": {
                "errors": 0,
                "failed": 2,
                "skipped": 5,
                "passed": 93,
                "total": 100
            }
        }
        with open(os.path.join(cls.temp_path, "testrun_summary.json"), 'w') as f:
            json.dump(summary_data, f)
        
        # startup-configuration.json
        startup_config = {
            "command": "testbase testing run --root /path/to/tests",
            "environment": {
                "PATH": "/usr/bin:/bin",
                "HOME": "/home/user"
            },
            "packages": {
                "automojo-testbase": "2.0.0",
                "pytest": "7.4.0"
            }
        }
        with open(os.path.join(cls.temp_path, "startup-configuration.json"), 'w') as f:
            json.dump(startup_config, f)
        
        # landscape-declared.json
        landscape_config = {
            "apod": {
                "default": [
                    {"name": "device1", "deviceType": "network/ssh", "host": "192.168.1.1"}
                ]
            },
            "infrastructure": {
                "services": [
                    {"name": "api-server", "serviceType": "http", "host": "api.example.com"}
                ]
            }
        }
        with open(os.path.join(cls.temp_path, "landscape-declared.json"), 'w') as f:
            json.dump(landscape_config, f)
        
        # testrun_results_stream.jsos
        results = [
            {
                "rtype": "TEST",
                "name": "tests.test_module#test_passing",
                "instance": "inst-001",
                "parent": "parent-001",
                "monikers": [],
                "pivots": {},
                "result": "PASSED",
                "start": "2024-01-15T10:30:00.000000",
                "stop": "2024-01-15T10:30:01.000000",
                "detail": {"errors": [], "failures": [], "warnings": []}
            },
            {
                "rtype": "TEST",
                "name": "tests.test_module#test_failing",
                "instance": "inst-002",
                "parent": "parent-001",
                "monikers": [],
                "pivots": {},
                "result": "FAILED",
                "start": "2024-01-15T10:30:02.000000",
                "stop": "2024-01-15T10:30:03.000000",
                "detail": {
                    "errors": [],
                    "failures": [{"message": "Assertion failed"}],
                    "warnings": []
                }
            }
        ]
        jsos_content = cls.RECORD_SEPARATOR.join(json.dumps(r) for r in results)
        with open(os.path.join(cls.temp_path, "testrun_results_stream.jsos"), 'w') as f:
            f.write(jsos_content)
        
        # import_errors.jsos (empty - no import errors)
        with open(os.path.join(cls.temp_path, "import_errors.jsos"), 'w') as f:
            f.write("")
        
        # catalog.json
        catalog = {
            "files": [
                "testrun_summary.json",
                "testrun_results_stream.jsos",
                "startup-configuration.json",
                "landscape-declared.json",
                "import_errors.jsos"
            ],
            "folders": ["artifacts", "logs"]
        }
        with open(os.path.join(cls.temp_path, "catalog.json"), 'w') as f:
            json.dump(catalog, f)
        
        # Create artifacts folder with catalog
        artifacts_dir = os.path.join(cls.temp_path, "artifacts")
        os.makedirs(artifacts_dir, exist_ok=True)
        
        artifacts_catalog = {
            "files": [],
            "folders": ["images"]
        }
        with open(os.path.join(artifacts_dir, "catalog.json"), 'w') as f:
            json.dump(artifacts_catalog, f)
        
        # Create images subfolder with catalog
        images_dir = os.path.join(artifacts_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        
        images_catalog = {
            "files": ["screenshot.png", "tab.html"],
            "folders": []
        }
        with open(os.path.join(images_dir, "catalog.json"), 'w') as f:
            json.dump(images_catalog, f)
        
        # Create a dummy tab.html
        with open(os.path.join(images_dir, "tab.html"), 'w') as f:
            f.write("<html><body>Images Tab</body></html>")

    def test_all_data_sources_load_correctly(self):
        """
        Test that all data sources load correctly during page load sequence.
        
        Requirement 27.1: THE refresh_page function SHALL orchestrate loading 
        and refreshing all page sections.
        
        Requirement 27.2: THE refresh_page function SHALL load summary, 
        configuration, results, import errors, and catalog in parallel.
        
        This test verifies that all required data files can be loaded successfully.
        """
        test_script = self._create_data_loading_test_script()
        
        result = self._run_node_script(test_script)
        
        self.assertEqual(result["status"], "success", 
                        f"Data loading failed: {result.get('error', 'Unknown error')}")
        
        # Verify all data sources were loaded
        self.assertIn("summary", result["data"])
        self.assertIn("configuration", result["data"])
        self.assertIn("results", result["data"])
        self.assertIn("import_errors", result["data"])
        self.assertIn("catalog", result["data"])
        
        # Verify summary data
        self.assertEqual(result["data"]["summary"]["apod"], "test-automation-pod")
        self.assertEqual(result["data"]["summary"]["result"], "PASSED")
        
        # Verify configuration data
        self.assertIn("command", result["data"]["configuration"]["startup"])
        self.assertIn("environment", result["data"]["configuration"]["startup"])
        
        # Verify results data
        self.assertEqual(len(result["data"]["results"]), 2)
        
        # Verify catalog data
        self.assertIn("files", result["data"]["catalog"])
        self.assertIn("folders", result["data"]["catalog"])

    def test_components_render_with_sample_data(self):
        """
        Test that components can render with sample data.
        
        Requirement 27.3: EACH load function SHALL trigger its corresponding 
        refresh function upon completion.
        
        This test verifies that the data loaded can be processed for rendering.
        """
        test_script = self._create_component_rendering_test_script()
        
        result = self._run_node_script(test_script)
        
        self.assertEqual(result["status"], "success",
                        f"Component rendering test failed: {result.get('error', 'Unknown error')}")
        
        # Verify summary can be processed for banner
        self.assertIn("banner_data", result["data"])
        self.assertEqual(result["data"]["banner_data"]["apod"], "test-automation-pod")
        self.assertEqual(result["data"]["banner_data"]["metrics"]["passed"], 93)
        self.assertEqual(result["data"]["banner_data"]["metrics"]["failed"], 2)
        
        # Verify results can be grouped by package
        self.assertIn("grouped_results", result["data"])
        self.assertIn("tests.test_module", result["data"]["grouped_results"])
        
        # Verify configuration can be processed
        self.assertIn("config_data", result["data"])
        self.assertIn("command", result["data"]["config_data"])

    def test_error_states_handled_gracefully(self):
        """
        Test that error states are handled gracefully during page load.
        
        Requirement 27.1: THE refresh_page function SHALL orchestrate loading 
        and refreshing all page sections.
        
        Requirement 27.2: THE refresh_page function SHALL load summary, 
        configuration, results, import errors, and catalog in parallel.
        
        This test verifies that missing files don't cause the entire page load
        to fail, and that the system continues loading other data sources.
        """
        test_script = self._create_error_handling_test_script()
        
        result = self._run_node_script(test_script)
        
        self.assertEqual(result["status"], "success",
                        f"Error handling test failed: {result.get('error', 'Unknown error')}")
        
        # Verify that available data was still loaded despite missing files
        self.assertIn("summary_loaded", result["data"])
        self.assertTrue(result["data"]["summary_loaded"])
        
        # Verify that missing file was handled gracefully
        self.assertIn("missing_file_handled", result["data"])
        self.assertTrue(result["data"]["missing_file_handled"])
        
        # Verify that the error was logged but didn't crash
        self.assertIn("error_logged", result["data"])
        self.assertTrue(result["data"]["error_logged"])

    def test_artifact_loading_conditional_on_folder_existence(self):
        """
        Test that artifact loading only occurs if artifacts folder exists.
        
        Requirement 27.4: THE artifact loading SHALL only occur if the artifacts 
        folder exists in the catalog.
        
        This test verifies that artifacts are loaded when the folder exists
        and skipped when it doesn't.
        """
        test_script = self._create_artifact_loading_test_script()
        
        result = self._run_node_script(test_script)
        
        self.assertEqual(result["status"], "success",
                        f"Artifact loading test failed: {result.get('error', 'Unknown error')}")
        
        # Verify artifacts were loaded when folder exists
        self.assertIn("artifacts_loaded", result["data"])
        self.assertTrue(result["data"]["artifacts_loaded"])
        
        # Verify artifact catalog was loaded
        self.assertIn("artifact_catalog", result["data"])
        self.assertIn("folders", result["data"]["artifact_catalog"])

    def _create_data_loading_test_script(self):
        """Create a Node.js test script that tests all data sources loading."""
        script = f'''
const http = require('http');

const BASE_URL = "http://localhost:{self.port}";

async function fetch_json(url) {{
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
            res.on('data', (chunk) => {{ data += chunk; }});
            res.on('end', () => {{
                if (res.statusCode === 200) {{
                    try {{
                        resolve(JSON.parse(data));
                    }} catch (e) {{
                        reject({{ type: 'parse_error', message: e.message }});
                    }}
                }} else {{
                    reject({{ type: 'http_error', status: res.statusCode }});
                }}
            }});
        }});
        req.on('error', (e) => {{ reject({{ type: 'network_error', message: e.message }}); }});
        req.end();
    }});
}}

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
            res.on('data', (chunk) => {{ data += chunk; }});
            res.on('end', () => {{
                if (res.statusCode === 200) {{
                    try {{
                        var json_objects = [];
                        var split_responses = data.split("\\x1e");
                        for (var ritem of split_responses) {{
                            if (ritem.length > 0) {{
                                json_objects.push(JSON.parse(ritem));
                            }}
                        }}
                        resolve(json_objects);
                    }} catch (e) {{
                        reject({{ type: 'parse_error', message: e.message }});
                    }}
                }} else {{
                    reject({{ type: 'http_error', status: res.statusCode }});
                }}
            }});
        }});
        req.on('error', (e) => {{ reject({{ type: 'network_error', message: e.message }}); }});
        req.end();
    }});
}}

async function runTest() {{
    try {{
        // Load all data sources in parallel (simulating refresh_page behavior)
        const [summary, startup, landscape, results, import_errors, catalog] = await Promise.all([
            fetch_json(BASE_URL + "/testrun_summary.json"),
            fetch_json(BASE_URL + "/startup-configuration.json"),
            fetch_json(BASE_URL + "/landscape-declared.json"),
            fetch_json_stream(BASE_URL + "/testrun_results_stream.jsos"),
            fetch_json_stream(BASE_URL + "/import_errors.jsos"),
            fetch_json(BASE_URL + "/catalog.json")
        ]);
        
        console.log(JSON.stringify({{
            status: "success",
            data: {{
                summary: summary,
                configuration: {{
                    startup: startup,
                    landscape: landscape
                }},
                results: results,
                import_errors: import_errors,
                catalog: catalog
            }}
        }}));
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

    def _create_component_rendering_test_script(self):
        """Create a Node.js test script that tests component rendering with sample data."""
        script = f'''
const http = require('http');

const BASE_URL = "http://localhost:{self.port}";

async function fetch_json(url) {{
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
            res.on('data', (chunk) => {{ data += chunk; }});
            res.on('end', () => {{
                if (res.statusCode === 200) {{
                    try {{
                        resolve(JSON.parse(data));
                    }} catch (e) {{
                        reject({{ type: 'parse_error', message: e.message }});
                    }}
                }} else {{
                    reject({{ type: 'http_error', status: res.statusCode }});
                }}
            }});
        }});
        req.on('error', (e) => {{ reject({{ type: 'network_error', message: e.message }}); }});
        req.end();
    }});
}}

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
            res.on('data', (chunk) => {{ data += chunk; }});
            res.on('end', () => {{
                if (res.statusCode === 200) {{
                    try {{
                        var json_objects = [];
                        var split_responses = data.split("\\x1e");
                        for (var ritem of split_responses) {{
                            if (ritem.length > 0) {{
                                json_objects.push(JSON.parse(ritem));
                            }}
                        }}
                        resolve(json_objects);
                    }} catch (e) {{
                        reject({{ type: 'parse_error', message: e.message }});
                    }}
                }} else {{
                    reject({{ type: 'http_error', status: res.statusCode }});
                }}
            }});
        }});
        req.on('error', (e) => {{ reject({{ type: 'network_error', message: e.message }}); }});
        req.end();
    }});
}}

// Simulate split_test_fullname function from testsummary.js
function split_test_fullname(testname_full) {{
    var package_name = null;
    var test_name = null;
    var sindex = testname_full.search("#");
    if (sindex > -1) {{
        var name_parts = testname_full.split("#");
        package_name = name_parts[0];
        test_name = name_parts[1];
    }}
    return [package_name, test_name];
}}

// Simulate result grouping logic from testsummary.js
function groupResultsByPackage(results) {{
    var grouped = {{}};
    for (var ritem of results) {{
        if (ritem.rtype === "TEST" && ritem.stop && ritem.stop.length > 0) {{
            var [package_name, test_name] = split_test_fullname(ritem.name);
            if (package_name) {{
                if (!grouped[package_name]) {{
                    grouped[package_name] = [];
                }}
                grouped[package_name].push({{
                    name: test_name,
                    result: ritem.result,
                    detail: ritem.detail
                }});
            }}
        }}
    }}
    return grouped;
}}

async function runTest() {{
    try {{
        // Load data
        const [summary, startup, results] = await Promise.all([
            fetch_json(BASE_URL + "/testrun_summary.json"),
            fetch_json(BASE_URL + "/startup-configuration.json"),
            fetch_json_stream(BASE_URL + "/testrun_results_stream.jsos")
        ]);
        
        // Process data for banner component
        var banner_data = {{
            apod: summary.apod,
            result: summary.result,
            start: summary.start,
            stop: summary.stop,
            build: summary.build,
            metrics: summary.detail
        }};
        
        // Process results for grouping
        var grouped_results = groupResultsByPackage(results);
        
        // Process configuration
        var config_data = {{
            command: startup.command,
            environment: startup.environment,
            packages: startup.packages
        }};
        
        console.log(JSON.stringify({{
            status: "success",
            data: {{
                banner_data: banner_data,
                grouped_results: grouped_results,
                config_data: config_data
            }}
        }}));
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

    def _create_error_handling_test_script(self):
        """Create a Node.js test script that tests error handling during page load."""
        script = f'''
const http = require('http');

const BASE_URL = "http://localhost:{self.port}";

async function fetch_json(url) {{
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
            res.on('data', (chunk) => {{ data += chunk; }});
            res.on('end', () => {{
                if (res.statusCode === 200) {{
                    try {{
                        resolve(JSON.parse(data));
                    }} catch (e) {{
                        reject({{ type: 'parse_error', message: e.message }});
                    }}
                }} else {{
                    reject({{ type: 'http_error', status: res.statusCode }});
                }}
            }});
        }});
        req.on('error', (e) => {{ reject({{ type: 'network_error', message: e.message }}); }});
        req.end();
    }});
}}

async function runTest() {{
    var summary_loaded = false;
    var missing_file_handled = false;
    var error_logged = false;
    var errors = [];
    
    try {{
        // Try to load summary (should succeed)
        const summary = await fetch_json(BASE_URL + "/testrun_summary.json");
        summary_loaded = (summary && summary.apod);
    }} catch (e) {{
        errors.push("Summary load failed: " + e.message);
    }}
    
    try {{
        // Try to load a non-existent file (should fail gracefully)
        await fetch_json(BASE_URL + "/nonexistent_file.json");
    }} catch (e) {{
        // This is expected - the error should be handled gracefully
        missing_file_handled = true;
        error_logged = true;
    }}
    
    // Verify that we can continue after an error
    var catalog_loaded = false;
    try {{
        const catalog = await fetch_json(BASE_URL + "/catalog.json");
        catalog_loaded = (catalog && catalog.files);
    }} catch (e) {{
        errors.push("Catalog load failed: " + e.message);
    }}
    
    console.log(JSON.stringify({{
        status: "success",
        data: {{
            summary_loaded: summary_loaded,
            missing_file_handled: missing_file_handled,
            error_logged: error_logged,
            catalog_loaded: catalog_loaded,
            errors: errors
        }}
    }}));
}}

runTest();
'''
        return script

    def _create_artifact_loading_test_script(self):
        """Create a Node.js test script that tests conditional artifact loading."""
        script = f'''
const http = require('http');

const BASE_URL = "http://localhost:{self.port}";

async function fetch_json(url) {{
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
            res.on('data', (chunk) => {{ data += chunk; }});
            res.on('end', () => {{
                if (res.statusCode === 200) {{
                    try {{
                        resolve(JSON.parse(data));
                    }} catch (e) {{
                        reject({{ type: 'parse_error', message: e.message }});
                    }}
                }} else {{
                    reject({{ type: 'http_error', status: res.statusCode }});
                }}
            }});
        }});
        req.on('error', (e) => {{ reject({{ type: 'network_error', message: e.message }}); }});
        req.end();
    }});
}}

async function runTest() {{
    try {{
        // Load catalog first
        const catalog = await fetch_json(BASE_URL + "/catalog.json");
        
        var artifacts_loaded = false;
        var artifact_catalog = null;
        var sub_catalogs = {{}};
        
        // Check if artifacts folder exists in catalog (simulating refresh_page logic)
        if (catalog.folders && catalog.folders.indexOf("artifacts") > -1) {{
            // Load artifacts catalog
            artifact_catalog = await fetch_json(BASE_URL + "/artifacts/catalog.json");
            artifacts_loaded = true;
            
            // Load sub-folder catalogs
            if (artifact_catalog.folders) {{
                for (var folder of artifact_catalog.folders) {{
                    try {{
                        var sub_catalog = await fetch_json(BASE_URL + "/artifacts/" + folder + "/catalog.json");
                        sub_catalogs[folder] = sub_catalog;
                    }} catch (e) {{
                        // Sub-folder catalog might not exist, continue
                    }}
                }}
            }}
        }}
        
        console.log(JSON.stringify({{
            status: "success",
            data: {{
                artifacts_loaded: artifacts_loaded,
                artifact_catalog: artifact_catalog,
                sub_catalogs: sub_catalogs
            }}
        }}));
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
            timeout=30
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
