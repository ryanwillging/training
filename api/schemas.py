"""
Pydantic schemas for API request/response validation.
"""

from typing import Optional, List
from datetime import date
from pydantic import BaseModel, Field


# Import Schemas
class ImportRequest(BaseModel):
    """Request schema for importing activities."""
    athlete_id: int = Field(..., description="Athlete ID")
    start_date: date = Field(..., description="Start date for import")
    end_date: date = Field(..., description="End date for import")


class ImportResponse(BaseModel):
    """Response schema for import operations."""
    imported_count: int = Field(..., description="Number of activities imported")
    skipped_count: int = Field(..., description="Number of activities skipped (already exist)")
    errors: List[str] = Field(default_factory=list, description="List of error messages")
    message: str = Field(..., description="Summary message")


# Activity Schemas
class ActivityBase(BaseModel):
    """Base schema for activities."""
    activity_date: date
    activity_type: str
    activity_name: Optional[str] = None
    duration_minutes: Optional[int] = None


class ActivityResponse(ActivityBase):
    """Response schema for activity."""
    id: int
    athlete_id: int
    source: str
    external_id: Optional[str] = None

    class Config:
        from_attributes = True


# Metrics Schemas
class BodyCompositionEntry(BaseModel):
    """Body composition metrics entry."""
    athlete_id: int
    measurement_date: date
    body_fat_pct: Optional[float] = Field(None, description="Body fat percentage")
    weight_lbs: Optional[float] = Field(None, description="Weight in pounds")
    measurement_method: str = Field("inbody_scale", description="Measurement method")
    notes: Optional[str] = None


class PerformanceTestEntry(BaseModel):
    """Performance test metrics entry."""
    athlete_id: int
    test_date: date
    metric_type: str = Field(..., description="Type of test (e.g., '100yd_freestyle', 'broad_jump')")
    value: float = Field(..., description="Test result value")
    unit: str = Field(..., description="Unit of measurement")
    notes: Optional[str] = None


class SubjectiveMetricsEntry(BaseModel):
    """Subjective metrics entry."""
    athlete_id: int
    entry_date: date
    sleep_quality: Optional[int] = Field(None, ge=1, le=10, description="Sleep quality (1-10)")
    soreness_level: Optional[int] = Field(None, ge=1, le=10, description="Soreness level (1-10)")
    energy_level: Optional[int] = Field(None, ge=1, le=10, description="Energy level (1-10)")
    stress_level: Optional[int] = Field(None, ge=1, le=10, description="Stress level (1-10)")
    notes: Optional[str] = None


class MetricsResponse(BaseModel):
    """Response schema for metrics entry."""
    id: int
    metric_type: str
    message: str
