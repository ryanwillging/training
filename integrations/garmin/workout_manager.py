"""
Garmin Connect workout manager.
Creates and schedules workouts on Garmin Connect calendar.
"""

import json
import os
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

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
    duration_type: str  # "time", "distance", "lap_button", "open"
    duration_value: Optional[float] = None  # seconds or meters
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
    """

    def __init__(self, client: Optional[GarminClient] = None):
        """
        Initialize the workout manager.

        Args:
            client: Optional GarminClient instance. Creates one if not provided.
        """
        self.client = client or GarminClient()
        self._authenticated = False

    def _ensure_authenticated(self):
        """Ensure we're authenticated with Garmin Connect."""
        if not self._authenticated:
            self.client.authenticate()
            self._authenticated = True

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
            # Regular main set
            steps.append(WorkoutStep(
                type=WorkoutStepType.INTERVAL,
                duration_type="open",
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
            duration_value=420,  # 7 minutes
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
                duration_type="lap_button",
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
            duration_value=540,  # 9 minutes
            target_type="open",
            description="Easy warmup + dynamic stretches + strides"
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
            duration_type="lap_button",
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

    def workout_to_garmin_format(self, workout: GarminWorkout) -> Dict[str, Any]:
        """
        Convert a GarminWorkout to the format expected by Garmin Connect API.

        This creates the JSON structure needed for the workout creation API.
        """
        # Map our sport types to Garmin's sport type IDs
        sport_type_map = {
            WorkoutSportType.RUNNING: {"sportTypeId": 1, "sportTypeKey": "running"},
            WorkoutSportType.CYCLING: {"sportTypeId": 2, "sportTypeKey": "cycling"},
            WorkoutSportType.SWIMMING: {"sportTypeId": 5, "sportTypeKey": "lap_swimming"},
            WorkoutSportType.STRENGTH: {"sportTypeId": 13, "sportTypeKey": "strength_training"},
            WorkoutSportType.CARDIO: {"sportTypeId": 29, "sportTypeKey": "cardio_training"},
            WorkoutSportType.OTHER: {"sportTypeId": 0, "sportTypeKey": "other"},
        }

        sport_info = sport_type_map.get(workout.sport_type, sport_type_map[WorkoutSportType.OTHER])

        # Build workout steps in Garmin format
        garmin_steps = []
        step_order = 1

        for step in workout.steps:
            garmin_step = self._step_to_garmin_format(step, step_order)
            garmin_steps.append(garmin_step)
            step_order += 1
            if step.child_steps:
                for child in step.child_steps:
                    garmin_steps.append(self._step_to_garmin_format(child, step_order))
                    step_order += 1

        return {
            "workoutName": workout.name,
            "description": workout.description or "",
            "sportType": sport_info,
            "workoutSegments": [
                {
                    "segmentOrder": 1,
                    "sportType": sport_info,
                    "workoutSteps": garmin_steps
                }
            ],
            "estimatedDurationInSecs": (workout.estimated_duration_minutes or 45) * 60,
            "avgTrainingSpeed": None,
            "poolLength": 22.86 if workout.sport_type == WorkoutSportType.SWIMMING else None,  # 25 yards in meters
            "poolLengthUnit": {"unitKey": "yard"} if workout.sport_type == WorkoutSportType.SWIMMING else None,
        }

    def _step_to_garmin_format(self, step: WorkoutStep, order: int) -> Dict[str, Any]:
        """Convert a WorkoutStep to Garmin's step format."""
        # Map step types
        step_type_map = {
            WorkoutStepType.WARMUP: {"stepTypeId": 1, "stepTypeKey": "warmup"},
            WorkoutStepType.COOLDOWN: {"stepTypeId": 2, "stepTypeKey": "cooldown"},
            WorkoutStepType.INTERVAL: {"stepTypeId": 3, "stepTypeKey": "interval"},
            WorkoutStepType.RECOVERY: {"stepTypeId": 4, "stepTypeKey": "recovery"},
            WorkoutStepType.REST: {"stepTypeId": 5, "stepTypeKey": "rest"},
            WorkoutStepType.REPEAT: {"stepTypeId": 6, "stepTypeKey": "repeat"},
            WorkoutStepType.OTHER: {"stepTypeId": 7, "stepTypeKey": "other"},
        }

        step_type_info = step_type_map.get(step.type, step_type_map[WorkoutStepType.OTHER])

        # Duration condition
        duration_condition = {
            "conditionTypeId": 1 if step.duration_type == "time" else 3 if step.duration_type == "distance" else 7,
            "conditionTypeKey": step.duration_type
        }

        garmin_step = {
            "stepOrder": order,
            "stepType": step_type_info,
            "endCondition": duration_condition,
            "endConditionValue": step.duration_value,
            "repeatType": None,
            "repeatValue": step.repeat_count,
            "description": step.description or "",
        }

        # Target condition
        if step.target_type and step.target_type != "open":
            target_map = {
                "heart_rate": 4,
                "pace": 2,
                "power": 3,
                "cadence": 5,
            }
            garmin_step["targetType"] = {
                "workoutTargetTypeId": target_map.get(step.target_type, 1),
                "workoutTargetTypeKey": step.target_type
            }
            garmin_step["targetValueLow"] = step.target_value_low
            garmin_step["targetValueHigh"] = step.target_value_high
        else:
            garmin_step["targetType"] = {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target"}

        return garmin_step

    def upload_workout(self, workout: GarminWorkout) -> Optional[str]:
        """
        Upload a workout to Garmin Connect.

        Args:
            workout: GarminWorkout to upload

        Returns:
            Workout ID if successful, None otherwise
        """
        self._ensure_authenticated()

        try:
            garmin_format = self.workout_to_garmin_format(workout)

            # Use the garminconnect library's add_workout method if available
            if hasattr(self.client.client, 'add_workout'):
                result = self.client.client.add_workout(garmin_format)
                workout_id = result.get('workoutId')
                print(f"✓ Uploaded workout '{workout.name}' - ID: {workout_id}")
                return str(workout_id)
            else:
                # Fallback: manual API call
                print(f"⚠ Workout upload API not available in garminconnect library")
                return None

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
        self._ensure_authenticated()

        try:
            # Format date for Garmin API
            date_str = scheduled_date.strftime("%Y-%m-%d")

            if hasattr(self.client.client, 'schedule_workout'):
                self.client.client.schedule_workout(workout_id, date_str)
                print(f"✓ Scheduled workout {workout_id} for {date_str}")
                return True
            else:
                print(f"⚠ Workout scheduling API not available")
                return False

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
        self._ensure_authenticated()

        try:
            if hasattr(self.client.client, 'get_workouts'):
                # Get workouts from Garmin
                start_str = start_date.strftime("%Y-%m-%d")
                end_str = end_date.strftime("%Y-%m-%d")

                # This may need adjustment based on actual API
                workouts = self.client.client.get_workouts()
                return workouts if workouts else []

        except Exception as e:
            print(f"✗ Error getting scheduled workouts: {e}")

        return []

    def delete_workout(self, workout_id: str) -> bool:
        """
        Delete a workout from Garmin Connect.

        Args:
            workout_id: Garmin workout ID to delete

        Returns:
            True if successful
        """
        self._ensure_authenticated()

        try:
            if hasattr(self.client.client, 'delete_workout'):
                self.client.client.delete_workout(workout_id)
                print(f"✓ Deleted workout {workout_id}")
                return True

        except Exception as e:
            print(f"✗ Error deleting workout: {e}")

        return False
