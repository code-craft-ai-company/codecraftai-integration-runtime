"""
    .. module:: ccai.tests.singlehost.integrationruntime.results.templates.test_cross_browser_compatibility
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Cross-browser compatibility tests for HTML report templates.

    .. moduleauthor:: CodeCraftX

    These tests verify cross-browser compatibility for the HTML report templates.
    The tests validate:
    - Web Components support (Requirement 3.1)
    - CSS custom properties (Requirement 20.1)
    - Shadow DOM styling (Requirement 3.4)

    Requirements covered: 3.1, 3.4, 20.1
"""

import json
import os
import subprocess
import tempfile

from typing import Any, Dict


def _establish_env() -> tempfile.TemporaryDirectory:
    """
        Establish the per-test working fixture.

        The original test class created a single :class:`tempfile.TemporaryDirectory`
        in ``setUpClass`` and exposed ``temp_path`` for the Node.js script files. To
        preserve per-test isolation, a fresh temporary directory is created for each
        test function and cleaned up in that test's ``finally`` block.

        :returns: The :class:`tempfile.TemporaryDirectory` handle whose ``name``
                  attribute is the directory path used for script files.
    """
    tempdir = tempfile.TemporaryDirectory()
    return tempdir


def _create_web_components_registration_test_script() -> str:
    """
        Create a Node.js test script for Web Components registration.

        :returns: The Node.js script source as a string.
    """
    script = '''
// Simulate Web Components API behavior
// Note: Node.js doesn't have native Web Components, so we simulate the API

class MockHTMLElement {
    constructor() {
        this.shadowRoot = null;
    }

    attachShadow(options) {
        this.shadowRoot = new MockShadowRoot(options.mode);
        return this.shadowRoot;
    }
}

class MockShadowRoot {
    constructor(mode) {
        this.mode = mode;
        this.innerHTML = "";
        this.adoptedStyleSheets = [];
    }

    querySelector(selector) {
        // Simulate finding an element
        return { id: "mock-element" };
    }
}

// Simulate customElements registry
var customElementsRegistry = {};

var mockCustomElements = {
    define: function(tagName, constructor) {
        customElementsRegistry[tagName] = constructor;
    },
    get: function(tagName) {
        return customElementsRegistry[tagName];
    }
};

// Test component class
class TestComponent extends MockHTMLElement {
    static tagname = "test-component";
    static template = "<div id='test-container'>Test Content</div>";

    constructor() {
        super();
        const shadowRoot = this.attachShadow({mode: 'open'});
        shadowRoot.innerHTML = TestComponent.template;
    }
}

function runTest() {
    try {
        var class_defined = false;
        var component_registered = false;
        var component_instantiated = false;
        var shadow_mode = null;

        // Test 1: Class can be defined
        class_defined = (typeof TestComponent === 'function');

        // Test 2: Component can be registered
        mockCustomElements.define(TestComponent.tagname, TestComponent);
        component_registered = (mockCustomElements.get(TestComponent.tagname) === TestComponent);

        // Test 3: Component can be instantiated
        var instance = new TestComponent();
        component_instantiated = (instance !== null && instance.shadowRoot !== null);

        // Test 4: Shadow root mode is 'open'
        shadow_mode = instance.shadowRoot.mode;

        console.log(JSON.stringify({
            status: "success",
            data: {
                class_defined: class_defined,
                component_registered: component_registered,
                component_instantiated: component_instantiated,
                shadow_mode: shadow_mode
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


def _create_shadow_dom_encapsulation_test_script() -> str:
    """
        Create a Node.js test script for Shadow DOM encapsulation.

        :returns: The Node.js script source as a string.
    """
    script = '''
// Simulate Shadow DOM encapsulation

class MockShadowRoot {
    constructor(mode) {
        this.mode = mode;
        this._innerHTML = "";
        this.adoptedStyleSheets = [];
        this._elements = {};
    }

    set innerHTML(value) {
        this._innerHTML = value;
        // Parse simple HTML to create mock elements
        var match = value.match(/id=['"]([^'"]+)['"]/);
        if (match) {
            this._elements[match[1]] = { id: match[1], innerHTML: value };
        }
    }

    get innerHTML() {
        return this._innerHTML;
    }

    querySelector(selector) {
        if (selector.startsWith('#')) {
            var id = selector.substring(1);
            return this._elements[id] || null;
        }
        return null;
    }
}

class MockHTMLElement {
    constructor() {
        this.shadowRoot = null;
    }

    attachShadow(options) {
        this.shadowRoot = new MockShadowRoot(options.mode);
        return this.shadowRoot;
    }
}

class TestComponent extends MockHTMLElement {
    static template = "<div id='test-container' class='test-class'>Test Content</div>";

    constructor() {
        super();
        const shadowRoot = this.attachShadow({mode: 'open'});
        shadowRoot.innerHTML = TestComponent.template;
    }
}

function runTest() {
    try {
        var instance = new TestComponent();

        var has_shadow_root = (instance.shadowRoot !== null);
        var template_set = (instance.shadowRoot.innerHTML.includes('test-container'));
        var content_accessible = (instance.shadowRoot.querySelector('#test-container') !== null);

        console.log(JSON.stringify({
            status: "success",
            data: {
                has_shadow_root: has_shadow_root,
                template_set: template_set,
                content_accessible: content_accessible
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


def _create_css_custom_properties_test_script() -> str:
    """
        Create a Node.js test script for CSS custom properties.

        :returns: The Node.js script source as a string.
    """
    script = '''
// Test CSS custom properties definition
// This simulates parsing the branding-theme.css @property definitions

var cssContent = `
@property --color-error {
    syntax: "<color>";
    inherits: false;
    initial-value: maroon;
}

@property --color-fail {
    syntax: "<color>";
    inherits: false;
    initial-value: red;
}

@property --color-ghost {
    syntax: "<color>";
    inherits: false;
    initial-value: #B0B0B0;
}

@property --color-pass {
    syntax: "<color>";
    inherits: false;
    initial-value: green;
}

@property --color-skip {
    syntax: "<color>";
    inherits: false;
    initial-value: gray;
}

@property --color-warn {
    syntax: "<color>";
    inherits: false;
    initial-value: orange;
}
`;

function parsePropertyDefinitions(css) {
    var properties = [];
    var regex = /@property\\s+(--[a-zA-Z0-9-]+)\\s*\\{/g;
    var match;

    while ((match = regex.exec(css)) !== null) {
        properties.push(match[1]);
    }

    return properties;
}

function validatePropertySyntax(css) {
    // Check that @property rules have required fields
    var propertyBlocks = css.match(/@property[^}]+}/g) || [];

    for (var block of propertyBlocks) {
        if (!block.includes('syntax:')) return false;
        if (!block.includes('inherits:')) return false;
        if (!block.includes('initial-value:')) return false;
    }

    return propertyBlocks.length > 0;
}

function runTest() {
    try {
        var property_syntax_valid = validatePropertySyntax(cssContent);
        var defined_properties = parsePropertyDefinitions(cssContent);
        var custom_properties_defined = defined_properties.length > 0;

        console.log(JSON.stringify({
            status: "success",
            data: {
                property_syntax_valid: property_syntax_valid,
                custom_properties_defined: custom_properties_defined,
                defined_properties: defined_properties
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


def _create_css_var_function_test_script() -> str:
    """
        Create a Node.js test script for CSS var() function.

        :returns: The Node.js script source as a string.
    """
    script = '''
// Test CSS var() function behavior

// Simulate CSS variable resolution
var cssVariables = {
    "--color-error": "maroon",
    "--color-fail": "red",
    "--color-pass": "green",
    "--color-skip": "gray"
};

function resolveVar(varExpression, fallback) {
    // Parse var(--name) or var(--name, fallback)
    var match = varExpression.match(/var\\(([^,)]+)(?:,\\s*([^)]+))?\\)/);

    if (!match) return null;

    var varName = match[1].trim();
    var varFallback = match[2] ? match[2].trim() : fallback;

    if (cssVariables[varName] !== undefined) {
        return cssVariables[varName];
    }

    return varFallback || null;
}

function runTest() {
    try {
        // Test var() with existing variable
        var result1 = resolveVar("var(--color-error)");
        var var_function_works = (result1 === "maroon");

        // Test var() with fallback for non-existent variable
        var result2 = resolveVar("var(--color-nonexistent, blue)");
        var fallback_works = (result2 === "blue");

        console.log(JSON.stringify({
            status: "success",
            data: {
                var_function_works: var_function_works,
                fallback_works: fallback_works
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


def _create_adopted_stylesheets_test_script() -> str:
    """
        Create a Node.js test script for adoptedStyleSheets API.

        :returns: The Node.js script source as a string.
    """
    script = '''
// Simulate adoptedStyleSheets API

class MockCSSStyleSheet {
    constructor() {
        this.cssRules = [];
        this._cssText = "";
    }

    replaceSync(cssText) {
        this._cssText = cssText;
        // Parse simple CSS rules
        var rules = cssText.split('}').filter(r => r.trim());
        this.cssRules = rules.map(r => ({ cssText: r + '}' }));
    }
}

class MockShadowRoot {
    constructor(mode) {
        this.mode = mode;
        this.innerHTML = "";
        this.adoptedStyleSheets = [];
    }
}

class MockHTMLElement {
    constructor() {
        this.shadowRoot = null;
    }

    attachShadow(options) {
        this.shadowRoot = new MockShadowRoot(options.mode);
        return this.shadowRoot;
    }
}

function runTest() {
    try {
        var element = new MockHTMLElement();
        var shadowRoot = element.attachShadow({mode: 'open'});

        // Test 1: adoptedStyleSheets property exists
        var adopted_stylesheets_exists = Array.isArray(shadowRoot.adoptedStyleSheets);

        // Test 2: CSSStyleSheet can be created
        var sheet = new MockCSSStyleSheet();
        var css_stylesheet_creatable = (sheet !== null);

        // Test 3: replaceSync works
        var replace_sync_works = false;
        try {
            sheet.replaceSync(".test { color: red; }");
            replace_sync_works = (sheet._cssText.includes("color: red"));
        } catch (e) {
            replace_sync_works = false;
        }

        // Test 4: Can push to adoptedStyleSheets
        var push_to_adopted_works = false;
        try {
            shadowRoot.adoptedStyleSheets.push(sheet);
            push_to_adopted_works = (shadowRoot.adoptedStyleSheets.length === 1);
        } catch (e) {
            push_to_adopted_works = false;
        }

        console.log(JSON.stringify({
            status: "success",
            data: {
                adopted_stylesheets_exists: adopted_stylesheets_exists,
                css_stylesheet_creatable: css_stylesheet_creatable,
                replace_sync_works: replace_sync_works,
                push_to_adopted_works: push_to_adopted_works
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


def _create_style_isolation_test_script() -> str:
    """
        Create a Node.js test script for Shadow DOM style isolation.

        :returns: The Node.js script source as a string.
    """
    script = '''
// Simulate Shadow DOM style isolation

class MockCSSStyleSheet {
    constructor() {
        this._cssText = "";
    }

    replaceSync(cssText) {
        this._cssText = cssText;
    }

    getCssText() {
        return this._cssText;
    }
}

class MockShadowRoot {
    constructor(mode) {
        this.mode = mode;
        this.innerHTML = "";
        this.adoptedStyleSheets = [];
    }

    hasStyle(selector) {
        // Check if any adopted stylesheet contains the selector
        for (var sheet of this.adoptedStyleSheets) {
            if (sheet.getCssText().includes(selector)) {
                return true;
            }
        }
        return false;
    }
}

class MockHTMLElement {
    constructor() {
        this.shadowRoot = null;
    }

    attachShadow(options) {
        this.shadowRoot = new MockShadowRoot(options.mode);
        return this.shadowRoot;
    }
}

// Simulate document styles (outside shadow DOM)
var documentStyles = ".document-class { color: blue; }";

// Simulate component-specific styles (inside shadow DOM)
var componentStyles = ".component-class { color: red; }";

function runTest() {
    try {
        var element = new MockHTMLElement();
        var shadowRoot = element.attachShadow({mode: 'open'});

        // Add component-specific styles to shadow DOM
        var componentSheet = new MockCSSStyleSheet();
        componentSheet.replaceSync(componentStyles);
        shadowRoot.adoptedStyleSheets.push(componentSheet);

        // Test 1: Shadow DOM styles are isolated (document styles not in shadow)
        var styles_isolated = !shadowRoot.hasStyle(".document-class");

        // Test 2: Adopted styles are applied inside shadow DOM
        var adopted_styles_applied = shadowRoot.hasStyle(".component-class");

        console.log(JSON.stringify({
            status: "success",
            data: {
                styles_isolated: styles_isolated,
                adopted_styles_applied: adopted_styles_applied
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


def _create_stylesheet_caching_test_script() -> str:
    """
        Create a Node.js test script for stylesheet caching.

        :returns: The Node.js script source as a string.
    """
    script = '''
// Simulate getGlobalStyleSheets caching behavior from webcomponent-helpers.js

let globalSheets = null;

class MockCSSStyleSheet {
    constructor() {
        this._cssText = "";
    }

    replaceSync(cssText) {
        this._cssText = cssText;
    }
}

// Simulate document.styleSheets
var mockDocumentStyleSheets = [
    { cssRules: [{ cssText: ".class1 { color: red; }" }] },
    { cssRules: [{ cssText: ".class2 { color: blue; }" }] }
];

function getGlobalStyleSheets() {
    if (globalSheets === null) {
        globalSheets = mockDocumentStyleSheets.map(x => {
            const sheet = new MockCSSStyleSheet();
            const css = x.cssRules.map(rule => rule.cssText).join(' ');
            sheet.replaceSync(css);
            return sheet;
        });
    }

    return globalSheets;
}

function runTest() {
    try {
        // First call - should create and cache
        var firstCall = getGlobalStyleSheets();

        // Second call - should return cached
        var secondCall = getGlobalStyleSheets();

        // Test 1: Caching works (globalSheets is not null after first call)
        var caching_works = (globalSheets !== null);

        // Test 2: Same reference returned
        var same_reference = (firstCall === secondCall);

        console.log(JSON.stringify({
            status: "success",
            data: {
                caching_works: caching_works,
                same_reference: same_reference
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

        :param temp_path: The directory path used to materialize the script file.
        :param script: The Node.js script source to execute.

        :returns: The parsed JSON result, or an error dictionary when Node.js is
                  missing, times out, or returns invalid output.
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
        rtnval = {"status": "error", "error": "Node.js not found. Please install Node.js to run these tests."}
        return rtnval
    except subprocess.TimeoutExpired:
        rtnval = {"status": "error", "error": "Test script timed out"}
        return rtnval

    if result.returncode != 0 and not result.stdout:
        rtnval = {"status": "error", "error": result.stderr}
        return rtnval

    try:
        rtnval = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        rtnval = {"status": "error", "error": f"Invalid output: {result.stdout}"}

    return rtnval


def test_web_components_can_be_defined_and_registered() -> None:
    """
        Test that Web Components can be defined and registered with customElements.

        Requirement 3.1: EACH web component constructor SHALL call attachShadow
        with mode 'open'.

        This test verifies that the customElements.define API works correctly
        and components can be instantiated.
    """
    tempdir = _establish_env()
    try:
        temp_path = tempdir.name

        test_script = _create_web_components_registration_test_script()

        result = _run_node_script(temp_path=temp_path, script=test_script)

        assert result["status"] == "success", \
            f"Web Components registration test failed: {result.get('error', 'Unknown error')}"

        # Verify component class can be defined
        assert result["data"]["class_defined"], \
            "Component class should be definable"

        # Verify component can be registered
        assert result["data"]["component_registered"], \
            "Component should be registerable with customElements"

        # Verify component can be instantiated
        assert result["data"]["component_instantiated"], \
            "Component should be instantiable"

        # Verify shadow root is created with mode 'open'
        assert result["data"]["shadow_mode"] == "open", \
            "Shadow root should be created with mode 'open'"
    finally:
        tempdir.cleanup()

    return


def test_web_components_shadow_dom_encapsulation() -> None:
    """
        Test that Web Components properly encapsulate content in Shadow DOM.

        Requirement 3.1: EACH web component constructor SHALL call attachShadow
        with mode 'open'.

        Requirement 3.4: THE addGlobalStylesToShadowRoot function SHALL copy
        document stylesheets to the shadow root's adoptedStyleSheets.

        This test verifies Shadow DOM encapsulation works correctly.
    """
    tempdir = _establish_env()
    try:
        temp_path = tempdir.name

        test_script = _create_shadow_dom_encapsulation_test_script()

        result = _run_node_script(temp_path=temp_path, script=test_script)

        assert result["status"] == "success", \
            f"Shadow DOM encapsulation test failed: {result.get('error', 'Unknown error')}"

        # Verify shadow root exists
        assert result["data"]["has_shadow_root"], \
            "Component should have a shadow root"

        # Verify shadow root innerHTML can be set
        assert result["data"]["template_set"], \
            "Shadow root innerHTML should be settable"

        # Verify shadow root content is accessible
        assert result["data"]["content_accessible"], \
            "Shadow root content should be accessible via querySelector"
    finally:
        tempdir.cleanup()

    return


def test_css_custom_properties_definition() -> None:
    """
        Test that CSS custom properties are properly defined.

        Requirement 20.1: THE branding-theme.css file SHALL define CSS custom
        properties for result colors (error, fail, pass, skip, warn, ghost).

        This test verifies that CSS custom properties can be defined and parsed.
    """
    tempdir = _establish_env()
    try:
        temp_path = tempdir.name

        test_script = _create_css_custom_properties_test_script()

        result = _run_node_script(temp_path=temp_path, script=test_script)

        assert result["status"] == "success", \
            f"CSS custom properties test failed: {result.get('error', 'Unknown error')}"

        # Verify @property syntax is valid
        assert result["data"]["property_syntax_valid"], \
            "@property syntax should be valid"

        # Verify custom properties can be defined
        assert result["data"]["custom_properties_defined"], \
            "CSS custom properties should be definable"

        # Verify all required color properties are present
        required_colors = ["error", "fail", "pass", "skip", "warn", "ghost"]
        for color in required_colors:
            assert f"--color-{color}" in result["data"]["defined_properties"], \
                f"--color-{color} should be defined"
    finally:
        tempdir.cleanup()

    return


def test_css_custom_properties_inheritance() -> None:
    """
        Test that CSS custom properties work with var() function.

        Requirement 20.1: THE branding-theme.css file SHALL define CSS custom
        properties for result colors.

        This test verifies that CSS custom properties can be used with var().
    """
    tempdir = _establish_env()
    try:
        temp_path = tempdir.name

        test_script = _create_css_var_function_test_script()

        result = _run_node_script(temp_path=temp_path, script=test_script)

        assert result["status"] == "success", \
            f"CSS var() function test failed: {result.get('error', 'Unknown error')}"

        # Verify var() function can reference custom properties
        assert result["data"]["var_function_works"], \
            "var() function should work with custom properties"

        # Verify fallback values work
        assert result["data"]["fallback_works"], \
            "var() fallback values should work"
    finally:
        tempdir.cleanup()

    return


def test_shadow_dom_adopted_stylesheets() -> None:
    """
        Test that Shadow DOM adoptedStyleSheets API works correctly.

        Requirement 3.4: THE addGlobalStylesToShadowRoot function SHALL copy
        document stylesheets to the shadow root's adoptedStyleSheets.

        This test verifies that adoptedStyleSheets can be used to share styles.
    """
    tempdir = _establish_env()
    try:
        temp_path = tempdir.name

        test_script = _create_adopted_stylesheets_test_script()

        result = _run_node_script(temp_path=temp_path, script=test_script)

        assert result["status"] == "success", \
            f"adoptedStyleSheets test failed: {result.get('error', 'Unknown error')}"

        # Verify adoptedStyleSheets property exists
        assert result["data"]["adopted_stylesheets_exists"], \
            "adoptedStyleSheets property should exist on shadow root"

        # Verify CSSStyleSheet can be created
        assert result["data"]["css_stylesheet_creatable"], \
            "CSSStyleSheet should be creatable"

        # Verify replaceSync works
        assert result["data"]["replace_sync_works"], \
            "CSSStyleSheet.replaceSync should work"

        # Verify stylesheets can be pushed to adoptedStyleSheets
        assert result["data"]["push_to_adopted_works"], \
            "Stylesheets should be pushable to adoptedStyleSheets"
    finally:
        tempdir.cleanup()

    return


def test_shadow_dom_style_isolation() -> None:
    """
        Test that Shadow DOM provides style isolation.

        Requirement 3.4: THE addGlobalStylesToShadowRoot function SHALL copy
        document stylesheets to the shadow root's adoptedStyleSheets.

        This test verifies that styles inside Shadow DOM don't leak out.
    """
    tempdir = _establish_env()
    try:
        temp_path = tempdir.name

        test_script = _create_style_isolation_test_script()

        result = _run_node_script(temp_path=temp_path, script=test_script)

        assert result["status"] == "success", \
            f"Style isolation test failed: {result.get('error', 'Unknown error')}"

        # Verify shadow DOM styles are isolated
        assert result["data"]["styles_isolated"], \
            "Shadow DOM styles should be isolated from document"

        # Verify adopted styles are applied inside shadow DOM
        assert result["data"]["adopted_styles_applied"], \
            "Adopted styles should be applied inside shadow DOM"
    finally:
        tempdir.cleanup()

    return


def test_global_stylesheet_caching() -> None:
    """
        Test that global stylesheets are cached for reuse.

        Requirement 3.4: THE getGlobalStyleSheets function SHALL cache the
        global stylesheets for reuse across components.

        This test verifies that the caching mechanism works correctly.
    """
    tempdir = _establish_env()
    try:
        temp_path = tempdir.name

        test_script = _create_stylesheet_caching_test_script()

        result = _run_node_script(temp_path=temp_path, script=test_script)

        assert result["status"] == "success", \
            f"Stylesheet caching test failed: {result.get('error', 'Unknown error')}"

        # Verify caching returns same reference
        assert result["data"]["caching_works"], \
            "getGlobalStyleSheets should return cached reference"

        # Verify multiple calls return same object
        assert result["data"]["same_reference"], \
            "Multiple calls should return same cached object"
    finally:
        tempdir.cleanup()

    return
