#!/usr/bin/env python3
"""
Migration script to add evaluation_type and lifestyle_insights_json columns to daily_reviews table.

Run with:
    source .env.local && python scripts/add_evaluation_columns.py
"""

import os
import sys

# Load environment FIRST before any imports
from dotenv import load_dotenv
load_dotenv(".env.local")  # Explicitly load .env.local

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_migration():
    """Add new columns to daily_reviews table."""
    from sqlalchemy import create_engine, text

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        print("Set it to your PostgreSQL connection string")
        sys.exit(1)

    # Remove quotes if present (from .env.local format)
    database_url = database_url.strip('"').strip("'")

    print(f"Connecting to database...")
    engine = create_engine(database_url)

    with engine.connect() as conn:
        # Check if columns already exist
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'daily_reviews'
            AND column_name IN ('evaluation_type', 'lifestyle_insights_json')
        """))
        existing_columns = [row[0] for row in result]

        # Add evaluation_type column if it doesn't exist
        if 'evaluation_type' not in existing_columns:
            print("Adding evaluation_type column...")
            conn.execute(text("""
                ALTER TABLE daily_reviews
                ADD COLUMN evaluation_type VARCHAR DEFAULT 'nightly'
            """))
            print("  Added evaluation_type column")

            # Update existing records to have 'nightly' as default
            result = conn.execute(text("""
                UPDATE daily_reviews
                SET evaluation_type = 'nightly'
                WHERE evaluation_type IS NULL
            """))
            print(f"  Updated {result.rowcount} existing records with default value")
        else:
            print("evaluation_type column already exists, skipping...")

        # Add lifestyle_insights_json column if it doesn't exist
        if 'lifestyle_insights_json' not in existing_columns:
            print("Adding lifestyle_insights_json column...")
            conn.execute(text("""
                ALTER TABLE daily_reviews
                ADD COLUMN lifestyle_insights_json TEXT
            """))
            print("  Added lifestyle_insights_json column")
        else:
            print("lifestyle_insights_json column already exists, skipping...")

        conn.commit()
        print("\nMigration completed successfully!")

        # Show current table structure
        result = conn.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'daily_reviews'
            ORDER BY ordinal_position
        """))
        print("\nCurrent daily_reviews columns:")
        for row in result:
            print(f"  {row[0]}: {row[1]} (nullable: {row[2]})")


if __name__ == "__main__":
    run_migration()
