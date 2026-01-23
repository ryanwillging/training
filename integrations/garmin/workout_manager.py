"""
Garmin Connect workout manager.
Creates and schedules workouts on Garmin Connect calendar.

API format discovered by inspecting actual Garmin workouts - the official
garminconnect library doesn't fully support workout creation.
"""

import json
import os
import re
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

    # Fixed rest condition
    FIXED_REST_CONDITION = {"conditionTypeId": 8, "conditionTypeKey": "fixed.rest", "displayOrder": 8, "displayable": True}

    # Iterations condition for repeat groups
    ITERATIONS_CONDITION = {"conditionTypeId": 7, "conditionTypeKey": "iterations", "displayOrder": 7, "displayable": False}

    @staticmethod
    def parse_sets_string(sets_str: str) -> Tuple[Optional[int], Optional[float], Optional[str]]:
        """
        Parse a sets string like "4×50" or "3×8-10" or "2×30s".

        Returns:
            Tuple of (reps, value, unit) where unit is "distance", "time", or "reps"
        """
        if not sets_str:
            return None, None, None

        # Match patterns like "4×50", "3x8-10", "2×30s"
        match = re.match(r'(\d+)[×x](\d+(?:-\d+)?)(s|m|min|y|yd|yards?)?', sets_str, re.IGNORECASE)
        if match:
            reps = int(match.group(1))
            value_str = match.group(2)
            unit_suffix = match.group(3)

            # Handle range like "8-10" by taking average
            if '-' in value_str:
                parts = value_str.split('-')
                value = (int(parts[0]) + int(parts[1])) / 2
            else:
                value = float(value_str)

            # Determine unit type
            if unit_suffix and unit_suffix.lower() in ('s', 'm', 'min'):
                unit = "time"
                if unit_suffix.lower() in ('m', 'min'):
                    value *= 60  # Convert minutes to seconds
            elif unit_suffix and unit_suffix.lower() in ('y', 'yd', 'yard', 'yards'):
                unit = "distance"
            else:
                # Default: if value > 20, assume distance in yards; else assume reps
                unit = "distance" if value > 20 else "reps"

            return reps, value, unit

        return None, None, None

    @staticmethod
    def parse_rest_string(rest_str: str) -> Optional[float]:
        """
        Parse a rest string like "15-20s" or "20s" or "2 min" or "45-60s".

        Returns:
            Rest time in seconds, or None if cannot parse
        """
        if not rest_str:
            return None

        # Handle ranges like "15-20s" or "45-60s"
        range_match = re.match(r'(\d+)-(\d+)\s*(s|sec|seconds?|m|min|minutes?)?', rest_str, re.IGNORECASE)
        if range_match:
            low = int(range_match.group(1))
            high = int(range_match.group(2))
            unit = range_match.group(3) or 's'
            avg = (low + high) / 2
            if unit.lower() in ('m', 'min', 'minute', 'minutes'):
                return avg * 60
            return avg

        # Handle single values like "20s" or "2 min"
        single_match = re.match(r'(\d+(?:\.\d+)?)\s*(s|sec|seconds?|m|min|minutes?)?', rest_str, re.IGNORECASE)
        if single_match:
            value = float(single_match.group(1))
            unit = single_match.group(2) or 's'
            if unit.lower() in ('m', 'min', 'minute', 'minutes'):
                return value * 60
            return value

        return None

    @staticmethod
    def parse_distance_string(distance_str: str) -> Optional[float]:
        """
        Parse a distance string like "300 yards" or "200y" or "400".

        Returns:
            Distance in yards, or None if cannot parse
        """
        if not distance_str:
            return None

        # Match patterns like "300 yards", "200y", "400"
        match = re.match(r'(\d+(?:\.\d+)?)\s*(y|yd|yards?|m|meters?)?', distance_str, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            # Assume yards if not specified (for swimming)
            return value

        return None

    @staticmethod
    def parse_duration_string(duration_str: str) -> Optional[float]:
        """
        Parse a duration string like "5 min" or "30s" or "5-8 min".

        Returns:
            Duration in seconds, or None if cannot parse
        """
        if not duration_str:
            return None

        # Handle ranges like "5-8 min"
        range_match = re.match(r'(\d+)-(\d+)\s*(s|sec|seconds?|m|min|minutes?)?', duration_str, re.IGNORECASE)
        if range_match:
            low = int(range_match.group(1))
            high = int(range_match.group(2))
            unit = range_match.group(3) or 'min'
            avg = (low + high) / 2
            if unit.lower() in ('m', 'min', 'minute', 'minutes'):
                return avg * 60
            return avg

        # Handle single values
        single_match = re.match(r'(\d+(?:\.\d+)?)\s*(s|sec|seconds?|m|min|minutes?)?', duration_str, re.IGNORECASE)
        if single_match:
            value = float(single_match.group(1))
            unit = single_match.group(2) or 'min'
            if unit.lower() in ('m', 'min', 'minute', 'minutes'):
                return value * 60
            return value

        return None

    def _create_repeat_group(
        self,
        iterations: int,
        child_steps: List[Dict[str, Any]],
        step_order: int,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Create a RepeatGroupDTO for Garmin workouts.

        Args:
            iterations: Number of times to repeat the group
            child_steps: List of child step dictionaries (already in Garmin format)
            step_order: Step order number for this group
            description: Optional description for the repeat group

        Returns:
            RepeatGroupDTO dictionary
        """
        return {
            "type": "RepeatGroupDTO",
            "stepOrder": step_order,
            "stepType": None,
            "childStepId": 1,
            "description": description,
            "numberOfIterations": iterations,
            "smartRepeat": False,
            "endCondition": self.ITERATIONS_CONDITION,
            "endConditionValue": float(iterations),
            "preferredEndConditionUnit": None,
            "workoutSteps": child_steps
        }

    def _create_swim_interval_step(
        self,
        distance: float,
        step_order: int,
        step_type: str = "interval",
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Create a swim interval step (distance-based).

        Args:
            distance: Distance in yards
            step_order: Step order number
            step_type: Step type key (interval, warmup, cooldown, recovery)
            description: Optional description

        Returns:
            ExecutableStepDTO dictionary
        """
        step_type_map = {
            "interval": {"stepTypeId": 3, "stepTypeKey": "interval", "displayOrder": 3},
            "warmup": {"stepTypeId": 1, "stepTypeKey": "warmup", "displayOrder": 1},
            "cooldown": {"stepTypeId": 2, "stepTypeKey": "cooldown", "displayOrder": 2},
            "recovery": {"stepTypeId": 4, "stepTypeKey": "recovery", "displayOrder": 4},
        }

        return {
            "type": "ExecutableStepDTO",
            "stepOrder": step_order,
            "stepType": step_type_map.get(step_type, step_type_map["interval"]),
            "childStepId": None,
            "description": description,
            "endCondition": self.CONDITION_TYPE_MAP["distance"],
            "endConditionValue": float(distance),
            "preferredEndConditionUnit": self.POOL_LENGTH_UNIT,
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
            "strokeType": {"strokeTypeId": 6, "strokeTypeKey": "free", "displayOrder": 6},
            "equipmentType": {"equipmentTypeId": 0, "equipmentTypeKey": None, "displayOrder": 0},
            "category": None,
            "exerciseName": None,
            "workoutProvider": None,
            "providerExerciseSourceId": None,
            "weightValue": None,
            "weightUnit": None
        }

    def _create_rest_step(
        self,
        rest_seconds: float,
        step_order: int,
        description: str = "Rest"
    ) -> Dict[str, Any]:
        """
        Create a rest step (time-based).

        Args:
            rest_seconds: Rest duration in seconds
            step_order: Step order number
            description: Optional description

        Returns:
            ExecutableStepDTO dictionary for rest
        """
        return {
            "type": "ExecutableStepDTO",
            "stepOrder": step_order,
            "stepType": {"stepTypeId": 5, "stepTypeKey": "rest", "displayOrder": 5},
            "childStepId": None,
            "description": description,
            "endCondition": self.FIXED_REST_CONDITION,
            "endConditionValue": float(rest_seconds),
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
            "strokeType": {"strokeTypeId": 6, "strokeTypeKey": "free", "displayOrder": 6},
            "equipmentType": {"equipmentTypeId": 0, "equipmentTypeKey": None, "displayOrder": 0},
            "category": None,
            "exerciseName": None,
            "workoutProvider": None,
            "providerExerciseSourceId": None,
            "weightValue": None,
            "weightUnit": None
        }

    def _exercise_to_garmin_steps(
        self,
        exercise: Dict[str, Any],
        step_order: int,
        step_type: str = "interval"
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Convert an exercise dictionary to Garmin step(s).

        Handles both simple distance exercises and sets with rest.

        Args:
            exercise: Exercise dictionary with keys like 'distance', 'sets', 'rest', 'name'
            step_order: Starting step order number
            step_type: Type of step (warmup, interval, cooldown)

        Returns:
            Tuple of (list of steps, next step order)
        """
        steps = []
        current_order = step_order

        # Check for simple distance-based exercise
        if exercise.get("distance") and not exercise.get("sets"):
            distance = self.parse_distance_string(exercise["distance"])
            if distance:
                step = self._create_swim_interval_step(
                    distance=distance,
                    step_order=current_order,
                    step_type=step_type,
                    description=exercise.get("name", "")
                )
                steps.append(step)
                current_order += 1
            return steps, current_order

        # Check for sets-based exercise (e.g., "4×50")
        if exercise.get("sets"):
            reps, value, unit = self.parse_sets_string(exercise["sets"])
            rest_seconds = self.parse_rest_string(exercise.get("rest", ""))

            if reps and value and unit == "distance":
                # Create repeat group with interval + optional rest
                child_steps = []

                # Interval step
                interval_step = self._create_swim_interval_step(
                    distance=value,
                    step_order=1,
                    step_type="interval",
                    description=exercise.get("notes", exercise.get("name", ""))
                )
                child_steps.append(interval_step)

                # Rest step (if specified)
                if rest_seconds:
                    rest_step = self._create_rest_step(
                        rest_seconds=rest_seconds,
                        step_order=2,
                        description=f"{int(rest_seconds)}s rest"
                    )
                    child_steps.append(rest_step)

                # Create repeat group
                group_desc = f"{reps}×{int(value)}"
                if rest_seconds:
                    group_desc += f", {int(rest_seconds)}s rest"
                if exercise.get("notes"):
                    group_desc += f" - {exercise['notes']}"

                repeat_group = self._create_repeat_group(
                    iterations=reps,
                    child_steps=child_steps,
                    step_order=current_order,
                    description=group_desc
                )
                steps.append(repeat_group)
                current_order += 1

            return steps, current_order

        # Fallback: parse description for main set pattern like "12×50 @ moderate-hard, 20s rest"
        description = exercise.get("description", "")
        if description:
            # Try to parse "12×50 @ intensity, 20s rest" pattern
            match = re.match(r'(\d+)[×x](\d+)\s*@\s*([^,]+),?\s*(\d+s?\s*rest)?', description, re.IGNORECASE)
            if match:
                reps = int(match.group(1))
                distance = float(match.group(2))
                intensity = match.group(3).strip()
                rest_match = match.group(4)
                rest_seconds = self.parse_rest_string(rest_match) if rest_match else 20.0

                child_steps = []

                # Interval step
                interval_step = self._create_swim_interval_step(
                    distance=distance,
                    step_order=1,
                    step_type="interval",
                    description=intensity
                )
                child_steps.append(interval_step)

                # Rest step
                rest_step = self._create_rest_step(
                    rest_seconds=rest_seconds,
                    step_order=2,
                    description=f"{int(rest_seconds)}s rest"
                )
                child_steps.append(rest_step)

                repeat_group = self._create_repeat_group(
                    iterations=reps,
                    child_steps=child_steps,
                    step_order=current_order,
                    description=f"{reps}×{int(distance)} @ {intensity}"
                )
                steps.append(repeat_group)
                current_order += 1

                return steps, current_order

        return steps, current_order

    def create_detailed_swim_workout(
        self,
        name: str,
        week_number: int,
        workout_details: Dict[str, List[Dict[str, Any]]],
        pool_length: int = 25
    ) -> Dict[str, Any]:
        """
        Create a detailed swim workout with individual sets/reps for Garmin.

        Args:
            name: Workout name
            week_number: Week number in training plan
            workout_details: Dictionary with 'warmup', 'main', 'cooldown' lists
                Each list contains exercise dictionaries with keys like:
                - distance: "300 yards"
                - sets: "4×50"
                - rest: "15-20s"
                - name: "Easy swim"
                - description: "12×50 @ moderate-hard (RPE 7), 20s rest"
            pool_length: Pool length in yards (default 25)

        Returns:
            Garmin workout JSON ready for API upload
        """
        sport_info = self.SPORT_TYPE_MAP[WorkoutSportType.SWIMMING]
        garmin_steps = []
        step_order = 1

        # Process warmup
        warmup_exercises = workout_details.get("warmup", [])
        for exercise in warmup_exercises:
            # First warmup item uses warmup step type
            step_type = "warmup" if step_order == 1 else "interval"
            new_steps, step_order = self._exercise_to_garmin_steps(exercise, step_order, step_type)
            garmin_steps.extend(new_steps)

        # Process main set
        main_exercises = workout_details.get("main", [])
        for exercise in main_exercises:
            new_steps, step_order = self._exercise_to_garmin_steps(exercise, step_order, "interval")
            garmin_steps.extend(new_steps)

        # Process cooldown
        cooldown_exercises = workout_details.get("cooldown", [])
        for exercise in cooldown_exercises:
            step_type = "cooldown"
            new_steps, step_order = self._exercise_to_garmin_steps(exercise, step_order, step_type)
            garmin_steps.extend(new_steps)

        # Build workout JSON
        workout_json = {
            "workoutName": name,
            "description": f"Week {week_number} - Detailed swim workout",
            "sportType": sport_info,
            "subSportType": None,
            "poolLength": float(pool_length),
            "poolLengthUnit": self.POOL_LENGTH_UNIT,
            "workoutSegments": [
                {
                    "segmentOrder": 1,
                    "sportType": sport_info,
                    "poolLengthUnit": self.POOL_LENGTH_UNIT,
                    "poolLength": float(pool_length),
                    "avgTrainingSpeed": None,
                    "estimatedDurationInSecs": None,
                    "estimatedDistanceInMeters": None,
                    "estimatedDistanceUnit": None,
                    "estimateType": None,
                    "description": None,
                    "workoutSteps": garmin_steps
                }
            ],
            "estimatedDurationInSecs": 2700,  # 45 min estimate
            "estimatedDistanceInMeters": None,
            "avgTrainingSpeed": 0.0
        }

        return workout_json

    def upload_detailed_workout(self, workout_json: Dict[str, Any]) -> Optional[str]:
        """
        Upload a detailed workout (already in Garmin format) to Garmin Connect.

        Args:
            workout_json: Workout in Garmin API format

        Returns:
            Workout ID if successful, None otherwise
        """
        self._ensure_garth()

        try:
            result = garth.connectapi(
                "/workout-service/workout",
                method="POST",
                json=workout_json
            )

            workout_id = str(result.get("workoutId"))
            print(f"✓ Uploaded detailed workout '{workout_json.get('workoutName')}' - ID: {workout_id}")
            return workout_id

        except Exception as e:
            print(f"✗ Error uploading detailed workout: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _create_strength_step(
        self,
        exercise_name: str,
        step_order: int,
        step_type: str = "other",
        sets: Optional[str] = None,
        duration: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a strength exercise step.

        Args:
            exercise_name: Name of the exercise
            step_order: Step order number
            step_type: Step type (warmup, cooldown, other, interval)
            sets: Sets string like "3×8-10"
            duration: Duration string like "5-8 min"
            notes: Additional notes

        Returns:
            ExecutableStepDTO dictionary
        """
        step_type_map = {
            "warmup": {"stepTypeId": 1, "stepTypeKey": "warmup", "displayOrder": 1},
            "cooldown": {"stepTypeId": 2, "stepTypeKey": "cooldown", "displayOrder": 2},
            "interval": {"stepTypeId": 3, "stepTypeKey": "interval", "displayOrder": 3},
            "rest": {"stepTypeId": 5, "stepTypeKey": "rest", "displayOrder": 5},
            "other": {"stepTypeId": 7, "stepTypeKey": "other", "displayOrder": 7},
        }

        # Build description
        desc_parts = [exercise_name]
        if sets:
            desc_parts.append(f"({sets})")
        if duration:
            desc_parts.append(f"- {duration}")
        if notes:
            desc_parts.append(f"- {notes}")
        description = " ".join(desc_parts)

        # Determine end condition
        if duration:
            # Parse duration to seconds
            duration_secs = self.parse_duration_string(duration)
            if duration_secs:
                end_condition = self.CONDITION_TYPE_MAP["time"]
                end_condition_value = duration_secs
            else:
                end_condition = self.CONDITION_TYPE_MAP["lap.button"]
                end_condition_value = None
        else:
            # Use lap button for exercises without duration
            end_condition = self.CONDITION_TYPE_MAP["lap.button"]
            end_condition_value = None

        return {
            "type": "ExecutableStepDTO",
            "stepOrder": step_order,
            "stepType": step_type_map.get(step_type, step_type_map["other"]),
            "childStepId": None,
            "description": description,
            "endCondition": end_condition,
            "endConditionValue": end_condition_value,
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
            "strokeType": {"strokeTypeId": 0, "strokeTypeKey": None, "displayOrder": 0},
            "equipmentType": {"equipmentTypeId": 0, "equipmentTypeKey": None, "displayOrder": 0},
            "category": None,
            "exerciseName": exercise_name,
            "workoutProvider": None,
            "providerExerciseSourceId": None,
            "weightValue": None,
            "weightUnit": None
        }

    def _strength_exercise_to_garmin_steps(
        self,
        exercise: Dict[str, Any],
        step_order: int,
        step_type: str = "other"
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Convert a strength exercise dictionary to Garmin step(s).

        Args:
            exercise: Exercise dictionary with keys like 'name', 'sets', 'duration', 'notes'
            step_order: Starting step order number
            step_type: Type of step (warmup, cooldown, other)

        Returns:
            Tuple of (list of steps, next step order)
        """
        steps = []
        current_order = step_order

        name = exercise.get("name", "Exercise")
        sets = exercise.get("sets")
        duration = exercise.get("duration")
        notes = exercise.get("notes")

        step = self._create_strength_step(
            exercise_name=name,
            step_order=current_order,
            step_type=step_type,
            sets=sets,
            duration=duration,
            notes=notes
        )
        steps.append(step)
        current_order += 1

        return steps, current_order

    def create_detailed_strength_workout(
        self,
        name: str,
        week_number: int,
        workout_details: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Create a detailed strength workout with individual exercises for Garmin.

        Args:
            name: Workout name
            week_number: Week number in training plan
            workout_details: Dictionary with 'warmup', 'main', 'finisher', 'cooldown' lists
                Each list contains exercise dictionaries with keys like:
                - name: "Bench Press or Push-ups"
                - sets: "3×8-10"
                - duration: "5-8 min"
                - notes: "Each side"

        Returns:
            Garmin workout JSON ready for API upload
        """
        sport_info = self.SPORT_TYPE_MAP[WorkoutSportType.STRENGTH]
        garmin_steps = []
        step_order = 1

        # Process warmup
        warmup_exercises = workout_details.get("warmup", [])
        for exercise in warmup_exercises:
            step_type = "warmup" if step_order == 1 else "other"
            new_steps, step_order = self._strength_exercise_to_garmin_steps(exercise, step_order, step_type)
            garmin_steps.extend(new_steps)

        # Process main exercises
        main_exercises = workout_details.get("main", [])
        for exercise in main_exercises:
            new_steps, step_order = self._strength_exercise_to_garmin_steps(exercise, step_order, "interval")
            garmin_steps.extend(new_steps)

        # Process finisher
        finisher_exercises = workout_details.get("finisher", [])
        for exercise in finisher_exercises:
            new_steps, step_order = self._strength_exercise_to_garmin_steps(exercise, step_order, "interval")
            garmin_steps.extend(new_steps)

        # Process cooldown
        cooldown_exercises = workout_details.get("cooldown", [])
        for exercise in cooldown_exercises:
            new_steps, step_order = self._strength_exercise_to_garmin_steps(exercise, step_order, "cooldown")
            garmin_steps.extend(new_steps)

        # Build workout JSON
        workout_json = {
            "workoutName": name,
            "description": f"Week {week_number} - Detailed strength workout",
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
            "estimatedDurationInSecs": 2700,  # 45 min estimate
            "estimatedDistanceInMeters": None,
            "avgTrainingSpeed": 0.0
        }

        return workout_json

    def _create_cardio_interval_step(
        self,
        duration_seconds: float,
        step_order: int,
        step_type: str = "interval",
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Create a cardio interval step (time-based).

        Args:
            duration_seconds: Duration in seconds
            step_order: Step order number
            step_type: Step type key (interval, warmup, cooldown, recovery)
            description: Optional description

        Returns:
            ExecutableStepDTO dictionary
        """
        step_type_map = {
            "interval": {"stepTypeId": 3, "stepTypeKey": "interval", "displayOrder": 3},
            "warmup": {"stepTypeId": 1, "stepTypeKey": "warmup", "displayOrder": 1},
            "cooldown": {"stepTypeId": 2, "stepTypeKey": "cooldown", "displayOrder": 2},
            "recovery": {"stepTypeId": 4, "stepTypeKey": "recovery", "displayOrder": 4},
        }

        return {
            "type": "ExecutableStepDTO",
            "stepOrder": step_order,
            "stepType": step_type_map.get(step_type, step_type_map["interval"]),
            "childStepId": None,
            "description": description,
            "endCondition": self.CONDITION_TYPE_MAP["time"],
            "endConditionValue": float(duration_seconds),
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
            "strokeType": {"strokeTypeId": 0, "strokeTypeKey": None, "displayOrder": 0},
            "equipmentType": {"equipmentTypeId": 0, "equipmentTypeKey": None, "displayOrder": 0},
            "category": None,
            "exerciseName": None,
            "workoutProvider": None,
            "providerExerciseSourceId": None,
            "weightValue": None,
            "weightUnit": None
        }

    def create_detailed_vo2_workout(
        self,
        name: str,
        week_number: int,
        workout_details: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Create a detailed VO2 max workout with intervals for Garmin.

        Args:
            name: Workout name
            week_number: Week number in training plan
            workout_details: Dictionary with 'warmup', 'main', 'cooldown' lists
                Main set description like "6×2 min @ hard (RPE 8), 2 min easy between"

        Returns:
            Garmin workout JSON ready for API upload
        """
        sport_info = self.SPORT_TYPE_MAP[WorkoutSportType.CARDIO]  # Uses running
        garmin_steps = []
        step_order = 1

        # Process warmup
        warmup_exercises = workout_details.get("warmup", [])
        for exercise in warmup_exercises:
            duration = exercise.get("duration")
            if duration:
                duration_secs = self.parse_duration_string(duration)
                if duration_secs:
                    step = self._create_cardio_interval_step(
                        duration_seconds=duration_secs,
                        step_order=step_order,
                        step_type="warmup" if step_order == 1 else "other",
                        description=exercise.get("name", "Warmup")
                    )
                    garmin_steps.append(step)
                    step_order += 1
            elif exercise.get("sets"):
                # Strides like "3-4×15-20s"
                step = self._create_strength_step(
                    exercise_name=exercise.get("name", "Strides"),
                    step_order=step_order,
                    step_type="other",
                    sets=exercise.get("sets")
                )
                garmin_steps.append(step)
                step_order += 1
            else:
                # Generic step
                step = self._create_strength_step(
                    exercise_name=exercise.get("name", "Warmup"),
                    step_order=step_order,
                    step_type="warmup" if step_order == 1 else "other"
                )
                garmin_steps.append(step)
                step_order += 1

        # Process main set - parse interval description
        main_exercises = workout_details.get("main", [])
        for exercise in main_exercises:
            description = exercise.get("description", "")

            # Try to parse "6×2 min @ hard (RPE 8), 2 min easy between" pattern
            match = re.match(
                r'(\d+)[×x](\d+(?:\.\d+)?)\s*(min|s|sec)?\s*@\s*([^,]+),?\s*(\d+(?:\.\d+)?)\s*(min|s|sec)?\s*(?:easy\s+)?(?:between|rest)?',
                description,
                re.IGNORECASE
            )
            if match:
                reps = int(match.group(1))
                interval_value = float(match.group(2))
                interval_unit = match.group(3) or 'min'
                intensity = match.group(4).strip()
                rest_value = float(match.group(5))
                rest_unit = match.group(6) or 'min'

                # Convert to seconds
                if interval_unit.lower() in ('min', 'm'):
                    interval_secs = interval_value * 60
                else:
                    interval_secs = interval_value

                if rest_unit.lower() in ('min', 'm'):
                    rest_secs = rest_value * 60
                else:
                    rest_secs = rest_value

                # Create repeat group
                child_steps = []

                # Hard interval
                interval_step = self._create_cardio_interval_step(
                    duration_seconds=interval_secs,
                    step_order=1,
                    step_type="interval",
                    description=f"Hard @ {intensity}"
                )
                child_steps.append(interval_step)

                # Recovery
                recovery_step = self._create_cardio_interval_step(
                    duration_seconds=rest_secs,
                    step_order=2,
                    step_type="recovery",
                    description="Easy recovery"
                )
                child_steps.append(recovery_step)

                # Create repeat group
                repeat_group = self._create_repeat_group(
                    iterations=reps,
                    child_steps=child_steps,
                    step_order=step_order,
                    description=f"{reps}×{int(interval_value)} min @ {intensity}"
                )
                garmin_steps.append(repeat_group)
                step_order += 1
            else:
                # Fallback - just add as a generic step
                step = self._create_strength_step(
                    exercise_name=exercise.get("name", "Main Set"),
                    step_order=step_order,
                    step_type="interval",
                    notes=description
                )
                garmin_steps.append(step)
                step_order += 1

        # Process cooldown
        cooldown_exercises = workout_details.get("cooldown", [])
        for exercise in cooldown_exercises:
            duration = exercise.get("duration")
            if duration:
                duration_secs = self.parse_duration_string(duration)
                if duration_secs:
                    step = self._create_cardio_interval_step(
                        duration_seconds=duration_secs,
                        step_order=step_order,
                        step_type="cooldown",
                        description=exercise.get("name", "Cooldown")
                    )
                    garmin_steps.append(step)
                    step_order += 1

        # Build workout JSON
        workout_json = {
            "workoutName": name,
            "description": f"Week {week_number} - VO2 max intervals",
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
            "estimatedDurationInSecs": 2400,  # 40 min estimate
            "estimatedDistanceInMeters": None,
            "avgTrainingSpeed": 0.0
        }

        return workout_json

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
