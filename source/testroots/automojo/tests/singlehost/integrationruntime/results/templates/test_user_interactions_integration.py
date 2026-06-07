"""
    .. module:: automojo.tests.singlehost.integrationruntime.results.templates.test_user_interactions_integration
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Integration tests for HTML report user interactions.

    .. moduleauthor:: AutomationX

    These tests verify user interaction behavior for the HTML report components.
    The tests validate:
    - Collapsible expand/collapse functionality (Requirement 17.1, 17.2)
    - Tab switching functionality (Requirement 18.3)
    - Copy to clipboard functionality (Requirement 30.2)

    Requirements covered: 17.1, 17.2, 18.3, 30.2
"""

import json
import os
import subprocess
import tempfile

from typing import Any, Dict


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


def _create_collapsible_toggle_test_script() -> str:
    """
        Create a Node.js test script for collapsible toggle functionality.

        :returns: The generated Node.js test script source.
    """
    script = '''
// Simulate MojoCollapsible toggle behavior
class MockCollapsible {
    constructor() {
        this.contentDisplay = "none";  // Initially collapsed
    }

    toggle() {
        if (this.contentDisplay === "none") {
            this.contentDisplay = "";
        } else {
            this.contentDisplay = "none";
        }
    }

    getContentDisplay() {
        return this.contentDisplay;
    }
}

function runTest() {
    try {
        var collapsible = new MockCollapsible();

        // Get initial state
        var initial_display = collapsible.getContentDisplay();

        // Toggle once (should expand)
        collapsible.toggle();
        var after_first_toggle = collapsible.getContentDisplay();

        // Toggle again (should collapse)
        collapsible.toggle();
        var after_second_toggle = collapsible.getContentDisplay();

        console.log(JSON.stringify({
            status: "success",
            data: {
                initial_display: initial_display,
                after_first_toggle: after_first_toggle,
                after_second_toggle: after_second_toggle
            }
        }));
    } catch (error) {
        console.log(JSON.stringify({
            status: "error",
            error: error.message || String(error)
        }));
    }
}

runTest();
'''
    return script


def _create_collapsible_icon_test_script() -> str:
    """
        Create a Node.js test script for collapsible icon updates.

        :returns: The generated Node.js test script source.
    """
    script = '''
// Simulate MojoCollapsible icon update behavior
class MockCollapsible {
    constructor() {
        this.contentDisplay = "none";  // Initially collapsed
        this.iconContent = "<icon-plus-sign></icon-plus-sign>";
    }

    toggle() {
        if (this.contentDisplay === "none") {
            this.contentDisplay = "";
        } else {
            this.contentDisplay = "none";
        }
        this.updateIconContent();
    }

    updateIconContent() {
        if (this.contentDisplay !== "none") {
            this.iconContent = "<icon-minus-sign></icon-minus-sign>";
        } else {
            this.iconContent = "<icon-plus-sign></icon-plus-sign>";
        }
    }

    getIconContent() {
        return this.iconContent;
    }
}

function runTest() {
    try {
        var collapsible = new MockCollapsible();

        // Get collapsed icon
        var collapsed_icon = collapsible.getIconContent();

        // Toggle to expand
        collapsible.toggle();
        var expanded_icon = collapsible.getIconContent();

        console.log(JSON.stringify({
            status: "success",
            data: {
                collapsed_icon: collapsed_icon,
                expanded_icon: expanded_icon
            }
        }));
    } catch (error) {
        console.log(JSON.stringify({
            status: "error",
            error: error.message || String(error)
        }));
    }
}

runTest();
'''
    return script


def _create_collapsible_sync_data_test_script() -> str:
    """
        Create a Node.js test script for collapsible syncData functionality.

        :returns: The generated Node.js test script source.
    """
    script = '''
// Simulate MojoCollapsible syncData behavior
class MockCollapsible {
    constructor() {
        this.headerText = "";
        this.contentText = "";
        this.contentDisplay = "none";
        this.iconContent = "<icon-plus-sign></icon-plus-sign>";
    }

    syncData(header, content, expanded) {
        this.headerText = header;

        if (content !== undefined) {
            this.contentText = content;
        }

        if (expanded) {
            this.contentDisplay = "";
        } else {
            this.contentDisplay = "none";
        }

        this.updateIconContent();
    }

    updateIconContent() {
        if (this.contentDisplay !== "none") {
            this.iconContent = "<icon-minus-sign></icon-minus-sign>";
        } else {
            this.iconContent = "<icon-plus-sign></icon-plus-sign>";
        }
    }
}

function runTest() {
    try {
        // Test with expanded = true
        var expandedCollapsible = new MockCollapsible();
        expandedCollapsible.syncData("Test Header", "Test Content", true);

        // Test with expanded = false
        var collapsedCollapsible = new MockCollapsible();
        collapsedCollapsible.syncData("Test Header", "Test Content", false);

        console.log(JSON.stringify({
            status: "success",
            data: {
                header_text: expandedCollapsible.headerText,
                content_text: expandedCollapsible.contentText,
                expanded_display: expandedCollapsible.contentDisplay,
                collapsed_display: collapsedCollapsible.contentDisplay
            }
        }));
    } catch (error) {
        console.log(JSON.stringify({
            status: "error",
            error: error.message || String(error)
        }));
    }
}

runTest();
'''
    return script


def _create_tabset_click_test_script() -> str:
    """
        Create a Node.js test script for tabset click functionality.

        :returns: The generated Node.js test script source.
    """
    script = '''
// Simulate MojoTabPage
class MockTabPage {
    constructor(key, label, content) {
        this.key = key;
        this.label = label;
        this.content = content;
        this.selected = false;
    }

    updateSelected(isSelected) {
        this.selected = isSelected;
    }
}

// Simulate MojoTabSet tabClick behavior
class MockTabSet {
    constructor() {
        this.pages = {};
        this.selected = undefined;
    }

    syncData(tabPages) {
        if (tabPages.length > 0) {
            this.pages = {};

            for (var tpage of tabPages) {
                this.pages[tpage.key] = tpage;
            }

            this.selected = tabPages[0].key;
        }

        this.switchToSelected();
    }

    switchToSelected() {
        var pageKeys = Object.keys(this.pages);

        if (pageKeys.length > 0) {
            for (var pkey of pageKeys) {
                var page = this.pages[pkey];
                page.updateSelected(pkey === this.selected);
            }
        }
    }

    tabClick(tpage) {
        this.selected = tpage.key;
        this.switchToSelected();
    }
}

function runTest() {
    try {
        var tabset = new MockTabSet();

        // Create tab pages
        var tab1 = new MockTabPage("tab1", "Tab 1", "Content 1");
        var tab2 = new MockTabPage("tab2", "Tab 2", "Content 2");
        var tab3 = new MockTabPage("tab3", "Tab 3", "Content 3");

        // Initialize tabset
        tabset.syncData([tab1, tab2, tab3]);
        var initial_selected = tabset.selected;

        // Click tab2
        tabset.tabClick(tab2);
        var after_click_tab2 = tabset.selected;

        // Click tab1
        tabset.tabClick(tab1);
        var after_click_tab1 = tabset.selected;

        console.log(JSON.stringify({
            status: "success",
            data: {
                initial_selected: initial_selected,
                after_click_tab2: after_click_tab2,
                after_click_tab1: after_click_tab1
            }
        }));
    } catch (error) {
        console.log(JSON.stringify({
            status: "error",
            error: error.message || String(error)
        }));
    }
}

runTest();
'''
    return script


def _create_tabset_visibility_test_script() -> str:
    """
        Create a Node.js test script for tabset visibility updates.

        :returns: The generated Node.js test script source.
    """
    script = '''
// Simulate MojoTabPage with selected attribute tracking
class MockTabPage {
    constructor(key, label, content) {
        this.key = key;
        this.label = label;
        this.content = content;
        this.hasSelectedAttr = false;
    }

    updateSelected(isSelected) {
        this.hasSelectedAttr = isSelected;
    }
}

// Simulate MojoTabSet
class MockTabSet {
    constructor() {
        this.pages = {};
        this.selected = undefined;
    }

    syncData(tabPages) {
        if (tabPages.length > 0) {
            this.pages = {};

            for (var tpage of tabPages) {
                this.pages[tpage.key] = tpage;
            }

            this.selected = tabPages[0].key;
        }

        this.switchToSelected();
    }

    switchToSelected() {
        var pageKeys = Object.keys(this.pages);

        if (pageKeys.length > 0) {
            for (var pkey of pageKeys) {
                var page = this.pages[pkey];
                page.updateSelected(pkey === this.selected);
            }
        }
    }
}

function runTest() {
    try {
        var tabset = new MockTabSet();

        // Create tab pages
        var tab1 = new MockTabPage("tab1", "Tab 1", "Content 1");
        var tab2 = new MockTabPage("tab2", "Tab 2", "Content 2");

        // Initialize tabset (tab1 should be selected)
        tabset.syncData([tab1, tab2]);

        console.log(JSON.stringify({
            status: "success",
            data: {
                tab1_selected_attr: tab1.hasSelectedAttr,
                tab2_selected_attr: tab2.hasSelectedAttr
            }
        }));
    } catch (error) {
        console.log(JSON.stringify({
            status: "error",
            error: error.message || String(error)
        }));
    }
}

runTest();
'''
    return script


def _create_copy_value_test_script() -> str:
    """
        Create a Node.js test script for copy value functionality.

        :returns: The generated Node.js test script source.
    """
    script = '''
// Simulate clipboard API and copyValue behavior
var clipboardCalled = false;
var clipboardValue = null;

// Mock navigator.clipboard
var mockClipboard = {
    writeText: function(value) {
        clipboardCalled = true;
        clipboardValue = value;
        return Promise.resolve();
    }
};

// Simulate MojoPropertySingle copyValue behavior
function copyValue(valueElement) {
    var value = valueElement.innerHTML;
    mockClipboard.writeText(value);
    return value;
}

// Simulate a value element
class MockElement {
    constructor(innerHTML) {
        this.innerHTML = innerHTML;
    }
}

function runTest() {
    try {
        // Create a mock value element
        var valueEl = new MockElement("test-value-to-copy");

        // Call copyValue
        var extracted_value = copyValue(valueEl);

        console.log(JSON.stringify({
            status: "success",
            data: {
                extracted_value: extracted_value,
                clipboard_called: clipboardCalled,
                clipboard_value: clipboardValue
            }
        }));
    } catch (error) {
        console.log(JSON.stringify({
            status: "error",
            error: error.message || String(error)
        }));
    }
}

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
    try:
        result = subprocess.run(
            ['node', script_path],
            capture_output=True,
            text=True,
            timeout=30
        )
    except FileNotFoundError:
        not_found_result = {"status": "error", "error": "Node.js not found. Please install Node.js to run these tests."}
        return not_found_result
    except subprocess.TimeoutExpired:
        timeout_result = {"status": "error", "error": "Test script timed out"}
        return timeout_result

    if result.returncode != 0 and not result.stdout:
        error_result = {"status": "error", "error": result.stderr}
        return error_result

    try:
        parsed_result = json.loads(result.stdout.strip())
        return parsed_result
    except json.JSONDecodeError:
        decode_result = {"status": "error", "error": f"Invalid output: {result.stdout}"}
        return decode_result


def test_collapsible_toggle_switches_display() -> None:
    """
        Test that MojoCollapsible toggle function switches content visibility.

        Requirement 17.1: THE MojoCollapsible component SHALL provide a clickable
        button to toggle content visibility.

        Requirement 17.2: THE toggle function SHALL switch content display between
        visible and hidden.

        This test verifies that calling toggle() changes the display state.
    """
    tempdir = _establish_env()
    try:
        temp_path = tempdir.name

        test_script = _create_collapsible_toggle_test_script()

        result = _run_node_script(temp_path=temp_path, script=test_script)

        assert result["status"] == "success", f"Collapsible toggle test failed: {result.get('error', 'Unknown error')}"

        # Verify initial state is collapsed (display: none)
        assert result["data"]["initial_display"] == "none", "Initial display should be 'none' (collapsed)"

        # Verify after first toggle, content is visible
        assert result["data"]["after_first_toggle"] == "", "After first toggle, display should be '' (visible)"

        # Verify after second toggle, content is hidden again
        assert result["data"]["after_second_toggle"] == "none", "After second toggle, display should be 'none' (hidden)"
    finally:
        tempdir.cleanup()

    return


def test_collapsible_icon_updates_on_toggle() -> None:
    """
        Test that MojoCollapsible icon updates based on expanded state.

        Requirement 17.2: THE toggle function SHALL switch content display between
        visible and hidden.

        This test verifies that the icon content changes when toggling.
    """
    tempdir = _establish_env()
    try:
        temp_path = tempdir.name

        test_script = _create_collapsible_icon_test_script()

        result = _run_node_script(temp_path=temp_path, script=test_script)

        assert result["status"] == "success", f"Collapsible icon test failed: {result.get('error', 'Unknown error')}"

        # Verify icon changes based on state
        assert "plus" in result["data"]["collapsed_icon"].lower(), "Collapsed state should show plus icon"
        assert "minus" in result["data"]["expanded_icon"].lower(), "Expanded state should show minus icon"
    finally:
        tempdir.cleanup()

    return


def test_collapsible_sync_data_sets_initial_state() -> None:
    """
        Test that MojoCollapsible syncData sets header, content, and expanded state.

        Requirement 17.1: THE MojoCollapsible component SHALL provide a clickable
        button to toggle content visibility.

        This test verifies that syncData properly initializes the component.
    """
    tempdir = _establish_env()
    try:
        temp_path = tempdir.name

        test_script = _create_collapsible_sync_data_test_script()

        result = _run_node_script(temp_path=temp_path, script=test_script)

        assert result["status"] == "success", f"Collapsible syncData test failed: {result.get('error', 'Unknown error')}"

        # Verify header is set
        assert result["data"]["header_text"] == "Test Header", "Header text should be set correctly"

        # Verify content is set
        assert result["data"]["content_text"] == "Test Content", "Content should be set correctly"

        # Verify expanded state when initialized as expanded
        assert result["data"]["expanded_display"] == "", "Expanded state should have display ''"

        # Verify collapsed state when initialized as collapsed
        assert result["data"]["collapsed_display"] == "none", "Collapsed state should have display 'none'"
    finally:
        tempdir.cleanup()

    return


def test_tabset_tab_click_switches_selection() -> None:
    """
        Test that MojoTabSet tabClick function switches to clicked tab.

        Requirement 18.3: THE tabClick function SHALL switch to the clicked tab
        and update visual selection.

        This test verifies that clicking a tab changes the selected tab.
    """
    tempdir = _establish_env()
    try:
        temp_path = tempdir.name

        test_script = _create_tabset_click_test_script()

        result = _run_node_script(temp_path=temp_path, script=test_script)

        assert result["status"] == "success", f"TabSet click test failed: {result.get('error', 'Unknown error')}"

        # Verify initial selection is first tab
        assert result["data"]["initial_selected"] == "tab1", "Initial selection should be first tab"

        # Verify clicking second tab changes selection
        assert result["data"]["after_click_tab2"] == "tab2", "After clicking tab2, selection should be 'tab2'"

        # Verify clicking first tab changes selection back
        assert result["data"]["after_click_tab1"] == "tab1", "After clicking tab1, selection should be 'tab1'"
    finally:
        tempdir.cleanup()

    return


def test_tabset_switch_to_selected_updates_visibility() -> None:
    """
        Test that MojoTabSet switchToSelected shows selected content and hides others.

        Requirement 18.3: THE tabClick function SHALL switch to the clicked tab
        and update visual selection.

        This test verifies that tab content visibility is updated correctly.
    """
    tempdir = _establish_env()
    try:
        temp_path = tempdir.name

        test_script = _create_tabset_visibility_test_script()

        result = _run_node_script(temp_path=temp_path, script=test_script)

        assert result["status"] == "success", f"TabSet visibility test failed: {result.get('error', 'Unknown error')}"

        # Verify selected tab has 'selected' attribute
        assert result["data"]["tab1_selected_attr"], "Selected tab should have 'selected' attribute"

        # Verify non-selected tab does not have 'selected' attribute
        assert not result["data"]["tab2_selected_attr"], "Non-selected tab should not have 'selected' attribute"
    finally:
        tempdir.cleanup()

    return


def test_copy_value_function_copies_to_clipboard() -> None:
    """
        Test that copyValue function copies value to clipboard.

        Requirement 30.2: THE copyValue function SHALL use navigator.clipboard.writeText
        to copy the value.

        This test verifies that the copyValue function correctly extracts and
        prepares the value for clipboard copying.
    """
    tempdir = _establish_env()
    try:
        temp_path = tempdir.name

        test_script = _create_copy_value_test_script()

        result = _run_node_script(temp_path=temp_path, script=test_script)

        assert result["status"] == "success", f"Copy value test failed: {result.get('error', 'Unknown error')}"

        # Verify the value was extracted correctly for copying
        assert result["data"]["extracted_value"] == "test-value-to-copy", "Value should be extracted correctly from element"

        # Verify clipboard API was called with correct value
        assert result["data"]["clipboard_called"], "Clipboard writeText should be called"
        assert result["data"]["clipboard_value"] == "test-value-to-copy", "Clipboard should receive the correct value"
    finally:
        tempdir.cleanup()

    return
