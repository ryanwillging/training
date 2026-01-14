"""
API routes for training plan management.
"""

import os
from datetime import date, datetime
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel

from database.base import SessionLocal
from analyst.plan_manager import TrainingPlanManager


router = APIRouter(prefix="/plan", tags=["plan"])


class PlanInitRequest(BaseModel):
    """Request to initialize the training plan."""
    start_date: str  # ISO format: YYYY-MM-DD


class GarminSyncRequest(BaseModel):
    """Request to sync workouts to Garmin."""
    week_number: Optional[int] = None
    days_ahead: int = 7


@router.get("/status")
async def get_plan_status():
    """
    Get the current status of the training plan.

    Returns:
        Plan status including current week, progress, and test week info.
    """
    athlete_id = int(os.getenv("ATHLETE_ID", "1"))
    db = SessionLocal()

    try:
        manager = TrainingPlanManager(db, athlete_id)
        status = manager.get_plan_status()
        return status
    finally:
        db.close()


@router.post("/initialize")
async def initialize_plan(request: PlanInitRequest):
    """
    Initialize the 24-week training plan with a start date.

    This creates all scheduled workouts in the database.
    The start_date should be a Monday for proper weekly alignment.

    Args:
        request: Contains start_date in ISO format (YYYY-MM-DD)

    Returns:
        Initialization summary
    """
    athlete_id = int(os.getenv("ATHLETE_ID", "1"))
    db = SessionLocal()

    try:
        start_date = date.fromisoformat(request.start_date)

        # Validate it's a Monday
        if start_date.weekday() != 0:
            raise HTTPException(
                status_code=400,
                detail=f"Start date should be a Monday. {request.start_date} is a {start_date.strftime('%A')}"
            )

        manager = TrainingPlanManager(db, athlete_id)
        result = manager.initialize_plan(start_date)

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    finally:
        db.close()


@router.get("/week/{week_number}")
async def get_week_summary(week_number: int):
    """
    Get a summary of workouts for a specific week.

    Args:
        week_number: Week number (1-24)

    Returns:
        Week summary with workout details and completion status
    """
    if not 1 <= week_number <= 24:
        raise HTTPException(status_code=400, detail="Week number must be between 1 and 24")

    athlete_id = int(os.getenv("ATHLETE_ID", "1"))
    db = SessionLocal()

    try:
        manager = TrainingPlanManager(db, athlete_id)
        summary = manager.get_weekly_summary(week_number)
        return summary
    finally:
        db.close()


@router.get("/week")
async def get_current_week_summary():
    """
    Get a summary of the current week's workouts.

    Returns:
        Current week summary with workout details
    """
    athlete_id = int(os.getenv("ATHLETE_ID", "1"))
    db = SessionLocal()

    try:
        manager = TrainingPlanManager(db, athlete_id)
        summary = manager.get_weekly_summary()
        return summary
    finally:
        db.close()


@router.post("/sync-garmin")
async def sync_to_garmin(request: Optional[GarminSyncRequest] = None):
    """
    Sync scheduled workouts to Garmin Connect calendar.

    Args:
        request: Optional sync parameters (week_number or days_ahead)

    Returns:
        Sync results showing which workouts were synced/failed
    """
    athlete_id = int(os.getenv("ATHLETE_ID", "1"))
    db = SessionLocal()

    try:
        manager = TrainingPlanManager(db, athlete_id)

        if not manager.get_plan_start_date():
            raise HTTPException(
                status_code=400,
                detail="Plan not initialized. Call /plan/initialize first."
            )

        week_number = request.week_number if request else None
        days_ahead = request.days_ahead if request else 7

        results = manager.sync_workouts_to_garmin(
            week_number=week_number,
            days_ahead=days_ahead
        )

        return results

    finally:
        db.close()


@router.post("/evaluate")
async def run_evaluation():
    """
    Run AI-powered evaluation of training progress.

    This uses ChatGPT (o1 reasoning model) to analyze:
    - Wellness data (sleep, HRV, readiness)
    - Completed workouts
    - Goal progress
    - Upcoming schedule

    Returns:
        Evaluation results with assessment and any recommended modifications
    """
    athlete_id = int(os.getenv("ATHLETE_ID", "1"))
    db = SessionLocal()

    try:
        manager = TrainingPlanManager(db, athlete_id)

        if not manager.get_plan_start_date():
            raise HTTPException(
                status_code=400,
                detail="Plan not initialized. Call /plan/initialize first."
            )

        results = manager.run_nightly_evaluation()
        return results

    finally:
        db.close()


@router.get("/upcoming")
async def get_upcoming_workouts(days: int = Query(default=7, ge=1, le=30)):
    """
    Get upcoming scheduled workouts.

    Args:
        days: Number of days ahead to look (1-30)

    Returns:
        List of upcoming workouts
    """
    athlete_id = int(os.getenv("ATHLETE_ID", "1"))
    db = SessionLocal()

    try:
        manager = TrainingPlanManager(db, athlete_id)
        workouts = manager._get_upcoming_workouts(days)
        return {
            "days_ahead": days,
            "workouts": workouts
        }
    finally:
        db.close()
