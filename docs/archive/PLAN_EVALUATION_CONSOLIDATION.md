# Plan: Consolidate Training Evaluation System

## Current State

```
┌─────────────────────────────────────────────────────────────────┐
│                         CRON JOB                                │
├─────────────────────────────────────────────────────────────────┤
│ 1. Sync Garmin activities                                       │
│ 2. Sync Garmin wellness                                         │
│ 3. Sync Hevy workouts                                           │
│ 4. Run WorkoutRecommendationEngine (goal_analyzer.py) ← REMOVE  │
│ 5. Run TrainingPlanManager.run_nightly_evaluation() ← KEEP      │
│    └── Calls ChatGPTEvaluator                                   │
│    └── Stores to DailyReview                                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      /reviews PAGE                              │
├─────────────────────────────────────────────────────────────────┤
│ - Manual trigger: POST /api/plan/evaluate-with-context          │
│ - Same path: TrainingPlanManager.run_nightly_evaluation()       │
│ - Already unified ✓                                             │
└─────────────────────────────────────────────────────────────────┘
```

## Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              SINGLE EVALUATION PIPELINE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  INPUTS (gathered by plan_manager.py):                          │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐       │
│  │ Goal Progress  │ │ Recent Workouts│ │ Wellness Data  │       │
│  │ - targets      │ │ - last 14 days │ │ - sleep score  │       │
│  │ - current      │ │ - types        │ │ - HRV          │       │
│  │ - trend        │ │ - completion   │ │ - readiness    │       │
│  └────────────────┘ └────────────────┘ │ - body battery │       │
│                                        │ - stress       │       │
│  ┌────────────────┐ ┌────────────────┐ └────────────────┘       │
│  │ Scheduled      │ │ User Context   │                          │
│  │ Workouts       │ │ (optional)     │                          │
│  │ - next 14 days │ │ - notes        │                          │
│  │ - types        │ │ - constraints  │                          │
│  └────────────────┘ └────────────────┘                          │
│                                                                 │
│  PROCESSOR (chatgpt_evaluator.py):                              │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    GPT-5.2 REASONING                        ││
│  │  - Analyze all inputs                                       ││
│  │  - Identify issues & opportunities                          ││
│  │  - Propose specific modifications (next 7 days only)        ││
│  │  - Generate lifestyle insights                              ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  OUTPUTS (stored in DailyReview):                               │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐       │
│  │ Assessment     │ │ Modifications  │ │ Insights       │       │
│  │ - on_track     │ │ - skip workout │ │ - health       │       │
│  │ - needs_adjust │ │ - reduce volume│ │ - recovery     │       │
│  │ - significant  │ │ - swap type    │ │ - nutrition    │       │
│  │                │ │ - reschedule   │ │ - sleep        │       │
│  └────────────────┘ └────────────────┘ └────────────────┘       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Changes Required

### 1. Update ChatGPT Prompt (chatgpt_evaluator.py)

**Current prompt asks for:**
- Overall assessment
- Progress summary
- Modifications (type, week, day, description, reason, priority)
- Next week focus
- Warnings

**New prompt will add:**
- **Lifestyle insights** section:
  - Health observations (based on wellness data)
  - Recovery recommendations (based on readiness, HRV, sleep)
  - Nutrition suggestions (based on goals, training load)
  - Sleep optimization (based on sleep scores, body battery)
- **Modification scope**: Emphasize changes to next 7 days only, keep future intact
- **Conservative approach**: Only suggest changes when clearly needed

### 2. Update Response Schema

```json
{
  "overall_assessment": "on_track|needs_adjustment|significant_changes_needed",
  "progress_summary": "...",
  "modifications": [...],  // ONLY for next 7 days
  "next_week_focus": "...",
  "warnings": [...],
  "confidence_score": 0.0-1.0,

  // NEW: Lifestyle insights
  "insights": {
    "health": "Observations about overall health metrics...",
    "recovery": "Recovery status and recommendations...",
    "nutrition": "Nutrition considerations based on goals/training...",
    "sleep": "Sleep quality observations and suggestions..."
  }
}
```

### 3. Update DailyReview Model (database/models.py)

Add column for structured insights:
```python
insights_json = Column(Text)  # JSON blob for health/recovery/nutrition/sleep insights
```

### 4. Remove goal_analyzer.py from Cron (api/cron/sync.py)

- Remove import of `GoalAnalyzer`, `WorkoutRecommendationEngine`
- Remove lines 133-144 (goal analysis step)
- Keep `goal_analyzer.py` file for potential future use or delete

### 5. Update /reviews UI (api/routes/plan.py or api/index.py)

Display insights alongside modifications:
- Health insights card
- Recovery recommendations card
- Nutrition tips card
- Sleep observations card

## Implementation Order

1. **Update DailyReview model** - Add `insights_json` column
2. **Update chatgpt_evaluator.py** - Enhance prompt and response parsing
3. **Update plan_manager.py** - Store insights in DailyReview
4. **Update cron/sync.py** - Remove redundant goal_analyzer call
5. **Update /reviews UI** - Display insights
6. **Run migration** - Add column to production database
7. **Test end-to-end** - Manual evaluation + cron

## Design Decisions (Confirmed)

1. **Modification window**: Next 7 days only
   - Plan is anchored to start date: **January 20, 2025**
   - Week numbers are fixed (Week 2/Test Week = Jan 26, etc.)
   - Never recreate the 24-week plan, only adjust near-term workouts

2. **Module architecture**: Keep specialized modules, combine in analysis
   - `goal_analyzer.py` - Goal progress tracking (trends, percentages)
   - `chatgpt_evaluator.py` - AI reasoning and insights
   - `plan_manager.py` - Orchestrator that combines both

3. **Insight detail level**: Detailed with actionable steps
   - Include specific actions to take
   - Format for potential automation (Google Calendar, reminders)
   - Example: "Sleep score dropped 15%. Actions: Set 10pm bedtime reminder, limit caffeine after 2pm, reduce screen time 1hr before bed"

4. **Reviews UI**: Full history with drill-down
   - List all past evaluations as clickable rows
   - Differentiate: "nightly" vs "on-demand" evaluation type
   - Show acceptance status: accepted, rejected, pending, partial
   - Click to expand full details (insights, modifications, reasoning)

## Files to Modify

| File | Change |
|------|--------|
| `database/models.py` | Add `insights_json` column to DailyReview |
| `analyst/chatgpt_evaluator.py` | Update prompt, add insights to response schema |
| `analyst/plan_manager.py` | Store insights in `_store_daily_review()` |
| `api/cron/sync.py` | Remove goal_analyzer usage |
| `api/index.py` or `api/routes/plan.py` | Display insights on /reviews page |
| `scripts/add_insights_column.py` | Migration script for production |
