"""
Material Design-inspired design system for consistent UI across all pages.

This module provides CSS styles, component helpers, and layout utilities
following Material Design 3 principles for server-rendered HTML pages.
"""

from typing import Optional

# Material Design 3 Color Palette
COLORS = {
    # Primary
    "primary": "#1976d2",
    "primary-light": "#42a5f5",
    "primary-dark": "#1565c0",
    "on-primary": "#ffffff",

    # Secondary
    "secondary": "#9c27b0",
    "secondary-light": "#ba68c8",
    "secondary-dark": "#7b1fa2",
    "on-secondary": "#ffffff",

    # Surface & Background
    "surface": "#ffffff",
    "surface-variant": "#f5f5f5",
    "background": "#fafafa",
    "on-surface": "#1c1b1f",
    "on-surface-variant": "#49454f",

    # Outline & Dividers
    "outline": "#79747e",
    "outline-variant": "#cac4d0",

    # Status Colors
    "success": "#2e7d32",
    "success-light": "#4caf50",
    "warning": "#ed6c02",
    "warning-light": "#ff9800",
    "error": "#d32f2f",
    "error-light": "#ef5350",
    "info": "#0288d1",
    "info-light": "#03a9f4",
}

# Workout Type Styling (icons, labels, colors)
WORKOUT_STYLES = {
    "swim_a": {"icon": "🏊", "label": "Swim A", "color": "#1976d2"},
    "swim_b": {"icon": "🏊", "label": "Swim B", "color": "#1565c0"},
    "swim_test": {"icon": "🏊‍♂️", "label": "400 TT Test", "color": "#0d47a1"},
    "lift_a": {"icon": "🏋️", "label": "Lift A (Lower)", "color": "#388e3c"},
    "lift_b": {"icon": "🏋️", "label": "Lift B (Upper)", "color": "#2e7d32"},
    "vo2": {"icon": "🫀", "label": "VO2 Session", "color": "#d32f2f"},
}

# Review Status Styling
STATUS_COLORS = {
    "pending": {"bg": "#fff3e0", "text": "#e65100", "label": "Pending Review"},
    "approved": {"bg": "#e8f5e9", "text": "#2e7d32", "label": "Approved"},
    "rejected": {"bg": "#ffebee", "text": "#c62828", "label": "Rejected"},
    "no_changes_needed": {"bg": "#e3f2fd", "text": "#1565c0", "label": "No Changes Needed"},
    "error": {"bg": "#fce4ec", "text": "#c62828", "label": "Evaluation Failed"},
}

EVAL_TYPE_STYLES = {
    "nightly": {"bg": "#e8eaf6", "text": "#3949ab", "icon": "🌙", "label": "Nightly"},
    "on_demand": {"bg": "#e0f2f1", "text": "#00796b", "icon": "👆", "label": "On-Demand"},
}

SEVERITY_STYLES = {
    "info": {"bg": "#e3f2fd", "text": "#1565c0", "icon": "ℹ️"},
    "warning": {"bg": "#fff3e0", "text": "#e65100", "icon": "⚠️"},
    "alert": {"bg": "#ffebee", "text": "#c62828", "icon": "🚨"},
}

ASSESSMENT_COLORS = {
    "on_track": {"bg": "#e8f5e9", "text": "#2e7d32", "icon": "✓"},
    "needs_adjustment": {"bg": "#fff3e0", "text": "#e65100", "icon": "⚠"},
    "significant_changes_needed": {"bg": "#ffebee", "text": "#c62828", "icon": "!"},
    "error": {"bg": "#fce4ec", "text": "#c62828", "icon": "✗"},
    "parse_error": {"bg": "#fce4ec", "text": "#c62828", "icon": "✗"},
}

PRIORITY_COLORS = {
    "high": {"bg": "#ffebee", "text": "#c62828"},
    "medium": {"bg": "#fff3e0", "text": "#e65100"},
    "low": {"bg": "#e3f2fd", "text": "#1565c0"},
}


def get_workout_status_css() -> str:
    """Generate CSS for workout status badges."""
    return """
    .workout-status.completed {
        background: #e8f5e9;
        color: #2e7d32;
    }
    .workout-status.skipped {
        background: #fff3e0;
        color: #e65100;
    }
    .workout-status.synced {
        background: #e3f2fd;
        color: #1565c0;
    }
    """


def get_base_css() -> str:
    """
    Return the base CSS framework with Material Design styles.
    Includes CSS reset, typography, spacing utilities, and responsive breakpoints.
    """
    return """
/* ===== CSS Reset & Base ===== */
*, *::before, *::after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

html {
    font-size: 16px;
    -webkit-text-size-adjust: 100%;
}

body {
    font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    font-size: 1rem;
    line-height: 1.5;
    color: #1c1b1f;
    background-color: #fafafa;
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* ===== CSS Variables (Material Design 3) ===== */
:root {
    /* Colors */
    --md-primary: #1976d2;
    --md-primary-light: #42a5f5;
    --md-primary-dark: #1565c0;
    --md-on-primary: #ffffff;

    --md-secondary: #9c27b0;
    --md-on-secondary: #ffffff;

    --md-surface: #ffffff;
    --md-surface-variant: #f5f5f5;
    --md-background: #fafafa;
    --md-on-surface: #1c1b1f;
    --md-on-surface-variant: #49454f;

    --md-outline: #79747e;
    --md-outline-variant: #e0e0e0;

    --md-success: #2e7d32;
    --md-warning: #ed6c02;
    --md-error: #d32f2f;
    --md-info: #0288d1;

    /* Elevation shadows */
    --md-elevation-1: 0 1px 2px rgba(0,0,0,0.3), 0 1px 3px 1px rgba(0,0,0,0.15);
    --md-elevation-2: 0 1px 2px rgba(0,0,0,0.3), 0 2px 6px 2px rgba(0,0,0,0.15);
    --md-elevation-3: 0 4px 8px 3px rgba(0,0,0,0.15), 0 1px 3px rgba(0,0,0,0.3);

    /* Spacing scale (4px base) */
    --spacing-1: 4px;
    --spacing-2: 8px;
    --spacing-3: 12px;
    --spacing-4: 16px;
    --spacing-5: 20px;
    --spacing-6: 24px;
    --spacing-8: 32px;
    --spacing-10: 40px;
    --spacing-12: 48px;

    /* Border radius */
    --radius-xs: 4px;
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-xl: 28px;
    --radius-full: 9999px;

    /* Typography */
    --font-display: 'Roboto', sans-serif;
    --font-body: 'Roboto', sans-serif;

    /* Transitions */
    --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
    --transition-medium: 250ms cubic-bezier(0.4, 0, 0.2, 1);
    --transition-slow: 350ms cubic-bezier(0.4, 0, 0.2, 1);

    /* Container widths */
    --container-sm: 640px;
    --container-md: 768px;
    --container-lg: 1024px;
    --container-xl: 1280px;
}

/* ===== Typography ===== */
.md-display-large {
    font-size: 3.5625rem;
    line-height: 4rem;
    font-weight: 400;
    letter-spacing: -0.25px;
}

.md-display-medium {
    font-size: 2.8125rem;
    line-height: 3.25rem;
    font-weight: 400;
}

.md-display-small {
    font-size: 2.25rem;
    line-height: 2.75rem;
    font-weight: 400;
}

.md-headline-large {
    font-size: 2rem;
    line-height: 2.5rem;
    font-weight: 400;
}

.md-headline-medium {
    font-size: 1.75rem;
    line-height: 2.25rem;
    font-weight: 400;
}

.md-headline-small {
    font-size: 1.5rem;
    line-height: 2rem;
    font-weight: 400;
}

.md-title-large {
    font-size: 1.375rem;
    line-height: 1.75rem;
    font-weight: 500;
}

.md-title-medium {
    font-size: 1rem;
    line-height: 1.5rem;
    font-weight: 500;
    letter-spacing: 0.15px;
}

.md-title-small {
    font-size: 0.875rem;
    line-height: 1.25rem;
    font-weight: 500;
    letter-spacing: 0.1px;
}

.md-body-large {
    font-size: 1rem;
    line-height: 1.5rem;
    font-weight: 400;
    letter-spacing: 0.5px;
}

.md-body-medium {
    font-size: 0.875rem;
    line-height: 1.25rem;
    font-weight: 400;
    letter-spacing: 0.25px;
}

.md-body-small {
    font-size: 0.75rem;
    line-height: 1rem;
    font-weight: 400;
    letter-spacing: 0.4px;
}

.md-label-large {
    font-size: 0.875rem;
    line-height: 1.25rem;
    font-weight: 500;
    letter-spacing: 0.1px;
}

.md-label-medium {
    font-size: 0.75rem;
    line-height: 1rem;
    font-weight: 500;
    letter-spacing: 0.5px;
}

.md-label-small {
    font-size: 0.6875rem;
    line-height: 1rem;
    font-weight: 500;
    letter-spacing: 0.5px;
}

/* ===== Layout ===== */
.md-container {
    width: 100%;
    max-width: var(--container-xl);
    margin: 0 auto;
    padding: 0 var(--spacing-4);
}

@media (min-width: 640px) {
    .md-container {
        padding: 0 var(--spacing-6);
    }
}

@media (min-width: 1024px) {
    .md-container {
        padding: 0 var(--spacing-8);
    }
}

.md-page {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

.md-main {
    flex: 1;
    padding: var(--spacing-4) 0;
}

@media (min-width: 640px) {
    .md-main {
        padding: var(--spacing-6) 0;
    }
}

/* ===== Grid System ===== */
.md-grid {
    display: grid;
    gap: var(--spacing-4);
}

.md-grid-cols-1 { grid-template-columns: repeat(1, minmax(0, 1fr)); }
.md-grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.md-grid-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.md-grid-cols-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }

@media (max-width: 639px) {
    .md-grid-cols-2,
    .md-grid-cols-3,
    .md-grid-cols-4 {
        grid-template-columns: repeat(1, minmax(0, 1fr));
    }
}

@media (min-width: 640px) and (max-width: 1023px) {
    .md-grid-cols-3,
    .md-grid-cols-4 {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}

.md-flex { display: flex; }
.md-flex-col { flex-direction: column; }
.md-flex-wrap { flex-wrap: wrap; }
.md-items-center { align-items: center; }
.md-items-start { align-items: flex-start; }
.md-justify-between { justify-content: space-between; }
.md-justify-center { justify-content: center; }
.md-gap-2 { gap: var(--spacing-2); }
.md-gap-3 { gap: var(--spacing-3); }
.md-gap-4 { gap: var(--spacing-4); }
.md-gap-6 { gap: var(--spacing-6); }

/* ===== Cards ===== */
.md-card {
    background: var(--md-surface);
    border-radius: var(--radius-md);
    box-shadow: var(--md-elevation-1);
    overflow: hidden;
}

.md-card-elevated {
    box-shadow: var(--md-elevation-2);
}

.md-card-outlined {
    box-shadow: none;
    border: 1px solid var(--md-outline-variant);
}

.md-card-header {
    padding: var(--spacing-4);
    border-bottom: 1px solid var(--md-outline-variant);
}

.md-card-content {
    padding: var(--spacing-4);
}

.md-card-actions {
    padding: var(--spacing-2) var(--spacing-4);
    display: flex;
    gap: var(--spacing-2);
    justify-content: flex-end;
}

/* ===== Buttons ===== */
.md-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--spacing-2);
    padding: var(--spacing-2) var(--spacing-6);
    font-size: 0.875rem;
    font-weight: 500;
    letter-spacing: 0.1px;
    line-height: 1.25rem;
    border: none;
    border-radius: var(--radius-full);
    cursor: pointer;
    transition: background-color var(--transition-fast), box-shadow var(--transition-fast);
    text-decoration: none;
    white-space: nowrap;
    min-height: 40px;
}

.md-btn:focus-visible {
    outline: 2px solid var(--md-primary);
    outline-offset: 2px;
}

.md-btn-filled {
    background: var(--md-primary);
    color: var(--md-on-primary);
}

.md-btn-filled:hover {
    box-shadow: var(--md-elevation-1);
    background: var(--md-primary-dark);
}

.md-btn-outlined {
    background: transparent;
    color: var(--md-primary);
    border: 1px solid var(--md-outline);
}

.md-btn-outlined:hover {
    background: rgba(25, 118, 210, 0.08);
}

.md-btn-text {
    background: transparent;
    color: var(--md-primary);
    padding: var(--spacing-2) var(--spacing-3);
}

.md-btn-text:hover {
    background: rgba(25, 118, 210, 0.08);
}

.md-btn-icon {
    padding: var(--spacing-2);
    min-height: 40px;
    min-width: 40px;
    border-radius: var(--radius-full);
}

/* ===== Form Controls ===== */
.md-form-group {
    margin-bottom: var(--spacing-4);
}

.md-label {
    display: block;
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--md-on-surface);
    margin-bottom: var(--spacing-1);
}

.md-input,
.md-select,
.md-textarea {
    width: 100%;
    padding: var(--spacing-3) var(--spacing-4);
    font-size: 1rem;
    line-height: 1.5;
    color: var(--md-on-surface);
    background: var(--md-surface);
    border: 1px solid var(--md-outline);
    border-radius: var(--radius-xs);
    transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.md-input:hover,
.md-select:hover,
.md-textarea:hover {
    border-color: var(--md-on-surface);
}

.md-input:focus,
.md-select:focus,
.md-textarea:focus {
    outline: none;
    border-color: var(--md-primary);
    box-shadow: 0 0 0 1px var(--md-primary);
}

.md-input::placeholder {
    color: var(--md-on-surface-variant);
}

.md-hint {
    font-size: 0.75rem;
    color: var(--md-on-surface-variant);
    margin-top: var(--spacing-1);
}

/* ===== Tables ===== */
.md-table-container {
    overflow-x: auto;
    border-radius: var(--radius-sm);
    border: 1px solid var(--md-outline-variant);
}

.md-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
}

.md-table th {
    text-align: left;
    padding: var(--spacing-3) var(--spacing-4);
    font-weight: 500;
    color: var(--md-on-surface-variant);
    background: var(--md-surface-variant);
    border-bottom: 1px solid var(--md-outline-variant);
    white-space: nowrap;
}

.md-table td {
    padding: var(--spacing-3) var(--spacing-4);
    border-bottom: 1px solid var(--md-outline-variant);
    color: var(--md-on-surface);
}

.md-table tr:last-child td {
    border-bottom: none;
}

.md-table tr:hover td {
    background: rgba(0, 0, 0, 0.04);
}

.md-table .text-right {
    text-align: right;
}

.md-table .text-center {
    text-align: center;
}

/* ===== Chips ===== */
.md-chip {
    display: inline-flex;
    align-items: center;
    gap: var(--spacing-1);
    padding: var(--spacing-1) var(--spacing-3);
    font-size: 0.75rem;
    font-weight: 500;
    border-radius: var(--radius-sm);
    background: var(--md-surface-variant);
    color: var(--md-on-surface-variant);
}

.md-chip-primary {
    background: rgba(25, 118, 210, 0.12);
    color: var(--md-primary);
}

.md-chip-success {
    background: rgba(46, 125, 50, 0.12);
    color: var(--md-success);
}

.md-chip-warning {
    background: rgba(237, 108, 2, 0.12);
    color: var(--md-warning);
}

.md-chip-error {
    background: rgba(211, 47, 47, 0.12);
    color: var(--md-error);
}

/* ===== Progress Indicators ===== */
.md-progress {
    height: 4px;
    background: var(--md-surface-variant);
    border-radius: var(--radius-full);
    overflow: hidden;
}

.md-progress-bar {
    height: 100%;
    background: var(--md-primary);
    border-radius: var(--radius-full);
    transition: width var(--transition-medium);
}

.md-progress-success .md-progress-bar {
    background: var(--md-success);
}

.md-progress-warning .md-progress-bar {
    background: var(--md-warning);
}

.md-progress-error .md-progress-bar {
    background: var(--md-error);
}

/* ===== Stats/Metrics ===== */
.md-stat {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-1);
}

.md-stat-value {
    font-size: 2rem;
    font-weight: 500;
    line-height: 1.2;
    color: var(--md-on-surface);
}

.md-stat-label {
    font-size: 0.75rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--md-on-surface-variant);
}

.md-stat-change {
    font-size: 0.75rem;
    display: flex;
    align-items: center;
    gap: var(--spacing-1);
}

.md-stat-change.positive {
    color: var(--md-success);
}

.md-stat-change.negative {
    color: var(--md-error);
}

/* ===== Dividers ===== */
.md-divider {
    height: 1px;
    background: var(--md-outline-variant);
    border: none;
    margin: var(--spacing-4) 0;
}

/* ===== Lists ===== */
.md-list {
    list-style: none;
}

.md-list-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-4);
    padding: var(--spacing-3) var(--spacing-4);
    border-bottom: 1px solid var(--md-outline-variant);
    transition: background var(--transition-fast);
}

.md-list-item:last-child {
    border-bottom: none;
}

.md-list-item:hover {
    background: rgba(0, 0, 0, 0.04);
}

.md-list-item-content {
    flex: 1;
    min-width: 0;
}

.md-list-item-primary {
    font-size: 1rem;
    font-weight: 400;
    color: var(--md-on-surface);
}

.md-list-item-secondary {
    font-size: 0.875rem;
    color: var(--md-on-surface-variant);
}

/* ===== Alerts/Banners ===== */
.md-alert {
    padding: var(--spacing-4);
    border-radius: var(--radius-sm);
    display: flex;
    gap: var(--spacing-3);
    align-items: flex-start;
}

.md-alert-info {
    background: rgba(2, 136, 209, 0.12);
    color: var(--md-info);
}

.md-alert-success {
    background: rgba(46, 125, 50, 0.12);
    color: var(--md-success);
}

.md-alert-warning {
    background: rgba(237, 108, 2, 0.12);
    color: var(--md-warning);
}

.md-alert-error {
    background: rgba(211, 47, 47, 0.12);
    color: var(--md-error);
}

/* ===== Utility Classes ===== */
.text-primary { color: var(--md-primary); }
.text-secondary { color: var(--md-on-surface-variant); }
.text-success { color: var(--md-success); }
.text-warning { color: var(--md-warning); }
.text-error { color: var(--md-error); }

.bg-surface { background: var(--md-surface); }
.bg-surface-variant { background: var(--md-surface-variant); }

.mt-2 { margin-top: var(--spacing-2); }
.mt-4 { margin-top: var(--spacing-4); }
.mt-6 { margin-top: var(--spacing-6); }
.mb-2 { margin-bottom: var(--spacing-2); }
.mb-4 { margin-bottom: var(--spacing-4); }
.mb-6 { margin-bottom: var(--spacing-6); }
.my-4 { margin-top: var(--spacing-4); margin-bottom: var(--spacing-4); }
.mx-auto { margin-left: auto; margin-right: auto; }

.p-2 { padding: var(--spacing-2); }
.p-4 { padding: var(--spacing-4); }
.p-6 { padding: var(--spacing-6); }
.px-4 { padding-left: var(--spacing-4); padding-right: var(--spacing-4); }
.py-4 { padding-top: var(--spacing-4); padding-bottom: var(--spacing-4); }

.rounded { border-radius: var(--radius-sm); }
.rounded-md { border-radius: var(--radius-md); }
.rounded-lg { border-radius: var(--radius-lg); }

.shadow { box-shadow: var(--md-elevation-1); }
.shadow-md { box-shadow: var(--md-elevation-2); }
.shadow-lg { box-shadow: var(--md-elevation-3); }

.w-full { width: 100%; }
.h-full { height: 100%; }
.min-h-screen { min-height: 100vh; }

.overflow-hidden { overflow: hidden; }
.overflow-auto { overflow: auto; }
.overflow-x-auto { overflow-x: auto; }

.truncate {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    border: 0;
}

/* ===== Mobile-specific adjustments ===== */
@media (max-width: 639px) {
    .md-stat-value {
        font-size: 1.5rem;
    }

    .md-card-content {
        padding: var(--spacing-3);
    }

    .md-table th,
    .md-table td {
        padding: var(--spacing-2) var(--spacing-3);
    }

    .hide-mobile {
        display: none !important;
    }
}

@media (min-width: 640px) {
    .hide-desktop {
        display: none !important;
    }
}
"""


def get_nav_css() -> str:
    """Return Material Design navigation bar styles."""
    return """
/* ===== Navigation Bar ===== */
.md-nav {
    background: var(--md-surface);
    border-bottom: 1px solid var(--md-outline-variant);
    position: sticky;
    top: 0;
    z-index: 1000;
}

.md-nav-container {
    max-width: var(--container-xl);
    margin: 0 auto;
    padding: 0 var(--spacing-4);
    display: flex;
    align-items: center;
    height: 64px;
    gap: var(--spacing-2);
}

@media (min-width: 640px) {
    .md-nav-container {
        padding: 0 var(--spacing-6);
        gap: var(--spacing-4);
    }
}

.md-nav-brand {
    font-size: 1.25rem;
    font-weight: 500;
    color: var(--md-primary);
    text-decoration: none;
    display: flex;
    align-items: center;
    gap: var(--spacing-2);
    margin-right: auto;
}

.md-nav-brand:hover {
    color: var(--md-primary-dark);
}

.md-nav-links {
    display: flex;
    align-items: center;
    gap: var(--spacing-1);
}

@media (max-width: 639px) {
    .md-nav-links {
        display: none;
    }
}

.md-nav-link {
    display: flex;
    align-items: center;
    padding: var(--spacing-2) var(--spacing-3);
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--md-on-surface-variant);
    text-decoration: none;
    border-radius: var(--radius-full);
    transition: background var(--transition-fast), color var(--transition-fast);
}

.md-nav-link:hover {
    background: rgba(0, 0, 0, 0.04);
    color: var(--md-on-surface);
}

.md-nav-link.active {
    background: rgba(25, 118, 210, 0.12);
    color: var(--md-primary);
}

/* Mobile menu button */
.md-nav-menu-btn {
    display: none;
    padding: var(--spacing-2);
    background: none;
    border: none;
    border-radius: var(--radius-full);
    cursor: pointer;
    color: var(--md-on-surface);
}

@media (max-width: 639px) {
    .md-nav-menu-btn {
        display: flex;
        align-items: center;
        justify-content: center;
    }
}

.md-nav-menu-btn:hover {
    background: rgba(0, 0, 0, 0.04);
}

/* Mobile menu */
.md-nav-mobile {
    display: none;
    background: var(--md-surface);
    border-bottom: 1px solid var(--md-outline-variant);
    padding: var(--spacing-2) var(--spacing-4);
}

.md-nav-mobile.open {
    display: block;
}

@media (min-width: 640px) {
    .md-nav-mobile {
        display: none !important;
    }
}

.md-nav-mobile .md-nav-link {
    width: 100%;
    padding: var(--spacing-3) var(--spacing-4);
    border-radius: var(--radius-sm);
}
"""


def get_page_header(title: str, subtitle: Optional[str] = None) -> str:
    """Generate a consistent page header component."""
    subtitle_html = f'<p class="md-body-large text-secondary">{subtitle}</p>' if subtitle else ''
    return f'''
    <header class="mb-6">
        <h1 class="md-headline-large mb-2">{title}</h1>
        {subtitle_html}
    </header>
    '''


def get_stat_card(value: str, label: str, change: Optional[str] = None, change_positive: Optional[bool] = None) -> str:
    """Generate a statistics card component."""
    change_html = ''
    if change:
        direction = 'positive' if change_positive else 'negative' if change_positive is False else ''
        arrow = '\u2191' if change_positive else '\u2193' if change_positive is False else ''
        change_html = f'<div class="md-stat-change {direction}">{arrow} {change}</div>'

    return f'''
    <div class="md-card">
        <div class="md-card-content">
            <div class="md-stat">
                <div class="md-stat-value">{value}</div>
                <div class="md-stat-label">{label}</div>
                {change_html}
            </div>
        </div>
    </div>
    '''


def get_progress_card(title: str, current: float, target: float, unit: str = '') -> str:
    """Generate a progress card component."""
    percentage = min(100, (current / target * 100)) if target > 0 else 0
    status_class = 'md-progress-success' if percentage >= 80 else 'md-progress-warning' if percentage >= 50 else ''

    return f'''
    <div class="md-card mb-4">
        <div class="md-card-content">
            <div class="md-flex md-justify-between md-items-center mb-2">
                <span class="md-title-medium">{title}</span>
                <span class="md-body-medium text-secondary">{current}{unit} / {target}{unit}</span>
            </div>
            <div class="md-progress {status_class}">
                <div class="md-progress-bar" style="width: {percentage}%"></div>
            </div>
        </div>
    </div>
    '''


def wrap_page(content: str, title: str, current_path: Optional[str] = None) -> str:
    """
    Wrap content in a complete HTML page with Material Design styling.

    Args:
        content: The main page content HTML
        title: Page title for the browser tab
        current_path: Current path for navigation highlighting
    """
    from api.navigation import PAGES

    # Build navigation links
    nav_links = []
    mobile_links = []
    for page in PAGES:
        active = ' active' if current_path == page['path'] else ''
        nav_links.append(f'<a href="{page["path"]}" class="md-nav-link{active}">{page["name"]}</a>')
        mobile_links.append(f'<a href="{page["path"]}" class="md-nav-link{active}">{page["name"]}</a>')

    base_css = get_base_css()
    nav_css = get_nav_css()

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#1976d2">
    <title>{title} - Training</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
{base_css}
{nav_css}
    </style>
</head>
<body>
    <div class="md-page">
        <nav class="md-nav">
            <div class="md-nav-container">
                <a href="/dashboard" class="md-nav-brand">
                    <svg width="26" height="26" viewBox="0 0 24 24" fill="currentColor">
                        <rect x="2" y="9" width="3" height="6" rx="1"/>
                        <rect x="19" y="9" width="3" height="6" rx="1"/>
                        <rect x="5" y="7" width="3" height="10" rx="1"/>
                        <rect x="16" y="7" width="3" height="10" rx="1"/>
                        <rect x="8" y="11" width="8" height="2" rx="0.5"/>
                        <path d="M12 2l2 3h-4l2-3z" opacity="0.7"/>
                        <path d="M10 4l1 1.5h-2l1-1.5z" opacity="0.5"/>
                        <path d="M14 4l1 1.5h-2l1-1.5z" opacity="0.5"/>
                    </svg>
                    Training
                </a>
                <div class="md-nav-links">
                    {' '.join(nav_links)}
                </div>
                <button class="md-nav-menu-btn" onclick="document.getElementById('mobile-menu').classList.toggle('open')" aria-label="Menu">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/>
                    </svg>
                </button>
            </div>
            <div id="mobile-menu" class="md-nav-mobile">
                {' '.join(mobile_links)}
            </div>
        </nav>

        <main class="md-main">
            <div class="md-container">
                {content}
            </div>
        </main>

        <footer class="py-4" style="border-top: 1px solid var(--md-outline-variant);">
            <div class="md-container">
                <p class="md-body-small text-secondary" style="text-align: center;">
                    Training Optimization System
                </p>
            </div>
        </footer>
    </div>
</body>
</html>'''
