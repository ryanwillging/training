"""
SQLAlchemy ORM models for the training optimization system.
"""

from datetime import datetime, date, time
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Date,
    Time,
    DateTime,
    Text,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from database.base import Base


class Athlete(Base):
    """
    Athlete profile and goals.
    """

    __tablename__ = "athletes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Current metrics
    current_body_fat = Column(Float)  # Percentage
    current_vo2_max = Column(Integer)  # ml/kg/min
    current_weight_lbs = Column(Float)

    # Goals stored as JSON text
    goals = Column(Text, nullable=False)  # JSON string

    # Preferences
    preferred_pool_length = Column(String, default="25y")
    weekly_volume_target_hours = Column(Float, default=4.0)
    timezone = Column(String, default="America/New_York")

    # Relationships
    training_plans = relationship("TrainingPlan", back_populates="athlete")
    completed_activities = relationship("CompletedActivity", back_populates="athlete")
    progress_metrics = relationship("ProgressMetric", back_populates="athlete")
    daily_reviews = relationship("DailyReview", back_populates="athlete")

    def __repr__(self):
        return f"<Athlete(id={self.id}, name='{self.name}', email='{self.email}')>"


class TrainingPlan(Base):
    """
    Training plan with metadata and schedule.
    """

    __tablename__ = "training_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False)
    name = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    status = Column(
        String, default="active"
    )  # 'active', 'completed', 'paused', 'archived'

    # Plan metadata
    plan_type = Column(
        String
    )  # '6-week-swim', 'athletic-performance', 'custom', etc.
    weekly_volume_target_hours = Column(Float)
    focus_areas = Column(Text)  # JSON array: ["swim", "strength", "vo2", "flexibility"]

    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    athlete = relationship("Athlete", back_populates="training_plans")
    planned_workouts = relationship("PlannedWorkout", back_populates="plan")
    plan_adjustments = relationship("PlanAdjustment", back_populates="plan")

    def __repr__(self):
        return f"<TrainingPlan(id={self.id}, name='{self.name}', status='{self.status}')>"


class PlannedWorkout(Base):
    """
    Individual planned workout within a training plan.
    """

    __tablename__ = "planned_workouts"
    __table_args__ = (
        Index("idx_planned_workouts_date", "scheduled_date"),
        Index("idx_planned_workouts_plan_date", "plan_id", "scheduled_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("training_plans.id"), nullable=False)
    scheduled_date = Column(Date, nullable=False)
    scheduled_time = Column(Time)  # Preferred time (e.g., 06:00 for morning)

    # Workout details
    workout_type = Column(
        String, nullable=False
    )  # 'swim', 'strength', 'vo2_intervals', 'flexibility', 'run', 'bike'
    workout_name = Column(String)  # e.g., "W1S1 - CSS Baseline", "Lower Body Strength"
    estimated_duration_minutes = Column(Integer)

    # Workout definition (JSON - schema varies by type)
    workout_definition = Column(Text, nullable=False)  # JSON string

    # Metadata
    priority = Column(
        String, default="normal"
    )  # 'critical', 'high', 'normal', 'optional'
    notes = Column(Text)
    completed = Column(Boolean, default=False)
    completed_activity_id = Column(Integer, ForeignKey("completed_activities.id"))

    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    plan = relationship("TrainingPlan", back_populates="planned_workouts")
    completed_activity = relationship("CompletedActivity", foreign_keys=[completed_activity_id])

    def __repr__(self):
        return f"<PlannedWorkout(id={self.id}, type='{self.workout_type}', date={self.scheduled_date})>"


class CompletedActivity(Base):
    """
    Completed workout activity from Garmin, Hevy, or manual entry.
    """

    __tablename__ = "completed_activities"
    __table_args__ = (
        UniqueConstraint(
            "athlete_id", "source", "external_id", name="uix_athlete_source_external"
        ),
        Index("idx_completed_activities_date", "athlete_id", "activity_date"),
        Index("idx_completed_activities_source", "source", "external_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False)
    activity_date = Column(Date, nullable=False)
    activity_time = Column(Time)

    # Source tracking
    source = Column(
        String, nullable=False
    )  # 'garmin', 'hevy', 'manual', 'apple_health'
    external_id = Column(String)  # ID from source system (for deduplication)

    # Activity details
    activity_type = Column(
        String, nullable=False
    )  # 'swim', 'run', 'bike', 'strength', 'other'
    activity_name = Column(String)
    duration_minutes = Column(Integer)

    # Detailed data (JSON - schema varies by type)
    activity_data = Column(Text, nullable=False)  # JSON string

    # Links
    planned_workout_id = Column(Integer, ForeignKey("planned_workouts.id"))

    # Metadata
    imported_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    athlete = relationship("Athlete", back_populates="completed_activities")
    planned_workout = relationship("PlannedWorkout", foreign_keys=[planned_workout_id])

    def __repr__(self):
        return f"<CompletedActivity(id={self.id}, type='{self.activity_type}', date={self.activity_date}, source='{self.source}')>"


class ProgressMetric(Base):
    """
    Progress tracking for goals (body fat, VO2 max, swim times, etc.).
    """

    __tablename__ = "progress_metrics"
    __table_args__ = (
        Index("idx_progress_metrics_athlete_type", "athlete_id", "metric_type", "metric_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False)
    metric_date = Column(Date, nullable=False)
    metric_type = Column(
        String, nullable=False
    )  # 'body_fat', 'vo2_max', '100yd_time', 'broad_jump', 'box_jump', etc.

    # Value storage (use appropriate field for data type)
    value_numeric = Column(Float)  # For numbers (body fat %, VO2 max, times, etc.)
    value_text = Column(String)  # For text values
    value_json = Column(Text)  # For complex data (multiple measurements, sets, etc.)

    # Context
    measurement_method = Column(
        String
    )  # e.g., 'inbody_scale', 'caliper', 'dexa', 'garmin_estimate'
    notes = Column(Text)

    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    athlete = relationship("Athlete", back_populates="progress_metrics")

    def __repr__(self):
        return f"<ProgressMetric(id={self.id}, type='{self.metric_type}', date={self.metric_date}, value={self.value_numeric})>"


class DailyReview(Base):
    """
    Daily review with analysis, insights, and proposed adjustments.
    Includes human approval tracking.
    """

    __tablename__ = "daily_reviews"
    __table_args__ = (
        UniqueConstraint("athlete_id", "review_date", name="uix_athlete_review_date"),
        Index("idx_daily_reviews_date", "athlete_id", "review_date"),
        Index("idx_daily_reviews_approval", "approval_status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False)
    review_date = Column(Date, nullable=False)

    # Analysis results (JSON)
    planned_vs_actual = Column(Text)  # Comparison data (JSON)
    adherence_metrics = Column(Text)  # Weekly adherence, volume, etc. (JSON)
    progress_summary = Column(Text)  # Progress toward each goal (JSON)

    # Insights
    insights = Column(Text)  # Generated insights (markdown or plain text)
    recommendations = Column(Text)  # Suggested actions (text)

    # Plan adjustments (proposed)
    proposed_adjustments = Column(Text)  # JSON array of proposed adjustments
    next_week_focus = Column(Text)  # Text summary

    # Human approval tracking (CRITICAL - human-in-the-loop workflow)
    approval_status = Column(
        String, default="pending"
    )  # 'pending', 'approved', 'rejected', 'no_changes_needed'
    approved_at = Column(DateTime)
    approval_notes = Column(Text)  # User's comments on approval/rejection

    # Export tracking
    adjustments_applied = Column(
        Boolean, default=False
    )  # Were adjustments applied to plan?
    workouts_exported = Column(Boolean, default=False)  # Were workouts exported to apps?
    exported_at = Column(DateTime)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    athlete = relationship("Athlete", back_populates="daily_reviews")
    plan_adjustments = relationship("PlanAdjustment", back_populates="review")

    def __repr__(self):
        return f"<DailyReview(id={self.id}, date={self.review_date}, status='{self.approval_status}')>"


class PlanAdjustment(Base):
    """
    Record of plan adjustments made (after human approval).
    """

    __tablename__ = "plan_adjustments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("training_plans.id"), nullable=False)
    review_id = Column(
        Integer, ForeignKey("daily_reviews.id")
    )  # Link to daily review that triggered it
    adjustment_date = Column(Date, nullable=False)

    # Adjustment details
    adjustment_type = Column(
        String, nullable=False
    )  # 'volume_change', 'focus_shift', 'reschedule', 'deload', 'exercise_swap'
    reasoning = Column(Text, nullable=False)

    # Changes (JSON)
    changes = Column(Text, nullable=False)  # JSON string with before/after details

    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    plan = relationship("TrainingPlan", back_populates="plan_adjustments")
    review = relationship("DailyReview", back_populates="plan_adjustments")

    def __repr__(self):
        return f"<PlanAdjustment(id={self.id}, type='{self.adjustment_type}', date={self.adjustment_date})>"
