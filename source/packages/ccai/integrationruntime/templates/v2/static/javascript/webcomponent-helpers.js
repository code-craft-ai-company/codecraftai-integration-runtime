/*
    Author: "Myron Walker"
    Copyright: "Copyright 2024, Myron W Walker"
    Version: = "2.0.0"
    Email: myron.walker@gmail.com
*/

/**
 * @fileoverview Helper functions for Web Component Shadow DOM management.
 * Provides utilities for copying global stylesheets into Shadow DOM roots
 * to ensure consistent styling across encapsulated components.
 * @module webcomponent-helpers
 */

/**
 * Cached array of global stylesheets converted to CSSStyleSheet objects.
 * Populated on first call to getGlobalStyleSheets() and reused thereafter.
 * @type {CSSStyleSheet[]|null}
 * @private
 */
let globalSheets = null;


/**
 * Retrieves all global stylesheets from the document and converts them to
 * CSSStyleSheet objects suitable for adoption by Shadow DOM roots.
 * Results are cached for performance on subsequent calls.
 * 
 * @function getGlobalStyleSheets
 * @returns {CSSStyleSheet[]} Array of CSSStyleSheet objects containing all document styles.
 * 
 * @example
 * // Get global stylesheets for manual adoption
 * const sheets = getGlobalStyleSheets();
 * console.log('Found', sheets.length, 'stylesheets');
 */
function getGlobalStyleSheets() {
    // =========================================================================
    // SHADOW DOM STYLE ADOPTION - Caching Strategy
    // =========================================================================
    // Global stylesheets are cached after first retrieval because:
    //   1. Converting stylesheets is expensive (iterating all CSS rules)
    //   2. Document stylesheets rarely change after page load
    //   3. Many components need the same styles (avoid redundant work)
    // The cache is module-scoped, so all components share the same sheets.
    if (globalSheets === null) {
        // =====================================================================
        // SHADOW DOM STYLE ADOPTION - Stylesheet Conversion Process
        // =====================================================================
        // Convert each document stylesheet to a CSSStyleSheet object that can
        // be adopted by Shadow DOM roots. This is necessary because:
        //   1. Shadow DOM is encapsulated - external styles don't apply by default
        //   2. adoptedStyleSheets requires CSSStyleSheet objects, not StyleSheet
        //   3. We need to extract CSS rules and create new constructable sheets
        globalSheets = Array.from(document.styleSheets)
          .map(x => {
            // Create a new constructable stylesheet
            // (Constructable stylesheets are a modern API for programmatic CSS)
            const sheet = new CSSStyleSheet();
            
            // Extract all CSS rules from the original stylesheet
            // and concatenate them into a single CSS string.
            // This preserves all selectors, properties, and values.
            const css = Array.from(x.cssRules).map(rule => rule.cssText).join(' ');
            
            // Synchronously replace the sheet's contents with the extracted CSS.
            // replaceSync() is used instead of replace() for immediate availability.
            sheet.replaceSync(css);
            
            return sheet;
          });
      }
    
      return globalSheets;
}


/**
 * Adds all global document stylesheets to a Shadow DOM root's adoptedStyleSheets.
 * This allows Shadow DOM components to inherit global styles while maintaining encapsulation.
 * Should be called in the constructor of each web component after attaching the shadow root.
 * 
 * @function addGlobalStylesToShadowRoot
 * @param {ShadowRoot} shadowRoot - The Shadow DOM root to add styles to.
 * @returns {void}
 * 
 * @example
 * class MyComponent extends HTMLElement {
 *   constructor() {
 *     super();
 *     const shadowRoot = this.attachShadow({mode: 'open'});
 *     shadowRoot.innerHTML = MyComponent.template;
 *     addGlobalStylesToShadowRoot(shadowRoot);
 *   }
 * }
 */
function addGlobalStylesToShadowRoot(shadowRoot) {
    // =========================================================================
    // SHADOW DOM STYLE ADOPTION - Applying Styles to Shadow Root
    // =========================================================================
    // The adoptedStyleSheets property allows sharing stylesheets between
    // documents and shadow roots. Benefits include:
    //   1. Memory efficiency - same CSSStyleSheet object shared across components
    //   2. Performance - browser can optimize shared stylesheet rendering
    //   3. Consistency - all components use identical style definitions
    //
    // We use push() with spread operator to append to any existing adopted
    // sheets (in case the component has its own component-specific styles).
    shadowRoot.adoptedStyleSheets.push(
        ...getGlobalStyleSheets()
    );
}
