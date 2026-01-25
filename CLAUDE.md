# Training Optimization System

## Quick Reference

| Item | Value |
|------|-------|
| **Live URL** | https://training.ryanwillging.com |
| **Python** | 3.9+ |
| **Deploy Frontend** | `cd frontend && vercel --prod` |
| **Deploy API** | (Auto-deploys via GitHub Actions) |
| **Local Frontend** | `cd frontend && npm run dev` (port 3000) |
| **Local API** | `source venv/bin/activate && uvicorn api.app:app --reload` (port 8000) |
| **Sync data** | `python scripts/run_sync.py` (local) or GitHub Actions UI |
| **Check sync** | `curl https://training.ryanwillging.com/api/cron/sync/status` |
| **Run tests** | `pytest tests/e2e/ --base-url https://training.ryanwillging.com` |

## Documentation Map

| Doc | Purpose |
|-----|---------|
| `PRD.md` | Product roadmap, phases, terminology, security requirements |
| `docs/GARMIN_API.md` | Garmin workout creation, payload structures, API reference |
| `docs/ARCHITECTURE.md` | System architecture overview |
| `.github/SETUP.md` | GitHub Actions secrets configuration |

## Project Structure (Key Directories)

```
frontend/      Next.js 14 app (deployed to frontend.vercel.app, aliased to training.ryanwillging.com)
  src/app/     App Router pages (dashboard, explore, goals, plan-adjustments, upcoming)
  src/components/ React components (UI, charts, dashboard widgets)
  src/lib/     API client, utilities
api/           FastAPI app (app.py=local, index.py=Vercel serverless)
analyst/       AI evaluation, plan parsing, workout scheduling
database/      SQLAlchemy models (models.py)
integrations/  Garmin + Hevy clients and importers
plans/         Training plan markdown (base_training_plan.md)
scripts/       Utility scripts (run_sync.py, setup_db.py)
tests/e2e/     Playwright tests
```

## Architecture

**Two Separate Vercel Projects:**

1. **Frontend** (Next.js) - Project name: `frontend`
   - Deployed to: `frontend-smoky-five-99.vercel.app` (changes per deployment)
   - Production domain: `training.ryanwillging.com` ⚠️ Must point to this project
   - API calls proxied to backend

2. **Backend** (Python/FastAPI) - Project name: `training`
   - Deployed to: `training-ryanwillgings-projects.vercel.app`
   - Handles all `/api/*` endpoints
   - GitHub Actions runs daily sync at 5:00 UTC
   - ⚠️ Should NOT have training.ryanwillging.com domain (frontend only)

## Critical Patterns

### Timezone: Always use Eastern time
```python
from api.timezone import get_eastern_today, get_eastern_now
today = get_eastern_today()  # NOT date.today()
now = get_eastern_now()      # NOT datetime.now()
```

### Database datetime comparison
```python
# Remove tzinfo before comparing with DB timestamps
now = get_eastern_now().replace(tzinfo=None)
hours_ago = (now - db_record.run_date).total_seconds() / 3600
```

### CronLog: Query ALL job types
```python
last_sync = db.query(CronLog).filter(
    CronLog.job_type.in_(["sync", "manual_sync", "github_actions"])
).order_by(CronLog.run_date.desc()).first()
```

### Vercel serverless: Lazy imports
```python
GARMIN_AVAILABLE = False
try:
    from integrations.garmin.workout_manager import GarminWorkoutManager
    GARMIN_AVAILABLE = True
except ImportError:
    pass
```

### Database error recovery
```python
try:
    result = db.query(Model).first()
except Exception:
    db.rollback()  # Required before next query
```

## Sync Architecture

- **GitHub Actions** (5:00 UTC daily): Runs `scripts/run_sync.py`, creates CronLog with `job_type="github_actions"`
- **Manual sync**: Run `python scripts/run_sync.py` locally, creates CronLog with `job_type="manual_sync"`
- **Vercel cron**: Monitoring only (can't import garminconnect/hevy-api-client in serverless)

## Training Plan

- **24 weeks**, started January 20, 2026 (ends ~June 2026)
- **Current week**: Check `/api/plan/status` for live week number
- **Primary Goal**: 400yd freestyle (target TBD after Week 2 baseline test)
- **Test weeks**: 2, 12, 24
- **Weekly schedule**: Mon=Swim A, Tue=Lift A, Wed=REST, Thu=Swim B, Fri=VO2, Sat=Lift B, Sun=REST
- **AI modifications**: Next 7 days only, stored in DailyReview for approval at `/plan-adjustments`

## Key Terminology (from PRD.md)

- **Plan Evaluator**: AI that analyzes wellness/workouts and suggests modifications
- **Plan Adjustments**: Page for reviewing AI recommendations (renaming from `/reviews`)
- **Goals**: Page for goal management (renaming from `/metrics`)

## Development Phases (from PRD.md)

1. **Phase A**: Enhanced dashboards (Main + Explore)
2. **Phase D**: New integrations (Strava, nutrition photo logging)
3. **Phase E**: Private health layer (genetics, blood work)
4. **Phase C**: Comparison engine
5. **Phase B**: iOS mobile app

## API Endpoints (Key)

| Endpoint | Purpose |
|----------|---------|
| `/api/cron/sync/status` | Last sync info (job type, hours ago, import counts) |
| `/api/plan/status` | Current week, test week status, adherence rate |
| `/api/plan/upcoming?days=7` | Next N days of scheduled workouts |
| `/api/wellness/latest` | Most recent wellness data (HRV, sleep, etc.) |
| `/api/plan/evaluate-with-context` | Run AI evaluation with user notes |
| `/api/metrics/goals` | Goals with current/target values |
| `/api/plan/reviews/latest` | Latest AI review with proposed modifications |

## Environment Variables

`DATABASE_URL`, `GARMIN_EMAIL`, `GARMIN_PASSWORD`, `HEVY_API_KEY`, `CRON_SECRET`, `OPENAI_API_KEY`, `OPENAI_MODEL`

## Vercel Config

- Dependencies: `pyproject.toml` (NOT requirements.txt)
- Timeout: 60s for AI evaluation (`vercel.json` → `functions.api/index.py.maxDuration`)
- Limitation: `garminconnect`/`hevy-api-client` cannot import in serverless

## Vercel Debugging

**Check deployments:**
```bash
vercel ls --scope ryanwillgings-projects
vercel inspect <deployment-url>  # Shows aliases, build info
```

**Fix domain pointing to wrong project:**
```bash
# Get latest deployment URL from correct project
vercel ls --scope ryanwillgings-projects | grep frontend

# Point domain to that deployment
vercel alias set <deployment-url> training.ryanwillging.com
```

**Verify site is working:**
```bash
curl -I https://training.ryanwillging.com  # Should return 200 or 307
curl https://training.ryanwillging.com/api/cron/sync/status  # Check API
curl https://training.ryanwillging.com/api/plan/status  # Check plan status
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Garmin auth fails | Check credentials in Vercel env vars, may need re-auth |
| Hevy sync empty | Verify `HEVY_API_KEY` with `curl -H "Authorization: Bearer $KEY" https://api.hevyapp.com/v1/workouts` |
| Env var whitespace | Re-enter in Vercel dashboard (copy-paste adds newlines) |
| Bad interpreter error | Recreate venv: `rm -rf venv && python3 -m venv venv && pip install -r requirements.txt` |

## Adding New Pages

1. Add to `PAGES` list in `api/navigation.py`
2. Use `wrap_page()` from `api/design_system.py`

## Adding New API Routes

1. Create `api/routes/my_feature.py` with `router = APIRouter(...)`
2. Export from `api/routes/__init__.py`
3. Include in `api/app.py`: `app.include_router(my_feature_router, prefix="/api")`
4. **Also update `api/index.py`** (Vercel serverless handler)

## Navigation

**Live Routes (Phase A Complete):**
- `/dashboard` - Main Dashboard (6 widgets: Today's Plan, Recovery, Goals, This Week, Plan Changes, Sleep)
- `/explore` - Long-term trends and analytics
- `/goals` - Goal management and progress tracking
- `/plan-adjustments` - Review AI recommendations
- `/upcoming` - Scheduled workouts calendar

**Implementation Notes:**
- Frontend: Next.js 14 with React components
- Backend: FastAPI endpoints serve data via `/api/*`
- All routes are mobile-responsive

## Git Workflow

```bash
git status && git diff
git add -A && git commit -m "Description"
git push origin main
```

Worktrees: Main at `/Users/ryanwillging/claude projects/training`, features at `/Users/ryanwillging/conductor/workspaces/training/<city>`
