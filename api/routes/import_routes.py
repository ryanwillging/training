"""
API routes for importing activities from external sources.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date, timedelta

from database.base import get_db
from api.schemas import ImportRequest, ImportResponse
from integrations.garmin.activity_importer import GarminActivityImporter
from integrations.hevy.activity_importer import HevyActivityImporter

router = APIRouter(prefix="/import", tags=["import"])


@router.post("/garmin/activities", response_model=ImportResponse)
def import_garmin_activities(
    request: ImportRequest,
    db: Session = Depends(get_db)
):
    """
    Import activities from Garmin Connect for a date range.

    Args:
        request: Import request with athlete_id, start_date, end_date
        db: Database session

    Returns:
        ImportResponse with counts and errors
    """
    try:
        importer = GarminActivityImporter(db, request.athlete_id)
        imported, skipped, errors = importer.import_activities(
            request.start_date,
            request.end_date
        )

        return ImportResponse(
            imported_count=imported,
            skipped_count=skipped,
            errors=errors,
            message=f"Imported {imported} activities, skipped {skipped}"
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/garmin/activities/recent", response_model=ImportResponse)
def import_recent_garmin_activities(
    athlete_id: int,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """
    Import recent Garmin activities (last N days).

    Args:
        athlete_id: Athlete ID
        days: Number of days to look back (default: 7)
        db: Database session

    Returns:
        ImportResponse with counts and errors
    """
    try:
        importer = GarminActivityImporter(db, athlete_id)
        imported, skipped, errors = importer.import_recent_activities(days)

        return ImportResponse(
            imported_count=imported,
            skipped_count=skipped,
            errors=errors,
            message=f"Imported {imported} activities from last {days} days, skipped {skipped}"
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/hevy/workouts", response_model=ImportResponse)
def import_hevy_workouts(
    request: ImportRequest,
    db: Session = Depends(get_db)
):
    """
    Import strength training workouts from Hevy for a date range.

    Args:
        request: Import request with athlete_id, start_date, end_date
        db: Database session

    Returns:
        ImportResponse with counts and errors
    """
    try:
        importer = HevyActivityImporter(db, request.athlete_id)
        imported, skipped, errors = importer.import_workouts(
            request.start_date,
            request.end_date
        )

        return ImportResponse(
            imported_count=imported,
            skipped_count=skipped,
            errors=errors,
            message=f"Imported {imported} workouts, skipped {skipped}"
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/hevy/workouts/recent", response_model=ImportResponse)
def import_recent_hevy_workouts(
    athlete_id: int,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """
    Import recent Hevy workouts (last N days).

    Args:
        athlete_id: Athlete ID
        days: Number of days to look back (default: 7)
        db: Database session

    Returns:
        ImportResponse with counts and errors
    """
    try:
        importer = HevyActivityImporter(db, athlete_id)
        imported, skipped, errors = importer.import_recent_workouts(days)

        return ImportResponse(
            imported_count=imported,
            skipped_count=skipped,
            errors=errors,
            message=f"Imported {imported} workouts from last {days} days, skipped {skipped}"
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/sync", response_model=dict)
def sync_all_sources(
    athlete_id: int,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """
    Sync activities from all sources (Garmin and Hevy) for recent days.

    Args:
        athlete_id: Athlete ID
        days: Number of days to look back (default: 7)
        db: Database session

    Returns:
        Combined import results from all sources
    """
    results = {
        "athlete_id": athlete_id,
        "days": days,
        "sources": {}
    }

    # Import from Garmin
    try:
        garmin_importer = GarminActivityImporter(db, athlete_id)
        garmin_imported, garmin_skipped, garmin_errors = garmin_importer.import_recent_activities(days)
        results["sources"]["garmin"] = {
            "imported": garmin_imported,
            "skipped": garmin_skipped,
            "errors": garmin_errors
        }
    except Exception as e:
        results["sources"]["garmin"] = {
            "imported": 0,
            "skipped": 0,
            "errors": [f"Garmin import failed: {str(e)}"]
        }

    # Import from Hevy
    try:
        hevy_importer = HevyActivityImporter(db, athlete_id)
        hevy_imported, hevy_skipped, hevy_errors = hevy_importer.import_recent_workouts(days)
        results["sources"]["hevy"] = {
            "imported": hevy_imported,
            "skipped": hevy_skipped,
            "errors": hevy_errors
        }
    except Exception as e:
        results["sources"]["hevy"] = {
            "imported": 0,
            "skipped": 0,
            "errors": [f"Hevy import failed: {str(e)}"]
        }

    # Calculate totals
    total_imported = results["sources"]["garmin"]["imported"] + results["sources"]["hevy"]["imported"]
    total_skipped = results["sources"]["garmin"]["skipped"] + results["sources"]["hevy"]["skipped"]

    results["summary"] = {
        "total_imported": total_imported,
        "total_skipped": total_skipped,
        "message": f"Synced {total_imported} activities from all sources"
    }

    return results
