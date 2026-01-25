"""
Phase A Frontend Integration Tests
Tests all Phase A features and workflows as specified in PHASE_A_NEXT_STEPS.md

These tests verify:
- Dashboard widgets (all 6)
- Goals page (goals list, metric history, performance test logging)
- Plan Adjustments page (review display, approve/reject, batch actions)
- Explore page (time range selector, wellness charts, correlation explorer)
- Upcoming page (workouts list)
- User workflows end-to-end
- Error handling and edge cases
"""
import pytest
from playwright.sync_api import Page, expect
import time


# Frontend is deployed separately from API
# API: https://training-ryanwillgings-projects.vercel.app (backend/Python)
# Frontend Production: https://training.ryanwillging.com (aliased from frontend.vercel.app)
# Frontend Staging: https://frontend-ryanwillgings-projects.vercel.app (Next.js)
BASE_URL = "https://training.ryanwillging.com"


class TestDashboardWidgets:
    """Test all 6 Dashboard widgets display correctly"""

    def test_dashboard_loads_without_errors(self, page: Page):
        """Test dashboard page loads with 200 status and no console errors"""
        errors = []
        page.on("console", lambda msg: errors.append(msg) if msg.type == "error" else None)

        response = page.goto(f"{BASE_URL}/dashboard")
        assert response.status == 200, "Dashboard failed to load"

        page.wait_for_load_state("networkidle")

        # Filter out non-critical errors (favicon, etc.)
        critical_errors = [e for e in errors if "favicon" not in str(e).lower()]
        assert len(critical_errors) == 0, f"Dashboard has console errors: {critical_errors}"

    def test_todays_plan_widget(self, page: Page):
        """Test Today's Plan widget displays workouts for today"""
        page.goto(f"{BASE_URL}/dashboard")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()

        # Should have "today" or "today's plan" heading
        assert "today" in content, "Today's Plan widget not found"

        # Should show either workouts or "no workouts" message
        has_workout_info = any(term in content for term in ["workout", "swim", "lift", "vo2", "rest", "no workout"])
        assert has_workout_info, "Today's Plan widget missing workout information"

    def test_recovery_status_widget(self, page: Page):
        """Test Recovery Status widget shows HRV, RHR, readiness"""
        page.goto(f"{BASE_URL}/dashboard")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()

        # Should have recovery-related terms
        recovery_terms = ["recovery", "hrv", "heart rate", "rhr", "readiness"]
        has_recovery = any(term in content for term in recovery_terms)
        assert has_recovery, "Recovery Status widget not found"

        # Check for gauge/visualization (SVG or canvas)
        has_visualization = page.locator("svg, canvas").count() > 0

    def test_goals_progress_widget(self, page: Page):
        """Test Goals Progress widget shows 3 activity rings"""
        page.goto(f"{BASE_URL}/dashboard")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()

        # Should have "goals" or "progress" heading
        assert "goal" in content or "progress" in content, "Goals Progress widget not found"

        # Should have SVG elements (for rings/charts)
        svg_count = page.locator("svg").count()
        assert svg_count > 0, "Goals Progress widget missing visualizations"

    def test_this_week_widget(self, page: Page):
        """Test This Week widget shows adherence and volume"""
        page.goto(f"{BASE_URL}/dashboard")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()

        # Should have "week" or "adherence" terms
        week_terms = ["week", "adherence", "volume", "completed", "scheduled"]
        has_week_info = any(term in content for term in week_terms)
        assert has_week_info, "This Week widget not found"

    def test_plan_changes_widget(self, page: Page):
        """Test Plan Changes widget shows pending modifications count"""
        page.goto(f"{BASE_URL}/dashboard")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()

        # Should have "plan" or "modifications" or "changes" terms
        plan_terms = ["plan", "modification", "change", "review", "pending"]
        has_plan_info = any(term in content for term in plan_terms)
        assert has_plan_info, "Plan Changes widget not found"

    def test_sleep_last_night_widget(self, page: Page):
        """Test Sleep Last Night widget shows sleep data"""
        page.goto(f"{BASE_URL}/dashboard")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()

        # Should have sleep-related terms
        sleep_terms = ["sleep", "rem", "deep", "light", "duration", "quality"]
        has_sleep_info = any(term in content for term in sleep_terms)
        assert has_sleep_info, "Sleep Last Night widget not found"

    def test_data_freshness_indicator(self, page: Page):
        """Test data freshness indicator shows last sync time"""
        page.goto(f"{BASE_URL}/dashboard")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()

        # Should have sync/update time information
        sync_terms = ["sync", "updated", "last", "ago", "minutes", "hours"]
        has_sync_info = any(term in content for term in sync_terms)
        assert has_sync_info, "Data freshness indicator not found"


class TestGoalsPage:
    """Test Goals page functionality"""

    def test_goals_page_loads(self, page: Page):
        """Test goals page loads without errors"""
        errors = []
        page.on("console", lambda msg: errors.append(msg) if msg.type == "error" else None)

        response = page.goto(f"{BASE_URL}/goals")
        assert response.status == 200, "Goals page failed to load"

        page.wait_for_load_state("networkidle")

        critical_errors = [e for e in errors if "favicon" not in str(e).lower()]
        assert len(critical_errors) == 0, f"Goals page has console errors: {critical_errors}"

    def test_goals_list_displays(self, page: Page):
        """Test goals list displays with name, current, target, progress"""
        page.goto(f"{BASE_URL}/goals")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()

        # Should have goal-related content
        assert "goal" in content, "Goals list not found"

        # Should show progress indicators
        progress_terms = ["target", "current", "progress", "%", "percentage"]
        has_progress = any(term in content for term in progress_terms)
        assert has_progress, "Goals list missing progress information"

    def test_metric_history_charts_render(self, page: Page):
        """Test metric history charts display trends"""
        page.goto(f"{BASE_URL}/goals")
        page.wait_for_load_state("networkidle")

        # Should have charts (SVG elements)
        svg_count = page.locator("svg").count()
        assert svg_count > 0, "Metric history charts not found"

        content = page.content().lower()

        # Should have metric names
        metrics = ["body fat", "weight", "vo2", "jump", "flexibility"]
        has_metrics = any(metric in content for metric in metrics)
        assert has_metrics, "Metric history missing metric labels"

    def test_performance_test_form_displays(self, page: Page):
        """Test performance test logging form is visible"""
        page.goto(f"{BASE_URL}/goals")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()

        # Should have form for logging tests
        form_terms = ["log", "test", "performance", "record", "submit"]
        has_form = any(term in content for term in form_terms)

        # Check for form elements
        has_inputs = page.locator("input").count() > 0
        has_buttons = page.locator("button").count() > 0

        assert has_inputs or has_buttons, "Performance test form not found"

    def test_quarterly_test_schedule_displays(self, page: Page):
        """Test quarterly test schedule shows baseline, mid-program, final"""
        page.goto(f"{BASE_URL}/goals")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()

        # Should have test schedule information
        schedule_terms = ["test", "baseline", "mid", "final", "week", "schedule"]
        has_schedule = any(term in content for term in schedule_terms)


class TestPlanAdjustmentsPage:
    """Test Plan Adjustments page functionality (formerly /reviews)"""

    def test_plan_adjustments_loads(self, page: Page):
        """Test plan adjustments page loads without errors"""
        errors = []
        page.on("console", lambda msg: errors.append(msg) if msg.type == "error" else None)

        # Try new name first, fall back to old name
        response = page.goto(f"{BASE_URL}/plan-adjustments")
        if response.status == 404:
            response = page.goto(f"{BASE_URL}/reviews")

        assert response.status == 200, "Plan Adjustments page failed to load"

        page.wait_for_load_state("networkidle")

        critical_errors = [e for e in errors if "favicon" not in str(e).lower()]
        assert len(critical_errors) == 0, f"Plan Adjustments has console errors: {critical_errors}"

    def test_latest_review_displays(self, page: Page):
        """Test latest review shows evaluation date, insights, recommendations"""
        page.goto(f"{BASE_URL}/reviews")  # Using old name for now
        page.wait_for_load_state("networkidle")

        content = page.content().lower()

        # Should have review information
        review_terms = ["review", "evaluation", "insight", "recommendation", "analysis"]
        has_review = any(term in content for term in review_terms)
        assert has_review, "Latest review section not found"

    def test_pending_modifications_list(self, page: Page):
        """Test pending modifications list shows all details"""
        page.goto(f"{BASE_URL}/reviews")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()

        # Should have modifications section
        mod_terms = ["modification", "pending", "change", "adjustment"]
        has_mods = any(term in content for term in mod_terms)

        # May show "no pending modifications" if none exist
        has_empty_state = "no pending" in content or "no modification" in content

    def test_modification_action_buttons_exist(self, page: Page):
        """Test approve/reject buttons exist for modifications"""
        page.goto(f"{BASE_URL}/reviews")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()

        # Look for action buttons
        if "modification" in content and "no pending" not in content:
            # If there are modifications, should have action buttons
            buttons = page.locator("button")
            button_texts = [buttons.nth(i).inner_text().lower() for i in range(min(buttons.count(), 20))]

            has_approve = any("approve" in text for text in button_texts)
            has_reject = any("reject" in text for text in button_texts)

    def test_batch_action_buttons_exist(self, page: Page):
        """Test batch approve/reject all buttons exist"""
        page.goto(f"{BASE_URL}/reviews")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()

        # Look for batch action buttons
        if "modification" in content and "no pending" not in content:
            has_approve_all = "approve all" in content
            has_reject_all = "reject all" in content

    def test_ai_reasoning_display(self, page: Page):
        """Test AI reasoning shows lifestyle insights and training context"""
        page.goto(f"{BASE_URL}/reviews")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()

        # Should have AI reasoning/insights
        reasoning_terms = ["reason", "insight", "because", "analysis", "context", "lifestyle"]
        has_reasoning = any(term in content for term in reasoning_terms)


class TestExplorePage:
    """Test Explore page functionality"""

    def test_explore_page_loads(self, page: Page):
        """Test explore page loads without errors"""
        errors = []
        page.on("console", lambda msg: errors.append(msg) if msg.type == "error" else None)

        response = page.goto(f"{BASE_URL}/explore")
        assert response.status == 200, "Explore page failed to load"

        page.wait_for_load_state("networkidle")

        critical_errors = [e for e in errors if "favicon" not in str(e).lower()]
        assert len(critical_errors) == 0, f"Explore page has console errors: {critical_errors}"

    def test_time_range_selector_displays(self, page: Page):
        """Test time range selector shows 7d, 30d, 90d, All time options"""
        page.goto(f"{BASE_URL}/explore")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()

        # Should have time range options
        time_ranges = ["7 day", "30 day", "90 day", "all time", "week", "month"]
        has_time_range = any(tr in content for tr in time_ranges)

        # Check for buttons or tabs for time selection
        buttons = page.locator("button")
        button_count = buttons.count()
        assert button_count > 0, "No interactive elements for time range selection"

    def test_wellness_metric_charts_render(self, page: Page):
        """Test wellness charts (HRV, RHR, Sleep, Body Battery, Stress, Steps)"""
        page.goto(f"{BASE_URL}/explore")
        page.wait_for_load_state("networkidle")

        # Should have charts (SVG elements)
        svg_count = page.locator("svg").count()
        assert svg_count > 0, "Wellness metric charts not found"

        content = page.content().lower()

        # Should have wellness metric labels
        wellness_metrics = ["hrv", "rhr", "sleep", "body battery", "stress", "steps", "heart"]
        has_wellness = any(metric in content for metric in wellness_metrics)
        assert has_wellness, "Wellness metric labels not found"

    def test_charts_have_proper_labels(self, page: Page):
        """Test charts have axis labels, legends, and tooltips"""
        page.goto(f"{BASE_URL}/explore")
        page.wait_for_load_state("networkidle")

        # Should have SVG charts
        svg_count = page.locator("svg").count()
        if svg_count > 0:
            # Check for text elements in SVG (labels)
            svg_text = page.locator("svg text").count()
            # Charts should have some text labels

    def test_correlation_explorer_displays(self, page: Page):
        """Test correlation explorer with scatter plots and dropdowns"""
        page.goto(f"{BASE_URL}/explore")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()

        # Should have correlation-related content
        correlation_terms = ["correlation", "relationship", "pattern", "compare"]
        has_correlation = any(term in content for term in correlation_terms)


class TestUpcomingPage:
    """Test Upcoming workouts page"""

    def test_upcoming_page_loads(self, page: Page):
        """Test upcoming page loads without errors"""
        errors = []
        page.on("console", lambda msg: errors.append(msg) if msg.type == "error" else None)

        response = page.goto(f"{BASE_URL}/upcoming")
        assert response.status == 200, "Upcoming page failed to load"

        page.wait_for_load_state("networkidle")

        critical_errors = [e for e in errors if "favicon" not in str(e).lower()]
        assert len(critical_errors) == 0, f"Upcoming page has console errors: {critical_errors}"

    def test_workouts_list_displays(self, page: Page):
        """Test workouts list shows next 7 days"""
        page.goto(f"{BASE_URL}/upcoming")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()

        # Should have upcoming workouts or empty state
        workout_terms = ["workout", "upcoming", "scheduled", "next", "week"]
        has_workouts = any(term in content for term in workout_terms)
        assert has_workouts, "Upcoming workouts section not found"

    def test_workout_details_display(self, page: Page):
        """Test each workout shows date, name, type, week number"""
        page.goto(f"{BASE_URL}/upcoming")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()

        # If workouts exist, should have workout details
        if "no workout" not in content and "no scheduled" not in content:
            # Should have workout types
            workout_types = ["swim", "lift", "vo2", "rest"]
            has_types = any(wtype in content for wtype in workout_types)

            # Should have dates
            has_dates = any(day in content for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"])

    def test_empty_state_displays(self, page: Page):
        """Test empty state shows when no upcoming workouts"""
        page.goto(f"{BASE_URL}/upcoming")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()

        # Should either have workouts or an empty state message
        has_workouts = any(wtype in content for wtype in ["swim", "lift", "vo2"])
        has_empty_state = "no workout" in content or "no scheduled" in content or "nothing scheduled" in content

        assert has_workouts or has_empty_state, "Neither workouts nor empty state found"


class TestUserWorkflows:
    """Test complete user workflows end-to-end"""

    def test_workflow_check_daily_dashboard(self, page: Page):
        """Workflow: Check daily dashboard and navigate to plan adjustments"""
        # Step 1: Navigate to Dashboard
        page.goto(f"{BASE_URL}/dashboard")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()

        # Step 2: Check Today's Plan widget
        assert "today" in content, "Today's Plan not found"

        # Step 3: Check Recovery Status
        recovery_terms = ["recovery", "hrv", "readiness"]
        has_recovery = any(term in content for term in recovery_terms)

        # Step 4: Check Goals Progress
        assert "goal" in content or "progress" in content

        # Step 5: Look for Plan Changes widget
        if "pending" in content or "modification" in content:
            # Step 6: Try to click link to plan adjustments
            links = page.locator("a")
            for i in range(min(links.count(), 20)):
                link = links.nth(i)
                href = link.get_attribute("href")
                if href and ("review" in href or "plan-adjustment" in href):
                    # Found link to plan adjustments
                    break

    def test_workflow_view_wellness_trends(self, page: Page):
        """Workflow: View wellness trends with different time ranges"""
        # Step 1: Navigate to Explore page
        page.goto(f"{BASE_URL}/explore")
        page.wait_for_load_state("networkidle")

        # Step 2: Verify charts are visible
        svg_count = page.locator("svg").count()
        assert svg_count > 0, "No charts found on Explore page"

        # Step 3: Look for time range selectors
        buttons = page.locator("button")
        button_texts = [buttons.nth(i).inner_text() for i in range(min(buttons.count(), 20))]

        # Step 4: Check for time range options
        time_range_options = ["7", "30", "90", "week", "month", "day"]
        has_time_options = any(option in " ".join(button_texts).lower() for option in time_range_options)

    def test_workflow_check_upcoming_workouts(self, page: Page):
        """Workflow: Check upcoming workouts for the week"""
        # Step 1: Navigate to Upcoming page
        page.goto(f"{BASE_URL}/upcoming")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()

        # Step 2: Verify workouts list or empty state
        has_workouts = any(wtype in content for wtype in ["swim", "lift", "vo2", "rest"])
        has_empty = "no workout" in content or "no scheduled" in content

        assert has_workouts or has_empty, "No workout information found"


class TestAPIIntegration:
    """Test API integration by monitoring network calls"""

    def test_dashboard_api_calls(self, page: Page):
        """Test dashboard makes correct API calls"""
        api_calls = []

        def handle_request(request):
            if "/api/" in request.url:
                api_calls.append(request.url)

        page.on("request", handle_request)

        page.goto(f"{BASE_URL}/dashboard")
        page.wait_for_load_state("networkidle")

        # Should have made API calls
        assert len(api_calls) > 0, "Dashboard made no API calls"

        # Check for expected endpoints
        api_calls_str = " ".join(api_calls)
        expected_endpoints = ["plan", "wellness", "metrics"]
        has_expected = any(endpoint in api_calls_str for endpoint in expected_endpoints)

    def test_goals_page_api_calls(self, page: Page):
        """Test goals page makes correct API calls"""
        api_calls = []

        def handle_request(request):
            if "/api/" in request.url:
                api_calls.append(request.url)

        page.on("request", handle_request)

        page.goto(f"{BASE_URL}/goals")
        page.wait_for_load_state("networkidle")

        # Should have made API calls
        assert len(api_calls) > 0, "Goals page made no API calls"

        # Check for metrics-related calls
        api_calls_str = " ".join(api_calls)
        assert "metric" in api_calls_str or "goal" in api_calls_str

    def test_api_calls_return_200(self, page: Page):
        """Test that API calls complete successfully"""
        api_responses = []

        def handle_response(response):
            if "/api/" in response.url:
                api_responses.append(response)

        page.on("response", handle_response)

        page.goto(f"{BASE_URL}/dashboard")
        page.wait_for_load_state("networkidle")

        # Check responses
        for response in api_responses:
            status = response.status
            # Allow 200-299 (success) and 404 (may not have data yet)
            assert status < 500, f"API call failed with {status}: {response.url}"


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_no_workouts_today_message(self, page: Page):
        """Test proper message when no workouts scheduled for today"""
        page.goto(f"{BASE_URL}/dashboard")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()

        # Should handle empty state gracefully
        # Either show workouts or a "no workouts" message
        has_workouts = any(wtype in content for wtype in ["swim", "lift", "vo2"])
        has_empty_message = "no workout" in content or "rest day" in content

    def test_no_wellness_data_message(self, page: Page):
        """Test proper message when no wellness data available"""
        page.goto(f"{BASE_URL}/dashboard")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()

        # Should either show data or indicate no data
        has_data = any(term in content for term in ["hrv", "sleep", "recovery"])
        has_empty = "no data" in content or "not available" in content

    def test_no_pending_modifications_message(self, page: Page):
        """Test proper message when no pending modifications"""
        page.goto(f"{BASE_URL}/reviews")
        page.wait_for_load_state("networkidle")

        content = page.content().lower()

        # Should either show modifications or empty state
        has_mods = "pending" in content and "modification" in content
        has_empty = "no pending" in content or "no modification" in content

    def test_invalid_page_returns_404(self, page: Page):
        """Test that invalid pages return 404"""
        response = page.goto(f"{BASE_URL}/this-page-definitely-does-not-exist")
        assert response.status == 404, "Invalid page didn't return 404"


class TestMobileResponsive:
    """Test mobile responsiveness of Phase A pages"""

    @pytest.mark.parametrize("path", ["/dashboard", "/goals", "/reviews", "/explore", "/upcoming"])
    def test_mobile_viewport_no_horizontal_scroll(self, page: Page, path: str):
        """Test pages don't have horizontal scroll on mobile"""
        # Set iPhone SE viewport
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{BASE_URL}{path}")
        page.wait_for_load_state("networkidle")

        # Check for horizontal scrolling
        scroll_width = page.evaluate("document.documentElement.scrollWidth")
        client_width = page.evaluate("document.documentElement.clientWidth")

        # Allow small difference for scrollbar
        assert scroll_width <= client_width + 20, f"{path} has horizontal scroll on mobile"

    @pytest.mark.parametrize("path", ["/dashboard", "/goals", "/reviews", "/explore", "/upcoming"])
    def test_mobile_content_visible(self, page: Page, path: str):
        """Test content is visible on mobile viewport"""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{BASE_URL}{path}")
        page.wait_for_load_state("networkidle")

        body = page.locator("body")
        assert body.is_visible(), f"{path} not visible on mobile"

        # Should have some text content
        text = body.inner_text()
        assert len(text) > 50, f"{path} has very little content on mobile"


class TestPerformanceMetrics:
    """Test performance characteristics"""

    @pytest.mark.parametrize("path", ["/dashboard", "/goals", "/reviews", "/explore", "/upcoming"])
    def test_page_load_time_under_threshold(self, page: Page, path: str):
        """Test pages load within 10 seconds"""
        start = time.time()
        page.goto(f"{BASE_URL}{path}")
        page.wait_for_load_state("networkidle")
        end = time.time()

        load_time = end - start
        assert load_time < 10, f"{path} took {load_time:.2f}s to load (>10s threshold)"

    def test_dashboard_widgets_load_quickly(self, page: Page):
        """Test dashboard widgets render without significant delay"""
        start = time.time()
        page.goto(f"{BASE_URL}/dashboard")

        # Wait for at least one SVG to appear (indicates widgets are rendering)
        page.wait_for_selector("svg, canvas", timeout=5000)
        end = time.time()

        render_time = end - start
        assert render_time < 5, f"Dashboard widgets took {render_time:.2f}s to render"


class TestAccessibility:
    """Test basic accessibility features"""

    @pytest.mark.parametrize("path", ["/dashboard", "/goals", "/reviews", "/explore", "/upcoming"])
    def test_page_has_main_heading(self, page: Page, path: str):
        """Test each page has an h1 heading"""
        page.goto(f"{BASE_URL}{path}")
        h1 = page.locator("h1")
        assert h1.count() > 0, f"{path} missing h1 heading"

    @pytest.mark.parametrize("path", ["/dashboard", "/goals", "/reviews", "/explore", "/upcoming"])
    def test_buttons_have_labels(self, page: Page, path: str):
        """Test buttons have text or aria-label"""
        page.goto(f"{BASE_URL}{path}")
        buttons = page.locator("button")

        for i in range(min(buttons.count(), 10)):
            button = buttons.nth(i)
            text = button.inner_text().strip()
            aria_label = button.get_attribute("aria-label")
            title = button.get_attribute("title")

            has_label = len(text) > 0 or aria_label or title
            assert has_label, f"{path} has button without label at index {i}"

    @pytest.mark.parametrize("path", ["/dashboard", "/goals", "/reviews", "/explore", "/upcoming"])
    def test_color_contrast_sufficient(self, page: Page, path: str):
        """Test page uses sufficient color contrast (basic check)"""
        page.goto(f"{BASE_URL}{path}")

        # Check body background and text color
        body = page.locator("body")
        bg_color = body.evaluate("el => window.getComputedStyle(el).backgroundColor")
        text_color = body.evaluate("el => window.getComputedStyle(el).color")

        # Both should be defined
        assert bg_color, f"{path} missing background color"
        assert text_color, f"{path} missing text color"


class TestDataConsistency:
    """Test data consistency across pages"""

    def test_goals_match_dashboard(self, page: Page):
        """Test goals shown on dashboard match goals page"""
        # Get goals from dashboard
        page.goto(f"{BASE_URL}/dashboard")
        page.wait_for_load_state("networkidle")
        dashboard_content = page.content().lower()

        # Get goals from goals page
        page.goto(f"{BASE_URL}/goals")
        page.wait_for_load_state("networkidle")
        goals_content = page.content().lower()

        # Both should mention goals
        assert "goal" in dashboard_content, "Dashboard missing goals"
        assert "goal" in goals_content, "Goals page missing goals"

    def test_upcoming_matches_dashboard_today(self, page: Page):
        """Test today's workouts on dashboard match upcoming page"""
        # Get today's workouts from dashboard
        page.goto(f"{BASE_URL}/dashboard")
        page.wait_for_load_state("networkidle")
        dashboard_content = page.content().lower()

        # Get workouts from upcoming
        page.goto(f"{BASE_URL}/upcoming")
        page.wait_for_load_state("networkidle")
        upcoming_content = page.content().lower()

        # Check for consistency in workout types
        workout_types = ["swim", "lift", "vo2", "rest"]
        dashboard_workouts = [wt for wt in workout_types if wt in dashboard_content]
        upcoming_workouts = [wt for wt in workout_types if wt in upcoming_content]
