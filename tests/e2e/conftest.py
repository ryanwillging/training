"""
Pytest configuration for end-to-end tests.

pytest-playwright provides --base-url option automatically.
Default production URL is set via pytest.ini or command line.
"""

import os
import pytest


# Production URL used as default
PRODUCTION_URL = "https://training.ryanwillging.com"


@pytest.fixture(scope="session")
def base_url(request):
    """Get the base URL for tests from --base-url option or environment."""
    # Try to get from pytest-playwright's --base-url option
    url = request.config.getoption("--base-url", default=None)
    if url:
        return url
    # Fall back to environment variable or default
    return os.getenv("TEST_BASE_URL", PRODUCTION_URL)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context for tests."""
    return {
        **browser_context_args,
        "ignore_https_errors": True,
    }
