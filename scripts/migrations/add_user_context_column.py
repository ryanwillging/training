#!/usr/bin/env python3
"""
Migration script to add user_context column to daily_reviews table.
Works with both SQLite (local) and PostgreSQL (production).

Usage:
    # Local (uses .env or defaults to SQLite):
    python scripts/add_user_context_column.py

    # Production (pass DATABASE_URL):
    DATABASE_URL="postgresql://..." python scripts/add_user_context_column.py
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Load dotenv BEFORE importing database module
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text, inspect, create_engine


def get_engine():
    """Create engine based on DATABASE_URL."""
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./training.db")

    # Convert postgres:// to postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    if DATABASE_URL.startswith("sqlite"):
        return create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    elif DATABASE_URL.startswith("postgresql"):
        connect_args = {}
        if any(x in DATABASE_URL.lower() for x in ["vercel", "neon", "supabase", "railway"]):
            connect_args["sslmode"] = "require"
        return create_engine(DATABASE_URL, connect_args=connect_args)
    else:
        return create_engine(DATABASE_URL)


def main():
    print("Adding user_context column to daily_reviews table...")

    engine = get_engine()

    # Check database dialect
    dialect = engine.dialect.name
    print(f"Database: {dialect}")

    with engine.connect() as conn:
        # Check if column already exists
        inspector = inspect(engine)
        columns = [c['name'] for c in inspector.get_columns('daily_reviews')]

        if 'user_context' in columns:
            print("✓ Column user_context already exists")
            return

        # Add the column
        conn.execute(text("""
            ALTER TABLE daily_reviews
            ADD COLUMN user_context TEXT
        """))
        conn.commit()

        print("✓ Added user_context column to daily_reviews table")


if __name__ == "__main__":
    main()
