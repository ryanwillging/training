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


class Report(Base):
    """
    Generated training reports (daily, weekly summaries).
    Stores HTML content for Tufte-style reports.
    """

    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False)
    report_date = Column(Date, nullable=False)
    report_type = Column(String, nullable=False)  # 'daily', 'weekly'

    # Report content
    html_content = Column(Text, nullable=False)

    # Metadata for quick access (JSON)
    metadata_json = Column(Text)  # Summary stats without parsing HTML

    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint: one report per athlete/date/type
    __table_args__ = (
        UniqueConstraint("athlete_id", "report_date", "report_type", name="uix_report_athlete_date_type"),
        Index("idx_reports_athlete_date", "athlete_id", "report_date"),
    )

    # Relationships
    athlete = relationship("Athlete")

    def __repr__(self):
        return f"<Report(id={self.id}, type='{self.report_type}', date={self.report_date})>"


class DailyWellness(Base):
    """
    Daily wellness data from Garmin (sleep, stress, HRV, body battery, etc.).
    One record per athlete per day.
    """

    __tablename__ = "daily_wellness"
    __table_args__ = (
        UniqueConstraint("athlete_id", "date", name="uix_wellness_athlete_date"),
        Index("idx_wellness_date", "athlete_id", "date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False)
    date = Column(Date, nullable=False)

    # Sleep metrics
    sleep_score = Column(Integer)  # 0-100
    sleep_duration_seconds = Column(Integer)
    sleep_deep_seconds = Column(Integer)
    sleep_light_seconds = Column(Integer)
    sleep_rem_seconds = Column(Integer)
    sleep_awake_seconds = Column(Integer)

    # Recovery & readiness
    body_battery_high = Column(Integer)  # Highest value of day
    body_battery_low = Column(Integer)   # Lowest value of day
    body_battery_charged = Column(Integer)  # Amount charged overnight
    training_readiness_score = Column(Integer)  # 0-100
    training_readiness_status = Column(String)  # 'OPTIMAL', 'PRIME', 'PRIMED', etc.

    # Stress
    avg_stress_level = Column(Integer)  # 0-100
    max_stress_level = Column(Integer)
    stress_duration_seconds = Column(Integer)  # Time in stress
    rest_duration_seconds = Column(Integer)  # Time at rest

    # Heart metrics
    resting_heart_rate = Column(Integer)  # bpm
    hrv_weekly_avg = Column(Integer)  # ms
    hrv_last_night = Column(Integer)  # ms
    hrv_status = Column(String)  # 'BALANCED', 'LOW', 'UNBALANCED', etc.

    # Respiratory
    avg_respiration_rate = Column(Float)  # breaths/min
    avg_spo2 = Column(Float)  # percentage

    # Activity summary
    steps = Column(Integer)
    floors_climbed = Column(Integer)
    active_calories = Column(Integer)
    total_calories = Column(Integer)

    # Training status (from Garmin)
    training_status = Column(String)  # 'PRODUCTIVE', 'MAINTAINING', 'RECOVERY', etc.
    training_load = Column(Float)  # 7-day load
    vo2_max_running = Column(Float)  # VO2 max estimate from running
    vo2_max_cycling = Column(Float)  # VO2 max estimate from cycling

    # Raw data storage for additional fields
    raw_data_json = Column(Text)  # Full JSON response for future use

    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    athlete = relationship("Athlete")

    def __repr__(self):
        return f"<DailyWellness(date={self.date}, sleep_score={self.sleep_score}, readiness={self.training_readiness_score})>"


class Goal(Base):
    """
    Structured goal definition with target values and tracking.
    """

    __tablename__ = "goals"
    __table_args__ = (
        Index("idx_goals_athlete_status", "athlete_id", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False)

    # Goal definition
    name = Column(String, nullable=False)  # "Reduce body fat to 14%"
    category = Column(String, nullable=False)  # 'body_composition', 'cardio', 'strength', 'flexibility', 'skill'
    metric_type = Column(String, nullable=False)  # Links to ProgressMetric metric_type

    # Target values
    target_value = Column(Float, nullable=False)
    target_unit = Column(String)  # '%', 'ml/kg/min', 'inches', 'seconds', etc.
    baseline_value = Column(Float)  # Starting point
    baseline_date = Column(Date)

    # Direction and bounds
    direction = Column(String, default="decrease")  # 'increase', 'decrease', 'maintain'
    min_acceptable = Column(Float)  # For 'maintain' goals
    max_acceptable = Column(Float)

    # Timeline
    target_date = Column(Date)  # When to achieve by
    status = Column(String, default="active")  # 'active', 'achieved', 'abandoned', 'paused'

    # Priority and notes
    priority = Column(Integer, default=2)  # 1=high, 2=medium, 3=low
    notes = Column(Text)

    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    achieved_at = Column(DateTime)

    # Relationships
    athlete = relationship("Athlete")
    progress_records = relationship("GoalProgress", back_populates="goal")

    def __repr__(self):
        return f"<Goal(id={self.id}, name='{self.name}', target={self.target_value}, status='{self.status}')>"


class GoalProgress(Base):
    """
    Track progress toward goals over time.
    """

    __tablename__ = "goal_progress"
    __table_args__ = (
        Index("idx_goal_progress_date", "goal_id", "date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=False)
    date = Column(Date, nullable=False)

    # Current state
    current_value = Column(Float)
    progress_percent = Column(Float)  # 0-100, how far toward goal

    # Analysis
    trend = Column(String)  # 'improving', 'stable', 'declining'
    days_to_target = Column(Integer)  # Estimated days to reach target at current rate
    on_track = Column(Boolean)  # Is progress on track for target_date?

    # Context
    notes = Column(Text)
    source = Column(String)  # 'garmin', 'manual', 'calculated'

    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    goal = relationship("Goal", back_populates="progress_records")

    def __repr__(self):
        return f"<GoalProgress(goal_id={self.goal_id}, date={self.date}, progress={self.progress_percent}%)>"


class WorkoutAnalysis(Base):
    """
    Analysis of workout patterns and recommendations.
    Generated periodically to assess training effectiveness.
    """

    __tablename__ = "workout_analyses"
    __table_args__ = (
        Index("idx_workout_analysis_date", "athlete_id", "analysis_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False)
    analysis_date = Column(Date, nullable=False)
    period_days = Column(Integer, default=7)  # Analysis period (7, 14, 30 days)

    # Volume analysis
    total_workouts = Column(Integer)
    total_duration_minutes = Column(Integer)
    workouts_by_type_json = Column(Text)  # {"swim": 2, "strength": 3, ...}

    # Intensity analysis
    avg_heart_rate = Column(Integer)
    time_in_zones_json = Column(Text)  # {"zone1": 120, "zone2": 45, ...} minutes

    # Goal alignment
    goal_alignment_json = Column(Text)  # {"goal_id": score, ...}
    overall_alignment_score = Column(Float)  # 0-100

    # Recommendations
    recommendations_json = Column(Text)  # List of recommendation objects
    priority_focus = Column(String)  # What to focus on next
    suggested_adjustments = Column(Text)  # Markdown text

    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    athlete = relationship("Athlete")

    def __repr__(self):
        return f"<WorkoutAnalysis(date={self.analysis_date}, alignment={self.overall_alignment_score})>"
