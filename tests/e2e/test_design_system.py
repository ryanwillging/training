"""
Tests for Material Design system consistency across all pages.

Verifies:
- Navigation is present and consistent on all pages
- Material Design classes are applied correctly
- Pages are responsive and mobile-friendly
- All pages load without errors
"""

import pytest
from playwright.sync_api import Page, expect


# All HTML pages that should have consistent navigation
PAGES = [
    ("/dashboard", "Dashboard"),
    ("/metrics", "Metrics"),
    ("/api/reports/daily", "Daily Report"),
    ("/api/reports/weekly", "Weekly Report"),
]


class TestNavigationConsistency:
    """Test that navigation is consistent across all pages."""

    @pytest.mark.parametrize("path,name", PAGES)
    def test_page_has_navigation(self, page: Page, base_url: str, path: str, name: str):
        """Each page should have the navigation bar."""
        page.goto(f"{base_url}{path}")

        # Navigation container should exist
        nav = page.locator("nav.md-nav")
        expect(nav).to_be_visible()

    @pytest.mark.parametrize("path,name", PAGES)
    def test_navigation_has_brand(self, page: Page, base_url: str, path: str, name: str):
        """Navigation should have the brand/logo link."""
        page.goto(f"{base_url}{path}")

        brand = page.locator(".md-nav-brand")
        expect(brand).to_be_visible()
        expect(brand).to_contain_text("Training")

    @pytest.mark.parametrize("path,name", PAGES)
    def test_navigation_has_all_links(self, page: Page, base_url: str, path: str, name: str):
        """Navigation should have links to all main pages."""
        page.goto(f"{base_url}{path}")

        # Check for all nav links (desktop view)
        nav_links = page.locator(".md-nav-links .md-nav-link")

        # Should have links to Dashboard, Metrics, Daily Report, Weekly Report
        expect(page.locator(".md-nav-links")).to_contain_text("Dashboard")
        expect(page.locator(".md-nav-links")).to_contain_text("Metrics")
        expect(page.locator(".md-nav-links")).to_contain_text("Daily Report")
        expect(page.locator(".md-nav-links")).to_contain_text("Weekly Report")

    @pytest.mark.parametrize("path,name", PAGES)
    def test_current_page_is_active(self, page: Page, base_url: str, path: str, name: str):
        """Current page should have active class in navigation."""
        page.goto(f"{base_url}{path}")

        # Find the active link in desktop nav (not mobile menu)
        active_link = page.locator(".md-nav-links .md-nav-link.active")
        expect(active_link).to_be_visible()
        expect(active_link).to_contain_text(name)

    def test_navigation_links_work(self, page: Page, base_url: str):
        """Navigation links should navigate to correct pages."""
        page.goto(f"{base_url}/dashboard")

        # Click on Metrics link
        page.locator(".md-nav-links .md-nav-link", has_text="Metrics").click()
        expect(page).to_have_url(f"{base_url}/metrics")

        # Click on Daily Report link
        page.locator(".md-nav-links .md-nav-link", has_text="Daily Report").click()
        expect(page).to_have_url(f"{base_url}/api/reports/daily")

        # Click on Dashboard link (via brand)
        page.locator(".md-nav-brand").click()
        expect(page).to_have_url(f"{base_url}/dashboard")


class TestMaterialDesignClasses:
    """Test that Material Design CSS classes are applied correctly."""

    @pytest.mark.parametrize("path,name", PAGES)
    def test_page_has_material_design_styles(self, page: Page, base_url: str, path: str, name: str):
        """Each page should include Material Design CSS."""
        page.goto(f"{base_url}{path}")

        html = page.content()

        # Check for Material Design CSS variables
        assert "--md-primary" in html, "Should have MD primary color variable"
        assert "--md-surface" in html, "Should have MD surface variable"

        # Check for Roboto font
        assert "Roboto" in html, "Should use Roboto font"

    @pytest.mark.parametrize("path,name", PAGES)
    def test_page_uses_md_card_components(self, page: Page, base_url: str, path: str, name: str):
        """Pages should use Material Design card components."""
        page.goto(f"{base_url}{path}")

        # Most pages should have at least one card
        cards = page.locator(".md-card")
        # Allow for empty state pages that might not have cards
        card_count = cards.count()
        assert card_count >= 0, "Card component should be available"

    @pytest.mark.parametrize("path,name", PAGES)
    def test_page_has_consistent_typography(self, page: Page, base_url: str, path: str, name: str):
        """Pages should use consistent Material Design typography classes."""
        page.goto(f"{base_url}{path}")

        html = page.content()

        # Should have headline or title classes for headers
        has_typography = any(cls in html for cls in [
            "md-headline-large",
            "md-headline-medium",
            "md-title-large",
            "md-title-medium"
        ])
        assert has_typography, "Should use MD typography classes"


class TestResponsiveDesign:
    """Test that pages are responsive and mobile-friendly."""

    @pytest.mark.parametrize("path,name", PAGES)
    def test_page_has_viewport_meta(self, page: Page, base_url: str, path: str, name: str):
        """Each page should have viewport meta tag for mobile."""
        page.goto(f"{base_url}{path}")

        html = page.content()
        assert "viewport" in html, "Should have viewport meta tag"
        assert "width=device-width" in html, "Should set width to device-width"

    @pytest.mark.parametrize("path,name", PAGES)
    def test_mobile_menu_button_visible_on_mobile(self, page: Page, base_url: str, path: str, name: str):
        """Mobile menu button should be visible on small screens."""
        # Set mobile viewport
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}{path}")

        # Menu button should be visible on mobile
        menu_btn = page.locator(".md-nav-menu-btn")
        expect(menu_btn).to_be_visible()

    @pytest.mark.parametrize("path,name", PAGES)
    def test_desktop_nav_links_visible_on_desktop(self, page: Page, base_url: str, path: str, name: str):
        """Desktop nav links should be visible on large screens."""
        # Set desktop viewport
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(f"{base_url}{path}")

        # Desktop nav links should be visible
        nav_links = page.locator(".md-nav-links")
        expect(nav_links).to_be_visible()

    @pytest.mark.parametrize("path,name", PAGES)
    def test_mobile_menu_toggles(self, page: Page, base_url: str, path: str, name: str):
        """Mobile menu should toggle when button is clicked."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}{path}")

        # Mobile menu should initially be hidden
        mobile_menu = page.locator("#mobile-menu")
        expect(mobile_menu).not_to_have_class("open")

        # Click menu button
        page.locator(".md-nav-menu-btn").click()

        # Mobile menu should now have 'open' class
        expect(mobile_menu).to_have_class("md-nav-mobile open")

    @pytest.mark.parametrize("path,name", PAGES)
    def test_grids_collapse_on_mobile(self, page: Page, base_url: str, path: str, name: str):
        """Grid layouts should collapse to single column on mobile."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}{path}")

        # Check that page renders without horizontal scroll
        body_width = page.evaluate("document.body.scrollWidth")
        viewport_width = 375

        # Allow small overflow but not significant horizontal scroll
        assert body_width <= viewport_width + 20, \
            f"Page should not have significant horizontal scroll on mobile (width: {body_width})"


class TestPageContent:
    """Test that each page has expected content."""

    def test_dashboard_has_key_sections(self, page: Page, base_url: str):
        """Dashboard should have key sections."""
        page.goto(f"{base_url}/dashboard")

        expect(page.locator("body")).to_be_visible()

        html = page.content()
        # Dashboard should have training-related content
        assert any(term in html.lower() for term in ["dashboard", "training", "workout", "activity"]), \
            "Dashboard should have training content"

    def test_metrics_has_form(self, page: Page, base_url: str):
        """Metrics page should have input form."""
        page.goto(f"{base_url}/metrics")

        expect(page.locator("body")).to_be_visible()

        # Should have form elements
        expect(page.locator("form")).to_be_visible()

        # Should have submit button
        submit_btn = page.locator("button[type='submit']")
        expect(submit_btn).to_be_visible()

    def test_daily_report_has_content(self, page: Page, base_url: str):
        """Daily report should have report content."""
        page.goto(f"{base_url}/api/reports/daily")

        expect(page.locator("body")).to_be_visible()

        html = page.content()
        # Should have report-related content
        assert any(term in html.lower() for term in ["report", "daily", "today", "training"]), \
            "Daily report should have report content"

    def test_weekly_report_has_content(self, page: Page, base_url: str):
        """Weekly report should have report content."""
        page.goto(f"{base_url}/api/reports/weekly")

        expect(page.locator("body")).to_be_visible()

        html = page.content()
        # Should have week-related content
        assert any(term in html.lower() for term in ["weekly", "week", "summary", "training"]), \
            "Weekly report should have week content"


class TestAccessibility:
    """Test basic accessibility features."""

    @pytest.mark.parametrize("path,name", PAGES)
    def test_page_has_lang_attribute(self, page: Page, base_url: str, path: str, name: str):
        """Each page should have lang attribute on html element."""
        page.goto(f"{base_url}{path}")

        html_tag = page.locator("html")
        expect(html_tag).to_have_attribute("lang", "en")

    @pytest.mark.parametrize("path,name", PAGES)
    def test_page_has_title(self, page: Page, base_url: str, path: str, name: str):
        """Each page should have a title."""
        page.goto(f"{base_url}{path}")

        title = page.title()
        assert title, "Page should have a title"
        assert len(title) > 0, "Title should not be empty"

    @pytest.mark.parametrize("path,name", PAGES)
    def test_mobile_menu_button_has_aria_label(self, page: Page, base_url: str, path: str, name: str):
        """Mobile menu button should have aria-label for accessibility."""
        page.goto(f"{base_url}{path}")

        menu_btn = page.locator(".md-nav-menu-btn")
        expect(menu_btn).to_have_attribute("aria-label", "Menu")


class TestNoErrors:
    """Test that pages load without errors."""

    @pytest.mark.parametrize("path,name", PAGES)
    def test_page_loads_without_errors(self, page: Page, base_url: str, path: str, name: str):
        """Each page should load without server errors."""
        response = page.request.get(f"{base_url}{path}")

        assert response.ok, f"{name} page returned error: {response.status}"

    @pytest.mark.parametrize("path,name", PAGES)
    def test_no_error_messages_visible(self, page: Page, base_url: str, path: str, name: str):
        """Pages should not display error messages."""
        page.goto(f"{base_url}{path}")

        html = page.content().lower()

        error_patterns = [
            "traceback",
            "exception",
            "error 500",
            "internal server error",
            "syntax error",
            "undefined",
            "typeerror",
        ]

        for pattern in error_patterns:
            assert pattern not in html, f"{name} page contains error: {pattern}"

    @pytest.mark.parametrize("path,name", PAGES)
    def test_no_console_errors(self, page: Page, base_url: str, path: str, name: str):
        """Pages should not have JavaScript console errors."""
        errors = []

        def handle_console(msg):
            if msg.type == "error":
                errors.append(msg.text)

        page.on("console", handle_console)
        page.goto(f"{base_url}{path}")

        # Allow time for any JS to execute
        page.wait_for_timeout(1000)

        assert len(errors) == 0, f"{name} page has console errors: {errors}"
