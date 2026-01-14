"""
Garmin activity importer.
Fetches activities from Garmin Connect and stores them in the database.
"""

from typing import Optional, List, Tuple
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from integrations.garmin.client import GarminClient
from integrations.garmin.parsers import parse_garmin_activity
from database.models import CompletedActivity, Athlete


class GarminActivityImporter:
    """
    Imports activities from Garmin Connect into the database.
    """

    def __init__(self, db: Session, athlete_id: int):
        """
        Initialize importer.

        Args:
            db: Database session
            athlete_id: ID of athlete to import activities for
        """
        self.db = db
        self.athlete_id = athlete_id
        self.client = GarminClient()

        # Verify athlete exists
        athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()
        if not athlete:
            raise ValueError(f"Athlete with ID {athlete_id} not found")

    def import_activities(
        self,
        start_date: date,
        end_date: date,
        activity_type: Optional[str] = None,
        fetch_splits: bool = True
    ) -> Tuple[int, int, List[str]]:
        """
        Import activities from Garmin Connect for a date range.

        Args:
            start_date: Start date for import
            end_date: End date for import
            activity_type: Optional filter by Garmin activity type
            fetch_splits: Whether to fetch detailed lap/split data

        Returns:
            Tuple of (imported_count, skipped_count, error_messages)
        """
        print(f"Importing Garmin activities from {start_date} to {end_date}...")

        # Authenticate with Garmin
        try:
            self.client.authenticate()
        except Exception as e:
            return (0, 0, [f"Authentication failed: {e}"])

        # Fetch activities
        try:
            activities = self.client.get_activities(start_date, end_date, activity_type)
            print(f"Found {len(activities)} activities")
        except Exception as e:
            return (0, 0, [f"Failed to fetch activities: {e}"])

        imported_count = 0
        skipped_count = 0
        errors = []

        for activity in activities:
            try:
                activity_id = activity.get('activityId')
                if not activity_id:
                    errors.append("Activity missing ID, skipping")
                    skipped_count += 1
                    continue

                # Check if activity already exists
                existing = self.db.query(CompletedActivity).filter(
                    CompletedActivity.athlete_id == self.athlete_id,
                    CompletedActivity.source == 'garmin',
                    CompletedActivity.external_id == str(activity_id)
                ).first()

                if existing:
                    skipped_count += 1
                    continue

                # Fetch splits if requested and activity type supports it
                splits = None
                activity_type_key = activity.get('activityType', {}).get('typeKey', '')
                if fetch_splits and activity_type_key in ['lap_swimming', 'running', 'cycling']:
                    try:
                        splits = self.client.get_activity_splits(activity_id)
                    except Exception as e:
                        # Continue without splits if fetch fails
                        errors.append(f"Failed to fetch splits for activity {activity_id}: {e}")

                # Parse activity
                parsed_data = parse_garmin_activity(activity, splits)

                # Create database record
                completed_activity = CompletedActivity(
                    athlete_id=self.athlete_id,
                    source='garmin',
                    external_id=parsed_data['external_id'],
                    activity_date=parsed_data['activity_date'],
                    activity_time=parsed_data['activity_time'],
                    activity_type=parsed_data['activity_type'],
                    activity_name=parsed_data['activity_name'],
                    duration_minutes=parsed_data['duration_minutes'],
                    activity_data=parsed_data['activity_data'],
                )

                self.db.add(completed_activity)
                self.db.commit()
                imported_count += 1

                print(f"✓ Imported: {parsed_data['activity_name']} ({parsed_data['activity_type']}) - {parsed_data['activity_date']}")

            except IntegrityError as e:
                self.db.rollback()
                errors.append(f"Duplicate activity {activity_id}: {e}")
                skipped_count += 1
            except Exception as e:
                self.db.rollback()
                errors.append(f"Error importing activity {activity.get('activityId')}: {e}")
                skipped_count += 1

        print(f"\nImport complete: {imported_count} imported, {skipped_count} skipped")
        if errors:
            print(f"Errors: {len(errors)}")

        return (imported_count, skipped_count, errors)

    def import_recent_activities(self, days: int = 7) -> Tuple[int, int, List[str]]:
        """
        Import activities from the last N days.

        Args:
            days: Number of days to look back

        Returns:
            Tuple of (imported_count, skipped_count, error_messages)
        """
        end_date = date.today()
        start_date = date.today() - timedelta(days=days)
        return self.import_activities(start_date, end_date)

    def import_activity_by_id(self, activity_id: int) -> bool:
        """
        Import a specific activity by its Garmin ID.

        Args:
            activity_id: Garmin activity ID

        Returns:
            True if imported, False if already exists or failed
        """
        # Check if already exists
        existing = self.db.query(CompletedActivity).filter(
            CompletedActivity.athlete_id == self.athlete_id,
            CompletedActivity.source == 'garmin',
            CompletedActivity.external_id == str(activity_id)
        ).first()

        if existing:
            print(f"Activity {activity_id} already exists")
            return False

        try:
            # Authenticate
            self.client.authenticate()

            # Fetch activity details
            activity = self.client.get_activity_details(activity_id)

            # Fetch splits
            splits = None
            activity_type_key = activity.get('activityType', {}).get('typeKey', '')
            if activity_type_key in ['lap_swimming', 'running', 'cycling']:
                try:
                    splits = self.client.get_activity_splits(activity_id)
                except Exception:
                    pass  # Continue without splits

            # Parse activity
            parsed_data = parse_garmin_activity(activity, splits)

            # Create database record
            completed_activity = CompletedActivity(
                athlete_id=self.athlete_id,
                source='garmin',
                external_id=parsed_data['external_id'],
                activity_date=parsed_data['activity_date'],
                activity_time=parsed_data['activity_time'],
                activity_type=parsed_data['activity_type'],
                activity_name=parsed_data['activity_name'],
                duration_minutes=parsed_data['duration_minutes'],
                activity_data=parsed_data['activity_data'],
            )

            self.db.add(completed_activity)
            self.db.commit()

            print(f"✓ Imported activity {activity_id}: {parsed_data['activity_name']}")
            return True

        except Exception as e:
            self.db.rollback()
            print(f"✗ Error importing activity {activity_id}: {e}")
            return False
