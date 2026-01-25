# Product Requirements Document: Holistic Health & Fitness Dashboard

## Project Overview

### Vision
Transform the current training optimization system into a comprehensive, AI-powered health and fitness dashboard that integrates multiple data sources, provides best-in-class visualizations, and enables data-driven optimization of training, nutrition, sleep, and recovery.

### Current State
- **Operational training system** at training.ryanwillging.com
- **Data sources**: Garmin (activities + wellness), Hevy (strength training)
- **AI evaluation**: OpenAI-powered nightly reviews with modification suggestions
- **24-week training plan**: Structured swim/lift/VO2 programming with Garmin integration
- **Web dashboard**: Material Design UI with basic reporting

### Target State
- **Holistic health platform**: Expand beyond training to include nutrition, sleep, recovery, and self-care
- **Multi-source integration**: Add Strava (historical + ongoing), Apple Fitness, nutrition tracking, manual logs
- **Enhanced visualization**: Best-in-class dashboards inspired by Garmin, Apple Health, Oura
- **Private health layer**: Secure storage for genetics (23andMe), quarterly blood work, supplements, body measurements
- **Comparison engine**: Sophisticated analytics for planned vs actual, goal tracking, correlations, predictive insights
- **Mobile experience**: iOS native app for meal photo logging, meditation tracking, voice input
- **Public profile**: Strava-like public dashboard with authenticated private sections

---

## Target Audience

### Primary User
- **Ryan Willging** - Individual athlete optimizing for:
  - Maintaining 14% body fat
  - Increasing VO2 Max
  - Improving 400yd freestyle swim time (100yd calculated from splits)
  - Maintaining explosive & flexible capabilities (snowboarding, golf, wakeboarding, wood chopping)
  - Training 3-5 hours per week at convenient times

### Future Users
- **Individual athletes** seeking comprehensive health optimization (not coaches)
- Single-athlete accounts with private data isolation

---

## Core Features

### 1. Enhanced Dashboard System

#### 1.1 Main Dashboard (Reimagined)
**Purpose**: Current, actionable, short-term view (today, this week)

**Widgets** (Essential, high-value info):
- **Today's Plan** - Scheduled workouts, completion status, time remaining
- **Recovery Status** - HRV, RHR, sleep quality, readiness score with color coding
- **Goals Progress** - 5 goals with current values, trend arrows (↑↓→), progress bars
- **This Week** - Adherence percentage, volume completed, workouts remaining
- **Plan Changes** - Count of pending AI recommendations (link to Plan Adjustments page)
- **Sleep Last Night** - Duration, quality score, HRV, REM %

**Design Principles**:
- Widget-based layout (6-8 compact cards)
- Mobile-responsive grid
- Real-time data freshness indicators
- One-tap navigation to drill-down pages

#### 1.2 Explore Dashboard (New)
**Purpose**: Long-term trends, secondary metrics, correlations, deep insights

**Features**:
- **Flexible time ranges**: 7/30/90 days, current week/month/quarter/year, custom range, all-time
- **Period comparisons**: "This month vs last month", "Q1 2026 vs Q1 2025"
- **Secondary metrics**: Training load, body battery trends, stress patterns, nutrition consistency
- **Correlation discovery**: Interactive charts showing relationships (sleep → performance, HRV → workout quality)
- **Pattern detection**: Simple statement format (e.g., "💡 Nights with 8+ hours sleep → 23% better VO2 performance")
- **Data export**: Download charts, CSV data

**Visualization Style**:
- **Overview**: Simple, clean, high-level (Apple-style activity rings, bold numbers)
- **Drill-down**: Detailed charts, data-dense Garmin-style graphs
- **Progressive disclosure**: Tap cards to expand into full-screen analysis

#### 1.3 Goals Page (Renamed from "Metrics")
**Purpose**: Editable goal management with progress tracking

**Goals (Current)**:
1. **Body Composition**: Maintain 14% body fat
2. **Cardiovascular Fitness**: Increase VO2 Max (trend-based, no specific target)
3. **Swim Performance**: Improve 400yd freestyle time
   - Current Baseline: TBD (record at Week 2 test)
   - Target: TBD (set after baseline, typically 5-10% improvement)
   - 100yd splits calculated from 400yd time
4. **Explosive & Flexible Capabilities**: Maintain/improve via quarterly performance tests
5. **Training Volume**: 3-5 hours per week

**Features**:
- Editable goals (add, modify, remove, set targets)
- Progress visualization (trend lines, goal runway, estimated achievement date)
- Historical tracking (quarterly, annual comparisons)
- Test result logging (swim times, performance tests)
- Goal-specific insights (factors affecting progress)

#### 1.4 Plan Adjustments (Renamed from "Reviews")
**Purpose**: Review and approve AI-suggested training modifications

**Existing Functionality** (Keep):
- View pending modifications with AI reasoning
- Approve/reject individual changes
- Automatic Garmin sync on approval (delete old workout, create new)

**Enhancements**:
- Make more prominent in navigation
- Surface count on Main Dashboard widget
- Add modification history log
- Batch approve/reject options

---

### 2. Data Integration Expansion

#### 2.1 Strava Integration
**Historical Import** (One-time):
- Pull ALL available Strava activities from account history
- Deduplicate with existing Garmin data (Garmin as source of truth)
- Import pre-Garmin era activities (fill historical gaps)

**Ongoing Sync**:
- Strava-specific data only: segments, routes, photos
- NO duplicate activities (Garmin auto-syncs to Strava)
- NO kudos/social features

#### 2.2 Apple Fitness/Health
**Status**: Deferred to post-MVP (not included in current phases)
- iPhone only, no Apple Watch - limited unique data
- Apple Health primarily aggregates Garmin data already synced
- Revisit if Apple Watch is added or data gaps identified
- See "Future Expansion" section for potential integration

#### 2.3 Nutrition Tracking
**Photo Logging** (Primary method):
- Mobile app: take meal photo
- AI analysis (Claude or GPT-4 Vision)
- Extract: calories, protein, carbs, fats, meal type (breakfast/lunch/dinner/snack)
- Manual override/editing capability

**Goals**:
- Track for awareness and body composition optimization
- No strict targets initially (flexible approach)
- Build data set for AI correlations (nutrition → performance/recovery)

#### 2.4 Self-Care Tracking
**Categories**:
- **Recovery**: Stretching, foam rolling, sauna, cold plunge (duration, type)
- **Mental Health**: Meditation (duration, type), journaling (yes/no), stress level (1-10)
- **Hydration**: Daily water intake (oz)
- **Supplements**: Name, dosage, timing (morning/evening/pre-workout)
- **Physical Therapy/Mobility**: Exercises, duration, pain levels

**Entry Methods**:
- Mobile app (iOS native)
- Web forms (authenticated)
- Voice logging via mobile ("I took my morning supplements")

---

### 3. Private Health Data Layer

**Purpose**: Secure storage of sensitive health data for AI analysis and personal reference

#### 3.1 Data Types
**Genetics**:
- 23andMe raw data file
- Third-party analysis documents
- Gene-specific insights (ACTN3, ACE, MTHFR, etc.)

**Blood Work**:
- Quarterly test results (comprehensive health panel)
- Markers: Lipids, glucose, hormones, vitamins, liver/kidney function, inflammation
- Trend analysis over time (year-over-year comparisons)

**Supplements**:
- Current stack with dosages and timing
- Changes over time (start/stop dates)
- Rationale/goals for each supplement

**Body Measurements**:
- Weight, body fat %, waist/hip/chest measurements
- Muscle mass, blood pressure, resting metabolic rate
- Manual entry via web forms

#### 3.2 Security & Access
**Storage**:
- Encrypted database fields OR separate private database
- NOT accessible via public website/API
- NOT in version control (GitHub)

**Access Methods**:
- Authenticated web pages (login required)
- Local-only access options (CLI, local server)
- API endpoints with special authentication

**Usage**:
- Available to Plan Evaluator (AI) for contextualized recommendations
- Example: "Given your MTHFR variant and current magnesium intake, consider switching to methylated forms"
- Example: "Your testosterone levels are suboptimal - prioritize sleep consistency and strength training"

**AI Integration Implementation**:
- **Approach**: Context injection (not RAG)
- When Plan Evaluator runs, decrypt relevant private data server-side
- Inject summarized context into AI prompt (not raw genetic file)
- Example prompt context:
  ```
  Genetic markers: ACTN3 (power-oriented), normal MTHFR
  Recent blood work (Jan 2026): Vitamin D 45 ng/mL (normal), Testosterone 650 ng/dL (normal)
  Current supplements: Vitamin D 5000 IU (morning), Creatine 5g (pre-workout)
  ```
- Private data never sent to AI in raw form
- User consent required for AI analysis of health data

---

### 4. Performance Testing System

#### 4.1 Explosive Power Tests (Quarterly)
**Tests**:
1. **Vertical Jump**: Lower body power (inches)
   - Standard: 20-24" average, 28"+ excellent
2. **Broad Jump**: Horizontal power (feet)
   - Standard: 7-8' average, 9'+ excellent

**Execution**:
- Gym or field completable
- Log best of 3 attempts
- Compare to previous quarters
- Track progress toward "maintain/improve" goal

#### 4.2 Flexibility Tests (Quarterly)
**Tests**:
1. **Sit-and-Reach**: Hamstring/lower back flexibility (inches past toes)
   - Standard: Touch toes average, 3"+ past excellent
2. **Shoulder Flexibility**: Overhead mobility (dowel lift height in inches)
   - Standard: 6-8" average, 10"+ excellent

#### 4.3 Swim Performance (Test Weeks: 2, 12, 24)
**Primary Goal**: 400yd freestyle time
**Derived Metric**: 100yd split times (calculated from 400yd)

**Existing in Plan**: Test weeks already scheduled, Garmin sync integrated

#### 4.4 VO2 Max Tracking
**Method**: Garmin estimated VO2 Max from cardio activities
**Frequency**: Continuous tracking via Garmin data sync
**Goal**: Increase over time (trend-based, no specific target)

#### 4.5 Training Plan Evolution (Post-Week 24)
**Strategy**: Start new 24-week cycle with updated goals

**Process**:
1. Complete Week 24 test (400yd freestyle time trial)
2. Review all quarterly performance test results
3. Analyze goal progress and adherence patterns
4. Set new targets based on achieved results
5. Generate new 24-week plan with adjusted progressions

**AI Assistance**: Plan Evaluator can suggest goal adjustments based on:
- Rate of improvement across the cycle
- Adherence patterns (what worked, what didn't)
- Recovery trends and interference patterns

---

### 5. Sleep Optimization

#### 5.1 Priority Metrics (Science-Backed)
Based on 2025-2026 research and Bryan Johnson's Blueprint protocol:

**Top Priority**:
1. **Sleep Consistency**: Bedtime and wake time regularity (target: <15min variance)
2. **HRV (Heart Rate Variability)**: Pre-sleep and overnight trends
3. **Resting Heart Rate**: Pre-sleep RHR and overnight pattern
4. **REM Sleep**: Duration (minutes) and percentage of total sleep (target: 20-25%)
5. **Deep Sleep**: Duration and percentage (target: 15-20% of total sleep)
   - Critical for physical recovery and muscle repair
   - Garmin tracks this via sleep stages
6. **Sleep Environment**: Room temperature (target: 67°F), pre-sleep routine adherence

**Data Source**: Garmin watch (current setup)
- Garmin provides: sleep stages, HRV, RHR, sleep score, body battery, respiration

**Note**: Oura ring has superior HRV/RHR accuracy per 2025 validation study, but Garmin data is directionally useful. Consider Oura upgrade if sleep becomes primary optimization focus.

#### 5.2 Visualizations
- **Sleep Consistency Chart**: Bedtime/wake time scatter plot over 30 days with consistency bands
- **HRV Trends**: Nightly HRV with 7-day and 30-day moving averages
- **Sleep Stages**: Stacked bar chart showing REM, Deep, Light percentages over time
- **REM + Deep Tracking**: Minutes and percentage with weekly averages
- **Correlation Views**: Sleep metrics → next-day workout performance

---

### 6. Comparison Engine

**Purpose**: Data presentation layer showing what happened, what patterns exist, trends over time

**Key Principle**: Comparison engine presents data; Plan Evaluator (AI) provides actionable recommendations

#### 6.1 Planned vs Actual
**Weekly View Example**:
```
Week of Jan 20-26, 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADHERENCE: 80% (4/5 workouts completed)

Planned                    Actual                     Status
Mon: Swim A (60min)     →  Swim (58min, 1400y)       ✓ Complete
Tue: Lift A (45min)     →  Lift (42min, 3 exercises) ✓ Complete
Wed: REST               →  REST                       ✓
Thu: Swim B (60min)     →  ✗ MISSED                  ✗ Missed
Fri: VO2 Run (45min)    →  Run (47min, 6 intervals)  ✓ Complete
Sat: Lift B (45min)     →  Lift (40min, 4 exercises) ✓ Complete
Sun: REST               →  REST                       ✓
```

**Features**:
- Adherence percentage (weekly, monthly, quarterly)
- Volume tracking (planned hours vs actual hours)
- Miss patterns (identify recurring schedule conflicts)
- Workout type breakdown (swim/lift/VO2/rest distribution)

#### 6.2 Goal vs Current
**Dashboard Cards**:
```
Goal: 14% Body Fat
Current: 15.2%
Trend: ↓ -0.3% vs last month
Progress: 60% to goal (1.2% remaining)
```

**Features**:
- Current value vs target
- Trend indicator (↑↓→)
- Progress percentage
- Historical chart (6 months, 1 year, all-time)
- Estimated achievement date (if linear trend continues)

#### 6.3 Period Comparisons
**Example Views**:
- "This week vs last week": Training volume, sleep quality, adherence
- "This month vs last month": Goal progress, workout distribution, recovery metrics
- "This quarter vs last quarter": Performance test results, body composition, VO2 max

**Features**:
- Side-by-side metric comparison
- Percentage change indicators
- Sparklines showing trends
- Custom date range picker

#### 6.4 Optimal vs Actual
**Sleep Example**:
```
Optimal: 8 hours, bedtime 8:30pm, wake 5:00am
Actual (last 7 days): 7.4 hours avg, bedtime 9:15pm avg, wake 5:00am
Gap: -36 min sleep, +45 min late bedtime
```

**Features**:
- Define optimal ranges for key metrics
- Track actual vs optimal over time
- Gap analysis (how far from optimal)
- Consistency scoring (variance from optimal)

#### 6.5 Correlations (Pattern Detection)
**Simple Statement Format**:
```
💡 Pattern Detected:
Nights with 8+ hours sleep → 23% better VO2 workout performance
(based on 12 weeks of data, r=0.67)
```

**Features**:
- Auto-detect correlations across all metrics
- Statistical significance indicators (correlation coefficient, sample size)
- Present insights, NOT recommendations (recommendations go to Plan Adjustments)
- Visualization: Scatter plots, heatmaps, correlation matrices

**Example Correlations to Track**:
- Sleep duration → workout performance
- HRV → next-day readiness
- Nutrition timing → recovery
- Training volume → body composition
- Rest days → explosive power test results

---

### 7. Enhanced Analytics

**Purpose**: Answer strategic questions about performance optimization

#### 7.1 Performance Drivers
**Question**: "What factors correlate with better workout completion and adherence?"

**Analysis**:
- Compare workout completion rates against pre-workout conditions
- Track: sleep quality, HRV, RHR, rest days since last session
- Identify patterns in completed vs skipped workouts

**Output**:
```
Workout Completion Patterns:
  • HRV > 60ms: 92% completion rate (vs 71% when below)
  • 7+ hours sleep: 88% completion rate (vs 65% when below)
  • 48+ hours since hard session: Better perceived effort
```

**Note**: Subjective workout quality scoring excluded initially - difficult to measure consistently. Focus on objective metrics (completion, adherence, duration vs planned).

#### 7.2 Predictive Analytics
**Question**: "When will I hit my 400yd freestyle goal?"

**Analysis**:
- Linear regression on test results (weeks 2, 12, 24)
- Factor in training adherence, volume trends
- Adjust for seasonality (test schedule)

**Output**:
```
400yd Freestyle Goal Projection:
Current: 4:45 (Week 2 test)
Target: 4:20
Trend: -3 seconds per test cycle
Projected achievement: Week 20 (± 2 weeks)
Confidence: Moderate (3 data points)
```

#### 7.3 Recovery Pattern Analysis
**Question**: "How long does it take me to recover from hard sessions?"

**Analysis**:
- Track HRV, RHR, body battery after high-intensity workouts
- Identify recovery time to baseline (24hrs, 48hrs, 72hrs+)
- Compare by workout type (swim vs lift vs VO2)

**Output**:
```
Your Recovery Timeline:
  • VO2 Sessions: 48-72 hours to baseline HRV
  • Hard Swim Sets: 36-48 hours
  • Heavy Lifts: 48 hours (upper body faster than lower)

Recommendation: Schedule high-intensity workouts 48+ hours apart
```

#### 7.4 Optimization Insights
**Question**: "What sleep duration gives me the best HRV?"

**Analysis**:
- Bucket sleep durations (<6, 6-7, 7-8, 8-9, 9+ hours)
- Calculate average HRV for each bucket
- Identify optimal range

**Output**:
```
Your Sleep-HRV Optimization:
  <7 hours: 52ms avg HRV
  7-8 hours: 58ms avg HRV
  8-9 hours: 67ms avg HRV ⭐ OPTIMAL
  9+ hours: 64ms avg HRV (diminishing returns)
```

#### 7.5 Interference Pattern Detection
**Question**: "Does strength training before swimming hurt swim performance?"

**Analysis**:
- Compare swim workouts preceded by lift (within 24hrs) vs preceded by rest
- Measure: swim pace, RPE, volume completed

**Output**:
```
Lift → Swim Interference Analysis:
  • Lift within 24hrs: -8% swim pace, +1.5 RPE
  • Lift within 48hrs: -3% swim pace, +0.5 RPE
  • 48+ hours rest: Baseline performance

Pattern: Lower body lifts have greater interference than upper body
```

---

### 8. Mobile Application (iOS Native)

**Purpose**: Seamless on-the-go logging for nutrition, meditation, self-care

**Platform**: iOS native (Swift/SwiftUI) for simplicity and performance

#### 8.1 Core Features
**Meal Photo Logging**:
- Camera integration (take photo or choose from library)
- AI nutrition analysis (Claude or GPT-4 Vision API)
- Extracted data: calories, protein, carbs, fats, meal type (standardized schema)
- Edit AI estimates if needed (no separate manual entry form)
- Photo timestamp from EXIF or capture time stored with entry
- Save to database, sync to web dashboard

**Error Handling**:
- AI can't identify food → Prompt user to retake photo with tips ("better lighting", "closer view")
- Low confidence (<50%) → Flag for review, show AI estimate as editable
- Multiple items in photo → AI itemizes each, user confirms totals
- Photo quality poor → Suggest retake before analysis

**Meditation Logging**:
- Quick entry: duration (minutes), type (breathing, mindfulness, guided)
- Timer integration (start/stop within app)
- Optional notes field

**Voice Input**:
- Voice-to-text: "I took my morning supplements" → log supplement entry
- Voice commands: "Log 20 minutes meditation", "Log sauna session 30 minutes"

**Voice Logging Scope** (Phase B):
- **Supported**: Self-care activities
  - "I took my morning supplements"
  - "Log 20 minutes meditation"
  - "Log sauna 30 minutes"
  - "Log 64 ounces water"
- **Not Supported** (initially):
  - Complex workout logging: "Log deadlift 3 sets of 8 at 225"
  - Multi-item nutrition: "Ate chicken, rice, and broccoli"
- **Future**: Expand voice commands based on usage patterns

**Quick Self-Care Logging**:
- Predefined buttons: Stretch, Foam Roll, Sauna, Cold Plunge, Hydration
- Tap to log, optional duration/notes

#### 8.2 Mobile Notifications
**Daily Prompts** (reminder-style, no insights/anomalies):
- "Log today's meals" (evening prompt if no meals logged)
- "Did you complete your workout?" (post-scheduled workout time)
- "Take evening supplements" (user-defined time)
- "Bedtime in 30 minutes" (based on sleep consistency goal)
- "How's your sleep?" (morning prompt)

**User Control**:
- Enable/disable by category
- Set notification times
- Snooze/dismiss options

#### 8.3 UI Design
- **Simple, fast, minimal friction**
- Large tap targets for logging
- Camera-first for meals (single tap to photo)
- Voice button prominently displayed
- Sync status indicator
- Offline mode with background sync

---

### 9. Authentication & Privacy

#### 9.1 User Model
**Current**: Single user (Ryan)
**Future**: Multi-user support (individual athletes, not coaches)

**Architecture**:
- User accounts with email/password
- Each user has isolated data (no cross-user access)
- Role-based permissions (future: admin, user)

#### 9.2 Public vs Private Pages
**PUBLIC (no login required)**:
- Main Dashboard (Strava-like public profile)
- Explore Dashboard (long-term trends, anonymized if sensitive)
- Goals page (progress toward fitness goals)

**PRIVATE (login required)**:
- Plan Adjustments (AI recommendations)
- Supplements (dosage, timing, stack management)
- Blood Work (quarterly results, trends)
- Genetics (23andMe data, analysis documents)
- Body Measurements (detailed tracking)
- All data entry forms (nutrition, meditation, self-care)

#### 9.3 Private Health Data Security
**Storage Options**:
- **Encrypted database fields** (AES-256, key stored separately)
- **Separate private database** (not publicly accessible)
- **Local-only files** (never uploaded to GitHub/Vercel)

**Access Control**:
- Multi-factor authentication for private pages
- API endpoints require bearer token with elevated permissions
- Audit log for private data access
- No public API exposure of genetics/blood work

**GitHub/Deployment**:
- Private health data files in `.gitignore`
- Environment variables for encryption keys
- Separate database connection for private data (optional architecture)

---

## Technical Stack

### Current Stack
**Backend**:
- Python 3.9+
- FastAPI (REST API)
- SQLAlchemy (ORM)
- PostgreSQL (Neon)
- OpenAI API (AI evaluation)

**Frontend**:
- HTML/CSS (Material Design framework)
- Vanilla JavaScript
- Responsive design (mobile-first)

**Deployment**:
- Vercel (serverless functions)
- GitHub Actions (daily sync automation)
- Neon PostgreSQL (cloud database)

**Integrations**:
- Garmin Connect API (garminconnect library)
- Hevy API (REST)
- Garmin Workout Manager (garth library)

### Recommended Evolution

#### Frontend Enhancement
**Current**: Vanilla JS → **Recommended**: React + Next.js

**Rationale**:
- Richer interactivity for dashboards (drill-downs, filters, period comparisons)
- Component reusability (widgets, charts)
- State management for complex UI (correlation explorer, comparison engine)
- Server-side rendering for SEO (public profile pages)
- Better developer experience (hot reload, TypeScript)

**Implementation**:
- Keep FastAPI backend as-is
- Next.js frontend consumes FastAPI REST API
- Deploy Next.js to Vercel (same hosting)
- Gradual migration with side-by-side comparison

**Migration Strategy**:
1. Set up Next.js project alongside existing HTML/CSS pages
2. Build new page (e.g., Main Dashboard) in Next.js
3. Deploy new page at alternate route (e.g., `/dashboard-new`)
4. Compare old vs new side-by-side
5. User chooses when to switch (e.g., update nav to point to new page)
6. Repeat for each page: Explore, Goals, Plan Adjustments
7. Deprecate old pages only after new versions are stable and preferred
8. No forced switchover - user controls the transition

#### Mobile App
**Platform**: iOS Native (Swift/SwiftUI)

**Architecture**:
- Standalone iOS app (not PWA)
- REST API client (consumes FastAPI endpoints)
- Local storage for offline mode
- Camera and voice input integration
- Push notifications via APNs (Apple Push Notification service)

#### AI Services
**Current**: OpenAI (GPT-4/GPT-5.2) for plan evaluation

**Additions**:
- **Claude API** (Anthropic) for meal photo analysis (multimodal vision)
- **OpenAI GPT-4 Vision** (alternative for meal analysis)
- Compare performance/cost, choose best

#### Data Visualization
**Charting Library**:
- **Recharts** (React + D3) - for interactive charts in Next.js
- **Chart.js** - for simpler charts if staying with vanilla JS
- **Victory** - React-friendly alternative

**Features Needed**:
- Line charts (trends over time)
- Scatter plots (correlations)
- Heatmaps (activity patterns, sleep consistency)
- Radial/circular progress (Apple-style activity rings)
- Sparklines (mini trend indicators)

---

## Data Model

### Data Preservation
**Existing data to preserve during all migrations**:
- 119+ CompletedActivity records (Garmin + Hevy synced)
- DailyWellness records (sleep, HRV, body battery, etc.)
- ScheduledWorkout entries (24-week training plan)
- CronLog history (sync execution audit trail)
- DailyReview evaluations (AI analysis history)

**Migration strategy**: All frontend changes are additive; backend data models and existing data remain untouched.

### Existing Models (Keep)
**Core Models**:
- `CompletedActivity` - Training sessions (date, type, duration, source)
- `DailyWellness` - Garmin wellness data (sleep, HRV, RHR, body battery, stress, SpO2, respiration)
- `ScheduledWorkout` - 24-week training plan (scheduled_date, workout_type, garmin_workout_id, status)
- `CronLog` - Sync execution tracking (job_type, run_date, status, import counts, errors)
- `DailyReview` - AI evaluations (overall_assessment, modifications_json, lifestyle_insights_json)

**Goal Tracking** (expand usage):
- `Goal` - Structured goals with targets (already exists, underutilized)
- `GoalProgress` - Progress snapshots over time

**Metrics**:
- `ProgressMetric` - Body composition, performance tests (already exists)

### New Models (Add)

#### Nutrition
```python
class MealLog(Base):
    id: int
    athlete_id: int
    logged_at: datetime  # When user submitted the meal
    meal_type: str  # breakfast, lunch, dinner, snack

    # Photo data
    photo_url: str  # Vercel Blob storage URL
    photo_timestamp: datetime  # From EXIF or capture time (when meal was eaten)

    # Nutrition data (from AI analysis)
    calories: float
    protein_g: float
    carbs_g: float
    fats_g: float
    meal_items_json: JSON  # Itemized breakdown from AI

    # AI metadata
    ai_confidence: float  # 0-1, quality of AI extraction
    ai_model_used: str  # "claude-3-opus", "gpt-4-vision", etc.
    ai_analysis_timestamp: datetime  # When AI processed
    user_edited: bool  # True if user modified AI estimates

    notes: str (optional)
```

#### Self-Care Tracking
```python
class SelfCareLog(Base):
    id: int
    athlete_id: int
    logged_at: datetime
    category: str  # recovery, mental_health, hydration, supplements, pt
    activity_type: str  # stretching, meditation, sauna, etc.
    duration_minutes: int (optional)
    quantity: float (optional, for hydration)
    notes: str (optional)

class SupplementLog(Base):
    id: int
    athlete_id: int
    logged_at: datetime
    supplement_name: str
    dosage: str  # "5000 IU", "5g", etc.
    timing: str  # morning, evening, pre-workout, with_meal
    notes: str (optional)
```

#### Private Health Data
```python
class GeneticData(Base):
    id: int
    athlete_id: int
    uploaded_at: datetime
    source: str  # 23andMe, AncestryDNA, etc.
    raw_data_path: str  # encrypted file path
    analysis_documents: JSON  # list of file paths
    key_markers: JSON  # parsed insights (ACTN3, MTHFR, etc.)

class BloodWorkResult(Base):
    id: int
    athlete_id: int
    test_date: date
    lab_name: str
    results_json: JSON  # structured: {marker: {value, unit, range, status}}
    pdf_path: str (optional)
    notes: str (optional)

    # Example JSON structure:
    # {
    #   "testosterone_total": {"value": 650, "unit": "ng/dL", "range": "300-1000", "status": "normal"},
    #   "vitamin_d": {"value": 45, "unit": "ng/mL", "range": "30-100", "status": "normal"},
    #   ...
    # }

class BodyMeasurement(Base):
    id: int
    athlete_id: int
    measured_at: date
    weight_lbs: float
    body_fat_pct: float
    waist_inches: float (optional)
    hip_inches: float (optional)
    chest_inches: float (optional)
    muscle_mass_lbs: float (optional)
    blood_pressure_systolic: int (optional)
    blood_pressure_diastolic: int (optional)
```

#### Performance Tests
```python
class PerformanceTest(Base):
    id: int
    athlete_id: int
    test_date: date
    test_type: str  # vertical_jump, broad_jump, sit_reach, shoulder_flex
    result_value: float
    result_unit: str  # inches, feet
    notes: str (optional)
```

#### Strava Data
```python
class StravaActivity(Base):
    id: int
    athlete_id: int
    strava_activity_id: str  # Strava's unique ID
    activity_date: datetime
    name: str
    type: str  # run, ride, swim
    distance_meters: float
    duration_seconds: int
    is_duplicate: bool  # true if also in Garmin data
    route_polyline: str (optional)
    photos: JSON (optional, list of URLs)
    segments: JSON (optional, segment PRs)
```

---

## UI/UX Principles

### Visualization Style
**Mixed Approach** (Apple + Garmin + Oura):
- **Overview pages**: Simple, clean, minimalist (Apple activity rings, bold numbers, color-coded status)
- **Drill-down pages**: Detailed charts, data-dense (Garmin-style multi-metric views)
- **Progressive disclosure**: Tap cards to expand, slide panels for more details

### Time-Based Design
**Core Principle**: Most visualizations include time axis and trends

**Examples**:
- Not just "HRV: 65ms" → "HRV: 65ms (↑5% vs 7-day avg, ↑12% vs 30-day avg)"
- Not just "Body Fat: 15.2%" → Line chart showing 6-month trend toward 14% goal
- Not just "Workouts: 4 this week" → Bar chart showing weekly volume over last 12 weeks

### Goal Comparison Integration
**Every metric should show**:
- Current value
- Target/optimal value
- Gap analysis (distance to goal)
- Trend toward goal (on track, behind, ahead)

### Activity Rings (Apple Inspiration)
**Adapt for fitness dashboard**:
- **Outer ring**: Weekly training volume (3-5 hour target)
- **Middle ring**: Goal progress (composite score of 5 goals)
- **Inner ring**: Daily recovery/readiness (based on HRV, sleep, RHR)

**Display**: On Main Dashboard as hero widget, animated fills

### Mobile-First Responsive Design
**Breakpoints**:
- Mobile: 320-767px (single column, stacked widgets)
- Tablet: 768-1023px (2-column grid)
- Desktop: 1024px+ (3-4 column grid)

**Touch Targets**: Minimum 44x44px for mobile tap zones

### Navigation Structure (Post-Phase A)
**Primary Navigation**:
- **Main Dashboard** (`/dashboard`) - Current, actionable overview
- **Explore** (`/explore`) - Long-term trends, correlations, analytics
- **Goals** (`/goals`) - Renamed from Metrics; goal management and progress
- **Plan Adjustments** (`/plan-adjustments`) - Renamed from Reviews; AI recommendations
- **Upcoming** (`/upcoming`) - Keep existing; scheduled workouts calendar

**Private Pages** (login required):
- **Supplements** (`/supplements`) - Dosage, timing, stack management
- **Health Data** (`/health`) - Blood work, genetics, body measurements

**Removed**:
- Daily Report (`/api/reports/daily`) - Replaced by Explore Dashboard
- Weekly Report (`/api/reports/weekly`) - Replaced by Explore Dashboard

---

## Development Phases

### Phase A: Enhanced Dashboards (Priority 1)
**Goal**: Best-in-class visualization and navigation

**Deliverables**:
1. **Main Dashboard Redesign**
   - Widget-based layout (6 core widgets)
   - Real-time data freshness indicators
   - Mobile-responsive grid
   - Activity rings widget

2. **Explore Dashboard (New)**
   - Time range selector (7/30/90 days, custom)
   - Period comparison views
   - Correlation explorer
   - Secondary metrics deep-dives

3. **Goals Page (Renamed from Metrics)**
   - Editable goal management
   - Progress visualization (trend lines, goal runway)
   - Performance test logging (quarterly tests: vertical jump, broad jump, flexibility)
   - Quarterly test reminders (automated notification when tests are due)
   - Historical comparison (show progress vs previous quarters)

4. **Plan Adjustments (Renamed from Reviews)**
   - Enhanced UI for modification review
   - Batch approve/reject
   - Modification history log

**Technical Work**:
- Migrate to React + Next.js (or enhance current stack with better charting)
- Implement charting library (Recharts or Chart.js)
- Design component library (widgets, cards, charts)
- Responsive layout system

**Success Metrics**:
- All 4 pages live and functional
- Mobile-responsive (tested on iPhone)
- Page load time <2 seconds
- User feedback: "Easier to understand my data"

### Phase D: New Data Integrations (Priority 2)
**Goal**: Expand data sources for holistic view

**Deliverables**:
1. **Strava Integration**
   - One-time historical import (all available data)
   - Ongoing sync (segments, routes, photos only)
   - Deduplication with Garmin data

2. **Nutrition Tracking Foundation**
   - Backend API endpoints for meal logging
   - AI integration (Claude or GPT-4 Vision) for photo analysis
   - Standardized AI output schema for consistent data storage

3. **Self-Care Logging**
   - Backend API endpoints (supplements, meditation, recovery, hydration, PT)
   - Data models (SelfCareLog, SupplementLog)

**Note on Supplements Feature Split**:
- **Phase D**: Backend API endpoints + data models
- **Phase E**: Web form UI for supplement entry (authenticated `/supplements` page)
- **Phase B**: Mobile voice logging for supplements

**Technical Work**:
- Strava API client (OAuth 2.0 authentication)
- Historical data import script (batch processing)
- AI vision API integration (Claude or OpenAI)
- Database migrations for new models

**Success Metrics**:
- Strava historical data imported (100% of available activities)
- Nutrition AI extraction accuracy >80%
- All self-care categories loggable via API

### Phase E: Private Health Layer (Priority 3)
**Goal**: Secure storage and AI-contextualized recommendations

**Deliverables**:
1. **Genetics Data Storage**
   - Upload 23andMe raw data file
   - Store third-party analysis documents
   - Encrypt sensitive data

2. **Blood Work Tracking**
   - Quarterly test result entry
   - Structured marker tracking (testosterone, vitamin D, cholesterol, etc.)
   - Trend visualization over time

3. **Supplement Management**
   - Current stack entry (name, dosage, timing)
   - Daily supplement logging
   - Integration with AI evaluator

4. **Body Measurements**
   - Manual entry forms (weight, body fat, waist, etc.)
   - Historical tracking and trends

5. **Authentication & Privacy**
   - Login system (email/password, JWT)
   - Private page access control
   - Encrypted database fields for sensitive data

**Technical Work**:
- User authentication (JWT tokens)
- Database encryption (AES-256 for sensitive fields)
- Private page middleware (auth checks)
- File upload and secure storage (S3 or Vercel Blob)

**Success Metrics**:
- All private health data stored securely
- Login system functional with MFA option
- Private pages inaccessible without authentication
- AI evaluator can reference genetics/blood work in recommendations

### Phase C: Comparison Engine and Analytics (Priority 4)
**Goal**: Data-driven insights and correlations

**Deliverables**:
1. **Planned vs Actual Views**
   - Weekly adherence dashboard
   - Volume tracking (planned hours vs actual)
   - Miss pattern detection

2. **Goal vs Current Tracking**
   - Real-time progress toward 5 goals
   - Trend indicators (↑↓→)
   - Estimated achievement dates

3. **Period Comparisons**
   - Week/week, month/month, quarter/quarter
   - Custom date range comparisons

4. **Optimal vs Actual**
   - Define optimal ranges (sleep, HRV, training volume)
   - Gap analysis and consistency scoring

5. **Correlation Detection**
   - Auto-detect relationships (sleep → performance, HRV → readiness)
   - Statistical significance (correlation coefficient, p-value)
   - Simple statement format ("💡 Pattern Detected...")

6. **Advanced Analytics**
   - Performance driver analysis (what leads to best workouts)
   - Predictive analytics (goal achievement timelines)
   - Recovery pattern analysis (time to baseline after hard sessions)
   - Optimization insights (what sleep duration gives best HRV)
   - Interference pattern detection (strength training → swim performance)

**Technical Work**:
- Analytics engine (Python pandas, numpy, scipy for stats)
- Correlation algorithms (Pearson, Spearman)
- Prediction models (linear regression, time series)
- Visualization components (scatter plots, heatmaps)

**Success Metrics**:
- All 5 comparison types functional
- At least 3 significant correlations detected (r > 0.5, p < 0.05)
- Predictive models for 400yd swim goal (with confidence intervals)
- User feedback: "This helps me understand what works"

### Phase B: Mobile Application (Priority 5)
**Goal**: Seamless on-the-go logging

**Deliverables**:
1. **iOS App (Native)**
   - Meal photo logging with AI analysis
   - Meditation logging (duration, type, notes)
   - Voice input for quick logging
   - Self-care quick logging (buttons for common activities)

2. **Mobile Notifications**
   - Daily prompts (meal logging, workout completion, supplements, bedtime)
   - User-configurable settings (enable/disable by category)

3. **Offline Mode**
   - Local storage for offline logging
   - Background sync when online

**Technical Work**:
- iOS app development (Swift/SwiftUI)
- Camera integration (photo capture, gallery picker)
- Voice input (Speech Recognition framework)
- Push notifications (APNs)
- REST API client (consume FastAPI endpoints)
- Offline sync logic (local SQLite, background tasks)

**Success Metrics**:
- App submitted to TestFlight (internal testing)
- Meal logging flow <10 seconds (photo → AI analysis → save)
- Voice logging functional ("I took my morning supplements" → logged)
- Push notifications delivered reliably
- User feedback: "This is way easier than web forms"

---

## Technical Considerations

### Scalability
**Current Load**: Single user (Ryan)
**Future Load**: 10-100 users (individual athletes)

**Architecture**:
- Vercel serverless functions auto-scale (no changes needed)
- PostgreSQL (Neon) can handle 100 concurrent users with free tier
- Plan for database connection pooling if >50 users
- Consider Redis cache for frequently accessed data (dashboard queries)

### Performance
**Target Metrics**:
- Dashboard page load: <2 seconds
- Explore page (with charts): <3 seconds
- API response time: <500ms (p95)
- Mobile app sync: <5 seconds

**Optimizations**:
- Database indexes on athlete_id, date fields (already exists)
- Query result caching (Redis or in-memory LRU cache)
- Lazy loading for Explore Dashboard charts (render on scroll)
- Image optimization for meal photos (resize, compress, WebP format)

### Data Privacy & Compliance
**GDPR Considerations** (if expanding to EU users):
- Right to access: Export all user data (JSON or CSV)
- Right to deletion: Cascade delete all user data
- Data portability: Standard export format

**HIPAA Considerations** (NOT applicable initially):
- Blood work data may be considered PHI (Protected Health Information)
- If expanding to medical use cases, consider HIPAA compliance

**Current Approach**:
- Clear privacy policy (what data is collected, how it's used)
- User consent for AI analysis of health data
- Encrypted storage of sensitive data
- No sharing of data with third parties (except API providers: OpenAI, Claude)

### Image Storage (Meal Photos)
**Options**:
- **Vercel Blob**: Simple, integrated, ~$0.15/GB/month
- **S3/R2**: More control, ~$0.023/GB/month (Cloudflare R2 has free egress)
- **Local/Self-hosted**: Not recommended for mobile sync

**Recommendation**: Start with Vercel Blob for simplicity

**Estimated storage**: ~1MB/meal × 3 meals × 30 days = ~90MB/month/user
**Cost**: <$0.02/month per user with Vercel Blob

### Nutrition AI - Standardized Output Schema
**Purpose**: Ensure consistent data structure from AI photo analysis for reliable storage and analytics

**Required Output Fields**:
```json
{
  "meal_items": [
    {
      "name": "Grilled chicken breast",
      "portion_size": "6 oz",
      "calories": 280,
      "protein_g": 52,
      "carbs_g": 0,
      "fats_g": 6
    }
  ],
  "meal_totals": {
    "calories": 650,
    "protein_g": 58,
    "carbs_g": 45,
    "fats_g": 22
  },
  "confidence_score": 0.85,
  "meal_type_suggestion": "lunch",
  "notes": "Appears to be meal prep container with chicken, rice, broccoli"
}
```

**Photo Metadata** (stored with each meal):
- `photo_timestamp`: From image EXIF data or upload time
- `photo_url`: Vercel Blob storage URL
- `ai_analysis_timestamp`: When AI processed the image
- `ai_model_used`: Which model analyzed (e.g., "claude-3-opus", "gpt-4-vision")

### AI Costs
**Current**: OpenAI GPT-4/GPT-5.2 for nightly evaluations (~$0.10/day)

**Additions**:
- **Meal photo analysis**: Claude or GPT-4 Vision (~$0.02-0.05 per image)
- **Estimated monthly cost** (1 user, 3 meals/day): ~$2-5/month for nutrition AI
- **Correlation analysis**: Local computation (no API cost)

**Cost Optimization**:
- Cache AI responses (same meal photo → same result)
- Batch API requests where possible
- Use smaller models for simple tasks (gpt-4o-mini for text extraction)

### Security
**Authentication**:
- JWT tokens (refresh + access token pattern)
- Password hashing (bcrypt with salt)
- Rate limiting (prevent brute force)
- Optional MFA (TOTP via authenticator app)

**API Security**:
- CORS restrictions (only allow frontend domain)
- Input validation (Pydantic schemas)
- SQL injection prevention (SQLAlchemy ORM, parameterized queries)
- XSS prevention (sanitize user inputs, CSP headers)

**Private Health Data**:
- Encrypt at rest (AES-256 for genetics, blood work)
- Encrypt in transit (HTTPS for all API calls)
- Access logging (audit trail for sensitive data access)
- Separation of concerns (private data in separate DB or schema)

### Mobile App Distribution
**TestFlight** (iOS internal testing):
- Invite-only beta testing
- No App Store approval needed
- 10,000 external testers allowed

**App Store** (public release, future):
- Apple review process (~1-2 weeks)
- Privacy policy required
- Health data permissions (HealthKit integration if pulling Apple Health)

---

## Success Metrics

### User Engagement
**Current** (single user):
- Dashboard views per day: Target >2
- Weekly adherence to training plan: Target >80%
- Data entry consistency: Target >80% of days logged

**Future** (multi-user):
- Daily active users (DAU): Target >60% of total users
- Weekly active users (WAU): Target >90%
- Retention (30-day): Target >70%

### Data Quality
- Garmin sync success rate: Target >95%
- Hevy sync success rate: Target >95%
- Strava sync success rate: Target >90%
- Nutrition AI extraction accuracy: Target >80%
- Meal logging consistency: Target >80% of days

### Goal Progress
- Body fat: Maintain 14% ± 1%
- VO2 Max: Increase trend (no specific target yet)
- 400yd freestyle: Achieve target time by Week 24
- Explosive/Flexible: Maintain or improve quarterly test scores
- Training volume: 3-5 hours per week, >80% adherence

### System Performance
- Dashboard page load: <2 seconds (p95)
- API response time: <500ms (p95)
- Mobile app sync: <5 seconds
- AI evaluation completion: <30 seconds
- Uptime: >99.5%

### User Satisfaction (Qualitative)
- "I understand my data better"
- "This helps me make better training decisions"
- "I trust the AI recommendations"
- "Logging is easy and fast"

---

## Future Expansion

### Beyond Phase B (Post-MVP)
**Advanced AI Features**:
- Voice-based AI coach ("Ask me about your training")
- Automated plan adjustments (no approval needed for minor changes)
- Predictive injury risk (based on volume, recovery, patterns)

**Social Features** (Optional):
- Share workouts publicly (Strava-style)
- Compare with anonymized athlete cohorts ("You're in top 10% for your age group")
- Community challenges (e.g., "100-day workout streak")

**Integrations**:
- Oura Ring (superior HRV/sleep tracking)
- Whoop (recovery and strain tracking)
- MyFitnessPal (nutrition sync)
- Zwift (indoor cycling data)
- Peloton (indoor workouts)

**Wearable Expansion**:
- Apple Watch app (quick workout logging, real-time HRV)
- Garmin Connect IQ app (custom data fields)

**Advanced Analytics**:
- Machine learning models (predict optimal training load)
- Anomaly detection (flag unusual patterns automatically)
- Natural language queries ("Show me weeks where I slept >8 hours and ran well")

**Coach Integration** (Future business model):
- Multi-user: Coach accounts with read access to athlete data
- Communication tools (messaging, plan comments)
- Coach-defined goals and plan templates

---

## Open Questions & Decisions Needed

### Resolved
1. **Frontend Framework**: ✅ Migrate to React + Next.js in Phase A
   - Side-by-side deployment with user-controlled switchover

2. **Strava Historical Import**: ✅ Pull all available data

3. **Post-Week 24 Strategy**: ✅ Start new 24-week cycle with updated goals

4. **Apple Fitness**: ✅ Deferred to post-MVP (not in current phases)

5. **Meal Photo Storage**: ✅ Vercel Blob for simplicity

6. **Workout Quality Scoring**: ✅ Excluded - focus on completion/adherence metrics

### Still Open
1. **AI Provider for Nutrition**: Claude vs GPT-4 Vision?
   - **Recommendation**: Test both, compare accuracy and cost, choose best

2. **Private Health Data Architecture**: Encrypted DB fields vs separate private DB?
   - **Recommendation**: Start with encrypted fields, migrate to separate DB if compliance required

3. **Mobile App Distribution**: TestFlight only or App Store?
   - **Recommendation**: Start with TestFlight, launch App Store if multi-user expansion happens

4. **Authentication Provider**: Build custom or use Auth0/Firebase?
   - **Recommendation**: Build custom (simple JWT) to start, migrate to Auth0 if scaling to 100+ users

5. **Notification Strategy**: Push notifications via APNs or web push?
   - **Recommendation**: APNs for iOS app (Phase B), web push later if PWA desired

6. **400yd Freestyle Target Time**: TBD after Week 2 baseline test

---

## Appendix

### Technical Documentation
Detailed implementation patterns, API endpoints, and code conventions are maintained in:
- **`CLAUDE.md`** - Project-specific development instructions, sync architecture, Garmin workout formats
- **`docs/ARCHITECTURE.md`** - System architecture reference
- **`docs/TECHNICAL_SPEC.md`** - Original technical specification

This PRD focuses on **what** to build; the above documents cover **how** to build it.

### Glossary
- **HRV**: Heart Rate Variability (measure of autonomic nervous system balance)
- **RHR**: Resting Heart Rate
- **VO2 Max**: Maximum oxygen uptake (aerobic fitness measure)
- **REM**: Rapid Eye Movement (sleep stage associated with cognitive function)
- **CSS**: Critical Swim Speed (lactate threshold pace)
- **RPE**: Rate of Perceived Exertion (1-10 scale)
- **PWA**: Progressive Web App
- **APNs**: Apple Push Notification service
- **JWT**: JSON Web Token (authentication method)

### References
- [Bryan Johnson Blueprint Sleep Protocol](https://blueprint.bryanjohnson.com/blogs/news/how-i-fixed-my-terrible-sleep)
- [Validation of HRV/RHR in Consumer Wearables (2025)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12367097/)
- [Pre-sleep HRV Predicts Sleep Quality (2025)](https://www.frontiersin.org/journals/physiology/articles/10.3389/fphys.2025.1627287/full)
- Garmin API Documentation (Connect IQ, Workout Service)
- Strava API v3 Documentation
- Apple HealthKit Documentation

### Contact
- **Product Owner**: Ryan Willging (ryanwillging@gmail.com)
- **Development**: Claude Code (AI-assisted development)
- **Repository**: https://github.com/ryanwillging/training (assumed)

---

**Document Version**: 1.1
**Last Updated**: January 24, 2026
**Status**: Ready for Implementation

### Changelog
**v1.1** (January 24, 2026):
- Added 400yd swim target time as TBD (pending Week 2 baseline)
- Standardized terminology: "Plan Evaluator" for AI system
- Added post-Week 24 strategy (start new cycle with updated goals)
- Added quarterly performance test scheduling to Goals page
- Moved Apple Fitness to Future Expansion (not in current phases)
- Added meal photo storage strategy (Vercel Blob)
- Added standardized AI output schema for nutrition
- Added AI access implementation for private health data (context injection)
- Added data preservation note for migrations
- Added navigation structure (post-Phase A)
- Clarified supplement feature phasing across D/E/B
- Added deep sleep to priority sleep metrics
- Updated nutrition error handling (photo-only, no manual entry)
- Added photo timestamp fields to MealLog model
- Added reference to CLAUDE.md for technical documentation
- Clarified voice logging scope (self-care only initially)
- Updated frontend migration strategy (side-by-side comparison, user-controlled switchover)
- Simplified Performance Drivers analytics (exclude subjective quality scoring)
- Reorganized Open Questions (resolved vs still open)

**v1.0** (January 24, 2026):
- Initial PRD created
