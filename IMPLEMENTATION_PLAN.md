# Implementation Plan - Training Optimization System

## Priority Order & Rationale

### Phase 1: Core Data Foundation (Priority: CRITICAL)
**Goal:** Get data flowing in and stored properly before building intelligence

#### 1.1 Database Setup
**Files to create:**
- `database/schema.sql` - Database schema definition
- `database/models.py` - SQLAlchemy ORM models
- `database/migrations/` - Alembic migration scripts
- `database/__init__.py` - Database connection setup

**Tasks:**
- [x] Design schema (documented in ARCHITECTURE.md)
- [ ] Create SQLAlchemy models for all tables
- [ ] Set up Alembic for migrations
- [ ] Create initial migration
- [ ] Add database connection pooling

**Dependencies:** None
**Estimated Complexity:** Medium
**Critical Path:** YES

---

#### 1.2 Garmin Data Import
**Files to create:**
- `integrations/garmin/activity_importer.py` - Pull activities from Garmin
- `integrations/garmin/models.py` - Activity data models
- `integrations/garmin/parsers.py` - Parse Garmin activity data

**Tasks:**
- [ ] Extend existing Garmin Connect integration
- [ ] Fetch activities by date range
- [ ] Parse swimming activities (laps, strokes, times)
- [ ] Parse running/cycling activities (HR, pace, VO2 estimates)
- [ ] Store activities in `completed_activities` table
- [ ] Handle duplicates (don't re-import same activity)

**API Endpoints:**
- `POST /api/import/garmin/activities?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
- `GET /api/activities?athlete_id=X&date=YYYY-MM-DD`

**Dependencies:** 1.1 (Database)
**Estimated Complexity:** Medium
**Critical Path:** YES

---

#### 1.3 Hevy Integration
**Files to create:**
- `integrations/hevy/client.py` - Hevy API client
- `integrations/hevy/activity_importer.py` - Import strength workouts
- `integrations/hevy/models.py` - Hevy data models

**Research needed:**
- Hevy API documentation (https://hevy.com/api or check developer docs)
- Authentication method (API key, OAuth?)
- Endpoints for fetching workouts

**Tasks:**
- [ ] Research Hevy API capabilities
- [ ] Implement authentication
- [ ] Fetch workout history
- [ ] Parse exercises, sets, reps, weight
- [ ] Store in `completed_activities` table with type='strength'
- [ ] Handle exercise variations/substitutions

**API Endpoints:**
- `POST /api/import/hevy/workouts?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`

**Alternative:** If Hevy API is limited, create manual entry form
- `POST /api/activities/strength` - Manual strength workout entry

**Dependencies:** 1.1 (Database)
**Estimated Complexity:** Medium (depends on API availability)
**Critical Path:** YES

---

#### 1.4 Manual Data Entry
**Files to create:**
- `api/routes/manual_entry.py` - Endpoints for manual data
- `api/schemas/manual_entry.py` - Pydantic models for validation

**Tasks:**
- [ ] Body composition entry (body fat %, weight)
- [ ] Subjective metrics (sleep quality, soreness, energy)
- [ ] Test results (100yd time, box jump height, etc.)
- [ ] Store in `progress_metrics` table

**API Endpoints:**
- `POST /api/metrics/body-composition`
- `POST /api/metrics/performance-test`
- `POST /api/metrics/subjective`

**Dependencies:** 1.1 (Database)
**Estimated Complexity:** Low
**Critical Path:** YES

---

### Phase 2: Planning & Comparison (Priority: HIGH)

#### 2.1 Workout Plan System
**Files to create:**
- `plans/plan_manager.py` - CRUD for training plans
- `plans/workout_templates.py` - Workout definition templates
- `plans/scheduler.py` - Schedule workouts for athlete

**Tasks:**
- [ ] Define workout schema (JSON structure for different types)
- [ ] Import existing plans from markdown to database
- [ ] Create plan templates (6-week swim, athletic performance)
- [ ] Generate weekly schedules from plans
- [ ] Support plan customization (swap days, adjust volume)

**Workout Definition Schema:**
```json
{
  "type": "swim",
  "duration_minutes": 60,
  "pool_length": "25y",
  "sets": [
    {"distance": 400, "stroke": "free", "intensity": "easy", "rest": 30},
    {"distance": 200, "stroke": "free", "intensity": "hard", "rest": 60}
  ]
}
```

**API Endpoints:**
- `POST /api/plans` - Create new plan
- `GET /api/plans/{plan_id}/schedule?week=1` - Get week's workouts
- `POST /api/plans/{plan_id}/workouts` - Add workout to plan

**Dependencies:** 1.1 (Database)
**Estimated Complexity:** High
**Critical Path:** YES

---

#### 2.2 Comparison Engine
**Files to create:**
- `analytics/comparison.py` - Compare planned vs actual
- `analytics/metrics.py` - Calculate adherence, volume, etc.

**Tasks:**
- [ ] Match completed activities to planned workouts (by date + type)
- [ ] Calculate adherence rate (% completed)
- [ ] Compare workout details (did they do what was planned?)
- [ ] Identify missed workouts
- [ ] Calculate weekly volume (planned vs actual)
- [ ] Detect patterns (always missing Mondays, etc.)

**Metrics to Calculate:**
- Weekly adherence %
- Volume delta (planned vs actual hours)
- Workout type distribution
- Average rest days
- Intensity compliance (did they go hard when planned?)

**API Endpoints:**
- `GET /api/analytics/adherence?athlete_id=X&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
- `GET /api/analytics/comparison/weekly?athlete_id=X&week=YYYY-WXX`

**Dependencies:** 1.2, 1.3, 2.1
**Estimated Complexity:** Medium
**Critical Path:** YES

---

### Phase 3: Intelligence Layer (Priority: HIGH)

#### 3.1 Progress Tracking
**Files to create:**
- `analytics/progress.py` - Track goal progress
- `analytics/trends.py` - Calculate trends and rates of improvement

**Tasks:**
- [ ] Body fat tracking and trend analysis
- [ ] VO2 max tracking (from Garmin estimates)
- [ ] Swim time tracking (100yd, CSS tests)
- [ ] Strength metrics (lifts, box jumps)
- [ ] Weekly volume compliance (3-5hr target)
- [ ] Calculate rates of improvement
- [ ] Identify which goals are on/off track

**Goal Tracking Schema:**
```python
{
  "goal_type": "100yd_freestyle",
  "target": "54 seconds",  # Example target
  "current": "58 seconds",
  "baseline": "62 seconds",
  "progress_pct": 66.7,  # (62-58)/(62-54) * 100
  "trend": "improving",
  "rate_of_change": "-1 sec/month"
}
```

**API Endpoints:**
- `GET /api/analytics/goals?athlete_id=X` - All goal progress
- `GET /api/analytics/goals/{goal_type}/history` - Historical data for one goal

**Dependencies:** 1.2, 1.3, 1.4
**Estimated Complexity:** Medium
**Critical Path:** YES

---

#### 3.2 Daily Review System
**Files to create:**
- `review/daily_review.py` - Main review orchestrator
- `review/insights.py` - Generate insights from data
- `review/recommendations.py` - Suggest plan adjustments

**Tasks:**
- [ ] Scheduled job (cron/systemd timer) to run each evening
- [ ] Fetch today's data (planned vs actual)
- [ ] Calculate 7-day rolling metrics
- [ ] Generate insights (what's working, what's not)
- [ ] Determine if plan adjustment needed
- [ ] Save review to database
- [ ] Send notification/summary to user

**Review Output:**
```
=== Daily Review - 2026-01-13 ===

TODAY:
✓ Completed: Swim Workout A (60 min)
✗ Missed: Lower Body Strength (45 min)

WEEKLY ADHERENCE: 80% (4/5 workouts completed)
WEEKLY VOLUME: 3.2 hrs (target: 3-5 hrs) ✓

PROGRESS:
✓ 100yd Freestyle: 58s (down from 60s last month)
✓ VO2 Max: 48 (up from 46)
⚠ Body Fat: 15.2% (target: 14%) - slight increase
⚠ Strength: Missed 2 sessions this week

INSIGHTS:
- Swim volume is driving good freestyle improvement
- Strength consistency is low (40% adherence)
- Consider shifting strength to different days?

RECOMMENDATION: Keep current plan, but move Wednesday strength
to Saturday morning when adherence is typically higher.
```

**CLI Command:**
```bash
python -m review.daily_review --athlete-id=1
```

**API Endpoint:**
- `POST /api/review/run?athlete_id=X&date=YYYY-MM-DD` - Trigger review
- `GET /api/review/latest?athlete_id=X` - Get most recent review

**Dependencies:** 2.2, 3.1
**Estimated Complexity:** High
**Critical Path:** YES

---

#### 3.3 Adaptive Planning Logic
**Files to create:**
- `plans/adjuster.py` - Make plan adjustments
- `plans/rules.py` - Adjustment decision rules

**Tasks:**
- [ ] Implement rule-based adjustment system
- [ ] Volume adjustments (add/remove sessions)
- [ ] Focus shifts (pivot between goals)
- [ ] Workout rescheduling (swap days)
- [ ] Deload week insertion
- [ ] Exercise substitutions
- [ ] Log all adjustments with rationale

**Adjustment Rules:**
```python
# Example rules
if adherence < 0.7 and weekly_volume > 4.5:
    action = "Reduce volume (plan too aggressive)"

if goal_progress["100yd_freestyle"] > 90 and goal_progress["vo2_max"] < 40:
    action = "Shift focus: Reduce swim volume, add VO2 intervals"

if consecutive_missed_strength > 2:
    action = "Reschedule strength to higher-adherence days"

if weekly_tss > threshold and hrv_trend == "declining":
    action = "Insert deload week"
```

**API Endpoints:**
- `POST /api/plans/{plan_id}/adjust` - Apply adjustment (with reasoning)
- `GET /api/plans/{plan_id}/adjustment-history` - View past adjustments

**Dependencies:** 3.2
**Estimated Complexity:** High
**Critical Path:** YES

---

### Phase 4: Workout Export (Priority: MEDIUM)

#### 4.1 Enhanced Garmin Export
**Files to extend:**
- `integrations/garmin/workout_exporter.py` - Export various workout types

**Tasks:**
- [ ] Extend existing FIT export to support running/cycling
- [ ] Generate VO2 interval workouts
- [ ] Generate strength workout FIT files (if supported by device)
- [ ] Batch upload workouts for upcoming week
- [ ] Handle workout updates/deletions

**API Endpoints:**
- `POST /api/export/garmin/workout?planned_workout_id=X` - Export single workout
- `POST /api/export/garmin/week?plan_id=X&week=1` - Export week's workouts

**Dependencies:** 2.1
**Estimated Complexity:** Medium
**Critical Path:** NO (can use existing CSV method temporarily)

---

#### 4.2 Hevy Export
**Files to create:**
- `integrations/hevy/workout_exporter.py` - Export strength workouts to Hevy

**Tasks:**
- [ ] Create workouts in Hevy via API
- [ ] Sync planned exercises, sets, reps
- [ ] Support exercise variations
- [ ] Update workouts if plan adjusted

**Alternative:** If API doesn't support creation, generate shareable workout links

**API Endpoints:**
- `POST /api/export/hevy/workout?planned_workout_id=X`

**Dependencies:** 2.1
**Estimated Complexity:** Medium
**Critical Path:** NO (can enter manually initially)

---

### Phase 5: User Interface (Priority: LOW)

#### 5.1 CLI Improvements
**Files to create:**
- `cli/commands.py` - Rich CLI commands
- `cli/display.py` - Formatted output

**Tasks:**
- [ ] Beautiful daily review output (colors, tables)
- [ ] Interactive plan adjustment prompts
- [ ] Quick data entry commands
- [ ] Weekly summary command

**Commands:**
```bash
training review                    # Run daily review
training status                    # Quick status check
training log --type=strength       # Log manual workout
training plan --show-week          # View this week's plan
training goals                     # Show goal progress
```

**Dependencies:** 3.2
**Estimated Complexity:** Low
**Critical Path:** NO

---

#### 5.2 Web Dashboard
**Files to create:**
- `web/templates/` - HTML templates
- `web/static/` - CSS/JS
- `web/routes.py` - Web page routes

**Pages:**
- Dashboard (overview, upcoming workouts, recent activities)
- Progress (charts for each goal)
- Plan (calendar view of workouts)
- History (past daily reviews)

**Technology:**
- FastAPI templates (Jinja2)
- Simple CSS (no framework needed initially)
- Chart.js for visualizations

**Dependencies:** All previous phases
**Estimated Complexity:** Medium
**Critical Path:** NO

---

## Development Workflow

### Setup
1. Create feature branch: `claude/setup-daily-review-jGyVI` (already on it!)
2. Set up Python virtual environment
3. Install dependencies
4. Initialize database

### Iteration Cycle
1. Pick highest priority incomplete task
2. Implement with tests
3. Commit with clear message
4. Update this document with [x] for completed tasks
5. Move to next task

### Testing Strategy
- Unit tests for each module
- Integration tests for API endpoints
- Mock external APIs (Garmin, Hevy) in tests
- Manual testing with real data

### Deployment
- Dockerize application
- Set up systemd timer for daily review
- Configure environment variables
- Set up backup for SQLite database

---

## Next Steps (Immediate)

1. **Set up database** (Task 1.1)
   - Create `database/` directory structure
   - Define SQLAlchemy models
   - Initialize SQLite database
   - Create first migration

2. **Extend Garmin integration** (Task 1.2)
   - Add activity fetching to existing API
   - Parse swim activities
   - Store in database

3. **Research Hevy API** (Task 1.3)
   - Check API documentation
   - Test authentication
   - Verify capabilities

4. **Create manual entry endpoints** (Task 1.4)
   - Body composition
   - Performance tests
   - Subjective metrics

Once Phase 1 is complete, you'll have data flowing in and can build intelligence on top!

---

## Questions to Resolve

1. **Hevy API Access:** Do you have Hevy API credentials? Is their API public?
2. **Alternative strength app:** If Hevy API is limited, would you prefer a different app with better API?
3. **Body composition measurement:** How are you tracking body fat? (scale, calipers, DEXA?)
4. **Notification preference:** Email, SMS, or just CLI output for daily reviews?
5. **Garmin device:** Which Garmin device do you use? (affects FIT file compatibility)

---

## Success Metrics

**Phase 1 Complete When:**
- ✓ Database created and migrations working
- ✓ Can import Garmin activities
- ✓ Can import Hevy workouts (or manual strength entry)
- ✓ Can manually enter body metrics

**Phase 2 Complete When:**
- ✓ Training plan stored in database
- ✓ Weekly schedule generated
- ✓ Comparison engine shows adherence %
- ✓ Can see planned vs actual side-by-side

**Phase 3 Complete When:**
- ✓ Daily review runs automatically
- ✓ Progress toward all 5 goals tracked
- ✓ System suggests plan adjustments
- ✓ Adjustments applied and logged

**System is "MVP Complete" When:**
- You can run `training review` each evening
- It shows what you did vs planned
- It tracks your progress toward goals
- It suggests when to adjust your plan
- Plans sync to Garmin/Hevy

**System is "Fully Featured" When:**
- Web dashboard shows all data
- Automatic notifications
- Historical analysis and trends
- Predictive recommendations
- Multi-week planning
