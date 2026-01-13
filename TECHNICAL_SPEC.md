# Technical Specification - Training Optimization System

## Database Schema (Detailed)

### Table: athletes
```sql
CREATE TABLE athletes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Current metrics
    current_body_fat REAL,
    current_vo2_max INTEGER,
    current_weight_lbs REAL,

    -- Goals (JSON)
    goals TEXT NOT NULL,  -- JSON: see schema below

    -- Preferences
    preferred_pool_length TEXT DEFAULT '25y',
    weekly_volume_target_hours REAL DEFAULT 4.0,
    timezone TEXT DEFAULT 'America/New_York'
);

-- Example goals JSON:
{
  "body_fat": {"target": 14.0, "unit": "%", "priority": "high"},
  "vo2_max": {"target": 55, "unit": "ml/kg/min", "priority": "medium", "direction": "increase"},
  "100yd_freestyle": {"target": 54, "unit": "seconds", "priority": "high", "direction": "decrease"},
  "explosive_strength": {"metric": "box_jump_height", "target": 36, "unit": "inches", "priority": "medium"},
  "weekly_volume": {"target": 4.0, "min": 3.0, "max": 5.0, "unit": "hours", "priority": "high"}
}
```

### Table: training_plans
```sql
CREATE TABLE training_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    athlete_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    status TEXT DEFAULT 'active',  -- active, completed, paused

    -- Plan metadata
    plan_type TEXT,  -- '6-week-swim', 'athletic-performance', 'custom'
    weekly_volume_target_hours REAL,
    focus_areas TEXT,  -- JSON array: ["swim", "strength", "vo2", "flexibility"]

    -- Tracking
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);
```

### Table: planned_workouts
```sql
CREATE TABLE planned_workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL,
    scheduled_date DATE NOT NULL,
    scheduled_time TIME,  -- Preferred time (e.g., 06:00 for morning)

    -- Workout details
    workout_type TEXT NOT NULL,  -- 'swim', 'strength', 'vo2_intervals', 'flexibility'
    workout_name TEXT,  -- e.g., "W1S1 - CSS Baseline", "Lower Body Strength"
    estimated_duration_minutes INTEGER,

    -- Workout definition (JSON - schema varies by type)
    workout_definition TEXT NOT NULL,

    -- Metadata
    priority TEXT DEFAULT 'normal',  -- 'critical', 'high', 'normal', 'optional'
    notes TEXT,
    completed BOOLEAN DEFAULT FALSE,
    completed_activity_id INTEGER,

    -- Tracking
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (plan_id) REFERENCES training_plans(id),
    FOREIGN KEY (completed_activity_id) REFERENCES completed_activities(id)
);

CREATE INDEX idx_planned_workouts_date ON planned_workouts(scheduled_date);
CREATE INDEX idx_planned_workouts_athlete ON planned_workouts(plan_id, scheduled_date);
```

### Table: completed_activities
```sql
CREATE TABLE completed_activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    athlete_id INTEGER NOT NULL,
    activity_date DATE NOT NULL,
    activity_time TIME,

    -- Source tracking
    source TEXT NOT NULL,  -- 'garmin', 'hevy', 'manual'
    external_id TEXT,  -- ID from source system (for deduplication)

    -- Activity details
    activity_type TEXT NOT NULL,  -- 'swim', 'run', 'bike', 'strength', 'other'
    activity_name TEXT,
    duration_minutes INTEGER,

    -- Detailed data (JSON - schema varies by type)
    activity_data TEXT NOT NULL,

    -- Links
    planned_workout_id INTEGER,  -- If this was a planned workout

    -- Metadata
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (athlete_id) REFERENCES athletes(id),
    FOREIGN KEY (planned_workout_id) REFERENCES planned_workouts(id),
    UNIQUE(athlete_id, source, external_id)  -- Prevent duplicate imports
);

CREATE INDEX idx_completed_activities_date ON completed_activities(athlete_id, activity_date);
CREATE INDEX idx_completed_activities_source ON completed_activities(source, external_id);
```

### Table: progress_metrics
```sql
CREATE TABLE progress_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    athlete_id INTEGER NOT NULL,
    metric_date DATE NOT NULL,
    metric_type TEXT NOT NULL,  -- 'body_fat', 'vo2_max', '100yd_time', etc.

    -- Value storage (use appropriate field for data type)
    value_numeric REAL,
    value_text TEXT,
    value_json TEXT,

    -- Context
    measurement_method TEXT,  -- e.g., 'scale', 'caliper', 'dexa', 'garmin_estimate'
    notes TEXT,

    -- Tracking
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);

CREATE INDEX idx_progress_metrics_athlete_type ON progress_metrics(athlete_id, metric_type, metric_date);
```

### Table: daily_reviews
```sql
CREATE TABLE daily_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    athlete_id INTEGER NOT NULL,
    review_date DATE NOT NULL,

    -- Analysis results (JSON)
    planned_vs_actual TEXT,  -- Comparison data
    adherence_metrics TEXT,  -- Weekly adherence, volume, etc.
    progress_summary TEXT,   -- Progress toward each goal

    -- Insights
    insights TEXT,  -- Generated insights (markdown or plain text)
    recommendations TEXT,  -- Suggested actions

    -- Plan adjustments
    adjustments_made TEXT,  -- JSON array of adjustments applied
    next_week_focus TEXT,   -- Text summary

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (athlete_id) REFERENCES athletes(id),
    UNIQUE(athlete_id, review_date)  -- One review per day per athlete
);

CREATE INDEX idx_daily_reviews_date ON daily_reviews(athlete_id, review_date);
```

### Table: plan_adjustments
```sql
CREATE TABLE plan_adjustments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL,
    review_id INTEGER,  -- Link to daily review that triggered it
    adjustment_date DATE NOT NULL,

    -- Adjustment details
    adjustment_type TEXT NOT NULL,  -- 'volume_change', 'focus_shift', 'reschedule', 'deload', 'exercise_swap'
    reasoning TEXT NOT NULL,

    -- Changes (JSON)
    changes TEXT NOT NULL,

    -- Tracking
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (plan_id) REFERENCES training_plans(id),
    FOREIGN KEY (review_id) REFERENCES daily_reviews(id)
);
```

---

## JSON Schemas

### Workout Definition Schemas

#### Swim Workout
```json
{
  "type": "swim",
  "pool_length": "25y",
  "sets": [
    {
      "set_number": 1,
      "description": "Warm-up",
      "intervals": [
        {
          "distance": 200,
          "stroke": "free",
          "intensity": "easy",
          "target_pace": null,
          "rest_seconds": 0
        }
      ]
    },
    {
      "set_number": 2,
      "description": "CSS Test Set",
      "intervals": [
        {
          "distance": 400,
          "stroke": "free",
          "intensity": "threshold",
          "target_pace": "1:30/100y",
          "rest_seconds": 60,
          "note": "Record time"
        },
        {
          "distance": 200,
          "stroke": "free",
          "intensity": "threshold",
          "target_pace": "1:28/100y",
          "rest_seconds": 90,
          "note": "Record time"
        }
      ]
    }
  ],
  "total_distance": 600,
  "estimated_duration_minutes": 60
}
```

#### Strength Workout
```json
{
  "type": "strength",
  "focus": "lower_body",
  "exercises": [
    {
      "exercise_name": "Box Jumps",
      "sets": 3,
      "reps": "6-8",
      "rest_seconds": 120,
      "intensity": "explosive",
      "notes": "Focus on height, not speed"
    },
    {
      "exercise_name": "Back Squat",
      "sets": 4,
      "reps": 6,
      "weight_pct": 80,
      "weight_unit": "% of 1RM",
      "rest_seconds": 180,
      "tempo": "2-0-1-0",
      "notes": "Controlled descent"
    },
    {
      "exercise_name": "Romanian Deadlift",
      "sets": 3,
      "reps": 8,
      "weight_pct": 70,
      "rest_seconds": 120,
      "notes": "Feel stretch in hamstrings"
    }
  ],
  "estimated_duration_minutes": 45
}
```

#### VO2 Intervals
```json
{
  "type": "vo2_intervals",
  "modality": "run",  // or "bike", "row"
  "warmup": {
    "duration_minutes": 10,
    "intensity": "easy"
  },
  "intervals": {
    "work_duration_seconds": 180,
    "rest_duration_seconds": 120,
    "work_intensity": "95-100% max HR",
    "rest_intensity": "easy jog/walk",
    "repetitions": 6,
    "notes": "Stay relaxed, focus on breathing"
  },
  "cooldown": {
    "duration_minutes": 5,
    "intensity": "easy"
  },
  "estimated_duration_minutes": 45
}
```

### Activity Data Schemas

#### Swim Activity (from Garmin)
```json
{
  "activity_type": "swim",
  "pool_length_meters": 22.86,
  "pool_length_unit": "25y",
  "duration_seconds": 3600,
  "distance_meters": 1500,
  "avg_pace_per_100y": "1:35",
  "calories": 450,
  "avg_heart_rate": 145,
  "max_heart_rate": 168,
  "laps": [
    {
      "lap_number": 1,
      "distance_meters": 100,
      "duration_seconds": 95,
      "stroke_type": "freestyle",
      "pace_per_100y": "1:35",
      "strokes": 42,
      "avg_heart_rate": 142
    }
    // ... more laps
  ],
  "notes": "Felt strong on threshold intervals"
}
```

#### Strength Activity (from Hevy)
```json
{
  "activity_type": "strength",
  "duration_minutes": 48,
  "exercises": [
    {
      "exercise_name": "Box Jump",
      "sets": [
        {"set_number": 1, "reps": 8, "weight_lbs": 0, "rpe": 7},
        {"set_number": 2, "reps": 7, "weight_lbs": 0, "rpe": 8},
        {"set_number": 3, "reps": 6, "weight_lbs": 0, "rpe": 9}
      ]
    },
    {
      "exercise_name": "Back Squat",
      "sets": [
        {"set_number": 1, "reps": 6, "weight_lbs": 225, "rpe": 8},
        {"set_number": 2, "reps": 6, "weight_lbs": 225, "rpe": 8},
        {"set_number": 3, "reps": 6, "weight_lbs": 225, "rpe": 9},
        {"set_number": 4, "reps": 5, "weight_lbs": 225, "rpe": 9.5}
      ]
    }
  ],
  "total_volume_lbs": 8100,
  "notes": "Legs felt fatigued from swim yesterday"
}
```

#### VO2 Activity (from Garmin)
```json
{
  "activity_type": "run",
  "duration_seconds": 2700,
  "distance_meters": 7200,
  "avg_pace_per_mile": "6:15",
  "calories": 520,
  "avg_heart_rate": 172,
  "max_heart_rate": 185,
  "vo2_max_estimate": 48,
  "intervals": [
    {
      "interval_number": 1,
      "type": "work",
      "duration_seconds": 180,
      "distance_meters": 800,
      "avg_heart_rate": 178,
      "avg_pace": "6:00/mi"
    },
    {
      "interval_number": 1,
      "type": "rest",
      "duration_seconds": 120,
      "distance_meters": 200,
      "avg_heart_rate": 145,
      "avg_pace": "10:00/mi"
    }
    // ... more intervals
  ]
}
```

---

## API Endpoints (Complete List)

### Athletes
```
GET    /api/athletes/{athlete_id}
POST   /api/athletes
PUT    /api/athletes/{athlete_id}
PATCH  /api/athletes/{athlete_id}/goals
```

### Training Plans
```
GET    /api/plans?athlete_id={id}
POST   /api/plans
GET    /api/plans/{plan_id}
PUT    /api/plans/{plan_id}
DELETE /api/plans/{plan_id}
GET    /api/plans/{plan_id}/schedule?week={week_number}
POST   /api/plans/{plan_id}/workouts
PUT    /api/plans/{plan_id}/workouts/{workout_id}
DELETE /api/plans/{plan_id}/workouts/{workout_id}
```

### Activity Import
```
POST   /api/import/garmin/activities
  Query params: ?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
  Response: {imported_count, skipped_count, activities: [...]}

POST   /api/import/hevy/workouts
  Query params: ?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
  Response: {imported_count, skipped_count, workouts: [...]}

POST   /api/activities (manual entry)
  Body: activity schema (JSON)
  Response: {id, message}
```

### Manual Metrics Entry
```
POST   /api/metrics/body-composition
  Body: {date, body_fat_pct, weight_lbs, measurement_method}

POST   /api/metrics/performance-test
  Body: {date, metric_type, value, unit, notes}

POST   /api/metrics/subjective
  Body: {date, sleep_quality, soreness_level, energy_level, notes}
```

### Analytics & Comparison
```
GET    /api/analytics/adherence
  Query params: ?athlete_id={id}&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
  Response: {adherence_pct, completed_count, planned_count, breakdown_by_type}

GET    /api/analytics/comparison/weekly
  Query params: ?athlete_id={id}&week=YYYY-WXX
  Response: {week, planned_workouts: [...], completed_activities: [...], matches: [...]}

GET    /api/analytics/volume
  Query params: ?athlete_id={id}&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
  Response: {planned_hours, actual_hours, delta, by_type: {...}}
```

### Progress Tracking
```
GET    /api/analytics/goals?athlete_id={id}
  Response: {goals: [{type, target, current, progress_pct, trend, ...}]}

GET    /api/analytics/goals/{goal_type}/history
  Query params: ?athlete_id={id}&period={7d|30d|90d|all}
  Response: {data_points: [{date, value}, ...], trend_line, rate_of_change}

GET    /api/analytics/progress/summary
  Query params: ?athlete_id={id}
  Response: Dashboard summary with all goals
```

### Daily Review
```
POST   /api/review/run
  Query params: ?athlete_id={id}&date=YYYY-MM-DD (defaults to today)
  Response: {review_id, insights, recommendations, adjustments_made}

GET    /api/review/latest?athlete_id={id}
  Response: Most recent daily review

GET    /api/review/{review_id}
  Response: Specific review details

GET    /api/reviews?athlete_id={id}&limit=10
  Response: List of recent reviews
```

### Plan Adjustments
```
POST   /api/plans/{plan_id}/adjust
  Body: {adjustment_type, reasoning, changes: {...}}
  Response: {adjustment_id, updated_plan}

GET    /api/plans/{plan_id}/adjustments
  Response: History of adjustments
```

### Workout Export
```
POST   /api/export/garmin/workout/{planned_workout_id}
  Response: {fit_file_url, upload_status}

POST   /api/export/garmin/week
  Query params: ?plan_id={id}&week={week_number}
  Response: {workouts_exported: [...], upload_status}

POST   /api/export/hevy/workout/{planned_workout_id}
  Response: {hevy_workout_id, workout_url}

GET    /api/export/fit/{workout_id}
  Response: Binary FIT file download
```

---

## CLI Commands

### Daily Operations
```bash
training review                         # Run daily review
training status                         # Quick status (today's plan, adherence)
training sync                          # Pull data from Garmin/Hevy
```

### Workout Management
```bash
training plan show                     # Show current week
training plan show --week 2            # Show specific week
training plan adjust                   # Interactive adjustment
training workouts upcoming             # Next 7 days
```

### Data Entry
```bash
training log --type swim --duration 60     # Quick manual entry
training log --type strength --hevy-import # Import from Hevy
training metrics --body-fat 14.5           # Log body composition
training test --type 100yd --time 58       # Log performance test
```

### Analytics
```bash
training goals                         # Show all goal progress
training adherence --period 30d        # 30-day adherence
training volume --week                 # This week's volume
training history --goal vo2_max        # VO2 max over time
```

### Export
```bash
training export garmin --week          # Export this week to Garmin
training export hevy --workout {id}    # Export workout to Hevy
```

---

## Environment Variables

```bash
# Database
DATABASE_URL=sqlite:///./training.db

# Garmin
GARMIN_EMAIL=your-email@example.com
GARMIN_PASSWORD=your-garmin-password

# Hevy
HEVY_API_KEY=your-hevy-api-key

# Optional
TIMEZONE=America/New_York
LOG_LEVEL=INFO
DAILY_REVIEW_TIME=18:00  # Run review at 6 PM
```

---

## File Structure

```
training/
├── api/
│   ├── app.py                    # FastAPI app (already exists)
│   ├── routes/
│   │   ├── athletes.py
│   │   ├── plans.py
│   │   ├── activities.py
│   │   ├── analytics.py
│   │   ├── review.py
│   │   └── export.py
│   └── schemas/
│       ├── athlete.py
│       ├── plan.py
│       ├── activity.py
│       └── workout.py
├── database/
│   ├── __init__.py
│   ├── models.py                 # SQLAlchemy models
│   ├── schema.sql                # SQL schema
│   └── migrations/
│       └── (alembic migrations)
├── integrations/
│   ├── garmin/
│   │   ├── client.py
│   │   ├── activity_importer.py
│   │   ├── workout_exporter.py
│   │   └── parsers.py
│   └── hevy/
│       ├── client.py
│       ├── activity_importer.py
│       └── workout_exporter.py
├── analytics/
│   ├── comparison.py             # Compare planned vs actual
│   ├── metrics.py                # Calculate adherence, volume
│   ├── progress.py               # Track goal progress
│   └── trends.py                 # Trend analysis
├── plans/
│   ├── plan_manager.py           # CRUD for plans
│   ├── workout_templates.py      # Workout builders
│   ├── scheduler.py              # Generate schedules
│   ├── adjuster.py               # Make plan adjustments
│   └── rules.py                  # Adjustment rules
├── review/
│   ├── daily_review.py           # Main orchestrator
│   ├── insights.py               # Generate insights
│   └── recommendations.py        # Plan recommendations
├── cli/
│   ├── __init__.py
│   ├── commands.py               # Click commands
│   └── display.py                # Pretty output
├── web/
│   ├── routes.py                 # Web UI routes
│   ├── templates/
│   └── static/
├── tests/
│   ├── test_api/
│   ├── test_integrations/
│   ├── test_analytics/
│   └── fixtures/
├── scripts/
│   ├── convert_swim_csvs.sh     # (already exists)
│   ├── csv_to_fit.sh             # (already exists)
│   └── setup_db.py               # Initialize database
├── garmin/                       # (already exists)
├── plans/                        # (already exists)
├── requirements.txt              # (already exists)
├── README.md
├── ARCHITECTURE.md               # (just created)
├── IMPLEMENTATION_PLAN.md        # (just created)
└── TECHNICAL_SPEC.md             # (this file)
```

---

## Testing Plan

### Unit Tests
- Database models (CRUD operations)
- Parsers (Garmin/Hevy activity parsing)
- Comparison logic (matching workouts)
- Progress calculations
- Adjustment rules

### Integration Tests
- API endpoints (request/response validation)
- Garmin API integration (with mocks)
- Hevy API integration (with mocks)
- Database transactions
- Daily review workflow

### End-to-End Tests
- Complete import → analysis → adjustment flow
- Export workflow (plan → FIT file → Garmin)
- CLI commands
- Web UI (with Selenium/Playwright)

### Test Data
- Create fixtures with sample workouts
- Mock Garmin responses
- Mock Hevy responses
- Sample athlete profiles with different goals

---

## Performance Considerations

### Database
- Use indexes on frequently queried fields (dates, athlete_id)
- Consider partitioning for large datasets (historical data)
- Use connection pooling for API

### API
- Cache frequently accessed data (current plan, athlete info)
- Paginate list endpoints
- Use async database queries where possible

### Data Import
- Batch imports for date ranges
- Use upsert logic to avoid duplicate checks
- Queue for background processing (Celery/RQ)

### Daily Review
- Run as background job (don't block API)
- Cache intermediate calculations
- Optimize queries (avoid N+1 problems)

---

## Security Considerations

### Credentials
- Store API credentials in environment variables only
- Never commit credentials to git
- Use secrets management (Vault, AWS Secrets Manager) in production

### Data Privacy
- All data stored locally by default
- No third-party analytics
- Option to encrypt database at rest
- Secure API with authentication (JWT tokens)

### API Security
- Rate limiting on endpoints
- Input validation on all requests
- SQL injection prevention (use ORM)
- CORS configuration for web UI

---

## Deployment Options

### Local Development
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python scripts/setup_db.py
uvicorn api.app:app --reload
```

### Production (Self-Hosted)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Systemd Timer (for daily review)
```ini
[Unit]
Description=Training Daily Review
Requires=training-api.service

[Timer]
OnCalendar=daily
OnCalendar=*-*-* 18:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

---

This technical specification provides the detailed schemas, API contracts, and implementation details needed to build the system. Use this alongside ARCHITECTURE.md and IMPLEMENTATION_PLAN.md as the complete reference for development.
