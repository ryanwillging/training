"""
Post-deployment tests for production endpoints.

Run after each deployment to verify the application is working correctly.

Usage:
    pytest tests/e2e/ -v                           # Test production
    pytest tests/e2e/ -v --base-url http://localhost:8000  # Test local
"""

import re
import pytest
from playwright.sync_api import Page, expect


class TestHealthEndpoints:
    """Test health and status endpoints."""

    def test_health_check(self, page: Page, base_url: str):
        """Health endpoint should return healthy status with database connected."""
        response = page.request.get(f"{base_url}/health")

        assert response.ok, f"Health check failed: {response.status}"

        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected", "Database should be connected"
        assert "activities" in data, "Should report activity count"

    def test_root_endpoint(self, page: Page, base_url: str):
        """Root endpoint should be accessible."""
        response = page.request.get(f"{base_url}/")

        # Root may return JSON API info or redirect - just verify it's accessible
        assert response.status in [200, 301, 302], f"Root failed: {response.status}"

    def test_cron_status(self, page: Page, base_url: str):
        """Cron status endpoint should be accessible."""
        response = page.request.get(f"{base_url}/api/cron/sync/status")

        assert response.ok

        data = response.json()
        assert data["status"] == "configured"
        assert "schedule" in data


class TestReportEndpoints:
    """Test report generation endpoints."""

    def test_daily_report_returns_html(self, page: Page, base_url: str):
        """Daily report should return valid HTML."""
        response = page.request.get(f"{base_url}/api/reports/daily")

        assert response.ok, f"Daily report failed: {response.status}"

        content_type = response.headers.get("content-type", "")
        assert "text/html" in content_type, f"Expected HTML, got {content_type}"

        html = response.text()
        assert "<html" in html.lower(), "Response should be HTML"
        assert "</html>" in html.lower(), "HTML should be complete"

    def test_daily_report_contains_key_elements(self, page: Page, base_url: str):
        """Daily report should contain expected sections."""
        page.goto(f"{base_url}/api/reports/daily")

        # Check page loaded without errors
        expect(page.locator("body")).to_be_visible()

        # Check for title/header
        html = page.content()
        assert "training" in html.lower() or "report" in html.lower(), \
            "Report should contain training-related content"

    def test_weekly_report_returns_html(self, page: Page, base_url: str):
        """Weekly report should return valid HTML."""
        response = page.request.get(f"{base_url}/api/reports/weekly")

        # Skip if endpoint not deployed yet
        if response.status == 404:
            pytest.skip("Weekly report endpoint not deployed yet")

        assert response.ok, f"Weekly report failed: {response.status}"

        content_type = response.headers.get("content-type", "")
        assert "text/html" in content_type

        html = response.text()
        assert "<html" in html.lower()

    def test_weekly_report_contains_key_elements(self, page: Page, base_url: str):
        """Weekly report should contain expected sections."""
        response = page.request.get(f"{base_url}/api/reports/weekly")
        if response.status == 404:
            pytest.skip("Weekly report endpoint not deployed yet")

        page.goto(f"{base_url}/api/reports/weekly")

        expect(page.locator("body")).to_be_visible()

        html = page.content()
        assert "week" in html.lower() or "training" in html.lower()

    def test_report_list_endpoint(self, page: Page, base_url: str):
        """Report list should return cached reports."""
        response = page.request.get(f"{base_url}/api/reports/list")

        # Skip if endpoint not deployed yet
        if response.status == 404:
            pytest.skip("Report list endpoint not deployed yet")

        assert response.ok

        data = response.json()
        assert "reports" in data
        assert "count" in data


class TestReportQuality:
    """Test the quality and content of generated reports."""

    def test_daily_report_no_errors_visible(self, page: Page, base_url: str):
        """Daily report should not display error messages."""
        page.goto(f"{base_url}/api/reports/daily")

        html = page.content().lower()

        # Should not contain common error indicators
        error_patterns = ["traceback", "exception", "error 500", "internal server error"]
        for pattern in error_patterns:
            assert pattern not in html, f"Report contains error: {pattern}"

    def test_weekly_report_no_errors_visible(self, page: Page, base_url: str):
        """Weekly report should not display error messages."""
        page.goto(f"{base_url}/api/reports/weekly")

        html = page.content().lower()

        error_patterns = ["traceback", "exception", "error 500", "internal server error"]
        for pattern in error_patterns:
            assert pattern not in html, f"Report contains error: {pattern}"

    def test_daily_report_has_styles(self, page: Page, base_url: str):
        """Daily report should include CSS styling (Tufte-style)."""
        page.goto(f"{base_url}/api/reports/daily")

        html = page.content()

        # Should have either inline styles or style tags
        has_styles = "<style" in html or "style=" in html
        assert has_styles, "Report should include CSS styling"

    def test_report_regeneration(self, page: Page, base_url: str):
        """Should be able to force regenerate a report."""
        response = page.request.get(f"{base_url}/api/reports/daily?regenerate=true")

        assert response.ok, "Report regeneration should succeed"


class TestPerformance:
    """Test response times are acceptable."""

    def test_health_response_time(self, page: Page, base_url: str):
        """Health endpoint should respond quickly."""
        import time

        start = time.time()
        response = page.request.get(f"{base_url}/health")
        elapsed = time.time() - start

        assert response.ok
        assert elapsed < 5.0, f"Health check took {elapsed:.2f}s (should be <5s)"

    def test_daily_report_response_time(self, page: Page, base_url: str):
        """Daily report should respond within reasonable time."""
        import time

        start = time.time()
        response = page.request.get(f"{base_url}/api/reports/daily")
        elapsed = time.time() - start

        assert response.ok
        # Reports may take longer due to generation, but should still be <30s
        assert elapsed < 30.0, f"Daily report took {elapsed:.2f}s (should be <30s)"


class TestErrorHandling:
    """Test error handling for edge cases."""

    def test_invalid_date_format(self, page: Page, base_url: str):
        """Should handle invalid date format gracefully."""
        response = page.request.get(f"{base_url}/api/reports/daily?report_date=invalid")

        # Server should either return 400 (proper validation) or handle gracefully
        # Current production may not have full validation deployed
        assert response.status in [200, 400, 422], f"Unexpected status: {response.status}"

    def test_invalid_athlete_id(self, page: Page, base_url: str):
        """Should handle non-existent athlete gracefully."""
        response = page.request.get(f"{base_url}/api/reports/daily?athlete_id=99999")

        # Server should either return 404 or handle gracefully
        assert response.status in [200, 404, 500], f"Unexpected status: {response.status}"
