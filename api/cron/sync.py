"""
Cron job endpoint for daily data synchronization.
Called by Vercel Cron at midnight daily.

Syncs:
- Garmin activities
- Garmin wellness data (sleep, stress, HRV, body battery, etc.)
- Hevy workouts
- Generates goal progress analysis
"""

import os
from datetime import date
from fastapi import APIRouter, HTTPException, Header, Request
from typing import Optional

from database.base import SessionLocal
from integrations.garmin.activity_importer import GarminActivityImporter
from integrations.garmin.wellness_importer import GarminWellnessImporter
from integrations.hevy.activity_importer import HevyActivityImporter
from analyst.goal_analyzer import GoalAnalyzer, WorkoutRecommendationEngine

router = APIRouter(prefix="/cron", tags=["cron"])


def verify_cron_auth(authorization: Optional[str], request: Request) -> bool:
    """
    Verify the request is from Vercel Cron or has valid authorization.

    Vercel Cron requests include a special header that can be verified.
    For manual testing, we accept Bearer token authorization.
    """
    cron_secret = os.getenv("CRON_SECRET")

    # Check for Vercel's cron verification header
    vercel_cron = request.headers.get("x-vercel-cron")
    if vercel_cron:
        return True

    # Check for Bearer token authorization
    if authorization and cron_secret:
        if authorization == f"Bearer {cron_secret}":
            return True

    # In development (no CRON_SECRET set), allow all requests
    if not cron_secret:
        return True

    return False


@router.get("/sync")
async def cron_sync(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Midnight sync job - imports new activities from Garmin and Hevy.

    This endpoint is called automatically by Vercel Cron at 5:00 UTC (midnight EST).
    It can also be triggered manually with proper authorization.

    Security: Verifies either Vercel Cron header or CRON_SECRET Bearer token.
    """
    # Verify authorization
    if not verify_cron_auth(authorization, request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    athlete_id = int(os.getenv("ATHLETE_ID", "1"))
    days = 2  # Look back 2 days to catch any missed activities

    db = SessionLocal()
    results = {
        "date": str(date.today()),
        "athlete_id": athlete_id,
        "days_synced": days,
        "garmin_activities": None,
        "garmin_wellness": None,
        "hevy": None,
        "goal_analysis": None,
        "errors": []
    }

    try:
        # Sync Garmin activities
        try:
            garmin = GarminActivityImporter(db, athlete_id)
            imported, skipped, errors = garmin.import_recent_activities(days)
            results["garmin_activities"] = {
                "imported": imported,
                "skipped": skipped,
                "errors": errors
            }
            if errors:
                results["errors"].extend([f"Garmin Activities: {e}" for e in errors])
        except Exception as e:
            results["garmin_activities"] = {"imported": 0, "skipped": 0, "errors": [str(e)]}
            results["errors"].append(f"Garmin activities sync failed: {str(e)}")

        # Sync Garmin wellness data (sleep, stress, HRV, body battery, etc.)
        try:
            wellness = GarminWellnessImporter(db, athlete_id)
            imported, updated, errors = wellness.import_recent_wellness(days)
            wellness.update_athlete_metrics()
            results["garmin_wellness"] = {
                "imported": imported,
                "updated": updated,
                "errors": errors
            }
            if errors:
                results["errors"].extend([f"Garmin Wellness: {e}" for e in errors])
        except Exception as e:
            results["garmin_wellness"] = {"imported": 0, "updated": 0, "errors": [str(e)]}
            results["errors"].append(f"Garmin wellness sync failed: {str(e)}")

        # Sync Hevy workouts
        try:
            hevy = HevyActivityImporter(db, athlete_id)
            imported, skipped, errors = hevy.import_recent_workouts(days)
            results["hevy"] = {
                "imported": imported,
                "skipped": skipped,
                "errors": errors
            }
            if errors:
                results["errors"].extend([f"Hevy: {e}" for e in errors])
        except Exception as e:
            results["hevy"] = {"imported": 0, "skipped": 0, "errors": [str(e)]}
            results["errors"].append(f"Hevy sync failed: {str(e)}")

        # Run goal analysis and generate recommendations
        try:
            analyzer = WorkoutRecommendationEngine(db, athlete_id)
            recommendations = analyzer.generate_weekly_recommendations()
            results["goal_analysis"] = {
                "goals_analyzed": len(recommendations.get("goal_progress", [])),
                "priority_focus": recommendations.get("priority_focus"),
                "recommendations_count": len(recommendations.get("recommendations", []))
            }
        except Exception as e:
            results["goal_analysis"] = {"error": str(e)}
            results["errors"].append(f"Goal analysis failed: {str(e)}")

        # Calculate totals
        total_imported = (
            (results["garmin_activities"]["imported"] if results["garmin_activities"] else 0) +
            (results["garmin_wellness"]["imported"] if results["garmin_wellness"] else 0) +
            (results["hevy"]["imported"] if results["hevy"] else 0)
        )

        results["summary"] = {
            "total_imported": total_imported,
            "status": "completed" if not results["errors"] else "completed_with_errors"
        }

        return results

    finally:
        db.close()


@router.get("/sync/status")
async def cron_status():
    """
    Simple status check for the cron endpoint.
    Returns basic info without requiring authentication.
    """
    return {
        "endpoint": "/api/cron/sync",
        "schedule": "0 5 * * * (5:00 UTC daily)",
        "status": "configured"
    }
