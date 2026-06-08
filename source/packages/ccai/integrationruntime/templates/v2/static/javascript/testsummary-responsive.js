/*
    Author: "Myron Walker"
    Copyright: "Copyright 2024, Myron W Walker"
    Version: = "2.0.0"
    Email: myron.walker@gmail.com
    
    Responsive Design JavaScript for TestSummary HTML Report Templates
    Provides mobile navigation toggle, collapsible sidebar, and touch interactions.
*/

/**
 * @fileoverview Responsive design functionality for TestSummary reports.
 * Handles mobile navigation, sidebar toggle, and touch-friendly interactions.
 * @module testsummary-responsive
 */

/**
 * Responsive navigation manager for mobile devices.
 * Handles sidebar toggle, overlay, and navigation state.
 */
class ResponsiveNavManager {
    constructor() {
        this.isOpen = false;
        this.toggleButton = null;
        this.sidebar = null;
        this.overlay = null;
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.swipeThreshold = 50;
    }

    /**
     * Initializes the responsive navigation system.
     * Creates navigation elements and sets up event listeners.
     */
    init() {
        this.createNavigationElements();
        this.setupEventListeners();
        this.setupTouchGestures();
        this.updateNavigationLinks();
    }

    /**
     * Creates the mobile navigation toggle button, sidebar, and overlay.
     */
    createNavigationElements() {
        // Create mobile nav toggle button
        this.toggleButton = document.createElement('button');
        this.toggleButton.className = 'ts-mobile-nav-toggle';
        this.toggleButton.setAttribute('aria-label', 'Toggle navigation menu');
        this.toggleButton.setAttribute('aria-expanded', 'false');
        this.toggleButton.innerHTML = `
            <div class="ts-mobile-nav-toggle-icon">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;

        // Create sidebar navigation
        this.sidebar = document.createElement('nav');
        this.sidebar.className = 'ts-sidebar-nav';
        this.sidebar.setAttribute('aria-label', 'Main navigation');
        this.sidebar.innerHTML = `
            <div class="ts-sidebar-nav-header">
                <h2 class="ts-sidebar-nav-title">Test Summary</h2>
            </div>
            <ul class="ts-sidebar-nav-list" role="menu">
                <li class="ts-sidebar-nav-item" role="none">
                    <a href="#testsummary-banner" class="ts-sidebar-nav-link" role="menuitem">
                        <span class="ts-sidebar-nav-icon">📊</span>
                        Summary
                    </a>
                </li>
                <li class="ts-sidebar-nav-item" role="none">
                    <a href="#testsummary-configuration" class="ts-sidebar-nav-link" role="menuitem">
                        <span class="ts-sidebar-nav-icon">⚙️</span>
                        Configuration
                    </a>
                </li>
                <li class="ts-sidebar-nav-item" role="none">
                    <a href="#testsummary-resultdetail" class="ts-sidebar-nav-link" role="menuitem">
                        <span class="ts-sidebar-nav-icon">📋</span>
                        Results
                    </a>
                </li>
                <li class="ts-sidebar-nav-item" role="none">
                    <a href="#testsummary-comparison" class="ts-sidebar-nav-link" role="menuitem">
                        <span class="ts-sidebar-nav-icon">🔄</span>
                        Comparison
                    </a>
                </li>
                <li class="ts-sidebar-nav-item" role="none">
                    <a href="#testsummary-trend-analysis" class="ts-sidebar-nav-link" role="menuitem">
                        <span class="ts-sidebar-nav-icon">📈</span>
                        Trends
                    </a>
                </li>
                <li class="ts-sidebar-nav-item" role="none">
                    <a href="#testsummary-artifacts" class="ts-sidebar-nav-link" role="menuitem">
                        <span class="ts-sidebar-nav-icon">📁</span>
                        Artifacts
                    </a>
                </li>
                <li class="ts-sidebar-nav-item" role="none">
                    <a href="#testsummary-importfailures" class="ts-sidebar-nav-link" role="menuitem">
                        <span class="ts-sidebar-nav-icon">⚠️</span>
                        Import Failures
                    </a>
                </li>
                <li class="ts-sidebar-nav-item" role="none">
                    <a href="#testsummary-filesandfolders" class="ts-sidebar-nav-link" role="menuitem">
                        <span class="ts-sidebar-nav-icon">📂</span>
                        Files & Folders
                    </a>
                </li>
            </ul>
        `;

        // Create overlay
        this.overlay = document.createElement('div');
        this.overlay.className = 'ts-sidebar-overlay';
        this.overlay.setAttribute('aria-hidden', 'true');

        // Insert elements into DOM
        document.body.insertBefore(this.toggleButton, document.body.firstChild);
        document.body.insertBefore(this.sidebar, document.body.firstChild);
        document.body.insertBefore(this.overlay, document.body.firstChild);
    }

    /**
     * Sets up event listeners for navigation interactions.
     */
    setupEventListeners() {
        // Toggle button click
        this.toggleButton.addEventListener('click', (e) => {
            e.preventDefault();
            this.toggle();
        });

        // Overlay click to close
        this.overlay.addEventListener('click', () => {
            this.close();
        });

        // Navigation link clicks
        const navLinks = this.sidebar.querySelectorAll('.ts-sidebar-nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                this.handleNavLinkClick(e, link);
            });
        });

        // Keyboard navigation
        this.sidebar.addEventListener('keydown', (e) => {
            this.handleKeyboardNavigation(e);
        });

        // Close on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.close();
                this.toggleButton.focus();
            }
        });

        // Handle window resize
        window.addEventListener('resize', () => {
            this.handleResize();
        });
    }

    /**
     * Sets up touch gesture support for swipe navigation.
     */
    setupTouchGestures() {
        // Track touch start position
        document.addEventListener('touchstart', (e) => {
            this.touchStartX = e.touches[0].clientX;
            this.touchStartY = e.touches[0].clientY;
        }, { passive: true });

        // Handle swipe gestures
        document.addEventListener('touchend', (e) => {
            const touchEndX = e.changedTouches[0].clientX;
            const touchEndY = e.changedTouches[0].clientY;
            
            const deltaX = touchEndX - this.touchStartX;
            const deltaY = touchEndY - this.touchStartY;
            
            // Only handle horizontal swipes (ignore vertical scrolling)
            if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > this.swipeThreshold) {
                if (deltaX > 0 && this.touchStartX < 30 && !this.isOpen) {
                    // Swipe right from left edge - open sidebar
                    this.open();
                } else if (deltaX < 0 && this.isOpen) {
                    // Swipe left - close sidebar
                    this.close();
                }
            }
        }, { passive: true });
    }

    /**
     * Toggles the sidebar open/closed state.
     */
    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }

    /**
     * Opens the sidebar navigation.
     */
    open() {
        this.isOpen = true;
        this.sidebar.classList.add('open');
        this.overlay.classList.add('visible');
        this.toggleButton.classList.add('active');
        this.toggleButton.setAttribute('aria-expanded', 'true');
        this.overlay.setAttribute('aria-hidden', 'false');
        
        // Prevent body scroll when sidebar is open
        document.body.style.overflow = 'hidden';
        
        // Focus first navigation link
        const firstLink = this.sidebar.querySelector('.ts-sidebar-nav-link');
        if (firstLink) {
            firstLink.focus();
        }
    }

    /**
     * Closes the sidebar navigation.
     */
    close() {
        this.isOpen = false;
        this.sidebar.classList.remove('open');
        this.overlay.classList.remove('visible');
        this.toggleButton.classList.remove('active');
        this.toggleButton.setAttribute('aria-expanded', 'false');
        this.overlay.setAttribute('aria-hidden', 'true');
        
        // Restore body scroll
        document.body.style.overflow = '';
    }

    /**
     * Handles navigation link clicks.
     * @param {Event} e - The click event.
     * @param {HTMLElement} link - The clicked link element.
     */
    handleNavLinkClick(e, link) {
        const targetId = link.getAttribute('href').substring(1);
        const targetElement = document.getElementById(targetId);
        
        if (targetElement) {
            e.preventDefault();
            
            // Close sidebar first
            this.close();
            
            // Smooth scroll to target
            setTimeout(() => {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }, 300);
            
            // Update active state
            this.setActiveLink(link);
        }
    }

    /**
     * Sets the active navigation link.
     * @param {HTMLElement} activeLink - The link to mark as active.
     */
    setActiveLink(activeLink) {
        const allLinks = this.sidebar.querySelectorAll('.ts-sidebar-nav-link');
        allLinks.forEach(link => {
            link.classList.remove('active');
        });
        activeLink.classList.add('active');
    }

    /**
     * Handles keyboard navigation within the sidebar.
     * @param {KeyboardEvent} e - The keyboard event.
     */
    handleKeyboardNavigation(e) {
        const links = Array.from(this.sidebar.querySelectorAll('.ts-sidebar-nav-link'));
        const currentIndex = links.indexOf(document.activeElement);
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                if (currentIndex < links.length - 1) {
                    links[currentIndex + 1].focus();
                }
                break;
            case 'ArrowUp':
                e.preventDefault();
                if (currentIndex > 0) {
                    links[currentIndex - 1].focus();
                }
                break;
            case 'Home':
                e.preventDefault();
                links[0].focus();
                break;
            case 'End':
                e.preventDefault();
                links[links.length - 1].focus();
                break;
        }
    }

    /**
     * Handles window resize events.
     * Closes sidebar on larger screens.
     */
    handleResize() {
        if (window.innerWidth > 768 && this.isOpen) {
            this.close();
        }
    }

    /**
     * Updates navigation links based on visible sections.
     * Hides links for sections that don't exist or are hidden.
     */
    updateNavigationLinks() {
        const navLinks = this.sidebar.querySelectorAll('.ts-sidebar-nav-link');
        navLinks.forEach(link => {
            const targetId = link.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            const listItem = link.parentElement;
            
            if (!targetElement || targetElement.style.display === 'none') {
                listItem.style.display = 'none';
            } else {
                listItem.style.display = '';
            }
        });
    }
}

/**
 * Touch interaction enhancer for better mobile experience.
 */
class TouchInteractionManager {
    constructor() {
        this.activeElement = null;
    }

    /**
     * Initializes touch interaction enhancements.
     */
    init() {
        this.enhanceCollapsibles();
        this.enhanceTabs();
        this.enhanceButtons();
    }

    /**
     * Enhances collapsible elements for touch interaction.
     */
    enhanceCollapsibles() {
        const collapsibleButtons = document.querySelectorAll(
            '.mojo-collapsible-button, .mojo-collapsible-lvl2-button, .mojo-collapsible-lvl3-button, ' +
            '.ts-errors-collapsible-button, .ts-failures-collapsible-button'
        );
        
        collapsibleButtons.forEach(button => {
            button.classList.add('ts-touch-target', 'ts-touch-feedback', 'ts-no-select');
        });
    }

    /**
     * Enhances tab elements for touch interaction.
     */
    enhanceTabs() {
        const tabLabels = document.querySelectorAll('.mojo-tab-label');
        tabLabels.forEach(tab => {
            tab.classList.add('ts-touch-target', 'ts-touch-feedback', 'ts-no-select');
        });
    }

    /**
     * Enhances button elements for touch interaction.
     */
    enhanceButtons() {
        const buttons = document.querySelectorAll(
            '.ts-filter-btn, .ts-export-btn, .ts-date-clear, .ts-search-clear'
        );
        buttons.forEach(button => {
            button.classList.add('ts-touch-target', 'ts-touch-feedback');
        });
    }
}

/**
 * Viewport manager for responsive layout adjustments.
 */
class ViewportManager {
    constructor() {
        this.viewportMeta = null;
    }

    /**
     * Initializes viewport management.
     */
    init() {
        this.ensureViewportMeta();
        this.handleOrientationChange();
    }

    /**
     * Ensures the viewport meta tag exists with proper settings.
     */
    ensureViewportMeta() {
        this.viewportMeta = document.querySelector('meta[name="viewport"]');
        
        if (!this.viewportMeta) {
            this.viewportMeta = document.createElement('meta');
            this.viewportMeta.name = 'viewport';
            this.viewportMeta.content = 'width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes';
            document.head.appendChild(this.viewportMeta);
        }
    }

    /**
     * Handles orientation change events.
     */
    handleOrientationChange() {
        window.addEventListener('orientationchange', () => {
            // Force layout recalculation after orientation change
            setTimeout(() => {
                window.scrollTo(0, window.scrollY);
            }, 100);
        });
    }
}

// Global responsive manager instances
let g_responsiveNavManager = null;
let g_touchInteractionManager = null;
let g_viewportManager = null;

/**
 * Initializes all responsive design functionality.
 * Should be called after page load.
 */
function init_responsive_design() {
    // Initialize viewport manager
    g_viewportManager = new ViewportManager();
    g_viewportManager.init();
    
    // Initialize responsive navigation
    g_responsiveNavManager = new ResponsiveNavManager();
    g_responsiveNavManager.init();
    
    // Initialize touch interactions
    g_touchInteractionManager = new TouchInteractionManager();
    g_touchInteractionManager.init();
    
    console.log("Responsive design initialized");
}

/**
 * Updates the responsive navigation based on current page state.
 * Should be called after dynamic content changes.
 */
function update_responsive_navigation() {
    if (g_responsiveNavManager) {
        g_responsiveNavManager.updateNavigationLinks();
    }
    
    if (g_touchInteractionManager) {
        g_touchInteractionManager.init();
    }
}

// Export functions for use in other modules
if (typeof window !== 'undefined') {
    window.init_responsive_design = init_responsive_design;
    window.update_responsive_navigation = update_responsive_navigation;
}
