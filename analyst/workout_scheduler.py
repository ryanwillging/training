"""
Workout scheduler for assigning dates and managing training plan state.
"""

import json
from datetime import date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session

from analyst.plan_parser import PlanParser, Workout, WorkoutType, TrainingPlan
from database.models import Athlete, ScheduledWorkout
from api.timezone import get_eastern_today


@dataclass
class ScheduledWorkoutInfo:
    """Information about a scheduled workout."""
    workout: Workout
    status: str  # "scheduled", "completed", "skipped", "modified"
    garmin_workout_id: Optional[str] = None
    actual_date: Optional[date] = None
    modifications: Optional[Dict] = None


class WorkoutScheduler:
    """
    Manages workout scheduling, date assignment, and plan state.
    """

    def __init__(self, db: Session, athlete_id: int, plan_path: str):
        self.db = db
        self.athlete_id = athlete_id
        self.plan_path = plan_path
        self.parser = PlanParser(plan_path)
        self.plan: Optional[TrainingPlan] = None

    def initialize_plan(self, start_date: date) -> TrainingPlan:
        """
        Initialize the training plan with a start date.
        This generates all workouts with their scheduled dates.
        """
        self.plan = self.parser.generate_full_plan(start_date)

        # Store plan metadata in athlete record
        athlete = self.db.query(Athlete).filter(Athlete.id == self.athlete_id).first()
        if athlete:
            goals_data = athlete.goals or {}
            if isinstance(goals_data, str):
                goals_data = json.loads(goals_data)
            goals_data["training_plan"] = {
                "name": self.plan.name,
                "start_date": start_date.isoformat(),
                "total_weeks": self.plan.total_weeks,
                "test_weeks": self.plan.test_weeks,
                "initialized_at": get_eastern_today().isoformat(),
            }
            athlete.goals = json.dumps(goals_data) if isinstance(athlete.goals, str) else goals_data
            self.db.commit()

        return self.plan

    def get_current_week(self, start_date: date) -> int:
        """Calculate the current week number based on start date."""
        days_elapsed = (get_eastern_today() - start_date).days
        return min(max(1, (days_elapsed // 7) + 1), 24)

    def get_workouts_for_week(self, week_number: int) -> List[Workout]:
        """Get all workouts scheduled for a specific week."""
        if not self.plan:
            return []
        return [w for w in self.plan.workouts if w.week_number == week_number]

    def get_upcoming_workouts(self, days: int = 7) -> List[Workout]:
        """Get workouts scheduled for the next N days."""
        if not self.plan:
            return []

        today = get_eastern_today()
        end_date = today + timedelta(days=days)

        return [
            w for w in self.plan.workouts
            if w.date and today <= w.date <= end_date
        ]

    def get_workout_for_date(self, target_date: date) -> Optional[Workout]:
        """Get the workout scheduled for a specific date."""
        if not self.plan:
            return None

        for w in self.plan.workouts:
            if w.date == target_date:
                return w
        return None

    def schedule_workout_to_db(self, workout: Workout) -> ScheduledWorkout:
        """
        Store a scheduled workout in the database.
        """
        # Check if already exists
        existing = self.db.query(ScheduledWorkout).filter(
            ScheduledWorkout.athlete_id == self.athlete_id,
            ScheduledWorkout.scheduled_date == workout.date,
            ScheduledWorkout.workout_type == workout.workout_type.value
        ).first()

        if existing:
            return existing

        scheduled = ScheduledWorkout(
            athlete_id=self.athlete_id,
            scheduled_date=workout.date,
            workout_type=workout.workout_type.value,
            workout_name=workout.name,
            week_number=workout.week_number,
            day_of_week=workout.day_of_week,
            is_test_week=workout.is_test_week,
            duration_minutes=workout.total_duration_minutes,
            workout_data_json=json.dumps(self._workout_to_dict(workout)),
            status="scheduled"
        )

        self.db.add(scheduled)
        self.db.commit()

        return scheduled

    def schedule_week_to_db(self, week_number: int) -> List[ScheduledWorkout]:
        """Schedule all workouts for a week to the database."""
        workouts = self.get_workouts_for_week(week_number)
        scheduled = []

        for workout in workouts:
            scheduled.append(self.schedule_workout_to_db(workout))

        return scheduled

    def mark_workout_completed(
        self,
        scheduled_date: date,
        workout_type: str,
        actual_data: Optional[Dict] = None
    ) -> bool:
        """Mark a scheduled workout as completed."""
        workout = self.db.query(ScheduledWorkout).filter(
            ScheduledWorkout.athlete_id == self.athlete_id,
            ScheduledWorkout.scheduled_date == scheduled_date,
            ScheduledWorkout.workout_type == workout_type
        ).first()

        if workout:
            workout.status = "completed"
            workout.completed_date = get_eastern_today()
            if actual_data:
                workout.actual_data_json = json.dumps(actual_data)
            self.db.commit()
            return True

        return False

    def mark_workout_skipped(
        self,
        scheduled_date: date,
        workout_type: str,
        reason: Optional[str] = None
    ) -> bool:
        """Mark a scheduled workout as skipped."""
        workout = self.db.query(ScheduledWorkout).filter(
            ScheduledWorkout.athlete_id == self.athlete_id,
            ScheduledWorkout.scheduled_date == scheduled_date,
            ScheduledWorkout.workout_type == workout_type
        ).first()

        if workout:
            workout.status = "skipped"
            if reason:
                workout.notes = reason
            self.db.commit()
            return True

        return False

    def modify_workout(
        self,
        scheduled_date: date,
        workout_type: str,
        modifications: Dict[str, Any]
    ) -> bool:
        """
        Apply modifications to a scheduled workout.
        Modifications can include intensity changes, volume adjustments, etc.
        """
        workout = self.db.query(ScheduledWorkout).filter(
            ScheduledWorkout.athlete_id == self.athlete_id,
            ScheduledWorkout.scheduled_date == scheduled_date,
            ScheduledWorkout.workout_type == workout_type
        ).first()

        if workout:
            workout.status = "modified"

            # Merge modifications with existing workout data
            workout_data = json.loads(workout.workout_data_json) if workout.workout_data_json else {}
            workout_data["modifications"] = modifications

            workout.workout_data_json = json.dumps(workout_data)
            workout.modification_reason = modifications.get("reason", "")
            self.db.commit()
            return True

        return False

    def get_plan_progress(self) -> Dict[str, Any]:
        """
        Get overall progress through the training plan.
        """
        scheduled = self.db.query(ScheduledWorkout).filter(
            ScheduledWorkout.athlete_id == self.athlete_id
        ).all()

        total_workouts = len(self.plan.workouts) if self.plan else len(scheduled)
        completed = len([s for s in scheduled if s.status == "completed"])
        skipped = len([s for s in scheduled if s.status == "skipped"])
        modified = len([s for s in scheduled if s.status == "modified"])
        scheduled_count = len([s for s in scheduled if s.status == "scheduled"])

        # Determine plan start date from athlete metadata when available.
        athlete = self.db.query(Athlete).filter(Athlete.id == self.athlete_id).first()
        plan_start: Optional[date] = None
        total_weeks = 24
        if athlete and athlete.goals:
            goals_data = json.loads(athlete.goals) if isinstance(athlete.goals, str) else athlete.goals
            plan_info = goals_data.get("training_plan", {})
            start_str = plan_info.get("start_date")
            if start_str:
                plan_start = date.fromisoformat(start_str)
            total_weeks = int(plan_info.get("total_weeks", total_weeks))

        # Calculate adherence rate
        attempted = completed + skipped
        adherence_rate = (completed / attempted * 100) if attempted > 0 else 0

        return {
            "total_planned": total_workouts,
            "scheduled_in_db": len(scheduled),
            "completed": completed,
            "skipped": skipped,
            "modified": modified,
            "pending": scheduled_count,
            "adherence_rate": round(adherence_rate, 1),
            "current_week": self.get_current_week(plan_start) if plan_start else None,
            "total_weeks": total_weeks,
        }

    def get_weekly_summary(self, week_number: int) -> Dict[str, Any]:
        """Get a dashboard-friendly summary of workouts for a specific week."""
        scheduled = self.db.query(ScheduledWorkout).filter(
            ScheduledWorkout.athlete_id == self.athlete_id,
            ScheduledWorkout.week_number == week_number
        ).order_by(ScheduledWorkout.scheduled_date).all()

        # Determine start/end dates from athlete plan metadata if present.
        athlete = self.db.query(Athlete).filter(Athlete.id == self.athlete_id).first()
        plan_start: Optional[date] = None
        if athlete and athlete.goals:
            goals_data = json.loads(athlete.goals) if isinstance(athlete.goals, str) else athlete.goals
            plan_info = goals_data.get("training_plan", {})
            start_str = plan_info.get("start_date")
            if start_str:
                plan_start = date.fromisoformat(start_str)

        if plan_start:
            week_start = plan_start + timedelta(weeks=week_number - 1)
            week_end = week_start + timedelta(days=6)
        elif scheduled:
            week_start = scheduled[0].scheduled_date
            week_end = scheduled[-1].scheduled_date
        else:
            week_start = None
            week_end = None

        completed = len([s for s in scheduled if s.status == "completed"])
        total = len(scheduled)
        completion_rate = round((completed / total * 100) if total > 0 else 0, 1)
        is_test_week = week_number in [2, 12, 24]
        if not plan_start and not scheduled:
            is_test_week = False

        return {
            "week_number": week_number,
            "start_date": week_start.isoformat() if week_start else None,
            "end_date": week_end.isoformat() if week_end else None,
            "is_test_week": is_test_week,
            "completion_rate": completion_rate,
            "workouts": [
                {
                    "id": s.id,
                    "workout_type": s.workout_type,
                    "workout_name": s.workout_name,
                    "scheduled_date": s.scheduled_date.isoformat() if s.scheduled_date else None,
                    "week_number": s.week_number,
                    "status": s.status,
                    "duration_minutes": s.duration_minutes,
                    "is_test_week": s.is_test_week,
                    "garmin_workout_id": s.garmin_workout_id,
                }
                for s in scheduled
            ],
            "completed": completed,
            "total": total,
        }

    def _workout_to_dict(self, workout: Workout) -> Dict[str, Any]:
        """Convert a workout to dictionary format."""
        return {
            "workout_type": workout.workout_type.value,
            "week_number": workout.week_number,
            "day_of_week": workout.day_of_week,
            "date": workout.date.isoformat() if workout.date else None,
            "name": workout.name,
            "is_test_week": workout.is_test_week,
            "total_duration_minutes": workout.total_duration_minutes,
            "phases": [
                {
                    "name": p.name,
                    "duration_minutes": p.duration_minutes,
                    "notes": p.notes,
                    "exercises": [
                        {
                            "name": e.name,
                            "sets": e.sets,
                            "reps": e.reps,
                            "rest_seconds": e.rest_seconds,
                            "intensity": e.intensity,
                            "notes": e.notes,
                        }
                        for e in p.exercises
                    ]
                }
                for p in workout.phases
            ]
        }

    def suggest_reschedule(
        self,
        missed_date: date,
        workout_type: str
    ) -> Optional[date]:
        """
        Suggest a reschedule date for a missed workout.
        Returns the next available rest day.
        """
        if not self.plan or not self.plan.start_date:
            return None

        # Look at next 7 days
        for i in range(1, 8):
            check_date = missed_date + timedelta(days=i)

            # Check if there's already a workout scheduled
            existing = self.get_workout_for_date(check_date)
            if not existing:
                return check_date

        return None


class PlanAdjuster:
    """
    Handles adjustments to the training plan based on progress and wellness data.
    """

    def __init__(self, scheduler: WorkoutScheduler):
        self.scheduler = scheduler

    def evaluate_adjustment_needed(
        self,
        wellness_data: Dict[str, Any],
        recent_performance: Dict[str, Any]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Evaluate if a plan adjustment is needed based on data.

        Returns:
            Tuple of (adjustment_needed, reason, suggested_changes)
        """
        suggested_changes = {}
        reasons = []

        # Check training readiness
        readiness = wellness_data.get("training_readiness_score")
        if readiness and readiness < 40:
            reasons.append(f"Low training readiness ({readiness})")
            suggested_changes["intensity_modifier"] = 0.8  # Reduce by 20%
            suggested_changes["reduce_volume"] = True

        # Check HRV status
        hrv_status = wellness_data.get("hrv_status")
        if hrv_status and hrv_status.lower() in ["low", "poor"]:
            reasons.append(f"HRV status is {hrv_status}")
            suggested_changes["add_recovery_day"] = True

        # Check sleep
        sleep_score = wellness_data.get("sleep_score")
        if sleep_score and sleep_score < 60:
            reasons.append(f"Poor sleep score ({sleep_score})")
            suggested_changes["intensity_modifier"] = min(
                suggested_changes.get("intensity_modifier", 1.0),
                0.85
            )

        # Check recent performance (looking for decline)
        if recent_performance.get("performance_trend") == "declining":
            reasons.append("Performance trend declining")
            suggested_changes["consider_deload"] = True

        adjustment_needed = len(reasons) > 0
        reason = "; ".join(reasons) if reasons else "No adjustment needed"

        return adjustment_needed, reason, suggested_changes

    def apply_intensity_modifier(
        self,
        workout: Workout,
        modifier: float
    ) -> Workout:
        """
        Apply an intensity modifier to a workout.
        For example, modifier=0.8 reduces all intensities by 20%.
        """
        # This would modify RPE targets, pace targets, etc.
        # For now, we just note the modification
        workout.notes = f"Intensity modified by {modifier:.0%}"
        return workout

    def generate_deload_week(self, original_week: int) -> List[Workout]:
        """
        Generate a deload version of a week's workouts.
        Reduces volume by 40-50% while maintaining some intensity.
        """
        if not self.scheduler.plan:
            return []

        original_workouts = self.scheduler.get_workouts_for_week(original_week)
        deload_workouts = []

        for workout in original_workouts:
            # Reduce sets/reps in each phase
            for phase in workout.phases:
                for exercise in phase.exercises:
                    if exercise.sets:
                        exercise.sets = max(1, int(exercise.sets * 0.6))

            workout.notes = "DELOAD - Reduced volume"
            workout.name = f"[DELOAD] {workout.name}"
            deload_workouts.append(workout)

        return deload_workouts
