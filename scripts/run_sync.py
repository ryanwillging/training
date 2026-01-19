#!/usr/bin/env python3
"""Run sync locally against production database."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env.prod, stripping any \n literals
env_file = project_root / ".env.prod"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                # Remove quotes and \n literals
                value = value.strip('"').strip("'").replace("\\n", "")
                os.environ[key] = value

from datetime import date, timedelta
from database.base import engine, Base, SessionLocal
from database.models import DailyWellness, CompletedActivity

def run_sync():
    """Run the full sync."""
    # Create tables
    print("Creating/verifying database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables ready.")

    db = SessionLocal()
    athlete_id = int(os.environ.get("ATHLETE_ID", "1"))
    days = 7
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    results = {
        "garmin_wellness": None,
        "garmin_activities": None,
        "hevy": None,
        "errors": []
    }

    # Sync Garmin wellness data
    try:
        from integrations.garmin.wellness_importer import GarminWellnessImporter
        print(f"\nSyncing Garmin wellness data for last {days} days...")
        importer = GarminWellnessImporter(db, athlete_id)
        imported = 0
        for i in range(days):
            target_date = end_date - timedelta(days=i)
            success, msg = importer.import_wellness_for_date(target_date)
            if success:
                imported += 1
            print(f"  {target_date}: {msg}")
        results["garmin_wellness"] = f"{imported} days imported"
        print(f"Wellness sync complete: {imported} days")
    except Exception as e:
        error = f"Garmin wellness sync failed: {str(e)}"
        results["errors"].append(error)
        print(error)
        import traceback
        traceback.print_exc()

    # Sync Garmin activities
    try:
        from integrations.garmin.activity_importer import GarminActivityImporter
        print(f"\nSyncing Garmin activities for last {days} days...")
        importer = GarminActivityImporter(db, athlete_id)
        imported, skipped, errors = importer.import_activities(start_date, end_date)
        results["garmin_activities"] = f"{imported} imported, {skipped} skipped"
        print(f"Activity sync complete: {imported} imported, {skipped} skipped")
        if errors:
            for err in errors:
                print(f"  Error: {err}")
    except Exception as e:
        error = f"Garmin activity sync failed: {str(e)}"
        results["errors"].append(error)
        print(error)
        import traceback
        traceback.print_exc()

    # Sync Hevy workouts
    try:
        from integrations.hevy.activity_importer import HevyActivityImporter
        print(f"\nSyncing Hevy workouts for last {days} days...")
        importer = HevyActivityImporter(db, athlete_id)
        imported, skipped, errors = importer.import_workouts(start_date, end_date)
        results["hevy"] = f"{imported} imported, {skipped} skipped"
        print(f"Hevy sync complete: {imported} imported, {skipped} skipped")
        if errors:
            for err in errors:
                print(f"  Error: {err}")
    except Exception as e:
        error = f"Hevy sync failed: {str(e)}"
        results["errors"].append(error)
        print(error)
        import traceback
        traceback.print_exc()

    # Show current wellness data
    print("\n--- Current Wellness Data ---")
    wellness = db.query(DailyWellness).order_by(DailyWellness.date.desc()).limit(5).all()
    if wellness:
        for w in wellness:
            print(f"{w.date}: TR={w.training_readiness_score}, Sleep={w.sleep_score}, BB={w.body_battery_high}/{w.body_battery_low}, Stress={w.avg_stress_level}, Steps={w.steps}")
    else:
        print("No wellness data found.")

    db.close()

    print("\n--- Sync Results ---")
    print(f"Garmin Wellness: {results['garmin_wellness']}")
    print(f"Garmin Activities: {results['garmin_activities']}")
    print(f"Hevy: {results['hevy']}")
    if results["errors"]:
        print(f"Errors: {results['errors']}")

    return results

if __name__ == "__main__":
    run_sync()
