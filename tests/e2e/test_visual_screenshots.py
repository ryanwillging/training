"""
Visual verification test - capture screenshots of all pages
"""
import pytest
from playwright.sync_api import Page
import os


BASE_URL = "https://training.ryanwillging.com"

PAGES = [
    ("/dashboard", "Dashboard"),
    ("/upcoming", "Upcoming"),
    ("/reviews", "Reviews"),
    ("/metrics", "Metrics"),
    ("/api/reports/daily", "Daily_Report"),
    ("/api/reports/weekly", "Weekly_Report"),
]


class TestVisualScreenshots:
    """Capture screenshots for visual verification"""

    @pytest.mark.parametrize("path,name", PAGES)
    def test_desktop_screenshot(self, page: Page, path: str, name: str):
        """Capture desktop view"""
        page.set_viewport_size({"width": 1920, "height": 1080})
        page.goto(f"{BASE_URL}{path}")
        page.wait_for_load_state("networkidle")

        os.makedirs("test-results/screenshots", exist_ok=True)
        page.screenshot(path=f"test-results/screenshots/{name}_desktop.png", full_page=True)

    @pytest.mark.parametrize("path,name", PAGES)
    def test_mobile_screenshot(self, page: Page, path: str, name: str):
        """Capture mobile view"""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{BASE_URL}{path}")
        page.wait_for_load_state("networkidle")

        os.makedirs("test-results/screenshots", exist_ok=True)
        page.screenshot(path=f"test-results/screenshots/{name}_mobile.png", full_page=True)
