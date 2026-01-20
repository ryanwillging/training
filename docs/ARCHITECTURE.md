# Training Optimization System - Architecture

## Overview
An AI-powered training coach that performs daily reviews of activity data, compares against planned workouts, tracks progress toward goals, and adaptively adjusts training plans to optimize performance across multiple fitness domains.

## Goals
1. Maintain 14% body fat
2. Increase VO2 Max
3. Increase/maintain explosive and flexible capabilities (snowboarding, golf, wakeboarding, wood chopping)
4. Improve 100yd freestyle time
5. Train for 3-5hrs per week at convenient times

## System Components

### 1. Data Intake Layer
**Purpose:** Import workout data from external sources

**Components:**
- **Garmin Connector**
  - Pull completed activities from Garmin Connect API
  - Import: swim workouts, running, cycling, HR data, VO2 max estimates
  - Use `python-garminconnect` library

- **Hevy Connector** (or alternative strength app)
  - Pull completed strength training sessions via Hevy API
  - Import: exercises, sets, reps, weight, RPE
  - Support for exercise modifications on-the-fly

- **Manual Data Entry API**
  - Endpoint for entering body composition (body fat %)
  - Subjective metrics (energy levels, soreness, sleep quality)

### 2. Database Schema
**Technology:** SQLite initially (easy to migrate to PostgreSQL later)

**Tables:**
- **athletes**
  - id, name, email, created_at
  - current_body_fat, vo2_max, goals (JSON)

- **training_plans**
  - id, athlete_id, start_date, end_date, name
  - focus_areas (JSON: swim, strength, vo2, flexibility)
  - weekly_volume_target (hours)

- **planned_workouts**
  - id, plan_id, scheduled_date, workout_type
  - workout_definition (JSON: sets, reps, intervals, etc.)
  - priority, estimated_duration

- **completed_activities**
  - id, athlete_id, activity_date, source (garmin/hevy/manual)
  - activity_type, duration, data (JSON: detailed metrics)
  - planned_workout_id (nullable - links to plan if exists)

- **progress_metrics**
  - id, athlete_id, metric_date, metric_type
  - value, notes
  - Examples: body_fat, vo2_max, 100yd_time, weekly_volume

- **daily_reviews**
  - id, athlete_id, review_date
  - planned_vs_actual (JSON comparison)
  - insights (text analysis)
  - plan_adjustments (JSON: what changed and why)
  - next_week_focus (text)

### 3. Comparison Engine
**Purpose:** Compare planned workouts vs completed activities

**Logic:**
- Match completed activities to planned workouts by date and type
- Calculate adherence rate (% of planned workouts completed)
- Identify missed workouts and reasons (if manually entered)
- Calculate volume metrics (actual vs planned hours/week)
- Detect pattern deviations (consistently missing certain workout types)

**Output:**
- Weekly adherence score
- Volume comparison (planned vs actual)
- Workout type distribution
- Recovery metrics (days between hard sessions)

### 4. Progress Tracking System
**Purpose:** Monitor progress toward each goal

**Metrics per Goal:**

1. **Body Fat (14% target)**
   - Track body fat % over time
   - Calculate trend (weekly/monthly average)
   - Estimate caloric balance from activity volume

2. **VO2 Max**
   - Pull Garmin's VO2 max estimates
   - Track cardiovascular fitness trend
   - Monitor training load and recovery

3. **Explosive/Flexibility**
   - Track key lifts (box jump height, squat weight, RDL weight)
   - Monitor strength-to-weight ratio
   - Balance/stability assessments from planned tests

4. **100yd Freestyle Time**
   - Extract swim times from Garmin activities
   - Track CSS (Critical Swim Speed) improvements
   - Monitor swim frequency and volume

5. **Weekly Training Volume**
   - Track actual hours/week
   - Ensure 3-5hr range is maintained
   - Balance across modalities

**Analytics:**
- Rate of improvement per goal
- Goal priority ranking (which are on/off track)
- Correlations (e.g., swim volume vs 100yd time)

### 5. Daily Review System
**Purpose:** Evening analysis to generate insights and recommendations

**Process:**
1. **Data Collection** (runs automatically each evening)
   - Pull today's completed activities from Garmin/Hevy
   - Retrieve today's planned workout
   - Get recent progress metrics

2. **Analysis**
   - Compare planned vs actual for today
   - Calculate weekly adherence (rolling 7 days)
   - Assess fatigue/recovery (TSS, subjective notes)
   - Evaluate goal progress (weekly/monthly trends)

3. **Insight Generation** (AI-powered)
   - Identify what's working well
   - Flag areas of concern (missed workouts, declining metrics)
   - Suggest adjustments if needed

4. **Plan Adjustment Decision**
   - **Keep current plan if:**
     - Adherence >80%
     - All goals progressing as expected
     - Volume within 3-5hr target

   - **Adjust plan if:**
     - Adherence <70% (plan may be too aggressive)
     - One goal lagging significantly (pivot focus)
     - Progressing too quickly in one area (redistribute effort)
     - Injury/fatigue accumulating (deload needed)
     - Schedule conflicts (shift workout days)

5. **Generate Report**
   - Save to `daily_reviews` table
   - Output summary to user (CLI or notification)

### 6. Adaptive Planning Logic
**Purpose:** Modify training plan based on review insights

**Adjustment Types:**

1. **Volume Adjustments**
   - Increase/decrease weekly hours
   - Add/remove workout sessions

2. **Focus Shifts**
   - If swim time improving rapidly but VO2 lagging → add cardio, reduce swim
   - If missing strength sessions → simplify program or reduce frequency

3. **Workout Modifications**
   - Swap workout days to fit schedule
   - Replace exercises (e.g., box jumps → broad jumps if equipment unavailable)
   - Adjust intensity (if fatigue high, reduce percentages)

4. **Deload/Recovery**
   - Insert deload week if TSS accumulating
   - Add extra rest day if sleep/soreness poor

**Implementation:**
- Use rule-based system initially
- Store adjustment history for learning
- Future: ML model to predict optimal adjustments

### 7. Workout Export System
**Purpose:** Convert planned workouts to app-specific formats

**Garmin Export (already partially built):**
- Generate FIT files from workout definitions
- Support swim workouts (CSV → FIT conversion exists)
- Add running/cycling workouts (new)
- Upload via API to Garmin Connect

**Hevy Export:**
- Use Hevy API to create strength workouts
- Sync planned lifts to app
- Allow in-app exercise substitutions

**Apple Health Integration (future):**
- Export workouts to HealthKit
- Import body metrics from Apple Health

### 8. User Interface

**Phase 1 (MVP):**
- CLI commands for daily review
- API endpoints for data inspection

**Phase 2:**
- Simple web dashboard (FastAPI + HTML templates)
- Show weekly schedule
- Display progress charts
- View daily review summaries

**Phase 3:**
- Mobile-responsive web app
- Push notifications for daily review
- Workout reminders

## Data Flow

### Evening (Daily Review) - Human-in-the-Loop Workflow
```
1. Import Data:
   Garmin/Hevy APIs → Pull Today's Activities → Store in DB

2. Analysis:
   Compare to Plan → Calculate Adherence → Track Goal Progress
   → Generate Insights → Propose Plan Adjustments (if needed)

3. Human Review (CRITICAL):
   Present Review Summary → USER REVIEWS → USER APPROVES/REJECTS Changes

4. If Approved:
   Update Plan in DB → Generate Workouts → Export to Garmin/Hevy IMMEDIATELY
   → Send Notification (CLI output initially, push notification future)

5. Store Review:
   Save review, insights, adjustments, and approval status to daily_reviews table
```

**Key Change**: Workouts are exported **immediately after approval** (not the next morning).
This ensures approved plan changes are available on apps right away for upcoming workouts.

## Technology Stack

**Backend:**
- Python 3.11+
- FastAPI (existing)
- SQLAlchemy (ORM)
- SQLite → PostgreSQL (production)

**Data Integration:**
- `python-garminconnect` (existing)
- Hevy API (requests library)
- `fitparse` for reading FIT files

**Analytics:**
- Pandas for data analysis
- NumPy for calculations
- Matplotlib/Plotly for visualizations (future)

**AI/ML (future enhancement):**
- LangChain for structured insights
- Claude API for natural language review summaries
- Scikit-learn for predictive modeling

**Infrastructure:**
- Docker for deployment
- GitHub Actions for CI/CD
- Cron/systemd timer for daily review automation

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
- Database schema and migrations
- Garmin activity import
- Basic comparison engine
- Manual daily review CLI

### Phase 2: Integration (Weeks 3-4)
- Hevy API integration
- Progress tracking for all goals
- Automated daily review system
- Simple adjustment logic

### Phase 3: Intelligence (Weeks 5-6)
- Advanced analytics
- AI-powered insights
- Adaptive planning algorithm
- Web dashboard

### Phase 4: Polish (Week 7+)
- Notifications
- Mobile optimization
- Historical analysis
- Multi-athlete support

## Security & Privacy
- Store Garmin/Hevy credentials in environment variables
- Encrypt sensitive data at rest
- No sharing of workout data without consent
- Local-first architecture (data stays on your machine)

## Testing Strategy
- Unit tests for comparison logic
- Integration tests for API connectors
- End-to-end tests for daily review flow
- Mock Garmin/Hevy APIs for development

## Future Enhancements
- Coach recommendations via LLM
- Social features (training partners)
- Race/event planning
- Nutrition tracking integration
- Recovery score algorithms
- Wearable integration (Whoop, Oura)
