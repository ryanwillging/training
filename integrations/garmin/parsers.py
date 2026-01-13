"""
Parsers for converting Garmin API data into our database format.
Handles different activity types: swimming, running, cycling, etc.
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime, date, time


class GarminActivityParser:
    """Base parser for Garmin activities."""

    @staticmethod
    def parse_base_activity(activity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse common fields from any Garmin activity.

        Args:
            activity: Raw activity data from Garmin API

        Returns:
            Dictionary with standardized activity data
        """
        # Parse activity date and time
        start_time_str = activity.get('startTimeLocal', activity.get('startTimeGMT', ''))
        if start_time_str:
            start_dt = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            activity_date = start_dt.date()
            activity_time = start_dt.time()
        else:
            activity_date = date.today()
            activity_time = None

        # Get activity type
        activity_type_obj = activity.get('activityType', {})
        activity_type_key = activity_type_obj.get('typeKey', 'unknown')

        # Map Garmin activity types to our types
        type_mapping = {
            'lap_swimming': 'swim',
            'open_water_swimming': 'swim',
            'swimming': 'swim',
            'running': 'run',
            'cycling': 'bike',
            'indoor_cycling': 'bike',
            'strength_training': 'strength',
            'cardio_training': 'other',
            'multi_sport': 'other',
        }
        our_activity_type = type_mapping.get(activity_type_key, 'other')

        return {
            'external_id': str(activity.get('activityId')),
            'activity_date': activity_date,
            'activity_time': activity_time,
            'activity_type': our_activity_type,
            'activity_name': activity.get('activityName', ''),
            'duration_minutes': int(activity.get('duration', 0) / 60) if activity.get('duration') else None,
        }


class SwimActivityParser(GarminActivityParser):
    """Parser for swimming activities."""

    @staticmethod
    def parse(activity: Dict[str, Any], splits: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Parse a swimming activity from Garmin.

        Args:
            activity: Raw activity data from Garmin API
            splits: Optional lap/split data

        Returns:
            Dictionary with activity data in our format
        """
        base_data = GarminActivityParser.parse_base_activity(activity)

        # Swimming-specific data
        swim_data = {
            'activity_type': 'swim',
            'pool_length_meters': activity.get('poolLength'),
            'pool_length_unit': '25y' if activity.get('poolLength') == 22.86 else '25m',  # Approximate
            'duration_seconds': activity.get('duration'),
            'distance_meters': activity.get('distance'),
            'calories': activity.get('calories'),
            'avg_heart_rate': activity.get('averageHR'),
            'max_heart_rate': activity.get('maxHR'),
        }

        # Calculate pace if distance available
        if swim_data['duration_seconds'] and swim_data['distance_meters']:
            # Pace per 100 yards/meters
            pace_seconds_per_100 = (swim_data['duration_seconds'] / swim_data['distance_meters']) * 100
            minutes = int(pace_seconds_per_100 // 60)
            seconds = int(pace_seconds_per_100 % 60)
            swim_data['avg_pace_per_100y'] = f"{minutes}:{seconds:02d}"

        # Parse laps if available
        if splits:
            laps = []
            for i, lap in enumerate(splits, 1):
                lap_data = {
                    'lap_number': i,
                    'distance_meters': lap.get('distance'),
                    'duration_seconds': lap.get('duration'),
                    'stroke_type': lap.get('swimStroke', 'unknown'),
                    'avg_heart_rate': lap.get('averageHR'),
                }

                # Calculate lap pace
                if lap_data['duration_seconds'] and lap_data['distance_meters']:
                    lap_pace = (lap_data['duration_seconds'] / lap_data['distance_meters']) * 100
                    lap_minutes = int(lap_pace // 60)
                    lap_seconds = int(lap_pace % 60)
                    lap_data['pace_per_100y'] = f"{lap_minutes}:{lap_seconds:02d}"

                laps.append(lap_data)

            swim_data['laps'] = laps

        # Store as JSON string
        activity_data = {
            **base_data,
            'activity_data': json.dumps(swim_data),
        }

        return activity_data


class RunActivityParser(GarminActivityParser):
    """Parser for running activities."""

    @staticmethod
    def parse(activity: Dict[str, Any], splits: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Parse a running activity from Garmin.

        Args:
            activity: Raw activity data from Garmin API
            splits: Optional lap/split data

        Returns:
            Dictionary with activity data in our format
        """
        base_data = GarminActivityParser.parse_base_activity(activity)

        # Running-specific data
        run_data = {
            'activity_type': 'run',
            'duration_seconds': activity.get('duration'),
            'distance_meters': activity.get('distance'),
            'calories': activity.get('calories'),
            'avg_heart_rate': activity.get('averageHR'),
            'max_heart_rate': activity.get('maxHR'),
            'avg_speed': activity.get('averageSpeed'),  # m/s
            'max_speed': activity.get('maxSpeed'),
            'elevation_gain': activity.get('elevationGain'),
            'elevation_loss': activity.get('elevationLoss'),
            'vo2_max_estimate': activity.get('vO2MaxValue'),
        }

        # Calculate pace per mile
        if run_data['duration_seconds'] and run_data['distance_meters']:
            distance_miles = run_data['distance_meters'] / 1609.34
            pace_seconds_per_mile = run_data['duration_seconds'] / distance_miles
            minutes = int(pace_seconds_per_mile // 60)
            seconds = int(pace_seconds_per_mile % 60)
            run_data['avg_pace_per_mile'] = f"{minutes}:{seconds:02d}"

        # Parse splits if available
        if splits:
            intervals = []
            for i, split in enumerate(splits, 1):
                split_data = {
                    'split_number': i,
                    'distance_meters': split.get('distance'),
                    'duration_seconds': split.get('duration'),
                    'avg_heart_rate': split.get('averageHR'),
                    'avg_speed': split.get('averageSpeed'),
                    'elevation_gain': split.get('elevationGain'),
                }
                intervals.append(split_data)

            run_data['splits'] = intervals

        # Store as JSON string
        activity_data = {
            **base_data,
            'activity_data': json.dumps(run_data),
        }

        return activity_data


class BikeActivityParser(GarminActivityParser):
    """Parser for cycling activities."""

    @staticmethod
    def parse(activity: Dict[str, Any], splits: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Parse a cycling activity from Garmin.

        Args:
            activity: Raw activity data from Garmin API
            splits: Optional lap/split data

        Returns:
            Dictionary with activity data in our format
        """
        base_data = GarminActivityParser.parse_base_activity(activity)

        # Cycling-specific data
        bike_data = {
            'activity_type': 'bike',
            'duration_seconds': activity.get('duration'),
            'distance_meters': activity.get('distance'),
            'calories': activity.get('calories'),
            'avg_heart_rate': activity.get('averageHR'),
            'max_heart_rate': activity.get('maxHR'),
            'avg_speed': activity.get('averageSpeed'),  # m/s
            'max_speed': activity.get('maxSpeed'),
            'avg_cadence': activity.get('averageBikingCadenceInRevPerMinute'),
            'max_cadence': activity.get('maxBikingCadenceInRevPerMinute'),
            'elevation_gain': activity.get('elevationGain'),
            'elevation_loss': activity.get('elevationLoss'),
        }

        # Calculate average speed in mph
        if bike_data['avg_speed']:
            bike_data['avg_speed_mph'] = round(bike_data['avg_speed'] * 2.23694, 2)

        # Parse splits if available
        if splits:
            intervals = []
            for i, split in enumerate(splits, 1):
                split_data = {
                    'split_number': i,
                    'distance_meters': split.get('distance'),
                    'duration_seconds': split.get('duration'),
                    'avg_heart_rate': split.get('averageHR'),
                    'avg_speed': split.get('averageSpeed'),
                    'avg_cadence': split.get('averageBikingCadenceInRevPerMinute'),
                }
                intervals.append(split_data)

            bike_data['splits'] = intervals

        # Store as JSON string
        activity_data = {
            **base_data,
            'activity_data': json.dumps(bike_data),
        }

        return activity_data


class StrengthActivityParser(GarminActivityParser):
    """Parser for strength training activities."""

    @staticmethod
    def parse(activity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a strength training activity from Garmin.

        Note: Garmin doesn't provide detailed exercise/set data via API,
        so this is limited to duration and calories.

        Args:
            activity: Raw activity data from Garmin API

        Returns:
            Dictionary with activity data in our format
        """
        base_data = GarminActivityParser.parse_base_activity(activity)

        # Strength-specific data (limited from Garmin API)
        strength_data = {
            'activity_type': 'strength',
            'duration_seconds': activity.get('duration'),
            'calories': activity.get('calories'),
            'avg_heart_rate': activity.get('averageHR'),
            'max_heart_rate': activity.get('maxHR'),
            'notes': 'Imported from Garmin (limited detail - use Hevy for detailed strength tracking)',
        }

        # Store as JSON string
        activity_data = {
            **base_data,
            'activity_data': json.dumps(strength_data),
        }

        return activity_data


def parse_garmin_activity(
    activity: Dict[str, Any],
    splits: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Parse a Garmin activity based on its type.

    Args:
        activity: Raw activity data from Garmin API
        splits: Optional lap/split data

    Returns:
        Dictionary with activity data in our format
    """
    activity_type_obj = activity.get('activityType', {})
    activity_type_key = activity_type_obj.get('typeKey', 'unknown')

    # Select appropriate parser
    if 'swimming' in activity_type_key.lower():
        return SwimActivityParser.parse(activity, splits)
    elif 'running' in activity_type_key.lower():
        return RunActivityParser.parse(activity, splits)
    elif 'cycling' in activity_type_key.lower():
        return BikeActivityParser.parse(activity, splits)
    elif 'strength' in activity_type_key.lower():
        return StrengthActivityParser.parse(activity)
    else:
        # Default to base parser for unknown types
        base_data = GarminActivityParser.parse_base_activity(activity)
        base_data['activity_data'] = json.dumps({
            'activity_type': 'other',
            'duration_seconds': activity.get('duration'),
            'distance_meters': activity.get('distance'),
            'calories': activity.get('calories'),
            'raw_type': activity_type_key,
        })
        return base_data
