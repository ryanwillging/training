# Phase A Frontend E2E Tests

Comprehensive end-to-end test suite for the Training Optimization System frontend.

## Quick Start

```bash
# Run all tests
./run_phase_a_tests.sh

# Run with verbose output
./run_phase_a_tests.sh -v

# Run specific page tests
./run_phase_a_tests.sh --dashboard
./run_phase_a_tests.sh --goals
./run_phase_a_tests.sh --plan
./run_phase_a_tests.sh --explore
./run_phase_a_tests.sh --upcoming

# Save results to file
./run_phase_a_tests.sh -v -s
```

## Test Coverage

### Dashboard (8 tests)
- Page loading and error detection
- 6 widget tests (Today's Plan, Recovery Status, Goals Progress, This Week, Plan Changes, Sleep)
- Data freshness indicator

### Goals Page (5 tests)
- Page loading
- Goals list display
- Metric history charts
- Performance test form
- Quarterly test schedule

### Plan Adjustments Page (6 tests)
- Page loading
- Latest review display
- Pending modifications list
- Individual action buttons (approve/reject)
- Batch action buttons
- AI reasoning display

### Explore Page (4 tests)
- Page loading
- Time range selector
- Wellness metric charts
- Chart labels and formatting

### Upcoming Page (4 tests)
- Page loading
- Workouts list display
- Workout details
- Empty state handling

### Cross-Cutting Concerns (44 tests)
- User workflows (3 tests)
- API integration (3 tests)
- Error handling (4 tests)
- Mobile responsiveness (10 tests)
- Performance metrics (6 tests)
- Accessibility (15 tests)
- Data consistency (2 tests)

## Test Results

Latest results: `docs/PHASE_A_TEST_RESULTS.md`

**Current Status**: 56 passed, 15 failed (78.9% pass rate)

**Critical Issue**: Dashboard has JavaScript error preventing widgets from rendering

## Test Files

- `test_phase_a_frontend.py` - Main test suite (71 tests)
- `test_comprehensive_ui.py` - Legacy general UI tests
- `test_production.py` - Production smoke tests
- `test_design_system.py` - Design system verification
- `conftest.py` - Pytest configuration

## Environment

- **Frontend URL**: https://frontend-ryanwillgings-projects.vercel.app
- **API URL**: https://training-ryanwillgings-projects.vercel.app
- **Browser**: Chromium (via Playwright)
- **Python**: 3.9+
- **Framework**: pytest-playwright

## Dependencies

```bash
pip install pytest pytest-playwright pytest-base-url
playwright install chromium
```

## CI/CD Integration

Tests can be integrated into GitHub Actions:

```yaml
- name: Run Phase A Tests
  run: |
    source venv/bin/activate
    pytest tests/e2e/test_phase_a_frontend.py -v
```

## Reporting Issues

When a test fails:
1. Check the error message and stack trace
2. Open the URL in a browser and check console
3. Document findings in `docs/PHASE_A_TEST_RESULTS.md` (Phase A suite)
4. Document production e2e regressions in `TEST_REPORT.md`
5. Create issue with test name, error, and expected vs actual behavior

## Future Enhancements

- Visual regression testing with screenshots
- Interactive workflow tests (form submissions, button clicks)
- API error simulation tests
- Performance profiling
- Accessibility audit integration
- Cross-browser testing (Firefox, Safari)

---

**Created**: 2026-01-25
**Maintained By**: Ryan Willging
**Test Framework**: Playwright + pytest
