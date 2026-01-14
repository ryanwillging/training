"""
Hevy API client wrapper.
Uses the hevy-api-client library to interact with Hevy's API.
"""

import os
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from dotenv import load_dotenv

try:
    from hevy_api_client import Client
    from hevy_api_client.api.workouts import get_v1_workouts, get_v1_workouts_count
    from hevy_api_client.types import UNSET
    HEVY_AVAILABLE = True
except ImportError:
    HEVY_AVAILABLE = False
    print("Warning: hevy-api-client not installed. Run: pip install hevy-api-client")

load_dotenv()


class HevyClient:
    """
    Wrapper around hevy-api-client for easier use in our application.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Hevy client.

        Args:
            api_key: Hevy API key (defaults to HEVY_API_KEY env var)
        """
        if not HEVY_AVAILABLE:
            raise ImportError("hevy-api-client is not installed. Run: pip install hevy-api-client")

        self.api_key_str = api_key or os.getenv("HEVY_API_KEY")

        if not self.api_key_str:
            raise ValueError(
                "Hevy API key not provided. Set HEVY_API_KEY environment variable "
                "or pass it to the constructor."
            )

        # Store API key as string for headers
        self.api_key = self.api_key_str

        # Create the client
        self.client = Client()
        print(f"Initialized Hevy API client")

    def get_workouts(self, page: int = 1, page_size: int = 10) -> List[Dict[str, Any]]:
        """
        Get workouts from Hevy.

        Args:
            page: Page number (1-indexed)
            page_size: Number of workouts per page

        Returns:
            List of workout dictionaries
        """
        try:
            response = get_v1_workouts.sync(
                client=self.client,
                page=page,
                page_size=page_size,
                api_key=self.api_key
            )

            if response and hasattr(response, 'workouts') and not isinstance(response.workouts, type(UNSET)):
                # Convert Workout objects to dictionaries
                workouts = []
                for workout in response.workouts:
                    workout_dict = self._workout_to_dict(workout)
                    workouts.append(workout_dict)
                return workouts
            return []

        except Exception as e:
            print(f"Error fetching workouts: {e}")
            raise

    def get_all_workouts(self, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """
        Get all workouts, optionally filtered by date range.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of workout dictionaries
        """
        all_workouts = []
        page = 1
        page_size = 10  # Hevy API has a page size limit

        try:
            while True:
                workouts = self.get_workouts(page=page, page_size=page_size)

                if not workouts:
                    break

                # Filter by date if specified
                for workout in workouts:
                    workout_date = workout.get('date')
                    if workout_date:
                        if isinstance(workout_date, str):
                            workout_date = datetime.fromisoformat(workout_date.replace('Z', '+00:00')).date()

                        # Workouts are sorted newest first
                        # If we're past the start_date, we can stop
                        if start_date and workout_date < start_date:
                            return all_workouts

                        # Skip if after end_date
                        if end_date and workout_date > end_date:
                            continue

                        # Skip if before start_date
                        if start_date and workout_date < start_date:
                            continue

                    all_workouts.append(workout)

                # Check if we got fewer than page_size (last page)
                if len(workouts) < page_size:
                    break

                page += 1

                # Safety check
                if len(all_workouts) > 1000:
                    print("Warning: Retrieved over 1000 workouts, stopping")
                    break

        except Exception as e:
            print(f"Error fetching workouts: {e}")
            raise

        return all_workouts

    def get_workout_count(self) -> int:
        """
        Get total number of workouts.

        Returns:
            Workout count
        """
        try:
            response = get_v1_workouts_count.sync(
                client=self.client,
                api_key=self.api_key
            )
            if response and hasattr(response, 'workout_count') and not isinstance(response.workout_count, type(UNSET)):
                return response.workout_count
            return 0
        except Exception as e:
            print(f"Error fetching workout count: {e}")
            return 0

    def _workout_to_dict(self, workout: Any) -> Dict[str, Any]:
        """
        Convert Hevy Workout object to dictionary.

        Args:
            workout: Hevy Workout object

        Returns:
            Dictionary representation
        """
        # Use to_dict() if available, otherwise manually extract
        if hasattr(workout, 'to_dict'):
            workout_dict = workout.to_dict()
        else:
            workout_dict = {
                'id': getattr(workout, 'id', None),
                'title': getattr(workout, 'title', None),
                'description': getattr(workout, 'description', None),
                'start_time': getattr(workout, 'start_time', None),
                'end_time': getattr(workout, 'end_time', None),
                'created_at': getattr(workout, 'created_at', None),
                'updated_at': getattr(workout, 'updated_at', None),
                'exercises': [],
            }

            # Get exercises if available
            if hasattr(workout, 'exercises') and workout.exercises:
                for exercise in workout.exercises:
                    if hasattr(exercise, 'to_dict'):
                        workout_dict['exercises'].append(exercise.to_dict())

        # Parse start_time to get date and time
        start_time = workout_dict.get('start_time')
        if start_time:
            if isinstance(start_time, (int, float)):
                # Unix timestamp
                dt = datetime.fromtimestamp(start_time)
            elif isinstance(start_time, str):
                dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            else:
                dt = start_time
            workout_dict['date'] = dt.date() if hasattr(dt, 'date') else None
            workout_dict['time'] = dt.time() if hasattr(dt, 'time') else None
        else:
            workout_dict['date'] = None
            workout_dict['time'] = None

        # Ensure exercises have proper structure
        exercises = workout_dict.get('exercises', [])
        parsed_exercises = []
        for exercise in exercises:
            exercise_dict = {
                'exercise_id': exercise.get('exercise_template_id'),
                'title': exercise.get('title'),
                'exercise_type': exercise.get('exercise_type'),
                'equipment_type': exercise.get('equipment_type'),
                'muscle_group': exercise.get('muscle_group'),
                'sets': []
            }

            # Parse sets
            sets = exercise.get('sets', [])
            for i, set_obj in enumerate(sets):
                if isinstance(set_obj, dict):
                    set_dict = {
                        'set_index': set_obj.get('index', i),
                        'set_type': set_obj.get('set_type'),
                        'weight_kg': set_obj.get('weight_kg'),
                        'reps': set_obj.get('reps'),
                        'distance_meters': set_obj.get('distance_meters'),
                        'duration_seconds': set_obj.get('duration_seconds'),
                        'rpe': set_obj.get('rpe'),
                    }
                    # Convert weight to lbs
                    if set_dict['weight_kg']:
                        set_dict['weight_lbs'] = round(set_dict['weight_kg'] * 2.20462, 2)
                    exercise_dict['sets'].append(set_dict)

            parsed_exercises.append(exercise_dict)

        workout_dict['exercises'] = parsed_exercises

        return workout_dict
