"""
API routes for wellness data retrieval.
"""

import os
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.base import get_db
from database.models import DailyWellness
from api.timezone import get_eastern_today

router = APIRouter(prefix="/wellness", tags=["wellness"])


def _serialize_wellness(w: DailyWellness) -> dict:
    """Serialize a DailyWellness record to JSON-friendly dict."""
    return {
        "date": str(w.date),
        "hrv": w.hrv_last_night,
        "resting_heart_rate": w.resting_heart_rate,
        "body_battery": w.body_battery_current,
        "sleep_score": w.sleep_score,
        "sleep_duration_hours": round(w.sleep_duration_seconds / 3600, 2) if w.sleep_duration_seconds else None,
        "rem_sleep_minutes": round(w.sleep_rem_seconds / 60) if w.sleep_rem_seconds else None,
        "deep_sleep_minutes": round(w.sleep_deep_seconds / 60) if w.sleep_deep_seconds else None,
        "light_sleep_minutes": round(w.sleep_light_seconds / 60) if w.sleep_light_seconds else None,
        "awake_minutes": round(w.sleep_awake_seconds / 60) if w.sleep_awake_seconds else None,
        "stress_level": w.avg_stress_level,
        "steps": w.steps,
        "active_calories": w.active_calories,
        "training_readiness": w.training_readiness_score,
        "training_status": w.training_status,
    }


@router.get("/latest")
def get_latest_wellness(
    db: Session = Depends(get_db)
):
    """
    Get the most recent wellness data.

    Returns the latest day's wellness metrics including sleep, HRV,
    body battery, stress, and activity.
    """
    athlete_id = int(os.getenv("ATHLETE_ID", "1"))

    wellness = db.query(DailyWellness).filter(
        DailyWellness.athlete_id == athlete_id
    ).order_by(DailyWellness.date.desc()).first()

    if not wellness:
        return {
            "date": None,
            "hrv": None,
            "resting_heart_rate": None,
            "body_battery": None,
            "sleep_score": None,
            "sleep_duration_hours": None,
            "rem_sleep_minutes": None,
            "deep_sleep_minutes": None,
            "light_sleep_minutes": None,
            "awake_minutes": None,
            "stress_level": None,
            "steps": None,
            "active_calories": None,
        }

    return _serialize_wellness(wellness)


@router.get("")
def get_wellness_history(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get wellness data for the specified number of days.

    Args:
        days: Number of days of history to return (1-365)

    Returns:
        List of daily wellness records, most recent first.
    """
    athlete_id = int(os.getenv("ATHLETE_ID", "1"))
    today = get_eastern_today()
    start_date = today - timedelta(days=days)

    wellness_records = db.query(DailyWellness).filter(
        DailyWellness.athlete_id == athlete_id,
        DailyWellness.date >= start_date,
        DailyWellness.date <= today
    ).order_by(DailyWellness.date.desc()).all()

    return [_serialize_wellness(w) for w in wellness_records]


@router.get("/summary")
def get_wellness_summary(
    days: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """
    Get a summary of wellness metrics over the specified period.

    Args:
        days: Number of days to summarize (1-90)

    Returns:
        Summary statistics (averages, trends) for wellness metrics.
    """
    athlete_id = int(os.getenv("ATHLETE_ID", "1"))
    today = get_eastern_today()
    start_date = today - timedelta(days=days)

    wellness_records = db.query(DailyWellness).filter(
        DailyWellness.athlete_id == athlete_id,
        DailyWellness.date >= start_date,
        DailyWellness.date <= today
    ).order_by(DailyWellness.date.desc()).all()

    if not wellness_records:
        return {
            "days": days,
            "record_count": 0,
            "averages": {}
        }

    # Calculate averages
    def avg(values):
        valid = [v for v in values if v is not None]
        return round(sum(valid) / len(valid), 1) if valid else None

    return {
        "days": days,
        "record_count": len(wellness_records),
        "averages": {
            "hrv": avg([w.hrv_last_night for w in wellness_records]),
            "resting_heart_rate": avg([w.resting_heart_rate for w in wellness_records]),
            "body_battery": avg([w.body_battery_current for w in wellness_records]),
            "sleep_score": avg([w.sleep_score for w in wellness_records]),
            "sleep_duration_hours": avg([
                w.sleep_duration_seconds / 3600 if w.sleep_duration_seconds else None
                for w in wellness_records
            ]),
            "stress_level": avg([w.avg_stress_level for w in wellness_records]),
            "steps": avg([w.steps for w in wellness_records]),
        },
        "latest_date": str(wellness_records[0].date) if wellness_records else None,
    }
