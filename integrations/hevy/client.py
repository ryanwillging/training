"""
Hevy API client wrapper.
Uses the hevy-api-client library to interact with Hevy's API.
"""

import os
from typing import Optional, List, Dict, Any
from datetime import date
from dotenv import load_dotenv

try:
    from hevy_api.client import HevyClient as HevyAPIClient
    from hevy_api.models.model import Workout
    HEVY_AVAILABLE = True
except ImportError:
    HEVY_AVAILABLE = False
    print("⚠ Warning: hevy-api-client not installed. Run: pip install hevy-api-client")

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

        self.api_key = api_key or os.getenv("HEVY_API_KEY")

        if not self.api_key:
            raise ValueError(
                "Hevy API key not provided. Set HEVY_API_KEY environment variable "
                "or pass it to the constructor."
            )

        # Set environment variable for hevy-api-client
        os.environ["HEVY_API_KEY"] = self.api_key

        try:
            self.client = HevyAPIClient()
            print(f"✓ Initialized Hevy API client")
        except Exception as e:
            print(f"✗ Failed to initialize Hevy client: {e}")
            raise

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
            response = self.client.get_workouts(page=page, pageSize=page_size)

            if hasattr(response, 'workouts') and response.workouts:
                # Convert Workout objects to dictionaries
                workouts = []
                for workout in response.workouts:
                    workout_dict = self._workout_to_dict(workout)
                    workouts.append(workout_dict)
                return workouts
            return []

        except Exception as e:
            print(f"✗ Error fetching workouts: {e}")
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
        page_size = 50  # Fetch more per page for efficiency

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
                            from datetime import datetime
                            workout_date = datetime.fromisoformat(workout_date.replace('Z', '+00:00')).date()

                        # Check date range
                        if start_date and workout_date < start_date:
                            # Workouts are sorted newest first, so we can stop
                            return all_workouts
                        if start_date and workout_date < start_date:
                            continue
                        if end_date and workout_date > end_date:
                            continue

                    all_workouts.append(workout)

                # Check if we got fewer than page_size (last page)
                if len(workouts) < page_size:
                    break

                page += 1

                # Safety check
                if len(all_workouts) > 1000:
                    print("⚠ Warning: Retrieved over 1000 workouts, stopping")
                    break

        except Exception as e:
            print(f"✗ Error fetching workouts: {e}")
            raise

        return all_workouts

    def get_workout_count(self) -> int:
        """
        Get total number of workouts.

        Returns:
            Workout count
        """
        try:
            response = self.client.get_workouts_count()
            if hasattr(response, 'workout_count'):
                return response.workout_count
            return 0
        except Exception as e:
            print(f"✗ Error fetching workout count: {e}")
            return 0

    def _workout_to_dict(self, workout: Any) -> Dict[str, Any]:
        """
        Convert Hevy Workout object to dictionary.

        Args:
            workout: Hevy Workout object

        Returns:
            Dictionary representation
        """
        workout_dict = {
            'id': getattr(workout, 'id', None),
            'title': getattr(workout, 'title', None),
            'description': getattr(workout, 'description', None),
            'start_time': getattr(workout, 'start_time', None),
            'end_time': getattr(workout, 'end_time', None),
            'created_at': getattr(workout, 'created_at', None),
            'updated_at': getattr(workout, 'updated_at', None),
        }

        # Parse start_time to get date
        if workout_dict['start_time']:
            from datetime import datetime
            if isinstance(workout_dict['start_time'], str):
                dt = datetime.fromisoformat(workout_dict['start_time'].replace('Z', '+00:00'))
            else:
                dt = workout_dict['start_time']
            workout_dict['date'] = dt.date()
            workout_dict['time'] = dt.time()
        else:
            workout_dict['date'] = None
            workout_dict['time'] = None

        # Get exercises if available
        if hasattr(workout, 'exercises') and workout.exercises:
            exercises = []
            for exercise in workout.exercises:
                exercise_dict = {
                    'exercise_id': getattr(exercise, 'exercise_template_id', None),
                    'title': getattr(exercise, 'title', None),
                    'exercise_type': getattr(exercise, 'exercise_type', None),
                    'equipment_type': getattr(exercise, 'equipment_type', None),
                    'muscle_group': getattr(exercise, 'muscle_group', None),
                }

                # Get sets if available
                if hasattr(exercise, 'sets') and exercise.sets:
                    sets = []
                    for set_obj in exercise.sets:
                        set_dict = {
                            'set_index': getattr(set_obj, 'index', None),
                            'set_type': getattr(set_obj, 'set_type', None),
                            'weight_kg': getattr(set_obj, 'weight_kg', None),
                            'reps': getattr(set_obj, 'reps', None),
                            'distance_meters': getattr(set_obj, 'distance_meters', None),
                            'duration_seconds': getattr(set_obj, 'duration_seconds', None),
                            'rpe': getattr(set_obj, 'rpe', None),
                        }

                        # Convert weight to lbs if available
                        if set_dict['weight_kg']:
                            set_dict['weight_lbs'] = round(set_dict['weight_kg'] * 2.20462, 2)

                        sets.append(set_dict)

                    exercise_dict['sets'] = sets

                exercises.append(exercise_dict)

            workout_dict['exercises'] = exercises

        return workout_dict
