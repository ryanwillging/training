"""
API routes for training plan management.
"""

import os
from datetime import date, datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from typing import Optional
from pydantic import BaseModel

from api.timezone import get_eastern_today
from database.base import SessionLocal
from database.models import ScheduledWorkout, DailyReview, PlanAdjustment
from analyst.plan_manager import TrainingPlanManager
from api.design_system import (
    wrap_page,
    WORKOUT_STYLES, STATUS_COLORS, ASSESSMENT_COLORS, PRIORITY_COLORS,
)
import json


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


@router.post("/scan-formats")
async def scan_workout_formats(days_ahead: int = 14):
    """
    Scan all scheduled workouts and fix any that have incorrect Garmin format.

    This verifies that strength workouts use proper RepeatGroupDTO structure
    with reps conditions, and fixes any that use outdated lap.button format.

    Args:
        days_ahead: How many days ahead to scan (default 14)

    Returns:
        Scan results showing which workouts were fixed/failed
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

        results = manager.scan_and_fix_workout_formats(days_ahead=days_ahead)
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

        results = manager.run_nightly_evaluation(evaluation_type="on_demand")
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
        today = get_eastern_today()
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
            style = WORKOUT_STYLES.get(w.workout_type, {"icon": "💪", "label": w.workout_type, "color": "#666"})

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


class ReviewActionRequest(BaseModel):
    """Request to approve or reject a review."""
    action: str  # 'approve', 'reject'
    notes: Optional[str] = None


class EvaluationRequest(BaseModel):
    """Request to run an AI evaluation with optional user context."""
    user_context: Optional[str] = None


class ModificationActionRequest(BaseModel):
    """Request to approve or reject a single modification."""
    action: str  # 'approve' or 'reject'


@router.post("/reviews/{review_id}/modifications/{mod_index}/action")
async def action_modification(review_id: int, mod_index: int, request: ModificationActionRequest):
    """
    Approve or reject a single modification within a review.

    Args:
        review_id: ID of the DailyReview
        mod_index: Index of the modification in the adjustments list (0-based)
        request: Action to take (approve/reject)

    Returns:
        Result of the action including updated review status and any Garmin sync results
    """
    if request.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")

    athlete_id = int(os.getenv("ATHLETE_ID", "1"))
    db = SessionLocal()

    try:
        manager = TrainingPlanManager(db, athlete_id)
        result = manager.action_single_modification(review_id, mod_index, request.action)
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/reviews-page", response_class=HTMLResponse)
async def get_reviews_page():
    """
    HTML page showing AI-generated training plan reviews and proposed modifications.
    Allows approving or rejecting suggested changes.
    """
    athlete_id = int(os.getenv("ATHLETE_ID", "1"))
    db = SessionLocal()

    try:
        # Get recent reviews (last 30 days)
        today = get_eastern_today()
        cutoff = today - timedelta(days=30)

        reviews = db.query(DailyReview).filter(
            DailyReview.athlete_id == athlete_id,
            DailyReview.review_date >= cutoff
        ).order_by(DailyReview.review_date.desc()).all()

        # Get plan status for context
        manager = TrainingPlanManager(db, athlete_id)
        plan_status = manager.get_plan_status()

        content = _generate_reviews_html(reviews, plan_status, today)

        return HTMLResponse(content=wrap_page(content, "Plan Reviews", "/reviews"))

    finally:
        db.close()


@router.post("/reviews/{review_id}/action")
async def action_review(review_id: int, request: ReviewActionRequest):
    """
    Approve or reject all pending modifications in a review.

    When approved, only pending modifications are applied to the training plan
    and synced to Garmin Connect. Already-actioned modifications are skipped.

    Args:
        review_id: ID of the DailyReview
        request: Action to take (approve/reject) and optional notes
    """
    if request.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")

    athlete_id = int(os.getenv("ATHLETE_ID", "1"))
    db = SessionLocal()

    try:
        review = db.query(DailyReview).filter(
            DailyReview.id == review_id,
            DailyReview.athlete_id == athlete_id
        ).first()

        if not review:
            raise HTTPException(status_code=404, detail="Review not found")

        # Parse adjustments
        adjustments = json.loads(review.proposed_adjustments) if review.proposed_adjustments else []

        # Find pending modifications
        pending_mods = [adj for adj in adjustments if adj.get("status", "pending") == "pending"]

        if not pending_mods:
            raise HTTPException(
                status_code=400,
                detail="No pending modifications to action"
            )

        garmin_results = None
        action_time = datetime.utcnow().isoformat()

        # Create manager for plan operations
        manager = TrainingPlanManager(db, athlete_id)

        # Update status of all pending modifications
        for adj in adjustments:
            if adj.get("status", "pending") == "pending":
                adj["status"] = request.action + "d"  # 'approved' or 'rejected'
                adj["actioned_at"] = action_time

        if request.action == "approve":
            review.approval_notes = request.notes

            # Ensure a training plan exists for the PlanAdjustment foreign key
            plan_id = manager._ensure_training_plan_exists()

            # Create PlanAdjustment records for tracking (only for pending mods)
            for adj in pending_mods:
                plan_adj = PlanAdjustment(
                    plan_id=plan_id,
                    review_id=review.id,
                    adjustment_date=get_eastern_today(),
                    adjustment_type=adj.get("type", "unknown"),
                    reasoning=adj.get("reason", ""),
                    changes=json.dumps(adj)
                )
                db.add(plan_adj)

            # Apply modifications to ScheduledWorkouts and sync to Garmin
            try:
                garmin_results = manager.apply_approved_modifications(
                    pending_mods,
                    sync_to_garmin=True
                )
                review.adjustments_applied = True
            except Exception as e:
                # Still mark as approved even if Garmin sync fails
                review.adjustments_applied = True
                garmin_results = {"error": str(e)}

        elif request.action == "reject":
            review.approval_notes = request.notes

        # Update the review with modified adjustments
        review.proposed_adjustments = json.dumps(adjustments)

        # Recalculate overall review status
        review.approval_status = TrainingPlanManager.calculate_review_status(adjustments)
        review.approved_at = datetime.utcnow()

        db.commit()

        result = {
            "status": "success",
            "review_id": review_id,
            "action": request.action,
            "modifications_actioned": len(pending_mods),
            "approval_status": review.approval_status
        }

        if garmin_results:
            result["garmin_sync"] = garmin_results

        return result

    finally:
        db.close()


@router.get("/reviews/latest")
async def get_latest_review():
    """
    Get the most recent AI evaluation review.
    """
    athlete_id = int(os.getenv("ATHLETE_ID", "1"))
    db = SessionLocal()

    try:
        review = db.query(DailyReview).filter(
            DailyReview.athlete_id == athlete_id
        ).order_by(DailyReview.review_date.desc()).first()

        if not review:
            return {"status": "no_reviews", "message": "No AI evaluations have been run yet"}

        return {
            "id": review.id,
            "date": str(review.review_date),
            "approval_status": review.approval_status,
            "progress_summary": json.loads(review.progress_summary) if review.progress_summary else None,
            "insights": review.insights,
            "recommendations": review.recommendations,
            "proposed_adjustments": json.loads(review.proposed_adjustments) if review.proposed_adjustments else [],
            "created_at": review.created_at.isoformat() if review.created_at else None
        }

    finally:
        db.close()


@router.post("/evaluate-with-context")
async def run_evaluation_with_context(request: EvaluationRequest):
    """
    Run AI-powered evaluation with optional user-provided context.

    This allows the user to add notes or context that the AI should consider
    when evaluating the training plan.

    Args:
        request: Contains optional user_context string
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

        # Run evaluation with user context (on-demand via UI)
        results = manager.run_nightly_evaluation(
            user_context=request.user_context,
            evaluation_type="on_demand"
        )
        return results

    finally:
        db.close()


@router.get("/evaluation-context")
async def get_evaluation_context():
    """
    Get the data that would be sent to the AI for evaluation.
    Useful for understanding what the AI sees when making recommendations.
    """
    athlete_id = int(os.getenv("ATHLETE_ID", "1"))
    db = SessionLocal()

    try:
        manager = TrainingPlanManager(db, athlete_id)

        if not manager.get_plan_start_date():
            return {
                "status": "plan_not_initialized",
                "message": "Initialize your training plan first"
            }

        # Gather the same data used for evaluation
        current_week = manager.get_current_week()
        wellness_data = manager._get_recent_wellness(days=7)
        recent_workouts = manager._get_recent_workouts(days=14)
        goal_progress = manager._get_goal_progress()
        upcoming_workouts = manager._get_upcoming_workouts(days=7)
        plan_summary = manager._get_plan_summary()

        return {
            "current_week": current_week,
            "wellness_data": wellness_data,
            "recent_workouts": recent_workouts,
            "goal_progress": goal_progress,
            "upcoming_workouts": upcoming_workouts,
            "plan_summary": plan_summary,
            "ai_instructions": "The AI is instructed to be conservative with modifications - only suggesting changes when clearly warranted. It evaluates wellness trends, workout adherence, and goal alignment to determine if adjustments are needed."
        }

    finally:
        db.close()


def _generate_reviews_html(reviews: list, plan_status: dict, today: date) -> str:
    """Generate HTML content for the reviews page."""

    # Count total pending modifications across all reviews
    total_pending_mods = 0
    for r in reviews:
        if r.proposed_adjustments:
            adjustments = json.loads(r.proposed_adjustments)
            total_pending_mods += sum(1 for adj in adjustments if adj.get("status", "pending") == "pending")

    pending_count = total_pending_mods

    # Plan info header
    current_week = plan_status.get("current_week", "?")
    is_initialized = plan_status.get("initialized", False)

    if not is_initialized:
        return '''
        <header class="mb-6">
            <h1 class="md-headline-large mb-2">Plan Reviews</h1>
            <p class="md-body-large text-secondary">AI-generated training plan evaluations</p>
        </header>

        <div class="md-card">
            <div class="md-card-content" style="text-align: center; padding: 48px;">
                <div style="font-size: 48px; margin-bottom: 16px;">📋</div>
                <h2 class="md-title-large mb-4">Plan Not Initialized</h2>
                <p class="md-body-medium text-secondary">Initialize your training plan to enable AI evaluations.</p>
            </div>
        </div>
        '''

    if not reviews:
        return f'''
        <header class="mb-6">
            <h1 class="md-headline-large mb-2">Plan Reviews</h1>
            <p class="md-body-large text-secondary">Week {current_week} of 24</p>
        </header>

        <div class="md-card">
            <div class="md-card-content" style="text-align: center; padding: 48px;">
                <div style="font-size: 48px; margin-bottom: 16px;">🤖</div>
                <h2 class="md-title-large mb-4">No Evaluations Yet</h2>
                <p class="md-body-medium text-secondary">AI evaluations run nightly after the cron sync.</p>
                <p class="md-body-small text-secondary mt-2">You can also trigger a manual evaluation via the API.</p>
            </div>
        </div>
        '''

    # Build review cards
    cards_html = ""
    for review in reviews:
        # Parse data
        adjustments = json.loads(review.proposed_adjustments) if review.proposed_adjustments else []

        # Status (used for card styling)
        status = review.approval_status or "pending"

        # Date formatting
        review_date = review.review_date
        if review_date == today:
            date_label = "Today"
        elif review_date == today - timedelta(days=1):
            date_label = "Yesterday"
        else:
            date_label = review_date.strftime("%b %d, %Y")

        # Build modifications list with individual status and actions
        mods_html = ""
        pending_mod_count = 0
        if adjustments:
            for idx, adj in enumerate(adjustments):
                adj_type = adj.get("type", "unknown")
                adj_desc = adj.get("description", "No description")
                adj_reason = adj.get("reason", "")
                adj_priority = adj.get("priority", "medium")
                adj_week = adj.get("week", "?")
                mod_status = adj.get("status", "pending")

                if mod_status == "pending":
                    pending_mod_count += 1

                p_style = PRIORITY_COLORS.get(adj_priority, PRIORITY_COLORS["medium"])

                # Status badge colors
                mod_status_styles = {
                    "pending": {"bg": "#fff3e0", "text": "#e65100", "label": "Pending"},
                    "approved": {"bg": "#e8f5e9", "text": "#2e7d32", "label": "Approved"},
                    "rejected": {"bg": "#ffebee", "text": "#c62828", "label": "Rejected"}
                }
                s_style = mod_status_styles.get(mod_status, mod_status_styles["pending"])

                # Individual action buttons (only for pending modifications)
                mod_actions_html = ""
                if mod_status == "pending":
                    mod_actions_html = f'''
                    <div class="mod-actions">
                        <button class="mod-btn approve-mod" onclick="actionModification({review.id}, {idx}, 'approve')" title="Approve this modification">✓</button>
                        <button class="mod-btn reject-mod" onclick="actionModification({review.id}, {idx}, 'reject')" title="Reject this modification">✗</button>
                    </div>
                    '''

                mods_html += f'''
                <div class="modification-item {'mod-actioned' if mod_status != 'pending' else ''}">
                    <div class="mod-header">
                        <span class="mod-type">{adj_type.replace("_", " ").title()}</span>
                        <span class="mod-priority" style="background: {p_style["bg"]}; color: {p_style["text"]};">{adj_priority.upper()}</span>
                        <span class="mod-week">Week {adj_week}</span>
                        <span class="mod-status" style="background: {s_style["bg"]}; color: {s_style["text"]};">{s_style["label"]}</span>
                    </div>
                    <div class="mod-content">
                        <div class="mod-details">
                            <div class="mod-description">{adj_desc}</div>
                            {f'<div class="mod-reason">{adj_reason}</div>' if adj_reason else ''}
                        </div>
                        {mod_actions_html}
                    </div>
                </div>
                '''
        else:
            mods_html = '<p class="text-secondary" style="padding: 16px;">No modifications proposed</p>'

        # Action buttons for bulk approve/reject (only if there are pending modifications)
        actions_html = ""
        if pending_mod_count > 0:
            actions_html = f'''
            <div class="review-actions">
                <button class="md-btn md-btn-filled approve-btn" onclick="actionReview({review.id}, 'approve')">
                    ✓ Approve All Pending ({pending_mod_count})
                </button>
                <button class="md-btn md-btn-outlined reject-btn" onclick="actionReview({review.id}, 'reject')">
                    ✗ Reject All Pending
                </button>
            </div>
            '''
        elif review.approval_notes:
            actions_html = f'''
            <div class="review-notes">
                <strong>Notes:</strong> {review.approval_notes}
            </div>
            '''

        # Show user context if provided
        user_context_html = ""
        if review.user_context:
            user_context_html = f'''
            <div class="user-context-section">
                <span class="context-icon">💬</span>
                <span class="context-label">Your notes:</span>
                <span class="context-text">{review.user_context}</span>
            </div>
            '''

        cards_html += f'''
        <div class="review-card {'pending' if status == 'pending' else ''}">
            <div class="review-header">
                <div class="review-date">
                    <span class="date-label">{date_label}</span>
                    <span class="date-full">{review_date.strftime("%A")}</span>
                </div>
            </div>
            {user_context_html}

            <div class="review-body">
                {f'<div class="review-insights"><h4>Insights</h4><p>{review.insights}</p></div>' if review.insights else ''}
                {f'<div class="review-recommendations"><h4>Recommendations</h4><p>{review.recommendations}</p></div>' if review.recommendations else ''}

                <div class="review-modifications">
                    <h4>Proposed Modifications ({len(adjustments)})</h4>
                    <div class="modifications-list">
                        {mods_html}
                    </div>
                </div>
            </div>

            {actions_html}
        </div>
        '''

    # Pending alert if any
    pending_alert = ""
    if pending_count > 0:
        pending_alert = f'''
        <div class="pending-alert">
            <div class="alert-icon">⚠️</div>
            <div class="alert-content">
                <strong>{pending_count} modification{"s" if pending_count > 1 else ""} pending approval</strong>
                <p>Review the AI-suggested modifications and approve or reject them individually or in bulk.</p>
            </div>
        </div>
        '''

    return f'''
    <header class="mb-6">
        <h1 class="md-headline-large mb-2">Plan Reviews</h1>
        <p class="md-body-large text-secondary">Week {current_week} of 24 · {len(reviews)} evaluations</p>
    </header>

    <!-- Manual Evaluation Section -->
    <div class="md-card mb-6">
        <div class="md-card-header">
            <h2 class="md-title-medium">Run AI Evaluation</h2>
        </div>
        <div class="md-card-content">
            <p class="md-body-medium text-secondary mb-4">
                Add context or notes for the AI to consider when evaluating your training plan.
                The AI will analyze your wellness data, recent workouts, and goal progress.
            </p>
            <div class="context-input-group">
                <label for="user-context" class="md-label-medium">Your Notes (optional)</label>
                <textarea
                    id="user-context"
                    class="md-input context-textarea"
                    placeholder="Example: I've been feeling fatigued this week, considering taking an extra rest day... or I'm feeling great and want to push harder..."
                    rows="3"
                ></textarea>
            </div>
            <div class="evaluation-actions">
                <button class="md-btn md-btn-filled" onclick="runEvaluation()" id="eval-btn">
                    🤖 Run Evaluation
                </button>
                <button class="md-btn md-btn-outlined" onclick="viewContext()">
                    📊 View Input Data
                </button>
            </div>
            <div id="eval-status" class="eval-status hidden"></div>
        </div>
    </div>

    <!-- Context Modal -->
    <div id="context-modal" class="modal hidden">
        <div class="modal-content">
            <div class="modal-header">
                <h3 class="md-title-large">AI Evaluation Input Data</h3>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body" id="context-data">
                Loading...
            </div>
        </div>
    </div>

    {pending_alert}

    <div class="reviews-list">
        {cards_html}
    </div>

    <script>
    async function actionReview(reviewId, action) {{
        const notes = action === 'reject'
            ? prompt('Reason for rejection (optional):')
            : null;

        try {{
            const response = await fetch(`/api/plan/reviews/${{reviewId}}/action`, {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{ action, notes }})
            }});

            if (response.ok) {{
                location.reload();
            }} else {{
                const data = await response.json();
                alert('Error: ' + (data.detail || 'Failed to process action'));
            }}
        }} catch (e) {{
            alert('Error: ' + e.message);
        }}
    }}

    async function actionModification(reviewId, modIndex, action) {{
        try {{
            const response = await fetch(`/api/plan/reviews/${{reviewId}}/modifications/${{modIndex}}/action`, {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{ action }})
            }});

            if (response.ok) {{
                location.reload();
            }} else {{
                const data = await response.json();
                alert('Error: ' + (data.detail || 'Failed to process action'));
            }}
        }} catch (e) {{
            alert('Error: ' + e.message);
        }}
    }}

    async function runEvaluation() {{
        const userContext = document.getElementById('user-context').value.trim();
        const btn = document.getElementById('eval-btn');
        const status = document.getElementById('eval-status');

        btn.disabled = true;
        btn.textContent = '⏳ Running...';
        status.className = 'eval-status';
        status.innerHTML = '<div class="status-loading">Analyzing your training data with AI... This may take 30-60 seconds.</div>';

        try {{
            const response = await fetch('/api/plan/evaluate-with-context', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{ user_context: userContext || null }})
            }});

            const data = await response.json();

            if (response.ok) {{
                status.innerHTML = '<div class="status-success">✓ Evaluation complete! Refreshing...</div>';
                setTimeout(() => location.reload(), 1500);
            }} else {{
                status.innerHTML = '<div class="status-error">✗ Error: ' + (data.detail || 'Evaluation failed') + '</div>';
                btn.disabled = false;
                btn.textContent = '🤖 Run Evaluation';
            }}
        }} catch (e) {{
            status.innerHTML = '<div class="status-error">✗ Error: ' + e.message + '</div>';
            btn.disabled = false;
            btn.textContent = '🤖 Run Evaluation';
        }}
    }}

    async function viewContext() {{
        const modal = document.getElementById('context-modal');
        const content = document.getElementById('context-data');
        modal.classList.remove('hidden');

        try {{
            const response = await fetch('/api/plan/evaluation-context');
            const data = await response.json();

            content.innerHTML = `
                <div class="context-section">
                    <h4>Current Week</h4>
                    <p>Week ${{data.current_week}} of 24</p>
                </div>
                <div class="context-section">
                    <h4>AI Instructions</h4>
                    <p class="text-secondary">${{data.ai_instructions}}</p>
                </div>
                <div class="context-section">
                    <h4>Wellness Data (7-day average)</h4>
                    <pre>${{JSON.stringify(data.wellness_data, null, 2)}}</pre>
                </div>
                <div class="context-section">
                    <h4>Recent Workouts (14 days)</h4>
                    <pre>${{JSON.stringify(data.recent_workouts, null, 2)}}</pre>
                </div>
                <div class="context-section">
                    <h4>Goal Progress</h4>
                    <pre>${{JSON.stringify(data.goal_progress, null, 2)}}</pre>
                </div>
                <div class="context-section">
                    <h4>Upcoming Workouts</h4>
                    <pre>${{JSON.stringify(data.upcoming_workouts, null, 2)}}</pre>
                </div>
            `;
        }} catch (e) {{
            content.innerHTML = '<p class="status-error">Error loading context: ' + e.message + '</p>';
        }}
    }}

    function closeModal() {{
        document.getElementById('context-modal').classList.add('hidden');
    }}

    // Close modal on escape key
    document.addEventListener('keydown', (e) => {{
        if (e.key === 'Escape') closeModal();
    }});
    </script>

    <style>
        .pending-alert {{
            display: flex;
            align-items: flex-start;
            gap: 16px;
            padding: 16px 20px;
            background: #fff3e0;
            border-radius: var(--radius-lg);
            border: 1px solid #ffcc80;
            margin-bottom: 24px;
        }}

        .alert-icon {{
            font-size: 24px;
        }}

        .alert-content strong {{
            color: #e65100;
        }}

        .alert-content p {{
            margin: 4px 0 0;
            color: #bf360c;
            font-size: 14px;
        }}

        .reviews-list {{
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}

        .review-card {{
            background: var(--md-surface);
            border-radius: var(--radius-lg);
            border: 1px solid var(--md-outline-variant);
            overflow: hidden;
        }}

        .review-card.pending {{
            border-color: #ffcc80;
            box-shadow: 0 0 0 1px #fff3e0;
        }}

        .review-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 20px;
            background: var(--md-surface-variant);
            border-bottom: 1px solid var(--md-outline-variant);
            flex-wrap: wrap;
            gap: 12px;
        }}

        .review-date {{
            display: flex;
            flex-direction: column;
        }}

        .date-label {{
            font-size: 18px;
            font-weight: 600;
            color: var(--md-on-surface);
        }}

        .date-full {{
            font-size: 13px;
            color: var(--md-on-surface-variant);
        }}

        .user-context-section {{
            padding: 12px 20px;
            background: #f3e5f5;
            border-bottom: 1px solid var(--md-outline-variant);
            display: flex;
            align-items: flex-start;
            gap: 8px;
            font-size: 14px;
        }}
        .context-icon {{ font-size: 16px; }}
        .context-label {{ font-weight: 600; color: #7b1fa2; white-space: nowrap; }}
        .context-text {{ color: #4a148c; line-height: 1.4; }}

        .review-body {{
            padding: 20px;
        }}

        .review-insights, .review-recommendations {{
            margin-bottom: 20px;
        }}

        .review-body h4 {{
            font-size: 14px;
            font-weight: 600;
            color: var(--md-on-surface);
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .review-body p {{
            color: var(--md-on-surface-variant);
            line-height: 1.6;
        }}

        .review-modifications {{
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid var(--md-outline-variant);
        }}

        .modifications-list {{
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-top: 12px;
        }}

        .modification-item {{
            padding: 16px;
            background: var(--md-surface-variant);
            border-radius: var(--radius-md);
            border-left: 4px solid var(--md-primary);
        }}

        .modification-item.mod-actioned {{
            opacity: 0.7;
            border-left-color: #9e9e9e;
        }}

        .mod-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
            flex-wrap: wrap;
        }}

        .mod-type {{
            font-weight: 600;
            color: var(--md-on-surface);
        }}

        .mod-priority {{
            font-size: 10px;
            padding: 2px 8px;
            border-radius: var(--radius-full);
            font-weight: 600;
        }}

        .mod-week {{
            font-size: 12px;
            color: var(--md-on-surface-variant);
        }}

        .mod-status {{
            font-size: 10px;
            padding: 2px 8px;
            border-radius: var(--radius-full);
            font-weight: 600;
            margin-left: auto;
        }}

        .mod-content {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 16px;
        }}

        .mod-details {{
            flex: 1;
        }}

        .mod-description {{
            color: var(--md-on-surface);
            margin-bottom: 6px;
        }}

        .mod-reason {{
            font-size: 13px;
            color: var(--md-on-surface-variant);
            font-style: italic;
        }}

        .mod-actions {{
            display: flex;
            gap: 8px;
            flex-shrink: 0;
        }}

        .mod-btn {{
            width: 32px;
            height: 32px;
            border-radius: 50%;
            border: none;
            cursor: pointer;
            font-size: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.1s, background 0.2s;
        }}

        .mod-btn:hover {{
            transform: scale(1.1);
        }}

        .mod-btn.approve-mod {{
            background: #e8f5e9;
            color: #2e7d32;
        }}

        .mod-btn.approve-mod:hover {{
            background: #c8e6c9;
        }}

        .mod-btn.reject-mod {{
            background: #ffebee;
            color: #c62828;
        }}

        .mod-btn.reject-mod:hover {{
            background: #ffcdd2;
        }}

        .review-actions {{
            display: flex;
            gap: 12px;
            padding: 16px 20px;
            background: var(--md-surface-variant);
            border-top: 1px solid var(--md-outline-variant);
        }}

        .approve-btn {{
            background: #2e7d32 !important;
        }}

        .approve-btn:hover {{
            background: #1b5e20 !important;
        }}

        .reject-btn {{
            color: #c62828 !important;
            border-color: #c62828 !important;
        }}

        .reject-btn:hover {{
            background: #ffebee !important;
        }}

        .review-notes {{
            padding: 12px 20px;
            background: var(--md-surface-variant);
            border-top: 1px solid var(--md-outline-variant);
            font-size: 14px;
            color: var(--md-on-surface-variant);
        }}

        /* Context input styles */
        .context-input-group {{
            margin-bottom: 16px;
        }}

        .context-input-group label {{
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: var(--md-on-surface);
        }}

        .context-textarea {{
            width: 100%;
            min-height: 80px;
            resize: vertical;
            font-family: inherit;
        }}

        .evaluation-actions {{
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }}

        .eval-status {{
            margin-top: 16px;
        }}

        .eval-status.hidden {{
            display: none;
        }}

        .status-loading {{
            padding: 12px 16px;
            background: #e3f2fd;
            color: #1565c0;
            border-radius: var(--radius-md);
        }}

        .status-success {{
            padding: 12px 16px;
            background: #e8f5e9;
            color: #2e7d32;
            border-radius: var(--radius-md);
        }}

        .status-error {{
            padding: 12px 16px;
            background: #ffebee;
            color: #c62828;
            border-radius: var(--radius-md);
        }}

        /* Modal styles */
        .modal {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            padding: 20px;
        }}

        .modal.hidden {{
            display: none;
        }}

        .modal-content {{
            background: var(--md-surface);
            border-radius: var(--radius-lg);
            max-width: 800px;
            max-height: 80vh;
            width: 100%;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }}

        .modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 20px;
            border-bottom: 1px solid var(--md-outline-variant);
        }}

        .modal-close {{
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: var(--md-on-surface-variant);
            padding: 4px 8px;
        }}

        .modal-close:hover {{
            color: var(--md-on-surface);
        }}

        .modal-body {{
            padding: 20px;
            overflow-y: auto;
        }}

        .context-section {{
            margin-bottom: 24px;
        }}

        .context-section h4 {{
            font-size: 14px;
            font-weight: 600;
            color: var(--md-on-surface);
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .context-section pre {{
            background: var(--md-surface-variant);
            padding: 12px;
            border-radius: var(--radius-md);
            overflow-x: auto;
            font-size: 12px;
            line-height: 1.5;
            max-height: 200px;
            overflow-y: auto;
        }}

        @media (max-width: 640px) {{
            .review-header {{
                flex-direction: column;
                align-items: flex-start;
            }}

            .review-actions {{
                flex-direction: column;
            }}

            .review-actions button {{
                width: 100%;
            }}

            .evaluation-actions {{
                flex-direction: column;
            }}

            .evaluation-actions button {{
                width: 100%;
            }}

            .modal-content {{
                max-height: 90vh;
            }}
        }}
    </style>
    '''
