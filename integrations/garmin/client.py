"""
Garmin Connect API client wrapper.
Handles authentication and API calls to Garmin Connect.
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from garminconnect import Garmin, GarminConnectConnectionError, GarminConnectAuthenticationError
from dotenv import load_dotenv

load_dotenv()


class GarminClient:
    """
    Wrapper around python-garminconnect for easier use in our application.
    Handles authentication, session management, and API calls.
    """

    def __init__(self, email: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize Garmin client.

        Args:
            email: Garmin Connect email (defaults to GARMIN_EMAIL env var)
            password: Garmin Connect password (defaults to GARMIN_PASSWORD env var)
        """
        self.email = email or os.getenv("GARMIN_EMAIL")
        self.password = password or os.getenv("GARMIN_PASSWORD")

        if not self.email or not self.password:
            raise ValueError(
                "Garmin credentials not provided. Set GARMIN_EMAIL and GARMIN_PASSWORD "
                "environment variables or pass them to the constructor."
            )

        self.client: Optional[Garmin] = None
        self._authenticated = False

    def authenticate(self) -> bool:
        """
        Authenticate with Garmin Connect.

        Returns:
            True if authentication successful, False otherwise

        Raises:
            GarminConnectAuthenticationError: If credentials are invalid
            GarminConnectConnectionError: If connection fails
        """
        try:
            self.client = Garmin(self.email, self.password)
            self.client.login()
            self._authenticated = True
            print(f"✓ Authenticated with Garmin Connect as {self.email}")
            return True
        except GarminConnectAuthenticationError as e:
            print(f"✗ Garmin authentication failed: {e}")
            raise
        except GarminConnectConnectionError as e:
            print(f"✗ Garmin connection failed: {e}")
            raise

    def _ensure_authenticated(self):
        """Ensure client is authenticated before making API calls."""
        if not self._authenticated or not self.client:
            self.authenticate()

    def get_activities(
        self,
        start_date: date,
        end_date: date,
        activity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get activities for a date range.

        Args:
            start_date: Start date for activity search
            end_date: End date for activity search
            activity_type: Optional filter by activity type (e.g., 'swimming', 'running')

        Returns:
            List of activity dictionaries
        """
        self._ensure_authenticated()

        activities = []
        start = 0
        limit = 100  # Garmin API limit per request

        try:
            while True:
                batch = self.client.get_activities(start, limit)
                if not batch:
                    break

                for activity in batch:
                    # Parse activity date
                    activity_date_str = activity.get('startTimeLocal', '')
                    if activity_date_str:
                        activity_date = datetime.fromisoformat(
                            activity_date_str.replace('Z', '+00:00')
                        ).date()

                        # Filter by date range
                        if activity_date < start_date:
                            # Activities are sorted newest first, so we can stop
                            return activities
                        if activity_date <= end_date:
                            # Filter by activity type if specified
                            if activity_type is None or activity.get('activityType', {}).get('typeKey') == activity_type:
                                activities.append(activity)

                start += limit

                # Safety check to prevent infinite loops
                if len(activities) > 1000:
                    print("⚠ Warning: Retrieved over 1000 activities, stopping to prevent excessive API calls")
                    break

        except Exception as e:
            print(f"✗ Error fetching activities: {e}")
            raise

        return activities

    def get_activity_details(self, activity_id: int) -> Dict[str, Any]:
        """
        Get detailed information for a specific activity.

        Args:
            activity_id: Garmin activity ID

        Returns:
            Activity details dictionary
        """
        self._ensure_authenticated()

        try:
            details = self.client.get_activity(activity_id)
            return details
        except Exception as e:
            print(f"✗ Error fetching activity {activity_id}: {e}")
            raise

    def get_activity_splits(self, activity_id: int) -> List[Dict[str, Any]]:
        """
        Get splits/laps for a specific activity.

        Args:
            activity_id: Garmin activity ID

        Returns:
            List of split/lap dictionaries
        """
        self._ensure_authenticated()

        try:
            splits_response = self.client.get_activity_splits(activity_id)
            # Garmin API returns a dict with lapDTOs - extract the laps list
            if isinstance(splits_response, dict):
                return splits_response.get('lapDTOs', [])
            return splits_response if splits_response else []
        except Exception as e:
            print(f"✗ Error fetching splits for activity {activity_id}: {e}")
            raise

    def get_user_summary(self, date_str: str) -> Dict[str, Any]:
        """
        Get user summary for a specific date (steps, calories, etc.).

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            User summary dictionary
        """
        self._ensure_authenticated()

        try:
            summary = self.client.get_user_summary(date_str)
            return summary
        except Exception as e:
            print(f"✗ Error fetching user summary for {date_str}: {e}")
            raise

    def get_stats(self, date_str: str) -> Dict[str, Any]:
        """
        Get stats for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Stats dictionary
        """
        self._ensure_authenticated()

        try:
            stats = self.client.get_stats(date_str)
            return stats
        except Exception as e:
            print(f"✗ Error fetching stats for {date_str}: {e}")
            raise

    def get_heart_rates(self, date_str: str) -> Dict[str, Any]:
        """
        Get heart rate data for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Heart rate data dictionary
        """
        self._ensure_authenticated()

        try:
            hr_data = self.client.get_heart_rates(date_str)
            return hr_data
        except Exception as e:
            print(f"✗ Error fetching heart rates for {date_str}: {e}")
            raise

    def upload_activity(self, file_path: str, activity_format: str = ".fit") -> Dict[str, Any]:
        """
        Upload an activity file (FIT, GPX, TCX) to Garmin Connect.

        Args:
            file_path: Path to activity file
            activity_format: File format (.fit, .gpx, .tcx)

        Returns:
            Upload response dictionary
        """
        self._ensure_authenticated()

        try:
            with open(file_path, 'rb') as f:
                response = self.client.upload_activity(f, activity_format)
            print(f"✓ Uploaded activity from {file_path}")
            return response
        except Exception as e:
            print(f"✗ Error uploading activity: {e}")
            raise
