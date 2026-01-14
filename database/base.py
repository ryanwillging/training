"""
Database engine and session configuration.
Supports SQLite (local development) and PostgreSQL (Vercel production).
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment
# On Vercel (VERCEL env var set), require PostgreSQL - no SQLite fallback
if os.getenv("VERCEL"):
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    if not DATABASE_URL:
        # Use in-memory SQLite as placeholder (won't persist but won't crash)
        DATABASE_URL = "sqlite:///:memory:"
else:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./training.db")

# Vercel Postgres uses 'postgres://' but SQLAlchemy requires 'postgresql://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


def _create_engine():
    """Create database engine based on DATABASE_URL."""
    if DATABASE_URL.startswith("sqlite"):
        # SQLite configuration for local development
        return create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},
            echo=False,
        )
    elif DATABASE_URL.startswith("postgresql"):
        # PostgreSQL configuration optimized for serverless (Vercel)
        connect_args = {}
        # Enable SSL for cloud PostgreSQL providers
        if any(x in DATABASE_URL.lower() for x in ["vercel", "neon", "supabase", "railway"]):
            connect_args["sslmode"] = "require"

        return create_engine(
            DATABASE_URL,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args=connect_args,
            echo=False,
        )
    else:
        return create_engine(DATABASE_URL, echo=False)


# Create engine
engine = _create_engine()

# Create SessionLocal class for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency function for FastAPI to get database session.
    Usage:
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database by creating all tables.
    This should be called once when setting up the application.
    """
    from database import models  # Import models to register them with Base

    Base.metadata.create_all(bind=engine)
    print(f"Database initialized at: {DATABASE_URL}")
