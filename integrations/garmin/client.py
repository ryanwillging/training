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

    # ==================== WELLNESS & RECOVERY DATA ====================

    def get_sleep_data(self, date_str: str) -> Dict[str, Any]:
        """
        Get sleep data for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Sleep data including duration, stages, score
        """
        self._ensure_authenticated()
        try:
            return self.client.get_sleep_data(date_str)
        except Exception as e:
            print(f"✗ Error fetching sleep data for {date_str}: {e}")
            return {}

    def get_stress_data(self, date_str: str) -> Dict[str, Any]:
        """
        Get stress data for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Stress level data throughout the day
        """
        self._ensure_authenticated()
        try:
            return self.client.get_stress_data(date_str)
        except Exception as e:
            print(f"✗ Error fetching stress data for {date_str}: {e}")
            return {}

    def get_body_battery(self, date_str: str) -> List[Dict[str, Any]]:
        """
        Get body battery data for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Body battery readings throughout the day
        """
        self._ensure_authenticated()
        try:
            return self.client.get_body_battery(date_str)
        except Exception as e:
            print(f"✗ Error fetching body battery for {date_str}: {e}")
            return []

    def get_resting_heart_rate(self, date_str: str) -> Dict[str, Any]:
        """
        Get resting heart rate for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Resting heart rate data
        """
        self._ensure_authenticated()
        try:
            return self.client.get_rhr_day(date_str)
        except Exception as e:
            print(f"✗ Error fetching resting HR for {date_str}: {e}")
            return {}

    def get_hrv_data(self, date_str: str) -> Dict[str, Any]:
        """
        Get heart rate variability data for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            HRV data including status and readings
        """
        self._ensure_authenticated()
        try:
            return self.client.get_hrv_data(date_str)
        except Exception as e:
            print(f"✗ Error fetching HRV data for {date_str}: {e}")
            return {}

    def get_respiration_data(self, date_str: str) -> Dict[str, Any]:
        """
        Get respiration/breathing rate data for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Respiration rate data
        """
        self._ensure_authenticated()
        try:
            return self.client.get_respiration_data(date_str)
        except Exception as e:
            print(f"✗ Error fetching respiration data for {date_str}: {e}")
            return {}

    def get_spo2_data(self, date_str: str) -> Dict[str, Any]:
        """
        Get blood oxygen saturation data for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            SpO2 readings
        """
        self._ensure_authenticated()
        try:
            return self.client.get_spo2_data(date_str)
        except Exception as e:
            print(f"✗ Error fetching SpO2 data for {date_str}: {e}")
            return {}

    # ==================== TRAINING & PERFORMANCE METRICS ====================

    def get_training_readiness(self, date_str: str) -> Dict[str, Any]:
        """
        Get training readiness score for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Training readiness data including score and factors
        """
        self._ensure_authenticated()
        try:
            return self.client.get_training_readiness(date_str)
        except Exception as e:
            print(f"✗ Error fetching training readiness for {date_str}: {e}")
            return {}

    def get_training_status(self, date_str: str) -> Dict[str, Any]:
        """
        Get training status for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Training status data (productive, maintaining, detraining, etc.)
        """
        self._ensure_authenticated()
        try:
            return self.client.get_training_status(date_str)
        except Exception as e:
            print(f"✗ Error fetching training status for {date_str}: {e}")
            return {}

    def get_max_metrics(self, date_str: str) -> Dict[str, Any]:
        """
        Get max metrics (VO2 max, etc.) for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Max metrics data including VO2 max estimates
        """
        self._ensure_authenticated()
        try:
            return self.client.get_max_metrics(date_str)
        except Exception as e:
            print(f"✗ Error fetching max metrics for {date_str}: {e}")
            return {}

    def get_race_predictions(self) -> Dict[str, Any]:
        """
        Get race time predictions based on fitness data.

        Returns:
            Predicted race times for various distances
        """
        self._ensure_authenticated()
        try:
            return self.client.get_race_predictions()
        except Exception as e:
            print(f"✗ Error fetching race predictions: {e}")
            return {}

    def get_personal_records(self) -> List[Dict[str, Any]]:
        """
        Get personal records across all activities.

        Returns:
            List of personal records
        """
        self._ensure_authenticated()
        try:
            return self.client.get_personal_record()
        except Exception as e:
            print(f"✗ Error fetching personal records: {e}")
            return []

    def get_endurance_score(self, date_str: str) -> Dict[str, Any]:
        """
        Get endurance score for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Endurance score data
        """
        self._ensure_authenticated()
        try:
            return self.client.get_endurance_score(date_str)
        except Exception as e:
            print(f"✗ Error fetching endurance score for {date_str}: {e}")
            return {}

    def get_hill_score(self, date_str: str) -> Dict[str, Any]:
        """
        Get hill/climb score for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Hill score data
        """
        self._ensure_authenticated()
        try:
            return self.client.get_hill_score(date_str)
        except Exception as e:
            print(f"✗ Error fetching hill score for {date_str}: {e}")
            return {}

    # ==================== BODY COMPOSITION ====================

    def get_body_composition(self, date_str: str) -> Dict[str, Any]:
        """
        Get body composition data for a specific date (requires Garmin scale).

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Body composition data (weight, body fat %, muscle mass, etc.)
        """
        self._ensure_authenticated()
        try:
            return self.client.get_body_composition(date_str)
        except Exception as e:
            print(f"✗ Error fetching body composition for {date_str}: {e}")
            return {}

    def get_weigh_ins(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Get weight measurements for a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            List of weigh-in records
        """
        self._ensure_authenticated()
        try:
            return self.client.get_weigh_ins(start_date, end_date)
        except Exception as e:
            print(f"✗ Error fetching weigh-ins: {e}")
            return []

    # ==================== DAILY SUMMARIES ====================

    def get_steps_data(self, date_str: str) -> Dict[str, Any]:
        """
        Get steps data for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Steps data including total, goal, distance
        """
        self._ensure_authenticated()
        try:
            return self.client.get_steps_data(date_str)
        except Exception as e:
            print(f"✗ Error fetching steps data for {date_str}: {e}")
            return {}

    def get_floors(self, date_str: str) -> Dict[str, Any]:
        """
        Get floors climbed data for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Floors climbed data
        """
        self._ensure_authenticated()
        try:
            return self.client.get_floors(date_str)
        except Exception as e:
            print(f"✗ Error fetching floors data for {date_str}: {e}")
            return {}

    def get_hydration_data(self, date_str: str) -> Dict[str, Any]:
        """
        Get hydration/water intake data for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Hydration data
        """
        self._ensure_authenticated()
        try:
            return self.client.get_hydration_data(date_str)
        except Exception as e:
            print(f"✗ Error fetching hydration data for {date_str}: {e}")
            return {}

    # ==================== AGGREGATED DATA ====================

    def get_daily_wellness(self, date_str: str) -> Dict[str, Any]:
        """
        Get all wellness data for a specific date in one call.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Combined wellness data dict
        """
        return {
            "date": date_str,
            "sleep": self.get_sleep_data(date_str),
            "stress": self.get_stress_data(date_str),
            "body_battery": self.get_body_battery(date_str),
            "resting_hr": self.get_resting_heart_rate(date_str),
            "hrv": self.get_hrv_data(date_str),
            "respiration": self.get_respiration_data(date_str),
            "spo2": self.get_spo2_data(date_str),
            "steps": self.get_steps_data(date_str),
            "training_readiness": self.get_training_readiness(date_str),
            "training_status": self.get_training_status(date_str),
        }

    def get_fitness_metrics(self, date_str: str) -> Dict[str, Any]:
        """
        Get all fitness/performance metrics for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Combined fitness metrics dict
        """
        return {
            "date": date_str,
            "max_metrics": self.get_max_metrics(date_str),
            "endurance_score": self.get_endurance_score(date_str),
            "hill_score": self.get_hill_score(date_str),
            "training_readiness": self.get_training_readiness(date_str),
            "training_status": self.get_training_status(date_str),
        }
