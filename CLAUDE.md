# Training Optimization System

## Quick Reference

| Item | Value |
|------|-------|
| **Live URL** | https://training.ryanwillging.com |
| **Python** | 3.9+ |
| **Deploy** | `vercel deploy --prod` |
| **Local server** | `source venv/bin/activate && uvicorn api.app:app --reload` |
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
api/           FastAPI app (app.py=local, index.py=Vercel serverless)
analyst/       AI evaluation, plan parsing, workout scheduling
database/      SQLAlchemy models (models.py)
integrations/  Garmin + Hevy clients and importers
plans/         Training plan markdown (base_training_plan.md)
scripts/       Utility scripts (run_sync.py, setup_db.py)
tests/e2e/     Playwright tests
```

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

- **24 weeks**, anchored to January 20, 2025
- **Primary Goal**: 400yd freestyle (target TBD after baseline)
- **Test weeks**: 2, 12, 24
- **Weekly**: Mon=Swim A, Tue=Lift A, Wed=REST, Thu=Swim B, Fri=VO2, Sat=Lift B, Sun=REST
- **AI modifications**: Next 7 days only, stored in DailyReview for approval at `/reviews`

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
| `/dashboard` | Main dashboard (HTML) |
| `/reviews` | Plan modifications to approve/reject |
| `/metrics` | Body composition, performance tests |
| `/api/cron/sync/status` | Last sync info |
| `/api/plan/evaluate-with-context` | Run AI evaluation with user notes |

## Environment Variables

`DATABASE_URL`, `GARMIN_EMAIL`, `GARMIN_PASSWORD`, `HEVY_API_KEY`, `CRON_SECRET`, `OPENAI_API_KEY`, `OPENAI_MODEL`

## Vercel Config

- Dependencies: `pyproject.toml` (NOT requirements.txt)
- Timeout: 60s for AI evaluation (`vercel.json` → `functions.api/index.py.maxDuration`)
- Limitation: `garminconnect`/`hevy-api-client` cannot import in serverless

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

## Navigation (Current vs Planned)

| Current | Planned | Status |
|---------|---------|--------|
| `/dashboard` | Main Dashboard | Rename Phase A |
| - | `/explore` | New Phase A |
| `/reviews` | `/plan-adjustments` | Rename Phase A |
| `/metrics` | `/goals` | Rename Phase A |
| `/api/reports/daily` | - | Remove Phase A |

## Git Workflow

```bash
git status && git diff
git add -A && git commit -m "Description"
git push origin main
```

Worktrees: Main at `/Users/ryanwillging/claude projects/training`, features at `/Users/ryanwillging/conductor/workspaces/training/<city>`
