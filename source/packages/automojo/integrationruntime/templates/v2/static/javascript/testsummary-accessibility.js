/*
    Author: "Myron Walker"
    Copyright: "Copyright 2024, Myron W Walker"
    Version: = "2.0.0"
    Email: myron.walker@gmail.com
*/

/**
 * @fileoverview Accessibility enhancements for the TestSummary HTML report.
 * Provides ARIA labels, keyboard navigation, and screen reader compatibility.
 * @module testsummary-accessibility
 */

/**
 * Flag indicating whether accessibility features have been initialized.
 * @type {boolean}
 * @private
 */
let accessibilityInitialized = false;

/**
 * Keyboard navigation key codes.
 * @const {Object}
 */
const KEYS = {
    TAB: 'Tab',
    ENTER: 'Enter',
    SPACE: ' ',
    ESCAPE: 'Escape',
    ARROW_UP: 'ArrowUp',
    ARROW_DOWN: 'ArrowDown',
    ARROW_LEFT: 'ArrowLeft',
    ARROW_RIGHT: 'ArrowRight',
    HOME: 'Home',
    END: 'End'
};

/**
 * Initializes accessibility features for the test summary page.
 * Should be called after the page content is loaded.
 * 
 * @function init_accessibility
 * @returns {void}
 */
function init_accessibility() {
    if (accessibilityInitialized) {
        return;
    }
    accessibilityInitialized = true;

    // Add skip link for keyboard users
    addSkipLink();

    // Set up landmark regions
    setupLandmarkRegions();

    // Initialize keyboard navigation
    initKeyboardNavigation();

    // Add ARIA labels to interactive elements
    addAriaLabels();

    // Set up focus management
    setupFocusManagement();

    // Add live region for dynamic content announcements
    addLiveRegion();

    console.log("Accessibility features initialized");
}

/**
 * Adds a skip link at the top of the page for keyboard users to skip to main content.
 * 
 * @function addSkipLink
 * @returns {void}
 */
function addSkipLink() {
    // Check if skip link already exists
    if (document.getElementById('skip-to-main')) {
        return;
    }

    var skipLink = document.createElement('a');
    skipLink.id = 'skip-to-main';
    skipLink.href = '#testsummary-resultdetail';
    skipLink.className = 'skip-link';
    skipLink.textContent = 'Skip to main content';
    skipLink.setAttribute('tabindex', '0');

    // Insert at the beginning of body
    document.body.insertBefore(skipLink, document.body.firstChild);

    // Handle click to focus on main content
    skipLink.addEventListener('click', function(event) {
        event.preventDefault();
        var mainContent = document.getElementById('testsummary-resultdetail');
        if (mainContent) {
            mainContent.setAttribute('tabindex', '-1');
            mainContent.focus();
            // Announce to screen readers
            announceToScreenReader('Skipped to main content');
        }
    });
}

/**
 * Sets up ARIA landmark regions for the page structure.
 * 
 * @function setupLandmarkRegions
 * @returns {void}
 */
function setupLandmarkRegions() {
    // Header section - banner landmark
    var headerSection = document.querySelector('.section-header');
    if (headerSection) {
        headerSection.setAttribute('role', 'banner');
        headerSection.setAttribute('aria-label', 'Test run summary banner');
    }

    // Body section - main landmark
    var bodySection = document.querySelector('.section-body');
    if (bodySection) {
        bodySection.setAttribute('role', 'main');
        bodySection.setAttribute('aria-label', 'Test results and configuration');
    }

    // Footer section - contentinfo landmark
    var footerSection = document.querySelector('.section-footer');
    if (footerSection) {
        footerSection.setAttribute('role', 'contentinfo');
        footerSection.setAttribute('aria-label', 'Files and folders navigation');
    }
}

/**
 * Initializes keyboard navigation for interactive elements.
 * 
 * @function initKeyboardNavigation
 * @returns {void}
 */
function initKeyboardNavigation() {
    // Add keyboard handler for the document
    document.addEventListener('keydown', handleGlobalKeydown);

    // Set up keyboard navigation for collapsible elements
    setupCollapsibleKeyboardNav();

    // Set up keyboard navigation for tabs
    setupTabKeyboardNav();

    // Set up keyboard navigation for filter buttons
    setupFilterKeyboardNav();
}

/**
 * Handles global keyboard events for navigation.
 * 
 * @function handleGlobalKeydown
 * @param {KeyboardEvent} event - The keyboard event.
 */
function handleGlobalKeydown(event) {
    // Handle Escape key to close any open dialogs or return focus
    if (event.key === KEYS.ESCAPE) {
        var activeElement = document.activeElement;
        if (activeElement && activeElement.closest('details[open]')) {
            var details = activeElement.closest('details');
            details.open = false;
            details.querySelector('summary').focus();
        }
    }
}

/**
 * Sets up keyboard navigation for collapsible elements.
 * 
 * @function setupCollapsibleKeyboardNav
 * @returns {void}
 */
function setupCollapsibleKeyboardNav() {
    // Find all collapsible buttons in shadow DOMs
    var collapsibles = document.querySelectorAll('mojo-collapsible, mojo-collapsible-lvl2, mojo-collapsible-lvl3');
    
    collapsibles.forEach(function(collapsible) {
        if (collapsible.shadowRoot) {
            var button = collapsible.shadowRoot.querySelector('.mojo-collapsible-button, .mojo-collapsible-lvl2-button, .mojo-collapsible-lvl3-button');
            if (button) {
                // Make button focusable
                button.setAttribute('tabindex', '0');
                button.setAttribute('role', 'button');
                
                // Add keyboard handler
                button.addEventListener('keydown', function(event) {
                    if (event.key === KEYS.ENTER || event.key === KEYS.SPACE) {
                        event.preventDefault();
                        button.click();
                    }
                });
            }
        }
    });
}

/**
 * Sets up keyboard navigation for tab components.
 * 
 * @function setupTabKeyboardNav
 * @returns {void}
 */
function setupTabKeyboardNav() {
    var tabsets = document.querySelectorAll('mojo-tabset');
    
    tabsets.forEach(function(tabset) {
        if (tabset.shadowRoot) {
            var tabLabels = tabset.shadowRoot.querySelectorAll('.mojo-tab-label');
            
            tabLabels.forEach(function(tabLabel, index) {
                // Set up ARIA attributes
                tabLabel.setAttribute('role', 'tab');
                tabLabel.setAttribute('tabindex', index === 0 ? '0' : '-1');
                
                // Add keyboard navigation
                tabLabel.addEventListener('keydown', function(event) {
                    handleTabKeydown(event, tabLabels, index);
                });
            });

            // Set up tab list container
            var tabList = tabset.shadowRoot.querySelector('.mojo-tabset-label-collection');
            if (tabList) {
                tabList.setAttribute('role', 'tablist');
            }

            // Set up tab panels
            var tabContents = tabset.shadowRoot.querySelectorAll('.mojo-tab-content');
            tabContents.forEach(function(content, index) {
                content.setAttribute('role', 'tabpanel');
                content.setAttribute('tabindex', '0');
            });
        }
    });
}

/**
 * Handles keyboard events for tab navigation.
 * 
 * @function handleTabKeydown
 * @param {KeyboardEvent} event - The keyboard event.
 * @param {NodeList} tabs - List of tab elements.
 * @param {number} currentIndex - Current tab index.
 */
function handleTabKeydown(event, tabs, currentIndex) {
    var newIndex = currentIndex;
    
    switch (event.key) {
        case KEYS.ARROW_LEFT:
        case KEYS.ARROW_UP:
            event.preventDefault();
            newIndex = currentIndex > 0 ? currentIndex - 1 : tabs.length - 1;
            break;
        case KEYS.ARROW_RIGHT:
        case KEYS.ARROW_DOWN:
            event.preventDefault();
            newIndex = currentIndex < tabs.length - 1 ? currentIndex + 1 : 0;
            break;
        case KEYS.HOME:
            event.preventDefault();
            newIndex = 0;
            break;
        case KEYS.END:
            event.preventDefault();
            newIndex = tabs.length - 1;
            break;
        case KEYS.ENTER:
        case KEYS.SPACE:
            event.preventDefault();
            tabs[currentIndex].click();
            return;
        default:
            return;
    }

    // Update tabindex and focus
    tabs[currentIndex].setAttribute('tabindex', '-1');
    tabs[newIndex].setAttribute('tabindex', '0');
    tabs[newIndex].focus();
    tabs[newIndex].click();
}

/**
 * Sets up keyboard navigation for filter buttons.
 * 
 * @function setupFilterKeyboardNav
 * @returns {void}
 */
function setupFilterKeyboardNav() {
    var resultDetail = document.getElementById('testsummary-resultdetail');
    if (resultDetail && resultDetail.shadowRoot) {
        var filterButtons = resultDetail.shadowRoot.querySelectorAll('.ts-filter-btn');
        
        filterButtons.forEach(function(button, index) {
            button.setAttribute('role', 'button');
            
            button.addEventListener('keydown', function(event) {
                if (event.key === KEYS.ARROW_LEFT || event.key === KEYS.ARROW_RIGHT) {
                    event.preventDefault();
                    var newIndex;
                    if (event.key === KEYS.ARROW_LEFT) {
                        newIndex = index > 0 ? index - 1 : filterButtons.length - 1;
                    } else {
                        newIndex = index < filterButtons.length - 1 ? index + 1 : 0;
                    }
                    filterButtons[newIndex].focus();
                }
            });
        });
    }
}

/**
 * Adds ARIA labels to interactive elements throughout the page.
 * 
 * @function addAriaLabels
 * @returns {void}
 */
function addAriaLabels() {
    // Add ARIA labels to banner component
    addBannerAriaLabels();

    // Add ARIA labels to configuration component
    addConfigurationAriaLabels();

    // Add ARIA labels to result detail component
    addResultDetailAriaLabels();

    // Add ARIA labels to artifacts component
    addArtifactsAriaLabels();

    // Add ARIA labels to files and folders component
    addFilesAndFoldersAriaLabels();
}

/**
 * Adds ARIA labels to the banner component.
 * 
 * @function addBannerAriaLabels
 * @returns {void}
 */
function addBannerAriaLabels() {
    var banner = document.getElementById('testsummary-banner');
    if (banner && banner.shadowRoot) {
        var bannerEl = banner.shadowRoot.querySelector('.ts-banner');
        if (bannerEl) {
            bannerEl.setAttribute('role', 'region');
            bannerEl.setAttribute('aria-label', 'Test run summary');
        }

        // Add labels to metrics
        var metricsPanel = banner.shadowRoot.querySelector('.ts-banner-metrics-panel');
        if (metricsPanel) {
            metricsPanel.setAttribute('role', 'group');
            metricsPanel.setAttribute('aria-label', 'Test result metrics');
        }

        // Add aria-live for dynamic metric updates
        var metricValues = banner.shadowRoot.querySelectorAll('.ts-banner-metrics-value');
        metricValues.forEach(function(value) {
            value.setAttribute('aria-live', 'polite');
        });
    }
}

/**
 * Adds ARIA labels to the configuration component.
 * 
 * @function addConfigurationAriaLabels
 * @returns {void}
 */
function addConfigurationAriaLabels() {
    var config = document.getElementById('testsummary-configuration');
    if (config && config.shadowRoot) {
        var configCard = config.shadowRoot.querySelector('.ts-configuration-card');
        if (configCard) {
            configCard.setAttribute('role', 'region');
            configCard.setAttribute('aria-label', 'Test configuration');
        }

        // Add labels to collapsible sections
        var collapsibles = config.shadowRoot.querySelectorAll('mojo-collapsible');
        collapsibles.forEach(function(collapsible) {
            if (collapsible.shadowRoot) {
                var button = collapsible.shadowRoot.querySelector('.mojo-collapsible-button');
                var content = collapsible.shadowRoot.querySelector('.mojo-collapsible-content');
                if (button && content) {
                    var headerId = 'config-header-' + Math.random().toString(36).substr(2, 9);
                    var contentId = 'config-content-' + Math.random().toString(36).substr(2, 9);
                    
                    button.setAttribute('id', headerId);
                    button.setAttribute('aria-expanded', content.style.display !== 'none');
                    button.setAttribute('aria-controls', contentId);
                    
                    content.setAttribute('id', contentId);
                    content.setAttribute('aria-labelledby', headerId);
                }
            }
        });
    }
}

/**
 * Adds ARIA labels to the result detail component.
 * 
 * @function addResultDetailAriaLabels
 * @returns {void}
 */
function addResultDetailAriaLabels() {
    var resultDetail = document.getElementById('testsummary-resultdetail');
    if (resultDetail && resultDetail.shadowRoot) {
        var resultCard = resultDetail.shadowRoot.querySelector('.ts-resultdetail-card');
        if (resultCard) {
            resultCard.setAttribute('role', 'region');
            resultCard.setAttribute('aria-label', 'Test result details');
        }

        // Add labels to filter toolbar
        var filterToolbar = resultDetail.shadowRoot.querySelector('.ts-filter-toolbar');
        if (filterToolbar) {
            filterToolbar.setAttribute('role', 'toolbar');
            filterToolbar.setAttribute('aria-label', 'Result filters');
        }

        // Add labels to filter buttons
        var filterButtons = resultDetail.shadowRoot.querySelectorAll('.ts-filter-btn');
        filterButtons.forEach(function(button) {
            var filter = button.getAttribute('data-filter');
            button.setAttribute('aria-pressed', button.classList.contains('ts-filter-btn-active'));
            button.setAttribute('aria-label', 'Filter by ' + filter.toLowerCase() + ' tests');
        });

        // Add label to search input
        var searchInput = resultDetail.shadowRoot.querySelector('#id-search-input');
        if (searchInput) {
            searchInput.setAttribute('aria-label', 'Search test names');
            searchInput.setAttribute('role', 'searchbox');
        }

        // Add labels to date inputs
        var dateStart = resultDetail.shadowRoot.querySelector('#id-date-start');
        var dateEnd = resultDetail.shadowRoot.querySelector('#id-date-end');
        if (dateStart) {
            dateStart.setAttribute('aria-label', 'Filter start date');
        }
        if (dateEnd) {
            dateEnd.setAttribute('aria-label', 'Filter end date');
        }

        // Add labels to export buttons
        var exportCSV = resultDetail.shadowRoot.querySelector('#id-export-csv');
        var exportPDF = resultDetail.shadowRoot.querySelector('#id-export-pdf');
        if (exportCSV) {
            exportCSV.setAttribute('aria-label', 'Export results to CSV file');
        }
        if (exportPDF) {
            exportPDF.setAttribute('aria-label', 'Export results to PDF file');
        }

        // Add label to display mode selector
        var displayMode = resultDetail.shadowRoot.querySelector('#id-display-mode');
        if (displayMode) {
            displayMode.setAttribute('aria-label', 'Select result display mode');
        }

        // Add label to grouping selector
        var groupingOption = resultDetail.shadowRoot.querySelector('#id-grouping-option');
        if (groupingOption) {
            groupingOption.setAttribute('aria-label', 'Select result grouping option');
        }

        // Add label to filter summary
        var filterSummary = resultDetail.shadowRoot.querySelector('#id-filter-summary');
        if (filterSummary) {
            filterSummary.setAttribute('role', 'status');
            filterSummary.setAttribute('aria-live', 'polite');
        }
    }
}

/**
 * Adds ARIA labels to the artifacts component.
 * 
 * @function addArtifactsAriaLabels
 * @returns {void}
 */
function addArtifactsAriaLabels() {
    var artifacts = document.getElementById('testsummary-artifacts');
    if (artifacts && artifacts.shadowRoot) {
        var artifactsCard = artifacts.shadowRoot.querySelector('.ts-artifacts-card');
        if (artifactsCard) {
            artifactsCard.setAttribute('role', 'region');
            artifactsCard.setAttribute('aria-label', 'Test artifacts');
        }

        // Add labels to iframes
        var iframes = artifacts.shadowRoot.querySelectorAll('iframe');
        iframes.forEach(function(iframe) {
            var title = iframe.getAttribute('title') || 'Artifact viewer';
            iframe.setAttribute('aria-label', title + ' artifact viewer');
        });
    }
}

/**
 * Adds ARIA labels to the files and folders component.
 * 
 * @function addFilesAndFoldersAriaLabels
 * @returns {void}
 */
function addFilesAndFoldersAriaLabels() {
    var filesAndFolders = document.getElementById('testsummary-filesandfolders');
    if (filesAndFolders && filesAndFolders.shadowRoot) {
        var card = filesAndFolders.shadowRoot.querySelector('.ts-filesandfolders-card');
        if (card) {
            card.setAttribute('role', 'navigation');
            card.setAttribute('aria-label', 'Output directory navigation');
        }

        // Add labels to folder and file lists
        var foldersList = filesAndFolders.shadowRoot.querySelector('#id-folders-list');
        var filesList = filesAndFolders.shadowRoot.querySelector('#id-files-list');
        
        if (foldersList) {
            foldersList.setAttribute('role', 'list');
            foldersList.setAttribute('aria-label', 'Folders');
        }
        if (filesList) {
            filesList.setAttribute('role', 'list');
            filesList.setAttribute('aria-label', 'Files');
        }
    }
}

/**
 * Sets up focus management for better keyboard navigation.
 * 
 * @function setupFocusManagement
 * @returns {void}
 */
function setupFocusManagement() {
    // Add visible focus indicators
    document.addEventListener('keydown', function(event) {
        if (event.key === KEYS.TAB) {
            document.body.classList.add('keyboard-navigation');
        }
    });

    document.addEventListener('mousedown', function() {
        document.body.classList.remove('keyboard-navigation');
    });

    // Trap focus in modal-like elements when open
    setupFocusTrap();
}

/**
 * Sets up focus trapping for modal-like elements.
 * 
 * @function setupFocusTrap
 * @returns {void}
 */
function setupFocusTrap() {
    // Find all details elements that act as expandable sections
    var detailsElements = document.querySelectorAll('details');
    
    detailsElements.forEach(function(details) {
        details.addEventListener('toggle', function() {
            if (details.open) {
                // Focus the first focusable element inside
                var firstFocusable = details.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
                if (firstFocusable) {
                    setTimeout(function() {
                        firstFocusable.focus();
                    }, 100);
                }
            }
        });
    });
}

/**
 * Adds a live region for screen reader announcements.
 * 
 * @function addLiveRegion
 * @returns {void}
 */
function addLiveRegion() {
    // Check if live region already exists
    if (document.getElementById('aria-live-region')) {
        return;
    }

    var liveRegion = document.createElement('div');
    liveRegion.id = 'aria-live-region';
    liveRegion.setAttribute('role', 'status');
    liveRegion.setAttribute('aria-live', 'polite');
    liveRegion.setAttribute('aria-atomic', 'true');
    liveRegion.className = 'sr-only';
    
    document.body.appendChild(liveRegion);
}

/**
 * Announces a message to screen readers via the live region.
 * 
 * @function announceToScreenReader
 * @param {string} message - The message to announce.
 * @param {string} [priority='polite'] - The announcement priority ('polite' or 'assertive').
 */
function announceToScreenReader(message, priority) {
    priority = priority || 'polite';
    
    var liveRegion = document.getElementById('aria-live-region');
    if (!liveRegion) {
        addLiveRegion();
        liveRegion = document.getElementById('aria-live-region');
    }

    liveRegion.setAttribute('aria-live', priority);
    
    // Clear and set message to trigger announcement
    liveRegion.textContent = '';
    setTimeout(function() {
        liveRegion.textContent = message;
    }, 100);
}

/**
 * Updates ARIA attributes when filter state changes.
 * Called by the result detail component when filters are applied.
 * 
 * @function updateFilterAriaState
 * @param {string} activeFilter - The currently active filter.
 * @param {number} visibleCount - Number of visible results.
 * @param {number} totalCount - Total number of results.
 */
function updateFilterAriaState(activeFilter, visibleCount, totalCount) {
    var resultDetail = document.getElementById('testsummary-resultdetail');
    if (resultDetail && resultDetail.shadowRoot) {
        // Update aria-pressed on filter buttons
        var filterButtons = resultDetail.shadowRoot.querySelectorAll('.ts-filter-btn');
        filterButtons.forEach(function(button) {
            var filter = button.getAttribute('data-filter');
            button.setAttribute('aria-pressed', filter === activeFilter);
        });

        // Announce filter change to screen readers
        var message = 'Showing ' + visibleCount + ' of ' + totalCount + ' tests';
        if (activeFilter !== 'ALL') {
            message += ', filtered by ' + activeFilter.toLowerCase();
        }
        announceToScreenReader(message);
    }
}

/**
 * Updates ARIA attributes when a collapsible section is toggled.
 * 
 * @function updateCollapsibleAriaState
 * @param {HTMLElement} button - The collapsible button element.
 * @param {boolean} expanded - Whether the section is expanded.
 */
function updateCollapsibleAriaState(button, expanded) {
    button.setAttribute('aria-expanded', expanded);
    
    var headerText = button.querySelector('.mojo-collapsible-header, .mojo-collapsible-lvl2-header, .mojo-collapsible-lvl3-header');
    var sectionName = headerText ? headerText.textContent : 'Section';
    
    announceToScreenReader(sectionName + ' ' + (expanded ? 'expanded' : 'collapsed'));
}

/**
 * Updates ARIA attributes when a tab is selected.
 * 
 * @function updateTabAriaState
 * @param {HTMLElement} selectedTab - The selected tab element.
 * @param {NodeList} allTabs - All tab elements.
 */
function updateTabAriaState(selectedTab, allTabs) {
    allTabs.forEach(function(tab) {
        tab.setAttribute('aria-selected', tab === selectedTab);
        tab.setAttribute('tabindex', tab === selectedTab ? '0' : '-1');
    });

    var tabName = selectedTab.textContent || 'Tab';
    announceToScreenReader(tabName + ' tab selected');
}

// Export functions for use by other modules
if (typeof window !== 'undefined') {
    window.init_accessibility = init_accessibility;
    window.announceToScreenReader = announceToScreenReader;
    window.updateFilterAriaState = updateFilterAriaState;
    window.updateCollapsibleAriaState = updateCollapsibleAriaState;
    window.updateTabAriaState = updateTabAriaState;
}
