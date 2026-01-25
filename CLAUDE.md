# Training Optimization System - Claude Configuration

## Permission Mode
--permission-mode=dontAsk

## Requirements
- **Python**: 3.9+
- **Key Dependencies**: FastAPI, SQLAlchemy, garminconnect, playwright (for tests)

## Project Structure
```
training/
├── api/                    # FastAPI application
│   ├── app.py             # Main app entry point
│   ├── index.py           # Vercel serverless handler
│   ├── navigation.py      # Shared navigation component (PAGES registry)
│   ├── design_system.py   # Material Design CSS framework
│   ├── timezone.py        # Eastern timezone utilities (use instead of datetime.now)
│   ├── dashboard.py       # Dashboard HTML generation
│   ├── schemas.py         # Pydantic schemas for API
│   ├── routes/            # API route handlers
│   │   ├── __init__.py    # Exports all routers
│   │   ├── reports.py     # Daily/weekly report endpoints
│   │   ├── import_routes.py # Data import endpoints
│   │   ├── metrics_routes.py # Metrics tracking endpoints
│   │   └── plan.py        # Training plan endpoints
│   └── cron/              # Cron job handlers
│       └── sync.py        # Daily sync cron handler
├── analyst/               # Report generation & visualizations
│   ├── report_generator.py
│   ├── visualizations.py
│   ├── goal_analyzer.py   # Goal progress analysis
│   ├── plan_parser.py     # Parse training plan markdown
│   ├── plan_manager.py    # Orchestrate plan components
│   ├── workout_scheduler.py # Schedule workouts
│   └── chatgpt_evaluator.py # AI plan evaluation
├── database/              # SQLAlchemy models & session
│   ├── models.py          # Data models (Workout, Exercise, etc.)
│   └── base.py           # Database connection setup
├── integrations/          # External API integrations
│   ├── garmin/           # Garmin Connect client
│   │   ├── client.py     # API wrapper
│   │   ├── parsers.py    # Data transformation
│   │   ├── wellness_importer.py # Wellness data sync
│   │   ├── activity_importer.py # Activity sync
│   │   └── workout_manager.py # Create/schedule workouts
│   └── hevy/             # Hevy workout app client
│       ├── client.py     # API wrapper
│       └── activity_importer.py # Workout sync
├── plans/                 # Training plan files
│   └── base_training_plan.md # 24-week training plan
├── scripts/              # Utility scripts
│   ├── setup_db.py       # Database initialization
│   ├── run_sync.py       # Local sync against production DB
│   ├── capture_snapshots.py # API snapshot testing for refactoring
│   └── migrations/       # One-time database migrations (archived)
├── tests/                # Test suite
│   ├── e2e/              # End-to-end tests (Playwright)
│   │   ├── conftest.py   # Pytest fixtures
│   │   ├── test_production.py # Production smoke tests
│   │   └── test_design_system.py # Design consistency tests
│   └── snapshots/        # API response snapshots for verification
└── docs/                 # Documentation
    ├── ARCHITECTURE.md   # System architecture reference
    ├── TECHNICAL_SPEC.md # Original technical specification
    └── archive/          # Historical planning documents
```

## Product Roadmap

See `PRD.md` for the comprehensive product requirements document defining the evolution to a holistic health dashboard.

### Development Phases (from PRD)
1. **Phase A**: Enhanced dashboards (Main + Explore) with best-in-class visualizations
2. **Phase D**: New integrations (Strava, nutrition photo logging, self-care)
3. **Phase E**: Private health layer (genetics, blood work, supplements)
4. **Phase C**: Comparison engine and analytics
5. **Phase B**: iOS mobile app

### Key Terminology
- **Plan Evaluator**: The AI system that analyzes wellness/workout data and suggests modifications (stored in `DailyReview` model)
- **Plan Adjustments**: Page for reviewing/approving AI recommendations (renaming from `/reviews`)
- **Goals**: Page for goal management and progress (renaming from `/metrics`)

## Vercel Deployment
- **Live URL**: https://training.ryanwillging.com
- **Alt URL**: https://training-rho-eight.vercel.app
- **Status**: Deployed and operational
- **Cron**: Daily sync at 5:00 UTC (midnight EST)

### Function Configuration
AI evaluation requires longer timeout than Vercel's default (10s):
```json
// vercel.json
{
  "functions": {
    "api/index.py": {
      "maxDuration": 60
    }
  }
}
```

### Python Dependencies (Vercel)
Vercel uses `pyproject.toml` for Python dependencies (**NOT** requirements.txt):
```toml
[project]
dependencies = [
    "sqlalchemy>=2.0.0",
    "psycopg2-binary>=2.9.0",
    "python-dotenv>=1.0.0",
    "openai>=1.0.0",
    # Add new deps here, then redeploy
]
```
Vercel auto-generates `uv.lock` during build. Use `requirements.txt` for local development only.

## Sync Architecture

### Automated Sync via GitHub Actions
The system runs daily syncs at 5:00 UTC using GitHub Actions (see `.github/workflows/daily-sync.yml`):

**How it works:**
- GitHub Actions cron triggers daily at 5:00 UTC
- Runs `python scripts/run_sync.py` with full package access
- Writes to production Neon PostgreSQL database
- Creates CronLog entry with job_type="github_actions"
- Can be manually triggered from GitHub Actions UI

**Setup:** See `.github/SETUP.md` for configuring GitHub secrets

**Monitoring:**
- GitHub sends email if workflow fails
- Check status: `curl https://training.ryanwillging.com/api/cron/sync/status`
- View logs: https://github.com/ryanwillging/training/actions

#### Verifying GitHub Actions Setup

After configuring secrets and enabling the workflow:

1. **Trigger first run manually**:
   - Go to https://github.com/ryanwillging/training/actions/workflows/daily-sync.yml
   - Click "Run workflow" → Select "main" → Click "Run workflow"

2. **Check workflow execution**:
   ```bash
   # Check GitHub Actions logs for errors
   open https://github.com/ryanwillging/training/actions
   ```

3. **Verify CronLog was created**:
   ```bash
   curl https://training.ryanwillging.com/api/cron/sync/status | jq '.last_run'
   ```
   - Should show `job_type: "github_actions"`
   - Status should be "success" or "partial" (if some imports failed)
   - Check `hours_ago` is recent (<1 hour)

4. **Verify dashboard updated**:
   - Visit https://training.ryanwillging.com/dashboard
   - Header should show "Last sync: [recent timestamp]"
   - Wellness data should be current (not stale Monday date)

#### First Automated Run

The GitHub Actions cron is scheduled for **5:00 UTC daily** (midnight EST).

**First run timeline**:
- If you configured secrets on January 24 at 2pm EST, the first automated run will be January 25 at 12:00am EST
- Until then, dashboard shows the last manual or GitHub Actions sync
- You can trigger manually anytime from the GitHub Actions UI (see verification steps above)

### Manual Sync (Local)
For immediate data updates or testing:
- Run via `python scripts/run_sync.py`
- Full access to all Python packages
- Syncs to production Neon database
- Creates CronLog entry with job_type="manual_sync"

### Vercel Cron Endpoint (Monitoring Only)

The Vercel cron endpoint at `/api/cron/sync` is still configured and should be **kept for monitoring purposes**:

**Why it's still valuable**:
- Verifies Vercel deployment is healthy and can reach the database
- Acts as a fallback status check endpoint
- Provides a webhook target for external monitoring services
- Creates CronLog entries that help diagnose deployment issues

**Limitations**:
- **CANNOT import data** (missing garminconnect/hevy-api-client in serverless)
- Creates CronLog entry with status="partial" and import errors
- Not used for actual data syncing (GitHub Actions handles that)

**Configuration**: See `vercel.json` cron settings. The endpoint is called daily but doesn't perform imports.

### CronLog Tracking
All sync types persist execution logs to the `cron_logs` table:
- `job_type`: "github_actions" (automated), "manual_sync" (local), or "sync" (legacy Vercel)
- `status`: "success", "partial", or "failed"
- `run_date`: Eastern time (naive datetime)
- Import counts and error details

Dashboard and status endpoints query for ALL job types to show most recent sync.

#### Critical Patterns

**ALWAYS query all three job types** when displaying sync status:

```python
# CORRECT - Query all job types
last_sync = db.query(CronLog).filter(
    CronLog.job_type.in_(["sync", "manual_sync", "github_actions"])
).order_by(CronLog.run_date.desc()).first()

# WRONG - Only queries one job type
last_sync = db.query(CronLog).filter(
    CronLog.job_type == "sync"
).order_by(CronLog.run_date.desc()).first()
```

**Applied in**:
- `api/dashboard.py` - Dashboard header sync status
- `api/cron/sync.py` - `/api/cron/sync/status` endpoint
- `api/index.py` - Serverless status endpoint

**Rationale**: Users can trigger syncs via multiple methods (GitHub Actions, local script, Vercel cron). The dashboard must show the most recent sync regardless of source.

## Vercel Serverless Architecture

### Critical Limitation: Package Import Failures
Vercel's Python serverless runtime **cannot import** `garminconnect` or `hevy-api-client`. This is a permanent limitation, not a configuration issue.

**Implications**:
1. Nightly cron syncs will ALWAYS show "partial" status with import errors
2. Dashboard may show stale wellness data until local sync runs
3. Local `python scripts/run_sync.py` is required for actual data import

### Dual-Handler Pattern
- **`api/index.py`**: Vercel serverless handler (limited imports)
- **`api/app.py`**: FastAPI app for local development (full imports)
- Routes duplicated in both files must stay in sync

When adding new endpoints, update BOTH files.

## API Endpoints

### Core
- `/` - API info and status (JSON)
- `/health` - Health check with database status
- `/dashboard` - Main dashboard (HTML)
- `/metrics` - Metrics tracking page (HTML)

### Reports
- `/api/reports/daily` - Daily training report (HTML)
- `/api/reports/weekly` - Weekly training report (HTML, rolling 7 days)

### Data Import
- `/api/import/garmin/activities` - Import Garmin activities
- `/api/import/hevy/workouts` - Import Hevy workouts
- `/api/import/sync` - Full data sync (POST)
- `/api/sync` - Dashboard sync trigger (POST, no auth - limited in Vercel)

### Metrics
- `/api/metrics/body-composition` - Body composition data
- `/api/metrics/performance-test` - Performance test results
- `/api/metrics/subjective` - Subjective metrics
- `/api/metrics/history/{metric_type}` - Metric history

### Training Plan
- `/api/plan/status` - Current plan status and progress
- `/api/plan/initialize` - Initialize plan with start date (POST)
- `/api/plan/week` - Current week summary
- `/api/plan/week/{number}` - Specific week summary
- `/api/plan/sync-garmin` - Sync workouts to Garmin (POST)
  - Also scans and fixes any workouts with outdated format
- `/api/plan/scan-formats` - Scan and fix workout formats (POST)
  - Query param: `days_ahead` (default 14)
  - Verifies Garmin workouts use correct format (RepeatGroupDTO, reps conditions)
  - Automatically deletes and recreates any with outdated format
- `/api/plan/evaluate` - Run AI evaluation (POST)
- `/api/plan/upcoming` - Upcoming scheduled workouts

### Plan Reviews
- `/reviews` - Plan reviews page (HTML) - Review AI-suggested modifications
- `/api/plan/evaluation-context` - View data sent to AI for evaluation
- `/api/plan/reviews/latest` - Get most recent AI evaluation
- `/api/plan/reviews/{id}/action` - Approve/reject a modification (POST)
  - Body: `{"action": "approve" | "reject"}`
  - On approve: Updates ScheduledWorkout, syncs to Garmin (delete old, create new)
- `/api/plan/evaluate-with-context` - Run AI evaluation with user notes (POST)
  - Body: `{"user_context": "optional notes for AI to consider"}`

### Cron
- `/api/cron/sync` - Trigger data sync (GET for Vercel Cron, POST for manual)
  - Vercel Cron sends `x-vercel-cron` header (auto-authorized)
  - Manual: `Authorization: Bearer $CRON_SECRET`
- `/api/cron/sync/status` - Cron status with last run info (date, status, errors)

## Deployment Status
**Target**: Fully autonomous operation on Vercel (no local dependencies)

### Completed
- Vercel deployment configured and operational
- Neon PostgreSQL database connected (119+ activities synced)
- Cron job for daily sync (5:00 UTC)
- Environment variables set (DATABASE_URL, Garmin, Hevy, CRON_SECRET)

## Data Models
Key SQLAlchemy models in `database/models.py`:
- **CompletedActivity** - Training sessions (date, type, duration, source)
- **DailyWellness** - Garmin wellness data (sleep, stress, HRV, body battery, etc.)
- **Goal** - Structured goals with targets and tracking
- **GoalProgress** - Progress toward goals over time
- **WorkoutAnalysis** - Training pattern analysis and recommendations
- **ProgressMetric** - Body composition, performance tests, etc.
- **ScheduledWorkout** - Planned workouts from training plan
  - `scheduled_date`, `workout_type`, `week_number`
  - `garmin_workout_id`, `garmin_calendar_date` (Garmin sync tracking)
  - `status`: scheduled, completed, skipped, modified
- **CronLog** - Tracks cron job executions
  - `run_date`, `job_type`, `status` (success/partial/failed)
  - `garmin_activities_imported`, `garmin_wellness_imported`, `hevy_imported`
  - `errors_json`, `results_json`, `duration_seconds`
- **DailyReview** - AI plan evaluations and review history
  - `athlete_id`, `review_date` (unique constraint - one review per athlete per day)
  - `overall_assessment`, `progress_summary`, `next_week_focus`
  - `modifications_json`, `warnings_json`, `user_context`
  - `evaluation_type`: "nightly" or "on_demand"
  - `lifestyle_insights_json`: Structured insights (health/recovery/nutrition/sleep)
  - `approval_status`: pending, approved, rejected, no_changes_needed, error
  - **Note**: Multiple evaluations on same day UPDATE existing record (don't insert)

Data sources:
- **Hevy**: Strength training workouts and exercises
- **Garmin**: Activities, wellness data, fitness metrics

## Integrations

### Garmin Connect (`integrations/garmin/`)
- **Authentication**: Email/password via `garminconnect` library
- **Activities**: Cardio, swimming, cycling, strength
- **Wellness**: Sleep, stress, body battery, HRV, SpO2, respiration
- **Training**: Readiness score, training status, VO2 max, race predictions
- **Body**: Weight, body composition (if Garmin scale connected)
- **Files**: `client.py` (API), `parsers.py` (data transform), `wellness_importer.py` (wellness sync)

### Hevy (`integrations/hevy/`)
- **Authentication**: API key (Bearer token)
- **Data pulled**: Strength workouts, exercises, sets (weight/reps/RPE)
- **Client**: `client.py` handles API requests
- **Importer**: `activity_importer.py` syncs to database

### Upcoming Integrations (see PRD.md Phase D)
- **Strava**: Pull historical data, ongoing sync for segments/routes/photos only (no kudos)
- **Nutrition**: Photo-based logging with AI analysis (Claude/GPT-4 Vision) - no manual entry
- **Apple Fitness**: Deferred to Future Expansion (no Apple Watch currently)

### Private Health Data Layer (see PRD.md Phase E)
Phase E introduces sensitive health data storage with strict security requirements:

| Data Type | Storage | Encryption | Access |
|-----------|---------|------------|--------|
| Genetic data (23andMe, etc.) | Database | AES-256 | Private only |
| Blood work results | Database | AES-256 | Private only |
| Supplement logs | Database | Standard | Private only |
| Body measurements | Database | Standard | Private only |

**Security Requirements**:
- Files must NOT be downloadable via GitHub or ryanwillging.com
- All entry forms require authentication
- AI can access summarized data (context injection) but not raw files
- Public pages: Main Dashboard, Explore, Goals
- Private pages: Plan Adjustments, all health data, all entry forms

## Garmin Workout Sync

### Authentication
- Uses `garth` library for OAuth token management
- Tokens cached in `~/.garth/`
- Re-authenticate if tokens expire: `garth.login(email, password)` then `garth.save(path)`

### API Endpoints Used
- `GET /workout-service/workouts` - List all workouts
- `GET /workout-service/workout/{id}` - Get workout details
- `POST /workout-service/workout` - Create workout
- `PUT /workout-service/workout/{id}` - Update workout
- `DELETE /workout-service/workout/{id}` - Delete workout
- `POST /workout-service/schedule/{workoutId}` - Schedule workout on calendar
- `GET /calendar-service/year/{year}/month/{month}` - View calendar

### Swim Workout Settings
- Pool size: 25 yards (unitId: 230, unitKey: "yard")
- Stroke type: freestyle (strokeTypeId: 6)

### Sport Types
- Swimming: sportTypeId 4
- Strength Training: sportTypeId 5
- Running: sportTypeId 1

### Parsing Helpers (`workout_manager.py`)

| Function | Input Example | Returns |
|----------|---------------|---------|
| `parse_sets_string()` | `"4×50"`, `"3×8-10"` | `(reps, value, unit)` |
| `parse_sets_and_reps()` | `"3×8-10"` | `(num_sets, reps_per_set)` |
| `parse_strides_string()` | `"4×20s"`, `"3-4×15-20s"` | `(num_strides, duration_secs)` |
| `parse_rest_string()` | `"20s"`, `"15-20s"`, `"2 min"` | `seconds` |
| `parse_duration_string()` | `"5 min"`, `"30s"`, `"5-8 min"` | `seconds` |
| `parse_distance_string()` | `"300 yards"`, `"200y"` | `yards` |

### Workout Details Field Convention

When defining exercises in `_get_vo2_workout_details()`, `_get_lift_workout_details()`, etc., use these field names to control Garmin step creation:

| Field | Creates | conditionTypeId | Use For |
|-------|---------|-----------------|---------|
| `duration` | ExecutableStepDTO | 2 (time) | Warmup, cooldown, timed activities |
| `sets` | RepeatGroupDTO | 10 (reps) | Strength exercises (e.g., "3×8-10") |
| `strides` | RepeatGroupDTO | 2 (time) | Time-based intervals (e.g., "4×20s") |
| `distance` | ExecutableStepDTO | 3 (distance) | Swim distances, runs |

**Priority**: If multiple fields are present, `strides` takes precedence, then `duration`, then `sets`.

### Workout Payload Structure

Workouts are created via `POST /workout-service/workout` with this structure:

```python
{
    "sportType": {"sportTypeId": 5, "sportTypeKey": "strength_training"},
    "workoutName": "Lift A - Lower Body",
    "description": "Optional description",
    "workoutSegments": [
        {
            "segmentOrder": 1,
            "sportType": {"sportTypeId": 5, "sportTypeKey": "strength_training"},
            "workoutSteps": [
                # ExecutableStepDTO or RepeatGroupDTO items
            ]
        }
    ]
}
```

**Step Types**:
- `ExecutableStepDTO`: Single exercise step (warmup, interval, cooldown, rest)
- `RepeatGroupDTO`: Repeating group for sets (contains child steps)

**End Condition Types** (`conditionTypeId`):
| ID | Key | Use Case |
|----|-----|----------|
| 1 | `lap.button` | Manual lap/stop |
| 2 | `time` | Duration-based (seconds) |
| 3 | `distance` | Distance-based (meters) |
| 10 | `reps` | Rep-based (strength training) |

### Strength Workout Structure (RepeatGroupDTO)

Strength exercises with sets use `RepeatGroupDTO` to create rounds:

```python
# Example: Squat 3×8 reps
{
    "type": "RepeatGroupDTO",
    "stepOrder": 1,
    "numberOfIterations": 3,  # Number of sets
    "smartRepeat": False,
    "childSteps": [
        {
            "type": "ExecutableStepDTO",
            "stepOrder": 1,
            "stepType": {"stepTypeId": 3, "stepTypeKey": "interval"},
            "exerciseCategory": {"exerciseCategoryId": 119, "exerciseName": "SQUAT"},
            "endCondition": {"conditionTypeId": 10, "conditionTypeKey": "reps"},
            "endConditionValue": 8.0  # Reps per set
        }
    ],
    "repeatGroupDescription": {"value": "3 sets of 8 reps"}
}
```

**Key Points**:
- `numberOfIterations` = number of sets
- Child step's `endConditionValue` = reps per set
- Use `conditionTypeId: 10` for reps (not time or lap.button)
- The `parse_sets_and_reps()` helper in `workout_manager.py` extracts sets and reps from strings like "3×8-10"

### VO2 Workout Strides (RepeatGroupDTO)

Strides in VO2 warmups use `RepeatGroupDTO` with time-based intervals:

```python
# In _get_vo2_workout_details():
{"name": "Strides/pickups", "strides": "4×20s", "recovery": "45s", "notes": "Build to fast pace"}

# Creates this Garmin structure:
{
    "type": "RepeatGroupDTO",
    "stepOrder": 3,
    "numberOfIterations": 4,  # Number of strides
    "workoutSteps": [
        {
            "type": "ExecutableStepDTO",
            "stepOrder": 1,
            "stepType": {"stepTypeId": 3, "stepTypeKey": "interval"},
            "description": "Stride (20s)",
            "endCondition": {"conditionTypeId": 2, "conditionTypeKey": "time"},
            "endConditionValue": 20.0  # Duration in seconds
        },
        {
            "type": "ExecutableStepDTO",
            "stepOrder": 2,
            "stepType": {"stepTypeId": 4, "stepTypeKey": "recovery"},
            "description": "Walk-back recovery",
            "endCondition": {"conditionTypeId": 2, "conditionTypeKey": "time"},
            "endConditionValue": 45.0  # Recovery in seconds
        }
    ]
}
```

**Strides Field Format**:
- `strides`: `"N×Ds"` where N=repetitions, D=duration in seconds (e.g., "4×20s")
- `recovery`: Rest time between strides (default 45s for walk-back)
- Ranges supported: "3-4×15-20s" (uses average values)

**Key Points**:
- Use `strides` field (NOT `duration` or `sets`) for repetition-based warmup exercises
- Child steps use `conditionTypeId: 2` (time), not `1` (lap.button) or `10` (reps)
- The `parse_strides_string()` helper in `workout_manager.py` extracts strides and duration
- `_strides_to_garmin_steps()` creates the RepeatGroupDTO structure

### Automatic Format Verification

The system automatically scans and fixes outdated workout formats:

- **When it runs**: After every Garmin sync or workout modification
- **What it checks**:
  - Strength workouts: Use RepeatGroupDTO with reps (not lap.button)
  - VO2 workouts: Warmup/cooldown steps have time (not lap.button); strides are RepeatGroupDTO
- **What it does**: Deletes and recreates any workouts with incorrect format
- **Manual trigger**: `POST /api/plan/scan-formats?days_ahead=14`

The `verify_workout_format()` method in `workout_manager.py` fetches a workout from Garmin and checks:
1. **Strength**: Exercises use `conditionTypeId: 10` (reps), not `1` (lap.button)
2. **Strength**: Sets are structured as RepeatGroupDTO, not flat ExecutableStepDTO
3. **VO2**: Warmup/cooldown/other steps use `conditionTypeId: 2` (time), not `1` (lap.button)
4. **VO2**: Strides are RepeatGroupDTO with time-based child steps, not flat ExecutableStepDTO

### Local Garmin Sync (Required for Calendar Updates)

The `garminconnect` library does NOT support workout upload/creation. Use `garth` for direct API calls:

```python
import os
import garth
from dotenv import load_dotenv
load_dotenv('.env.production')

# Authenticate (tokens saved to ~/.garth/)
token_dir = os.path.expanduser("~/.garth")
try:
    garth.resume(token_dir)
except:
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")
    garth.login(email, password)
    garth.save(token_dir)
```

**Delete a workout from calendar:**
```python
workout_id = 1442151086  # From ScheduledWorkout.garmin_workout_id
garth.connectapi(f"/workout-service/workout/{workout_id}", method="DELETE")
```

**View calendar for a month:**
```python
# month is 0-indexed (0=Jan, 11=Dec)
response = garth.connectapi("/calendar-service/year/2026/month/0")
for item in response.get("calendarItems", []):
    if item.get("itemType") == "workout":
        print(f"{item['date']}: {item['title']} (id: {item['workoutId']})")
```

**Full sync script for modified workouts:**
```bash
source venv/bin/activate
python3 << 'EOF'
import os
import garth
from dotenv import load_dotenv
load_dotenv('.env.production')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import ScheduledWorkout
from datetime import date, timedelta

# Setup
token_dir = os.path.expanduser("~/.garth")
garth.resume(token_dir)

db_url = os.environ.get("DATABASE_URL", "").replace("postgres://", "postgresql://", 1)
engine = create_engine(db_url)
db = sessionmaker(bind=engine)()

# Find modified workouts with Garmin IDs
today = date.today()
workouts = db.query(ScheduledWorkout).filter(
    ScheduledWorkout.status.in_(["modified", "skipped"]),
    ScheduledWorkout.garmin_workout_id.isnot(None),
    ScheduledWorkout.scheduled_date >= today - timedelta(days=7)
).all()

# Delete each from Garmin and clear the ID
for w in workouts:
    print(f"Deleting {w.scheduled_date} {w.workout_type} (ID: {w.garmin_workout_id})")
    try:
        garth.connectapi(f"/workout-service/workout/{w.garmin_workout_id}", method="DELETE")
        w.garmin_workout_id = None
        w.garmin_calendar_date = None
        print("  ✓ Deleted")
    except Exception as e:
        print(f"  ✗ Error: {e}")

db.commit()
db.close()
EOF
```

**Note:** Workout creation is fully implemented in `workout_manager.py`. Supports:
- **Swim workouts**: Intervals with distance/time targets
- **Strength workouts**: Uses RepeatGroupDTO for sets with rep targets (see "Strength Workout Structure" above)
- **VO2/cardio sessions**: Running, rowing, cycling with interval structure

For modifications that change workout structure, the system deletes the old workout and creates a new one with the updated format.

## Goal Analysis
The AI evaluation pipeline (`chatgpt_evaluator.py`) is the primary system for goal analysis and recommendations. Rule-based analysis modules were consolidated into the unified AI evaluation.

## Training Plan System (`analyst/` + `plans/`)
The 24-week training plan system provides automated workout scheduling, Garmin integration, and AI-powered plan evaluation.

### Components
- **plan_parser.py**: Parses `plans/base_training_plan.md` into structured workout data
- **workout_scheduler.py**: Assigns dates to workouts, manages plan state
- **chatgpt_evaluator.py**: AI evaluation with lifestyle insights
  - Uses OpenAI models (gpt-4o, gpt-5.2, etc.)
  - Analyzes wellness, workouts, goals
  - Generates lifestyle insights (health/recovery/nutrition/sleep)
  - Returns `PlanEvaluation` with `LifestyleInsight` objects
- **plan_manager.py**: Orchestrates all plan components, stores evaluations

### Garmin Workout Integration
- **workout_manager.py**: Creates workouts in Garmin Connect format
- Supports: swim (A/B/test), lift (A/B), VO2 sessions
- Schedules workouts on Garmin calendar

### Automated Daily Flow (GitHub Actions)
The daily sync workflow runs at 5:00 UTC:

1. **Sync Garmin activities and wellness data**
2. **Sync Hevy workouts**
3. **Future: Run unified AI evaluation pipeline**
   - Analyzes wellness, workouts, goal progress
   - Generates lifestyle insights (health, recovery, nutrition, sleep)
   - Proposes modifications for next 7 days only (conservative approach)
   - Modifications stored as pending for user review at `/reviews`
   - Evaluation type marked as "nightly"
   - **Note**: AI evaluation not yet integrated into GitHub Actions workflow

### Sync Logging & Monitoring
Each sync run is logged to the `CronLog` table with:
- Timestamp, duration, and status (success/partial/failed)
- Count of imported activities/wellness/workouts
- Any errors encountered

Check last run status:
```bash
curl https://training.ryanwillging.com/api/cron/sync/status
```

View GitHub Actions history:
```bash
open https://github.com/ryanwillging/training/actions/workflows/daily-sync.yml
```

### Training Plan Structure
- **24 weeks**, 3 phases + taper
- **Plan Start Date**: January 20, 2025 (historical anchor - week numbers calculated from this date)
- **Primary Goal**: 400yd freestyle swim time (target TBD after baseline test)
  - 100yd time is derived from 400yd splits, not a separate goal
- **Test weeks**: 2, 12, 24 (400 TT)
- **Post-Week 24**: Start new 24-week cycle (Option A from PRD)
- **Quarterly Performance Tests** (see PRD.md):
  - Vertical jump, broad jump (explosive power)
  - Sit-and-reach, shoulder flexibility (mobility)
- **Weekly cadence**:
  - Mon: Swim A (Threshold/CSS)
  - Tue: Lift A (Lower body)
  - Wed: REST
  - Thu: Swim B (VO2/400-specific) or Test on test weeks
  - Fri: VO2 Session (Run/Row/Bike)
  - Sat: Lift B (Upper body)
  - Sun: REST

### Plan Anchoring
- The plan is **anchored to January 20, 2025** - week numbers are fixed
- Never recreate the 24-week plan; only adjust near-term workouts
- AI modifications are limited to the **next 7 days only**
- Future workouts remain unchanged until their evaluation window

### Unified Evaluation Pipeline
A single evaluation process is used for both nightly (cron) and on-demand (manual) evaluations:

| Trigger | Evaluation Type | Source |
|---------|-----------------|--------|
| Nightly cron | `nightly` | Automated after data sync |
| Manual via /reviews | `on_demand` | User-initiated with optional notes |

Both use `TrainingPlanManager.run_nightly_evaluation()` and store results in `DailyReview`.

### Lifestyle Insights
The AI provides detailed, actionable insights in four categories:

| Category | Description |
|----------|-------------|
| **Health** | Overall health observations from wellness metrics |
| **Recovery** | Training readiness, HRV trends, recovery status |
| **Nutrition** | Diet considerations based on goals and training load |
| **Sleep** | Sleep quality analysis and optimization tips |

Each insight includes:
- **Observation**: What the AI sees in the data
- **Severity**: `info`, `warning`, or `alert`
- **Actions**: 2-4 specific, actionable steps (e.g., "Set 10pm bedtime alarm")

Actions are designed to be specific enough for potential automation (calendar reminders, app notifications).

### Plan Review & Approval Workflow
The Reviews page (`/reviews`) displays AI-suggested modifications from nightly evaluations:

1. **View Modifications**: See pending changes with AI reasoning
2. **Approve/Reject**: Click buttons to accept or reject each modification
3. **Garmin Sync**: On approval, the system automatically:
   - Deletes the old workout from Garmin calendar
   - Creates a new workout with the modification applied
   - Schedules the new workout on Garmin calendar

**Supported Modification Types**:
- `add_rest` / `skip` - Mark workout as skipped, remove from Garmin
- `intensity` / `volume` - Update workout details, recreate in Garmin
- `reschedule` - Move workout to new date, update Garmin calendar
- `swap_workout` - Replace workout type, recreate in Garmin

### Manual AI Evaluation
Run AI evaluation manually with optional user context:
```bash
# Via API
curl -X POST https://training.ryanwillging.com/api/plan/evaluate-with-context \
  -H "Content-Type: application/json" \
  -d '{"user_context": "Feeling fatigued from travel this week"}'
```

The user context is included in the AI prompt, allowing the athlete to provide relevant information (fatigue, schedule constraints, injuries) that the AI should consider when evaluating the plan.

## Local Development Setup
```bash
# Create virtual environment (first time only)
python3.9 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install playwright browsers (for E2E tests)
playwright install

# Copy environment template and configure
cp .env.example .env
# Edit .env with your credentials
```

## Common Commands
```bash
# Deploy to production
vercel deploy --prod

# Trigger manual data sync via GitHub Actions
# Go to: https://github.com/ryanwillging/training/actions/workflows/daily-sync.yml
# Click "Run workflow" → Select "main" → Click "Run workflow"

# Check sync status (production)
curl https://training.ryanwillging.com/api/cron/sync/status

# Local development server (for testing changes)
source venv/bin/activate && uvicorn api.app:app --reload

# Run sync locally against production database
source venv/bin/activate && python scripts/run_sync.py
```

### Manual Sync with CronLog Tracking

When running manual syncs, `scripts/run_sync.py` automatically creates CronLog entries. Pattern to follow for new sync scripts:

```python
import time
import json
from database.models import CronLog
from api.timezone import get_eastern_now

start_time = time.time()

# ... perform sync operations ...

# Track import counts
garmin_wellness_imported = 0
garmin_activities_imported = 0
hevy_imported = 0
errors = []

# Create CronLog entry
log_entry = CronLog(
    run_date=get_eastern_now().replace(tzinfo=None),  # Remove timezone!
    job_type="manual_sync",  # or "sync" for automated, "github_actions" for CI
    status="success",  # or "partial"/"failed"
    garmin_activities_imported=garmin_activities_imported,
    garmin_wellness_imported=garmin_wellness_imported,
    hevy_imported=hevy_imported,
    errors_json=json.dumps(errors) if errors else None,
    results_json=json.dumps(results),
    duration_seconds=round(time.time() - start_time, 2)
)
db.add(log_entry)
db.commit()
```

Dashboard queries for ALL job types: `CronLog.job_type.in_(["sync", "manual_sync", "github_actions"])`

## Git Workflow
Commit changes regularly to keep local and remote in sync:
```bash
# Check status before committing
git status && git diff

# Stage and commit changes
git add -A && git commit -m "Description of changes"

# Push to remote
git push origin <branch>
```
**Important**:
- Commit working changes frequently. Don't let local drift from the repository.
- After merging a branch to main, delete the feature branch:
  - If branch has a worktree: `git worktree remove <path> && git branch -D <branch>`
  - Otherwise: `git push origin --delete <branch> && git branch -D <branch>`

## Git Worktrees

This project uses git worktrees for parallel development. Each worktree has a different branch checked out:

| Worktree Path | Branch |
|---------------|--------|
| `/Users/ryanwillging/claude projects/training` | `main` |
| `/Users/ryanwillging/conductor/workspaces/training/<city>` | Feature branches |

### Working with Worktrees
```bash
# List all worktrees
git worktree list

# Cannot checkout main from feature worktree (use main worktree instead)
cd "/Users/ryanwillging/claude projects/training" && git merge origin/<branch>

# Remove a worktree before deleting its branch
git worktree remove /path/to/worktree
git branch -D branch-name
```

**Important**: You cannot checkout a branch that's already in use by another worktree. To merge to main, cd to the main worktree first.

## CI/CD

### GitHub Actions
Tests run automatically via `.github/workflows/test-deployment.yml`:
- **Push to main**: Waits for Vercel deploy, then runs E2E tests
- **Pull requests**: Runs E2E tests against production
- **Manual**: Can trigger via GitHub Actions UI

## Testing

### Post-Deployment Tests (Playwright)
Run after each deployment to verify production is working:
```bash
# Test production
./scripts/test_deployment.sh

# Test local server
./scripts/test_deployment.sh --local

# Or with pytest directly
pytest tests/e2e/ --base-url https://training.ryanwillging.com
```

Tests verify:
- Health endpoint and database connectivity
- Daily/weekly report generation
- Report quality (no errors, proper HTML/CSS)
- Response times
- Error handling

### Unit Tests
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_reports.py
```

## Environment Variables (Vercel)
All required variables are configured:
- `DATABASE_URL` - Neon PostgreSQL connection string
- `GARMIN_EMAIL` - Garmin Connect email
- `GARMIN_PASSWORD` - Garmin Connect password
- `HEVY_API_KEY` - Hevy API key
- `CRON_SECRET` - Secret for cron authorization
- `OPENAI_API_KEY` - OpenAI API key (for ChatGPT plan evaluation)
- `OPENAI_MODEL` - Model to use (e.g., gpt-4o, gpt-5.2-2025-12-11)

## Troubleshooting

### Common Issues
- **Garmin auth fails**: Credentials may have expired or MFA triggered. Check `GARMIN_EMAIL`/`GARMIN_PASSWORD` in Vercel env vars
- **Hevy sync empty**: Verify `HEVY_API_KEY` is valid. Test with: `curl -H "Authorization: Bearer $HEVY_API_KEY" https://api.hevyapp.com/v1/workouts`
- **Database errors**: Locally uses SQLite (`training.db`). For Vercel, ensure `DATABASE_URL` points to PostgreSQL
- **Env var whitespace errors**: Vercel env vars may contain hidden newline characters. If you see "contains leading or trailing whitespace" errors:
  - **Vercel dashboard**: Re-enter the value manually (copy-paste may include newlines)
  - **CLI**: Use `printf` instead of `echo` to avoid trailing newlines:
    ```bash
    # Wrong - echo adds newline
    echo "my-api-key" | vercel env add MY_VAR production

    # Correct - printf doesn't add newline
    printf "my-api-key" | vercel env add MY_VAR production
    ```

### Vercel Serverless Limitations
- **Package imports fail**: `garminconnect` and `hevy-api-client` cannot import in Vercel's Python serverless runtime
- **Workaround**: Run `python scripts/run_sync.py` locally to sync data to production database
- **Dashboard sync button**: Will show import errors in production; use local sync instead for full functionality

### Lazy Import Pattern for Serverless
For packages that can't import in Vercel serverless, use conditional imports with availability flags:
```python
# At module level - attempt import, set flag
GARMIN_AVAILABLE = False
GarminWorkoutManager = None
try:
    from integrations.garmin.workout_manager import GarminWorkoutManager
    GARMIN_AVAILABLE = True
except ImportError:
    pass

# In functions - check flag before using
def sync_to_garmin(self):
    if not GARMIN_AVAILABLE:
        return {"error": "Garmin integration not available in serverless"}

    manager = GarminWorkoutManager()
    # ... rest of implementation
```
This allows the module to load in Vercel while gracefully degrading functionality.

### Virtual Environment Issues

**Bad interpreter error** (`/old/path/to/python3: no such file or directory`):
```bash
# Venv has hardcoded absolute paths - recreate it
cd "/Users/ryanwillging/claude projects/training"
rm -rf venv
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

**Missing packages after fresh checkout**:
```bash
venv/bin/pip install -r requirements.txt
```

**Verify venv is working**:
```bash
venv/bin/python -c "import garminconnect; print('✓ OK')"
```

### Checking Logs
```bash
# Vercel function logs
vercel logs

# Local server shows logs in terminal when running uvicorn

# GitHub Actions workflow logs
# https://github.com/ryanwillging/training/actions
```

## Architecture
- **Local**: FastAPI with SQLite (full functionality)
- **Vercel**: Simple Python handler (serverless-compatible)
- **Database**: PostgreSQL required for Vercel data persistence
- **Reports**: Tufte-style HTML with inline SVG visualizations

### Database Error Handling
When a query fails (e.g., missing table), the SQLAlchemy transaction is aborted. Call `db.rollback()` before subsequent queries:
```python
try:
    result = db.query(SomeModel).first()
except Exception:
    db.rollback()  # Required for next query to work
    result = None
```

### Garmin API Response Quirks
Some Garmin API endpoints return lists instead of dicts:
- `training_readiness` - List of daily readings (use `[0]` for most recent)
- `steps` - List of time intervals (sum all `steps` values)
- `max_metrics` - List (may be empty)
- `body_battery` - List with `bodyBatteryValuesArray` inside each item

The `wellness_importer.py` handles these variations.

### Timezone Handling (`api/timezone.py`)
All pages use Eastern time via the shared timezone module:
```python
from api.timezone import get_eastern_today, get_eastern_now

today = get_eastern_today()  # Instead of date.today()
now = get_eastern_now()      # Instead of datetime.now()
```
**Never use `date.today()` or `datetime.now()` directly** - Vercel runs in UTC.

### Database Comparison Pattern
When comparing database timestamps with current time, ALWAYS use:

```python
from api.timezone import get_eastern_now

# CORRECT - Remove timezone info before comparison
now = get_eastern_now().replace(tzinfo=None)
hours_ago = (now - db_record.run_date).total_seconds() / 3600

# WRONG - Will cause "can't subtract offset-naive and offset-aware" error
now = get_eastern_now()  # This is timezone-aware
hours_ago = (now - db_record.run_date).total_seconds() / 3600
```

**Rationale**: Database stores naive datetimes, `get_eastern_now()` returns timezone-aware. Must convert to naive before comparison.

## Navigation Pages
All HTML pages are registered in `api/navigation.py` and appear in the nav bar.

### Current vs Planned Navigation (see PRD.md)

| Current Path | Current Name | Planned Path | Planned Name | Status |
|--------------|--------------|--------------|--------------|--------|
| `/dashboard` | Dashboard | `/dashboard` | Main Dashboard | Rename in Phase A |
| - | - | `/explore` | Explore Dashboard | New in Phase A |
| `/reviews` | Reviews | `/plan-adjustments` | Plan Adjustments | Rename in Phase A |
| `/metrics` | Metrics | `/goals` | Goals | Rename in Phase A |
| `/upcoming` | Upcoming | `/upcoming` | Upcoming | Keep |
| `/api/reports/daily` | Daily Report | - | - | Remove in Phase A |
| `/api/reports/weekly` | Weekly Report | - | - | Remove in Phase A |

To add a new page, add it to the `PAGES` list in `api/navigation.py`.

## Design System (`api/design_system.py`)
All HTML pages use a consistent Material Design-inspired CSS framework:

### Features
- **Typography**: Roboto font with Material Design 3 type scale
- **Colors**: CSS custom properties (--md-primary, --md-surface, etc.)
- **Components**: Cards, buttons, forms, tables, alerts, progress bars
- **Responsive**: Mobile-first with breakpoints at 640px and 1024px
- **Navigation**: Sticky nav bar with mobile hamburger menu

### Adding New Pages
1. Add the page to `PAGES` list in `api/navigation.py`
2. Use `wrap_page()` from design_system.py:
   ```python
   from api.design_system import wrap_page
   content = '<h1 class="md-headline-large">My Page</h1>...'
   html = wrap_page(content, "Page Title", "/my-page")
   ```

### Adding New API Routes
1. Create a new router file in `api/routes/`:
   ```python
   # api/routes/my_feature.py
   from fastapi import APIRouter

   router = APIRouter(prefix="/my-feature", tags=["my-feature"])

   @router.get("/")
   def get_feature():
       return {"status": "ok"}
   ```

2. Export from `api/routes/__init__.py`:
   ```python
   from api.routes.my_feature import router as my_feature_router
   __all__ = [..., "my_feature_router"]
   ```

3. Include in `api/app.py`:
   ```python
   from api.routes import my_feature_router
   app.include_router(my_feature_router, prefix="/api")
   ```

### CSS Classes
- **Layout**: `.md-container`, `.md-grid`, `.md-grid-cols-2`
- **Cards**: `.md-card`, `.md-card-header`, `.md-card-content`
- **Typography**: `.md-headline-large`, `.md-title-medium`, `.md-body-large`
- **Forms**: `.md-input`, `.md-select`, `.md-btn`, `.md-btn-filled`
- **Tables**: `.md-table`, `.md-table-container`
- **Utilities**: `.mb-4`, `.mt-6`, `.text-secondary`, `.md-flex`

### Testing
Design system tests verify consistency across all pages:
```bash
pytest tests/e2e/test_design_system.py -v
```
