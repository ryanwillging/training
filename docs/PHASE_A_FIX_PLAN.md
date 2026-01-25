# Phase A: Enhanced Dashboards - Fix Plan

## Overview

This document outlines the plan to fix issues identified during Phase A testing.

## Issues Summary

See `PHASE_A_TEST_RESULTS.md` for complete test results.

**Key Problems**:
1. ✅ **FIXED**: SSO protection blocking access
2. ❌ **Critical**: API endpoint mismatches (frontend expects endpoints that don't exist)
3. ❌ **Critical**: Missing data (no upcoming workouts)
4. ❌ **Medium**: Missing action endpoints (approve/reject modifications)

## Fix Plan

### Step 1: Backend API Alignment (Priority 1)

**Goal**: Make backend API match frontend expectations

#### 1.1 Add Metrics History Endpoint with Filtering

**Current**: `/api/metrics/history` returns all metrics
**Required**: `/api/metrics/history/:metricType?athlete_id=X&limit=Y`

**Implementation**:
```python
# In api/index.py
if path.startswith("/api/metrics/history/"):
    metric_type = path.split("/")[-1]
    athlete_id = int(query.get("athlete_id", [1])[0])
    limit = int(query.get("limit", [30])[0])

    db = get_db_session()
    if db:
        try:
            from database.models import ProgressMetric
            metrics = db.query(ProgressMetric).filter(
                ProgressMetric.metric_type == metric_type,
                ProgressMetric.athlete_id == athlete_id
            ).order_by(
                ProgressMetric.metric_date.desc()
            ).limit(limit).all()

            result = {
                "metric_type": metric_type,
                "athlete_id": athlete_id,
                "count": len(metrics),
                "data": [
                    {
                        "id": m.id,
                        "date": str(m.metric_date),
                        "value": m.value_numeric,
                        "value_text": m.value_text,
                        "notes": m.notes
                    }
                    for m in metrics
                ]
            }
            db.close()
            return self.send_json(200, result)
```

#### 1.2 Add Goals Endpoint

**Required**: `/api/metrics/goals?athlete_id=X`

**Implementation**:
```python
if path == "/api/metrics/goals":
    athlete_id = int(query.get("athlete_id", [1])[0])

    db = get_db_session()
    if db:
        try:
            from database.models import Goal, ProgressMetric

            goals = db.query(Goal).filter(
                Goal.athlete_id == athlete_id
            ).all()

            result = []
            for goal in goals:
                # Get latest metric value
                latest_metric = db.query(ProgressMetric).filter(
                    ProgressMetric.metric_type == goal.metric_type,
                    ProgressMetric.athlete_id == athlete_id
                ).order_by(ProgressMetric.metric_date.desc()).first()

                current_value = latest_metric.value_numeric if latest_metric else 0
                progress_pct = (current_value / goal.target_value * 100) if goal.target_value > 0 else 0

                result.append({
                    "id": goal.id,
                    "name": goal.name,
                    "metric_type": goal.metric_type,
                    "target_value": goal.target_value,
                    "current_value": current_value,
                    "unit": goal.unit,
                    "deadline": str(goal.deadline) if goal.deadline else None,
                    "progress_pct": progress_pct
                })

            db.close()
            return self.send_json(200, result)
```

**Note**: Requires `Goal` model to exist in database. May need to create table and seed data.

#### 1.3 Add Performance Test Endpoint

**Required**: POST `/api/metrics/performance-test`

**Implementation**: Already exists in routes, need to add to index.py or verify it's included.

#### 1.4 Add Plan Review Action Endpoints

**Required**:
- POST `/api/plan/reviews/:reviewId/modifications/:modIndex/action`
- POST `/api/plan/reviews/:reviewId/action`

**Check**: Verify if these exist in the plan_routes.py and are exposed in index.py

### Step 2: Data Issues (Priority 2)

#### 2.1 Fix Empty Upcoming Workouts

**Issue**: `/api/plan/upcoming?days=1` returns `{"days_ahead": 1, "workouts": []}`

**Investigation Steps**:
1. Check if PlannedWorkout table has data
2. Check date filtering logic
3. Check if week 1 workouts are scheduled
4. Verify athlete_id matching

**Query to test**:
```sql
SELECT * FROM planned_workouts WHERE athlete_id = 1 AND date >= CURRENT_DATE LIMIT 10;
```

**Possible Fixes**:
- Re-run plan initialization if table is empty
- Fix date calculation if filtering is wrong
- Seed initial workout data

#### 2.2 Initialize Goals if Missing

**Steps**:
1. Check if `goals` table exists
2. If not, create table from model
3. Seed initial goals:
   - 400yd freestyle time goal
   - Body fat % goal
   - VO2 max goal (multi-modal)
   - Flexibility/explosiveness goals

### Step 3: Frontend Fixes (Priority 3)

#### 3.1 Update API Client Error Handling

Add better error handling in `frontend/src/lib/api.ts`:
- Show meaningful error messages
- Handle 404s gracefully
- Add loading states

#### 3.2 Add Fallback UI for Missing Data

For widgets that might have no data:
- Show helpful messages ("No workouts scheduled yet")
- Add CTAs ("Set up your first goal")
- Don't show error states for expected empty data

### Step 4: Testing (Priority 4)

#### 4.1 Create E2E Test Suite

**File**: `tests/e2e/test_phase_a.py`

```python
def test_dashboard_loads(page):
    page.goto("https://training.ryanwillging.com/dashboard")
    expect(page.locator("h1")).to_contain_text("Dashboard")

def test_api_plan_status(api_context):
    response = api_context.get("https://training.ryanwillging.com/api/plan/status")
    assert response.status == 200
    data = response.json()
    assert "initialized" in data

def test_api_wellness_latest(api_context):
    response = api_context.get("https://training.ryanwillging.com/api/wellness/latest")
    assert response.status == 200
    data = response.json()
    assert "hrv" in data or "sleep_score" in data

# Add more tests for each endpoint
```

#### 4.2 Manual Testing Checklist

- [ ] Load each page and verify no console errors
- [ ] Test each widget on dashboard
- [ ] Test approve/reject on plan adjustments
- [ ] Test metric logging on goals page
- [ ] Test date range selector on explore page
- [ ] Verify all charts render with data

## Implementation Order

### Phase 1: Quick Wins (Day 1)
1. Fix SSO protection (DONE)
2. Add metrics history with filtering endpoint
3. Add performance test endpoint
4. Test dashboard loads correctly

### Phase 2: Data Setup (Day 1-2)
5. Investigate empty workouts
6. Create and seed goals table
7. Re-run plan initialization if needed
8. Verify all widgets have data

### Phase 3: Missing Features (Day 2-3)
9. Add goals endpoint
10. Add plan review action endpoints
11. Test approve/reject workflow
12. Test goal CRUD operations

### Phase 4: Polish (Day 3-4)
13. Add E2E tests
14. Improve error handling
15. Add loading states
16. Final manual testing

## Verification Criteria

**Phase A is complete when**:
1. All 5 pages load without errors
2. All dashboard widgets display data (or appropriate empty states)
3. Users can approve/reject plan modifications
4. Users can log performance tests
5. Wellness data displays correctly in all charts
6. No console errors in browser dev tools
7. All API endpoints return expected data format
8. E2E tests pass

## Rollback Plan

If issues are found:
1. Old Python pages are still available at same routes
2. Can revert domain alias to point back to old deployment
3. Frontend code is in git, can revert commits
4. Database unchanged, safe to rollback

## Notes

- Backend changes go to `api/index.py` (Vercel serverless)
- Frontend changes go to `frontend/src/`
- Both deploy independently
- Test in staging before production (if available)
