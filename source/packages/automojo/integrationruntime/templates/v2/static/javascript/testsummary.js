/*
    Author: "Myron Walker"
    Copyright: "Copyright 2025, Automation Mojo LLC"
    Version: = "2.0.0"
    Email: myron.walker@gmail.com
*/

/**
 * @fileoverview Main application logic for the TestSummary HTML report.
 * Handles data loading, result processing, and page refresh orchestration.
 * @module testsummary
 */

// Summary State
/**
 * Global test run summary data loaded from testrun_summary.json.
 * @type {Object|null}
 */
var g_summary = null;

// Configuration State
/**
 * Global landscape configuration data loaded from landscape-declared.json.
 * @type {Object|null}
 */
var g_landscape_configuration = null
/**
 * Global startup configuration data loaded from startup-configuration.json.
 * @type {Object|null}
 */
var g_startup_configuration = null;

// Results State
/**
 * Global test results data, organized by package name when display mode is GROUPED.
 * @type {Object|null}
 */
var g_results = null;
/**
 * Counter for passed tests.
 * @type {number}
 */
var g_counter_passed = 0;
/**
 * Counter for failed tests.
 * @type {number}
 */
var g_counter_failed = 0;
/**
 * Counter for errored tests.
 * @type {number}
 */
var g_counter_errors = 0;
/**
 * Counter for skipped tests.
 * @type {number}
 */
var g_counter_skipped = 0;
/**
 * Counter for total tests.
 * @type {number}
 */
var g_counter_total = 0;
/**
 * Display mode for results: "GROUPED" (by package), "TREE" (hierarchical), or "TIMELINE" (chronological).
 * @type {string}
 */
var g_display_mode = "GROUPED";
/**
 * Filter mode for results: "NONE", "PASSED", "FAILED", "ERRORED", or "SKIPPED".
 * @type {string}
 */
var g_filter_mode = "NONE";
/**
 * Grouping option for results: "package", "result", or "module".
 * @type {string}
 */
var g_grouping_option = "package";

// Artifacts State
/**
 * Global artifacts catalog data loaded from artifacts/catalog.json.
 * @type {Object|null}
 */
var g_artifacts_catalog = null;
/**
 * Global sub-catalogs for each artifact folder.
 * @type {Object|null}
 */
var g_artifacts_sub_catalogs = null;
/**
 * Artifact tab buttons (unused, reserved for future use).
 * @type {Object|null}
 */
var g_artifacts_buttons = null;
/**
 * Artifact tabs (unused, reserved for future use).
 * @type {Object|null}
 */
var g_artifacts_tabs = null;

// Import Error State
/**
 * Global import errors data loaded from import_errors.jsos.
 * @type {Array|null}
 */
var g_import_errors = null;

// File Catalog State
/**
 * Global file catalog data loaded from catalog.json.
 * @type {Object|null}
 */
var g_catalog = null;

// Bug Server State
/**
 * Flag indicating if a bug server is available (detected via response headers).
 * @type {boolean}
 */
var g_bug_server_available = false;


/*************************************************************************************
 *************************************************************************************
 *
 *                                  HELPER FUNCTIONS
 * 
 *************************************************************************************
 *************************************************************************************/

/**
 * Splits a full test name into package name and test name components.
 * Full test names use '#' as a separator between package and test name.
 * 
 * @function split_test_fullname
 * @param {string} testname_full - The full test name (e.g., "package.module::TestClass#test_method").
 * @returns {Array} A two-element array [package_name, test_name], or [null, null] if no separator found.
 * 
 * @example
 * split_test_fullname('mypackage.tests::TestSuite#test_example');
 * // Returns ['mypackage.tests::TestSuite', 'test_example']
 * 
 * @example
 * split_test_fullname('test_without_package');
 * // Returns [null, null]
 */
function split_test_fullname(testname_full) {
    var package_name = null;
    var test_name = null;

    var sindex = testname_full.search("#");

    if (sindex > -1) {
        name_parts = testname_full.split("#");
        package_name = name_parts[0];
        test_name = name_parts[1];
    }

    return [package_name, test_name];
}


/**
 * Finalizes a test result item by categorizing it and updating counters.
 * Processes moniker suffixes, splits the test name, determines pass/fail/error/skip status,
 * and adds the result to the appropriate package group in the results table.
 * 
 * @function finalize_test_result_item
 * @param {Object} ritem - The test result item to finalize.
 * @param {string} ritem.name - The full test name.
 * @param {string[]} [ritem.monikers] - Optional array of moniker suffixes.
 * @param {string} ritem.result - The test result status ("PASSED", "FAILED", "ERRORED", "SKIPPED").
 * @param {Object} ritem.detail - The test detail object containing errors and failures.
 * @param {Array} ritem.detail.errors - Array of error objects.
 * @param {Array} ritem.detail.failures - Array of failure objects.
 * @param {Object} counters - Counter object to update with result statistics.
 * @param {number} counters.passed - Count of passed tests.
 * @param {number} counters.failed - Count of failed tests.
 * @param {number} counters.errors - Count of errored tests.
 * @param {number} counters.skipped - Count of skipped tests.
 * @param {Object} results_table - Results table object keyed by package name.
 * @returns {void}
 * 
 * @example
 * const counters = { passed: 0, failed: 0, errors: 0, skipped: 0 };
 * const results = {};
 * finalize_test_result_item(testItem, counters, results);
 */
function finalize_test_result_item(ritem, counters, results_table) {

    // =========================================================================
    // RESULT PROCESSING ALGORITHM - Step 1: Build Moniker Suffix
    // =========================================================================
    // Monikers are test variant identifiers (e.g., parameterized test values).
    // They are appended to the test name in bracket notation: test_name:[moniker1][moniker2]
    // This allows distinguishing between different parameterized runs of the same test.
    var moniker_suffix = ""
    if ((ritem.monikers) && (ritem.monikers.length > 0)) {
        moniker_start = "["
        ritem.monikers.forEach(item => {
            // Each moniker is wrapped in brackets and concatenated
            moniker_suffix = moniker_suffix + "[" + item + "]"
            moniker_start = ",["
        });
    }

    // =========================================================================
    // RESULT PROCESSING ALGORITHM - Step 2: Construct Full Test Name
    // =========================================================================
    // Combine the base test name with any moniker suffixes.
    // Format: "package.module::TestClass#test_method:[moniker1][moniker2]"
    var testname_full = ritem.name;
    if (moniker_suffix != "") {
        testname_full = testname_full + ":" + moniker_suffix;
    }

    // =========================================================================
    // RESULT PROCESSING ALGORITHM - Step 3: Split Name into Package and Test
    // =========================================================================
    // The full test name uses '#' as separator between package path and test name.
    // Example: "mypackage.tests::TestSuite#test_example" splits into:
    //   - package_name: "mypackage.tests::TestSuite"
    //   - test_name: "test_example"
    const [package_name, test_name] = split_test_fullname(testname_full);
    ritem.name = test_name
    ritem.package_name = package_name

    // =========================================================================
    // RESULT PROCESSING ALGORITHM - Step 4: Categorize Result Status
    // =========================================================================
    // Result categorization follows a priority hierarchy:
    //   1. Errors (highest priority) - Test encountered an unexpected exception
    //   2. Failures - Test assertions failed
    //   3. Skipped - Test was intentionally skipped
    //   4. Passed - Test completed successfully with no issues
    // This hierarchy ensures errors are counted even if failures also exist.
    var detail = ritem.detail;
    detail.passed = false;
    detail.skipped = false;

    // Check for errors first (highest priority)
    if (detail.errors.length > 0) {
        counters.errors += 1;
    }
    // Then check for failures (second priority)
    else if (detail.failures.length > 0) {
        counters.failed += 1;
    }
    // Finally, check if skipped or passed
    else {
        if (ritem.result == "SKIPPED") {
            detail.skipped = true;
            counters.skipped += 1;
        } else {
            // No errors, no failures, not skipped = passed
            detail.passed = true;
            counters.passed += 1;
        }
    }

    // =========================================================================
    // RESULT PROCESSING ALGORITHM - Step 5: Group by Package Name
    // =========================================================================
    // Results are organized into a hash table keyed by package name.
    // This enables efficient grouping for the "GROUPED" display mode.
    // Each package maps to an array of test result items.
    var package_list = null;
    if (package_name in results_table) {
        // Package already exists, retrieve its result list
        package_list = results_table[package_name];
    } else {
        // First test for this package, create new result list
        package_list = [];
        results_table[package_name] = package_list;
    }

    // Add the processed result item to its package group
    package_list.push(ritem);
}


/*************************************************************************************
 *************************************************************************************
 *
 *                                  ENABLE FUNCTIONS
 * 
 *************************************************************************************
 *************************************************************************************/

/**
 * Enables the artifacts section in the UI.
 * Currently a placeholder for future implementation.
 * 
 * @function enable_artifacts_section
 * @returns {void}
 */
function enable_artifacts_section() {
    //document.getElementById('artifacts-title').style = "display: block";
    //document.getElementById('artifacts-tab-bar').style = "display: block";
    //document.getElementById('artifacts-tab-content').style = "display: block";
}

/*************************************************************************************
 *************************************************************************************
 *
 *                                   LOAD FUNCTIONS
 * 
 *************************************************************************************
 *************************************************************************************/

/**
 * Loads artifact folder catalogs from the artifacts directory.
 * Fetches the main artifacts/catalog.json and then loads sub-catalogs for each folder.
 * Populates g_artifacts_catalog and g_artifacts_sub_catalogs global variables.
 * 
 * @async
 * @function load_artifact_folders
 * @returns {Promise<void>}
 * 
 * @example
 * await load_artifact_folders();
 * console.log('Artifact folders:', Object.keys(g_artifacts_sub_catalogs));
 */
async function load_artifact_folders() {
    g_artifacts_catalog = await fetch_json("artifacts/catalog.json");

    if ((g_artifacts_catalog != null) && (g_artifacts_catalog.folders.length > 0)) {
        enable_artifacts_section();

        g_artifacts_sub_catalogs = {};

        for (var findex in g_artifacts_catalog.folders) {
            var folder = g_artifacts_catalog.folders[findex];
            var folderCatalogURL = "artifacts/" + folder + "/catalog.json";

            var artifact_catalog = await fetch_json(folderCatalogURL).catch(err => {
                console.log("The '" + folder + "' artifacts folder does not have a 'catalog.json' file.")
            });

            if ((artifact_catalog != null) && (artifact_catalog != "")) {
                g_artifacts_sub_catalogs[folder] = artifact_catalog;
            }
        }
    }
}

/**
 * Loads the main catalog.json file into the g_catalog global variable.
 * The catalog contains lists of files and folders in the output directory.
 * 
 * @async
 * @function load_catalog
 * @returns {Promise<void>}
 * 
 * @example
 * await load_catalog();
 * console.log('Files:', g_catalog.files);
 * console.log('Folders:', g_catalog.folders);
 */
async function load_catalog() {
    g_catalog = await fetch_json("catalog.json");
}

/**
 * Loads configuration files (landscape and startup configuration).
 * Fetches landscape-declared.json and startup-configuration.json.
 * Populates g_landscape_configuration and g_startup_configuration global variables.
 * Errors are logged but do not prevent page loading.
 * 
 * @async
 * @function load_configuration
 * @returns {Promise<void>}
 * 
 * @example
 * await load_configuration();
 * if (g_startup_configuration) {
 *   console.log('Command:', g_startup_configuration.command);
 * }
 */
async function load_configuration() {

    g_landscape_configuration = await fetch_json("landscape-declared.json").catch(err => {
        console.log("Unable to load the landscape declaration file='landscape-declared.json'.")
    });

    g_startup_configuration = await fetch_json("startup-configuration.json").catch(err => {
        console.log("Unable to load the landscape declaration file='startup-configuration.json'.")
    });

}

/**
 * Loads import errors from the import_errors.jsos file.
 * Populates the g_import_errors global variable with an array of import error objects.
 * 
 * @async
 * @function load_import_errors
 * @returns {Promise<void>}
 * 
 * @example
 * await load_import_errors();
 * g_import_errors.forEach(err => console.log('Import error:', err.module));
 */
async function load_import_errors() {
    g_import_errors = await fetch_json_stream("import_errors.jsos")
}

/**
 * Loads test results from the JSOS stream file and processes them.
 * Handles different display modes (GROUPED, TREE) and filter modes.
 * Processes TEST, TASKING_GROUP, and TASKING record types.
 * Populates the g_results global variable with processed results.
 * 
 * @async
 * @function load_results_from_stream
 * @param {Object} counters - Counter object to update with result statistics.
 * @param {number} counters.passed - Count of passed tests.
 * @param {number} counters.failed - Count of failed tests.
 * @param {number} counters.errors - Count of errored tests.
 * @param {number} counters.skipped - Count of skipped tests.
 * @returns {Promise<void>}
 * 
 * @example
 * const counters = { passed: 0, failed: 0, errors: 0, skipped: 0 };
 * await load_results_from_stream(counters);
 * console.log('Passed:', counters.passed, 'Failed:', counters.failed);
 */
async function load_results_from_stream(counters) {

    // =========================================================================
    // RESULT STREAM LOADING - Step 1: Fetch JSOS Stream
    // =========================================================================
    // Load the test results from the JSOS (JSON Separated Object Stream) file.
    // The stream contains TEST, TASKING_GROUP, and TASKING records that form
    // a hierarchical structure representing the test execution tree.
    var results = await fetch_json_stream("testrun_results_stream.jsos");

    if (g_display_mode == "GROUPED") {

        // =====================================================================
        // GROUPED DISPLAY MODE - Initialize Data Structures
        // =====================================================================
        // g_results: Hash table mapping package names to arrays of test results
        // parent_lookup: Temporary lookup table for tracking parent-child relationships
        //   - Keys are instance IDs (unique identifiers for each record)
        //   - Values are the record objects themselves
        //   - Used to link TASKING_GROUP and TASKING records to their parent TEST
        g_results = {};

        var parent_lookup = {};

        if (g_filter_mode == "NONE") {
            // =================================================================
            // UNFILTERED PROCESSING - Process All Records
            // =================================================================
            // Process records in order, maintaining parent-child relationships.
            // The JSOS stream contains records in execution order, with preview
            // records (stop="") appearing before final result records.
            var rcount = results.length;

            while (rcount > 0) {

                var ritem = results.shift();

                // Extract instance ID (unique identifier) and parent ID for linking
                var ritem_instance = ritem.instance;
                var ritem_parentid = ritem.parent;

                if (ritem.rtype == "TEST") {
                    // =========================================================
                    // TEST RECORD PROCESSING
                    // =========================================================
                    // Tests appear twice in the stream:
                    //   1. Preview record (stop="") - written when test starts
                    //   2. Final record (stop has value) - written when test ends
                    // We use the preview to establish parent-child links for
                    // TASKING_GROUP and TASKING records that arrive between
                    // the preview and final records.

                    if (!parent_lookup.hasOwnProperty(ritem_instance)) {
                        // First occurrence - this is the preview record
                        // Initialize tasking_groups array to collect child records
                        ritem.tasking_groups = [];
                        if (ritem.stop.length == 0) {
                            // Preview record - store in lookup for child linking
                            parent_lookup[ritem_instance] = ritem;
                        } else {
                            // Final record with no preview - process immediately
                            // (This can happen if test has no tasking groups)
                            finalize_test_result_item(ritem, counters, g_results);
                        }

                    } else {
                        // Second occurrence - this is the final result record
                        // Transfer tasking_groups from preview to final record
                        var preview_ritem = parent_lookup[ritem_instance];
                        ritem.tasking_groups = preview_ritem.tasking_groups;

                        // Process and categorize the final test result
                        finalize_test_result_item(ritem, counters, g_results);
                    }

                } else if (ritem.rtype == "TASKING_GROUP") {
                    // =========================================================
                    // TASKING_GROUP RECORD PROCESSING
                    // =========================================================
                    // Tasking groups are containers for distributed task execution.
                    // They appear twice: preview (when group starts) and final
                    // (when group completes). We link them to their parent TEST.

                    if (parent_lookup.hasOwnProperty(ritem_parentid)) {
                        // Parent TEST exists in lookup - we can link this group

                        if (!parent_lookup.hasOwnProperty(ritem_instance)) {
                            // First occurrence - preview record for tasking group
                            // Initialize tracking arrays and counters
                            parent_item = parent_lookup[ritem_parentid];
                            ritem.taskings = [];  // Will hold individual TASKING records
                            ritem.passed = 0;     // Counter for passed taskings
                            ritem.failed = 0;     // Counter for failed taskings
                            ritem.errored = 0;    // Counter for errored taskings

                            // Link to parent TEST's tasking_groups array
                            parent_item.tasking_groups.push(ritem);

                            // Store in lookup so TASKING records can find this group
                            parent_lookup[ritem_instance] = ritem;

                        } else {
                            // Second occurrence - final record for tasking group
                            // Update the stop time on the original group record
                            original_tgroup = parent_lookup[ritem_instance];
                            original_tgroup.stop = ritem.stop;
                        }

                    }

                } else if (ritem.rtype == "TASKING") {
                    // =========================================================
                    // TASKING RECORD PROCESSING
                    // =========================================================
                    // Individual taskings are the actual distributed work units.
                    // They are linked to their parent TASKING_GROUP and their
                    // results update the group's pass/fail/error counters.

                    if (parent_lookup.hasOwnProperty(ritem_parentid)) {
                        // Parent TASKING_GROUP exists - link this tasking
                        var parent_item = parent_lookup[ritem_parentid];
                        parent_item.taskings.push(ritem)

                        // Update parent group counters based on tasking result
                        // Priority: errors > failures > passed
                        if (ritem.detail.errors.length > 0) {
                            parent_item.errored += 1;
                        }
                        else if (ritem.detail.failures.length > 0) {
                            parent_item.failed += 1;
                        }
                        else {
                            parent_item.passed += 1;
                        }
                    }

                } else if (ritem.rtype == "CHECK") {
                    // =========================================================
                    // CHECK RECORD PROCESSING
                    // =========================================================
                    // Individual check results from property tests.
                    // They are linked to their parent TEST's checks array.
                    // CHECK records are NOT counted in top-level counters.

                    if (parent_lookup.hasOwnProperty(ritem_parentid)) {
                        var parent_item = parent_lookup[ritem_parentid];

                        // Initialize checks tracking if not yet present
                        if (!parent_item.checks) {
                            parent_item.checks = [];
                            parent_item.checks_passed = 0;
                            parent_item.checks_failed = 0;
                            parent_item.checks_errored = 0;
                        }

                        parent_item.checks.push(ritem);

                        // Update check counters based on check result
                        if (ritem.result == "PASSED") {
                            parent_item.checks_passed += 1;
                        } else if (ritem.result == "FAILED") {
                            parent_item.checks_failed += 1;
                        } else if (ritem.result == "ERRORED") {
                            parent_item.checks_errored += 1;
                        }
                    }
                }

                rcount = rcount - 1;
            }

        } else {
            // =================================================================
            // FILTERED PROCESSING - Only Include Matching Results
            // =================================================================
            // When a filter is active, only include TEST records that match
            // the specified result status (PASSED, FAILED, ERRORED, SKIPPED).
            // Tasking groups and taskings are not included in filtered view.

            var filter_status = g_filter_mode;
            var rcount = results.length;
            while (rcount > 0) {
                var ritem = results.shift();
                // Only include TEST records with matching result status
                if ((ritem.rtype == "TEST") && (ritem.result == filter_status)) {
                    g_results.push(ritem);
                }
                rcount = rcount - 1;
            }

        }

    } else {
        // =====================================================================
        // TREE DISPLAY MODE (Not Yet Implemented)
        // =====================================================================
        // TODO: Add code to create tree-based g_results structure
        // This would preserve the full hierarchical relationship between
        // tests, tasking groups, and taskings for tree-view rendering.
    }

}

/**
 * Loads test results and updates global counters.
 * Initializes counters, calls load_results_from_stream, and updates global counter variables.
 * 
 * @async
 * @function load_results
 * @returns {Promise<void>}
 * 
 * @example
 * await load_results();
 * console.log('Total passed:', g_counter_passed);
 */
async function load_results() {

    counters = {
        passed: 0,
        errors: 0,
        failed: 0,
        skipped: 0
    }

    // Because we dont necessarily display the results in a maching result tree, for now we probably should just
    // load the results from the results stream
    await load_results_from_stream(counters)

    g_counter_passed = counters.passed;
    g_counter_errors = counters.errors;
    g_counter_failed = counters.failed;
    g_counter_skipped = counters.skipped;

}

/**
 * Loads the test run summary from testrun_summary.json.
 * Populates g_summary global variable and checks for bug server availability via headers.
 * 
 * @async
 * @function load_summary
 * @returns {Promise<void>}
 * 
 * @example
 * await load_summary();
 * console.log('Test result:', g_summary.result);
 */
async function load_summary() {
    respHeaders = {}

    g_summary = await fetch_json("testrun_summary.json", respHeaders);

    if (respHeaders.hasOwnProperty("AM-BUG-SERVER-TYPE")) {
        g_bug_server_available = true;
    }
}

/*************************************************************************************
 *************************************************************************************
 *
 *                                 ELEMENT CREATION
 * 
 *************************************************************************************
 *************************************************************************************/

/**
 * Adjusts the display name for index identifiers based on the path context.
 * Provides human-readable names for various configuration objects like credentials,
 * devices, and scan results.
 * 
 * @function adjust_index_identifier
 * @param {string[]} path - Array of path segments indicating the context.
 * @param {string} name - The original name/index.
 * @param {Object} value - The value object containing additional properties.
 * @returns {string} The adjusted display name with additional context.
 * 
 * @example
 * adjust_index_identifier(['landscape', 'pod', 'devices'], '0', {deviceType: 'network/ssh', host: '192.168.1.1'});
 * // Returns '0 - 192.168.1.1'
 */
function adjust_index_identifier(path, name, value) {
    var display_name = name;

    var modpath = path.join("/")
    if (modpath == "landscape/environment/credentials") {
        display_name = display_name + " - " + value["identifier"];
    } else if (modpath == "landscape/pod/devices") {
        var devtype = value["deviceType"];
        if (devtype == "network/upnp") {
            var upnpinfo = value["upnp"];
            display_name = display_name + " - " + upnpinfo["modelNumber"] + ", " + upnpinfo["modelName"] + " - " + upnpinfo["IP"] + " - " + upnpinfo["USN"];
        } else if (devtype == "network/ssh") {
            display_name = display_name + " - " + value["host"];
        }

    } else if ((modpath == "landscape/pod/power") || (modpath == "landscape/pod/serial")) {
        display_name = display_name + " - " + value["name"]
    } else if ((modpath == "startup/scans/upnp/found_devices") ||
        (modpath == "startup/scans/upnp/matching_devices") ||
        (modpath == "startup/scans/upnp/missing_devices")) {
        display_name = display_name + " - " + value["IP"];
        var usn = value["USN"];
        if (usn != undefined) {
            display_name = display_name + " - " + usn;
        }
    } else if ((modpath == "startup/scans/ssh/matching_devices") ||
        (modpath == "startup/scans/ssh/missing_devices")) {
        var devtype = value["deviceType"];
        if (devtype == "network/upnp") {
            var upnpinfo = value["upnp"];
            display_name = display_name + " - " + value["host"] + " - " + upnpinfo["modelNumber"] + ", " + upnpinfo["modelName"] + " - " + upnpinfo["USN"];
        } else if (devtype == "network/ssh") {
            display_name = display_name + " - " + value["host"];
        }
    }


    return display_name;
}

/**
 * Escapes HTML entities in a string to prevent XSS vulnerabilities.
 * Replaces &, <, and > with their HTML entity equivalents.
 * 
 * @function entity_escape
 * @param {string} tgtstr - The string to escape.
 * @returns {string} The escaped string safe for HTML insertion.
 * 
 * @example
 * entity_escape('<script>alert("XSS")</script>');
 * // Returns '&lt;script&gt;alert("XSS")&lt;/script&gt;'
 * 
 * @example
 * entity_escape('Tom & Jerry');
 * // Returns 'Tom &amp; Jerry'
 */
function entity_escape(tgtstr) {
    return tgtstr.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}


/*************************************************************************************
 *************************************************************************************
 *
 *                                   SECTION REFRESH
 * 
 *************************************************************************************
 *************************************************************************************/

/**
 * Refreshes the artifacts section by syncing data to the TestSummaryArtifacts component.
 * Uses g_artifacts_catalog and g_artifacts_sub_catalogs global variables.
 * 
 * @function refresh_artifacts
 * @returns {void}
 */
function refresh_artifacts() {

    var artifactsEl = document.getElementById("testsummary-artifacts");

    artifactsEl.syncData(g_artifacts_catalog, g_artifacts_sub_catalogs);

}

/**
 * Refreshes the catalog section (files and folders navigation).
 * Syncs g_catalog data to the TestSummaryFilesAndFolders component.
 * 
 * @function refresh_catalog
 * @returns {void}
 */
function refresh_catalog() {
    var filesAndFoldersEl = document.getElementById("testsummary-filesandfolders");

    filesAndFoldersEl.syncData(g_catalog.files, g_catalog.folders);

}

/**
 * Refreshes the import errors section.
 * Syncs g_import_errors data to the TestSummaryImportFailures component.
 * 
 * @function refresh_import_errors
 * @returns {void}
 */
function refresh_import_errors() {
    var impErrorEl = document.getElementById("testsummary-importfailures");

    impErrorEl.syncData(g_import_errors);
}

/**
 * Refreshes the startup environment section.
 * Creates and appends startup environment panels to the configuration body.
 * Errors are silently caught to prevent page failure.
 * 
 * @function refresh_startup_environment
 * @returns {void}
 */
function refresh_startup_environment() {
    try {
        var startupNodeElement = create_startup_environment_panels("startup", g_startup_configuration["startup"]);
        configurationBodyElement.appendChild(startupNodeElement);
    } catch (e) {
    }
}

/**
 * Refreshes the startup landscape section.
 * Creates and appends startup landscape panels to the configuration body.
 * Errors are silently caught to prevent page failure.
 * 
 * @function refresh_startup_landscape
 * @returns {void}
 */
function refresh_startup_landscape() {
    var configurationBodyElement = document.getElementById("test-configuration-body");

    try {
        var landscapeNodeElement = create_startup_landscape_panels("landscape", g_startup_configuration["landscape"]);
        configurationBodyElement.appendChild(landscapeNodeElement);
    } catch (e) {
    }
}

/**
 * Refreshes the configuration section.
 * Syncs startup and landscape configuration data to the TestSummaryConfiguration component.
 * 
 * @function refresh_configuration
 * @returns {void}
 */
function refresh_configuration() {
    var configurationComponent = document.getElementById("testsummary-configuration");

    configurationComponent.syncData(g_startup_configuration, g_landscape_configuration)
}

/**
 * Refreshes the results content section with results grouped by package.
 * Syncs g_results data to the TestSummaryResultDetail component in "render_by_package" mode.
 * 
 * @function refesh_results_content_as_grouped
 * @returns {void}
 */
function refesh_results_content_as_grouped() {
    var resultsDetail = document.getElementById("testsummary-resultdetail");

    resultsDetail.syncData("render_by_package", g_results, g_grouping_option)
}

/**
 * Refreshes the results content section with results as a hierarchical tree.
 * Syncs g_results data to the TestSummaryResultDetail component in "render_as_tree" mode.
 * 
 * @function refresh_results_content_as_tree
 * @returns {void}
 */
function refresh_results_content_as_tree() {
    var resultsDetail = document.getElementById("testsummary-resultdetail");

    resultsDetail.syncData("render_as_tree", g_results, g_grouping_option)
}

/**
 * Refreshes the results content section with results as a timeline view.
 * Syncs g_results data to the TestSummaryResultDetail component in "render_as_timeline" mode.
 * 
 * @function refresh_results_content_as_timeline
 * @returns {void}
 */
function refresh_results_content_as_timeline() {
    var resultsDetail = document.getElementById("testsummary-resultdetail");

    resultsDetail.syncData("render_as_timeline", g_results)
}

/**
 * Sets the display mode for results rendering.
 * Valid modes are: "GROUPED", "TREE", "TIMELINE".
 * 
 * @function set_display_mode
 * @param {string} mode - The display mode to set.
 * @returns {void}
 * 
 * @example
 * set_display_mode("TREE");
 */
function set_display_mode(mode) {
    var validModes = ["GROUPED", "TREE", "TIMELINE"];
    if (validModes.indexOf(mode) > -1) {
        g_display_mode = mode;
    } else {
        console.warn("Invalid display mode: " + mode + ". Valid modes are: " + validModes.join(", "));
    }
}

/**
 * Sets the grouping option for results rendering.
 * Valid options are: "package", "result", "module".
 * 
 * @function set_grouping_option
 * @param {string} option - The grouping option to set.
 * @returns {void}
 * 
 * @example
 * set_grouping_option("result");
 */
function set_grouping_option(option) {
    var validOptions = ["package", "result", "module"];
    if (validOptions.indexOf(option) > -1) {
        g_grouping_option = option;
    } else {
        console.warn("Invalid grouping option: " + option + ". Valid options are: " + validOptions.join(", "));
    }
}

/**
 * Refreshes the results content based on the current display mode.
 * 
 * @function refresh_results_content
 * @returns {void}
 */
function refresh_results_content() {
    if (g_display_mode == "GROUPED") {
        refesh_results_content_as_grouped();
    } else if (g_display_mode == "TREE") {
        refresh_results_content_as_tree();
    } else if (g_display_mode == "TIMELINE") {
        refresh_results_content_as_timeline();
    } else {
        // Default to grouped view
        refesh_results_content_as_grouped();
    }
}

/**
 * Refreshes the summary banner section.
 * Syncs g_summary data to the TestSummaryBanner component if available.
 * 
 * @function refresh_summary
 * @returns {void}
 */
function refresh_summary() {

    if (g_summary != null) {
        var summaryComponent = document.getElementById("testsummary-banner");

        summaryComponent.syncData(g_summary)
    }

}

/**
 * Refreshes the comparison and trend analysis components with current results.
 * Passes the processed results to the comparison components so they can
 * compare against baseline data when loaded.
 * 
 * @function refresh_comparison_components
 * @returns {void}
 */
function refresh_comparison_components() {
    // Sync current results to comparison component
    var comparisonComponent = document.getElementById("testsummary-comparison");
    if (comparisonComponent && g_results) {
        comparisonComponent.setCurrentResultsFromDetail(g_results);
    }

    // Sync current results to trend analysis component
    var trendComponent = document.getElementById("testsummary-trend-analysis");
    if (trendComponent && g_results) {
        trendComponent.syncData(g_results);
    }
}

/*************************************************************************************
 *************************************************************************************
 *
 *                                      PAGE LOAD
 * 
 *************************************************************************************
 *************************************************************************************/

/**
 * Main page refresh orchestration function.
 * Loads all data sources in parallel and triggers corresponding refresh functions.
 * Handles summary, configuration, results, import errors, catalog, and artifacts.
 * Also triggers Prism.js syntax highlighting after results are rendered.
 * 
 * @async
 * @function refresh_page
 * @returns {Promise<void>}
 * 
 * @example
 * // Called on page load
 * refresh_page().then(() => console.log('Page refresh complete'));
 */
async function refresh_page() {

    // =========================================================================
    // PAGE REFRESH ORCHESTRATION - Overview
    // =========================================================================
    // This function coordinates the loading and rendering of all page sections.
    // Data sources are loaded in PARALLEL for optimal performance, with each
    // load triggering its corresponding refresh function upon completion.
    //
    // Load Order (all start simultaneously):
    //   1. Summary (testrun_summary.json) -> refresh_summary()
    //   2. Configuration (landscape + startup) -> refresh_configuration()
    //   3. Results (testrun_results_stream.jsos) -> refresh_results_content()
    //   4. Import Errors (import_errors.jsos) -> refresh_import_errors()
    //   5. Catalog (catalog.json) -> refresh_catalog() + conditional artifacts
    //
    // This parallel loading pattern minimizes total page load time by not
    // waiting for one resource before starting the next.
    // =========================================================================

    // =========================================================================
    // LOAD SECTION 1: Test Run Summary
    // =========================================================================
    // Load the summary data and update the banner component.
    // The summary contains overall test run metrics and status.
    load_summary().then(() => {
        refresh_summary();
    });

    // =========================================================================
    // LOAD SECTION 2: Configuration Data
    // =========================================================================
    // Load landscape and startup configuration files.
    // These provide context about the test environment and settings.
    load_configuration().then(() => {
        refresh_configuration();
    });

    // =========================================================================
    // LOAD SECTION 3: Test Results
    // =========================================================================
    // Load and process the test results stream.
    // After results are rendered, trigger Prism.js for syntax highlighting
    // of code snippets in error tracebacks.
    load_results().then(() => {
        // Use the unified refresh function that handles all display modes
        refresh_results_content();

        // =====================================================================
        // COMPARISON COMPONENTS - Sync Current Results
        // =====================================================================
        // Pass the current results to the comparison and trend analysis
        // components so they can compare against baseline data when loaded.
        refresh_comparison_components();

        // =====================================================================
        // SYNTAX HIGHLIGHTING - Post-Render Processing
        // =====================================================================
        // Prism.js must be called AFTER results are rendered because it
        // searches the DOM for <code> elements to highlight. We use manual
        // mode to control exactly when highlighting occurs.
        try {
            // Enable manual mode to prevent automatic highlighting on page load
            window.Prism = window.Prism || {};
            window.Prism.manual = true;
            // Highlight all code blocks in the document
            Prism.highlightAll();
        } catch (error) {
            // Log but don't fail if Prism is unavailable
            console.warn(error)
        }
    });

    // =========================================================================
    // LOAD SECTION 4: Import Errors
    // =========================================================================
    // Load any import errors that occurred during test discovery.
    // These help diagnose why certain tests may not have run.
    load_import_errors().then(() => {
        refresh_import_errors();
    });

    // =========================================================================
    // LOAD SECTION 5: File Catalog and Artifacts
    // =========================================================================
    // Load the catalog.json which lists all files and folders in the output.
    // If an "artifacts" folder exists, also load artifact sub-catalogs.
    load_catalog().then(() => {
        // Check if artifacts folder exists before attempting to load
        // This prevents unnecessary 404 errors for test runs without artifacts
        if (g_catalog.folders.indexOf("artifacts") > -1) {
            // Artifacts loading is CHAINED (not parallel) because it depends
            // on the catalog being loaded first to know if artifacts exist
            load_artifact_folders().then(() => {
                refresh_artifacts();
            });
        }

        // Always refresh the files/folders navigation
        refresh_catalog();
    });

}