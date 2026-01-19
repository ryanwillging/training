"""
Garmin wellness data importer.
Syncs sleep, stress, HRV, body battery, and training metrics.
"""

import json
from datetime import date, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from integrations.garmin.client import GarminClient
from database.models import DailyWellness, Athlete, ProgressMetric


class GarminWellnessImporter:
    """
    Import wellness data from Garmin Connect into the database.
    """

    def __init__(self, db: Session, athlete_id: int):
        self.db = db
        self.athlete_id = athlete_id
        self.client = GarminClient()

    def import_wellness_for_date(self, target_date: date) -> Tuple[bool, str]:
        """
        Import all wellness data for a specific date.

        Returns:
            Tuple of (success, message)
        """
        date_str = target_date.strftime("%Y-%m-%d")

        # Check if already imported
        existing = self.db.query(DailyWellness).filter(
            DailyWellness.athlete_id == self.athlete_id,
            DailyWellness.date == target_date
        ).first()

        try:
            # Fetch all wellness data
            sleep = self.client.get_sleep_data(date_str)
            stress = self.client.get_stress_data(date_str)
            body_battery = self.client.get_body_battery(date_str)
            rhr = self.client.get_resting_heart_rate(date_str)
            hrv = self.client.get_hrv_data(date_str)
            respiration = self.client.get_respiration_data(date_str)
            spo2 = self.client.get_spo2_data(date_str)
            steps = self.client.get_steps_data(date_str)
            training_readiness = self.client.get_training_readiness(date_str)
            training_status = self.client.get_training_status(date_str)
            max_metrics = self.client.get_max_metrics(date_str)
            user_summary = self.client.get_user_summary(date_str)

            # Parse wellness data
            wellness_data = self._parse_wellness_data(
                target_date, sleep, stress, body_battery, rhr, hrv,
                respiration, spo2, steps, training_readiness, training_status,
                max_metrics, user_summary
            )

            if existing:
                # Update existing record
                for key, value in wellness_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                self.db.commit()
                return True, f"Updated wellness for {date_str}"
            else:
                # Create new record
                wellness = DailyWellness(
                    athlete_id=self.athlete_id,
                    date=target_date,
                    **wellness_data
                )
                self.db.add(wellness)
                self.db.commit()
                return True, f"Imported wellness for {date_str}"

        except Exception as e:
            self.db.rollback()
            return False, f"Error importing wellness for {date_str}: {str(e)}"

    def _parse_wellness_data(
        self, target_date: date, sleep: Dict, stress: Dict, body_battery: Any,
        rhr: Dict, hrv: Dict, respiration: Dict, spo2: Dict, steps: Dict,
        training_readiness: Dict, training_status: Dict, max_metrics: Dict,
        user_summary: Dict
    ) -> Dict[str, Any]:
        """Parse raw Garmin data into wellness fields."""

        data = {}

        # Sleep data
        if sleep:
            daily_sleep = sleep.get("dailySleepDTO", {})
            data["sleep_score"] = daily_sleep.get("sleepScores", {}).get("overall", {}).get("value")
            data["sleep_duration_seconds"] = daily_sleep.get("sleepTimeSeconds")
            data["sleep_deep_seconds"] = daily_sleep.get("deepSleepSeconds")
            data["sleep_light_seconds"] = daily_sleep.get("lightSleepSeconds")
            data["sleep_rem_seconds"] = daily_sleep.get("remSleepSeconds")
            data["sleep_awake_seconds"] = daily_sleep.get("awakeSleepSeconds")

        # Body battery (list with daily summaries containing bodyBatteryValuesArray)
        if body_battery and isinstance(body_battery, list) and len(body_battery) > 0:
            bb_day = body_battery[0]  # Get today's data
            if isinstance(bb_day, dict):
                # Extract values from bodyBatteryValuesArray [[timestamp, level], ...]
                values_array = bb_day.get("bodyBatteryValuesArray", [])
                if values_array:
                    bb_values = [v[1] for v in values_array if isinstance(v, list) and len(v) > 1]
                    if bb_values:
                        data["body_battery_high"] = max(bb_values)
                        data["body_battery_low"] = min(bb_values)
                        # Current is the most recent reading (last in array)
                        data["body_battery_current"] = bb_values[-1]
                # Get charged/drained values directly from summary
                data["body_battery_charged"] = bb_day.get("charged")
                data["body_battery_drained"] = bb_day.get("drained")

        # Training readiness (may be a list)
        if training_readiness:
            tr = training_readiness
            if isinstance(training_readiness, list) and len(training_readiness) > 0:
                tr = training_readiness[0]  # Use most recent
            if isinstance(tr, dict):
                data["training_readiness_score"] = tr.get("score")
                data["training_readiness_status"] = tr.get("level")

        # Stress
        if stress:
            data["avg_stress_level"] = stress.get("avgStressLevel") or stress.get("overallStressLevel")
            data["max_stress_level"] = stress.get("maxStressLevel")
            data["stress_duration_seconds"] = stress.get("highStressDuration")
            data["rest_duration_seconds"] = stress.get("restStressDuration")

        # Resting heart rate
        if rhr:
            data["resting_heart_rate"] = rhr.get("restingHeartRate") or rhr.get("value")

        # HRV
        if hrv:
            hrv_summary = hrv.get("hrvSummary", {})
            data["hrv_weekly_avg"] = hrv_summary.get("weeklyAvg")
            data["hrv_last_night"] = hrv_summary.get("lastNightAvg") or hrv_summary.get("lastNight5MinHigh")
            data["hrv_status"] = hrv_summary.get("status") or hrv.get("status")

        # Respiration
        if respiration:
            data["avg_respiration_rate"] = respiration.get("avgWakingRespirationValue")

        # SpO2
        if spo2:
            data["avg_spo2"] = spo2.get("avgSleepSpo2") or spo2.get("latestSpo2Value")

        # Steps and activity (steps may be a list of intervals)
        if steps:
            if isinstance(steps, list):
                # Sum steps from all intervals
                total_steps = sum(s.get("steps", 0) for s in steps if isinstance(s, dict))
                data["steps"] = total_steps if total_steps > 0 else None
            elif isinstance(steps, dict):
                data["steps"] = steps.get("totalSteps")
        if user_summary:
            data["steps"] = data.get("steps") or user_summary.get("totalSteps")
            data["floors_climbed"] = user_summary.get("floorsAscended")
            data["active_calories"] = user_summary.get("activeKilocalories")
            data["total_calories"] = user_summary.get("totalKilocalories")

        # Training status
        if training_status:
            data["training_status"] = training_status.get("trainingStatusPhrase") or training_status.get("status")
            data["training_load"] = training_status.get("currentLoad")

        # Max metrics (VO2 max) - may be a list or dict
        if max_metrics:
            mm = max_metrics
            if isinstance(max_metrics, list) and len(max_metrics) > 0:
                mm = max_metrics[0]  # Use first item
            if isinstance(mm, dict):
                generic = mm.get("generic", {})
                data["vo2_max_running"] = generic.get("vo2MaxPreciseValue") or generic.get("vo2MaxValue")
                cycling = mm.get("cycling", {})
                data["vo2_max_cycling"] = cycling.get("vo2MaxPreciseValue") or cycling.get("vo2MaxValue")

        # Store raw data for future use
        raw_data = {
            "sleep": sleep,
            "stress": stress,
            "hrv": hrv,
            "training_readiness": training_readiness,
            "training_status": training_status,
            "max_metrics": max_metrics,
        }
        data["raw_data_json"] = json.dumps(raw_data, default=str)

        return data

    def import_recent_wellness(self, days: int = 7) -> Tuple[int, int, list]:
        """
        Import wellness data for the last N days.

        Returns:
            Tuple of (imported_count, skipped_count, errors)
        """
        imported = 0
        skipped = 0
        errors = []

        today = date.today()

        for i in range(days):
            target_date = today - timedelta(days=i)
            success, message = self.import_wellness_for_date(target_date)

            if success:
                if "Updated" in message:
                    skipped += 1
                else:
                    imported += 1
            else:
                errors.append(message)

        return imported, skipped, errors

    def update_athlete_metrics(self) -> None:
        """
        Update athlete's current metrics from latest wellness data.
        """
        # Get latest wellness record
        latest = self.db.query(DailyWellness).filter(
            DailyWellness.athlete_id == self.athlete_id
        ).order_by(DailyWellness.date.desc()).first()

        if not latest:
            return

        athlete = self.db.query(Athlete).filter(Athlete.id == self.athlete_id).first()
        if not athlete:
            return

        # Update VO2 max if available
        if latest.vo2_max_running:
            athlete.current_vo2_max = int(latest.vo2_max_running)

            # Also store as progress metric
            existing_metric = self.db.query(ProgressMetric).filter(
                ProgressMetric.athlete_id == self.athlete_id,
                ProgressMetric.metric_type == "vo2_max",
                ProgressMetric.metric_date == latest.date
            ).first()

            if not existing_metric:
                metric = ProgressMetric(
                    athlete_id=self.athlete_id,
                    metric_date=latest.date,
                    metric_type="vo2_max",
                    value_numeric=latest.vo2_max_running,
                    measurement_method="garmin_estimate",
                    notes="Auto-synced from Garmin"
                )
                self.db.add(metric)

        self.db.commit()
