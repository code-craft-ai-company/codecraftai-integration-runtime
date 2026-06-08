/*
    Author: "Myron Walker"
    Copyright: "Copyright 2024, Myron W Walker"
    Version: = "2.0.0"
    Email: myron.walker@gmail.com
*/

/**
 * @fileoverview TestSummary web components for displaying test execution results.
 * Provides specialized components for banners, configurations, results, artifacts,
 * and error displays in the test summary report.
 * @module testsummary-components
 */

/**
 * Banner component displaying test run summary information.
 * Shows automation pod name, build info, timestamps, result status, and metrics.
 * 
 * @class TestSummaryBanner
 * @extends HTMLElement
 * 
 * @example
 * const banner = document.getElementById('testsummary-banner');
 * banner.syncData(summaryData);
 */
class TestSummaryBanner extends HTMLElement {

    static tagname = 'testsummary-banner'

    static template = `
        <div class='ts-banner'>
            <div class='ts-banner-job'>
                <div class='ts-banner-logo'>
                </div>
                <div class="ts-banner-content">
                    <div style="flex-grow: 1;"></div>
                    <div class="ts-banner-column">
                        <div class="ts-banner-row">
                            <div class="ts-banner-prop-pair">
                                <div class="ts-banner-prop-label">Automation Pod:</div>
                                <div class="ts-banner-prop-value" id="id-summary-banner-apod">(not set)</div>
                            </div>
                        </div>
                    </div>
                    <div class="ts-banner-column">
                        <div class="ts-banner-row">
                            <div class="ts-banner-prop-pair">
                                <div class="ts-banner-prop-label">Branch:</div>
                                <div class="ts-banner-prop-value" id="id-summary-banner-branch">(not set)</div>
                            </div>
                        </div>
                        <br>   
                        <div class="ts-banner-row">
                            <div class="ts-banner-prop-pair" style="flex-basis: 1;">
                                <div class="ts-banner-prop-label">Start:</div>
                                <div class="ts-banner-prop-value" id="id-summary-banner-start">(not set)</div>
                            </div>
                        </div>
                    </div>
                    <div class="ts-banner-column">
                        <div class="ts-banner-row">
                            <div class="ts-banner-prop-pair">
                                <div class="ts-banner-prop-label">Build:</div>
                                <div class="ts-banner-prop-value" id="id-summary-banner-build">(not set)</div>
                            </div>
                        </div>
                        <br>
                        <div class="ts-banner-row">
                            <div class="ts-banner-prop-pair">
                                <div class="ts-banner-prop-label">Stop:</div>
                                <div class="ts-banner-prop-value" id="id-summary-banner-stop">(not set)</div>
                            </div>
                        </div>
                    </div>
                    <div class="ts-banner-column">
                        <div class="ts-banner-row">
                            <div class="ts-banner-prop-pair">
                                <div class="ts-banner-prop-label">Flavor:</div>
                                <div class="ts-banner-prop-value" id="id-summary-banner-flavor">(not set)</div>
                            </div>
                        </div>
                        <br>
                        <div class="ts-banner-row">
                            <div class="ts-banner-prop-pair">
                                <div class="ts-banner-prop-label">Status:</div>
                                <div class="ts-banner-prop-value" id="id-summary-banner-status">(not set)</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="ts-banner-metrics" >
                <div style="flex-grow: 1;"></div>
                <div class="ts-banner-metrics-panel">
                    <div class="ts-banner-metrics-column">
                        <div class="ts-banner-metrics-value-pair">
                            <div class="ts-banner-metrics-label">Errors:</div>
                            <div class="color-error ts-banner-metrics-value" id="id-summary-metrics-error">NaN</div>
                        </div>
                    </div>
                    <div class="ts-banner-metrics-column">
                        <div class="ts-banner-metrics-value-pair">
                            <div class="ts-banner-metrics-label">Failed:</div>
                            <div class="color-fail ts-banner-metrics-value" id="id-summary-metrics-fail">NaN</div>
                        </div>
                    </div>
                    <div class="ts-banner-metrics-column">
                        <div class="ts-banner-metrics-value-pair">
                            <div class="ts-banner-metrics-label">Skipped:</div>
                            <div class="color-skip ts-banner-metrics-value" id="id-summary-metrics-skip">NaN</div>
                        </div>
                    </div>
                    <div class="ts-banner-metrics-column">
                        <div class="ts-banner-metrics-value-pair">
                            <div class="ts-banner-metrics-label">Passed:</div>
                            <div class="color-pass ts-banner-metrics-value" id="id-summary-metrics-pass">NaN</div>
                        </div>
                    </div>
                    <div class="ts-banner-metrics-column">
                        <div class="ts-banner-metrics-value-pair">
                            <div class="ts-banner-metrics-label">Total:</div>
                            <div class="ts-banner-metrics-value" id="id-summary-metrics-total">NaN</div>
                        </div>
                        <div class="ts-banner-metrics-value-pair">
                            <div class="ts-banner-metrics-label">Score:</div>
                            <div class="ts-banner-metrics-value" id="id-summary-metrics-score">NaN</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `

    constructor() {
        super();

        const shadowRoot = this.attachShadow({ mode: 'open' });
        shadowRoot.innerHTML = this.getTemplate();

        addGlobalStylesToShadowRoot(shadowRoot);

        this.summary = {};
    }

    /**
     * Gets the HTML template for this component.
     * @returns {string} The HTML template string.
     */
    getTemplate() {
        return TestSummaryBanner.template;
    }

    /**
     * Synchronizes the component with summary data.
     * Updates banner display with automation pod, build info, timestamps, and metrics.
     * 
     * @param {Object} summary - The test run summary object.
     * @param {string} [summary.apod] - Automation pod name.
     * @param {string} [summary.start] - Test run start timestamp.
     * @param {string} [summary.stop] - Test run stop timestamp.
     * @param {Object} [summary.build] - Build information object.
     * @param {string} [summary.build.branch] - Branch name.
     * @param {string} [summary.build.build] - Build number.
     * @param {string} [summary.build.flavor] - Build flavor.
     * @param {string} [summary.result] - Overall result status.
     * @param {Object} [summary.detail] - Detailed metrics object.
     * @param {number} [summary.detail.errors] - Error count.
     * @param {number} [summary.detail.failed] - Failed count.
     * @param {number} [summary.detail.skipped] - Skipped count.
     * @param {number} [summary.detail.passed] - Passed count.
     * @param {number} [summary.detail.total] - Total count.
     */
    syncData(summary) {
        this.summary = summary;

        var result = null;

        if ("apod" in this.summary) {
            this.shadowRoot.querySelector("#id-summary-banner-apod").innerHTML = this.summary["apod"];
        }

        if ("start" in this.summary) {
            this.shadowRoot.querySelector("#id-summary-banner-start").innerHTML = this.summary["start"];
        }

        if ("stop" in this.summary) {
            this.shadowRoot.querySelector("#id-summary-banner-stop").innerHTML = this.summary["stop"];
        }

        if ("build" in this.summary) {
            var buildInfo = this.summary["build"];

            this.shadowRoot.querySelector("#id-summary-banner-branch").innerHTML = buildInfo["branch"];
            this.shadowRoot.querySelector("#id-summary-banner-build").innerHTML = buildInfo["build"];
            this.shadowRoot.querySelector("#id-summary-banner-flavor").innerHTML = buildInfo["flavor"];
            this.shadowRoot.querySelector("#id-summary-banner-flavor").innerHTML = buildInfo["flavor"];
        }

        if ("result" in this.summary) {
            result = this.summary["result"];

            this.shadowRoot.querySelector("#id-summary-banner-status").innerHTML = result;
        }

        if ("detail" in this.summary) {
            var detailInfo = this.summary["detail"];

            var errors = detailInfo["errors"];
            var failed = detailInfo["failed"];
            var skipped = detailInfo["skipped"];
            var passed = detailInfo["passed"];
            var total = detailInfo["total"];

            this.shadowRoot.querySelector("#id-summary-metrics-error").innerHTML = errors;
            this.shadowRoot.querySelector("#id-summary-metrics-fail").innerHTML = failed;
            this.shadowRoot.querySelector("#id-summary-metrics-skip").innerHTML = skipped;
            this.shadowRoot.querySelector("#id-summary-metrics-pass").innerHTML = passed;
            this.shadowRoot.querySelector("#id-summary-metrics-total").innerHTML = total;

            if ((result != null) && (total > 0)) {
                if ((total - skipped) > 0) {
                    var score = (passed / (total - skipped)) * 100;
                    var scoreFormat = score.toFixed(2);

                    this.shadowRoot.querySelector("#id-summary-metrics-score").innerHTML = scoreFormat;
                } else {
                    this.shadowRoot.querySelector("#id-summary-metrics-score").innerHTML = "NaN";
                }
            }
        }

    }
}


/**
 * Base component for displaying landscape configuration objects.
 * Provides common functionality for rendering device, service, and data profile properties.
 * 
 * @class TestSummaryLandscapeObject
 * @extends HTMLElement
 */
class TestSummaryLandscapeObject extends HTMLElement {

    static tagname = 'testsummary-landscapeobject'

    static template = `
        <div id='id-lscape-object-container' class='ts-lscape-object-item'>
        </div>
    `

    sel_container = "#id-lscape-object-container"

    property_order = ['name']
    property_label_lookup = { 'name': 'Name' }

    constructor() {
        super();

        const shadowRoot = this.attachShadow({ mode: 'open' });
        shadowRoot.innerHTML = this.getTemplate();

        addGlobalStylesToShadowRoot(shadowRoot);

        this.lscapeItem = undefined;
    }

    /**
     * Creates a property pair element with label and value.
     * @param {string} label - The property label/key.
     * @param {*} value - The property value.
     * @returns {Array} A two-element array [labelEl, valueEl].
     */
    createPropertyPairElement(label, value) {
        var propLabel = this.getPropertyLabel(label);

        var labelEl = document.createElement('div');
        labelEl.innerHTML = propLabel + ":";
        labelEl.classList.add("ts-lscape-item-prop-lbl");

        var valueEl = document.createElement('div');
        valueEl.classList.add("ts-lscape-item-prop-val");
        valueEl.innerHTML = this.formatProperty(value);

        return [labelEl, valueEl];
    }

    /**
     * Formats a property value for display.
     * Handles strings, arrays, and objects with appropriate HTML formatting.
     * @param {*} propVal - The property value to format.
     * @returns {string} HTML string representation of the value.
     */
    formatProperty(propVal) {
        var formattedHtml = "";

        if (typeof propVal === 'string') {
            formattedHtml = propVal;
        } else if (Array.isArray(propVal)) {
            formattedHtml = "<div class='ts-lscape-item-value-list'>";
            for (var val of propVal) {
                formattedHtml += "<span>" + val + "</span>"
            }
            formattedHtml += "</div>"
        } else if (Object.keys(propVal).length > 0) {
            formattedHtml = "<div class='ts-lscape-item-value-list'>";
            for (var key of Object.keys(propVal)) {
                var val = propVal[key];
                formattedHtml += "<div class='ts-lscape-item-value-row-pair'><div class='ts-lscape-item-value-row-lbl'>" + key +
                    ":</div><div class='ts-lscape-item-value-row-val'>" + val + "</div></div>";
            }
            formattedHtml += "</div>";
        } else {
            formattedHtml = propVal;
        }

        return formattedHtml;
    }

    /**
     * Gets the display label for a property key.
     * @param {string} propKey - The property key.
     * @returns {string} The display label.
     */
    getPropertyLabel(propKey) {
        var label = "";

        var propLabelLookup = this.getPropertyLabelLookup();

        if (propLabelLookup.hasOwnProperty(propKey)) {
            label = propLabelLookup[propKey];
        } else {
            label = propKey.substring(0, 1).toUpperCase(); + propKey.substring(1);
        }

        return label;
    }

    /**
     * Gets the property label lookup table.
     * @returns {Object} Object mapping property keys to display labels.
     */
    getPropertyLabelLookup() {
        return this.property_label_lookup
    }

    /**
     * Gets the preferred property display order.
     * @returns {string[]} Array of property keys in preferred order.
     */
    getPropertyOrder() {
        return this.property_order;
    }

    /**
     * Gets the HTML template for this component.
     * @returns {string} The HTML template string.
     */
    getTemplate() {
        return TestSummaryLandscapeObject.template;
    }

    /**
     * Synchronizes the component with landscape item data.
     * @param {Object} lscapeItem - The landscape item object to display.
     */
    syncData(lscapeItem) {

        this.lscapeItem = lscapeItem;

        var containerEl = this.shadowRoot.querySelector(this.sel_container);

        var propKeys = Object.keys(lscapeItem);
        var prefPropOrder = this.getPropertyOrder();

        for (const prefProp of prefPropOrder) {
            if (lscapeItem.hasOwnProperty(prefProp)) {
                propKeys = propKeys.filter(function (item) {
                    var matches = item == prefProp;
                    return matches;
                });

                const propVal = lscapeItem[prefProp];

                const [labelEl, valueEl] = this.createPropertyPairElement(prefProp, propVal);
                containerEl.appendChild(labelEl);
                containerEl.appendChild(valueEl);
            }
        }

        for (const propName of propKeys) {
            if (lscapeItem.hasOwnProperty(propName)) {
                const propVal = lscapeItem[propName];

                const [labelEl, valueEl] = this.createPropertyPairElement(propName, propVal);
                containerEl.appendChild(labelEl);
                containerEl.appendChild(valueEl);
            }
        }

    }

}


/**
 * Component for displaying data profile configuration objects.
 * @class TestSummaryDataProfileObject
 * @extends TestSummaryLandscapeObject
 */
class TestSummaryDataProfileObject extends TestSummaryLandscapeObject {

    static tagname = 'testsummary-dataprofileobject'

    property_order = ['name', 'profileType', 'host', 'credentials']

    property_label_lookup = {
        'name': 'Name',
        'profileType': 'ProfileType',
        'host': 'Host',
        'credentials': 'Credentials'
    }

    constructor() {
        super();
    }

    getPropertyLabelLookup() {
        return this.property_label_lookup
    }

    getPropertyOrder() {
        return this.property_order;
    }

}


/**
 * Component for displaying device configuration objects.
 * Shows device properties like name, type, host, role, credentials, and features.
 * @class TestSummaryDeviceObject
 * @extends TestSummaryLandscapeObject
 */
class TestSummaryDeviceObject extends TestSummaryLandscapeObject {

    static tagname = 'testsummary-deviceobject'

    property_order = ['name', 'deviceType', 'host', 'role', 'credentials', 'features', 'skip']

    property_label_lookup = {
        'name': 'Name',
        'deviceType': 'DeviceType',
        'host': 'Host',
        'role': 'Role',
        'credentials': 'Credentials',
        'features': 'Features',
        'skip': 'Skip'
    }

    constructor() {
        super();
    }

    getPropertyLabelLookup() {
        return this.property_label_lookup
    }

    getPropertyOrder() {
        return this.property_order;
    }
}


/**
 * Component for displaying a group of devices.
 * Shows the group name and contains device object components.
 * @class TestSummaryDeviceGroup
 * @extends HTMLElement
 */
class TestSummaryDeviceGroup extends HTMLElement {

    static tagname = 'testsummary-devicegroup'

    static template = `
        <div id="id-device-group-container" class="ts-lscape-device-group">
            <div id="id-device-group-name" class="ts-lscape-device-group-name">
            </div>
            <div id="id-device-group-items" class="ts-lscape-device-group-items">
            </div>
        </div>
    `

    sel_container = "#id-device-group-container"
    sel_group_name = "#id-device-group-name"
    sel_group_items = "#id-device-group-items"

    constructor() {
        super();

        const shadowRoot = this.attachShadow({ mode: 'open' });
        shadowRoot.innerHTML = this.getTemplate();

        addGlobalStylesToShadowRoot(shadowRoot);

        this.name = undefined;
        this.devices = undefined;
    }

    /**
     * Gets the HTML template for this component.
     * @returns {string} The HTML template string.
     */
    getTemplate() {
        return TestSummaryDeviceGroup.template;
    }

    /**
     * Synchronizes the component with device group data.
     * @param {string} group_name - The name of the device group.
     * @param {Object[]} group_devices - Array of device objects in the group.
     */
    syncData(group_name, group_devices) {

        var groupNameEl = this.shadowRoot.querySelector(this.sel_group_name);
        var groupItemsEl = this.shadowRoot.querySelector(this.sel_group_items);

        this.group_name = name;
        this.group_devices = group_devices;

        groupNameEl.innerHTML = group_name;

        for (var device of group_devices) {
            var deviceEl = document.createElement(TestSummaryDeviceObject.tagname);
            deviceEl.syncData(device);

            groupItemsEl.appendChild(deviceEl);
        }

    }
}

/**
 * Component for displaying service configuration objects.
 * Shows service properties like name, type, host, and credentials.
 * @class TestSummaryServiceObject
 * @extends TestSummaryLandscapeObject
 */
class TestSummaryServiceObject extends TestSummaryLandscapeObject {

    static tagname = 'testsummary-serviceobject'

    property_order = ['name', 'serviceType', 'host', 'credentials']

    property_label_lookup = {
        'name': 'Name',
        'serviceType': 'ServiceType',
        'host': 'Host',
        'credentials': 'Credentials'
    }

    constructor() {
        super();
    }

    getPropertyLabelLookup() {
        return this.property_label_lookup
    }

    getPropertyOrder() {
        return this.property_order;
    }

}


/**
 * Component for displaying test configuration information.
 * Shows command, environment variables, packages, and landscape configuration.
 * @class TestSummaryConfiguration
 * @extends HTMLElement
 */
class TestSummaryConfiguration extends HTMLElement {

    static tagname = 'testsummary-configuration'

    static template = `
        <div class="ts-configuration-card">
            <div class="ts-section-header">
                <h2 class="zero-margins-and-padding">Configuration</h2>
            </div>
            <div class="ts-section-detail">
                <div id="id-ts-configuration-content" class="ts_vertical_tiling_panel">
                    <mojo-property-single id="id-ts-configuration-command">
                    </mojo-property-single>
                    <mojo-collapsible id="id-ts-configuration-environment">
                    </mojo-collapsible>
                    <mojo-collapsible id="id-ts-configuration-packages">
                    </mojo-collapsible>
                    <testsummary-config-landscape id="id-ts-configuration-landscape">
                    </testsummary-config-landscape>
                </div>
            </div>  
        </div>
    `

    constructor() {
        super();

        const shadowRoot = this.attachShadow({ mode: 'open' });
        shadowRoot.innerHTML = this.getTemplate();

        addGlobalStylesToShadowRoot(shadowRoot);

        this.landscape = undefined;
        this.command = undefined;
        this.environment = undefined;
        this.packages = undefined;
    }

    /**
     * Gets the HTML template for this component.
     * @returns {string} The HTML template string.
     */
    getTemplate() {
        return TestSummaryConfiguration.template;
    }

    /**
     * Synchronizes the component with startup and landscape configuration data.
     * @param {Object} startup - The startup configuration object.
     * @param {string} [startup.command] - The command used to run tests.
     * @param {Object} [startup.environment] - Environment variables.
     * @param {Object} [startup.packages] - Installed packages.
     * @param {Object} landscape - The landscape configuration object.
     */
    syncData(startup, landscape) {

        this.landscape = landscape;

        if (startup != null) {
            if ("command" in startup) {
                this.command = startup.command;
            }

            if ("environment" in startup) {
                this.environment = startup.environment;
            }

            if ("packages" in startup) {
                this.packages = startup.packages;
            }
        }

        var contentEl = this.shadowRoot.querySelector("#id-ts-configuration-content");

        if (this.command != undefined) {
            var commandEl = this.shadowRoot.querySelector("#id-ts-configuration-command");

            commandEl.syncData("Command", this.command);
        }

        var environmentEl = this.shadowRoot.querySelector("#id-ts-configuration-environment");
        if (this.environment != undefined) {

            var tableEl = document.createElement(MojoPropertyTable.tagname);
            tableEl.syncData(this.environment);

            environmentEl.syncData("Environment", tableEl);

        } else {
            environmentEl.style.display = "none";
        }

        var packagesEl = this.shadowRoot.querySelector("#id-ts-configuration-packages");
        if (this.packages != undefined) {

            var tableEl = document.createElement(MojoPropertyTable.tagname);
            tableEl.syncData(this.packages);

            packagesEl.syncData("Packages", tableEl);

        } else {
            packagesEl.style.display = "none";
        }

        var landscapeEl = this.shadowRoot.querySelector("#id-ts-configuration-landscape");
        if (this.landscape != undefined) {

            landscapeEl.syncData("Landscape", this.landscape);

        } else {
            landscapeEl.style.display = "none";
        }

    }

}

class TestSummaryConfigurationEnvironment extends MojoCollapsible {

    static tagname = 'testsummary-config-environment'

    static template = `
        <div id="id-collapsible-container" class="mojo-collapsible" >
            <div id="id-collapsible-button" class="mojo-collapsible-button">
                <div id="id-header-text" class="mojo-collapsible-header"></div>
                <div id="id-header-icon" class="mojo-collapsible-icon">+</div>
            </div>
            <div id="id-collapsible-content" class="ts-collapsible-content">
                <property-table id="id-ts-configuration-environment"></property-table>
            </div>
        </div>
    `

    constructor() {
        super();
    }

    getTemplate() {
        return TestSummaryConfigurationEnvironment.template;
    }

    syncData(environment) {
        this.environment = environment;

        var tableEl = this.shadowRoot.querySelector("#id-ts-configuration-environment")
        tableEl.syncData(environment);

        super.syncData("Environment", undefined, false);
    }

}


class TestSummaryConfigurationLandscape extends MojoCollapsible {

    static tagname = 'testsummary-config-landscape'

    static template = `
        <div id="id-collapsible-container" class="mojo-collapsible" >
            <div id="id-collapsible-button" class="mojo-collapsible-button">
                <div id="id-header-text" class="mojo-collapsible-header"></div>
                <div id="id-header-icon" class="mojo-collapsible-icon">+</div>
            </div>
            <div id="id-collapsible-content" class="ts-lscape-collapsable-content">
                <mojo-collapsible-lvl2 id="id-ts-configuration-landscape-dataprofiles">
                </mojo-collapsible-lvl2>
                <div style="height: 8px;"></div>
                <mojo-collapsible-lvl2 id="id-ts-configuration-landscape-device-groups">
                </mojo-collapsible-lvl2>
                <div style="height: 8px;"></div>
                <mojo-collapsible-lvl2 id="id-ts-configuration-landscape-services">
                </mojo-collapsible-lvl2>
                <div style="height: 4px;"></div>
            </div>
        </div>
    `

    constructor() {
        super();
    }

    getTemplate() {
        return TestSummaryConfigurationLandscape.template;
    }

    syncData(header, landscape) {

        this.landscape = landscape;

        var deviceGroupsEl = this.shadowRoot.querySelector("#id-ts-configuration-landscape-device-groups");

        if ((landscape.apod != undefined) && (Object.keys(landscape.apod).length > 0)) {

            deviceGroupsEl.style.display = "";

            var deviceGroupListEl = document.createElement("div");
            deviceGroupListEl.classList.add("ts-lscape-device-groups-list");

            var apod = landscape.apod

            // If we have device groups in the automation pod, then 

            for (var device_group of Object.keys(apod)) {

                console.debug("Processing device group (" + device_group + ")");

                var group_devices = apod[device_group];

                var nextDeviceGroupEl = document.createElement(TestSummaryDeviceGroup.tagname);
                nextDeviceGroupEl.syncData(device_group, group_devices);

                deviceGroupListEl.appendChild(nextDeviceGroupEl)
            }

            deviceGroupsEl.syncData("Device Groups", deviceGroupListEl, true);

        } else {
            deviceGroupsEl.style.display = "none";
        }

        var landscapeDataProfilesEl = this.shadowRoot.querySelector("#id-ts-configuration-landscape-dataprofiles");
        if ((landscape.dataprofiles != undefined) && (landscape.dataprofiles.length > 0)) {
            landscapeDataProfilesEl.style.display = "";

            var landscapeDataProfilesListEl = document.createElement("div");
            landscapeDataProfilesListEl.classList.add("ts-lscape-dataprofiles-list");

            // TODO: Add support for displaying data profiles

            landscapeDataProfilesEl.syncData("Data Profiles", landscapeDataProfilesListEl, true);

        } else {

            landscapeDataProfilesEl.style.display = "none";
        }

        if (landscape.environment != undefined) {
            var lscape_env = landscape.environment;

            if (lscape_env.label != undefined) {
                var env_label = lscape_env.label;

                // TODO: Update the environment declared in the landscape file
            }

        }

        var landscapeServiceEl = this.shadowRoot.querySelector("#id-ts-configuration-landscape-services");

        if (landscape.infrastructure != undefined) {

            var infrastructure = landscape.infrastructure;

            if ((infrastructure.services != undefined) && (infrastructure.services.length > 0)) {
                // TODO: Add support for displaying infrastructure details
                landscapeServiceEl.style.display = '';

                var landscapeServicesListEl = document.createElement("div");
                landscapeServicesListEl.classList.add("ts-lscape-services-list");

                for (const serviceInfo of infrastructure.services) {
                    var serviceEl = document.createElement(TestSummaryServiceObject.tagname);
                    serviceEl.syncData(serviceInfo)

                    landscapeServicesListEl.appendChild(serviceEl);
                }

                landscapeServiceEl.syncData("Services", landscapeServicesListEl, true);


            } else {
                landscapeServiceEl.style.display = 'none';
            }

        } else {
            landscapeServiceEl.style.display = 'none';
        }

        super.syncData(header, undefined, false);

    }

}


class TestSummaryConfigurationPackages extends MojoCollapsible {

    static tagname = 'testsummary-config-packages'

    static template = `
        <div id="id-collapsible-container" class="mojo-collapsible" >
            <div id="id-collapsible-button" class="mojo-collapsible-button">
                <div id="id-header-text" class="mojo-collapsible-header"></div>
                <div id="id-header-icon" class="mojo-collapsible-icon">+</div>
            </div>
            <div id="id-collapsible-content" class="ts-collapsible-content">
                <property-table id="id-ts-configuration-packages"></property-table>
            </div>
        </div>
    `

    constructor() {
        super();
    }

    getTemplate() {
        return TestSummaryConfigurationPackages.template;
    }

    syncData(packages) {
        this.packages = packages;

        var tableEl = this.shadowRoot.querySelector("#id-ts-configuration-packages")
        tableEl.syncData(packages);

        super.syncData("Packages", undefined, false);
    }

}



class TestSummaryResultGroup extends HTMLElement {

    static tagname = 'testsummary-resultgroup'

    static template = `
        <details>
            <summary id="id-rgroup-summary">
                <div class="ts-results-grp-grid">
                    <span id="id-rgs-name" class="ts-results-grp-name"></span>
                    <span id="id-rgs-error" class="ts-results-grp-score"></span>
                    <span id="id-rgs-failure" class="ts-results-grp-score"></span>
                    <span id="id-rgs-skip" class="ts-results-grp-score"></span>
                    <span id="id-rgs-pass" class="ts-results-grp-score"></span>
                </div>
            </summary>
            <div id="id-resultgroup-detail" style="margin-left: 20px;">
            </div>
        </details>
    `

    constructor() {
        super();

        const shadowRoot = this.attachShadow({ mode: 'open' })
        shadowRoot.innerHTML = this.getTemplate();

        addGlobalStylesToShadowRoot(shadowRoot);
    }

    getTemplate() {
        return TestSummaryResultGroup.template;
    }

    syncData(groupName, groupInfo) {

        var grpDetailEl = this.shadowRoot.querySelector("#id-resultgroup-detail");

        var grpNameEl = this.shadowRoot.querySelector("#id-rgs-name");
        grpNameEl.innerHTML = groupName;

        var errored = 0;
        var failed = 0;
        var skipped = 0;
        var passed = 0;

        for (const testItem of groupInfo) {

            if (testItem.hasOwnProperty("detail")) {
                var itemResult = testItem.result;

                if (itemResult == "PASSED") {
                    passed += 1;
                } else if (itemResult == "FAILED") {
                    failed += 1;
                } else if (itemResult == "ERRORED") {
                    errored += 1;
                } else if (itemResult == "SKIPPED") {
                    skipped += 1;
                }

                var resultItemEl = document.createElement("testsummary-resultitem");
                resultItemEl.syncData(testItem);

                grpDetailEl.appendChild(resultItemEl);
            }

        }

        var grpErrorEl = this.shadowRoot.querySelector("#id-rgs-error");
        if (errored > 0) {
            grpErrorEl.classList.add("color-error");
        } else {
            grpErrorEl.classList.add("color-ghost");
        }
        grpErrorEl.innerHTML = errored.toString();

        var grpFailEl = this.shadowRoot.querySelector("#id-rgs-failure");
        if (failed > 0) {
            grpFailEl.classList.add("color-fail");
        } else {
            grpFailEl.classList.add("color-ghost");
        }
        grpFailEl.innerHTML = failed.toString();

        var grpSkipEl = this.shadowRoot.querySelector("#id-rgs-skip");
        if (skipped > 0) {
            grpSkipEl.classList.add("color-skip");
        } else {
            grpSkipEl.classList.add("color-ghost");
        }
        grpSkipEl.innerHTML = skipped.toString();

        var grpPassEl = this.shadowRoot.querySelector("#id-rgs-pass");
        if (passed > 0) {
            grpPassEl.classList.add("color-pass");
        } else {
            grpPassEl.classList.add("color-ghost");
        }
        grpPassEl.innerHTML = passed.toString();

    }
}


class TestSummaryResultItem extends HTMLElement {

    static tagname = 'testsummary-resultitem'

    static template = `
        <details>
            <summary id="id-ritem-summary">
                <div class="ts-results-items-grid">
                    <span id="id-ris-start" class="ts-results-item-start"></span>
                    <span id="id-ris-name" class="ts-results-item-name"></span>
                    <span id="id-ris-error" class="ts-results-item-score"></span>
                    <span id="id-ris-failure"  class="ts-results-item-score"></span>
                    <span id="id-ris-skip"  class="ts-results-item-score"></span>
                    <span id="id-ris-pass"  class="ts-results-item-score"></span>
                </div>
            </summary>
            <div id="id-resultitem-detail">
                <div id="id-ris-item-detail" class="ts-results-item-detail">
                    <div class="ts-results-item-prop-row" >
                        <div class="ts-results-item-prop-pair" >
                            <div id="id-rip-inst-label" class="ts-results-item-prop-label">InstId</div>
                            <div id="id-rip-inst-value" class="ts-results-item-prop-value"></div>
                        </div>
                        <div class="ts-results-item-prop-pair" >
                            <div id="id-rip-start-label" class="ts-results-item-prop-label">Start</div>
                            <div id="id-rip-start-value" class="ts-results-item-prop-value"></div>
                        </div>
                        <div class="ts-results-item-prop-pair" >
                            <div id="id-rip-stop-label" class="ts-results-item-prop-label">Stop</div>
                            <div id="id-rip-stop-value" class="ts-results-item-prop-value"></div>
                        </div>
                        <div class="ts-results-item-prop-pair" >
                            <div id="id-rip-elapsed-label" class="ts-results-item-prop-label">Elapsed</div>
                            <div id="id-rip-elapsed-value" class="ts-results-item-prop-value"></div>
                        </div>
                    </div>
                </div>
            </div>
        </details>
    `

    constructor() {
        super();

        const shadowRoot = this.attachShadow({ mode: 'open' })
        shadowRoot.innerHTML = this.getTemplate();

        addGlobalStylesToShadowRoot(shadowRoot);
    }

    getTemplate() {
        return TestSummaryResultItem.template;
    }

    syncData(testItem) {

        var itemNameEl = this.shadowRoot.querySelector("#id-ris-name");
        itemNameEl.innerHTML = testItem.name;

        var itemStartEl = this.shadowRoot.querySelector("#id-ris-start");
        itemStartEl.innerHTML = testItem.start;

        var detail = testItem.detail;

        var errored = detail.errors.length > 0 ? 1 : 0;
        var failed = detail.failures.length > 0 ? 1 : 0;
        var skipped = detail.skipped ? 1 : 0;
        var passed = detail.passed ? 1 : 0;

        var itemErrorEl = this.shadowRoot.querySelector("#id-ris-error");
        if (errored > 0) {
            itemErrorEl.classList.add("color-error");
        } else {
            itemErrorEl.classList.add("color-ghost");
        }
        itemErrorEl.innerHTML = errored.toString();

        var itemFailureEl = this.shadowRoot.querySelector("#id-ris-failure");
        if (failed > 0) {
            itemFailureEl.classList.add("color-fail");
        } else {
            itemFailureEl.classList.add("color-ghost");
        }
        itemFailureEl.innerHTML = failed.toString();

        var itemSkipEl = this.shadowRoot.querySelector("#id-ris-skip");
        if (skipped > 0) {
            itemSkipEl.classList.add("color-skip");
        } else {
            itemSkipEl.classList.add("color-ghost");
        }
        itemSkipEl.innerHTML = skipped.toString();

        var itemPassEl = this.shadowRoot.querySelector("#id-ris-pass");
        if (passed > 0) {
            itemPassEl.classList.add("color-pass");
        } else {
            itemPassEl.classList.add("color-ghost");
        }
        itemPassEl.innerHTML = passed.toString();

        var itemDetailEl = this.shadowRoot.querySelector("#id-resultitem-detail");

        var itemInstValEl = this.shadowRoot.querySelector("#id-rip-inst-value");
        itemInstValEl.innerHTML = testItem.instance;

        var itemStartValEl = this.shadowRoot.querySelector("#id-rip-start-value");
        itemStartValEl.innerHTML = testItem.start;

        var itemStopValEl = this.shadowRoot.querySelector("#id-rip-stop-value");
        itemStopValEl.innerHTML = testItem.stop;

        var elapsed = get_time_difference(testItem.start, testItem.stop);

        var itemElapsedValEl = this.shadowRoot.querySelector("#id-rip-elapsed-value");
        itemElapsedValEl.innerHTML = elapsed;

        if (errored > 0) {
            var errorsCollapsibleEl = document.createElement(TestSummaryErrorsCollapsible.tagname);

            errorsCollapsibleEl.syncData(detail.errors);

            itemDetailEl.appendChild(errorsCollapsibleEl);
        }

        if (failed > 0) {
            var failsCollapsibleEl = document.createElement(TestSummaryFailuresCollapsible.tagname);

            failsCollapsibleEl.syncData(detail.failures);

            itemDetailEl.appendChild(failsCollapsibleEl);
        }
        if ("tasking_groups" in testItem) {
            for (const tgroup of testItem.tasking_groups) {
                var taskGroupEl = document.createElement(TestSummaryTaskGroup.tagname);
                taskGroupEl.syncData(tgroup);
                itemDetailEl.appendChild(taskGroupEl);
            }
        }
        if ("checks" in testItem && testItem.checks.length > 0) {
            var checkGroupEl = document.createElement(TestSummaryCheckGroup.tagname);
            checkGroupEl.syncData(testItem);
            itemDetailEl.appendChild(checkGroupEl);
        }
        if ("property_metadata" in testItem) {
            var propMetaEl = document.createElement(TestSummaryPropertyMetadata.tagname);
            propMetaEl.syncData(testItem.property_metadata);
            itemDetailEl.appendChild(propMetaEl);
        }
    }
}

class TestSummaryTaskResult extends HTMLElement {

    static tagname = 'testsummary-taskresult'

    static template = `
        <details>
            <summary>
                <div class="ts-results-items-grid">
                    <span id="id-tris-start" class="ts-results-item-start"></span>
                    <span id="id-tris-name" class="ts-results-item-name"></span>
                    <span id="id-tris-error" class="ts-results-item-score"></span>
                    <span id="id-tris-failure" class="ts-results-item-score"></span>
                    <span id="id-tris-skip" class="ts-results-item-score"></span>
                    <span id="id-tris-pass" class="ts-results-item-score"></span>
                </div>
            </summary>
            <div id="id-taskresult-detail">
                <div class="ts-results-item-detail">
                    <div class="ts-results-item-prop-row" >
                        <div class="ts-results-item-prop-pair" >
                            <div class="ts-results-item-prop-label">InstId</div>
                            <div id="id-trip-inst-value" class="ts-results-item-prop-value"></div>
                        </div>
                        <div class="ts-results-item-prop-pair" >
                            <div class="ts-results-item-prop-label">Worker</div>
                            <div id="id-trip-worker-value" class="ts-results-item-prop-value"></div>
                        </div>
                        <div class="ts-results-item-prop-pair" >
                            <div class="ts-results-item-prop-label">Start</div>
                            <div id="id-trip-start-value" class="ts-results-item-prop-value"></div>
                        </div>
                        <div class="ts-results-item-prop-pair" >
                            <div class="ts-results-item-prop-label">Stop</div>
                            <div id="id-trip-stop-value" class="ts-results-item-prop-value"></div>
                        </div>
                        <div class="ts-results-item-prop-pair" >
                            <div class="ts-results-item-prop-label">Elapsed</div>
                            <div id="id-trip-elapsed-value" class="ts-results-item-prop-value"></div>
                        </div>
                    </div>
                </div>
            </div>
        </details>
    `

    constructor() {
        super();

        const shadowRoot = this.attachShadow({ mode: 'open' })
        shadowRoot.innerHTML = this.getTemplate();

        addGlobalStylesToShadowRoot(shadowRoot);
    }

    getTemplate() {
        return TestSummaryTaskResult.template;
    }

    syncData(taskItem) {

        var itemNameEl = this.shadowRoot.querySelector("#id-tris-name");
        itemNameEl.innerHTML = taskItem.name + " (" + taskItem.worker + ")";

        var itemStartEl = this.shadowRoot.querySelector("#id-tris-start");
        itemStartEl.innerHTML = taskItem.start;

        var errored = taskItem.result == "ERRORED" ? 1 : 0;
        var failed = taskItem.result == "FAILED" ? 1 : 0;
        var skipped = taskItem.result == "SKIPPED" ? 1 : 0;
        var passed = taskItem.result == "PASSED" ? 1 : 0;

        var detailsEl = this.shadowRoot.querySelector("details");
        var summaryEl = this.shadowRoot.querySelector("summary");
        var statusOutlineColor = "var(--color-ghost)";
        var statusBackgroundColor = "var(--color-ghost-background)";
        if (!taskItem.result || (errored + failed + skipped + passed) === 0) {
            statusOutlineColor = "var(--color-ghost)";
            statusBackgroundColor = "var(--color-ghost-background)";
        } else if (errored > 0) {
            statusOutlineColor = "var(--color-error)";
            statusBackgroundColor = "var(--color-error-background)";
        } else if (failed > 0) {
            statusOutlineColor = "var(--color-fail)";
            statusBackgroundColor = "var(--color-fail-background)";
        } else if (passed > 0) {
            statusOutlineColor = "var(--color-pass)";
            statusBackgroundColor = "var(--color-pass-background)";
        } else if (skipped > 0) {
            statusOutlineColor = "var(--color-skip)";
            statusBackgroundColor = "var(--color-skip-background)";
        }
        summaryEl.style.backgroundColor = statusBackgroundColor;
        detailsEl.style.border = "1px solid " + statusOutlineColor;

        var itemErrorEl = this.shadowRoot.querySelector("#id-tris-error");
        if (errored > 0) {
            itemErrorEl.classList.add("color-error");
        } else {
            itemErrorEl.classList.add("color-ghost");
        }
        itemErrorEl.innerHTML = errored.toString();

        var itemFailureEl = this.shadowRoot.querySelector("#id-tris-failure");
        if (failed > 0) {
            itemFailureEl.classList.add("color-fail");
        } else {
            itemFailureEl.classList.add("color-ghost");
        }
        itemFailureEl.innerHTML = failed.toString();

        var itemSkipEl = this.shadowRoot.querySelector("#id-tris-skip");
        if (skipped > 0) {
            itemSkipEl.classList.add("color-skip");
        } else {
            itemSkipEl.classList.add("color-ghost");
        }
        itemSkipEl.innerHTML = skipped.toString();

        var itemPassEl = this.shadowRoot.querySelector("#id-tris-pass");
        if (passed > 0) {
            itemPassEl.classList.add("color-pass");
        } else {
            itemPassEl.classList.add("color-ghost");
        }
        itemPassEl.innerHTML = passed.toString();

        var itemInstValEl = this.shadowRoot.querySelector("#id-trip-inst-value");
        itemInstValEl.innerHTML = taskItem.instance;

        var itemWorkerValEl = this.shadowRoot.querySelector("#id-trip-worker-value");
        itemWorkerValEl.innerHTML = taskItem.worker;

        var itemStartValEl = this.shadowRoot.querySelector("#id-trip-start-value");
        itemStartValEl.innerHTML = taskItem.start;

        var itemStopValEl = this.shadowRoot.querySelector("#id-trip-stop-value");
        itemStopValEl.innerHTML = taskItem.stop;

        var elapsed = get_time_difference(taskItem.start, taskItem.stop);

        var itemElapsedValEl = this.shadowRoot.querySelector("#id-trip-elapsed-value");
        itemElapsedValEl.innerHTML = elapsed;

        if (taskItem.detail && taskItem.detail.errors && taskItem.detail.errors.length > 0) {
            var errorsCollapsibleEl = document.createElement(TestSummaryErrorsCollapsible.tagname);
            errorsCollapsibleEl.syncData(taskItem.detail.errors);
            this.shadowRoot.querySelector("#id-taskresult-detail").appendChild(errorsCollapsibleEl);
        }

        if (taskItem.detail && taskItem.detail.failures && taskItem.detail.failures.length > 0) {
            var failsCollapsibleEl = document.createElement(TestSummaryFailuresCollapsible.tagname);
            failsCollapsibleEl.syncData(taskItem.detail.failures);
            this.shadowRoot.querySelector("#id-taskresult-detail").appendChild(failsCollapsibleEl);
        }
    }
}


class TestSummaryTaskGroup extends HTMLElement {

    static tagname = 'testsummary-taskgroup'

    static template = `
        <details>
            <summary id="id-tgrp-summary">
                <div class="ts-results-grp-grid">
                    <span id="id-tgs-name" class="ts-results-grp-name"></span>
                    <span id="id-tgs-error" class="ts-results-grp-score"></span>
                    <span id="id-tgs-failure" class="ts-results-grp-score"></span>
                    <span id="id-tgs-skip" class="ts-results-grp-score"></span>
                    <span id="id-tgs-pass" class="ts-results-grp-score"></span>
                </div>
            </summary>
            <div id="id-taskgroup-detail" style="margin-left: 20px;">
            </div>
        </details>
    `

    constructor() {
        super();

        const shadowRoot = this.attachShadow({ mode: 'open' })
        shadowRoot.innerHTML = this.getTemplate();

        addGlobalStylesToShadowRoot(shadowRoot);
    }

    getTemplate() {
        return TestSummaryTaskGroup.template;
    }

    syncData(groupInfo) {
        var grpDetailEl = this.shadowRoot.querySelector("#id-taskgroup-detail");
        grpDetailEl.innerHTML = "";

        var grpNameEl = this.shadowRoot.querySelector("#id-tgs-name");
        grpNameEl.innerHTML = groupInfo.name;

        var errored = 0;
        var failed = 0;
        var skipped = 0;
        var passed = 0;
        var total = 0;

        if (groupInfo.taskings) {
            total = groupInfo.taskings.length;
            for (const taskItem of groupInfo.taskings) {
                var itemResult = taskItem.result;

                if (itemResult == "PASSED") {
                    passed += 1;
                } else if (itemResult == "FAILED") {
                    failed += 1;
                } else if (itemResult == "ERRORED") {
                    errored += 1;
                } else if (itemResult == "SKIPPED") {
                    skipped += 1;
                }

                var taskItemEl = document.createElement(TestSummaryTaskResult.tagname);
                taskItemEl.syncData(taskItem);

                grpDetailEl.appendChild(taskItemEl);
            }
        }

        var grpSummaryEl = this.shadowRoot.querySelector("#id-tgrp-summary");
        var grpDetailsEl = this.shadowRoot.querySelector("details");
        var finished = errored + failed + skipped + passed;
        var grpStatusColor = "var(--color-pass)";
        var grpStatusBackground = "var(--color-pass-background)";
        if (total === 0 || finished < total) {
            grpStatusColor = "var(--color-ghost)";
            grpStatusBackground = "var(--color-ghost-background)";
        } else if (errored > 0) {
            grpStatusColor = "var(--color-error)";
            grpStatusBackground = "var(--color-error-background)";
        } else if (failed > 0) {
            grpStatusColor = "var(--color-fail)";
            grpStatusBackground = "var(--color-fail-background)";
        } else if (passed > 0) {
            grpStatusColor = "var(--color-pass)";
            grpStatusBackground = "var(--color-pass-background)";
        } else if (skipped > 0) {
            grpStatusColor = "var(--color-skip)";
            grpStatusBackground = "var(--color-skip-background)";
        }
        grpSummaryEl.style.backgroundColor = grpStatusBackground;
        grpDetailsEl.style.border = "1px solid " + grpStatusColor;

        var grpErrorEl = this.shadowRoot.querySelector("#id-tgs-error");
        if (errored > 0) {
            grpErrorEl.classList.add("color-error");
        } else {
            grpErrorEl.classList.add("color-ghost");
        }
        grpErrorEl.innerHTML = errored.toString();

        var grpFailEl = this.shadowRoot.querySelector("#id-tgs-failure");
        if (failed > 0) {
            grpFailEl.classList.add("color-fail");
        } else {
            grpFailEl.classList.add("color-ghost");
        }
        grpFailEl.innerHTML = failed.toString();

        var grpSkipEl = this.shadowRoot.querySelector("#id-tgs-skip");
        if (skipped > 0) {
            grpSkipEl.classList.add("color-skip");
        } else {
            grpSkipEl.classList.add("color-ghost");
        }
        grpSkipEl.innerHTML = skipped.toString();

        var grpPassEl = this.shadowRoot.querySelector("#id-tgs-pass");
        if (passed > 0) {
            grpPassEl.classList.add("color-pass");
        } else {
            grpPassEl.classList.add("color-ghost");
        }
        grpPassEl.innerHTML = passed.toString();

    }
}


/**
 * Individual check result component for property test examples.
 * Displays the generated values, result status, timing, and error/failure details
 * for a single property test example.
 */
class TestSummaryCheckResult extends HTMLElement {

    static tagname = 'testsummary-checkresult'

    static template = `
        <details>
            <summary>
                <div class="ts-results-items-grid">
                    <span id="id-cris-start" class="ts-results-item-start"></span>
                    <span id="id-cris-name" class="ts-results-item-name"></span>
                    <span id="id-cris-error" class="ts-results-item-score"></span>
                    <span id="id-cris-failure" class="ts-results-item-score"></span>
                    <span id="id-cris-skip" class="ts-results-item-score"></span>
                    <span id="id-cris-pass" class="ts-results-item-score"></span>
                </div>
            </summary>
            <div id="id-checkresult-detail">
                <div class="ts-results-item-detail">
                    <div class="ts-results-item-prop-row">
                        <div class="ts-results-item-prop-pair">
                            <div class="ts-results-item-prop-label">Example</div>
                            <div id="id-crip-index-value" class="ts-results-item-prop-value"></div>
                        </div>
                        <div class="ts-results-item-prop-pair">
                            <div class="ts-results-item-prop-label">Seed</div>
                            <div id="id-crip-seed-value" class="ts-results-item-prop-value"></div>
                        </div>
                        <div class="ts-results-item-prop-pair">
                            <div class="ts-results-item-prop-label">Start</div>
                            <div id="id-crip-start-value" class="ts-results-item-prop-value"></div>
                        </div>
                        <div class="ts-results-item-prop-pair">
                            <div class="ts-results-item-prop-label">Stop</div>
                            <div id="id-crip-stop-value" class="ts-results-item-prop-value"></div>
                        </div>
                        <div class="ts-results-item-prop-pair">
                            <div class="ts-results-item-prop-label">Elapsed</div>
                            <div id="id-crip-elapsed-value" class="ts-results-item-prop-value"></div>
                        </div>
                    </div>
                    <div id="id-crip-generated-values" class="ts-results-item-prop-row"></div>
                </div>
            </div>
        </details>
    `

    constructor() {
        super();
        const shadowRoot = this.attachShadow({ mode: 'open' })
        shadowRoot.innerHTML = this.getTemplate();
        addGlobalStylesToShadowRoot(shadowRoot);
    }

    getTemplate() {
        return TestSummaryCheckResult.template;
    }

    syncData(checkItem) {
        var genVals = checkItem.generated_values || {};
        var genValsStr = Object.keys(genVals).map(function (k) { return k + "=" + JSON.stringify(genVals[k]); }).join(", ");

        var itemNameEl = this.shadowRoot.querySelector("#id-cris-name");
        itemNameEl.innerHTML = checkItem.name + " (" + genValsStr + ")";

        var itemStartEl = this.shadowRoot.querySelector("#id-cris-start");
        itemStartEl.innerHTML = checkItem.start;

        var errored = checkItem.result == "ERRORED" ? 1 : 0;
        var failed = checkItem.result == "FAILED" ? 1 : 0;
        var skipped = checkItem.result == "SKIPPED" ? 1 : 0;
        var passed = checkItem.result == "PASSED" ? 1 : 0;

        var detailsEl = this.shadowRoot.querySelector("details");
        var summaryEl = this.shadowRoot.querySelector("summary");
        var statusOutlineColor = "var(--color-ghost)";
        var statusBackgroundColor = "var(--color-ghost-background)";
        if (errored > 0) {
            statusOutlineColor = "var(--color-error)";
            statusBackgroundColor = "var(--color-error-background)";
        } else if (failed > 0) {
            statusOutlineColor = "var(--color-fail)";
            statusBackgroundColor = "var(--color-fail-background)";
        } else if (passed > 0) {
            statusOutlineColor = "var(--color-pass)";
            statusBackgroundColor = "var(--color-pass-background)";
        }
        summaryEl.style.backgroundColor = statusBackgroundColor;
        detailsEl.style.border = "1px solid " + statusOutlineColor;

        var itemErrorEl = this.shadowRoot.querySelector("#id-cris-error");
        itemErrorEl.classList.add(errored > 0 ? "color-error" : "color-ghost");
        itemErrorEl.innerHTML = errored.toString();

        var itemFailureEl = this.shadowRoot.querySelector("#id-cris-failure");
        itemFailureEl.classList.add(failed > 0 ? "color-fail" : "color-ghost");
        itemFailureEl.innerHTML = failed.toString();

        var itemSkipEl = this.shadowRoot.querySelector("#id-cris-skip");
        itemSkipEl.classList.add(skipped > 0 ? "color-skip" : "color-ghost");
        itemSkipEl.innerHTML = skipped.toString();

        var itemPassEl = this.shadowRoot.querySelector("#id-cris-pass");
        itemPassEl.classList.add(passed > 0 ? "color-pass" : "color-ghost");
        itemPassEl.innerHTML = passed.toString();

        // Detail values
        var indexValEl = this.shadowRoot.querySelector("#id-crip-index-value");
        indexValEl.innerHTML = (checkItem.example_index !== undefined) ? checkItem.example_index.toString() : "";

        var seedValEl = this.shadowRoot.querySelector("#id-crip-seed-value");
        seedValEl.innerHTML = (checkItem.seed !== undefined) ? checkItem.seed.toString() : "";

        var startValEl = this.shadowRoot.querySelector("#id-crip-start-value");
        startValEl.innerHTML = checkItem.start;

        var stopValEl = this.shadowRoot.querySelector("#id-crip-stop-value");
        stopValEl.innerHTML = checkItem.stop;

        var elapsed = get_time_difference(checkItem.start, checkItem.stop);
        var elapsedValEl = this.shadowRoot.querySelector("#id-crip-elapsed-value");
        elapsedValEl.innerHTML = elapsed;

        // Generated values
        var genValsEl = this.shadowRoot.querySelector("#id-crip-generated-values");
        for (var key of Object.keys(genVals)) {
            var pairEl = document.createElement("div");
            pairEl.classList.add("ts-results-item-prop-pair");
            pairEl.innerHTML = '<div class="ts-results-item-prop-label">' + key +
                '</div><div class="ts-results-item-prop-value">' +
                JSON.stringify(genVals[key]) + '</div>';
            genValsEl.appendChild(pairEl);
        }

        // Error/failure detail
        var detailEl = this.shadowRoot.querySelector("#id-checkresult-detail");
        if (checkItem.detail && checkItem.detail.errors && checkItem.detail.errors.length > 0) {
            var errorsCollapsibleEl = document.createElement(TestSummaryErrorsCollapsible.tagname);
            errorsCollapsibleEl.syncData(checkItem.detail.errors);
            detailEl.appendChild(errorsCollapsibleEl);
        }
        if (checkItem.detail && checkItem.detail.failures && checkItem.detail.failures.length > 0) {
            var failsCollapsibleEl = document.createElement(TestSummaryFailuresCollapsible.tagname);
            failsCollapsibleEl.syncData(checkItem.detail.failures);
            detailEl.appendChild(failsCollapsibleEl);
        }
    }
}


/**
 * Check group component that aggregates multiple check results from a property test.
 * Displays pass/fail/error counters and contains individual TestSummaryCheckResult elements.
 */
class TestSummaryCheckGroup extends HTMLElement {

    static tagname = 'testsummary-checkgroup'

    static template = `
        <details>
            <summary id="id-cgrp-summary">
                <div class="ts-results-grp-grid">
                    <span id="id-cgs-name" class="ts-results-grp-name"></span>
                    <span id="id-cgs-error" class="ts-results-grp-score"></span>
                    <span id="id-cgs-failure" class="ts-results-grp-score"></span>
                    <span id="id-cgs-skip" class="ts-results-grp-score"></span>
                    <span id="id-cgs-pass" class="ts-results-grp-score"></span>
                </div>
            </summary>
            <div id="id-checkgroup-detail" style="margin-left: 20px;">
            </div>
        </details>
    `

    constructor() {
        super();
        const shadowRoot = this.attachShadow({ mode: 'open' })
        shadowRoot.innerHTML = this.getTemplate();
        addGlobalStylesToShadowRoot(shadowRoot);
    }

    getTemplate() {
        return TestSummaryCheckGroup.template;
    }

    syncData(testItem) {
        var grpDetailEl = this.shadowRoot.querySelector("#id-checkgroup-detail");
        grpDetailEl.innerHTML = "";

        var grpNameEl = this.shadowRoot.querySelector("#id-cgs-name");
        grpNameEl.innerHTML = "Property Checks";

        var errored = testItem.checks_errored || 0;
        var failed = testItem.checks_failed || 0;
        var passed = testItem.checks_passed || 0;

        if (testItem.checks) {
            for (const checkItem of testItem.checks) {
                var checkItemEl = document.createElement(TestSummaryCheckResult.tagname);
                checkItemEl.syncData(checkItem);
                grpDetailEl.appendChild(checkItemEl);
            }
        }

        var grpSummaryEl = this.shadowRoot.querySelector("#id-cgrp-summary");
        var grpDetailsEl = this.shadowRoot.querySelector("details");
        var grpStatusColor = "var(--color-pass)";
        var grpStatusBackground = "var(--color-pass-background)";
        if (errored > 0) {
            grpStatusColor = "var(--color-error)";
            grpStatusBackground = "var(--color-error-background)";
        } else if (failed > 0) {
            grpStatusColor = "var(--color-fail)";
            grpStatusBackground = "var(--color-fail-background)";
        } else if (passed === 0) {
            grpStatusColor = "var(--color-ghost)";
            grpStatusBackground = "var(--color-ghost-background)";
        }
        grpSummaryEl.style.backgroundColor = grpStatusBackground;
        grpDetailsEl.style.border = "1px solid " + grpStatusColor;

        var grpErrorEl = this.shadowRoot.querySelector("#id-cgs-error");
        grpErrorEl.classList.add(errored > 0 ? "color-error" : "color-ghost");
        grpErrorEl.innerHTML = errored.toString();

        var grpFailEl = this.shadowRoot.querySelector("#id-cgs-failure");
        grpFailEl.classList.add(failed > 0 ? "color-fail" : "color-ghost");
        grpFailEl.innerHTML = failed.toString();

        var grpSkipEl = this.shadowRoot.querySelector("#id-cgs-skip");
        grpSkipEl.classList.add("color-ghost");
        grpSkipEl.innerHTML = "0";

        var grpPassEl = this.shadowRoot.querySelector("#id-cgs-pass");
        grpPassEl.classList.add(passed > 0 ? "color-pass" : "color-ghost");
        grpPassEl.innerHTML = passed.toString();
    }
}


/**
 * Property metadata component displaying seed, examples, strategies, and counterexample
 * information for a property test. Extends MojoCollapsible for expandable UI.
 */
class TestSummaryPropertyMetadata extends MojoCollapsible {

    static tagname = 'testsummary-property-metadata'

    static template = `
        <div id="id-collapsible-container" class="mojo-collapsible">
            <div id="id-collapsible-button" class="mojo-collapsible-button">
                <div id="id-header-text" class="mojo-collapsible-header"></div>
                <div id="id-header-icon" class="mojo-collapsible-icon">+</div>
            </div>
            <div id="id-collapsible-content" class="ts-collapsible-content">
                <div id="id-prop-meta-detail" class="ts-results-item-detail"></div>
            </div>
        </div>
    `

    constructor() {
        super();
    }

    getTemplate() {
        return TestSummaryPropertyMetadata.template;
    }

    syncData(propMeta) {
        var detailEl = this.shadowRoot.querySelector("#id-prop-meta-detail");
        detailEl.innerHTML = "";

        if (propMeta.seed !== undefined) {
            detailEl.innerHTML += '<div class="ts-results-item-prop-row"><div class="ts-results-item-prop-pair">' +
                '<div class="ts-results-item-prop-label">Seed</div>' +
                '<div class="ts-results-item-prop-value">' + propMeta.seed + '</div></div></div>';
        }
        if (propMeta.job_seed !== undefined) {
            detailEl.innerHTML += '<div class="ts-results-item-prop-row"><div class="ts-results-item-prop-pair">' +
                '<div class="ts-results-item-prop-label">Job Seed</div>' +
                '<div class="ts-results-item-prop-value">' + propMeta.job_seed + '</div></div></div>';
        }
        if (propMeta.examples_run !== undefined) {
            detailEl.innerHTML += '<div class="ts-results-item-prop-row"><div class="ts-results-item-prop-pair">' +
                '<div class="ts-results-item-prop-label">Examples Run</div>' +
                '<div class="ts-results-item-prop-value">' + propMeta.examples_run + ' / ' + propMeta.max_examples + '</div></div></div>';
        }
        if (propMeta.strategy_descriptions) {
            var stratRow = '<div class="ts-results-item-prop-row">';
            for (var key of Object.keys(propMeta.strategy_descriptions)) {
                stratRow += '<div class="ts-results-item-prop-pair">' +
                    '<div class="ts-results-item-prop-label">' + key + '</div>' +
                    '<div class="ts-results-item-prop-value">' + propMeta.strategy_descriptions[key] + '</div></div>';
            }
            stratRow += '</div>';
            detailEl.innerHTML += stratRow;
        }
        if (propMeta.counterexample) {
            var ceRow = '<div class="ts-results-item-prop-row">';
            for (var key of Object.keys(propMeta.counterexample)) {
                ceRow += '<div class="ts-results-item-prop-pair">' +
                    '<div class="ts-results-item-prop-label">counterexample.' + key + '</div>' +
                    '<div class="ts-results-item-prop-value">' + JSON.stringify(propMeta.counterexample[key]) + '</div></div>';
            }
            ceRow += '</div>';
            detailEl.innerHTML += ceRow;
        }

        super.syncData("Property Metadata", undefined, false);
    }
}


/**
 * Result detail component displaying test results in various formats.
 * Supports grouped by package, tree view, and timeline view rendering modes.
 * 
 * @class TestSummaryResultDetail
 * @extends HTMLElement
 * 
 * @example
 * const resultDetail = document.getElementById('testsummary-resultdetail');
 * resultDetail.syncData('render_by_package', resultsData);
 */
class TestSummaryResultDetail extends HTMLElement {

    static tagname = 'testsummary-resultdetail'

    static template = `
        <div class="ts-resultdetail-card">
            <div class="ts-section-header">
                <h2 class="zero-margins-and-padding">Test Result Detail</h2>
                <div id="id-display-mode-selector" class="ts-display-mode-selector">
                    <label for="id-display-mode">View:</label>
                    <select id="id-display-mode" class="ts-display-mode-select">
                        <option value="render_by_package" selected>Grouped by Package</option>
                        <option value="render_as_tree">Tree View</option>
                        <option value="render_as_timeline">Timeline View</option>
                    </select>
                    <label for="id-grouping-option" class="ts-grouping-label">Group by:</label>
                    <select id="id-grouping-option" class="ts-grouping-select">
                        <option value="package" selected>Package</option>
                        <option value="result">Result Status</option>
                        <option value="module">Module</option>
                    </select>
                </div>
            </div>
            <div class="ts-filter-toolbar">
                <div class="ts-filter-buttons">
                    <button id="id-filter-all" class="ts-filter-btn ts-filter-btn-active" data-filter="ALL" title="Show all tests">All</button>
                    <button id="id-filter-pass" class="ts-filter-btn ts-filter-btn-pass" data-filter="PASSED" title="Show passed tests only">
                        <span class="ts-filter-btn-icon">✓</span> Pass
                    </button>
                    <button id="id-filter-fail" class="ts-filter-btn ts-filter-btn-fail" data-filter="FAILED" title="Show failed tests only">
                        <span class="ts-filter-btn-icon">✗</span> Fail
                    </button>
                    <button id="id-filter-error" class="ts-filter-btn ts-filter-btn-error" data-filter="ERRORED" title="Show errored tests only">
                        <span class="ts-filter-btn-icon">!</span> Error
                    </button>
                    <button id="id-filter-skip" class="ts-filter-btn ts-filter-btn-skip" data-filter="SKIPPED" title="Show skipped tests only">
                        <span class="ts-filter-btn-icon">⊘</span> Skip
                    </button>
                </div>
                <div class="ts-search-container">
                    <input type="text" id="id-search-input" class="ts-search-input" placeholder="Search test names..." title="Search for tests by name">
                    <button id="id-search-clear" class="ts-search-clear" title="Clear search">×</button>
                </div>
                <div class="ts-date-filter-container">
                    <label for="id-date-start" class="ts-date-label">From:</label>
                    <input type="datetime-local" id="id-date-start" class="ts-date-input" title="Filter tests starting from this date/time">
                    <label for="id-date-end" class="ts-date-label">To:</label>
                    <input type="datetime-local" id="id-date-end" class="ts-date-input" title="Filter tests ending at this date/time">
                    <button id="id-date-clear" class="ts-date-clear" title="Clear date filter">Clear Dates</button>
                </div>
                <div class="ts-filter-summary" id="id-filter-summary">
                    Showing all tests
                </div>
                <div class="ts-export-container">
                    <button id="id-export-csv" class="ts-export-btn" title="Export results to CSV">
                        <span class="ts-export-btn-icon">📄</span> CSV
                    </button>
                    <button id="id-export-pdf" class="ts-export-btn" title="Export results to PDF (Print)">
                        <span class="ts-export-btn-icon">📑</span> PDF
                    </button>
                </div>
            </div>
            <div class="ts-section-detail">
                <div id='id-test-results-header' class='ts-results-hdr-grid'>
                    
                </div>
                <div id='id-test-results-items'>
                    
                </div>
            </div>
        </div>
    `

    constructor() {
        super();

        const shadowRoot = this.attachShadow({ mode: 'open' })
        shadowRoot.innerHTML = this.getTemplate();

        addGlobalStylesToShadowRoot(shadowRoot);

        // Store reference to current results for re-rendering
        this._currentResults = null;
        this._currentGrouping = 'package';

        // Filter state
        this._activeFilter = 'ALL';
        this._searchQuery = '';
        this._dateStart = null;
        this._dateEnd = null;

        // Set up event listeners for display mode and grouping changes
        this._setupEventListeners();

        // Set up filter event listeners
        this._setupFilterEventListeners();
    }

    getTemplate() {
        return TestSummaryResultDetail.template;
    }

    /**
     * Sets up event listeners for display mode and grouping option changes.
     * @private
     */
    _setupEventListeners() {
        var self = this;

        var displayModeSelect = this.shadowRoot.querySelector("#id-display-mode");
        displayModeSelect.addEventListener("change", function (event) {
            var newMode = event.target.value;
            self._updateGroupingVisibility(newMode);
            if (self._currentResults) {
                self.syncData(newMode, self._currentResults, self._currentGrouping);
            }
        });

        var groupingSelect = this.shadowRoot.querySelector("#id-grouping-option");
        groupingSelect.addEventListener("change", function (event) {
            var newGrouping = event.target.value;
            self._currentGrouping = newGrouping;
            var currentMode = self.shadowRoot.querySelector("#id-display-mode").value;
            if (self._currentResults) {
                self.syncData(currentMode, self._currentResults, newGrouping);
            }
        });
    }

    /**
     * Updates the visibility of the grouping selector based on display mode.
     * Grouping is only applicable for grouped and tree views.
     * @param {string} displayMode - The current display mode.
     * @private
     */
    _updateGroupingVisibility(displayMode) {
        var groupingLabel = this.shadowRoot.querySelector(".ts-grouping-label");
        var groupingSelect = this.shadowRoot.querySelector("#id-grouping-option");

        if (displayMode === "render_as_timeline") {
            groupingLabel.style.display = "none";
            groupingSelect.style.display = "none";
        } else {
            groupingLabel.style.display = "";
            groupingSelect.style.display = "";
        }
    }

    /**
     * Sets up event listeners for filter buttons, search input, and date range filters.
     * @private
     */
    _setupFilterEventListeners() {
        var self = this;

        // Filter button click handlers
        var filterButtons = this.shadowRoot.querySelectorAll(".ts-filter-btn");
        filterButtons.forEach(function (btn) {
            btn.addEventListener("click", function (event) {
                var filterValue = event.currentTarget.getAttribute("data-filter");
                self._setActiveFilter(filterValue);
                self._applyFilters();
            });
        });

        // Search input handler with debounce
        var searchInput = this.shadowRoot.querySelector("#id-search-input");
        var searchTimeout = null;
        searchInput.addEventListener("input", function (event) {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(function () {
                self._searchQuery = event.target.value.trim().toLowerCase();
                self._applyFilters();
            }, 300); // 300ms debounce
        });

        // Search clear button
        var searchClear = this.shadowRoot.querySelector("#id-search-clear");
        searchClear.addEventListener("click", function () {
            searchInput.value = "";
            self._searchQuery = "";
            self._applyFilters();
        });

        // Date range filter handlers
        var dateStart = this.shadowRoot.querySelector("#id-date-start");
        dateStart.addEventListener("change", function (event) {
            self._dateStart = event.target.value ? new Date(event.target.value) : null;
            self._applyFilters();
        });

        var dateEnd = this.shadowRoot.querySelector("#id-date-end");
        dateEnd.addEventListener("change", function (event) {
            self._dateEnd = event.target.value ? new Date(event.target.value) : null;
            self._applyFilters();
        });

        // Date clear button
        var dateClear = this.shadowRoot.querySelector("#id-date-clear");
        dateClear.addEventListener("click", function () {
            dateStart.value = "";
            dateEnd.value = "";
            self._dateStart = null;
            self._dateEnd = null;
            self._applyFilters();
        });

        // Export button handlers
        var exportCsvBtn = this.shadowRoot.querySelector("#id-export-csv");
        exportCsvBtn.addEventListener("click", function () {
            self._exportToCSV();
        });

        var exportPdfBtn = this.shadowRoot.querySelector("#id-export-pdf");
        exportPdfBtn.addEventListener("click", function () {
            self._exportToPDF();
        });
    }

    /**
     * Sets the active filter and updates button styling.
     * @param {string} filterValue - The filter value: 'ALL', 'PASSED', 'FAILED', 'ERRORED', or 'SKIPPED'.
     * @private
     */
    _setActiveFilter(filterValue) {
        this._activeFilter = filterValue;

        // Update button active states
        var filterButtons = this.shadowRoot.querySelectorAll(".ts-filter-btn");
        filterButtons.forEach(function (btn) {
            var btnFilter = btn.getAttribute("data-filter");
            if (btnFilter === filterValue) {
                btn.classList.add("ts-filter-btn-active");
            } else {
                btn.classList.remove("ts-filter-btn-active");
            }
        });
    }

    /**
     * Applies all active filters (status, search, date range) and re-renders results.
     * @private
     */
    _applyFilters() {
        if (!this._currentResults) {
            return;
        }

        var filteredResults = this._filterResults(this._currentResults);

        // Update filter summary
        this._updateFilterSummary(filteredResults);

        // Re-render with filtered results
        var gridResultsHeaderEl = this.shadowRoot.querySelector("#id-test-results-header");
        gridResultsHeaderEl.innerHTML = "";

        var gridResultsItemsEl = this.shadowRoot.querySelector("#id-test-results-items");
        gridResultsItemsEl.innerHTML = "";

        var currentMode = this.shadowRoot.querySelector("#id-display-mode").value;

        if (currentMode == "render_by_package") {
            this._renderStandardHeader(gridResultsHeaderEl);
            this.renderTestsGroupedByPackage(gridResultsItemsEl, filteredResults, this._currentGrouping);
        } else if (currentMode == "render_as_tree") {
            this._renderStandardHeader(gridResultsHeaderEl);
            this.renderTestsAsTree(gridResultsItemsEl, filteredResults, this._currentGrouping);
        } else if (currentMode == "render_as_timeline") {
            this._renderTimelineHeader(gridResultsHeaderEl);
            this.renderTestsAsTimeline(gridResultsItemsEl, filteredResults);
        }
    }

    /**
     * Filters results based on active status filter, search query, and date range.
     * @param {Object} resultsDetail - The original results data.
     * @returns {Object} Filtered results data.
     * @private
     */
    _filterResults(resultsDetail) {
        var self = this;
        var filteredResults = {};

        for (var pkgName in resultsDetail) {
            if (resultsDetail.hasOwnProperty(pkgName)) {
                var tests = resultsDetail[pkgName];
                var filteredTests = tests.filter(function (test) {
                    return self._testMatchesFilters(test, pkgName);
                });

                if (filteredTests.length > 0) {
                    filteredResults[pkgName] = filteredTests;
                }
            }
        }

        return filteredResults;
    }

    /**
     * Checks if a test matches all active filters.
     * @param {Object} test - The test item to check.
     * @param {string} pkgName - The package name for the test.
     * @returns {boolean} True if the test matches all filters.
     * @private
     */
    _testMatchesFilters(test, pkgName) {
        // Check status filter
        if (this._activeFilter !== 'ALL') {
            var testStatus = this._getTestStatus(test);
            if (testStatus !== this._activeFilter) {
                return false;
            }
        }

        // Check search query
        if (this._searchQuery) {
            var testName = (test.name || '').toLowerCase();
            var fullName = (pkgName + '#' + test.name).toLowerCase();
            if (!testName.includes(this._searchQuery) && !fullName.includes(this._searchQuery)) {
                return false;
            }
        }

        // Check date range
        if (this._dateStart || this._dateEnd) {
            var testStart = test.start ? new Date(test.start) : null;

            if (testStart) {
                if (this._dateStart && testStart < this._dateStart) {
                    return false;
                }
                if (this._dateEnd && testStart > this._dateEnd) {
                    return false;
                }
            } else {
                // If test has no start time and date filter is active, exclude it
                return false;
            }
        }

        return true;
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
        // Fallback to result field
        return test.result || 'UNKNOWN';
    }

    /**
     * Updates the filter summary text showing how many tests are displayed.
     * @param {Object} filteredResults - The filtered results data.
     * @private
     */
    _updateFilterSummary(filteredResults) {
        var totalFiltered = 0;
        var totalOriginal = 0;

        // Count filtered tests
        for (var pkgName in filteredResults) {
            if (filteredResults.hasOwnProperty(pkgName)) {
                totalFiltered += filteredResults[pkgName].length;
            }
        }

        // Count original tests
        for (var pkgName in this._currentResults) {
            if (this._currentResults.hasOwnProperty(pkgName)) {
                totalOriginal += this._currentResults[pkgName].length;
            }
        }

        var summaryEl = this.shadowRoot.querySelector("#id-filter-summary");

        var summaryParts = [];

        if (this._activeFilter !== 'ALL') {
            summaryParts.push(this._activeFilter.toLowerCase() + " tests");
        }

        if (this._searchQuery) {
            summaryParts.push('matching "' + this._searchQuery + '"');
        }

        if (this._dateStart || this._dateEnd) {
            summaryParts.push("in date range");
        }

        if (summaryParts.length === 0) {
            summaryEl.innerHTML = "Showing all " + totalOriginal + " tests";
        } else {
            summaryEl.innerHTML = "Showing " + totalFiltered + " of " + totalOriginal + " tests (" + summaryParts.join(", ") + ")";
        }
    }

    /**
     * Exports the currently filtered results to CSV format.
     * Creates a downloadable CSV file with test name, package, status, start time, and duration.
     * @private
     */
    _exportToCSV() {
        if (!this._currentResults) {
            console.warn("No results to export");
            return;
        }

        // Get filtered results
        var filteredResults = this._filterResults(this._currentResults);

        // Build CSV content
        var csvRows = [];

        // Header row
        csvRows.push(["Test Name", "Package", "Status", "Start Time", "Stop Time", "Errors", "Failures"].join(","));

        // Data rows
        for (var pkgName in filteredResults) {
            if (filteredResults.hasOwnProperty(pkgName)) {
                var tests = filteredResults[pkgName];
                for (var i = 0; i < tests.length; i++) {
                    var test = tests[i];
                    var status = this._getTestStatus(test);
                    var errorCount = (test.detail && test.detail.errors) ? test.detail.errors.length : 0;
                    var failureCount = (test.detail && test.detail.failures) ? test.detail.failures.length : 0;

                    // Escape CSV values
                    var testName = this._escapeCSVValue(test.name || "");
                    var packageName = this._escapeCSVValue(pkgName || "");
                    var startTime = this._escapeCSVValue(test.start || "");
                    var stopTime = this._escapeCSVValue(test.stop || "");

                    csvRows.push([testName, packageName, status, startTime, stopTime, errorCount, failureCount].join(","));
                }
            }
        }

        // Create and download file
        var csvContent = csvRows.join("\n");
        var blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
        var url = URL.createObjectURL(blob);

        var link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", "test_results_" + this._getExportTimestamp() + ".csv");
        link.style.visibility = "hidden";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // Clean up the URL object
        URL.revokeObjectURL(url);
    }

    /**
     * Escapes a value for CSV format by wrapping in quotes if necessary.
     * @param {string} value - The value to escape.
     * @returns {string} The escaped CSV value.
     * @private
     */
    _escapeCSVValue(value) {
        if (value === null || value === undefined) {
            return "";
        }
        var strValue = String(value);
        // If value contains comma, newline, or quote, wrap in quotes and escape internal quotes
        if (strValue.indexOf(",") > -1 || strValue.indexOf("\n") > -1 || strValue.indexOf('"') > -1) {
            return '"' + strValue.replace(/"/g, '""') + '"';
        }
        return strValue;
    }

    /**
     * Gets a timestamp string for export filenames.
     * @returns {string} Timestamp in format YYYYMMDD_HHMMSS.
     * @private
     */
    _getExportTimestamp() {
        var now = new Date();
        var year = now.getFullYear();
        var month = String(now.getMonth() + 1).padStart(2, "0");
        var day = String(now.getDate()).padStart(2, "0");
        var hours = String(now.getHours()).padStart(2, "0");
        var minutes = String(now.getMinutes()).padStart(2, "0");
        var seconds = String(now.getSeconds()).padStart(2, "0");
        return year + month + day + "_" + hours + minutes + seconds;
    }

    /**
     * Exports the currently filtered results to PDF format using browser print functionality.
     * Opens a new window with a print-friendly view of the results.
     * @private
     */
    _exportToPDF() {
        if (!this._currentResults) {
            console.warn("No results to export");
            return;
        }

        // Get filtered results
        var filteredResults = this._filterResults(this._currentResults);

        // Build HTML content for print
        var htmlContent = this._buildPrintableHTML(filteredResults);

        // Open print window
        var printWindow = window.open("", "_blank", "width=800,height=600");
        printWindow.document.write(htmlContent);
        printWindow.document.close();

        // Wait for content to load then trigger print
        printWindow.onload = function () {
            printWindow.focus();
            printWindow.print();
        };
    }

    /**
     * Builds a printable HTML document for PDF export.
     * @param {Object} filteredResults - The filtered results to include in the document.
     * @returns {string} Complete HTML document string.
     * @private
     */
    _buildPrintableHTML(filteredResults) {
        var totalTests = 0;
        var passedCount = 0;
        var failedCount = 0;
        var errorCount = 0;
        var skippedCount = 0;

        // Count totals
        for (var pkgName in filteredResults) {
            if (filteredResults.hasOwnProperty(pkgName)) {
                var tests = filteredResults[pkgName];
                totalTests += tests.length;
                for (var i = 0; i < tests.length; i++) {
                    var status = this._getTestStatus(tests[i]);
                    if (status === "PASSED") passedCount++;
                    else if (status === "FAILED") failedCount++;
                    else if (status === "ERRORED") errorCount++;
                    else if (status === "SKIPPED") skippedCount++;
                }
            }
        }

        var html = '<!DOCTYPE html><html><head><title>Test Results Report</title>';
        html += '<style>';
        html += 'body { font-family: Arial, sans-serif; margin: 20px; font-size: 12pt; }';
        html += 'h1 { color: #333; border-bottom: 2px solid #333; padding-bottom: 10px; }';
        html += 'h2 { color: #555; margin-top: 20px; }';
        html += '.summary { background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }';
        html += '.summary-item { display: inline-block; margin-right: 30px; }';
        html += '.summary-label { font-weight: bold; }';
        html += '.pass { color: green; }';
        html += '.fail { color: red; }';
        html += '.error { color: maroon; }';
        html += '.skip { color: gray; }';
        html += 'table { width: 100%; border-collapse: collapse; margin-top: 10px; }';
        html += 'th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }';
        html += 'th { background-color: #f0f0f0; font-weight: bold; }';
        html += 'tr:nth-child(even) { background-color: #fafafa; }';
        html += '.package-header { background-color: #e0e0e0; font-weight: bold; }';
        html += '@media print { .no-print { display: none; } }';
        html += '</style></head><body>';

        // Header
        html += '<h1>Test Results Report</h1>';
        html += '<p>Generated: ' + new Date().toLocaleString() + '</p>';

        // Summary section
        html += '<div class="summary">';
        html += '<div class="summary-item"><span class="summary-label">Total Tests:</span> ' + totalTests + '</div>';
        html += '<div class="summary-item"><span class="summary-label pass">Passed:</span> ' + passedCount + '</div>';
        html += '<div class="summary-item"><span class="summary-label fail">Failed:</span> ' + failedCount + '</div>';
        html += '<div class="summary-item"><span class="summary-label error">Errors:</span> ' + errorCount + '</div>';
        html += '<div class="summary-item"><span class="summary-label skip">Skipped:</span> ' + skippedCount + '</div>';
        html += '</div>';

        // Filter info
        if (this._activeFilter !== 'ALL' || this._searchQuery || this._dateStart || this._dateEnd) {
            html += '<p><em>Filters applied: ';
            var filters = [];
            if (this._activeFilter !== 'ALL') filters.push('Status: ' + this._activeFilter);
            if (this._searchQuery) filters.push('Search: "' + this._searchQuery + '"');
            if (this._dateStart || this._dateEnd) filters.push('Date range filter');
            html += filters.join(', ') + '</em></p>';
        }

        // Results table
        html += '<h2>Test Results</h2>';
        html += '<table>';
        html += '<thead><tr><th>Test Name</th><th>Status</th><th>Start Time</th><th>Errors</th><th>Failures</th></tr></thead>';
        html += '<tbody>';

        for (var pkgName in filteredResults) {
            if (filteredResults.hasOwnProperty(pkgName)) {
                // Package header row
                html += '<tr class="package-header"><td colspan="5">' + this._escapeHTML(pkgName) + '</td></tr>';

                var tests = filteredResults[pkgName];
                for (var i = 0; i < tests.length; i++) {
                    var test = tests[i];
                    var status = this._getTestStatus(test);
                    var statusClass = status.toLowerCase();
                    var errCount = (test.detail && test.detail.errors) ? test.detail.errors.length : 0;
                    var failCount = (test.detail && test.detail.failures) ? test.detail.failures.length : 0;

                    html += '<tr>';
                    html += '<td>' + this._escapeHTML(test.name || "") + '</td>';
                    html += '<td class="' + statusClass + '">' + status + '</td>';
                    html += '<td>' + this._escapeHTML(test.start || "") + '</td>';
                    html += '<td>' + errCount + '</td>';
                    html += '<td>' + failCount + '</td>';
                    html += '</tr>';
                }
            }
        }

        html += '</tbody></table>';
        html += '</body></html>';

        return html;
    }

    /**
     * Escapes HTML special characters to prevent XSS in the print view.
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
     * Syncs data to the component and renders results in the specified format.
     * @param {string} renderFormat - The rendering format: 'render_by_package', 'render_as_tree', or 'render_as_timeline'.
     * @param {Object} resultsDetail - The results data to render.
     * @param {string} [groupingOption='package'] - The grouping option for grouped/tree views.
     */
    syncData(renderFormat, resultsDetail, groupingOption = 'package') {

        // Store results for potential re-rendering
        this._currentResults = resultsDetail;
        this._currentGrouping = groupingOption;

        var gridResultsHeaderEl = this.shadowRoot.querySelector("#id-test-results-header");
        gridResultsHeaderEl.innerHTML = "";

        var gridResultsItemsEl = this.shadowRoot.querySelector("#id-test-results-items");
        gridResultsItemsEl.innerHTML = "";

        // Update display mode selector to match current mode
        var displayModeSelect = this.shadowRoot.querySelector("#id-display-mode");
        displayModeSelect.value = renderFormat;
        this._updateGroupingVisibility(renderFormat);

        // Update grouping selector
        var groupingSelect = this.shadowRoot.querySelector("#id-grouping-option");
        groupingSelect.value = groupingOption;

        if (renderFormat == "render_by_package") {
            this._renderStandardHeader(gridResultsHeaderEl);
            this.renderTestsGroupedByPackage(gridResultsItemsEl, resultsDetail, groupingOption);
        } else if (renderFormat == "render_as_tree") {
            this._renderStandardHeader(gridResultsHeaderEl);
            this.renderTestsAsTree(gridResultsItemsEl, resultsDetail, groupingOption);
        } else if (renderFormat == "render_as_timeline") {
            this._renderTimelineHeader(gridResultsHeaderEl);
            this.renderTestsAsTimeline(gridResultsItemsEl, resultsDetail);
        }
    }

    /**
     * Renders the standard header for grouped and tree views.
     * @param {HTMLElement} headerEl - The header container element.
     * @private
     */
    _renderStandardHeader(headerEl) {
        var startHeader = document.createElement("div");
        startHeader.classList.add("ts-results-hdr-start");
        startHeader.innerHTML = "Start";
        headerEl.appendChild(startHeader);

        var nameHeader = document.createElement("div");
        nameHeader.classList.add("ts-results-hdr-name");
        nameHeader.innerHTML = "TestName";
        headerEl.appendChild(nameHeader);

        var errorHeader = document.createElement("div");
        errorHeader.classList.add("ts-results-hdr-e");
        errorHeader.innerHTML = "E";
        headerEl.appendChild(errorHeader);

        var failHeader = document.createElement("div");
        failHeader.classList.add("ts-results-hdr-f");
        failHeader.innerHTML = "F";
        headerEl.appendChild(failHeader);

        var skipHeader = document.createElement("div");
        skipHeader.classList.add("ts-results-hdr-s");
        skipHeader.innerHTML = "S";
        headerEl.appendChild(skipHeader);

        var passHeader = document.createElement("div");
        passHeader.classList.add("ts-results-hdr-p");
        passHeader.innerHTML = "P";
        headerEl.appendChild(passHeader);
    }

    /**
     * Renders the timeline header for timeline view.
     * @param {HTMLElement} headerEl - The header container element.
     * @private
     */
    _renderTimelineHeader(headerEl) {
        headerEl.classList.remove("ts-results-hdr-grid");
        headerEl.classList.add("ts-timeline-header");

        var timeHeader = document.createElement("div");
        timeHeader.classList.add("ts-timeline-hdr-time");
        timeHeader.innerHTML = "Timeline";
        headerEl.appendChild(timeHeader);

        var durationHeader = document.createElement("div");
        durationHeader.classList.add("ts-timeline-hdr-duration");
        durationHeader.innerHTML = "Duration";
        headerEl.appendChild(durationHeader);

        var nameHeader = document.createElement("div");
        nameHeader.classList.add("ts-timeline-hdr-name");
        nameHeader.innerHTML = "Test Name";
        headerEl.appendChild(nameHeader);

        var statusHeader = document.createElement("div");
        statusHeader.classList.add("ts-timeline-hdr-status");
        statusHeader.innerHTML = "Status";
        headerEl.appendChild(statusHeader);
    }

    /**
     * Renders tests grouped by package (default view).
     * @param {HTMLElement} gridResultsEl - The container element for results.
     * @param {Object} resultsDetail - The results data keyed by package name.
     * @param {string} groupingOption - The grouping option.
     */
    renderTestsGroupedByPackage(gridResultsEl, resultsDetail, groupingOption) {
        var groupedResults = this._groupResults(resultsDetail, groupingOption);

        for (const [groupName, testGroup] of Object.entries(groupedResults)) {
            var resultItemEl = document.createElement("testsummary-resultgroup");
            resultItemEl.syncData(groupName, testGroup);
            gridResultsEl.appendChild(resultItemEl);
        }
    }

    /**
     * Renders tests as a hierarchical tree view.
     * Organizes tests by their module path hierarchy.
     * @param {HTMLElement} gridResultsEl - The container element for results.
     * @param {Object} resultsDetail - The results data.
     * @param {string} groupingOption - The grouping option.
     */
    renderTestsAsTree(gridResultsEl, resultsDetail, groupingOption) {
        // Build tree structure from package names
        var treeRoot = this._buildTreeStructure(resultsDetail, groupingOption);

        // Render tree recursively
        this._renderTreeNode(gridResultsEl, treeRoot, 0);
    }

    /**
     * Renders tests as a timeline view showing execution order and duration.
     * @param {HTMLElement} gridResultsEl - The container element for results.
     * @param {Object} resultsDetail - The results data.
     */
    renderTestsAsTimeline(gridResultsEl, resultsDetail) {
        // Flatten all results and sort by start time
        var allTests = this._flattenResults(resultsDetail);
        allTests.sort(function (a, b) {
            return new Date(a.start) - new Date(b.start);
        });

        // Find time range for timeline scaling
        var timeRange = this._calculateTimeRange(allTests);

        // Create timeline container
        var timelineContainer = document.createElement("div");
        timelineContainer.classList.add("ts-timeline-container");

        // Render each test as a timeline item
        for (var i = 0; i < allTests.length; i++) {
            var testItem = allTests[i];
            var timelineItem = this._createTimelineItem(testItem, timeRange, i);
            timelineContainer.appendChild(timelineItem);
        }

        gridResultsEl.appendChild(timelineContainer);
    }

    /**
     * Groups results based on the specified grouping option.
     * @param {Object} resultsDetail - The results data.
     * @param {string} groupingOption - The grouping option: 'package', 'result', or 'module'.
     * @returns {Object} Grouped results.
     * @private
     */
    _groupResults(resultsDetail, groupingOption) {
        if (groupingOption === 'package') {
            // Already grouped by package
            return resultsDetail;
        }

        var grouped = {};

        for (const [pkgName, tests] of Object.entries(resultsDetail)) {
            for (const test of tests) {
                var groupKey;

                if (groupingOption === 'result') {
                    // Group by result status
                    groupKey = test.result || 'UNKNOWN';
                } else if (groupingOption === 'module') {
                    // Group by module (first part of package name)
                    var parts = pkgName.split('.');
                    groupKey = parts.length > 0 ? parts[0] : 'unknown';
                } else {
                    groupKey = pkgName;
                }

                if (!grouped[groupKey]) {
                    grouped[groupKey] = [];
                }
                grouped[groupKey].push(test);
            }
        }

        return grouped;
    }

    /**
     * Builds a tree structure from the results for tree view rendering.
     * @param {Object} resultsDetail - The results data.
     * @param {string} groupingOption - The grouping option.
     * @returns {Object} Tree structure with children and tests.
     * @private
     */
    _buildTreeStructure(resultsDetail, groupingOption) {
        var root = { name: 'root', children: {}, tests: [] };

        for (const [pkgName, tests] of Object.entries(resultsDetail)) {
            // Split package name into path segments
            var pathParts;
            if (groupingOption === 'module') {
                pathParts = pkgName.split('.');
            } else if (groupingOption === 'result') {
                // For result grouping, use result as first level
                for (const test of tests) {
                    var resultKey = test.result || 'UNKNOWN';
                    if (!root.children[resultKey]) {
                        root.children[resultKey] = { name: resultKey, children: {}, tests: [] };
                    }
                    root.children[resultKey].tests.push(test);
                }
                continue;
            } else {
                pathParts = pkgName.split('.');
            }

            // Navigate/create tree path
            var currentNode = root;
            for (var i = 0; i < pathParts.length; i++) {
                var part = pathParts[i];
                if (!currentNode.children[part]) {
                    currentNode.children[part] = { name: part, children: {}, tests: [] };
                }
                currentNode = currentNode.children[part];
            }

            // Add tests to leaf node
            for (const test of tests) {
                currentNode.tests.push(test);
            }
        }

        return root;
    }

    /**
     * Recursively renders a tree node and its children.
     * @param {HTMLElement} containerEl - The container element.
     * @param {Object} node - The tree node to render.
     * @param {number} depth - The current depth in the tree.
     * @private
     */
    _renderTreeNode(containerEl, node, depth) {
        var self = this;

        // Render children first
        var childKeys = Object.keys(node.children).sort();
        for (var i = 0; i < childKeys.length; i++) {
            var childKey = childKeys[i];
            var childNode = node.children[childKey];

            // Create tree node element
            var nodeEl = document.createElement("div");
            nodeEl.classList.add("ts-tree-node");
            nodeEl.style.marginLeft = (depth * 20) + "px";

            // Create expandable header
            var headerEl = document.createElement("details");
            headerEl.open = depth < 2; // Auto-expand first two levels

            var summaryEl = document.createElement("summary");
            summaryEl.classList.add("ts-tree-node-header");

            var iconEl = document.createElement("span");
            iconEl.classList.add("ts-tree-icon");
            iconEl.innerHTML = "📁";
            summaryEl.appendChild(iconEl);

            var nameEl = document.createElement("span");
            nameEl.classList.add("ts-tree-node-name");
            nameEl.innerHTML = childNode.name;
            summaryEl.appendChild(nameEl);

            // Add metrics summary
            var metrics = this._calculateNodeMetrics(childNode);
            var metricsEl = document.createElement("span");
            metricsEl.classList.add("ts-tree-node-metrics");
            metricsEl.innerHTML = this._formatMetrics(metrics);
            summaryEl.appendChild(metricsEl);

            headerEl.appendChild(summaryEl);

            // Create content container for children and tests
            var contentEl = document.createElement("div");
            contentEl.classList.add("ts-tree-node-content");

            // Recursively render children
            this._renderTreeNode(contentEl, childNode, depth + 1);

            // Render tests at this node
            if (childNode.tests.length > 0) {
                for (var j = 0; j < childNode.tests.length; j++) {
                    var test = childNode.tests[j];
                    var testEl = document.createElement("testsummary-resultitem");
                    testEl.syncData(test);
                    testEl.style.marginLeft = "20px";
                    contentEl.appendChild(testEl);
                }
            }

            headerEl.appendChild(contentEl);
            nodeEl.appendChild(headerEl);
            containerEl.appendChild(nodeEl);
        }

        // Render tests directly under root (if any)
        if (depth === 0 && node.tests.length > 0) {
            for (var k = 0; k < node.tests.length; k++) {
                var rootTest = node.tests[k];
                var rootTestEl = document.createElement("testsummary-resultitem");
                rootTestEl.syncData(rootTest);
                containerEl.appendChild(rootTestEl);
            }
        }
    }

    /**
     * Calculates aggregate metrics for a tree node and all its descendants.
     * @param {Object} node - The tree node.
     * @returns {Object} Metrics object with passed, failed, errored, skipped counts.
     * @private
     */
    _calculateNodeMetrics(node) {
        var metrics = { passed: 0, failed: 0, errored: 0, skipped: 0 };

        // Count tests at this node
        for (var i = 0; i < node.tests.length; i++) {
            var test = node.tests[i];
            if (test.result === 'PASSED') metrics.passed++;
            else if (test.result === 'FAILED') metrics.failed++;
            else if (test.result === 'ERRORED') metrics.errored++;
            else if (test.result === 'SKIPPED') metrics.skipped++;
        }

        // Recursively count children
        for (var childKey in node.children) {
            var childMetrics = this._calculateNodeMetrics(node.children[childKey]);
            metrics.passed += childMetrics.passed;
            metrics.failed += childMetrics.failed;
            metrics.errored += childMetrics.errored;
            metrics.skipped += childMetrics.skipped;
        }

        return metrics;
    }

    /**
     * Formats metrics for display in tree node headers.
     * @param {Object} metrics - The metrics object.
     * @returns {string} Formatted metrics string.
     * @private
     */
    _formatMetrics(metrics) {
        var parts = [];
        if (metrics.errored > 0) parts.push('<span class="color-error">' + metrics.errored + 'E</span>');
        if (metrics.failed > 0) parts.push('<span class="color-fail">' + metrics.failed + 'F</span>');
        if (metrics.skipped > 0) parts.push('<span class="color-skip">' + metrics.skipped + 'S</span>');
        if (metrics.passed > 0) parts.push('<span class="color-pass">' + metrics.passed + 'P</span>');
        return parts.join(' ');
    }

    /**
     * Flattens the results object into an array of all tests.
     * @param {Object} resultsDetail - The results data.
     * @returns {Array} Array of all test items.
     * @private
     */
    _flattenResults(resultsDetail) {
        var allTests = [];
        for (const [pkgName, tests] of Object.entries(resultsDetail)) {
            for (const test of tests) {
                // Add package name to test for display
                test.package_name = pkgName;
                allTests.push(test);
            }
        }
        return allTests;
    }

    /**
     * Calculates the time range for timeline scaling.
     * @param {Array} tests - Array of test items sorted by start time.
     * @returns {Object} Time range with start, end, and duration.
     * @private
     */
    _calculateTimeRange(tests) {
        if (tests.length === 0) {
            return { start: new Date(), end: new Date(), duration: 0 };
        }

        var startTime = new Date(tests[0].start);
        var endTime = startTime;

        for (var i = 0; i < tests.length; i++) {
            var test = tests[i];
            var testStart = new Date(test.start);
            var testEnd = test.stop ? new Date(test.stop) : testStart;

            if (testStart < startTime) startTime = testStart;
            if (testEnd > endTime) endTime = testEnd;
        }

        return {
            start: startTime,
            end: endTime,
            duration: endTime - startTime
        };
    }

    /**
     * Creates a timeline item element for a test.
     * @param {Object} testItem - The test item data.
     * @param {Object} timeRange - The overall time range.
     * @param {number} index - The index of the test in the timeline.
     * @returns {HTMLElement} The timeline item element.
     * @private
     */
    _createTimelineItem(testItem, timeRange, index) {
        var itemEl = document.createElement("div");
        itemEl.classList.add("ts-timeline-item");

        // Calculate position and width based on time
        var testStart = new Date(testItem.start);
        var testEnd = testItem.stop ? new Date(testItem.stop) : testStart;
        var testDuration = testEnd - testStart;

        // Time column
        var timeEl = document.createElement("div");
        timeEl.classList.add("ts-timeline-item-time");
        timeEl.innerHTML = this._formatTime(testStart);
        itemEl.appendChild(timeEl);

        // Duration bar column
        var durationEl = document.createElement("div");
        durationEl.classList.add("ts-timeline-item-duration");

        var barContainer = document.createElement("div");
        barContainer.classList.add("ts-timeline-bar-container");

        var bar = document.createElement("div");
        bar.classList.add("ts-timeline-bar");

        // Calculate bar position and width
        var offsetPercent = 0;
        var widthPercent = 100;
        if (timeRange.duration > 0) {
            offsetPercent = ((testStart - timeRange.start) / timeRange.duration) * 100;
            widthPercent = Math.max(1, (testDuration / timeRange.duration) * 100);
        }

        bar.style.left = offsetPercent + "%";
        bar.style.width = widthPercent + "%";

        // Color based on result
        if (testItem.result === 'PASSED') {
            bar.classList.add("ts-timeline-bar-pass");
        } else if (testItem.result === 'FAILED') {
            bar.classList.add("ts-timeline-bar-fail");
        } else if (testItem.result === 'ERRORED') {
            bar.classList.add("ts-timeline-bar-error");
        } else if (testItem.result === 'SKIPPED') {
            bar.classList.add("ts-timeline-bar-skip");
        }

        barContainer.appendChild(bar);

        // Add duration text
        var durationText = document.createElement("span");
        durationText.classList.add("ts-timeline-duration-text");
        durationText.innerHTML = this._formatDuration(testDuration);
        barContainer.appendChild(durationText);

        durationEl.appendChild(barContainer);
        itemEl.appendChild(durationEl);

        // Test name column
        var nameEl = document.createElement("div");
        nameEl.classList.add("ts-timeline-item-name");
        nameEl.innerHTML = testItem.name || testItem.package_name;
        nameEl.title = testItem.package_name + "#" + testItem.name;
        itemEl.appendChild(nameEl);

        // Status column
        var statusEl = document.createElement("div");
        statusEl.classList.add("ts-timeline-item-status");
        var statusSpan = document.createElement("span");
        statusSpan.innerHTML = testItem.result || 'UNKNOWN';
        if (testItem.result === 'PASSED') statusSpan.classList.add("color-pass");
        else if (testItem.result === 'FAILED') statusSpan.classList.add("color-fail");
        else if (testItem.result === 'ERRORED') statusSpan.classList.add("color-error");
        else if (testItem.result === 'SKIPPED') statusSpan.classList.add("color-skip");
        statusEl.appendChild(statusSpan);
        itemEl.appendChild(statusEl);

        return itemEl;
    }

    /**
     * Formats a date for display in the timeline.
     * @param {Date} date - The date to format.
     * @returns {string} Formatted time string.
     * @private
     */
    _formatTime(date) {
        var hours = date.getHours().toString().padStart(2, '0');
        var minutes = date.getMinutes().toString().padStart(2, '0');
        var seconds = date.getSeconds().toString().padStart(2, '0');
        return hours + ':' + minutes + ':' + seconds;
    }

    /**
     * Formats a duration in milliseconds for display.
     * @param {number} ms - Duration in milliseconds.
     * @returns {string} Formatted duration string.
     * @private
     */
    _formatDuration(ms) {
        if (ms < 1000) {
            return ms + 'ms';
        } else if (ms < 60000) {
            return (ms / 1000).toFixed(2) + 's';
        } else {
            var minutes = Math.floor(ms / 60000);
            var seconds = ((ms % 60000) / 1000).toFixed(0);
            return minutes + 'm ' + seconds + 's';
        }
    }
}


class TestSummaryErrorsCollapsible extends MojoCollapsible {

    static tagname = 'testsummary-errors-collection'

    static template = `
        <div id="id-collapsible-container" class="ts-errors-collapsible" >
            <div id="id-collapsible-button" class="ts-errors-collapsible-button">
                <div id="id-header-text" class="ts-errors-collapsible-header">ERRORS</div>
                <div id="id-header-icon" class="ts-errors-collapsible-icon">+</div>
            </div>
            <div id="id-collapsible-content" class="ts-errors-collapsible-content">
            </div>
        </div>
    `

    constructor() {
        super();
    }

    getTemplate() {
        return TestSummaryErrorsCollapsible.template;
    }

    syncData(errors) {

        var contentEl = this.shadowRoot.querySelector(this.sel_content);

        var errorCount = errors.length;

        for (var eidx = 0; eidx < errorCount; eidx++) {
            var traceInfo = errors[eidx];

            var traceEl = document.createElement(TestSummaryExceptionTrace.tagname)
            traceEl.syncData(traceInfo.exargs, traceInfo.extype, traceInfo.traces);

            contentEl.appendChild(traceEl);
        }

        super.syncData("ERRORS", undefined, false);
    }

}


class TestSummaryFailuresCollapsible extends MojoCollapsible {

    static tagname = 'testsummary-failures-collection'

    static template = `
        <div id="id-collapsible-container" class="ts-failures-collapsible" >
            <div id="id-collapsible-button" class="ts-failures-collapsible-button">
                <div id="id-header-text" class="ts-failures-collapsible-header"></div>
                <div id="id-header-icon" class="ts-failures-collapsible-icon">+</div>
            </div>
            <div id="id-collapsible-content" class="ts-failures-collapsible-content">
            </div>
        </div>
    `

    constructor() {
        super();
    }

    getTemplate() {
        return TestSummaryFailuresCollapsible.template;
    }

    syncData(failures) {

        var contentEl = this.shadowRoot.querySelector(this.sel_content);

        var failureCount = failures.length;

        for (var fidx = 0; fidx < failureCount; fidx++) {
            var traceInfo = failures[fidx];

            var traceEl = document.createElement(TestSummaryExceptionTrace.tagname)
            traceEl.syncData(traceInfo.exargs, traceInfo.extype, traceInfo.traces);

            contentEl.appendChild(traceEl);
        }

        super.syncData("FAILURES", undefined, false);
    }
}


class TestSummaryExceptionTrace extends HTMLElement {

    static tagname = 'testsummary-exception-trace'

    static template = `
        <div id="id-exception-content" class="ts-exception-content">
            <pre></pre>
        </div>
    `

    sel_exception_content = "#id-exception-content"

    constructor() {
        super();

        const shadowRoot = this.attachShadow({ mode: 'open' })
        shadowRoot.innerHTML = this.getTemplate();

        addGlobalStylesToShadowRoot(shadowRoot);
    }

    getTemplate() {
        return TestSummaryExceptionTrace.template;
    }

    syncData(exargs, extype, trace_lines) {

        var contentEl = this.shadowRoot.querySelector(this.sel_exception_content);

        var exAndMsgEl = document.createElement("pre");
        exAndMsgEl.classList.add("code-font-dk")
        exAndMsgEl.innerHTML = extype + ", " + exargs;
        contentEl.appendChild(exAndMsgEl);

        var traces_len = trace_lines.length;

        for (var tidx = 0; tidx < traces_len; tidx++) {
            var traceInfo = trace_lines[tidx];
            var traceEl = this.createTraceElement(traceInfo);
            contentEl.appendChild(traceEl);
        }
    }

    createTraceElement(traceInfo) {
        var outerDivEl = document.createElement('div');

        var origin = traceInfo.origin;

        var nxtPreEl = document.createElement('pre');
        nxtPreEl.classList.add("code-font-lt");
        nxtPreEl.innerHTML = "  File " + origin.file + ", line " + origin.lineno + ", in " + origin.scope;
        outerDivEl.appendChild(nxtPreEl);

        nxtPreEl = document.createElement('pre');
        nxtPreEl.classList.add("margin-lg");
        nxtPreEl.classList.add("code-font-dk");
        nxtPreEl.innerHTML = entity_escape(traceInfo.call);
        outerDivEl.appendChild(nxtPreEl);

        if ((traceInfo.code != undefined) && (traceInfo.code.length > 0)) {
            var nxtPreEl = document.createElement('pre');
            nxtPreEl.classList.add("margin-lg");

            var codeEl = document.createElement('code');
            codeEl.classList.add("language-python");
            codeEl.innerHTML = "\n" + traceInfo.code.join("\n");
            nxtPreEl.appendChild(codeEl);
        }

        outerDivEl.appendChild(nxtPreEl);

        return outerDivEl;
    }
}


class TestSummaryImportFailureTrace extends MojoCollapsible {
    static tagname = 'testsummary-import-failure-trace'

    static template = `
        <div id="id-collapsible-container" class="ts-importfailure-trace" >
            <div id="id-collapsible-button" class="ts-importfailure-trace-button">
                <div id="id-header-text" class="ts-importfailure-trace-header">Trace</div>
                <div id="id-header-icon" class="ts-importfailure-trace-icon">+</div>
            </div>
            <div id="id-collapsible-content" class="ts-importfailure-trace-content">
            </div>
        </div>
    `

    constructor() {
        super();
    }

    getTemplate() {
        return TestSummaryImportFailureTrace.template;
    }

    syncData(header, trace_lines) {

        var contentEl = this.shadowRoot.querySelector(this.sel_content);
        contentEl.innerHTML = "";

        var traceContentEl = this.createTraceContent(trace_lines);
        contentEl.appendChild(traceContentEl);

        super.syncData(header, undefined, false);
    }

    createTraceContent(trace_lines) {

        trace_lines = trace_lines.reverse();

        var traceLinesEl = document.createElement("div");

        for (var tindex in trace_lines) {
            var titem = trace_lines[tindex];
            var nxtLineEl = document.createElement("pre");
            nxtLineEl.innerHTML = titem;

            traceLinesEl.appendChild(nxtLineEl);
        }

        return traceLinesEl;

    }
}


class TestSummaryImportFailureItem extends HTMLElement {

    static tagname = 'testsummary-import-failure-item'

    static template = `
        <div class='ts-importfailure-item'>
            <mojo-property-table id="id-ts-trace-prop-table">
            </mojo-property-table>
            <testsummary-import-failure-trace id="id-ts-import-trace">
            </testsummary-import-failure-trace>
        </div>
    `

    sel_trace_prop_table = "#id-ts-trace-prop-table"
    sel_trace = "#id-ts-import-trace"

    constructor() {
        super();

        const shadowRoot = this.attachShadow({ mode: 'open' })
        shadowRoot.innerHTML = this.getTemplate();

        addGlobalStylesToShadowRoot(shadowRoot);
    }

    getTemplate() {
        return TestSummaryImportFailureItem.template;
    }

    syncData(importError) {

        var traceProps = {
            "Filename": importError.filename,
            "Module": importError.module
        };

        var trace = importError.trace;

        var propTableEl = this.shadowRoot.querySelector(this.sel_trace_prop_table);
        propTableEl.syncData(traceProps);

        var traceCollEl = this.shadowRoot.querySelector(this.sel_trace);
        traceCollEl.syncData("Trace", trace);
    }

    createTraceContent(trace_lines) {
        trace_lines = trace_lines.reverse();

        var traceLinesEl = document.createElement("div");

        for (var tindex in trace_lines) {
            var titem = trace_lines[tindex];
            var nxtLineEl = document.createElement("pre");
            nxtLineEl.innerHTML = titem;

            traceLinesEl.appendChild(nxtLineEl);
        }

        return traceLinesEl;
    }
}

class TestSummaryArtifacts extends HTMLElement {

    static tagname = 'testsummary-artifacts'

    static template = `
        <div class="ts-artifacts-card">
            <div class="ts-section-header">
                <h2 class="zero-margins-and-padding">Artifacts</h2>
            </div>
            <div class="ts-section-detail">
                <mojo-tabset id="id-artifacts-tabset"></mojo-tabset>
            </div>
        </div>
    `

    sel_tabset = "#id-artifacts-tabset"

    constructor() {
        super();

        const shadowRoot = this.attachShadow({ mode: 'open' })
        shadowRoot.innerHTML = this.getTemplate();

        addGlobalStylesToShadowRoot(shadowRoot);
    }

    getTemplate() {
        return TestSummaryArtifacts.template;
    }

    syncData(artifacts_catalog, artifacts_folder_catalogs) {

        if ((artifacts_catalog != undefined) && (artifacts_catalog.folders != undefined)) {

            var artifacts_folders = artifacts_catalog.folders;

            var tabsList = [];

            for (var findex in artifacts_folders) {
                var afolder = artifacts_folders[findex];
                var afolder_catalog = artifacts_folder_catalogs[afolder];

                if (afolder_catalog != undefined) {
                    if (afolder_catalog["files"] != undefined) {
                        if (afolder_catalog["files"].includes("tab.html")) {
                            var tabURL = "artifacts/" + afolder + "/tab.html";

                            var iframeEl = document.createElement("iframe");
                            iframeEl.classList.add("ts-artifact-tab-iframe");
                            iframeEl.setAttribute("src", tabURL);
                            iframeEl.setAttribute("title", afolder);

                            var tab = new MojoTabPage(afolder, afolder, iframeEl);
                            tabsList.push(tab);
                        }
                    }
                }
            }

            var tabsetEl = this.shadowRoot.querySelector(this.sel_tabset);
            tabsetEl.syncData(tabsList);

        }

    }
}


class TestSummaryImportFailures extends HTMLElement {

    static tagname = 'testsummary-importfailures'

    static template = `
        <div class="ts-importfailures-card">
            <div class="ts-section-header">
                <h2 class="zero-margins-and-padding">Import Failures</h2>
            </div>
            <div class="ts-section-detail">
                <div id="id-import-failures-list">

                </div>
            </div>
        </div>
    `

    sel_import_failures_list = "#id-import-failures-list"

    constructor() {
        super();

        const shadowRoot = this.attachShadow({ mode: 'open' })
        shadowRoot.innerHTML = this.getTemplate();

        addGlobalStylesToShadowRoot(shadowRoot);
    }

    getTemplate() {
        return TestSummaryImportFailures.template;
    }

    syncData(importFailures) {
        var failuresListEl = this.shadowRoot.querySelector(this.sel_import_failures_list);
        failuresListEl.innerHTML = "";

        for (var idx in importFailures) {
            var failItem = importFailures[idx];

            var failItemEl = document.createElement(TestSummaryImportFailureItem.tagname);
            failItemEl.syncData(failItem);

            failuresListEl.appendChild(failItemEl);
        }
    }
}


class TestSummaryFilesAndFolders extends HTMLElement {

    static tagname = 'testsummary-filesandfolders'

    static template = `
        <div class="ts-filesandfolders-card">
            <div class="ts-section-header">
                <h2 class="zero-margins-and-padding">Files and Folders</h2>
            </div>
            <div class="ts-section-detail">
                <h2>Folders</h2>
                <div id="id-folders-list">
                </div>
                <br></br>
                <h2>Files</h2>
                <div id="id-files-list">
                </div>
            </div>
        </div>
    `

    sel_files = "#id-files-list"
    sel_folders = "#id-folders-list"

    constructor() {
        super();

        const shadowRoot = this.attachShadow({ mode: 'open' })
        shadowRoot.innerHTML = this.getTemplate();

        addGlobalStylesToShadowRoot(shadowRoot);
    }

    getTemplate() {
        return TestSummaryFilesAndFolders.template;
    }

    createFileElement(label, path) {
        var fileEl = document.createElement("div");
        fileEl.innerHTML = "<icon-file class='ts-file-icon'></icon-file><a href='" + path + "'>" + label + "</a>";
        return fileEl;
    }

    createFolderElement(label, path) {
        var folderEl = document.createElement("div");
        folderEl.innerHTML = "<icon-folder class='ts-folder-icon'></icon-folder><a href='" + path + "'>" + label + "</a>";
        return folderEl;
    }

    syncData(files, folders) {

        var folderListEl = this.shadowRoot.querySelector(this.sel_folders);
        folderListEl.innerHTML = "";

        var folderEl = this.createFolderElement("Parent", "..");
        folderListEl.appendChild(folderEl);

        for (var idx in folders) {
            var nxt = folders[idx];

            folderEl = this.createFolderElement(nxt, nxt);
            folderListEl.appendChild(folderEl);
        }

        var fileListEl = this.shadowRoot.querySelector(this.sel_files);
        fileListEl.innerHTML = "";

        for (var idx in files) {
            var nxt = files[idx];

            var fileEl = this.createFolderElement(nxt, nxt);
            fileListEl.appendChild(fileEl);
        }
    }

}


/**
 * Registers all TestSummary components with the customElements registry.
 * Also registers Mojo base components as a dependency.
 * Should be called before using any TestSummary components.
 * 
 * @function register_testsummary_components
 * @returns {void}
 * 
 * @example
 * // Register components on page load
 * register_testsummary_components();
 */
function register_testsummary_components() {

    register_mojo_components()

    customElements.define(TestSummaryArtifacts.tagname, TestSummaryArtifacts);
    customElements.define(TestSummaryBanner.tagname, TestSummaryBanner);
    customElements.define(TestSummaryConfiguration.tagname, TestSummaryConfiguration);
    customElements.define(TestSummaryConfigurationEnvironment.tagname, TestSummaryConfigurationEnvironment);
    customElements.define(TestSummaryConfigurationLandscape.tagname, TestSummaryConfigurationLandscape);
    customElements.define(TestSummaryConfigurationPackages.tagname, TestSummaryConfigurationPackages);
    customElements.define(TestSummaryDataProfileObject.tagname, TestSummaryDataProfileObject);
    customElements.define(TestSummaryDeviceGroup.tagname, TestSummaryDeviceGroup);
    customElements.define(TestSummaryDeviceObject.tagname, TestSummaryDeviceObject);
    customElements.define(TestSummaryErrorsCollapsible.tagname, TestSummaryErrorsCollapsible);
    customElements.define(TestSummaryExceptionTrace.tagname, TestSummaryExceptionTrace);
    customElements.define(TestSummaryFailuresCollapsible.tagname, TestSummaryFailuresCollapsible);
    customElements.define(TestSummaryFilesAndFolders.tagname, TestSummaryFilesAndFolders);
    customElements.define(TestSummaryImportFailures.tagname, TestSummaryImportFailures);
    customElements.define(TestSummaryImportFailureItem.tagname, TestSummaryImportFailureItem);
    customElements.define(TestSummaryImportFailureTrace.tagname, TestSummaryImportFailureTrace);
    customElements.define(TestSummaryTaskGroup.tagname, TestSummaryTaskGroup);
    customElements.define(TestSummaryTaskResult.tagname, TestSummaryTaskResult);
    customElements.define(TestSummaryCheckGroup.tagname, TestSummaryCheckGroup);
    customElements.define(TestSummaryCheckResult.tagname, TestSummaryCheckResult);
    customElements.define(TestSummaryPropertyMetadata.tagname, TestSummaryPropertyMetadata);
    customElements.define(TestSummaryResultGroup.tagname, TestSummaryResultGroup);
    customElements.define(TestSummaryResultItem.tagname, TestSummaryResultItem);
    customElements.define(TestSummaryResultDetail.tagname, TestSummaryResultDetail);
    customElements.define(TestSummaryServiceObject.tagname, TestSummaryServiceObject);
}
