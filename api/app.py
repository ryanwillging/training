"""
Training Optimization System - FastAPI Application
Main API server with routes for data import, metrics tracking, and daily reviews.
"""

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from garminconnect import Garmin
import os
from pathlib import Path
import tempfile

from api.routes import import_router, metrics_router, reports_router, plan_router
from api.cron.sync import router as cron_router

# Lazy database initialization to support serverless cold starts
_db_initialized = False

def ensure_db():
    """Initialize database tables on first use."""
    global _db_initialized
    if not _db_initialized:
        try:
            from database.base import engine, Base
            Base.metadata.create_all(bind=engine)
            _db_initialized = True
        except Exception as e:
            print(f"Database initialization skipped: {e}")

# Initialize FastAPI app
app = FastAPI(
    title="Training Optimization System API",
    description="AI-powered training coach that imports data, tracks progress, and optimizes training plans",
    version="0.1.0"
)

# Add CORS middleware (for future web UI)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(import_router, prefix="/api")
app.include_router(metrics_router, prefix="/api")
app.include_router(cron_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(plan_router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup if available."""
    ensure_db()


# Legacy endpoint - kept for backwards compatibility
def get_garmin_client() -> Garmin:
    """Get authenticated Garmin Connect client."""
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")
    if not email or not password:
        raise HTTPException(status_code=500, detail="GARMIN_EMAIL and GARMIN_PASSWORD must be set")

    client = Garmin(email, password)
    client.login()
    return client


@app.post("/import/fit")
async def import_fit(file: UploadFile = File(...)) -> dict:
    """
    Legacy endpoint: Upload FIT file to Garmin Connect.

    Note: This is a legacy endpoint from the original implementation.
    For importing activities from Garmin Connect, use /api/import/garmin/activities
    """
    if not file.filename or not file.filename.lower().endswith(".fit"):
        raise HTTPException(status_code=400, detail="Upload a .fit file")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir) / file.filename
        temp_path.write_bytes(data)

        client = get_garmin_client()
        result = client.upload_activity(str(temp_path))

    return {
        "filename": file.filename,
        "garmin_response": result,
    }


@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "name": "Training Optimization System API",
        "version": "0.1.0",
        "status": "operational",
        "endpoints": {
            "import": {
                "garmin": "/api/import/garmin/activities",
                "hevy": "/api/import/hevy/workouts",
                "sync": "/api/import/sync"
            },
            "metrics": {
                "body_composition": "/api/metrics/body-composition",
                "performance_test": "/api/metrics/performance-test",
                "subjective": "/api/metrics/subjective",
                "history": "/api/metrics/history/{metric_type}"
            },
            "cron": {
                "sync": "/api/cron/sync",
                "status": "/api/cron/sync/status"
            },
            "reports": {
                "daily": "/api/reports/daily",
                "weekly": "/api/reports/weekly"
            },
            "plan": {
                "status": "/api/plan/status",
                "initialize": "/api/plan/initialize",
                "week": "/api/plan/week",
                "sync_garmin": "/api/plan/sync-garmin",
                "evaluate": "/api/plan/evaluate",
                "upcoming": "/api/plan/upcoming"
            },
            "docs": "/docs",
            "openapi": "/openapi.json"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    db_status = "connected" if _db_initialized else "not_configured"
    return {"status": "healthy", "database": db_status}
