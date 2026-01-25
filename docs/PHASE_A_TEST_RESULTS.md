# Phase A: Enhanced Dashboards - Test Results & Issues

**Test Date**: 2026-01-24
**Tester**: Claude (Automated)
**Environment**: Production (training.ryanwillging.com)

## Critical Issues Found

### 1. ✅ FIXED: Vercel SSO Protection Blocking All Access
**Status**: RESOLVED
**Impact**: Critical - Blocked all user access and API calls
**Issue**: Both frontend and backend projects had SSO protection enabled
**Fix**: Disabled SSO protection via Vercel API on both projects
**Verified**: API endpoints now return JSON data correctly

### 2. ❌ API Endpoint Mismatches

#### 2.1 Metrics History Endpoint
**Frontend Expects**: `/api/metrics/history/:metricType?athlete_id=X&limit=Y`
**Backend Provides**: `/api/metrics/history` (returns all metrics, no filtering)
**Impact**: Goals page cannot load metric history
**Data Format Mismatch**:
- Frontend expects: `{ metric_type, athlete_id, count, data: [...] }`
- Backend returns: `{ metrics: [...] }` with different field names

**Test Results**:
```bash
curl https://training.ryanwillging.com/api/metrics/history/body_fat
# Returns: {"error":"Not found","path":"/api/metrics/history/body_fat"}

curl https://training.ryanwillging.com/api/metrics/history
# Returns: {"metrics": [...]}  # Different format than expected
```

#### 2.2 Goals Endpoint Missing
**Frontend Expects**: `/api/metrics/goals`
**Backend Provides**: None
**Impact**: Goals page cannot load goal data
**Test Result**:
```bash
curl https://training.ryanwillging.com/api/metrics/goals
# Returns: {"error":"Not found","path":"/api/metrics/goals"}
```

#### 2.3 Performance Test Endpoint Missing
**Frontend Expects**: POST `/api/metrics/performance-test`
**Backend Provides**: None
**Impact**: Cannot log performance tests from Goals page

#### 2.4 Plan Review Action Endpoints Missing
**Frontend Expects**:
- POST `/api/plan/reviews/:reviewId/modifications/:modIndex/action`
- POST `/api/plan/reviews/:reviewId/action`

**Backend Provides**: Unknown (need to verify)
**Impact**: Cannot approve/reject plan modifications from UI

### 3. ❌ Missing Data

#### 3.1 No Upcoming Workouts
**Test Result**:
```json
{
    "days_ahead": 1,
    "workouts": []
}
```
**Impact**: "Today's Plan" widget shows no workouts
**Possible Causes**:
- No workouts scheduled in database
- Plan not initialized
- Date calculation issue

## Working Features

### ✅ API Endpoints Functioning Correctly

1. **Plan Status** - `/api/plan/status`
   ```json
   {
       "initialized": true,
       "start_date": "2026-01-19",
       "current_week": 1,
       "is_test_week": true,
       "progress": {"total_scheduled": 120, "completed": 0, "adherence_rate": 0.0}
   }
   ```

2. **Wellness Latest** - `/api/wellness/latest`
   - Returns latest wellness data (HRV, sleep, steps, etc.)
   - Data looks complete and accurate

3. **Wellness History** - `/api/wellness?days=7`
   - Returns array of wellness records
   - Data includes all expected fields

4. **Plan Reviews** - `/api/plan/reviews/latest`
   - Returns latest AI-generated review with modifications
   - Includes insights, recommendations, and proposed adjustments
   - Status shows "approved"

## Frontend Pages Status

### Dashboard (`/dashboard`)
**Status**: Partially Working
**Issues**:
- ✅ Page loads correctly
- ✅ UI widgets render
- ❌ "Today's Plan" widget shows no data (API returns empty array)
- ✅ "Recovery Status" should work (wellness API works)
- ❌ "Goals Progress" broken (no goals API)
- ❌ "This Week" needs testing
- ✅ "Plan Changes" should work (reviews API works)
- ✅ "Sleep Last Night" should work (wellness API works)

### Goals (`/goals`)
**Status**: Broken
**Issues**:
- ❌ Cannot load goals (API missing)
- ❌ Cannot load metric history (API mismatch)
- ❌ Cannot log performance tests (API missing)

### Plan Adjustments (`/plan-adjustments`)
**Status**: Partially Working
**Issues**:
- ✅ Can load latest review
- ❌ Cannot approve/reject modifications (API endpoints missing/unverified)

### Explore (`/explore`)
**Status**: Should Work
**APIs Used**:
- ✅ `/api/wellness?days=X` - Works
- Needs testing with actual page

### Upcoming (`/upcoming`)
**Status**: Broken
**Issues**:
- ❌ No workouts returned from `/api/plan/upcoming`

## Comparison: Old Python Pages vs New Next.js

### Old Python Pages (Still Available Routes)
- `/dashboard` - Old HTML dashboard
- `/metrics` - Metrics input form
- `/reviews` - Plan reviews page
- `/upcoming` - Upcoming workouts page
- `/api/reports/daily` - Daily report
- `/api/reports/weekly` - Weekly report

### New Next.js Pages
- `/dashboard` - New React dashboard (partially working)
- `/goals` - New Goals page (broken - no API)
- `/plan-adjustments` - New Plan Adjustments page (partially working)
- `/explore` - New Explore page (not tested)
- `/upcoming` - New Upcoming page (broken - no data)

### Functionality Gaps
1. **Metrics/Goals**: Old page had metric input form, new page expects full CRUD API
2. **Plan Reviews**: Old page likely had approve/reject buttons that worked
3. **Upcoming Workouts**: Old page showed workouts, new page shows none

## Required Fixes (Priority Order)

### Priority 1: Critical Functionality

1. **Add Missing API Endpoints to Backend**
   - Add `/api/metrics/history/:metricType` with proper filtering
   - Add `/api/metrics/goals` endpoint
   - Add `/api/metrics/performance-test` POST endpoint
   - Add plan review action endpoints

2. **Fix Upcoming Workouts**
   - Investigate why `/api/plan/upcoming` returns empty array
   - Check if plan initialization is complete
   - Verify workout scheduling logic

### Priority 2: Data Format Fixes

3. **Standardize API Response Formats**
   - Metrics history: Match frontend expectations
   - Ensure all endpoints return consistent error formats

### Priority 3: Feature Parity

4. **Port Missing Features from Old Pages**
   - Compare old /metrics page functionality
   - Compare old /reviews page functionality
   - Ensure all actions from old pages work in new pages

## Testing Plan

### Phase 1: Backend API Testing
- [ ] Test all `/api/plan/*` endpoints
- [ ] Test all `/api/wellness/*` endpoints
- [ ] Test all `/api/metrics/*` endpoints
- [ ] Document all missing endpoints
- [ ] Document all format mismatches

### Phase 2: Frontend Integration Testing
- [ ] Test Dashboard page with dev tools open
- [ ] Test Goals page and document errors
- [ ] Test Plan Adjustments and verify approve/reject
- [ ] Test Explore page with various date ranges
- [ ] Test Upcoming page and verify workout display

### Phase 3: End-to-End Testing
- [ ] Create Playwright test suite
- [ ] Test complete user flows
- [ ] Compare with old page functionality

### Phase 4: Data Verification
- [ ] Verify plan initialization
- [ ] Verify workout scheduling
- [ ] Verify goals setup
- [ ] Check database for missing data

## Next Steps

1. **Immediate**: Fix API endpoint mismatches
2. **Short-term**: Add missing endpoints
3. **Medium-term**: Fix data issues (empty workouts, etc.)
4. **Long-term**: Complete E2E test coverage

## Notes

- Frontend deployment successful
- API proxy working correctly after SSO fix
- Main issue is API contract mismatch between frontend and backend
- Some features may require database seeding/initialization
