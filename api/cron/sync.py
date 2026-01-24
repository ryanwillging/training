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
import json
import sys
import time
from datetime import date
from fastapi import APIRouter, HTTPException, Header, Request
from typing import Optional

from api.timezone import get_eastern_today, get_eastern_now
from database.base import SessionLocal
from database.models import CronLog
from integrations.garmin.activity_importer import GarminActivityImporter
from integrations.garmin.wellness_importer import GarminWellnessImporter
from integrations.hevy.activity_importer import HevyActivityImporter
from analyst.plan_manager import TrainingPlanManager

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
        "date": str(get_eastern_today()),
        "athlete_id": athlete_id,
        "days_synced": days,
        "garmin_activities": None,
        "garmin_wellness": None,
        "hevy": None,
        "errors": []
    }

    try:
        start_time = time.time()

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

        # Run AI-powered plan evaluation (unified evaluation pipeline)
        try:
            plan_manager = TrainingPlanManager(db, athlete_id)
            if plan_manager.get_plan_start_date():  # Only run if plan is initialized
                evaluation_results = plan_manager.run_nightly_evaluation(evaluation_type="nightly")
                evaluation_data = evaluation_results.get("evaluation", {})
                results["plan_evaluation"] = {
                    "current_week": evaluation_results.get("current_week"),
                    "assessment": evaluation_data.get("overall_assessment"),
                    "modifications_proposed": evaluation_results.get("modifications_proposed", 0),
                    "confidence": evaluation_data.get("confidence_score"),
                    "has_lifestyle_insights": bool(evaluation_data.get("lifestyle_insights"))
                }
                if evaluation_results.get("errors"):
                    results["errors"].extend([f"Plan evaluation: {e}" for e in evaluation_results["errors"]])

                # Clean up stale reviews (keep approved indefinitely, delete others after 1 day)
                cleanup_results = plan_manager.cleanup_stale_reviews()
                results["review_cleanup"] = cleanup_results
            else:
                results["plan_evaluation"] = {"status": "plan_not_initialized"}
        except Exception as e:
            results["plan_evaluation"] = {"error": str(e)}
            results["errors"].append(f"Plan evaluation failed: {str(e)}")

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

        # Persist to CronLog
        try:
            duration = time.time() - start_time

            # Determine status
            if not results["errors"]:
                status = "success"
            elif total_imported > 0:
                status = "partial"
            else:
                status = "failed"

            log_entry = CronLog(
                run_date=get_eastern_now(),
                job_type="sync",
                status=status,
                garmin_activities_imported=results["garmin_activities"]["imported"] if results["garmin_activities"] else 0,
                garmin_wellness_imported=results["garmin_wellness"]["imported"] if results["garmin_wellness"] else 0,
                hevy_imported=results["hevy"]["imported"] if results["hevy"] else 0,
                errors_json=json.dumps(results["errors"]) if results["errors"] else None,
                results_json=json.dumps(results),
                duration_seconds=round(duration, 2)
            )
            db.add(log_entry)
            db.commit()
        except Exception as log_error:
            # Don't let logging failures break sync
            print(f"Failed to persist CronLog: {log_error}", file=sys.stderr)
            db.rollback()

        return results

    finally:
        db.close()


@router.get("/sync/status")
async def cron_status():
    """
    Cron status with last run information.
    Shows when sync last ran and whether it succeeded.
    """
    db = SessionLocal()
    try:
        last_run = db.query(CronLog).filter(
            CronLog.job_type == "sync"
        ).order_by(CronLog.run_date.desc()).first()

        base_status = {
            "endpoint": "/api/cron/sync",
            "schedule": "0 5 * * * (5:00 UTC daily)",
            "status": "configured"
        }

        if not last_run:
            base_status["last_run"] = None
            return base_status

        # Use timezone-naive datetime for comparison (database stores naive datetimes)
        hours_since = (get_eastern_now().replace(tzinfo=None) - last_run.run_date).total_seconds() / 3600

        base_status["last_run"] = {
            "date": last_run.run_date.isoformat(),
            "status": last_run.status,
            "hours_ago": round(hours_since, 1),
            "activities_imported": last_run.garmin_activities_imported,
            "wellness_imported": last_run.garmin_wellness_imported,
            "hevy_imported": last_run.hevy_imported,
            "duration_seconds": last_run.duration_seconds,
            "errors": json.loads(last_run.errors_json) if last_run.errors_json else []
        }

        return base_status
    finally:
        db.close()
