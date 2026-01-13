# Quick Start Guide - Next Steps

## What We Just Created

You now have a comprehensive plan for your AI-powered training coach! Here's what was created:

1. **README.md** - Project overview and vision
2. **ARCHITECTURE.md** - System design and components
3. **IMPLEMENTATION_PLAN.md** - Detailed development roadmap
4. **TECHNICAL_SPEC.md** - Database schemas, API contracts, CLI commands

## Immediate Next Steps (Phase 1)

### Step 1: Set Up Database (Priority: CRITICAL)

**What to do:**
```bash
# Create database directory structure
mkdir -p database/migrations

# You'll need to:
# 1. Install SQLAlchemy and Alembic
# 2. Create models.py with all the database tables
# 3. Set up Alembic for migrations
# 4. Run initial migration to create tables
```

**Files to create:**
- `database/__init__.py` - Database connection setup
- `database/models.py` - SQLAlchemy ORM models
- `database/schema.sql` - Raw SQL schema (for reference)
- `scripts/setup_db.py` - Initialize database script

**Why this is critical:**
Nothing else can work until we have a place to store data!

---

### Step 2: Extend Garmin Integration

**What to do:**
You already have `python-garminconnect` working for uploading FIT files. Now you need to:
- Pull activities FROM Garmin (reverse direction)
- Parse swimming activities (laps, times, strokes)
- Parse running/cycling activities (HR, pace, VO2 estimates)
- Store in `completed_activities` table

**Files to create:**
- `integrations/garmin/activity_importer.py`
- `integrations/garmin/parsers.py`

**Why this is important:**
You need to get your actual workout data INTO the system before you can compare it to your plan.

---

### Step 3: Hevy Integration (or Manual Entry Alternative)

**What to do:**
Research Hevy's API capabilities:
- Check if public API exists
- Test authentication
- Verify you can pull workout history

**If Hevy API is limited, create manual entry form:**
- `POST /api/activities/strength` endpoint
- Simple JSON format to log exercises, sets, reps

**Files to create:**
- `integrations/hevy/client.py`
- `integrations/hevy/activity_importer.py`
OR
- `api/routes/manual_entry.py`

---

### Step 4: Manual Metrics Entry

**What to do:**
Create API endpoints for entering data that doesn't come from apps:
- Body composition (body fat %, weight)
- Subjective metrics (sleep, soreness, energy)
- Performance test results (100yd time, box jump height)

**Files to create:**
- `api/routes/metrics.py`
- `api/schemas/metrics.py` (Pydantic validation)

---

## Key Questions to Answer

Before implementing, please clarify:

1. **Hevy API Access**
   - Do you have API credentials for Hevy?
   - Is there a public API? (Check: https://hevy.com/api or developer docs)
   - Alternative: Would you prefer a different strength training app with better API support?

2. **Body Composition Tracking**
   - How are you currently measuring body fat? (smart scale, calipers, DEXA scan?)
   - How often do you measure it?
   - Should this be manual entry or is there an API?

3. **Garmin Device**
   - Which Garmin device(s) do you use? (e.g., Forerunner 945, Fenix, etc.)
   - This affects FIT file compatibility for workouts

4. **Notification Preferences**
   - For daily review, do you want:
     - CLI output only?
     - Email notification?
     - SMS/push notification?
     - Just a log file?

5. **Workout Schedule**
   - What days/times do you typically work out?
   - Any constraints? (e.g., pool only open certain hours)
   - Preferred rest days?

6. **Current Baseline Metrics** (if known)
   - Current body fat %:
   - Current VO2 max:
   - Current 100yd freestyle time:
   - Current box jump height:
   - Current squat 1RM (or working weight):

## Development Environment Setup

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add new dependencies we'll need
pip install sqlalchemy alembic
pip install click rich  # For nice CLI
pip install pytest pytest-asyncio httpx  # For testing

# 4. Update requirements.txt
pip freeze > requirements.txt

# 5. Create environment file
cat > .env << EOF
DATABASE_URL=sqlite:///./training.db
GARMIN_EMAIL=your-email@example.com
GARMIN_PASSWORD=your-password
HEVY_API_KEY=your-hevy-key  # If available
TIMEZONE=America/New_York
LOG_LEVEL=INFO
EOF

# 6. Initialize database (once we create setup script)
python scripts/setup_db.py
```

## Testing Strategy

For each component you build:
1. Write unit tests first (TDD approach)
2. Test with mock data
3. Test with real APIs (carefully, to avoid rate limits)
4. Verify data is stored correctly in database

## Git Workflow

```bash
# You're already on the feature branch
git status  # Should show: claude/setup-daily-review-jGyVI

# As you complete tasks:
git add <files>
git commit -m "descriptive message"

# Push regularly
git push -u origin claude/setup-daily-review-jGyVI
```

## Progress Tracking

Use the todo list to track progress:
- Mark tasks as in_progress when you start
- Mark as completed when done
- Add new tasks as you discover them

## When Phase 1 is Complete

You'll know Phase 1 is done when:
- ✓ Database exists and is queryable
- ✓ You can import Garmin activities from the past week
- ✓ You can import (or manually enter) strength workouts
- ✓ You can manually enter body metrics
- ✓ All data is visible in the database

Then you'll move to Phase 2: Planning & Comparison!

## Helpful Commands (Once Built)

```bash
# Check status
training status

# Import recent data
training sync --days 7

# View workouts
training workouts upcoming

# Manual entry
training log --type swim --duration 60
training metrics --body-fat 14.5

# Run review
training review

# Check progress
training goals
```

## Resources

- **Garmin Connect API**: Already using `python-garminconnect` library
- **Hevy API**: Need to research - check https://hevy.com or contact support
- **SQLAlchemy Tutorial**: https://docs.sqlalchemy.org/en/20/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Alembic Migrations**: https://alembic.sqlalchemy.org/

## Need Help?

Refer back to:
- **ARCHITECTURE.md** - "How does this work?"
- **IMPLEMENTATION_PLAN.md** - "What do I build next?"
- **TECHNICAL_SPEC.md** - "What should this look like?"

## Let's Get Started!

The first concrete task is: **Create the database models**

Would you like me to:
1. Create the SQLAlchemy models (`database/models.py`)?
2. Set up Alembic for migrations?
3. Create the database initialization script?

Or do you want to answer the key questions above first?
