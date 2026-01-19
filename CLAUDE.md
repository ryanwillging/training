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
│   └── run_sync.py       # Local sync against production DB
└── tests/                # Test suite
    └── e2e/              # End-to-end tests (Playwright)
        ├── conftest.py   # Pytest fixtures
        ├── test_production.py # Production smoke tests
        └── test_design_system.py # Design consistency tests
```

## Vercel Deployment
- **Live URL**: https://training.ryanwillging.com
- **Alt URL**: https://training-rho-eight.vercel.app
- **Status**: Deployed and operational
- **Cron**: Daily sync at 5:00 UTC (midnight EST)

## API Endpoints

### Core
- `/` - API info and status (JSON)
- `/health` - Health check with database status
- `/dashboard` - Main dashboard (HTML)
- `/metrics` - Metrics tracking page (HTML)

### Reports
- `/api/reports/daily` - Daily training report (HTML)
- `/api/reports/weekly` - Weekly training report (HTML)

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
- `/api/plan/evaluate` - Run AI evaluation (POST)
- `/api/plan/upcoming` - Upcoming scheduled workouts

### Cron
- `/api/cron/sync` - Trigger data sync (POST, requires CRON_SECRET)
- `/api/cron/sync/status` - Cron job status

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

## Garmin Workout Sync

### Authentication
- Uses `garth` library for OAuth token management
- Tokens cached in `~/.garmin_tokens/`
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

## Goal Analysis (`analyst/`)
- **GoalAnalyzer**: Assesses progress toward goals, calculates trends
- **WorkoutRecommendationEngine**: Generates weekly workout suggestions
- Runs automatically via daily cron sync

## Training Plan System (`analyst/` + `plans/`)
The 24-week training plan system provides automated workout scheduling, Garmin integration, and AI-powered plan evaluation.

### Components
- **plan_parser.py**: Parses `plans/base_training_plan.md` into structured workout data
- **workout_scheduler.py**: Assigns dates to workouts, manages plan state
- **chatgpt_evaluator.py**: AI evaluation using OpenAI o1 (reasoning mode)
- **plan_manager.py**: Orchestrates all plan components

### Garmin Workout Integration
- **workout_manager.py**: Creates workouts in Garmin Connect format
- Supports: swim (A/B/test), lift (A/B), VO2 sessions
- Schedules workouts on Garmin calendar

### Nightly Cron Flow
1. Sync Garmin activities and wellness data
2. Sync Hevy workouts
3. Run goal analysis
4. **Run AI plan evaluation** (ChatGPT o1 reasoning mode)
   - Analyzes wellness, workouts, goal progress
   - Proposes modifications if needed
   - High-confidence, high-priority changes auto-applied

### Training Plan Structure
- **24 weeks**, 3 phases + taper
- **Test weeks**: 2, 12, 24 (400 TT)
- **Weekly cadence**:
  - Mon: Swim A (Threshold/CSS)
  - Tue: Lift A (Lower body)
  - Wed: REST
  - Thu: Swim B (VO2/400-specific) or Test on test weeks
  - Fri: VO2 Session (Run/Row/Bike)
  - Sat: Lift B (Upper body)
  - Sun: REST

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

# Trigger manual data sync (production)
curl -X POST https://training.ryanwillging.com/api/cron/sync \
  -H "Authorization: Bearer $CRON_SECRET"

# Check sync status (production)
curl https://training.ryanwillging.com/api/cron/sync/status

# Local development server (for testing changes)
source venv/bin/activate && uvicorn api.app:app --reload

# Local data sync (via API)
curl -X POST http://localhost:8000/api/import/sync

# Run sync locally against production database (preferred method)
source venv/bin/activate && python scripts/run_sync.py
```

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
- After merging a branch to main, delete the feature branch locally and remotely.

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
- `OPENAI_MODEL` - Model to use (default: o1-preview)

## Troubleshooting

### Common Issues
- **Garmin auth fails**: Credentials may have expired or MFA triggered. Check `GARMIN_EMAIL`/`GARMIN_PASSWORD` in Vercel env vars
- **Hevy sync empty**: Verify `HEVY_API_KEY` is valid. Test with: `curl -H "Authorization: Bearer $HEVY_API_KEY" https://api.hevyapp.com/v1/workouts`
- **Database errors**: Locally uses SQLite (`training.db`). For Vercel, ensure `DATABASE_URL` points to PostgreSQL
- **Env var whitespace errors**: Vercel env vars may contain hidden newline characters. If you see "contains leading or trailing whitespace" errors, re-enter the value in Vercel dashboard

### Vercel Serverless Limitations
- **Package imports fail**: `garminconnect` and `hevy-api-client` cannot import in Vercel's Python serverless runtime
- **Workaround**: Run `python scripts/run_sync.py` locally to sync data to production database
- **Dashboard sync button**: Will show import errors in production; use local sync instead for full functionality

### Checking Logs
```bash
# Vercel function logs
vercel logs

# Local server shows logs in terminal when running uvicorn
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
