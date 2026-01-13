#!/usr/bin/env python3
"""
Database initialization script.
Creates all tables and optionally seeds initial data.

Usage:
    python scripts/setup_db.py
"""

import os
import sys
import json
from datetime import datetime

# Add parent directory to path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.base import init_db, SessionLocal
from database.models import Athlete


def create_initial_athlete(db):
    """
    Create initial athlete profile (Ryan Willging).
    """
    # Check if athlete already exists
    existing_athlete = db.query(Athlete).filter(Athlete.email == "ryan@example.com").first()
    if existing_athlete:
        print(f"✓ Athlete already exists: {existing_athlete.name}")
        return existing_athlete

    # Define goals
    goals = {
        "body_fat": {
            "target": 14.0,
            "unit": "%",
            "priority": "high",
            "current": None,  # To be measured
        },
        "vo2_max": {
            "target": 55,
            "unit": "ml/kg/min",
            "priority": "medium",
            "direction": "increase",
            "current": None,  # To be pulled from Garmin
        },
        "100yd_freestyle": {
            "target": 54,  # Example target - adjust after baseline
            "unit": "seconds",
            "priority": "high",
            "direction": "decrease",
            "current": None,  # To be tested
        },
        "explosive_strength": {
            "metrics": {
                "broad_jump": {
                    "current": 102,
                    "target": 108,
                    "unit": "inches",
                },
                "box_jump": {
                    "current": None,
                    "target": 36,
                    "unit": "inches",
                },
            },
            "priority": "medium",
        },
        "strength_endurance": {
            "metrics": {
                "dead_hang": {
                    "current": [70, 60],  # seconds per set
                    "target": [90, 75],
                    "unit": "seconds",
                },
                "pull_ups": {
                    "current": [10, 8, 7],  # reps per set
                    "target": [15, 12, 10],
                    "unit": "reps",
                },
            },
            "priority": "medium",
        },
        "weekly_volume": {
            "target": 4.0,
            "min": 3.0,
            "max": 5.0,
            "unit": "hours",
            "priority": "high",
        },
    }

    # Create athlete
    athlete = Athlete(
        name="Ryan Willging",
        email="ryan@example.com",
        goals=json.dumps(goals),
        preferred_pool_length="25y",
        weekly_volume_target_hours=4.0,
        timezone="America/New_York",
    )

    db.add(athlete)
    db.commit()
    db.refresh(athlete)

    print(f"✓ Created athlete: {athlete.name} (ID: {athlete.id})")
    return athlete


def main():
    """
    Main setup function.
    """
    print("=" * 60)
    print("Training Optimization System - Database Setup")
    print("=" * 60)
    print()

    # Initialize database (create all tables)
    print("Creating database tables...")
    init_db()
    print("✓ Database tables created successfully")
    print()

    # Create initial athlete
    db = SessionLocal()
    try:
        print("Creating initial athlete profile...")
        athlete = create_initial_athlete(db)
        print()

        # Show summary
        print("=" * 60)
        print("Setup Complete!")
        print("=" * 60)
        print(f"Athlete ID: {athlete.id}")
        print(f"Name: {athlete.name}")
        print(f"Email: {athlete.email}")
        print(f"Weekly Volume Target: {athlete.weekly_volume_target_hours} hours")
        print()
        print("Next steps:")
        print("1. Copy .env.example to .env and configure credentials")
        print("2. Run: training sync --days 7  (import recent activities)")
        print("3. Run: training review  (perform daily review)")
        print()

    except Exception as e:
        print(f"✗ Error during setup: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
