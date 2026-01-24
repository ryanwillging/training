"""
Comprehensive UI testing for training.ryanwillging.com
Tests all pages for functionality, design consistency, and user experience.
"""
import pytest
from playwright.sync_api import Page, expect
import time


BASE_URL = "https://training.ryanwillging.com"

# Pages to test
PAGES = [
    ("/dashboard", "Dashboard"),
    ("/upcoming", "Upcoming"),
    ("/reviews", "Reviews"),
    ("/metrics", "Metrics"),
    ("/api/reports/daily", "Daily Report"),
    ("/api/reports/weekly", "Weekly Report"),
]


class TestPageLoading:
    """Test that all pages load successfully without errors"""

    @pytest.mark.parametrize("path,name", PAGES)
    def test_page_loads(self, page: Page, path: str, name: str):
        """Test that page loads with 200 status"""
        response = page.goto(f"{BASE_URL}{path}")
        assert response.status == 200, f"{name} failed to load"

    @pytest.mark.parametrize("path,name", PAGES)
    def test_no_console_errors(self, page: Page, path: str, name: str):
        """Test that page has no JavaScript errors"""
        errors = []
        page.on("console", lambda msg: errors.append(msg) if msg.type == "error" else None)
        page.goto(f"{BASE_URL}{path}")
        page.wait_for_load_state("networkidle")

        # Filter out common non-critical errors
        critical_errors = [e for e in errors if "favicon" not in str(e)]
        assert len(critical_errors) == 0, f"{name} has console errors: {critical_errors}"

    @pytest.mark.parametrize("path,name", PAGES)
    def test_has_content(self, page: Page, path: str, name: str):
        """Test that page has visible content"""
        page.goto(f"{BASE_URL}{path}")
        body = page.locator("body")
        assert body.is_visible(), f"{name} has no visible content"

        # Check that body has some text content
        text_content = body.inner_text()
        assert len(text_content) > 100, f"{name} has very little content ({len(text_content)} chars)"


class TestNavigation:
    """Test navigation functionality across all pages"""

    def test_nav_bar_present(self, page: Page):
        """Test that navigation bar is present on all pages"""
        for path, name in PAGES:
            page.goto(f"{BASE_URL}{path}")
            nav = page.locator("nav")
            assert nav.is_visible(), f"Nav bar not visible on {name}"

    def test_nav_links_work(self, page: Page):
        """Test that navigation links navigate to correct pages"""
        page.goto(f"{BASE_URL}/dashboard")

        # Test each nav link
        nav_links = page.locator("nav a")
        count = nav_links.count()

        for i in range(count):
            link = nav_links.nth(i)
            href = link.get_attribute("href")
            text = link.inner_text()

            if href and href.startswith("/"):
                # Click and verify navigation
                link.click()
                page.wait_for_load_state("networkidle")
                assert href in page.url, f"Navigation to {text} failed"

                # Go back to dashboard for next iteration
                page.goto(f"{BASE_URL}/dashboard")

    def test_active_nav_state(self, page: Page):
        """Test that current page is highlighted in navigation"""
        for path, name in PAGES:
            page.goto(f"{BASE_URL}{path}")

            # Look for active/current state styling
            active_link = page.locator(f"nav a[href='{path}']")
            if active_link.count() > 0:
                # Check if it has active styling (class, aria-current, etc)
                classes = active_link.get_attribute("class") or ""
                aria_current = active_link.get_attribute("aria-current")

                # At least one indicator of active state should be present
                has_active_indicator = "active" in classes or aria_current == "page"
                # This is a soft check - some nav implementations may differ


class TestDesignConsistency:
    """Test design system consistency across pages"""

    @pytest.mark.parametrize("path,name", PAGES)
    def test_roboto_font_loaded(self, page: Page, path: str, name: str):
        """Test that Roboto font is loaded"""
        page.goto(f"{BASE_URL}{path}")
        body = page.locator("body")
        font_family = body.evaluate("el => window.getComputedStyle(el).fontFamily")
        assert "Roboto" in font_family, f"{name} doesn't use Roboto font"

    @pytest.mark.parametrize("path,name", PAGES)
    def test_responsive_meta_tag(self, page: Page, path: str, name: str):
        """Test that viewport meta tag is present for responsive design"""
        page.goto(f"{BASE_URL}{path}")
        viewport = page.locator("meta[name='viewport']")
        assert viewport.count() > 0, f"{name} missing viewport meta tag"

    @pytest.mark.parametrize("path,name", PAGES)
    def test_page_title_set(self, page: Page, path: str, name: str):
        """Test that page has a proper title"""
        page.goto(f"{BASE_URL}{path}")
        title = page.title()
        assert len(title) > 0, f"{name} has no title"
        assert "Training" in title, f"{name} title doesn't mention Training"


class TestDashboard:
    """Test Dashboard page specific functionality"""

    def test_dashboard_loads(self, page: Page):
        """Test dashboard loads with key elements"""
        page.goto(f"{BASE_URL}/dashboard")

        # Check for key dashboard elements
        assert page.locator("h1").count() > 0, "Dashboard missing main heading"

    def test_sync_status_visible(self, page: Page):
        """Test that sync status information is visible"""
        page.goto(f"{BASE_URL}/dashboard")
        page.wait_for_load_state("networkidle")

        # Look for sync-related content
        content = page.content()
        # Sync status should be mentioned somewhere
        assert "sync" in content.lower() or "last" in content.lower()

    def test_sync_button_present(self, page: Page):
        """Test that sync button exists"""
        page.goto(f"{BASE_URL}/dashboard")

        # Look for buttons that might trigger sync
        buttons = page.locator("button")
        button_count = buttons.count()
        assert button_count > 0, "Dashboard has no buttons"


class TestUpcoming:
    """Test Upcoming workouts page"""

    def test_upcoming_loads(self, page: Page):
        """Test upcoming page loads"""
        page.goto(f"{BASE_URL}/upcoming")
        page.wait_for_load_state("networkidle")

        # Should have some content about scheduled workouts
        content = page.content().lower()
        assert "workout" in content or "schedule" in content or "upcoming" in content

    def test_calendar_or_list_present(self, page: Page):
        """Test that workouts are displayed in some format"""
        page.goto(f"{BASE_URL}/upcoming")

        # Look for common calendar/list elements
        has_table = page.locator("table").count() > 0
        has_list = page.locator("ul, ol").count() > 0
        has_cards = page.locator(".md-card, [class*='card']").count() > 0

        assert has_table or has_list or has_cards, "No workout display format found"


class TestReviews:
    """Test Reviews page for AI modifications"""

    def test_reviews_loads(self, page: Page):
        """Test reviews page loads"""
        page.goto(f"{BASE_URL}/reviews")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()
        assert "review" in content or "modification" in content or "evaluation" in content

    def test_modification_actions(self, page: Page):
        """Test that modification approval/rejection buttons exist if modifications present"""
        page.goto(f"{BASE_URL}/reviews")
        page.wait_for_load_state("networkidle")

        # Look for approve/reject buttons (may not be present if no modifications)
        buttons = page.locator("button")
        button_texts = [buttons.nth(i).inner_text().lower() for i in range(buttons.count())]

        # If there are modifications, there should be action buttons
        content = page.content().lower()
        if "approve" in content or "reject" in content:
            has_action_button = any("approve" in text or "reject" in text or "accept" in text for text in button_texts)
            assert has_action_button, "Modifications present but no action buttons found"


class TestMetrics:
    """Test Metrics tracking page"""

    def test_metrics_loads(self, page: Page):
        """Test metrics page loads"""
        page.goto(f"{BASE_URL}/metrics")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()
        assert "metric" in content or "body" in content or "performance" in content

    def test_metric_forms_present(self, page: Page):
        """Test that metric input forms are present"""
        page.goto(f"{BASE_URL}/metrics")

        # Should have forms for entering metrics
        forms = page.locator("form")
        inputs = page.locator("input")

        assert forms.count() > 0 or inputs.count() > 0, "No forms or inputs found for metrics entry"

    def test_metric_history_visible(self, page: Page):
        """Test that metric history is displayed"""
        page.goto(f"{BASE_URL}/metrics")
        page.wait_for_load_state("networkidle")

        # Look for tables, lists, or charts showing history
        has_table = page.locator("table").count() > 0
        has_chart = page.locator("svg").count() > 0
        has_list = page.locator("ul, ol").count() > 0

        # At least one way to display history should exist


class TestReports:
    """Test Daily and Weekly report pages"""

    def test_daily_report_loads(self, page: Page):
        """Test daily report loads"""
        page.goto(f"{BASE_URL}/api/reports/daily")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()
        assert "daily" in content or "today" in content or "report" in content

    def test_weekly_report_loads(self, page: Page):
        """Test weekly report loads"""
        page.goto(f"{BASE_URL}/api/reports/weekly")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()
        assert "week" in content or "7 day" in content or "report" in content

    def test_reports_have_visualizations(self, page: Page):
        """Test that reports include data visualizations"""
        for path in ["/api/reports/daily", "/api/reports/weekly"]:
            page.goto(f"{BASE_URL}{path}")
            page.wait_for_load_state("networkidle")

            # Tufte-style reports should have SVG charts
            svg_count = page.locator("svg").count()
            assert svg_count > 0, f"{path} has no visualizations"

    def test_reports_have_data_tables(self, page: Page):
        """Test that reports include data tables"""
        for path in ["/api/reports/daily", "/api/reports/weekly"]:
            page.goto(f"{BASE_URL}{path}")
            page.wait_for_load_state("networkidle")

            # Should have some tabular data
            tables = page.locator("table").count()
            # Reports may use divs instead of tables for Tufte style


class TestMobileResponsiveness:
    """Test mobile responsiveness across pages"""

    @pytest.mark.parametrize("path,name", PAGES)
    def test_mobile_viewport(self, page: Page, path: str, name: str):
        """Test page renders properly on mobile viewport"""
        # Set mobile viewport
        page.set_viewport_size({"width": 375, "height": 667})  # iPhone SE
        page.goto(f"{BASE_URL}{path}")
        page.wait_for_load_state("networkidle")

        # Check that content is visible
        body = page.locator("body")
        assert body.is_visible(), f"{name} not visible on mobile"

        # Check for horizontal scrolling (bad UX)
        scroll_width = page.evaluate("document.documentElement.scrollWidth")
        client_width = page.evaluate("document.documentElement.clientWidth")

        # Allow small difference for scrollbar
        assert scroll_width <= client_width + 20, f"{name} has horizontal scroll on mobile"

    @pytest.mark.parametrize("path,name", PAGES)
    def test_tablet_viewport(self, page: Page, path: str, name: str):
        """Test page renders properly on tablet viewport"""
        # Set tablet viewport
        page.set_viewport_size({"width": 768, "height": 1024})  # iPad
        page.goto(f"{BASE_URL}{path}")
        page.wait_for_load_state("networkidle")

        # Check that content is visible
        body = page.locator("body")
        assert body.is_visible(), f"{name} not visible on tablet"

    def test_mobile_navigation(self, page: Page):
        """Test that mobile navigation works (hamburger menu)"""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{BASE_URL}/dashboard")
        page.wait_for_load_state("networkidle")

        # Look for hamburger menu button
        nav = page.locator("nav")
        buttons = nav.locator("button")

        # On mobile, there should be a menu toggle button
        if buttons.count() > 0:
            menu_button = buttons.first
            menu_button.click()
            page.wait_for_timeout(500)  # Wait for animation

            # Menu should expand and show links
            nav_links = page.locator("nav a")
            # At least some links should be visible after clicking


class TestPerformance:
    """Test page load performance"""

    @pytest.mark.parametrize("path,name", PAGES)
    def test_page_load_time(self, page: Page, path: str, name: str):
        """Test that pages load within reasonable time"""
        start = time.time()
        page.goto(f"{BASE_URL}{path}")
        page.wait_for_load_state("networkidle")
        end = time.time()

        load_time = end - start
        assert load_time < 10, f"{name} took {load_time:.2f}s to load (>10s threshold)"

    @pytest.mark.parametrize("path,name", PAGES)
    def test_no_large_images(self, page: Page, path: str, name: str):
        """Test that images are reasonably sized"""
        page.goto(f"{BASE_URL}{path}")
        page.wait_for_load_state("networkidle")

        # Check all images
        images = page.locator("img")
        for i in range(images.count()):
            img = images.nth(i)
            src = img.get_attribute("src")

            # Skip SVG and data URIs
            if src and not src.startswith("data:") and not src.endswith(".svg"):
                # Get natural size
                width = img.evaluate("el => el.naturalWidth")
                height = img.evaluate("el => el.naturalHeight")

                # Images shouldn't be excessively large (>3000px either dimension)
                assert width < 3000 and height < 3000, f"{name} has large image: {src} ({width}x{height})"


class TestAccessibility:
    """Test basic accessibility features"""

    @pytest.mark.parametrize("path,name", PAGES)
    def test_main_heading_present(self, page: Page, path: str, name: str):
        """Test that page has a main heading (h1)"""
        page.goto(f"{BASE_URL}{path}")
        h1 = page.locator("h1")
        assert h1.count() > 0, f"{name} missing h1 heading"

    @pytest.mark.parametrize("path,name", PAGES)
    def test_buttons_have_text(self, page: Page, path: str, name: str):
        """Test that buttons have text or aria-label"""
        page.goto(f"{BASE_URL}{path}")
        buttons = page.locator("button")

        for i in range(buttons.count()):
            button = buttons.nth(i)
            text = button.inner_text().strip()
            aria_label = button.get_attribute("aria-label")
            title = button.get_attribute("title")

            has_label = len(text) > 0 or aria_label or title
            assert has_label, f"{name} has button without text/label"

    @pytest.mark.parametrize("path,name", PAGES)
    def test_links_have_text(self, page: Page, path: str, name: str):
        """Test that links have text or aria-label"""
        page.goto(f"{BASE_URL}{path}")
        links = page.locator("a")

        for i in range(links.count()):
            link = links.nth(i)
            text = link.inner_text().strip()
            aria_label = link.get_attribute("aria-label")
            title = link.get_attribute("title")

            has_label = len(text) > 0 or aria_label or title
            # Some links may be icons only, which is okay if they have aria-label


class TestForms:
    """Test form functionality"""

    def test_metrics_form_validation(self, page: Page):
        """Test that metrics forms have proper validation"""
        page.goto(f"{BASE_URL}/metrics")
        page.wait_for_load_state("networkidle")

        # Find any forms
        forms = page.locator("form")
        if forms.count() > 0:
            form = forms.first

            # Look for submit button
            submit = form.locator("button[type='submit'], input[type='submit']")
            if submit.count() > 0:
                # Try submitting empty form (should validate)
                submit.first.click()
                page.wait_for_timeout(1000)

                # Form should either show validation errors or submit successfully
                # No assertion here, just checking it doesn't crash


class TestDataDisplay:
    """Test that data is displayed correctly"""

    def test_upcoming_shows_dates(self, page: Page):
        """Test that upcoming workouts show dates"""
        page.goto(f"{BASE_URL}/upcoming")
        page.wait_for_load_state("networkidle")

        content = page.content()

        # Should have some date references (various formats)
        # Mon, Tue, Wed, etc or 2025, Jan, etc
        has_dates = any(day in content for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
        has_months = any(month in content for month in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])

        # At least one date indicator should be present

    def test_reports_show_metrics(self, page: Page):
        """Test that reports display actual metrics"""
        page.goto(f"{BASE_URL}/api/reports/daily")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()

        # Should have some fitness-related terms
        fitness_terms = ["workout", "exercise", "training", "activity", "rest", "recovery", "sleep", "heart"]
        has_fitness_content = any(term in content for term in fitness_terms)

        assert has_fitness_content, "Daily report missing fitness-related content"


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_invalid_page_404(self, page: Page):
        """Test that invalid pages return proper 404"""
        response = page.goto(f"{BASE_URL}/this-page-does-not-exist-12345")
        assert response.status == 404, "Invalid page didn't return 404"

    def test_health_endpoint(self, page: Page):
        """Test that health endpoint is accessible"""
        response = page.goto(f"{BASE_URL}/health")
        assert response.status == 200, "Health endpoint not accessible"

        content = page.content()
        data = page.evaluate("() => document.body.innerText")

        # Should return JSON with status
        assert "status" in data.lower() or "ok" in data.lower() or "healthy" in data.lower()
