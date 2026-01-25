# Garmin API Reference

Detailed documentation for Garmin Connect workout creation and calendar sync.

## Authentication

Uses `garth` library for OAuth token management (NOT `garminconnect` for workout creation):

```python
import os
import garth
from dotenv import load_dotenv
load_dotenv('.env.production')

token_dir = os.path.expanduser("~/.garth")
try:
    garth.resume(token_dir)
except:
    garth.login(os.environ.get("GARMIN_EMAIL"), os.environ.get("GARMIN_PASSWORD"))
    garth.save(token_dir)
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/workout-service/workouts` | GET | List all workouts |
| `/workout-service/workout/{id}` | GET | Get workout details |
| `/workout-service/workout` | POST | Create workout |
| `/workout-service/workout/{id}` | PUT | Update workout |
| `/workout-service/workout/{id}` | DELETE | Delete workout |
| `/workout-service/schedule/{workoutId}` | POST | Schedule on calendar |
| `/calendar-service/year/{year}/month/{month}` | GET | View calendar (month 0-indexed) |

## Sport Types

| Sport | sportTypeId | sportTypeKey |
|-------|-------------|--------------|
| Running | 1 | running |
| Swimming | 4 | lap_swimming |
| Strength | 5 | strength_training |

## Swim Settings

- Pool size: 25 yards (unitId: 230, unitKey: "yard")
- Stroke type: freestyle (strokeTypeId: 6)

## Workout Payload Structure

```python
{
    "sportType": {"sportTypeId": 5, "sportTypeKey": "strength_training"},
    "workoutName": "Lift A - Lower Body",
    "description": "Optional description",
    "workoutSegments": [{
        "segmentOrder": 1,
        "sportType": {"sportTypeId": 5, "sportTypeKey": "strength_training"},
        "workoutSteps": [
            # ExecutableStepDTO or RepeatGroupDTO items
        ]
    }]
}
```

## Step Types

### ExecutableStepDTO
Single exercise step (warmup, interval, cooldown, rest):
```python
{
    "type": "ExecutableStepDTO",
    "stepOrder": 1,
    "stepType": {"stepTypeId": 3, "stepTypeKey": "interval"},
    "description": "5 min warmup",
    "endCondition": {"conditionTypeId": 2, "conditionTypeKey": "time"},
    "endConditionValue": 300.0  # seconds
}
```

### RepeatGroupDTO
Repeating group for sets (strength) or intervals (strides):
```python
{
    "type": "RepeatGroupDTO",
    "stepOrder": 1,
    "numberOfIterations": 3,  # Number of sets/reps
    "smartRepeat": False,
    "childSteps": [
        # ExecutableStepDTO items
    ],
    "repeatGroupDescription": {"value": "3 sets of 8 reps"}
}
```

## End Condition Types

| conditionTypeId | conditionTypeKey | Use Case |
|-----------------|------------------|----------|
| 1 | lap.button | Manual lap/stop |
| 2 | time | Duration-based (seconds) |
| 3 | distance | Distance-based (meters) |
| 10 | reps | Rep-based (strength) |

## Strength Workout Example (RepeatGroupDTO)

```python
# Squat 3×8 reps
{
    "type": "RepeatGroupDTO",
    "stepOrder": 1,
    "numberOfIterations": 3,
    "smartRepeat": False,
    "childSteps": [{
        "type": "ExecutableStepDTO",
        "stepOrder": 1,
        "stepType": {"stepTypeId": 3, "stepTypeKey": "interval"},
        "exerciseCategory": {"exerciseCategoryId": 119, "exerciseName": "SQUAT"},
        "endCondition": {"conditionTypeId": 10, "conditionTypeKey": "reps"},
        "endConditionValue": 8.0
    }],
    "repeatGroupDescription": {"value": "3 sets of 8 reps"}
}
```

**Key Points**:
- `numberOfIterations` = number of sets
- Child step's `endConditionValue` = reps per set
- Use `conditionTypeId: 10` for reps (NOT lap.button)

## VO2 Strides Example (RepeatGroupDTO)

```python
# 4×20s strides with 45s recovery
{
    "type": "RepeatGroupDTO",
    "stepOrder": 3,
    "numberOfIterations": 4,
    "workoutSteps": [
        {
            "type": "ExecutableStepDTO",
            "stepOrder": 1,
            "stepType": {"stepTypeId": 3, "stepTypeKey": "interval"},
            "description": "Stride (20s)",
            "endCondition": {"conditionTypeId": 2, "conditionTypeKey": "time"},
            "endConditionValue": 20.0
        },
        {
            "type": "ExecutableStepDTO",
            "stepOrder": 2,
            "stepType": {"stepTypeId": 4, "stepTypeKey": "recovery"},
            "description": "Walk-back recovery",
            "endCondition": {"conditionTypeId": 2, "conditionTypeKey": "time"},
            "endConditionValue": 45.0
        }
    ]
}
```

## Parsing Helpers (`workout_manager.py`)

| Function | Input Example | Returns |
|----------|---------------|---------|
| `parse_sets_string()` | `"4×50"`, `"3×8-10"` | `(reps, value, unit)` |
| `parse_sets_and_reps()` | `"3×8-10"` | `(num_sets, reps_per_set)` |
| `parse_strides_string()` | `"4×20s"` | `(num_strides, duration_secs)` |
| `parse_rest_string()` | `"20s"`, `"2 min"` | `seconds` |
| `parse_duration_string()` | `"5 min"`, `"30s"` | `seconds` |
| `parse_distance_string()` | `"300 yards"` | `yards` |

## Workout Details Field Convention

In `_get_vo2_workout_details()`, `_get_lift_workout_details()`, etc.:

| Field | Creates | conditionTypeId | Use For |
|-------|---------|-----------------|---------|
| `duration` | ExecutableStepDTO | 2 (time) | Warmup, cooldown |
| `sets` | RepeatGroupDTO | 10 (reps) | Strength ("3×8-10") |
| `strides` | RepeatGroupDTO | 2 (time) | Time intervals ("4×20s") |
| `distance` | ExecutableStepDTO | 3 (distance) | Swim/run distances |

**Priority**: `strides` > `duration` > `sets`

## Format Verification

The system auto-scans and fixes outdated formats after every sync:

**Checks performed** (`verify_workout_format()`):
1. Strength: Uses `conditionTypeId: 10` (reps), not `1` (lap.button)
2. Strength: Sets are RepeatGroupDTO, not flat ExecutableStepDTO
3. VO2: Warmup/cooldown use `conditionTypeId: 2` (time)
4. VO2: Strides are RepeatGroupDTO with time-based children

**Manual trigger**: `POST /api/plan/scan-formats?days_ahead=14`

## Common Operations

### Delete workout from calendar
```python
workout_id = 1442151086  # From ScheduledWorkout.garmin_workout_id
garth.connectapi(f"/workout-service/workout/{workout_id}", method="DELETE")
```

### View calendar for a month
```python
# month is 0-indexed (0=Jan, 11=Dec)
response = garth.connectapi("/calendar-service/year/2026/month/0")
for item in response.get("calendarItems", []):
    if item.get("itemType") == "workout":
        print(f"{item['date']}: {item['title']} (id: {item['workoutId']})")
```

## Garmin API Response Quirks

Some endpoints return lists instead of dicts:
- `training_readiness` - List (use `[0]` for most recent)
- `steps` - List of intervals (sum all `steps` values)
- `max_metrics` - List (may be empty)
- `body_battery` - List with `bodyBatteryValuesArray` inside

Handled in `wellness_importer.py`.
