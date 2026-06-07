/*
    Author: "Myron Walker"
    Copyright: "Copyright 2025, Automation Mojo LLC"
    Version: = "2.0.0"
    Email: myron.walker@gmail.com
*/

/**
 * @fileoverview Result comparison components for comparing test results between test runs.
 * Provides functionality to load results from different test runs, compare them,
 * highlight differences, and show trend analysis.
 * @module testsummary-comparison
 */

/**
 * Flag indicating whether comparison components have been registered.
 * @type {boolean}
 * @private
 */
let comparisonComponentsRegistered = false;

/**
 * Component for comparing test results between different test runs.
 * Allows users to load a baseline result set and compare it with the current results.
 * Highlights new failures, fixes, and unchanged tests.
 * 
 * @class TestSummaryResultComparison
 * @extends HTMLElement
 * 
 * @example
 * const comparison = document.getElementById('testsummary-comparison');
 * comparison.syncData(currentResults, baselineResults);
 */
class TestSummaryResultComparison extends HTMLElement {

    static tagname = 'testsummary-comparison'

    static template = `
        <div class="ts-comparison-card">
            <div class="ts-section-header">
                <h2 class="zero-margins-and-padding">Result Comparison</h2>
            </div>
            <div class="ts-comparison-toolbar">
                <div class="ts-comparison-load-section">
                    <label for="id-baseline-url" class="ts-comparison-label">Baseline URL:</label>
                    <input type="text" id="id-baseline-url" class="ts-comparison-input" 
                           placeholder="Enter path to baseline testrun_summary.json..." 
                           title="Enter the URL or path to the baseline test run results">
                    <button id="id-load-baseline" class="ts-comparison-btn" title="Load baseline results for comparison">
                        Load Baseline
                    </button>
                    <button id="id-clear-comparison" class="ts-comparison-btn ts-comparison-btn-secondary" title="Clear comparison">
                        Clear
                    </button>
                </div>
                <div class="ts-comparison-status" id="id-comparison-status">
                    No baseline loaded
                </div>
            </div>
            <div class="ts-comparison-summary" id="id-comparison-summary" style="display: none;">
                <div class="ts-comparison-summary-item ts-comparison-new-failures">
                    <span class="ts-comparison-summary-label">New Failures:</span>
                    <span class="ts-comparison-summary-value" id="id-new-failures-count">0</span>
                </div>
                <div class="ts-comparison-summary-item ts-comparison-fixes">
                    <span class="ts-comparison-summary-label">Fixes:</span>
                    <span class="ts-comparison-summary-value" id="id-fixes-count">0</span>
                </div>
                <div class="ts-comparison-summary-item ts-comparison-new-tests">
                    <span class="ts-comparison-summary-label">New Tests:</span>
                    <span class="ts-comparison-summary-value" id="id-new-tests-count">0</span>
                </div>
                <div class="ts-comparison-summary-item ts-comparison-removed-tests">
                    <span class="ts-comparison-summary-label">Removed Tests:</span>
                    <span class="ts-comparison-summary-value" id="id-removed-tests-count">0</span>
                </div>
                <div class="ts-comparison-summary-item ts-comparison-unchanged">
                    <span class="ts-comparison-summary-label">Unchanged:</span>
                    <span class="ts-comparison-summary-value" id="id-unchanged-count">0</span>
                </div>
            </div>
            <div class="ts-comparison-filter-bar" id="id-comparison-filter-bar" style="display: none;">
                <button id="id-filter-all-changes" class="ts-comparison-filter-btn ts-comparison-filter-btn-active" data-filter="ALL">
                    All Changes
                </button>
                <button id="id-filter-new-failures" class="ts-comparison-filter-btn ts-comparison-filter-btn-fail" data-filter="NEW_FAILURE">
                    New Failures
                </button>
                <button id="id-filter-fixes" class="ts-comparison-filter-btn ts-comparison-filter-btn-pass" data-filter="FIX">
                    Fixes
                </button>
                <button id="id-filter-new-tests" class="ts-comparison-filter-btn ts-comparison-filter-btn-new" data-filter="NEW_TEST">
                    New Tests
                </button>
                <button id="id-filter-removed" class="ts-comparison-filter-btn ts-comparison-filter-btn-removed" data-filter="REMOVED">
                    Removed
                </button>
            </div>
            <div class="ts-section-detail">
                <div id="id-comparison-content" class="ts-comparison-content">
                    <div class="ts-comparison-placeholder">
                        Load a baseline to compare test results between runs.
                    </div>
                </div>
            </div>
        </div>
    `

    constructor() {
        super();

        const shadowRoot = this.attachShadow({mode: 'open'});
        shadowRoot.innerHTML = this.getTemplate();

        addGlobalStylesToShadowRoot(shadowRoot);

        // State
        this._currentResults = null;
        this._baselineResults = null;
        this._comparisonData = null;
        this._activeFilter = 'ALL';

        // Set up event listeners
        this._setupEventListeners();
    }

    /**
     * Gets the HTML template for this component.
     * @returns {string} The HTML template string.
     */
    getTemplate() {
        return TestSummaryResultComparison.template;
    }

    /**
     * Sets up event listeners for the comparison component.
     * @private
     */
    _setupEventListeners() {
        var self = this;

        // Load baseline button
        var loadBtn = this.shadowRoot.querySelector("#id-load-baseline");
        loadBtn.addEventListener("click", function() {
            self._loadBaseline();
        });

        // Clear comparison button
        var clearBtn = this.shadowRoot.querySelector("#id-clear-comparison");
        clearBtn.addEventListener("click", function() {
            self._clearComparison();
        });

        // URL input - allow Enter key to load
        var urlInput = this.shadowRoot.querySelector("#id-baseline-url");
        urlInput.addEventListener("keypress", function(event) {
            if (event.key === "Enter") {
                self._loadBaseline();
            }
        });

        // Filter buttons
        var filterButtons = this.shadowRoot.querySelectorAll(".ts-comparison-filter-btn");
        filterButtons.forEach(function(btn) {
            btn.addEventListener("click", function(event) {
                var filterValue = event.currentTarget.getAttribute("data-filter");
                self._setActiveFilter(filterValue);
                self._renderComparison();
            });
        });
    }

    /**
     * Loads baseline results from the specified URL.
     * @private
     */
    async _loadBaseline() {
        var urlInput = this.shadowRoot.querySelector("#id-baseline-url");
        var baselineUrl = urlInput.value.trim();

        if (!baselineUrl) {
            this._updateStatus("Please enter a baseline URL", "error");
            return;
        }

        this._updateStatus("Loading baseline...", "loading");

        try {
            // Load baseline summary
            var baselineSummaryUrl = baselineUrl;
            if (!baselineUrl.endsWith("testrun_summary.json")) {
                baselineSummaryUrl = baselineUrl.replace(/\/?$/, "/testrun_summary.json");
            }

            var baselineSummary = await fetch_json(baselineSummaryUrl);
            if (!baselineSummary) {
                this._updateStatus("Failed to load baseline summary", "error");
                return;
            }

            // Load baseline results stream
            var baselineResultsUrl = baselineSummaryUrl.replace("testrun_summary.json", "testrun_results_stream.jsos");
            var baselineResults = await fetch_json_stream(baselineResultsUrl);
            
            if (!baselineResults || baselineResults.length === 0) {
                this._updateStatus("Failed to load baseline results", "error");
                return;
            }

            // Process baseline results into a comparable format
            this._baselineResults = this._processResultsForComparison(baselineResults);
            
            // Perform comparison
            this._performComparison();
            
            this._updateStatus("Baseline loaded: " + baselineSummary.start, "success");

        } catch (error) {
            console.error("Error loading baseline:", error);
            this._updateStatus("Error loading baseline: " + error.message, "error");
        }
    }

    /**
     * Processes raw results into a format suitable for comparison.
     * Creates a map of test names to their results.
     * @param {Array} results - Raw results array from JSOS stream.
     * @returns {Object} Map of test names to result objects.
     * @private
     */
    _processResultsForComparison(results) {
        var processedResults = {};

        for (var i = 0; i < results.length; i++) {
            var result = results[i];
            
            // Only process TEST records with final results (have stop time)
            if (result.rtype === "TEST" && result.stop && result.stop.length > 0) {
                var testName = result.name;
                
                // Add moniker suffix if present
                if (result.monikers && result.monikers.length > 0) {
                    var monikerSuffix = result.monikers.map(function(m) { return "[" + m + "]"; }).join("");
                    testName = testName + ":" + monikerSuffix;
                }

                processedResults[testName] = {
                    name: testName,
                    result: result.result,
                    start: result.start,
                    stop: result.stop,
                    detail: result.detail || {},
                    status: this._getTestStatus(result)
                };
            }
        }

        return processedResults;
    }

    /**
     * Gets the status of a test based on its detail object.
     * @param {Object} test - The test item.
     * @returns {string} The test status: 'PASSED', 'FAILED', 'ERRORED', or 'SKIPPED'.
     * @private
     */
    _getTestStatus(test) {
        if (test.detail) {
            if (test.detail.errors && test.detail.errors.length > 0) {
                return 'ERRORED';
            }
            if (test.detail.failures && test.detail.failures.length > 0) {
                return 'FAILED';
            }
            if (test.detail.skipped) {
                return 'SKIPPED';
            }
            if (test.detail.passed) {
                return 'PASSED';
            }
        }
        return test.result || 'UNKNOWN';
    }

    /**
     * Performs comparison between current and baseline results.
     * @private
     */
    _performComparison() {
        if (!this._currentResults || !this._baselineResults) {
            return;
        }

        var comparison = {
            newFailures: [],
            fixes: [],
            newTests: [],
            removedTests: [],
            unchanged: [],
            statusChanges: []
        };

        var currentTestNames = Object.keys(this._currentResults);
        var baselineTestNames = Object.keys(this._baselineResults);

        // Find new tests and compare existing tests
        for (var i = 0; i < currentTestNames.length; i++) {
            var testName = currentTestNames[i];
            var currentTest = this._currentResults[testName];

            if (!this._baselineResults.hasOwnProperty(testName)) {
                // New test
                comparison.newTests.push({
                    name: testName,
                    current: currentTest,
                    baseline: null,
                    changeType: 'NEW_TEST'
                });
            } else {
                // Existing test - compare status
                var baselineTest = this._baselineResults[testName];
                var currentStatus = currentTest.status;
                var baselineStatus = baselineTest.status;

                if (currentStatus !== baselineStatus) {
                    var changeItem = {
                        name: testName,
                        current: currentTest,
                        baseline: baselineTest,
                        currentStatus: currentStatus,
                        baselineStatus: baselineStatus
                    };

                    // Categorize the change
                    if (this._isFailure(currentStatus) && !this._isFailure(baselineStatus)) {
                        changeItem.changeType = 'NEW_FAILURE';
                        comparison.newFailures.push(changeItem);
                    } else if (!this._isFailure(currentStatus) && this._isFailure(baselineStatus)) {
                        changeItem.changeType = 'FIX';
                        comparison.fixes.push(changeItem);
                    } else {
                        changeItem.changeType = 'STATUS_CHANGE';
                        comparison.statusChanges.push(changeItem);
                    }
                } else {
                    comparison.unchanged.push({
                        name: testName,
                        current: currentTest,
                        baseline: baselineTest,
                        changeType: 'UNCHANGED'
                    });
                }
            }
        }

        // Find removed tests
        for (var j = 0; j < baselineTestNames.length; j++) {
            var baselineTestName = baselineTestNames[j];
            if (!this._currentResults.hasOwnProperty(baselineTestName)) {
                comparison.removedTests.push({
                    name: baselineTestName,
                    current: null,
                    baseline: this._baselineResults[baselineTestName],
                    changeType: 'REMOVED'
                });
            }
        }

        this._comparisonData = comparison;
        this._updateComparisonSummary();
        this._renderComparison();
    }

    /**
     * Checks if a status represents a failure (FAILED or ERRORED).
     * @param {string} status - The test status.
     * @returns {boolean} True if the status is a failure.
     * @private
     */
    _isFailure(status) {
        return status === 'FAILED' || status === 'ERRORED';
    }

    /**
     * Updates the comparison summary display.
     * @private
     */
    _updateComparisonSummary() {
        if (!this._comparisonData) {
            return;
        }

        var summaryEl = this.shadowRoot.querySelector("#id-comparison-summary");
        summaryEl.style.display = "flex";

        var filterBar = this.shadowRoot.querySelector("#id-comparison-filter-bar");
        filterBar.style.display = "flex";

        this.shadowRoot.querySelector("#id-new-failures-count").innerHTML = this._comparisonData.newFailures.length;
        this.shadowRoot.querySelector("#id-fixes-count").innerHTML = this._comparisonData.fixes.length;
        this.shadowRoot.querySelector("#id-new-tests-count").innerHTML = this._comparisonData.newTests.length;
        this.shadowRoot.querySelector("#id-removed-tests-count").innerHTML = this._comparisonData.removedTests.length;
        this.shadowRoot.querySelector("#id-unchanged-count").innerHTML = this._comparisonData.unchanged.length;
    }

    /**
     * Renders the comparison results based on the active filter.
     * @private
     */
    _renderComparison() {
        var contentEl = this.shadowRoot.querySelector("#id-comparison-content");
        contentEl.innerHTML = "";

        if (!this._comparisonData) {
            contentEl.innerHTML = '<div class="ts-comparison-placeholder">Load a baseline to compare test results between runs.</div>';
            return;
        }

        var itemsToRender = this._getFilteredComparisonItems();

        if (itemsToRender.length === 0) {
            contentEl.innerHTML = '<div class="ts-comparison-placeholder">No changes match the selected filter.</div>';
            return;
        }

        // Group items by change type for better organization
        var groupedItems = this._groupComparisonItems(itemsToRender);

        for (var groupName in groupedItems) {
            if (groupedItems.hasOwnProperty(groupName) && groupedItems[groupName].length > 0) {
                var groupEl = this._createComparisonGroup(groupName, groupedItems[groupName]);
                contentEl.appendChild(groupEl);
            }
        }
    }

    /**
     * Gets comparison items filtered by the active filter.
     * @returns {Array} Filtered comparison items.
     * @private
     */
    _getFilteredComparisonItems() {
        if (!this._comparisonData) {
            return [];
        }

        var items = [];

        switch (this._activeFilter) {
            case 'NEW_FAILURE':
                items = this._comparisonData.newFailures;
                break;
            case 'FIX':
                items = this._comparisonData.fixes;
                break;
            case 'NEW_TEST':
                items = this._comparisonData.newTests;
                break;
            case 'REMOVED':
                items = this._comparisonData.removedTests;
                break;
            case 'ALL':
            default:
                items = items.concat(
                    this._comparisonData.newFailures,
                    this._comparisonData.fixes,
                    this._comparisonData.newTests,
                    this._comparisonData.removedTests,
                    this._comparisonData.statusChanges
                );
                break;
        }

        return items;
    }

    /**
     * Groups comparison items by their change type.
     * @param {Array} items - Comparison items to group.
     * @returns {Object} Items grouped by change type.
     * @private
     */
    _groupComparisonItems(items) {
        var groups = {
            'NEW_FAILURE': [],
            'FIX': [],
            'NEW_TEST': [],
            'REMOVED': [],
            'STATUS_CHANGE': []
        };

        for (var i = 0; i < items.length; i++) {
            var item = items[i];
            if (groups.hasOwnProperty(item.changeType)) {
                groups[item.changeType].push(item);
            }
        }

        return groups;
    }

    /**
     * Creates a comparison group element.
     * @param {string} groupName - The name of the group.
     * @param {Array} items - Items in the group.
     * @returns {HTMLElement} The group element.
     * @private
     */
    _createComparisonGroup(groupName, items) {
        var groupEl = document.createElement("div");
        groupEl.classList.add("ts-comparison-group");

        var headerEl = document.createElement("div");
        headerEl.classList.add("ts-comparison-group-header");
        headerEl.classList.add("ts-comparison-group-" + groupName.toLowerCase().replace(/_/g, "-"));
        headerEl.innerHTML = this._getGroupDisplayName(groupName) + " (" + items.length + ")";
        groupEl.appendChild(headerEl);

        var itemsContainer = document.createElement("div");
        itemsContainer.classList.add("ts-comparison-group-items");

        for (var i = 0; i < items.length; i++) {
            var itemEl = this._createComparisonItem(items[i]);
            itemsContainer.appendChild(itemEl);
        }

        groupEl.appendChild(itemsContainer);
        return groupEl;
    }

    /**
     * Gets the display name for a group.
     * @param {string} groupName - The internal group name.
     * @returns {string} The display name.
     * @private
     */
    _getGroupDisplayName(groupName) {
        var displayNames = {
            'NEW_FAILURE': '🔴 New Failures',
            'FIX': '🟢 Fixes',
            'NEW_TEST': '🆕 New Tests',
            'REMOVED': '🗑️ Removed Tests',
            'STATUS_CHANGE': '🔄 Status Changes'
        };
        return displayNames[groupName] || groupName;
    }

    /**
     * Creates a comparison item element.
     * @param {Object} item - The comparison item.
     * @returns {HTMLElement} The item element.
     * @private
     */
    _createComparisonItem(item) {
        var itemEl = document.createElement("div");
        itemEl.classList.add("ts-comparison-item");
        itemEl.classList.add("ts-comparison-item-" + item.changeType.toLowerCase().replace(/_/g, "-"));

        var nameEl = document.createElement("div");
        nameEl.classList.add("ts-comparison-item-name");
        nameEl.innerHTML = this._escapeHTML(item.name);
        itemEl.appendChild(nameEl);

        var statusEl = document.createElement("div");
        statusEl.classList.add("ts-comparison-item-status");

        if (item.baseline && item.current) {
            statusEl.innerHTML = '<span class="ts-comparison-status-baseline">' + item.baselineStatus + '</span>' +
                                 '<span class="ts-comparison-status-arrow">→</span>' +
                                 '<span class="ts-comparison-status-current">' + item.currentStatus + '</span>';
        } else if (item.current) {
            statusEl.innerHTML = '<span class="ts-comparison-status-current">' + item.current.status + '</span>';
        } else if (item.baseline) {
            statusEl.innerHTML = '<span class="ts-comparison-status-baseline">' + item.baseline.status + '</span>';
        }

        itemEl.appendChild(statusEl);

        return itemEl;
    }

    /**
     * Sets the active filter and updates button styling.
     * @param {string} filterValue - The filter value.
     * @private
     */
    _setActiveFilter(filterValue) {
        this._activeFilter = filterValue;

        var filterButtons = this.shadowRoot.querySelectorAll(".ts-comparison-filter-btn");
        filterButtons.forEach(function(btn) {
            var btnFilter = btn.getAttribute("data-filter");
            if (btnFilter === filterValue) {
                btn.classList.add("ts-comparison-filter-btn-active");
            } else {
                btn.classList.remove("ts-comparison-filter-btn-active");
            }
        });
    }

    /**
     * Updates the status display.
     * @param {string} message - The status message.
     * @param {string} type - The status type: 'loading', 'success', 'error'.
     * @private
     */
    _updateStatus(message, type) {
        var statusEl = this.shadowRoot.querySelector("#id-comparison-status");
        statusEl.innerHTML = message;
        statusEl.className = "ts-comparison-status ts-comparison-status-" + type;
    }

    /**
     * Clears the comparison data and resets the UI.
     * @private
     */
    _clearComparison() {
        this._baselineResults = null;
        this._comparisonData = null;
        this._activeFilter = 'ALL';

        var urlInput = this.shadowRoot.querySelector("#id-baseline-url");
        urlInput.value = "";

        var summaryEl = this.shadowRoot.querySelector("#id-comparison-summary");
        summaryEl.style.display = "none";

        var filterBar = this.shadowRoot.querySelector("#id-comparison-filter-bar");
        filterBar.style.display = "none";

        var contentEl = this.shadowRoot.querySelector("#id-comparison-content");
        contentEl.innerHTML = '<div class="ts-comparison-placeholder">Load a baseline to compare test results between runs.</div>';

        this._updateStatus("No baseline loaded", "");

        // Reset filter button states
        var filterButtons = this.shadowRoot.querySelectorAll(".ts-comparison-filter-btn");
        filterButtons.forEach(function(btn) {
            var btnFilter = btn.getAttribute("data-filter");
            if (btnFilter === "ALL") {
                btn.classList.add("ts-comparison-filter-btn-active");
            } else {
                btn.classList.remove("ts-comparison-filter-btn-active");
            }
        });
    }

    /**
     * Escapes HTML special characters.
     * @param {string} str - The string to escape.
     * @returns {string} The escaped string.
     * @private
     */
    _escapeHTML(str) {
        if (str === null || str === undefined) {
            return "";
        }
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    /**
     * Synchronizes the component with current results data.
     * @param {Object} currentResults - The current test results (processed format).
     */
    syncData(currentResults) {
        this._currentResults = currentResults;

        // If baseline is already loaded, re-perform comparison
        if (this._baselineResults) {
            this._performComparison();
        }
    }

    /**
     * Sets the current results from raw results array.
     * @param {Object} resultsDetail - Results detail object keyed by package name.
     */
    setCurrentResultsFromDetail(resultsDetail) {
        // Convert from package-grouped format to flat comparison format
        var processedResults = {};

        for (var pkgName in resultsDetail) {
            if (resultsDetail.hasOwnProperty(pkgName)) {
                var tests = resultsDetail[pkgName];
                for (var i = 0; i < tests.length; i++) {
                    var test = tests[i];
                    var fullName = pkgName + "#" + test.name;
                    processedResults[fullName] = {
                        name: fullName,
                        result: test.result,
                        start: test.start,
                        stop: test.stop,
                        detail: test.detail || {},
                        status: this._getTestStatus(test)
                    };
                }
            }
        }

        this._currentResults = processedResults;

        // If baseline is already loaded, re-perform comparison
        if (this._baselineResults) {
            this._performComparison();
        }
    }
}


/**
 * Component for displaying trend analysis across multiple test runs.
 * Shows pass rate trends, failure patterns, and test stability metrics.
 * 
 * @class TestSummaryTrendAnalysis
 * @extends HTMLElement
 */
class TestSummaryTrendAnalysis extends HTMLElement {

    static tagname = 'testsummary-trend-analysis'

    static template = `
        <div class="ts-trend-card">
            <div class="ts-section-header">
                <h2 class="zero-margins-and-padding">Trend Analysis</h2>
            </div>
            <div class="ts-trend-toolbar">
                <div class="ts-trend-load-section">
                    <label class="ts-trend-label">Historical Runs:</label>
                    <input type="text" id="id-trend-urls" class="ts-trend-input" 
                           placeholder="Enter comma-separated paths to historical test runs..." 
                           title="Enter comma-separated URLs to historical test run directories">
                    <button id="id-load-trends" class="ts-trend-btn" title="Load historical data for trend analysis">
                        Analyze Trends
                    </button>
                    <button id="id-clear-trends" class="ts-trend-btn ts-trend-btn-secondary" title="Clear trend data">
                        Clear
                    </button>
                </div>
                <div class="ts-trend-status" id="id-trend-status">
                    No historical data loaded
                </div>
            </div>
            <div class="ts-section-detail">
                <div id="id-trend-content" class="ts-trend-content">
                    <div class="ts-trend-placeholder">
                        Load historical test runs to analyze trends over time.
                    </div>
                </div>
            </div>
        </div>
    `

    constructor() {
        super();

        const shadowRoot = this.attachShadow({mode: 'open'});
        shadowRoot.innerHTML = this.getTemplate();

        addGlobalStylesToShadowRoot(shadowRoot);

        // State
        this._currentResults = null;
        this._historicalRuns = [];
        this._trendData = null;

        // Set up event listeners
        this._setupEventListeners();
    }

    /**
     * Gets the HTML template for this component.
     * @returns {string} The HTML template string.
     */
    getTemplate() {
        return TestSummaryTrendAnalysis.template;
    }

    /**
     * Sets up event listeners for the trend analysis component.
     * @private
     */
    _setupEventListeners() {
        var self = this;

        // Load trends button
        var loadBtn = this.shadowRoot.querySelector("#id-load-trends");
        loadBtn.addEventListener("click", function() {
            self._loadTrends();
        });

        // Clear trends button
        var clearBtn = this.shadowRoot.querySelector("#id-clear-trends");
        clearBtn.addEventListener("click", function() {
            self._clearTrends();
        });

        // URL input - allow Enter key to load
        var urlInput = this.shadowRoot.querySelector("#id-trend-urls");
        urlInput.addEventListener("keypress", function(event) {
            if (event.key === "Enter") {
                self._loadTrends();
            }
        });
    }

    /**
     * Loads historical test runs for trend analysis.
     * @private
     */
    async _loadTrends() {
        var urlInput = this.shadowRoot.querySelector("#id-trend-urls");
        var urlsText = urlInput.value.trim();

        if (!urlsText) {
            this._updateStatus("Please enter historical run URLs", "error");
            return;
        }

        var urls = urlsText.split(",").map(function(url) { return url.trim(); }).filter(function(url) { return url.length > 0; });

        if (urls.length === 0) {
            this._updateStatus("Please enter valid URLs", "error");
            return;
        }

        this._updateStatus("Loading historical data...", "loading");
        this._historicalRuns = [];

        var loadedCount = 0;
        var failedCount = 0;

        for (var i = 0; i < urls.length; i++) {
            try {
                var runData = await this._loadRunData(urls[i]);
                if (runData) {
                    this._historicalRuns.push(runData);
                    loadedCount++;
                } else {
                    failedCount++;
                }
            } catch (error) {
                console.error("Error loading run:", urls[i], error);
                failedCount++;
            }
        }

        if (loadedCount === 0) {
            this._updateStatus("Failed to load any historical runs", "error");
            return;
        }

        // Sort by date
        this._historicalRuns.sort(function(a, b) {
            return new Date(a.summary.start) - new Date(b.summary.start);
        });

        // Perform trend analysis
        this._analyzeTrends();

        var statusMsg = "Loaded " + loadedCount + " runs";
        if (failedCount > 0) {
            statusMsg += " (" + failedCount + " failed)";
        }
        this._updateStatus(statusMsg, "success");
    }

    /**
     * Loads data for a single test run.
     * @param {string} url - The URL to the test run directory.
     * @returns {Object|null} The run data or null if failed.
     * @private
     */
    async _loadRunData(url) {
        var summaryUrl = url;
        if (!url.endsWith("testrun_summary.json")) {
            summaryUrl = url.replace(/\/?$/, "/testrun_summary.json");
        }

        var summary = await fetch_json(summaryUrl);
        if (!summary) {
            return null;
        }

        var resultsUrl = summaryUrl.replace("testrun_summary.json", "testrun_results_stream.jsos");
        var results = await fetch_json_stream(resultsUrl);

        return {
            url: url,
            summary: summary,
            results: results || [],
            processedResults: this._processResultsForTrend(results || [])
        };
    }

    /**
     * Processes results for trend analysis.
     * @param {Array} results - Raw results array.
     * @returns {Object} Processed results map.
     * @private
     */
    _processResultsForTrend(results) {
        var processed = {};

        for (var i = 0; i < results.length; i++) {
            var result = results[i];
            if (result.rtype === "TEST" && result.stop && result.stop.length > 0) {
                var testName = result.name;
                if (result.monikers && result.monikers.length > 0) {
                    testName += ":" + result.monikers.map(function(m) { return "[" + m + "]"; }).join("");
                }
                processed[testName] = this._getTestStatus(result);
            }
        }

        return processed;
    }

    /**
     * Gets the status of a test.
     * @param {Object} test - The test object.
     * @returns {string} The test status.
     * @private
     */
    _getTestStatus(test) {
        if (test.detail) {
            if (test.detail.errors && test.detail.errors.length > 0) return 'ERRORED';
            if (test.detail.failures && test.detail.failures.length > 0) return 'FAILED';
            if (test.detail.skipped) return 'SKIPPED';
            if (test.detail.passed) return 'PASSED';
        }
        return test.result || 'UNKNOWN';
    }

    /**
     * Analyzes trends across historical runs.
     * @private
     */
    _analyzeTrends() {
        if (this._historicalRuns.length === 0) {
            return;
        }

        var trendData = {
            passRates: [],
            testStability: {},
            flakyTests: [],
            consistentFailures: [],
            recentRegressions: []
        };

        // Calculate pass rates over time
        for (var i = 0; i < this._historicalRuns.length; i++) {
            var run = this._historicalRuns[i];
            var detail = run.summary.detail || {};
            var total = detail.total || 0;
            var passed = detail.passed || 0;
            var passRate = total > 0 ? (passed / total * 100) : 0;

            trendData.passRates.push({
                date: run.summary.start,
                passRate: passRate,
                total: total,
                passed: passed,
                failed: detail.failed || 0,
                errors: detail.errors || 0,
                skipped: detail.skipped || 0
            });
        }

        // Analyze test stability
        var allTestNames = new Set();
        for (var j = 0; j < this._historicalRuns.length; j++) {
            var runResults = this._historicalRuns[j].processedResults;
            for (var testName in runResults) {
                if (runResults.hasOwnProperty(testName)) {
                    allTestNames.add(testName);
                }
            }
        }

        allTestNames.forEach(function(testName) {
            var history = [];
            for (var k = 0; k < this._historicalRuns.length; k++) {
                var runResults = this._historicalRuns[k].processedResults;
                if (runResults.hasOwnProperty(testName)) {
                    history.push(runResults[testName]);
                } else {
                    history.push('NOT_RUN');
                }
            }

            var passCount = history.filter(function(s) { return s === 'PASSED'; }).length;
            var failCount = history.filter(function(s) { return s === 'FAILED' || s === 'ERRORED'; }).length;
            var totalRuns = history.filter(function(s) { return s !== 'NOT_RUN'; }).length;

            trendData.testStability[testName] = {
                history: history,
                passCount: passCount,
                failCount: failCount,
                totalRuns: totalRuns,
                passRate: totalRuns > 0 ? (passCount / totalRuns * 100) : 0
            };

            // Identify flaky tests (passed and failed in different runs)
            if (passCount > 0 && failCount > 0) {
                trendData.flakyTests.push({
                    name: testName,
                    passRate: (passCount / totalRuns * 100).toFixed(1),
                    history: history
                });
            }

            // Identify consistent failures (always failed)
            if (passCount === 0 && failCount > 0 && failCount === totalRuns) {
                trendData.consistentFailures.push({
                    name: testName,
                    failCount: failCount
                });
            }
        }.bind(this));

        // Sort flaky tests by pass rate (most unstable first)
        trendData.flakyTests.sort(function(a, b) {
            return Math.abs(50 - parseFloat(a.passRate)) - Math.abs(50 - parseFloat(b.passRate));
        });

        this._trendData = trendData;
        this._renderTrends();
    }

    /**
     * Renders the trend analysis results.
     * @private
     */
    _renderTrends() {
        var contentEl = this.shadowRoot.querySelector("#id-trend-content");
        contentEl.innerHTML = "";

        if (!this._trendData) {
            contentEl.innerHTML = '<div class="ts-trend-placeholder">Load historical test runs to analyze trends over time.</div>';
            return;
        }

        // Pass rate chart
        var chartSection = this._createPassRateChart();
        contentEl.appendChild(chartSection);

        // Flaky tests section
        if (this._trendData.flakyTests.length > 0) {
            var flakySection = this._createFlakyTestsSection();
            contentEl.appendChild(flakySection);
        }

        // Consistent failures section
        if (this._trendData.consistentFailures.length > 0) {
            var failuresSection = this._createConsistentFailuresSection();
            contentEl.appendChild(failuresSection);
        }
    }

    /**
     * Creates the pass rate chart section.
     * @returns {HTMLElement} The chart section element.
     * @private
     */
    _createPassRateChart() {
        var section = document.createElement("div");
        section.classList.add("ts-trend-section");

        var header = document.createElement("h3");
        header.classList.add("ts-trend-section-header");
        header.innerHTML = "📈 Pass Rate Over Time";
        section.appendChild(header);

        var chartContainer = document.createElement("div");
        chartContainer.classList.add("ts-trend-chart-container");

        // Create a simple text-based chart
        var table = document.createElement("table");
        table.classList.add("ts-trend-table");

        var thead = document.createElement("thead");
        thead.innerHTML = "<tr><th>Date</th><th>Pass Rate</th><th>Passed</th><th>Failed</th><th>Errors</th><th>Total</th><th>Trend</th></tr>";
        table.appendChild(thead);

        var tbody = document.createElement("tbody");
        for (var i = 0; i < this._trendData.passRates.length; i++) {
            var data = this._trendData.passRates[i];
            var row = document.createElement("tr");

            var dateStr = new Date(data.date).toLocaleDateString();
            var passRateStr = data.passRate.toFixed(1) + "%";
            
            // Create visual bar
            var barWidth = Math.min(100, data.passRate);
            var barColor = data.passRate >= 90 ? "var(--color-pass)" : 
                          data.passRate >= 70 ? "orange" : "var(--color-fail)";
            var barHtml = '<div class="ts-trend-bar" style="width: ' + barWidth + '%; background-color: ' + barColor + ';"></div>';

            row.innerHTML = '<td>' + dateStr + '</td>' +
                           '<td>' + passRateStr + '</td>' +
                           '<td class="color-pass">' + data.passed + '</td>' +
                           '<td class="color-fail">' + data.failed + '</td>' +
                           '<td class="color-error">' + data.errors + '</td>' +
                           '<td>' + data.total + '</td>' +
                           '<td class="ts-trend-bar-cell">' + barHtml + '</td>';
            tbody.appendChild(row);
        }
        table.appendChild(tbody);

        chartContainer.appendChild(table);
        section.appendChild(chartContainer);

        return section;
    }

    /**
     * Creates the flaky tests section.
     * @returns {HTMLElement} The flaky tests section element.
     * @private
     */
    _createFlakyTestsSection() {
        var section = document.createElement("div");
        section.classList.add("ts-trend-section");

        var header = document.createElement("h3");
        header.classList.add("ts-trend-section-header");
        header.innerHTML = "⚠️ Flaky Tests (" + this._trendData.flakyTests.length + ")";
        section.appendChild(header);

        var description = document.createElement("p");
        description.classList.add("ts-trend-description");
        description.innerHTML = "Tests that have both passed and failed across different runs:";
        section.appendChild(description);

        var list = document.createElement("div");
        list.classList.add("ts-trend-list");

        var maxToShow = Math.min(10, this._trendData.flakyTests.length);
        for (var i = 0; i < maxToShow; i++) {
            var test = this._trendData.flakyTests[i];
            var item = document.createElement("div");
            item.classList.add("ts-trend-list-item");
            item.classList.add("ts-trend-flaky-item");

            var historyHtml = test.history.map(function(status) {
                var color = status === 'PASSED' ? 'var(--color-pass)' : 
                           status === 'FAILED' || status === 'ERRORED' ? 'var(--color-fail)' :
                           status === 'SKIPPED' ? 'var(--color-skip)' : '#ccc';
                return '<span class="ts-trend-history-dot" style="background-color: ' + color + ';" title="' + status + '"></span>';
            }).join("");

            item.innerHTML = '<div class="ts-trend-item-name">' + this._escapeHTML(test.name) + '</div>' +
                            '<div class="ts-trend-item-rate">' + test.passRate + '% pass rate</div>' +
                            '<div class="ts-trend-item-history">' + historyHtml + '</div>';
            list.appendChild(item);
        }

        if (this._trendData.flakyTests.length > maxToShow) {
            var more = document.createElement("div");
            more.classList.add("ts-trend-more");
            more.innerHTML = "... and " + (this._trendData.flakyTests.length - maxToShow) + " more flaky tests";
            list.appendChild(more);
        }

        section.appendChild(list);
        return section;
    }

    /**
     * Creates the consistent failures section.
     * @returns {HTMLElement} The consistent failures section element.
     * @private
     */
    _createConsistentFailuresSection() {
        var section = document.createElement("div");
        section.classList.add("ts-trend-section");

        var header = document.createElement("h3");
        header.classList.add("ts-trend-section-header");
        header.innerHTML = "🔴 Consistent Failures (" + this._trendData.consistentFailures.length + ")";
        section.appendChild(header);

        var description = document.createElement("p");
        description.classList.add("ts-trend-description");
        description.innerHTML = "Tests that have failed in every run:";
        section.appendChild(description);

        var list = document.createElement("div");
        list.classList.add("ts-trend-list");

        var maxToShow = Math.min(10, this._trendData.consistentFailures.length);
        for (var i = 0; i < maxToShow; i++) {
            var test = this._trendData.consistentFailures[i];
            var item = document.createElement("div");
            item.classList.add("ts-trend-list-item");
            item.classList.add("ts-trend-failure-item");
            item.innerHTML = '<div class="ts-trend-item-name">' + this._escapeHTML(test.name) + '</div>' +
                            '<div class="ts-trend-item-count">Failed in ' + test.failCount + ' runs</div>';
            list.appendChild(item);
        }

        if (this._trendData.consistentFailures.length > maxToShow) {
            var more = document.createElement("div");
            more.classList.add("ts-trend-more");
            more.innerHTML = "... and " + (this._trendData.consistentFailures.length - maxToShow) + " more consistent failures";
            list.appendChild(more);
        }

        section.appendChild(list);
        return section;
    }

    /**
     * Updates the status display.
     * @param {string} message - The status message.
     * @param {string} type - The status type.
     * @private
     */
    _updateStatus(message, type) {
        var statusEl = this.shadowRoot.querySelector("#id-trend-status");
        statusEl.innerHTML = message;
        statusEl.className = "ts-trend-status ts-trend-status-" + type;
    }

    /**
     * Clears the trend data and resets the UI.
     * @private
     */
    _clearTrends() {
        this._historicalRuns = [];
        this._trendData = null;

        var urlInput = this.shadowRoot.querySelector("#id-trend-urls");
        urlInput.value = "";

        var contentEl = this.shadowRoot.querySelector("#id-trend-content");
        contentEl.innerHTML = '<div class="ts-trend-placeholder">Load historical test runs to analyze trends over time.</div>';

        this._updateStatus("No historical data loaded", "");
    }

    /**
     * Escapes HTML special characters.
     * @param {string} str - The string to escape.
     * @returns {string} The escaped string.
     * @private
     */
    _escapeHTML(str) {
        if (str === null || str === undefined) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    /**
     * Synchronizes the component with current results.
     * @param {Object} currentResults - The current test results.
     */
    syncData(currentResults) {
        this._currentResults = currentResults;
    }
}


/**
 * Registers comparison components with customElements.
 * Should be called once during page initialization.
 */
function register_comparison_components() {
    if (comparisonComponentsRegistered) {
        return;
    }

    customElements.define(TestSummaryResultComparison.tagname, TestSummaryResultComparison);
    customElements.define(TestSummaryTrendAnalysis.tagname, TestSummaryTrendAnalysis);

    comparisonComponentsRegistered = true;
}
