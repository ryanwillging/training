"""
E2E tests for cron automation and dashboard update tracking.
"""
import pytest
from playwright.sync_api import Page, expect


class TestCronStatusEndpoint:
    """Test the cron status endpoint."""

    def test_status_endpoint_exists(self, page: Page, base_url: str):
        """Status endpoint should return valid data."""
        response = page.request.get(f"{base_url}/api/cron/sync/status")
        assert response.ok

        data = response.json()
        assert "endpoint" in data
        assert "schedule" in data
        assert "status" in data
        assert "last_run" in data

    def test_status_shows_last_run(self, page: Page, base_url: str):
        """If sync has run, status should show details."""
        response = page.request.get(f"{base_url}/api/cron/sync/status")
        data = response.json()

        if data.get("last_run"):
            last_run = data["last_run"]
            # Verify structure
            assert "date" in last_run
            assert "status" in last_run
            assert last_run["status"] in ["success", "partial", "failed"]
            assert "hours_ago" in last_run
            assert "activities_imported" in last_run
            assert "wellness_imported" in last_run
            assert "hevy_imported" in last_run
            assert "duration_seconds" in last_run
            assert "errors" in last_run
            assert isinstance(last_run["errors"], list)


class TestDashboardSyncStatus:
    """Test dashboard shows correct sync status."""

    def test_dashboard_shows_sync_status(self, page: Page, base_url: str):
        """Dashboard should show sync status, not page render time."""
        page.goto(f"{base_url}/dashboard")

        header = page.locator("header")
        expect(header).to_be_visible()

        header_text = header.inner_text()

        # Should show either "Last sync:" or "Never synced"
        # Should NOT show generic "Updated" with current time
        assert any([
            "Last sync:" in header_text,
            "Never synced" in header_text
        ]), f"Dashboard should show sync status. Found: {header_text}"

    def test_dashboard_staleness_indicator(self, page: Page, base_url: str):
        """Dashboard should show visual staleness indicator."""
        # Get actual sync status
        status_response = page.request.get(f"{base_url}/api/cron/sync/status")
        status = status_response.json()

        page.goto(f"{base_url}/dashboard")
        header_html = page.locator("header").inner_html()

        if not status.get("last_run"):
            # Never synced - should show warning
            assert "⚠" in header_html or "warning" in header_html.lower()
        else:
            hours_ago = status["last_run"]["hours_ago"]

            # Verify appropriate indicator appears
            if hours_ago < 26:
                # Fresh - should have success indicator
                assert "✓" in header_html or "success" in header_html.lower()
            elif hours_ago < 50:
                # Stale - should have warning
                assert "⚠" in header_html or "warning" in header_html.lower()
            else:
                # Very stale - should have error
                assert "✗" in header_html or "error" in header_html.lower()


class TestSyncPersistence:
    """Test that sync creates CronLog entries."""

    def test_cron_creates_log_entry(self, page: Page, base_url: str):
        """After cron runs, status should update with new timestamp."""
        # Get initial status
        before = page.request.get(f"{base_url}/api/cron/sync/status").json()

        # Note: This test can't trigger sync in production without auth
        # It verifies the endpoint structure is correct
        if before.get("last_run"):
            # Verify last_run has expected structure
            last_run = before["last_run"]
            assert isinstance(last_run["hours_ago"], (int, float))
            assert last_run["hours_ago"] >= 0
