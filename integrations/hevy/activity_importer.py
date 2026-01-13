"""
Hevy activity importer.
Fetches strength training workouts from Hevy and stores them in the database.
"""

import json
from typing import Optional, List, Tuple
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from integrations.hevy.client import HevyClient
from database.models import CompletedActivity, Athlete


class HevyActivityImporter:
    """
    Imports strength training workouts from Hevy into the database.
    """

    def __init__(self, db: Session, athlete_id: int):
        """
        Initialize importer.

        Args:
            db: Database session
            athlete_id: ID of athlete to import workouts for
        """
        self.db = db
        self.athlete_id = athlete_id

        # Verify athlete exists
        athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()
        if not athlete:
            raise ValueError(f"Athlete with ID {athlete_id} not found")

        try:
            self.client = HevyClient()
        except Exception as e:
            print(f"✗ Failed to initialize Hevy client: {e}")
            raise

    def import_workouts(
        self,
        start_date: date,
        end_date: date
    ) -> Tuple[int, int, List[str]]:
        """
        Import workouts from Hevy for a date range.

        Args:
            start_date: Start date for import
            end_date: End date for import

        Returns:
            Tuple of (imported_count, skipped_count, error_messages)
        """
        print(f"Importing Hevy workouts from {start_date} to {end_date}...")

        # Fetch workouts
        try:
            workouts = self.client.get_all_workouts(start_date, end_date)
            print(f"Found {len(workouts)} workouts")
        except Exception as e:
            return (0, 0, [f"Failed to fetch workouts: {e}"])

        imported_count = 0
        skipped_count = 0
        errors = []

        for workout in workouts:
            try:
                workout_id = workout.get('id')
                if not workout_id:
                    errors.append("Workout missing ID, skipping")
                    skipped_count += 1
                    continue

                # Check if workout already exists
                existing = self.db.query(CompletedActivity).filter(
                    CompletedActivity.athlete_id == self.athlete_id,
                    CompletedActivity.source == 'hevy',
                    CompletedActivity.external_id == str(workout_id)
                ).first()

                if existing:
                    skipped_count += 1
                    continue

                # Parse workout data
                parsed_data = self._parse_hevy_workout(workout)

                # Create database record
                completed_activity = CompletedActivity(
                    athlete_id=self.athlete_id,
                    source='hevy',
                    external_id=str(workout_id),
                    activity_date=parsed_data['activity_date'],
                    activity_time=parsed_data['activity_time'],
                    activity_type='strength',
                    activity_name=parsed_data['activity_name'],
                    duration_minutes=parsed_data['duration_minutes'],
                    activity_data=parsed_data['activity_data'],
                )

                self.db.add(completed_activity)
                self.db.commit()
                imported_count += 1

                print(f"✓ Imported: {parsed_data['activity_name']} - {parsed_data['activity_date']}")

            except IntegrityError as e:
                self.db.rollback()
                errors.append(f"Duplicate workout {workout_id}: {e}")
                skipped_count += 1
            except Exception as e:
                self.db.rollback()
                errors.append(f"Error importing workout {workout.get('id')}: {e}")
                skipped_count += 1

        print(f"\nImport complete: {imported_count} imported, {skipped_count} skipped")
        if errors:
            print(f"Errors: {len(errors)}")

        return (imported_count, skipped_count, errors)

    def import_recent_workouts(self, days: int = 7) -> Tuple[int, int, List[str]]:
        """
        Import workouts from the last N days.

        Args:
            days: Number of days to look back

        Returns:
            Tuple of (imported_count, skipped_count, error_messages)
        """
        end_date = date.today()
        start_date = date.today() - timedelta(days=days)
        return self.import_workouts(start_date, end_date)

    def _parse_hevy_workout(self, workout: dict) -> dict:
        """
        Parse a Hevy workout into our database format.

        Args:
            workout: Hevy workout dictionary

        Returns:
            Dictionary with parsed data
        """
        # Extract basic info
        workout_date = workout.get('date') or date.today()
        workout_time = workout.get('time')
        workout_title = workout.get('title') or 'Strength Training'

        # Calculate duration
        start_time = workout.get('start_time')
        end_time = workout.get('end_time')
        duration_minutes = None

        if start_time and end_time:
            if isinstance(start_time, str):
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            else:
                start_dt = start_time

            if isinstance(end_time, str):
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            else:
                end_dt = end_time

            duration = end_dt - start_dt
            duration_minutes = int(duration.total_seconds() / 60)

        # Parse exercises
        exercises_data = []
        exercises = workout.get('exercises', [])
        total_volume_lbs = 0

        for exercise in exercises:
            exercise_name = exercise.get('title', 'Unknown Exercise')
            exercise_data = {
                'exercise_name': exercise_name,
                'exercise_type': exercise.get('exercise_type'),
                'equipment_type': exercise.get('equipment_type'),
                'muscle_group': exercise.get('muscle_group'),
                'sets': []
            }

            # Parse sets
            sets = exercise.get('sets', [])
            for set_info in sets:
                set_data = {
                    'set_number': set_info.get('set_index', 0) + 1,
                    'reps': set_info.get('reps'),
                    'weight_lbs': set_info.get('weight_lbs'),
                    'weight_kg': set_info.get('weight_kg'),
                    'rpe': set_info.get('rpe'),
                    'distance_meters': set_info.get('distance_meters'),
                    'duration_seconds': set_info.get('duration_seconds'),
                }

                # Calculate volume (weight * reps)
                if set_data['weight_lbs'] and set_data['reps']:
                    set_volume = set_data['weight_lbs'] * set_data['reps']
                    total_volume_lbs += set_volume

                exercise_data['sets'].append(set_data)

            exercises_data.append(exercise_data)

        # Compile activity data
        activity_data = {
            'activity_type': 'strength',
            'title': workout_title,
            'description': workout.get('description'),
            'duration_minutes': duration_minutes,
            'exercises': exercises_data,
            'total_volume_lbs': round(total_volume_lbs, 2),
            'exercise_count': len(exercises_data),
            'notes': workout.get('description') or '',
        }

        return {
            'activity_date': workout_date,
            'activity_time': workout_time,
            'activity_name': workout_title,
            'duration_minutes': duration_minutes,
            'activity_data': json.dumps(activity_data),
        }
