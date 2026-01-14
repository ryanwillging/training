# Training Optimization System - Claude Configuration

## Permission Mode
--permission-mode=dontAsk

## Project Structure
```
training/
├── api/                    # FastAPI application
│   ├── app.py             # Main app entry point
│   ├── routes/            # API route handlers
│   │   ├── reports.py     # Daily/weekly report endpoints
│   │   └── import_routes.py
│   └── cron/              # Cron job handlers
├── analyst/               # Report generation & visualizations
│   ├── report_generator.py
│   └── visualizations.py
├── database/              # SQLAlchemy models & session
│   ├── models.py          # Data models (Workout, Exercise, etc.)
│   └── base.py           # Database connection setup
├── integrations/          # External API integrations
│   ├── garmin/           # Garmin Connect client
│   └── hevy/             # Hevy workout app client
└── scripts/              # Utility scripts
```

## Vercel Deployment
- **Live URL**: https://training.ryanwillging.com
- **Alt URL**: https://training-rho-eight.vercel.app
- **Status**: Deployed and operational
- **Cron**: Daily sync at 5:00 UTC (midnight EST)

## Available Endpoints (Vercel)
- `/` - API info and status
- `/health` - Health check with database status
- `/api/reports/daily` - Daily training report (HTML)
- `/api/reports/weekly` - Weekly training report (HTML)
- `/api/cron/sync` - Trigger data sync (POST)
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

## Goal Analysis (`analyst/`)
- **GoalAnalyzer**: Assesses progress toward goals, calculates trends
- **WorkoutRecommendationEngine**: Generates weekly workout suggestions
- Runs automatically via daily cron sync

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

# Local data sync
curl -X POST http://localhost:8000/api/import/sync
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

## Troubleshooting

### Common Issues
- **Garmin auth fails**: Credentials may have expired or MFA triggered. Check `GARMIN_EMAIL`/`GARMIN_PASSWORD` in Vercel env vars
- **Hevy sync empty**: Verify `HEVY_API_KEY` is valid. Test with: `curl -H "Authorization: Bearer $HEVY_API_KEY" https://api.hevyapp.com/v1/workouts`
- **Database errors**: Locally uses SQLite (`training.db`). For Vercel, ensure `DATABASE_URL` points to PostgreSQL

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
