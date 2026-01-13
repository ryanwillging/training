# AI-Powered Training Optimization System

An intelligent training coach that reviews your daily activity, compares it against your plan, tracks progress toward your goals, and automatically adjusts your training to optimize performance.

## What This System Does

Every evening, this system:
1. **Pulls your workout data** from Garmin Connect and Hevy (strength training app)
2. **Compares what you actually did** vs what was planned
3. **Tracks your progress** toward 5 key fitness goals
4. **Analyzes patterns** (adherence, volume, trends)
5. **Decides if your plan needs adjustment** (too aggressive? lagging in one area?)
6. **Updates your training plan** accordingly
7. **Exports workouts** back to Garmin and Hevy for the upcoming week

Think of it as having an AI coach that continuously optimizes your training based on real data.

## Your Goals

1. **Maintain 14% body fat**
2. **Increase VO2 Max**
3. **Increase/maintain explosive & flexible capabilities** (for snowboarding, golf, wakeboarding, wood chopping)
4. **Improve 100yd freestyle time**
5. **Train 3-5 hours per week** at convenient times

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                      MORNING (Prep)                         │
│  Training Plan DB → Generate Workouts → Export to Apps     │
│              (Garmin watches, Hevy app)                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    You do your workouts
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    EVENING (Review)                         │
│  1. Import: Pull data from Garmin & Hevy                   │
│  2. Compare: Planned vs Actual                              │
│  3. Analyze: Progress toward goals                          │
│  4. Decide: Keep plan or adjust?                            │
│  5. Update: Modify upcoming workouts if needed              │
│  6. Report: Show you what happened and what's next          │
└─────────────────────────────────────────────────────────────┘
```

## Architecture

This system has several key components:

### 1. Data Intake Layer
- **Garmin Connector**: Pulls swim, run, bike, VO2 max data
- **Hevy Connector**: Pulls strength training sessions
- **Manual Entry**: Body fat, subjective metrics, performance tests

### 2. Database
- **Athletes**: Your profile and goals
- **Training Plans**: Current training program
- **Planned Workouts**: What you're supposed to do
- **Completed Activities**: What you actually did
- **Progress Metrics**: Body fat, VO2 max, swim times, etc.
- **Daily Reviews**: Analysis and insights

### 3. Analytics Engine
- **Comparison**: Match planned workouts to completed activities
- **Adherence**: Calculate completion rate (% of workouts done)
- **Volume**: Track weekly hours vs target
- **Progress**: Monitor improvement toward each goal
- **Trends**: Identify patterns and correlations

### 4. Daily Review System
- Runs automatically each evening
- Compares planned vs actual for today
- Calculates weekly adherence (rolling 7 days)
- Assesses fatigue/recovery
- Evaluates progress on all goals
- Generates insights and recommendations

### 5. Adaptive Planning Logic
- **Keep plan if**: Adherence >80%, all goals progressing, volume on target
- **Adjust plan if**:
  - Adherence <70% (plan too aggressive)
  - One goal lagging (pivot focus)
  - Progressing too fast in one area (redistribute)
  - Fatigue accumulating (insert deload)

### 6. Workout Export
- **Garmin**: Generate FIT files, upload to Garmin Connect
- **Hevy**: Create strength workouts via API
- **Apple Health**: (future) Export to HealthKit

## Current Status

### Already Built ✓
- FastAPI backend
- Garmin FIT file upload API
- 24 structured swim workouts (CSV format)
- Two 6-week training blocks:
  - 6-Week Swim Block (2x/week)
  - Athletic Performance Block (5-day structure: swim, strength, VO2, flexibility)
- CSV-to-FIT conversion pipeline

### In Progress 🚧
- **Phase 1**: Database setup and data import (Garmin, Hevy)
- **Phase 2**: Comparison engine and workout planning system
- **Phase 3**: Daily review automation and adaptive planning
- **Phase 4**: Workout export enhancements
- **Phase 5**: CLI and web dashboard

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for detailed roadmap.

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)**: System design, components, data flow, technology stack
- **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)**: Development phases, tasks, priorities, timeline
- **[TECHNICAL_SPEC.md](TECHNICAL_SPEC.md)**: Database schemas, API endpoints, JSON structures, CLI commands

## Quick Start (Coming Soon)

```bash
# Install dependencies
pip install -r requirements.txt

# Set up database
python scripts/setup_db.py

# Configure credentials
export GARMIN_EMAIL="your-email@example.com"
export GARMIN_PASSWORD="your-password"
export HEVY_API_KEY="your-hevy-api-key"

# Run API server
uvicorn api.app:app --reload

# Import your data
training sync --days 7

# Run daily review
training review
```

## Example Daily Review Output

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

ADJUSTMENTS MADE:
- Moved "Lower Body Strength" from Wed 6am → Sat 9am
- Reason: Better adherence on weekend mornings

NEXT WEEK FOCUS:
- Maintain swim volume (2x/week)
- Hit both strength sessions (Tue/Sat)
- Continue VO2 intervals (1x/week)
```

## Technology Stack

**Backend:**
- Python 3.11+
- FastAPI (web framework)
- SQLAlchemy (ORM)
- SQLite → PostgreSQL (production)

**Data Integration:**
- `python-garminconnect` (Garmin API)
- Hevy API (REST client)
- `fitparse` (FIT file parsing)

**Analytics:**
- Pandas (data analysis)
- NumPy (calculations)

**Future:**
- LangChain + Claude API (AI-powered insights)
- Plotly/Matplotlib (visualizations)
- Docker (deployment)

## Development Branch

All development is happening on branch: `claude/setup-daily-review-jGyVI`

## Contributing

This is a personal training system, but the architecture is designed to be extensible:
- Multi-athlete support (future)
- Additional sport integrations
- Custom goal types
- ML-based recommendations

## Privacy & Security

- All data stored locally by default
- Credentials in environment variables only
- No third-party analytics
- Data never leaves your machine (unless you deploy to cloud)

## License

Private repository - Personal use

## Next Steps

1. **Complete database setup** (models, migrations)
2. **Build Garmin activity import**
3. **Integrate Hevy API** (or create manual entry form)
4. **Implement comparison engine**
5. **Create daily review automation**
6. **Build adaptive planning logic**
7. **Add CLI commands**
8. **Create web dashboard**

## Questions?

See the detailed planning documents:
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) - Development roadmap
- [TECHNICAL_SPEC.md](TECHNICAL_SPEC.md) - Technical details

---

**Built with Claude Code by Ryan Willging**
