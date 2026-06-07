/*
    Author: "Myron Walker"
    Copyright: "Copyright 2024, Myron W Walker"
    Version: = "2.0.0"
    Email: myron.walker@gmail.com
*/

/**
 * @fileoverview Base UI components for the Mojo component library.
 * Provides reusable web components including collapsible panels, property displays,
 * tab sets, and icon targets.
 * @module mojo-components
 */

/**
 * Flag indicating whether Mojo components have been registered with customElements.
 * @type {boolean}
 * @private
 */
let mojoComponentsRegistered = false;

/**
 * A clickable icon target component with tooltip support.
 * Provides visual feedback on mouse interactions and optional tooltip display.
 * 
 * @class MojoIconTarget
 * @extends HTMLElement
 * 
 * @example
 * <mojo-icon-target tooltip="Click me">
 *   <icon-settings></icon-settings>
 * </mojo-icon-target>
 */
class MojoIconTarget extends HTMLElement {
    static tagname = 'mojo-icon-target'

    static template = `
        <div id="id-icon-target" class="mojo-icon-target">
            <icon-question-mark></icon-question-mark>
        </div>
    `

    sel_container = "#id-icon-target"
    sel_tooltip = "#id-tooltip"

    static observedAttributes = ["tooltip"];

    constructor() {
        super();

        const shadowRoot = this.attachShadow({mode: 'open'})
        shadowRoot.innerHTML = this.getTemplate();
        if (this.classList.length > 0) {
            shadowRoot.classList = this.classList;
        }

        addGlobalStylesToShadowRoot(shadowRoot);

        var containerEl =  this.shadowRoot.querySelector(this.sel_container);

        var tooltip = this.getAttribute("tooltip");
        if (tooltip != undefined) {
            this.update_tooltip(containerEl, tooltip);
        }
        
        if (this.innerHTML.trim().length > 0) {
            containerEl.innerHTML = this.innerHTML;    
        }

        var thisComp = this;

        containerEl.addEventListener("mousedown", (event) => { thisComp.mouse_down(event) });
        containerEl.addEventListener("mouseleave", (event) => { thisComp.mouse_leave(event) });
        containerEl.addEventListener("mouseup", (event) => { thisComp.mouse_up(event) });
    }

    attributeChangedCallback(name, oldValue, newValue) {
        if (name == "tooltip") {
            var containerEl =  this.shadowRoot.querySelector(this.sel_container);

            this.update_tooltip(containerEl, newValue);
        }
    }

    /**
     * Gets the HTML template for this component.
     * @returns {string} The HTML template string.
     */
    getTemplate() {
        return MojoIconTarget.template;
    }

    /**
     * Handles mouse down event by inverting fill and background colors.
     * @param {MouseEvent} event - The mouse down event.
     */
    mouse_down(event) {
        var thisStyle = getComputedStyle(this);

        var fillColor = thisStyle.getPropertyValue("fill");
        var backgroundColor = thisStyle.getPropertyValue("background-color");

        var containerEl =  this.shadowRoot.querySelector(this.sel_container);

        containerEl.style.fill = backgroundColor;
        containerEl.style.backgroundColor = fillColor;
    }

    /**
     * Handles mouse leave event by resetting colors.
     * @param {MouseEvent} event - The mouse leave event.
     */
    mouse_leave(event) {
        var containerEl =  this.shadowRoot.querySelector(this.sel_container);

        containerEl.style.fill = "";
        containerEl.style.backgroundColor = "";
    }

    /**
     * Handles mouse up event by resetting colors.
     * @param {MouseEvent} event - The mouse up event.
     */
    mouse_up(event) {
        var containerEl =  this.shadowRoot.querySelector(this.sel_container);

        containerEl.style.fill = "";
        containerEl.style.backgroundColor = "";
    }

    /**
     * Updates the tooltip content for the icon target.
     * @param {HTMLElement} containerEl - The container element.
     * @param {string} tooltip - The tooltip text to display.
     */
    update_tooltip(containerEl, tooltip) {

        var ttEl = containerEl.querySelector(this.sel_tooltip);

        if (tooltip.trim().length == 0) {
            containerEl.classList.remove("mojo-tooltip");

            if (ttEl != undefined) {
                containerEl.removeChild(ttEl);
            }
        } else {
            if (ttEl == undefined) {
                ttEl = document.createElement("span");

                ttEl.setAttribute("id", "id-tooltip");
                ttEl.classList.add("mojo-tooltip-text");

                containerEl.appendChild(ttEl);
            }

            containerEl.classList.add("mojo-tooltip");
            ttEl.innerHTML = tooltip;
        }
    
    }

}


/**
 * A collapsible panel component that can expand/collapse content.
 * Provides a clickable header button that toggles content visibility.
 * 
 * @class MojoCollapsible
 * @extends HTMLElement
 * 
 * @example
 * const collapsible = document.createElement('mojo-collapsible');
 * collapsible.syncData('Section Title', contentElement, false);
 */
class MojoCollapsible extends HTMLElement {

    static tagname = 'mojo-collapsible'

    static template = `
        <div id="id-collapsible-container" class="mojo-collapsible" >
            <div id="id-collapsible-button" class="mojo-collapsible-button" role="button" tabindex="0" aria-expanded="false">
                <div id="id-header-text" class="mojo-collapsible-header"></div>
                <div id="id-header-icon" class="mojo-collapsible-icon" aria-hidden="true">+</div>
            </div>
            <div id="id-collapsible-content" class="mojo-collapsible-content" role="region">
            </div>
        </div>
    `

    // CSS selectors for accessing Shadow DOM elements
    sel_container = "#id-collapsible-container"
    sel_button = "#id-collapsible-button"
    sel_header_text = "#id-header-text"
    sel_header_icon = "#id-header-icon"
    sel_content = "#id-collapsible-content"

    // =========================================================================
    // COMPONENT LIFECYCLE - Constructor Phase
    // =========================================================================
    // The constructor is called when the element is created (either via
    // document.createElement() or when the HTML parser encounters the tag).
    // This is the initialization phase where we set up the Shadow DOM.
    constructor() {
        // LIFECYCLE STEP 1: Call parent constructor (required for custom elements)
        super();

        // LIFECYCLE STEP 2: Attach Shadow DOM
        // =====================================================================
        // Shadow DOM provides encapsulation for the component's internal DOM
        // structure and styles. Using mode: 'open' allows external JavaScript
        // to access the shadow root via element.shadowRoot (useful for testing
        // and debugging). Mode: 'closed' would hide it completely.
        const shadowRoot = this.attachShadow({mode: 'open'})
        
        // LIFECYCLE STEP 3: Populate Shadow DOM with template
        // =====================================================================
        // Set the shadow root's innerHTML to the component's HTML template.
        // This creates the internal DOM structure that will be rendered.
        shadowRoot.innerHTML = this.getTemplate();

        // LIFECYCLE STEP 4: Adopt global styles
        // =====================================================================
        // Copy document-level stylesheets into the Shadow DOM so that global
        // CSS custom properties (theming variables) and shared styles are
        // available within the encapsulated component.
        addGlobalStylesToShadowRoot(shadowRoot);

        // LIFECYCLE STEP 5: Set up event listeners
        // =====================================================================
        // Query the Shadow DOM for interactive elements and attach event
        // handlers. This must happen after the template is rendered.
        var buttonEl =  this.shadowRoot.querySelector(this.sel_button)
        var thisComp = this;

        // Use arrow function to preserve 'this' context in the event handler
        buttonEl.addEventListener("click", (event) => { thisComp.toggle(event) });
        
        // LIFECYCLE STEP 6: Set up keyboard navigation for accessibility
        // =====================================================================
        buttonEl.addEventListener("keydown", (event) => { thisComp.handleKeydown(event) });
        
        // Generate unique IDs for ARIA relationships
        this._buttonId = 'collapsible-btn-' + Math.random().toString(36).substr(2, 9);
        this._contentId = 'collapsible-content-' + Math.random().toString(36).substr(2, 9);
        buttonEl.setAttribute('id', this._buttonId);
        buttonEl.setAttribute('aria-controls', this._contentId);
        
        var contentEl = this.shadowRoot.querySelector(this.sel_content);
        contentEl.setAttribute('id', this._contentId);
        contentEl.setAttribute('aria-labelledby', this._buttonId);
    }

    /**
     * Gets the HTML template for this component.
     * @returns {string} The HTML template string.
     */
    getTemplate() {
        return MojoCollapsible.template;
    }

    /**
     * Handles keyboard events for accessibility.
     * @param {KeyboardEvent} event - The keyboard event.
     */
    handleKeydown(event) {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            this.toggle(event);
        }
    }

    // =========================================================================
    // COMPONENT LIFECYCLE - Data Synchronization Phase
    // =========================================================================
    // syncData() is the primary method for updating component state with new
    // data. Unlike React's props or Angular's inputs, Web Components don't
    // have built-in data binding, so we use this explicit method pattern.
    /**
     * Synchronizes the component with data.
     * Sets the header text, content, and initial expanded state.
     * 
     * @param {string} header - The header text to display.
     * @param {HTMLElement|string|undefined} content - The content to display (element, HTML string, or undefined to keep existing).
     * @param {boolean} expanded - Whether the panel should be initially expanded.
     */
    syncData(header, content, expanded) {
        // DATA SYNC STEP 1: Update header text
        // =====================================================================
        // Query the Shadow DOM for the header element and update its content.
        // Using innerHTML allows HTML formatting in the header if needed.
        var headerTextEl =  this.shadowRoot.querySelector(this.sel_header_text);
        headerTextEl.innerHTML = header;

        // DATA SYNC STEP 2: Update content area
        // =====================================================================
        // The content parameter can be:
        //   - HTMLElement: Append directly to the content container
        //   - String: Set as innerHTML (allows HTML markup)
        //   - undefined: Keep existing content unchanged
        var contentEl =  this.shadowRoot.querySelector(this.sel_content);

        if (content != undefined) {
            // Clear existing content before adding new content
            contentEl.innerHTML = "";

            if (content instanceof HTMLElement) {
                // Append DOM element directly (preserves event handlers)
                contentEl.appendChild(content);
            } else {
                // Set as HTML string (creates new DOM nodes)
                contentEl.innerHTML = content;
            }
        }

        // DATA SYNC STEP 3: Set initial expanded/collapsed state
        // =====================================================================
        // Control visibility using CSS display property.
        // Empty string ("") uses the element's default display value.
        if (expanded) {
            contentEl.style.display = "";
        } else {
            contentEl.style.display = "none";
        }

        // DATA SYNC STEP 4: Update visual indicator and ARIA state
        // =====================================================================
        // Sync the expand/collapse icon with the current state.
        this.updateIconContent(contentEl);
        this.updateAriaState(contentEl);
    }

    /**
     * Toggles the visibility of the collapsible content.
     * @param {Event} event - The click event.
     */
    toggle (event) {
        // Toggle content visibility by switching display property
        var contentEl =  this.shadowRoot.querySelector(this.sel_content);

        if (contentEl.style.display == "none") {
            contentEl.style.display = "";
        } else {
            contentEl.style.display = "none";
        }

        // Update icon to reflect new state
        this.updateIconContent(contentEl);
        // Update ARIA state for accessibility
        this.updateAriaState(contentEl);
        
        // Announce state change to screen readers if function is available
        if (typeof updateCollapsibleAriaState === 'function') {
            var buttonEl = this.shadowRoot.querySelector(this.sel_button);
            updateCollapsibleAriaState(buttonEl, contentEl.style.display !== "none");
        }
    }

    /**
     * Updates the icon content based on the expanded/collapsed state.
     * Shows minus sign when expanded, plus sign when collapsed.
     * @param {HTMLElement} contentEl - The content element to check visibility of.
     */
    updateIconContent (contentEl) {
        var iconEl = this.shadowRoot.querySelector(this.sel_header_icon);

        // Use icon components for visual consistency
        if (contentEl.style.display != "none") {
            iconEl.innerHTML = "<icon-minus-sign></icon-minus-sign>";
        } else {
            iconEl.innerHTML = "<icon-plus-sign></icon-plus-sign>";
        }
    }
    
    /**
     * Updates ARIA attributes based on the expanded/collapsed state.
     * @param {HTMLElement} contentEl - The content element to check visibility of.
     */
    updateAriaState(contentEl) {
        var buttonEl = this.shadowRoot.querySelector(this.sel_button);
        var isExpanded = contentEl.style.display !== "none";
        buttonEl.setAttribute('aria-expanded', isExpanded);
    }

}

/**
 * A level 2 nested collapsible panel with different styling.
 * Extends MojoCollapsible with a different template for nested use.
 * 
 * @class MojoCollapsibleLvl2
 * @extends MojoCollapsible
 */
class MojoCollapsibleLvl2 extends MojoCollapsible {

    static tagname = 'mojo-collapsible-lvl2'

    static template = `
        <div id="id-collapsible-container" class="mojo-collapsible-lvl2" >
            <div id="id-collapsible-button" class="mojo-collapsible-lvl2-button" role="button" tabindex="0" aria-expanded="false">
                <div id="id-header-text" class="mojo-collapsible-lvl2-header"></div>
                <div id="id-header-icon" class="mojo-collapsible-lvl2-icon" aria-hidden="true">+</div>
            </div>
            <div id="id-collapsible-content" class="mojo-collapsible-lvl2-content" role="region">
            </div>
        </div>
    `

    constructor() {
        super();
    }

    /**
     * Gets the HTML template for this component.
     * @returns {string} The HTML template string.
     */
    getTemplate() {
        return MojoCollapsibleLvl2.template;
    }

}

/**
 * A level 3 nested collapsible panel with different styling.
 * Extends MojoCollapsible with a different template for deeply nested use.
 * 
 * @class MojoCollapsibleLvl3
 * @extends MojoCollapsible
 */
class MojoCollapsibleLvl3 extends MojoCollapsible {

    static tagname = 'mojo-collapsible-lvl3'

    static template = `
        <div id="id-collapsible-container" class="mojo-collapsible-lvl3" >
            <div id="id-collapsible-button" class="mojo-collapsible-lvl3-button" role="button" tabindex="0" aria-expanded="false">
                <div id="id-header-text" class="mojo-collapsible-lvl3-header"></div>
                <div id="id-header-icon" class="mojo-collapsible-lvl3-icon" aria-hidden="true">+</div>
            </div>
            <div id="id-collapsible-content" class="mojo-collapsible-lvl3-content" role="region">
            </div>
        </div>
    `

    constructor() {
        super();
    }

    /**
     * Gets the HTML template for this component.
     * @returns {string} The HTML template string.
     */
    getTemplate() {
        return MojoCollapsibleLvl3.template;
    }

}


/**
 * A project timeline component (placeholder for future implementation).
 * 
 * @class MojoProjectTimeline
 * @extends HTMLElement
 */
class MojoProjectTimeline extends HTMLElement {

    static tagname = "mojo-project-timeline"

    static template = `
        <div class="mojo-project-timeline">
        </div>
    `

    constructor() {
        super();

        const shadowRoot = this.attachShadow({mode: 'open'});
        shadowRoot.innerHTML = this.getTemplate();

        addGlobalStylesToShadowRoot(shadowRoot);

        var thisComp = this;

        copyEl.addEventListener("mousedown", (event) => { thisComp.mouse_down(event) });
        copyEl.addEventListener("mouseleave", (event) => { thisComp.mouse_leave(event) });
        copyEl.addEventListener("mouseup", (event) => { thisComp.mouse_up(event) });
    }

    /**
     * Gets the HTML template for this component.
     * @returns {string} The HTML template string.
     */
    getTemplate() {
        return MojoProjectTimeline.template;
    }

    /**
     * Handles mouse down event (placeholder).
     * @param {MouseEvent} event - The mouse down event.
     */
    mouse_down(event) {
        
    }

    /**
     * Handles mouse leave event (placeholder).
     * @param {MouseEvent} event - The mouse leave event.
     */
    mouse_leave(event) {
        
    }

    /**
     * Handles mouse up event (placeholder).
     * @param {MouseEvent} event - The mouse up event.
     */
    mouse_up(event) {
        
    }

    /**
     * Synchronizes the component with project information (placeholder).
     * @param {Object} projectInfo - The project information object.
     */
    syncData(projectInfo) {
        
    }

}


/**
 * A component for displaying a single property with label, value, and copy button.
 * Provides clipboard copy functionality for the property value.
 * 
 * @class MojoPropertySingle
 * @extends HTMLElement
 * 
 * @example
 * const prop = document.createElement('mojo-property-single');
 * prop.syncData('API Key', 'abc123xyz');
 */
class MojoPropertySingle extends HTMLElement {

    static tagname = "mojo-property-single"

    static template = `
        <div id="id-property-single-container" class="mojo-prop-single">
            <div id="id-property-single-label" class="mojo-prop-single-label"></div>
            <div id="id-property-single-value" class="mojo-prop-single-value"></div>
            <button id="id-property-single-copy" class="mojo-prop-single-copy" type="button" aria-label="Copy value to clipboard" title="Copy to clipboard"><icon-copy aria-hidden="true"></icon-copy></button>
        </div>
    `

    default_classes_container = ["mojo-prop-single"]
    default_classes_copy = ["mojo-prop-single-copy"]
    default_classes_label = ["mojo-prop-single-label"]
    default_classes_value = ["mojo-prop-single-value"]

    sel_copy = "#id-property-single-copy"
    sel_label = "#id-property-single-label"
    sel_value = "#id-property-single-value"

    constructor() {
        super();

        const shadowRoot = this.attachShadow({mode: 'open'});
        shadowRoot.innerHTML = this.getTemplate();

        addGlobalStylesToShadowRoot(shadowRoot);

        var copyEl = this.shadowRoot.querySelector(this.sel_copy);
        var valueEl = this.shadowRoot.querySelector(this.sel_value);
        
        var thisComp = this;
        copyEl.onclick = function(e) { thisComp.copyValue(valueEl, e) };

        copyEl.addEventListener("mousedown", (event) => { thisComp.mouse_down(event, copyEl) });
        copyEl.addEventListener("mouseleave", (event) => { thisComp.mouse_leave(event, copyEl) });
        copyEl.addEventListener("mouseup", (event) => { thisComp.mouse_up(event, copyEl) });
        
        // Add keyboard support for copy button
        copyEl.addEventListener("keydown", (event) => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                thisComp.copyValue(valueEl, event);
            }
        });
    }

    /**
     * Gets the HTML template for this component.
     * @returns {string} The HTML template string.
     */
    getTemplate() {
        return MojoPropertySingle.template;
    }

    /**
     * Copies the property value to the clipboard.
     * @param {HTMLElement} valueEl - The element containing the value to copy.
     * @param {Event} e - The click event.
     */
    copyValue(valueEl, e) {
        var value = valueEl.innerHTML;
        navigator.clipboard.writeText(value).then(function() {
            // Announce to screen readers if function is available
            if (typeof announceToScreenReader === 'function') {
                announceToScreenReader('Value copied to clipboard');
            }
        });
    }

    /**
     * Handles mouse down event by inverting colors on the copy button.
     * @param {MouseEvent} event - The mouse down event.
     * @param {HTMLElement} copyEl - The copy button element.
     */
    mouse_down(event, copyEl) {
        var thisStyle = getComputedStyle(copyEl);

        var fillColor = thisStyle.getPropertyValue("fill");
        var backgroundColor = thisStyle.getPropertyValue("background-color");

        copyEl.style.fill = backgroundColor;
        copyEl.style.backgroundColor = fillColor;
    }

    /**
     * Handles mouse leave event by resetting colors on the copy button.
     * @param {MouseEvent} event - The mouse leave event.
     * @param {HTMLElement} copyEl - The copy button element.
     */
    mouse_leave(event, copyEl) {
        copyEl.style.fill = "";
        copyEl.style.backgroundColor = "";
    }

    /**
     * Handles mouse up event by resetting colors on the copy button.
     * @param {MouseEvent} event - The mouse up event.
     * @param {HTMLElement} copyEl - The copy button element.
     */
    mouse_up(event, copyEl) {
        copyEl.style.fill = "";
        copyEl.style.backgroundColor = "";
    }

    /**
     * Synchronizes the component with label and value data.
     * @param {string} label - The property label.
     * @param {string} value - The property value.
     */
    syncData(label, value) {
        var labelEl = this.shadowRoot.querySelector(this.sel_label);
        var valueEl = this.shadowRoot.querySelector(this.sel_value);

        labelEl.innerHTML = label;
        valueEl.innerHTML = value;
    }

}


/**
 * A component for displaying multiple properties in a grid table layout.
 * Each property has a label, value, and copy button.
 * 
 * @class MojoPropertyTable
 * @extends HTMLElement
 * 
 * @example
 * const table = document.createElement('mojo-property-table');
 * table.syncData({ 'Name': 'John', 'Email': 'john@example.com' });
 */
class MojoPropertyTable extends HTMLElement {

    static tagname = "mojo-property-table";

    static template = `
        <div id="id-property-table-container" class="mojo-prop-table">
        </div>
    `

    default_classes_container = ["mojo-prop-table"]
    default_classes_item_copy = ["mojo-prop-table-item-copy"]
    default_classes_item_label = ["mojo-prop-table-item-label"]
    default_classes_item_value = ["mojo-prop-table-item-value"]

    sel_container = "#id-property-table-container"

    static observedAttributes = ["grid-class", "item-copy-class", "item-label-class", "item-value-class"]

    constructor() {
        super();

        const shadowRoot = this.attachShadow({mode: 'open'});
        shadowRoot.innerHTML = this.getTemplate();

        addGlobalStylesToShadowRoot(shadowRoot);
    }

    attributeChangedCallback(name, oldValue, newValue) {

        var containerEl = this.shadowRoot.querySelector(this.sel_container);

        if (name == "grid-class") {
            containerEl.classList = newValue;
        
        } else if ((name == "item-copy-class") || (name == "item-label-class") || (name == "item-value-class")) {

            var columnIndex = 0;
            if (name == "item-copy-class") {
                columnIndex = 2;
            } else if (name == "item-value-class") {
                columnIndex = 1;
            }

            var cindex = 0;
            for (childEl in containerEl.childNodes) {
                
                if ((cindex % 3) == columnIndex) {
                    childEl.classList = newValue;
                }

                cindex += 1;
            }

        }

    }

    /**
     * Copies a property value to the clipboard.
     * @param {HTMLElement} valEl - The element containing the value to copy.
     * @param {Event} e - The click event.
     */
    copyValue(valEl, e) {
        var value = valEl.innerHTML;
        navigator.clipboard.writeText(value).then(function() {
            // Announce to screen readers if function is available
            if (typeof announceToScreenReader === 'function') {
                announceToScreenReader('Value copied to clipboard');
            }
        });
    }
    
    /**
     * Creates a copy button element for a property value.
     * @param {HTMLElement} valEl - The value element to copy from.
     * @returns {HTMLElement} The copy button element.
     */
    createPropertyCopy(valEl) {

        var thisComp = this;

        var copyEl = document.createElement("button");
        copyEl.setAttribute("type", "button");
        copyEl.setAttribute("aria-label", "Copy value to clipboard");
        copyEl.setAttribute("title", "Copy to clipboard");
        copyEl.classList = this.default_classes_item_copy;
        copyEl.innerHTML = '<icon-copy aria-hidden="true"></icon-copy>';
        
        copyEl.onclick = function(e) { thisComp.copyValue(valEl, e) };

        copyEl.addEventListener("mousedown", (event) => { thisComp.mouse_down(event, copyEl) });
        copyEl.addEventListener("mouseleave", (event) => { thisComp.mouse_leave(event, copyEl) });
        copyEl.addEventListener("mouseup", (event) => { thisComp.mouse_up(event, copyEl) });
        
        // Add keyboard support for copy button
        copyEl.addEventListener("keydown", (event) => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                thisComp.copyValue(valEl, event);
            }
        });

        return copyEl;
    }

    /**
     * Creates a label element for a property.
     * @param {string} plabel - The label text.
     * @returns {HTMLElement} The label span element.
     */
    createPropertyLabel(plabel) {

        var labelEl = document.createElement("span");
        labelEl.innerHTML = plabel;
        labelEl.classList = this.default_classes_item_label;
        return labelEl;

    }

    /**
     * Creates a value element for a property.
     * @param {string} pval - The value text.
     * @returns {HTMLElement} The value span element.
     */
    createPropertyValue(pval) {

        var valueEl = document.createElement("span");
        valueEl.innerHTML = pval;
        valueEl.classList = this.default_classes_item_value;
        return valueEl;

    }

    /**
     * Gets the HTML template for this component.
     * @returns {string} The HTML template string.
     */
    getTemplate() {
        return MojoPropertyTable.template;
    }

    /**
     * Handles mouse down event by inverting colors on the copy button.
     * @param {MouseEvent} event - The mouse down event.
     * @param {HTMLElement} copyEl - The copy button element.
     */
    mouse_down(event, copyEl) {
        var thisStyle = getComputedStyle(copyEl);

        var fillColor = thisStyle.getPropertyValue("fill");
        var backgroundColor = thisStyle.getPropertyValue("background-color");

        copyEl.style.fill = backgroundColor;
        copyEl.style.backgroundColor = fillColor;
    }

    /**
     * Handles mouse leave event by resetting colors on the copy button.
     * @param {MouseEvent} event - The mouse leave event.
     * @param {HTMLElement} copyEl - The copy button element.
     */
    mouse_leave(event, copyEl) {
        copyEl.style.fill = "";
        copyEl.style.backgroundColor = "";
    }

    /**
     * Handles mouse up event by resetting colors on the copy button.
     * @param {MouseEvent} event - The mouse up event.
     * @param {HTMLElement} copyEl - The copy button element.
     */
    mouse_up(event, copyEl) {
        copyEl.style.fill = "";
        copyEl.style.backgroundColor = "";
    }
      
    /**
     * Synchronizes the component with a properties table object.
     * Creates label, value, and copy elements for each property.
     * @param {Object} propertiesTable - Object with property names as keys and values as values.
     */
    syncData(propertiesTable) {

        var containerEl = this.shadowRoot.querySelector(this.sel_container);
        containerEl.innerHTML = "";

        var propNames = Object.keys(propertiesTable);
        propNames.sort();
        
        if (propNames.length > 0) {

            for (const pindex in propNames) {
                var plabel = propNames[pindex];
                var pval = propertiesTable[plabel];

                var labelEl = this.createPropertyLabel(plabel);
                containerEl.appendChild(labelEl);

                var valEl = this.createPropertyValue(pval);
                containerEl.appendChild(valEl);

                var copyEl = this.createPropertyCopy(valEl);
                
                containerEl.appendChild(copyEl);
            }

        }

    }

}

/**
 * A tab label component for use within MojoTabSet.
 * Displays the label/title for a tab.
 * 
 * @class MojoTabLabel
 * @extends HTMLElement
 */
class MojoTabLabel extends HTMLElement {
    static tagname = "mojo-tab-label";

    static observedAttributes = ["selected"]

    static template = `
        <div id="id-tab-label-container" class="mojo-tab-label-container">
        </div>
    `

    sel_container = "#id-tab-label-container"

    constructor() {
        super();

        const shadowRoot = this.attachShadow({mode: 'open'});
        shadowRoot.innerHTML = this.getTemplate();

        addGlobalStylesToShadowRoot(shadowRoot);
    }

    /**
     * Gets the HTML template for this component.
     * @returns {string} The HTML template string.
     */
    getTemplate() {
        return MojoTabLabel.template;
    }

    /**
     * Synchronizes the component with label content.
     * @param {HTMLElement|string} label - The label content (element or text).
     */
    syncData(label) {
        var containertEl =  this.shadowRoot.querySelector(this.sel_container);
        containertEl.innerHTML = "";

        if (label instanceof HTMLElement) {
            containertEl.appendChild(label);
        } else {
            containertEl.innerHTML = "<span>" + label + "</span>";
        }
    }
}


/**
 * A tab content component for use within MojoTabSet.
 * Contains the content displayed when a tab is selected.
 * 
 * @class MojoTabContent
 * @extends HTMLElement
 */
class MojoTabContent extends HTMLElement {
    static tagname = "mojo-tab-content";

    static observedAttributes = ["selected"]

    static template = `
        <div id="id-tab-content-container" class="mojo-tab-content-container">
        </div>
    `

    sel_container = "#id-tab-content-container"

    constructor() {
        super();

        const shadowRoot = this.attachShadow({mode: 'open'});
        shadowRoot.innerHTML = this.getTemplate();

        addGlobalStylesToShadowRoot(shadowRoot);
    }

    /**
     * Gets the HTML template for this component.
     * @returns {string} The HTML template string.
     */
    getTemplate() {
        return MojoTabContent.template;
    }

    /**
     * Synchronizes the component with content.
     * @param {HTMLElement|string} content - The content to display (element or HTML string).
     */
    syncData(content) {
        var containertEl =  this.shadowRoot.querySelector(this.sel_container);
        containertEl.innerHTML = "";

        if (content instanceof HTMLElement) {
            containertEl.appendChild(content);
        } else {
            containertEl.innerHTML = content;
        }
    }
}


/**
 * Represents a single tab page with its label and content.
 * Used by MojoTabSet to manage individual tabs.
 * 
 * @class MojoTabPage
 * 
 * @example
 * const tab = new MojoTabPage('settings', 'Settings', settingsContent);
 * const [labelEl, contentEl] = tab.createTabElements();
 */
class MojoTabPage {

    /**
     * Creates a new MojoTabPage instance.
     * @param {string} key - Unique identifier for the tab.
     * @param {string|HTMLElement} label - The tab label (text or element).
     * @param {HTMLElement} content - The tab content element.
     */
    constructor(key, label, content) {
        this.key = key;
        this.label = label;
        this.content = content;

        this.labelEl = undefined;
        this.contentEl = undefined;
    }

    /**
     * Creates the content element for this tab.
     * @returns {HTMLElement} The MojoTabContent element.
     */
    createContentElement() {

        var contentEl = document.createElement("mojo-tab-content");

        contentEl.classList.add("mojo-tab-content");
        contentEl.syncData(this.content);

        this.contentEl = contentEl;

        return contentEl;

    }

    /**
     * Creates the label element for this tab.
     * @returns {HTMLElement} The MojoTabLabel element.
     */
    createLabelElement() {

        var labelEl = document.createElement("mojo-tab-label");
        
        labelEl.classList.add("mojo-tab-label");
        labelEl.syncData(this.label);
        
        this.labelEl = labelEl;

        return labelEl;

    }

    /**
     * Creates both label and content elements for this tab.
     * @returns {Array} A two-element array [labelEl, contentEl].
     */
    createTabElements() {
        var labelEl = this.createLabelElement();
        var contentEl = this.createContentElement();

        return [labelEl, contentEl];
    }

    /**
     * Removes the tab elements from the DOM.
     */
    disposeTabElements() {
        this.labelEl.remove();
        this.contentEl.remove();
    }

    /**
     * Updates the selected state of this tab's elements.
     * @param {boolean} selected - Whether this tab is selected.
     */
    updateSelected(selected) {
        if (selected) {
            this.contentEl.setAttribute("selected", selected);
            this.labelEl.setAttribute("selected", selected);
        } else {
            this.contentEl.removeAttribute("selected");
            this.labelEl.removeAttribute("selected");
        }
    }

}


/**
 * A tabbed interface component that manages multiple tab pages.
 * Displays tab labels and switches between tab content on click.
 * 
 * @class MojoTabSet
 * @extends HTMLElement
 * 
 * @example
 * const tabset = document.createElement('mojo-tabset');
 * const tabs = [
 *   new MojoTabPage('tab1', 'First Tab', content1),
 *   new MojoTabPage('tab2', 'Second Tab', content2)
 * ];
 * tabset.syncData(tabs);
 */
class MojoTabSet extends HTMLElement {

    static tagname = "mojo-tabset";

    static template = `
        <div id="id-tabset-container" class="mojo-tabset">
            <div id="id-tabset-labels-collection" class="mojo-tabset-label-collection" role="tablist" aria-label="Tab navigation">
            </div>
            <div id="id-tabset-content-collection" class="mojo-tabset-content-collection">
            </div>
        </div>
    `

    // CSS selectors for Shadow DOM element access
    sel_container = "#id-tabset-container"
    sel_labels = "#id-tabset-labels-collection"
    sel_content = "#id-tabset-content-collection"

    // =========================================================================
    // COMPONENT LIFECYCLE - Constructor Phase
    // =========================================================================
    constructor() {
        super();

        // Standard Shadow DOM setup (see MojoCollapsible for detailed comments)
        const shadowRoot = this.attachShadow({mode: 'open'});
        shadowRoot.innerHTML = this.getTemplate();

        addGlobalStylesToShadowRoot(shadowRoot);

        // Initialize tab state
        // pages: Object mapping tab keys to MojoTabPage instances
        // selected: Key of the currently selected tab
        this.pages = undefined;
        this.selected = undefined;
    }

    /**
     * Gets the HTML template for this component.
     * @returns {string} The HTML template string.
     */
    getTemplate() {
        return MojoTabSet.template;
    }

    /**
     * Removes old tab pages (placeholder for cleanup).
     */
    scrubOldPages() {
        // TODO: Implement cleanup of existing tab pages before adding new ones
        // This would call disposeTabElements() on each existing page
    }

    // =========================================================================
    // COMPONENT LIFECYCLE - Data Synchronization Phase
    // =========================================================================
    /**
     * Synchronizes the component with an array of tab pages.
     * Creates tab elements and sets up click handlers.
     * @param {MojoTabPage[]} tabPages - Array of MojoTabPage instances.
     */
    syncData(tabPages) {

        // Get references to the label and content container elements
        var labelsCollEl = this.shadowRoot.querySelector(this.sel_labels);
        var contentCollEl = this.shadowRoot.querySelector(this.sel_content);

        // Clean up any existing tabs before adding new ones
        this.scrubOldPages();

        if (tabPages.length > 0) {

            // Store reference to this component for use in event handlers
            var tabsetComp = this;

            // =====================================================================
            // TAB MANAGEMENT - Initialize Pages Registry
            // =====================================================================
            // The pages object maps tab keys to MojoTabPage instances.
            // This allows O(1) lookup when switching tabs by key.
            this.pages = {}

            for (const tindex in tabPages) {
                const tpage = tabPages[tindex];

                // =====================================================================
                // TAB MANAGEMENT - Create Tab Elements
                // =====================================================================
                // Each MojoTabPage creates two elements:
                //   1. labelEl - The clickable tab button
                //   2. contentEl - The content panel shown when tab is selected
                const [labelEl, contentEl] = tpage.createTabElements();

                // =====================================================================
                // TAB MANAGEMENT - Set Up ARIA Attributes for Accessibility
                // =====================================================================
                var tabId = 'tab-' + tpage.key;
                var panelId = 'tabpanel-' + tpage.key;
                
                labelEl.setAttribute('role', 'tab');
                labelEl.setAttribute('id', tabId);
                labelEl.setAttribute('aria-controls', panelId);
                labelEl.setAttribute('aria-selected', tindex == 0 ? 'true' : 'false');
                labelEl.setAttribute('tabindex', tindex == 0 ? '0' : '-1');
                
                contentEl.setAttribute('role', 'tabpanel');
                contentEl.setAttribute('id', panelId);
                contentEl.setAttribute('aria-labelledby', tabId);
                contentEl.setAttribute('tabindex', '0');

                // =====================================================================
                // TAB MANAGEMENT - Set Up Click Handler
                // =====================================================================
                // When a tab label is clicked, call tabClick() to switch to that tab.
                // We use a closure to capture the specific tpage for this handler.
                labelEl.onclick = function(e) {
                    tabsetComp.tabClick(tpage, e)
                };
                
                // =====================================================================
                // TAB MANAGEMENT - Set Up Keyboard Handler for Accessibility
                // =====================================================================
                labelEl.addEventListener('keydown', function(e) {
                    tabsetComp.handleTabKeydown(e, tpage);
                });

                // Register the page in the pages lookup table
                this.pages[tpage.key] = tpage;

                // =====================================================================
                // TAB MANAGEMENT - Append Elements to DOM
                // =====================================================================
                // Add the label to the labels collection (tab bar)
                // Add the content to the content collection (content area)
                labelsCollEl.appendChild(labelEl);
                contentCollEl.appendChild(contentEl);
            }

            // =====================================================================
            // TAB MANAGEMENT - Set Initial Selection
            // =====================================================================
            // Select the first tab by default
            this.selected = tabPages[0].key;
        }

        // Update visual state to show the selected tab
        this.switchToSelected()

    }

    /**
     * Handles keyboard navigation for tabs.
     * @param {KeyboardEvent} event - The keyboard event.
     * @param {MojoTabPage} currentPage - The currently focused tab page.
     */
    handleTabKeydown(event, currentPage) {
        var pageKeys = Object.keys(this.pages);
        var currentIndex = pageKeys.indexOf(currentPage.key);
        var newIndex = currentIndex;
        
        switch (event.key) {
            case 'ArrowLeft':
            case 'ArrowUp':
                event.preventDefault();
                newIndex = currentIndex > 0 ? currentIndex - 1 : pageKeys.length - 1;
                break;
            case 'ArrowRight':
            case 'ArrowDown':
                event.preventDefault();
                newIndex = currentIndex < pageKeys.length - 1 ? currentIndex + 1 : 0;
                break;
            case 'Home':
                event.preventDefault();
                newIndex = 0;
                break;
            case 'End':
                event.preventDefault();
                newIndex = pageKeys.length - 1;
                break;
            case 'Enter':
            case ' ':
                event.preventDefault();
                this.tabClick(currentPage, event);
                return;
            default:
                return;
        }
        
        // Focus and select the new tab
        var newKey = pageKeys[newIndex];
        var newPage = this.pages[newKey];
        if (newPage && newPage.labelEl) {
            newPage.labelEl.focus();
            this.tabClick(newPage, event);
        }
    }

    // =========================================================================
    // TAB MANAGEMENT - Selection State Update
    // =========================================================================
    /**
     * Updates the visual state to show the currently selected tab.
     * Hides non-selected tabs and shows the selected one.
     */
    switchToSelected() {
        var pageKeys = Object.keys(this.pages);

        if (pageKeys.length > 0) {

            // Iterate through all pages and update their selected state
            // Each page's updateSelected() method handles showing/hiding
            // and applying the appropriate CSS classes
            for (const pki in pageKeys) {
                var pkey = pageKeys[pki];
                var page = this.pages[pkey];
                var isSelected = pkey == this.selected;
                
                // Pass true if this page's key matches the selected key
                page.updateSelected(isSelected);
                
                // Update ARIA attributes for accessibility
                if (page.labelEl) {
                    page.labelEl.setAttribute('aria-selected', isSelected ? 'true' : 'false');
                    page.labelEl.setAttribute('tabindex', isSelected ? '0' : '-1');
                }
            }

        }

    }

    // =========================================================================
    // TAB MANAGEMENT - User Interaction Handler
    // =========================================================================
    /**
     * Handles tab click events by selecting the clicked tab.
     * @param {MojoTabPage} tpage - The tab page that was clicked.
     * @param {Event} event - The click event.
     */
    tabClick(tpage, event) {
        // Update the selected key to the clicked tab's key
        this.selected = tpage.key;
        // Refresh the visual state to reflect the new selection
        this.switchToSelected();
        
        // Announce tab change to screen readers if function is available
        if (typeof announceToScreenReader === 'function') {
            var tabName = tpage.label || tpage.key;
            announceToScreenReader(tabName + ' tab selected');
        }
    }
}



/**
 * Registers all Mojo base components with the customElements registry.
 * Should be called before using any Mojo components.
 * Safe to call multiple times - only registers once.
 * 
 * @function register_mojo_components
 * @returns {void}
 * 
 * @example
 * // Register components on page load
 * register_mojo_components();
 */
function register_mojo_components() {

    // =========================================================================
    // COMPONENT REGISTRATION - Dependency Chain
    // =========================================================================
    // Register icon components first because Mojo components use them
    // (e.g., MojoCollapsible uses icon-plus-sign and icon-minus-sign).
    // This ensures icons are available when Mojo components render.
    register_icon_components()

    // =========================================================================
    // COMPONENT REGISTRATION - Idempotency Guard
    // =========================================================================
    // Use a module-scoped flag to ensure components are only registered once.
    // Calling customElements.define() twice with the same tag name throws an
    // error, so this guard prevents crashes if register is called multiple times.
    if (!mojoComponentsRegistered) {
        mojoComponentsRegistered = true;

        // =====================================================================
        // COMPONENT REGISTRATION - Custom Element Definition
        // =====================================================================
        // customElements.define() associates a tag name with a class.
        // After registration, the browser will:
        //   1. Upgrade existing elements with that tag name
        //   2. Create instances of the class for new elements
        //   3. Call the constructor when elements are created
        //
        // Tag names MUST contain a hyphen (e.g., "mojo-collapsible") to
        // distinguish them from standard HTML elements.
        customElements.define(MojoCollapsible.tagname, MojoCollapsible);
        customElements.define(MojoCollapsibleLvl2.tagname, MojoCollapsibleLvl2);
        customElements.define(MojoCollapsibleLvl3.tagname, MojoCollapsibleLvl3);
        customElements.define(MojoIconTarget.tagname, MojoIconTarget);
        customElements.define(MojoProjectTimeline.tagname, MojoProjectTimeline);
        customElements.define(MojoPropertySingle.tagname, MojoPropertySingle);
        customElements.define(MojoPropertyTable.tagname, MojoPropertyTable);
        customElements.define(MojoTabSet.tagname, MojoTabSet);
        customElements.define(MojoTabContent.tagname, MojoTabContent);
        customElements.define(MojoTabLabel.tagname, MojoTabLabel);
    }

}

