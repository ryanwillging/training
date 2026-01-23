"""
Garmin Connect workout manager.
Creates and schedules workouts on Garmin Connect calendar.

API format discovered by inspecting actual Garmin workouts - the official
garminconnect library doesn't fully support workout creation.
"""

import json
import os
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Try to import garth for direct API access
try:
    import garth
    GARTH_AVAILABLE = True
except ImportError:
    GARTH_AVAILABLE = False
    garth = None

from integrations.garmin.client import GarminClient


class WorkoutStepType(Enum):
    """Garmin workout step types."""
    WARMUP = "warmup"
    COOLDOWN = "cooldown"
    INTERVAL = "interval"
    RECOVERY = "recovery"
    REST = "rest"
    REPEAT = "repeat"
    OTHER = "other"


class WorkoutSportType(Enum):
    """Garmin sport types for workouts."""
    RUNNING = "running"
    CYCLING = "cycling"
    SWIMMING = "swimming"
    STRENGTH = "strength_training"
    CARDIO = "cardio_training"
    OTHER = "other"


@dataclass
class WorkoutStep:
    """A single step in a Garmin workout."""
    type: WorkoutStepType
    duration_type: str  # "time", "distance", "lap.button", "open"
    duration_value: Optional[float] = None  # seconds or yards/meters
    target_type: Optional[str] = None  # "heart_rate", "pace", "power", "cadence", "open"
    target_value_low: Optional[float] = None
    target_value_high: Optional[float] = None
    description: Optional[str] = None
    repeat_count: Optional[int] = None  # For repeat steps
    child_steps: Optional[List['WorkoutStep']] = None


@dataclass
class GarminWorkout:
    """A Garmin workout definition."""
    name: str
    sport_type: WorkoutSportType
    description: Optional[str] = None
    steps: List[WorkoutStep] = None
    estimated_duration_minutes: Optional[int] = None

    def __post_init__(self):
        if self.steps is None:
            self.steps = []


class GarminWorkoutManager:
    """
    Manages workout creation and scheduling on Garmin Connect.

    Uses garth library for direct API access since garminconnect doesn't
    fully support workout creation/scheduling.
    """

    # Correct Garmin sport type mappings (discovered from actual API responses)
    SPORT_TYPE_MAP = {
        WorkoutSportType.RUNNING: {"sportTypeId": 1, "sportTypeKey": "running", "displayOrder": 1},
        WorkoutSportType.CYCLING: {"sportTypeId": 2, "sportTypeKey": "cycling", "displayOrder": 2},
        WorkoutSportType.SWIMMING: {"sportTypeId": 4, "sportTypeKey": "swimming", "displayOrder": 3},
        WorkoutSportType.STRENGTH: {"sportTypeId": 5, "sportTypeKey": "strength_training", "displayOrder": 5},
        WorkoutSportType.CARDIO: {"sportTypeId": 1, "sportTypeKey": "running", "displayOrder": 1},  # VO2 uses running
        WorkoutSportType.OTHER: {"sportTypeId": 0, "sportTypeKey": "other", "displayOrder": 0},
    }

    # Step type mappings
    STEP_TYPE_MAP = {
        WorkoutStepType.WARMUP: {"stepTypeId": 1, "stepTypeKey": "warmup", "displayOrder": 1},
        WorkoutStepType.COOLDOWN: {"stepTypeId": 2, "stepTypeKey": "cooldown", "displayOrder": 2},
        WorkoutStepType.INTERVAL: {"stepTypeId": 3, "stepTypeKey": "interval", "displayOrder": 3},
        WorkoutStepType.RECOVERY: {"stepTypeId": 4, "stepTypeKey": "recovery", "displayOrder": 4},
        WorkoutStepType.REST: {"stepTypeId": 5, "stepTypeKey": "rest", "displayOrder": 5},
        WorkoutStepType.REPEAT: {"stepTypeId": 6, "stepTypeKey": "repeat", "displayOrder": 6},
        WorkoutStepType.OTHER: {"stepTypeId": 7, "stepTypeKey": "other", "displayOrder": 7},
    }

    # End condition mappings
    CONDITION_TYPE_MAP = {
        "time": {"conditionTypeId": 2, "conditionTypeKey": "time", "displayOrder": 2, "displayable": True},
        "distance": {"conditionTypeId": 3, "conditionTypeKey": "distance", "displayOrder": 3, "displayable": True},
        "lap.button": {"conditionTypeId": 1, "conditionTypeKey": "lap.button", "displayOrder": 1, "displayable": True},
        "lap_button": {"conditionTypeId": 1, "conditionTypeKey": "lap.button", "displayOrder": 1, "displayable": True},
        "open": {"conditionTypeId": 1, "conditionTypeKey": "lap.button", "displayOrder": 1, "displayable": True},
    }

    # Pool length unit for swimming (25 yards)
    POOL_LENGTH_UNIT = {"unitId": 230, "unitKey": "yard", "factor": 91.44}

    def __init__(self, client: Optional[GarminClient] = None):
        """
        Initialize the workout manager.

        Args:
            client: Optional GarminClient instance. Creates one if not provided.
        """
        self.client = client or GarminClient()
        self._authenticated = False
        self._garth_initialized = False

    def _ensure_authenticated(self):
        """Ensure we're authenticated with Garmin Connect."""
        if not self._authenticated:
            self.client.authenticate()
            self._authenticated = True

    def _ensure_garth(self):
        """Ensure garth is available and authenticated."""
        if not GARTH_AVAILABLE:
            raise RuntimeError("garth library not available - install with: pip install garth")

        if not self._garth_initialized:
            # Try to resume from saved tokens
            try:
                garth.resume("~/.garth")
                self._garth_initialized = True
            except Exception:
                raise RuntimeError("garth not authenticated - run garth.login() first")

    def create_swim_workout(
        self,
        name: str,
        week_number: int,
        main_set_description: str,
        warmup_distance: int = 300,
        cooldown_distance: int = 200,
        pool_length: int = 25,
        is_test_day: bool = False
    ) -> GarminWorkout:
        """
        Create a swim workout for Garmin.

        Args:
            name: Workout name
            week_number: Week number in training plan
            main_set_description: Description of main set
            warmup_distance: Warmup distance in yards/meters
            cooldown_distance: Cooldown distance
            pool_length: Pool length (default 25 yards)
            is_test_day: Whether this is a 400 TT test day
        """
        steps = []

        # Warmup
        steps.append(WorkoutStep(
            type=WorkoutStepType.WARMUP,
            duration_type="distance",
            duration_value=warmup_distance,
            target_type="open",
            description=f"Easy warmup - {warmup_distance}y"
        ))

        if is_test_day:
            # Test day: 400 TT
            steps.append(WorkoutStep(
                type=WorkoutStepType.INTERVAL,
                duration_type="distance",
                duration_value=400,
                target_type="open",
                description="400y Time Trial - Push start. Controlled first 100, build through 200-300, hold form."
            ))
        else:
            # Regular main set - use lap button for open-ended
            steps.append(WorkoutStep(
                type=WorkoutStepType.INTERVAL,
                duration_type="lap.button",
                target_type="open",
                description=f"Main Set: {main_set_description}"
            ))

        # Cooldown
        steps.append(WorkoutStep(
            type=WorkoutStepType.COOLDOWN,
            duration_type="distance",
            duration_value=cooldown_distance,
            target_type="open",
            description=f"Easy cooldown - {cooldown_distance}y"
        ))

        return GarminWorkout(
            name=name,
            sport_type=WorkoutSportType.SWIMMING,
            description=f"Week {week_number} - {main_set_description}",
            steps=steps,
            estimated_duration_minutes=45
        )

    def create_strength_workout(
        self,
        name: str,
        week_number: int,
        workout_type: str,  # "lower" or "upper"
        exercises: List[Dict[str, Any]]
    ) -> GarminWorkout:
        """
        Create a strength workout for Garmin.

        Args:
            name: Workout name
            week_number: Week number in training plan
            workout_type: "lower" or "upper" body
            exercises: List of exercise dictionaries
        """
        steps = []

        # Warmup
        steps.append(WorkoutStep(
            type=WorkoutStepType.WARMUP,
            duration_type="time",
            duration_value=300,  # 5 minutes
            target_type="open",
            description="Dynamic warmup - foam roll, stretches, activation"
        ))

        # Exercise steps
        for exercise in exercises:
            sets = exercise.get('sets', 3)
            reps = exercise.get('reps', '8-10')
            desc = f"{exercise['name']}: {sets}x{reps}"
            if exercise.get('notes'):
                desc += f" - {exercise['notes']}"

            steps.append(WorkoutStep(
                type=WorkoutStepType.INTERVAL,
                duration_type="lap.button",
                target_type="open",
                description=desc
            ))

        # Cooldown/finisher
        steps.append(WorkoutStep(
            type=WorkoutStepType.COOLDOWN,
            duration_type="time",
            duration_value=300,  # 5 minutes
            target_type="open",
            description="Cooldown - stretching and mobility"
        ))

        body_part = "Lower Body" if workout_type == "lower" else "Upper Body"

        return GarminWorkout(
            name=name,
            sport_type=WorkoutSportType.STRENGTH,
            description=f"Week {week_number} - {body_part} strength + power",
            steps=steps,
            estimated_duration_minutes=45
        )

    def create_vo2_workout(
        self,
        name: str,
        week_number: int,
        intervals: int,
        interval_duration_minutes: float,
        rest_duration_minutes: float,
        intensity: str
    ) -> GarminWorkout:
        """
        Create a VO2 max interval workout for Garmin.

        Args:
            name: Workout name
            week_number: Week number
            intervals: Number of intervals
            interval_duration_minutes: Duration of each interval
            rest_duration_minutes: Rest between intervals
            intensity: Intensity description (e.g., "RPE 8-9")
        """
        steps = []

        # Warmup
        steps.append(WorkoutStep(
            type=WorkoutStepType.WARMUP,
            duration_type="time",
            duration_value=480,  # 8 minutes
            target_type="open",
            description="Easy warmup + dynamic stretches"
        ))

        # Intervals as a repeat block
        interval_steps = [
            WorkoutStep(
                type=WorkoutStepType.INTERVAL,
                duration_type="time",
                duration_value=interval_duration_minutes * 60,
                target_type="open",
                description=f"Hard effort @ {intensity}"
            ),
            WorkoutStep(
                type=WorkoutStepType.RECOVERY,
                duration_type="time",
                duration_value=rest_duration_minutes * 60,
                target_type="open",
                description="Easy recovery"
            )
        ]

        steps.append(WorkoutStep(
            type=WorkoutStepType.REPEAT,
            duration_type="lap.button",
            repeat_count=intervals,
            child_steps=interval_steps,
            description=f"{intervals}x{interval_duration_minutes}min @ {intensity}, {rest_duration_minutes}min rest"
        ))

        # Cooldown
        steps.append(WorkoutStep(
            type=WorkoutStepType.COOLDOWN,
            duration_type="time",
            duration_value=300,  # 5 minutes
            target_type="open",
            description="Easy cooldown + stretching"
        ))

        return GarminWorkout(
            name=name,
            sport_type=WorkoutSportType.CARDIO,
            description=f"Week {week_number} - VO2 intervals: {intervals}x{interval_duration_minutes}min",
            steps=steps,
            estimated_duration_minutes=40
        )

    def _step_to_garmin_format(
        self,
        step: WorkoutStep,
        order: int,
        is_swim: bool = False
    ) -> Dict[str, Any]:
        """
        Convert a WorkoutStep to Garmin's step format.

        Args:
            step: WorkoutStep to convert
            order: Step order number
            is_swim: Whether this is a swimming workout (affects stroke type)
        """
        step_type_info = self.STEP_TYPE_MAP.get(step.type, self.STEP_TYPE_MAP[WorkoutStepType.OTHER])

        # Normalize duration_type
        duration_type = step.duration_type
        if duration_type == "lap_button":
            duration_type = "lap.button"

        condition_info = self.CONDITION_TYPE_MAP.get(
            duration_type,
            self.CONDITION_TYPE_MAP["lap.button"]
        )

        # Build the step
        garmin_step = {
            "type": "ExecutableStepDTO",
            "stepOrder": order,
            "stepType": step_type_info,
            "childStepId": None,
            "description": step.description or "",
            "endCondition": condition_info,
            "endConditionValue": float(step.duration_value) if step.duration_value else None,
            "preferredEndConditionUnit": None,
            "endConditionCompare": None,
            "targetType": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target", "displayOrder": 1},
            "targetValueOne": None,
            "targetValueTwo": None,
            "targetValueUnit": None,
            "zoneNumber": None,
            "secondaryTargetType": None,
            "secondaryTargetValueOne": None,
            "secondaryTargetValueTwo": None,
            "secondaryTargetValueUnit": None,
            "secondaryZoneNumber": None,
            "endConditionZone": None,
            "strokeType": {"strokeTypeId": 6 if is_swim else 0, "strokeTypeKey": "free" if is_swim else None, "displayOrder": 6 if is_swim else 0},
            "equipmentType": {"equipmentTypeId": 0, "equipmentTypeKey": None, "displayOrder": 0},
            "category": None,
            "exerciseName": None,
            "workoutProvider": None,
            "providerExerciseSourceId": None,
            "weightValue": None,
            "weightUnit": None
        }

        # Add preferred unit for swim distance steps
        if is_swim and duration_type == "distance":
            garmin_step["preferredEndConditionUnit"] = self.POOL_LENGTH_UNIT

        # Handle target types (heart rate, pace, etc.)
        if step.target_type and step.target_type not in ("open", None):
            target_map = {
                "heart_rate": {"workoutTargetTypeId": 4, "workoutTargetTypeKey": "heart.rate.zone"},
                "pace": {"workoutTargetTypeId": 2, "workoutTargetTypeKey": "pace.zone"},
                "power": {"workoutTargetTypeId": 3, "workoutTargetTypeKey": "power.zone"},
                "cadence": {"workoutTargetTypeId": 5, "workoutTargetTypeKey": "cadence"},
            }
            if step.target_type in target_map:
                garmin_step["targetType"] = target_map[step.target_type]
                garmin_step["targetValueOne"] = step.target_value_low
                garmin_step["targetValueTwo"] = step.target_value_high

        return garmin_step

    def workout_to_garmin_format(self, workout: GarminWorkout) -> Dict[str, Any]:
        """
        Convert a GarminWorkout to the format expected by Garmin Connect API.

        This creates the JSON structure needed for the workout creation API.
        """
        sport_info = self.SPORT_TYPE_MAP.get(
            workout.sport_type,
            self.SPORT_TYPE_MAP[WorkoutSportType.OTHER]
        )
        is_swim = workout.sport_type == WorkoutSportType.SWIMMING

        # Build workout steps in Garmin format
        garmin_steps = []
        step_order = 1

        for step in workout.steps:
            garmin_step = self._step_to_garmin_format(step, step_order, is_swim=is_swim)
            garmin_steps.append(garmin_step)
            step_order += 1

            # Handle child steps (for repeat blocks)
            if step.child_steps:
                for child in step.child_steps:
                    garmin_steps.append(self._step_to_garmin_format(child, step_order, is_swim=is_swim))
                    step_order += 1

        workout_json = {
            "workoutName": workout.name,
            "description": workout.description if workout.description else None,
            "sportType": sport_info,
            "subSportType": None,
            "workoutSegments": [
                {
                    "segmentOrder": 1,
                    "sportType": sport_info,
                    "poolLengthUnit": None,
                    "poolLength": None,
                    "avgTrainingSpeed": None,
                    "estimatedDurationInSecs": None,
                    "estimatedDistanceInMeters": None,
                    "estimatedDistanceUnit": None,
                    "estimateType": None,
                    "description": None,
                    "workoutSteps": garmin_steps
                }
            ],
            "estimatedDurationInSecs": (workout.estimated_duration_minutes or 45) * 60,
            "estimatedDistanceInMeters": None,
            "avgTrainingSpeed": 0.0
        }

        # Add pool settings for swimming workouts
        if is_swim:
            workout_json["poolLength"] = 25.0
            workout_json["poolLengthUnit"] = self.POOL_LENGTH_UNIT

        return workout_json

    def upload_workout(self, workout: GarminWorkout) -> Optional[str]:
        """
        Upload a workout to Garmin Connect.

        Args:
            workout: GarminWorkout to upload

        Returns:
            Workout ID if successful, None otherwise
        """
        self._ensure_garth()

        try:
            garmin_format = self.workout_to_garmin_format(workout)

            result = garth.connectapi(
                "/workout-service/workout",
                method="POST",
                json=garmin_format
            )

            workout_id = str(result.get("workoutId"))
            print(f"✓ Uploaded workout '{workout.name}' - ID: {workout_id}")
            return workout_id

        except Exception as e:
            print(f"✗ Error uploading workout '{workout.name}': {e}")
            return None

    def schedule_workout(
        self,
        workout_id: str,
        scheduled_date: date
    ) -> bool:
        """
        Schedule an existing workout on the Garmin calendar.

        Args:
            workout_id: Garmin workout ID
            scheduled_date: Date to schedule the workout

        Returns:
            True if successful
        """
        self._ensure_garth()

        try:
            date_str = scheduled_date.strftime("%Y-%m-%d")

            garth.connectapi(
                f"/workout-service/schedule/{workout_id}",
                method="POST",
                json={"date": date_str}
            )

            print(f"✓ Scheduled workout {workout_id} for {date_str}")
            return True

        except Exception as e:
            print(f"✗ Error scheduling workout: {e}")
            return False

    def create_and_schedule_workout(
        self,
        workout: GarminWorkout,
        scheduled_date: date
    ) -> Tuple[Optional[str], bool]:
        """
        Create a workout and schedule it in one operation.

        Args:
            workout: GarminWorkout to create
            scheduled_date: Date to schedule it

        Returns:
            Tuple of (workout_id, scheduled_success)
        """
        workout_id = self.upload_workout(workout)
        if workout_id:
            scheduled = self.schedule_workout(workout_id, scheduled_date)
            return workout_id, scheduled
        return None, False

    def get_workouts(self) -> List[Dict[str, Any]]:
        """
        Get all workouts from Garmin Connect.

        Returns:
            List of workout dictionaries
        """
        self._ensure_garth()

        try:
            workouts = garth.connectapi("/workout-service/workouts")
            return workouts if workouts else []
        except Exception as e:
            print(f"✗ Error getting workouts: {e}")
            return []

    def get_workout(self, workout_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific workout from Garmin Connect.

        Args:
            workout_id: Garmin workout ID

        Returns:
            Workout dictionary or None
        """
        self._ensure_garth()

        try:
            return garth.connectapi(f"/workout-service/workout/{workout_id}")
        except Exception as e:
            print(f"✗ Error getting workout {workout_id}: {e}")
            return None

    def delete_workout(self, workout_id: str) -> bool:
        """
        Delete a workout from Garmin Connect.

        Args:
            workout_id: Garmin workout ID to delete

        Returns:
            True if successful
        """
        self._ensure_garth()

        try:
            garth.connectapi(
                f"/workout-service/workout/{workout_id}",
                method="DELETE"
            )
            print(f"✓ Deleted workout {workout_id}")
            return True

        except Exception as e:
            print(f"✗ Error deleting workout: {e}")
            return False

    def get_calendar(self, year: int, month: int) -> List[Dict[str, Any]]:
        """
        Get calendar items for a specific month.

        Args:
            year: Year (e.g., 2026)
            month: Month (1-12, but API uses 0-11)

        Returns:
            List of calendar items
        """
        self._ensure_garth()

        try:
            # Garmin calendar API uses 0-indexed months
            api_month = month - 1
            calendar = garth.connectapi(f"/calendar-service/year/{year}/month/{api_month}")
            return calendar.get("calendarItems", [])
        except Exception as e:
            print(f"✗ Error getting calendar: {e}")
            return []

    def get_scheduled_workouts(
        self,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """
        Get workouts scheduled in a date range.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of scheduled workout dictionaries
        """
        scheduled = []

        # Get calendar items for each month in range
        current = start_date.replace(day=1)
        while current <= end_date:
            items = self.get_calendar(current.year, current.month)
            for item in items:
                if item.get("itemType") == "workout":
                    item_date = item.get("date")
                    if item_date:
                        scheduled.append(item)

            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

        return scheduled
