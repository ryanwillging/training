"""
API routes for manual metrics entry (body composition, performance tests, subjective metrics).
"""

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.base import get_db
from database.models import ProgressMetric, Athlete
from api.schemas import (
    BodyCompositionEntry,
    PerformanceTestEntry,
    SubjectiveMetricsEntry,
    MetricsResponse
)

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.post("/body-composition", response_model=MetricsResponse)
def log_body_composition(
    entry: BodyCompositionEntry,
    db: Session = Depends(get_db)
):
    """
    Log body composition measurements (body fat %, weight).

    Args:
        entry: Body composition data
        db: Database session

    Returns:
        MetricsResponse with confirmation
    """
    # Verify athlete exists
    athlete = db.query(Athlete).filter(Athlete.id == entry.athlete_id).first()
    if not athlete:
        raise HTTPException(status_code=404, detail=f"Athlete {entry.athlete_id} not found")

    try:
        # Create body fat % metric if provided
        if entry.body_fat_pct is not None:
            body_fat_metric = ProgressMetric(
                athlete_id=entry.athlete_id,
                metric_date=entry.measurement_date,
                metric_type="body_fat",
                value_numeric=entry.body_fat_pct,
                measurement_method=entry.measurement_method,
                notes=entry.notes
            )
            db.add(body_fat_metric)

            # Update athlete's current body fat
            athlete.current_body_fat = entry.body_fat_pct

        # Create weight metric if provided
        if entry.weight_lbs is not None:
            weight_metric = ProgressMetric(
                athlete_id=entry.athlete_id,
                metric_date=entry.measurement_date,
                metric_type="weight",
                value_numeric=entry.weight_lbs,
                measurement_method=entry.measurement_method,
                notes=entry.notes
            )
            db.add(weight_metric)

            # Update athlete's current weight
            athlete.current_weight_lbs = entry.weight_lbs

        db.commit()

        metrics_logged = []
        if entry.body_fat_pct:
            metrics_logged.append(f"body fat {entry.body_fat_pct}%")
        if entry.weight_lbs:
            metrics_logged.append(f"weight {entry.weight_lbs} lbs")

        return MetricsResponse(
            id=body_fat_metric.id if entry.body_fat_pct else weight_metric.id,
            metric_type="body_composition",
            message=f"Logged {', '.join(metrics_logged)} for {entry.measurement_date}"
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to log metrics: {str(e)}")


@router.post("/performance-test", response_model=MetricsResponse)
def log_performance_test(
    entry: PerformanceTestEntry,
    db: Session = Depends(get_db)
):
    """
    Log performance test results (100yd freestyle, broad jump, box jump, etc.).

    Args:
        entry: Performance test data
        db: Database session

    Returns:
        MetricsResponse with confirmation
    """
    # Verify athlete exists
    athlete = db.query(Athlete).filter(Athlete.id == entry.athlete_id).first()
    if not athlete:
        raise HTTPException(status_code=404, detail=f"Athlete {entry.athlete_id} not found")

    try:
        metric = ProgressMetric(
            athlete_id=entry.athlete_id,
            metric_date=entry.test_date,
            metric_type=entry.metric_type,
            value_numeric=entry.value,
            value_text=f"{entry.value} {entry.unit}",
            notes=entry.notes
        )
        db.add(metric)
        db.commit()
        db.refresh(metric)

        return MetricsResponse(
            id=metric.id,
            metric_type=entry.metric_type,
            message=f"Logged {entry.metric_type}: {entry.value} {entry.unit}"
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to log test: {str(e)}")


@router.post("/subjective", response_model=MetricsResponse)
def log_subjective_metrics(
    entry: SubjectiveMetricsEntry,
    db: Session = Depends(get_db)
):
    """
    Log subjective metrics (sleep quality, soreness, energy level, stress).

    Args:
        entry: Subjective metrics data
        db: Database session

    Returns:
        MetricsResponse with confirmation
    """
    # Verify athlete exists
    athlete = db.query(Athlete).filter(Athlete.id == entry.athlete_id).first()
    if not athlete:
        raise HTTPException(status_code=404, detail=f"Athlete {entry.athlete_id} not found")

    try:
        # Compile subjective metrics into JSON
        subjective_data = {}
        if entry.sleep_quality is not None:
            subjective_data["sleep_quality"] = entry.sleep_quality
        if entry.soreness_level is not None:
            subjective_data["soreness_level"] = entry.soreness_level
        if entry.energy_level is not None:
            subjective_data["energy_level"] = entry.energy_level
        if entry.stress_level is not None:
            subjective_data["stress_level"] = entry.stress_level

        metric = ProgressMetric(
            athlete_id=entry.athlete_id,
            metric_date=entry.entry_date,
            metric_type="subjective",
            value_json=json.dumps(subjective_data),
            notes=entry.notes
        )
        db.add(metric)
        db.commit()
        db.refresh(metric)

        metrics_summary = ", ".join([f"{k.replace('_', ' ')}: {v}/10" for k, v in subjective_data.items()])

        return MetricsResponse(
            id=metric.id,
            metric_type="subjective",
            message=f"Logged subjective metrics: {metrics_summary}"
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to log metrics: {str(e)}")


@router.get("/history/{metric_type}")
def get_metric_history(
    metric_type: str,
    athlete_id: int,
    limit: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get historical data for a specific metric type.

    Args:
        metric_type: Type of metric to retrieve
        athlete_id: Athlete ID
        limit: Number of recent entries to return
        db: Database session

    Returns:
        List of metric entries
    """
    # Verify athlete exists
    athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()
    if not athlete:
        raise HTTPException(status_code=404, detail=f"Athlete {athlete_id} not found")

    try:
        metrics = db.query(ProgressMetric).filter(
            ProgressMetric.athlete_id == athlete_id,
            ProgressMetric.metric_type == metric_type
        ).order_by(ProgressMetric.metric_date.desc()).limit(limit).all()

        results = []
        for metric in metrics:
            result = {
                "id": metric.id,
                "date": metric.metric_date,
                "value": metric.value_numeric,
                "value_text": metric.value_text,
                "notes": metric.notes
            }

            # Parse JSON if present
            if metric.value_json:
                try:
                    result["data"] = json.loads(metric.value_json)
                except:
                    pass

            results.append(result)

        return {
            "metric_type": metric_type,
            "athlete_id": athlete_id,
            "count": len(results),
            "data": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")
