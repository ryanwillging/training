"""
API routes for training plan management.
"""

import os
from datetime import date, datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from typing import Optional
from pydantic import BaseModel

from database.base import SessionLocal
from database.models import ScheduledWorkout
from analyst.plan_manager import TrainingPlanManager
from api.design_system import wrap_page


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


@router.get("/upcoming-page", response_class=HTMLResponse)
async def get_upcoming_workouts_page(days: int = Query(default=14, ge=1, le=30)):
    """
    HTML page showing upcoming scheduled workouts.

    Args:
        days: Number of days ahead to show (1-30)
    """
    athlete_id = int(os.getenv("ATHLETE_ID", "1"))
    db = SessionLocal()

    try:
        today = date.today()
        end_date = today + timedelta(days=days)

        # Get scheduled workouts
        workouts = db.query(ScheduledWorkout).filter(
            ScheduledWorkout.athlete_id == athlete_id,
            ScheduledWorkout.scheduled_date >= today,
            ScheduledWorkout.scheduled_date <= end_date
        ).order_by(ScheduledWorkout.scheduled_date).all()

        # Group by date
        workouts_by_date = {}
        for w in workouts:
            date_key = w.scheduled_date
            if date_key not in workouts_by_date:
                workouts_by_date[date_key] = []
            workouts_by_date[date_key].append(w)

        # Generate HTML content
        content = _generate_upcoming_html(workouts_by_date, today, days)

        return HTMLResponse(content=wrap_page(content, "Upcoming Workouts", "/upcoming"))

    finally:
        db.close()


def _generate_upcoming_html(workouts_by_date: dict, today: date, days: int) -> str:
    """Generate HTML content for upcoming workouts page."""

    # Workout type icons and colors
    workout_styles = {
        "swim_a": {"icon": "🏊", "label": "Swim A", "color": "#1976d2"},
        "swim_b": {"icon": "🏊", "label": "Swim B", "color": "#1565c0"},
        "swim_test": {"icon": "🏊‍♂️", "label": "Swim Test", "color": "#0d47a1"},
        "lift_a": {"icon": "🏋️", "label": "Lift A (Lower)", "color": "#388e3c"},
        "lift_b": {"icon": "🏋️", "label": "Lift B (Upper)", "color": "#2e7d32"},
        "vo2": {"icon": "🫀", "label": "VO2 Session", "color": "#d32f2f"},
    }

    if not workouts_by_date:
        return '''
        <header class="mb-6">
            <h1 class="md-headline-large mb-2">Upcoming Workouts</h1>
            <p class="md-body-large text-secondary">Next ''' + str(days) + ''' days</p>
        </header>

        <div class="md-card">
            <div class="md-card-content" style="text-align: center; padding: 48px;">
                <div style="font-size: 48px; margin-bottom: 16px;">📅</div>
                <h2 class="md-title-large mb-4">No Upcoming Workouts</h2>
                <p class="md-body-medium text-secondary">Initialize your training plan to see scheduled workouts.</p>
            </div>
        </div>
        '''

    # Build workout cards by date
    cards_html = ""
    for workout_date in sorted(workouts_by_date.keys()):
        workouts = workouts_by_date[workout_date]

        # Format date header
        if workout_date == today:
            date_label = "Today"
            date_class = "today"
        elif workout_date == today + timedelta(days=1):
            date_label = "Tomorrow"
            date_class = "tomorrow"
        else:
            date_label = workout_date.strftime("%A, %B %d")
            date_class = ""

        day_name = workout_date.strftime("%a").upper()
        day_num = workout_date.strftime("%d")

        # Build workout items for this day
        items_html = ""
        for w in workouts:
            style = workout_styles.get(w.workout_type, {"icon": "💪", "label": w.workout_type, "color": "#666"})

            status_badge = ""
            if w.status == "completed":
                status_badge = '<span class="workout-status completed">✓ Completed</span>'
            elif w.status == "skipped":
                status_badge = '<span class="workout-status skipped">Skipped</span>'
            elif w.garmin_workout_id:
                status_badge = '<span class="workout-status synced">Synced to Garmin</span>'

            duration_text = f"{w.duration_minutes} min" if w.duration_minutes else ""
            week_badge = f'<span class="week-badge">Week {w.week_number}</span>'
            test_badge = '<span class="test-badge">TEST WEEK</span>' if w.is_test_week else ""

            items_html += f'''
            <div class="workout-item" style="border-left-color: {style["color"]};">
                <div class="workout-icon" style="background: {style["color"]}20; color: {style["color"]};">
                    {style["icon"]}
                </div>
                <div class="workout-info">
                    <div class="workout-title">{w.workout_name or style["label"]}</div>
                    <div class="workout-meta">
                        {week_badge}
                        {test_badge}
                        {f'<span>{duration_text}</span>' if duration_text else ''}
                    </div>
                </div>
                <div class="workout-actions">
                    {status_badge}
                </div>
            </div>
            '''

        cards_html += f'''
        <div class="day-card {date_class}">
            <div class="day-header">
                <div class="day-date">
                    <span class="day-name">{day_name}</span>
                    <span class="day-num">{day_num}</span>
                </div>
                <div class="day-label">{date_label}</div>
            </div>
            <div class="day-workouts">
                {items_html}
            </div>
        </div>
        '''

    return f'''
    <header class="mb-6">
        <h1 class="md-headline-large mb-2">Upcoming Workouts</h1>
        <p class="md-body-large text-secondary">Next {days} days · {len(workouts_by_date)} training days</p>
    </header>

    <div class="upcoming-grid">
        {cards_html}
    </div>

    <style>
        .upcoming-grid {{
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}

        .day-card {{
            background: var(--md-surface);
            border-radius: var(--radius-lg);
            border: 1px solid var(--md-outline-variant);
            overflow: hidden;
        }}

        .day-card.today {{
            border-color: var(--md-primary);
            box-shadow: 0 0 0 1px var(--md-primary);
        }}

        .day-header {{
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 16px 20px;
            background: var(--md-surface-variant);
            border-bottom: 1px solid var(--md-outline-variant);
        }}

        .day-card.today .day-header {{
            background: rgba(25, 118, 210, 0.08);
        }}

        .day-date {{
            display: flex;
            flex-direction: column;
            align-items: center;
            min-width: 48px;
        }}

        .day-name {{
            font-size: 11px;
            font-weight: 600;
            color: var(--md-on-surface-variant);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .day-num {{
            font-size: 24px;
            font-weight: 600;
            color: var(--md-on-surface);
            line-height: 1.2;
        }}

        .day-card.today .day-num {{
            color: var(--md-primary);
        }}

        .day-label {{
            font-size: 16px;
            font-weight: 500;
            color: var(--md-on-surface);
        }}

        .day-workouts {{
            padding: 12px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .workout-item {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
            background: var(--md-surface-variant);
            border-radius: var(--radius-md);
            border-left: 4px solid;
        }}

        .workout-icon {{
            width: 40px;
            height: 40px;
            border-radius: var(--radius-full);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            flex-shrink: 0;
        }}

        .workout-info {{
            flex: 1;
            min-width: 0;
        }}

        .workout-title {{
            font-weight: 500;
            color: var(--md-on-surface);
            margin-bottom: 4px;
        }}

        .workout-meta {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            align-items: center;
        }}

        .week-badge {{
            font-size: 11px;
            padding: 2px 8px;
            background: var(--md-surface);
            border-radius: var(--radius-full);
            color: var(--md-on-surface-variant);
        }}

        .test-badge {{
            font-size: 10px;
            padding: 2px 8px;
            background: #ff9800;
            color: white;
            border-radius: var(--radius-full);
            font-weight: 600;
        }}

        .workout-meta span {{
            font-size: 12px;
            color: var(--md-on-surface-variant);
        }}

        .workout-actions {{
            flex-shrink: 0;
        }}

        .workout-status {{
            font-size: 11px;
            padding: 4px 10px;
            border-radius: var(--radius-full);
            font-weight: 500;
        }}

        .workout-status.completed {{
            background: #e8f5e9;
            color: #2e7d32;
        }}

        .workout-status.skipped {{
            background: #fff3e0;
            color: #e65100;
        }}

        .workout-status.synced {{
            background: #e3f2fd;
            color: #1565c0;
        }}

        @media (max-width: 640px) {{
            .day-header {{
                padding: 12px 16px;
            }}

            .workout-item {{
                padding: 10px 12px;
            }}

            .workout-icon {{
                width: 36px;
                height: 36px;
                font-size: 18px;
            }}
        }}
    </style>
    '''
