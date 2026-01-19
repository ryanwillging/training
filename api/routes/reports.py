"""
API routes for generating and retrieving training reports.
"""

import json
from datetime import date, datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from api.timezone import get_eastern_today
from database.base import get_db
from database.models import Report, Athlete
from analyst.report_generator import TrainingReportGenerator
from api.navigation import wrap_page_with_nav
from api.design_system import wrap_page

router = APIRouter(prefix="/reports", tags=["reports"])


def get_week_bounds(week_str: str) -> tuple[date, date]:
    """
    Parse week string (YYYY-WNN) into start and end dates.
    Week starts on Monday, ends on Sunday.
    """
    year, week = week_str.split('-W')
    year = int(year)
    week = int(week)

    # First day of the year
    jan1 = date(year, 1, 1)
    # Days to first Monday
    days_to_monday = (7 - jan1.weekday()) % 7
    first_monday = jan1 + timedelta(days=days_to_monday)

    # Week start (Monday)
    week_start = first_monday + timedelta(weeks=week - 1)
    # Week end (Sunday)
    week_end = week_start + timedelta(days=6)

    return week_start, week_end


@router.get("/daily", response_class=HTMLResponse)
def get_daily_report(
    report_date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format (default: today)"),
    athlete_id: int = Query(1, description="Athlete ID"),
    regenerate: bool = Query(False, description="Force regenerate even if cached"),
    db: Session = Depends(get_db)
):
    """
    Get or generate a daily training report.

    Returns an HTML report with Tufte-style visualizations including:
    - Today's activities
    - Weekly summary metrics
    - Volume sparklines
    - Top exercises table

    The report is cached in the database. Use regenerate=true to force a fresh report.
    """
    # Parse date
    if report_date:
        try:
            target_date = datetime.strptime(report_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = get_eastern_today()

    # Verify athlete exists
    athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()
    if not athlete:
        raise HTTPException(status_code=404, detail=f"Athlete {athlete_id} not found")

    # Check for cached report
    if not regenerate:
        cached = db.query(Report).filter(
            Report.athlete_id == athlete_id,
            Report.report_date == target_date,
            Report.report_type == "daily"
        ).first()

        if cached:
            html_with_nav = wrap_page_with_nav(cached.html_content, "/api/reports/daily")
            return HTMLResponse(content=html_with_nav)

    # Generate new report
    try:
        generator = TrainingReportGenerator(db, athlete_id)
        html_content = generator.generate_daily_report(target_date)

        # Cache the report
        existing = db.query(Report).filter(
            Report.athlete_id == athlete_id,
            Report.report_date == target_date,
            Report.report_type == "daily"
        ).first()

        if existing:
            existing.html_content = html_content
            existing.updated_at = datetime.utcnow()
        else:
            new_report = Report(
                athlete_id=athlete_id,
                report_date=target_date,
                report_type="daily",
                html_content=html_content
            )
            db.add(new_report)

        db.commit()

        html_with_nav = wrap_page_with_nav(html_content, "/api/reports/daily")
        return HTMLResponse(content=html_with_nav)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.get("/weekly", response_class=HTMLResponse)
def get_weekly_report(
    week: Optional[str] = Query(None, description="Week in YYYY-WNN format (default: current week)"),
    athlete_id: int = Query(1, description="Athlete ID"),
    regenerate: bool = Query(False, description="Force regenerate even if cached"),
    db: Session = Depends(get_db)
):
    """
    Get or generate a weekly training summary report.

    Returns an HTML report with:
    - Weekly totals (workouts, duration, volume)
    - Week-over-week comparisons with slope graphs
    - 4-week volume trend
    - Complete workout log

    The report is cached in the database. Use regenerate=true to force a fresh report.
    """
    # Parse week or default to current week
    if week:
        try:
            week_start, week_end = get_week_bounds(week)
        except (ValueError, IndexError):
            raise HTTPException(
                status_code=400,
                detail="Invalid week format. Use YYYY-WNN (e.g., 2026-W02)"
            )
    else:
        # Rolling 7 days (today and previous 6 days)
        today = get_eastern_today()
        week_end = today
        week_start = today - timedelta(days=6)

    # Verify athlete exists
    athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()
    if not athlete:
        raise HTTPException(status_code=404, detail=f"Athlete {athlete_id} not found")

    # Check for cached report
    if not regenerate:
        cached = db.query(Report).filter(
            Report.athlete_id == athlete_id,
            Report.report_date == week_end,
            Report.report_type == "weekly"
        ).first()

        if cached:
            html_with_nav = wrap_page_with_nav(cached.html_content, "/api/reports/weekly")
            return HTMLResponse(content=html_with_nav)

    # Generate new report
    try:
        generator = TrainingReportGenerator(db, athlete_id)
        html_content = generator.generate_weekly_report(week_end)

        # Cache the report
        existing = db.query(Report).filter(
            Report.athlete_id == athlete_id,
            Report.report_date == week_end,
            Report.report_type == "weekly"
        ).first()

        if existing:
            existing.html_content = html_content
            existing.updated_at = datetime.utcnow()
        else:
            new_report = Report(
                athlete_id=athlete_id,
                report_date=week_end,
                report_type="weekly",
                html_content=html_content
            )
            db.add(new_report)

        db.commit()

        html_with_nav = wrap_page_with_nav(html_content, "/api/reports/weekly")
        return HTMLResponse(content=html_with_nav)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.get("/list")
def list_reports(
    athlete_id: int = Query(1, description="Athlete ID"),
    report_type: Optional[str] = Query(None, description="Filter by type: 'daily' or 'weekly'"),
    limit: int = Query(10, description="Maximum number of reports to return"),
    db: Session = Depends(get_db)
):
    """
    List available cached reports for an athlete.
    """
    query = db.query(Report).filter(Report.athlete_id == athlete_id)

    if report_type:
        query = query.filter(Report.report_type == report_type)

    reports = query.order_by(Report.report_date.desc()).limit(limit).all()

    return {
        "athlete_id": athlete_id,
        "count": len(reports),
        "reports": [
            {
                "id": r.id,
                "date": str(r.report_date),
                "type": r.report_type,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "url": f"/api/reports/{r.report_type}?report_date={r.report_date}&athlete_id={athlete_id}"
                       if r.report_type == "daily"
                       else f"/api/reports/{r.report_type}?week={r.report_date.strftime('%Y-W%W')}&athlete_id={athlete_id}"
            }
            for r in reports
        ]
    }
