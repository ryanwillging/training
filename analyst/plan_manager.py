"""
Training plan manager.
Orchestrates plan parsing, scheduling, Garmin sync, and AI evaluation.
"""

import json
import os
from datetime import date, timedelta, datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from analyst.plan_parser import PlanParser, Workout, WorkoutType, TrainingPlan
from analyst.workout_scheduler import WorkoutScheduler, PlanAdjuster
from analyst.chatgpt_evaluator import ChatGPTEvaluator, PlanEvaluation, PlanModification, LifestyleInsight
from database.models import (
    Athlete, DailyWellness, ScheduledWorkout, DailyReview, Goal, GoalProgress,
    CompletedActivity, WorkoutAnalysis, PlanAdjustment
)

# Lazy import for Garmin - not available in Vercel serverless
GARMIN_AVAILABLE = False
GarminWorkoutManager = None
GarminWorkout = None
WorkoutSportType = None
try:
    from integrations.garmin.workout_manager import (
        GarminWorkoutManager, GarminWorkout, WorkoutSportType
    )
    GARMIN_AVAILABLE = True
except ImportError:
    pass


class TrainingPlanManager:
    """
    Central manager for the training plan system.
    Coordinates all components for plan execution and adaptation.
    """

    PLAN_PATH = "plans/base_training_plan.md"

    def __init__(self, db: Session, athlete_id: int):
        self.db = db
        self.athlete_id = athlete_id

        # Initialize components
        self.parser = PlanParser(self.PLAN_PATH)
        self.scheduler = WorkoutScheduler(db, athlete_id, self.PLAN_PATH)
        self.adjuster = PlanAdjuster(self.scheduler)

        # These will be initialized on demand
        self._garmin_manager: Optional[GarminWorkoutManager] = None
        self._ai_evaluator: Optional[ChatGPTEvaluator] = None

    @property
    def garmin_manager(self) -> Optional["GarminWorkoutManager"]:
        """Lazy load Garmin workout manager. Returns None if not available."""
        if not GARMIN_AVAILABLE:
            return None
        if self._garmin_manager is None:
            self._garmin_manager = GarminWorkoutManager()
        return self._garmin_manager

    @property
    def ai_evaluator(self) -> ChatGPTEvaluator:
        """Lazy load ChatGPT evaluator."""
        if self._ai_evaluator is None:
            # Use o1-preview for deep reasoning, fall back to gpt-4o if not available
            model = os.getenv("OPENAI_MODEL", "o1-preview")
            self._ai_evaluator = ChatGPTEvaluator(model=model)
        return self._ai_evaluator

    def initialize_plan(self, start_date: date) -> Dict[str, Any]:
        """
        Initialize the training plan with a start date.
        Creates all scheduled workouts in the database.

        Args:
            start_date: First day of the 24-week plan (should be a Monday)

        Returns:
            Summary of initialization
        """
        # Parse and generate the plan
        plan = self.scheduler.initialize_plan(start_date)

        # Schedule all workouts to database
        total_scheduled = 0
        for week in range(1, plan.total_weeks + 1):
            scheduled = self.scheduler.schedule_week_to_db(week)
            total_scheduled += len(scheduled)

        return {
            "plan_name": plan.name,
            "start_date": start_date.isoformat(),
            "total_weeks": plan.total_weeks,
            "total_workouts_scheduled": total_scheduled,
            "test_weeks": plan.test_weeks,
            "status": "initialized"
        }

    def get_plan_start_date(self) -> Optional[date]:
        """Get the plan start date from athlete record."""
        athlete = self.db.query(Athlete).filter(Athlete.id == self.athlete_id).first()
        if athlete and athlete.goals:
            goals_data = json.loads(athlete.goals) if isinstance(athlete.goals, str) else athlete.goals
            plan_info = goals_data.get("training_plan", {})
            start_str = plan_info.get("start_date")
            if start_str:
                return date.fromisoformat(start_str)
        return None

    def get_current_week(self) -> int:
        """Get the current week number in the plan."""
        start_date = self.get_plan_start_date()
        if start_date:
            return self.scheduler.get_current_week(start_date)
        return 1

    def sync_workouts_to_garmin(
        self,
        week_number: Optional[int] = None,
        days_ahead: int = 7
    ) -> Dict[str, Any]:
        """
        Sync scheduled workouts to Garmin Connect calendar.

        Args:
            week_number: Specific week to sync, or None for upcoming days
            days_ahead: Number of days ahead to sync (if week_number is None)

        Returns:
            Sync results
        """
        results = {
            "synced": [],
            "failed": [],
            "skipped": []
        }

        # Check if Garmin integration is available
        if not GARMIN_AVAILABLE or self.garmin_manager is None:
            results["failed"].append({
                "error": "Garmin integration not available in serverless environment"
            })
            return results

        # Get workouts to sync
        if week_number:
            workouts = self.db.query(ScheduledWorkout).filter(
                ScheduledWorkout.athlete_id == self.athlete_id,
                ScheduledWorkout.week_number == week_number,
                ScheduledWorkout.garmin_workout_id.is_(None)  # Not yet synced
            ).all()
        else:
            today = date.today()
            end_date = today + timedelta(days=days_ahead)
            workouts = self.db.query(ScheduledWorkout).filter(
                ScheduledWorkout.athlete_id == self.athlete_id,
                ScheduledWorkout.scheduled_date >= today,
                ScheduledWorkout.scheduled_date <= end_date,
                ScheduledWorkout.garmin_workout_id.is_(None)
            ).all()

        for scheduled in workouts:
            try:
                # Convert to Garmin workout
                garmin_workout = self._create_garmin_workout(scheduled)
                if garmin_workout:
                    # Upload and schedule
                    workout_id, success = self.garmin_manager.create_and_schedule_workout(
                        garmin_workout,
                        scheduled.scheduled_date
                    )

                    if workout_id:
                        scheduled.garmin_workout_id = workout_id
                        scheduled.garmin_calendar_date = scheduled.scheduled_date
                        self.db.commit()
                        results["synced"].append({
                            "date": scheduled.scheduled_date.isoformat(),
                            "type": scheduled.workout_type,
                            "garmin_id": workout_id
                        })
                    else:
                        results["failed"].append({
                            "date": scheduled.scheduled_date.isoformat(),
                            "type": scheduled.workout_type,
                            "error": "Failed to upload"
                        })
                else:
                    results["skipped"].append({
                        "date": scheduled.scheduled_date.isoformat(),
                        "type": scheduled.workout_type,
                        "reason": "Could not create Garmin workout format"
                    })

            except Exception as e:
                results["failed"].append({
                    "date": scheduled.scheduled_date.isoformat(),
                    "type": scheduled.workout_type,
                    "error": str(e)
                })

        return results

    def _create_garmin_workout(self, scheduled: ScheduledWorkout) -> Optional["GarminWorkout"]:
        """Convert a scheduled workout to Garmin format."""
        if not GARMIN_AVAILABLE or self.garmin_manager is None:
            return None

        workout_data = json.loads(scheduled.workout_data_json) if scheduled.workout_data_json else {}

        if scheduled.workout_type in ["swim_a", "swim_b", "swim_test"]:
            # Get main set description from workout data
            main_set = ""
            for phase in workout_data.get("phases", []):
                if "main" in phase.get("name", "").lower():
                    exercises = phase.get("exercises", [])
                    if exercises:
                        main_set = exercises[0].get("notes", "") or exercises[0].get("description", "")
                    break

            return self.garmin_manager.create_swim_workout(
                name=scheduled.workout_name or f"Swim Week {scheduled.week_number}",
                week_number=scheduled.week_number,
                main_set_description=main_set or "See workout details",
                is_test_day=(scheduled.workout_type == "swim_test")
            )

        elif scheduled.workout_type in ["lift_a", "lift_b"]:
            exercises = []
            for phase in workout_data.get("phases", []):
                if "main" in phase.get("name", "").lower():
                    for ex in phase.get("exercises", []):
                        exercises.append({
                            "name": ex.get("name", "Exercise"),
                            "sets": ex.get("sets", 3),
                            "reps": ex.get("reps", "8-10"),
                            "notes": ex.get("notes", "")
                        })

            workout_type = "lower" if scheduled.workout_type == "lift_a" else "upper"
            return self.garmin_manager.create_strength_workout(
                name=scheduled.workout_name or f"Lift Week {scheduled.week_number}",
                week_number=scheduled.week_number,
                workout_type=workout_type,
                exercises=exercises
            )

        elif scheduled.workout_type == "vo2":
            # Parse VO2 workout parameters
            main_set = {}
            for phase in workout_data.get("phases", []):
                if "main" in phase.get("name", "").lower():
                    exercises = phase.get("exercises", [])
                    if exercises:
                        ex = exercises[0]
                        main_set = {
                            "intervals": ex.get("sets", 6),
                            "duration": ex.get("reps", "2 min").replace(" min", ""),
                            "intensity": ex.get("intensity", "hard")
                        }
                    break

            return self.garmin_manager.create_vo2_workout(
                name=scheduled.workout_name or f"VO2 Week {scheduled.week_number}",
                week_number=scheduled.week_number,
                intervals=int(main_set.get("intervals", 6)),
                interval_duration_minutes=float(main_set.get("duration", 2)),
                rest_duration_minutes=2.0,
                intensity=main_set.get("intensity", "hard (RPE 8)")
            )

        return None

    def run_nightly_evaluation(
        self,
        user_context: Optional[str] = None,
        evaluation_type: str = "nightly"
    ) -> Dict[str, Any]:
        """
        Run the AI evaluation of training progress.

        This is called by the cron job (nightly) or manually via /reviews page (on_demand).

        Args:
            user_context: Optional user-provided context or notes for the AI to consider
            evaluation_type: "nightly" for cron jobs, "on_demand" for manual evaluations

        Returns:
            Evaluation results and any proposed modifications
        """
        results = {
            "evaluation_date": date.today().isoformat(),
            "current_week": self.get_current_week(),
            "evaluation": None,
            "modifications_proposed": 0,
            "user_context_provided": bool(user_context),
            "evaluation_type": evaluation_type,
            "errors": []
        }

        try:
            # Gather data for evaluation
            wellness_data = self._get_recent_wellness(days=7)
            recent_workouts = self._get_recent_workouts(days=14)
            goal_progress = self._get_goal_progress()
            upcoming_workouts = self._get_upcoming_workouts(days=7)
            plan_summary = self._get_plan_summary()

            # Run AI evaluation
            evaluation = self.ai_evaluator.evaluate_progress(
                current_week=results["current_week"],
                wellness_data=wellness_data,
                recent_workouts=recent_workouts,
                goal_progress=goal_progress,
                scheduled_workouts=upcoming_workouts,
                plan_summary=plan_summary,
                user_context=user_context
            )

            # Convert lifestyle insights to dict format
            lifestyle_insights_dict = {}
            for insight in evaluation.lifestyle_insights:
                lifestyle_insights_dict[insight.category] = {
                    "observation": insight.observation,
                    "severity": insight.severity,
                    "actions": insight.actions
                }

            results["evaluation"] = {
                "overall_assessment": evaluation.overall_assessment,
                "progress_summary": evaluation.progress_summary,
                "next_week_focus": evaluation.next_week_focus,
                "warnings": evaluation.warnings,
                "confidence_score": evaluation.confidence_score,
                "lifestyle_insights": lifestyle_insights_dict
            }
            results["modifications_proposed"] = len(evaluation.modifications)

            # Store evaluation in daily review (with user context and evaluation type)
            self._store_daily_review(
                evaluation,
                user_context=user_context,
                evaluation_type=evaluation_type
            )

            # If modifications are needed and confidence is high, apply them
            if evaluation.modifications and evaluation.confidence_score >= 0.7:
                for mod in evaluation.modifications:
                    if mod.priority == "high":
                        self._apply_modification(mod)

        except Exception as e:
            error_msg = f"Evaluation error: {str(e)}"
            results["errors"].append(error_msg)

            # Store a failed evaluation record so we have history
            self._store_failed_evaluation(user_context, error_msg, evaluation_type)

        return results

    def _store_failed_evaluation(
        self,
        user_context: Optional[str],
        error_msg: str,
        evaluation_type: str = "nightly"
    ) -> None:
        """Store a record of a failed evaluation attempt. Updates existing if present."""
        try:
            today = date.today()
            progress_summary = json.dumps({
                "overall_assessment": "error",
                "error": error_msg
            })

            # Check for existing review today
            existing = self.db.query(DailyReview).filter(
                DailyReview.athlete_id == self.athlete_id,
                DailyReview.review_date == today
            ).first()

            if existing:
                existing.progress_summary = progress_summary
                existing.insights = f"Evaluation failed: {error_msg}"
                existing.proposed_adjustments = json.dumps([])
                existing.approval_status = "error"
                existing.user_context = user_context
                existing.evaluation_type = evaluation_type
            else:
                review = DailyReview(
                    athlete_id=self.athlete_id,
                    review_date=today,
                    progress_summary=progress_summary,
                    insights=f"Evaluation failed: {error_msg}",
                    proposed_adjustments=json.dumps([]),
                    approval_status="error",
                    user_context=user_context,
                    evaluation_type=evaluation_type
                )
                self.db.add(review)

            self.db.commit()
        except Exception:
            # If we can't store the error, just log it
            self.db.rollback()

    def _get_recent_wellness(self, days: int) -> Dict[str, Any]:
        """Get averaged wellness data for the past N days."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        wellness_records = self.db.query(DailyWellness).filter(
            DailyWellness.athlete_id == self.athlete_id,
            DailyWellness.date >= start_date,
            DailyWellness.date <= end_date
        ).all()

        if not wellness_records:
            return {}

        # Calculate averages
        def avg(values):
            valid = [v for v in values if v is not None]
            return sum(valid) / len(valid) if valid else None

        return {
            "sleep_score_avg": avg([w.sleep_score for w in wellness_records]),
            "training_readiness_avg": avg([w.training_readiness_score for w in wellness_records]),
            "hrv_avg": avg([w.hrv_weekly_avg for w in wellness_records]),
            "resting_hr_avg": avg([w.resting_heart_rate for w in wellness_records]),
            "stress_avg": avg([w.avg_stress_level for w in wellness_records]),
            "body_battery_avg": avg([w.body_battery_high for w in wellness_records]),
            "latest_training_status": wellness_records[-1].training_status if wellness_records else None,
            "latest_vo2_max": wellness_records[-1].vo2_max_running if wellness_records else None,
            "days_of_data": len(wellness_records)
        }

    def _get_recent_workouts(self, days: int) -> List[Dict[str, Any]]:
        """Get completed workouts from the past N days."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        activities = self.db.query(CompletedActivity).filter(
            CompletedActivity.athlete_id == self.athlete_id,
            CompletedActivity.activity_date >= start_date,
            CompletedActivity.activity_date <= end_date
        ).order_by(CompletedActivity.activity_date.desc()).all()

        return [
            {
                "date": a.activity_date.isoformat(),
                "type": a.activity_type,
                "name": a.activity_name,
                "duration_minutes": a.duration_minutes,
                "source": a.source
            }
            for a in activities
        ]

    def _get_goal_progress(self) -> Dict[str, Any]:
        """Get current progress toward all active goals."""
        goals = self.db.query(Goal).filter(
            Goal.athlete_id == self.athlete_id,
            Goal.status == "active"
        ).all()

        progress = {}
        for goal in goals:
            latest_progress = self.db.query(GoalProgress).filter(
                GoalProgress.goal_id == goal.id
            ).order_by(GoalProgress.date.desc()).first()

            progress[goal.name] = {
                "target": goal.target_value,
                "current": latest_progress.current_value if latest_progress else goal.baseline_value,
                "progress_percent": latest_progress.progress_percent if latest_progress else 0,
                "trend": latest_progress.trend if latest_progress else "unknown",
                "on_track": latest_progress.on_track if latest_progress else None
            }

        return progress

    def _get_upcoming_workouts(self, days: int) -> List[Dict[str, Any]]:
        """Get scheduled workouts for the next N days."""
        today = date.today()
        end_date = today + timedelta(days=days)

        scheduled = self.db.query(ScheduledWorkout).filter(
            ScheduledWorkout.athlete_id == self.athlete_id,
            ScheduledWorkout.scheduled_date >= today,
            ScheduledWorkout.scheduled_date <= end_date,
            ScheduledWorkout.status == "scheduled"
        ).order_by(ScheduledWorkout.scheduled_date).all()

        return [
            {
                "date": s.scheduled_date.isoformat(),
                "type": s.workout_type,
                "name": s.workout_name,
                "week": s.week_number,
                "is_test_week": s.is_test_week
            }
            for s in scheduled
        ]

    def _get_plan_summary(self) -> str:
        """Get a summary of the training plan for context."""
        current_week = self.get_current_week()
        start_date = self.get_plan_start_date()

        return f"""24-Week Performance Plan
Current Week: {current_week} of 24
Start Date: {start_date.isoformat() if start_date else 'Not set'}
Test Weeks: 1, 12, 24
Weekly Structure: Swim A (Mon), Lift A (Tue), VO2 (Wed), Swim B (Thu), Lift B (Fri)
Goals: Maintain 14% body fat, Increase VO2 max, Improve 400y freestyle time"""

    def _store_daily_review(
        self,
        evaluation: PlanEvaluation,
        user_context: Optional[str] = None,
        evaluation_type: str = "nightly"
    ) -> None:
        """Store the evaluation in the daily_reviews table. Updates existing if present."""
        today = date.today()

        # Check for existing review today
        existing = self.db.query(DailyReview).filter(
            DailyReview.athlete_id == self.athlete_id,
            DailyReview.review_date == today
        ).first()

        progress_summary = json.dumps({
            "overall_assessment": evaluation.overall_assessment,
            "confidence_score": evaluation.confidence_score
        })
        proposed_adjustments = json.dumps([
            {
                "type": m.modification_type,
                "week": m.week_number,
                "workout_type": m.workout_type,
                "description": m.description,
                "reason": m.reason,
                "priority": m.priority,
                "status": "pending",
                "actioned_at": None
            }
            for m in evaluation.modifications
        ])
        approval_status = "pending" if evaluation.modifications else "no_changes_needed"

        # Convert lifestyle insights to JSON
        lifestyle_insights_dict = {}
        for insight in evaluation.lifestyle_insights:
            lifestyle_insights_dict[insight.category] = {
                "observation": insight.observation,
                "severity": insight.severity,
                "actions": insight.actions
            }
        lifestyle_insights_json = json.dumps(lifestyle_insights_dict)

        if existing:
            # Update existing review
            existing.progress_summary = progress_summary
            existing.insights = evaluation.progress_summary
            existing.recommendations = evaluation.next_week_focus
            existing.proposed_adjustments = proposed_adjustments
            existing.approval_status = approval_status
            existing.user_context = user_context
            existing.evaluation_type = evaluation_type
            existing.lifestyle_insights_json = lifestyle_insights_json
        else:
            # Create new review
            review = DailyReview(
                athlete_id=self.athlete_id,
                review_date=today,
                progress_summary=progress_summary,
                insights=evaluation.progress_summary,
                recommendations=evaluation.next_week_focus,
                proposed_adjustments=proposed_adjustments,
                approval_status=approval_status,
                user_context=user_context,
                evaluation_type=evaluation_type,
                lifestyle_insights_json=lifestyle_insights_json
            )
            self.db.add(review)

        self.db.commit()

    def _apply_modification(self, modification: PlanModification) -> bool:
        """Apply a high-priority modification to the plan."""
        try:
            if modification.modification_type == "intensity":
                # Reduce intensity for affected workouts
                self.scheduler.modify_workout(
                    scheduled_date=date.today() + timedelta(days=modification.day_of_week or 0),
                    workout_type=modification.workout_type or "",
                    modifications={
                        "intensity_modifier": 0.85,
                        "reason": modification.reason
                    }
                )
                return True

            elif modification.modification_type == "add_rest":
                # Mark a workout as skipped for recovery
                if modification.day_of_week:
                    target_date = date.today() + timedelta(days=modification.day_of_week)
                    self.scheduler.mark_workout_skipped(
                        target_date,
                        modification.workout_type or "",
                        reason=modification.reason
                    )
                return True

            # Other modification types would be handled here
            return False

        except Exception as e:
            print(f"✗ Error applying modification: {e}")
            return False

    def apply_approved_modifications(self, modifications: List[Dict[str, Any]], sync_to_garmin: bool = True) -> Dict[str, Any]:
        """
        Apply approved modifications to the training plan and optionally sync to Garmin.

        Args:
            modifications: List of modification dictionaries from DailyReview.proposed_adjustments
            sync_to_garmin: Whether to sync changes to Garmin Connect

        Returns:
            Results of applying modifications
        """
        results = {
            "applied": [],
            "failed": [],
            "garmin_synced": [],
            "garmin_failed": []
        }

        # Check if Garmin is available
        if sync_to_garmin and not GARMIN_AVAILABLE:
            results["garmin_failed"].append({
                "action": "skip_all",
                "error": "Garmin integration not available in serverless environment"
            })
            sync_to_garmin = False  # Disable Garmin sync for this run

        for mod in modifications:
            mod_type = mod.get("type", "unknown")
            week_number = mod.get("week")
            workout_type = mod.get("workout_type")
            description = mod.get("description", "")
            reason = mod.get("reason", "")

            try:
                # Find the affected scheduled workout
                target_workout = None
                if week_number and workout_type:
                    target_workout = self.db.query(ScheduledWorkout).filter(
                        ScheduledWorkout.athlete_id == self.athlete_id,
                        ScheduledWorkout.week_number == week_number,
                        ScheduledWorkout.workout_type == workout_type
                    ).first()

                if mod_type == "add_rest" or mod_type == "skip":
                    # Mark workout as skipped
                    if target_workout:
                        old_garmin_id = target_workout.garmin_workout_id
                        target_workout.status = "skipped"
                        target_workout.modification_reason = reason
                        target_workout.modified_by = "ai"
                        self.db.commit()

                        results["applied"].append({
                            "type": mod_type,
                            "workout": workout_type,
                            "week": week_number,
                            "action": "marked_skipped"
                        })

                        # Delete from Garmin if it was synced
                        if sync_to_garmin and old_garmin_id:
                            try:
                                self.garmin_manager.delete_workout(old_garmin_id)
                                target_workout.garmin_workout_id = None
                                target_workout.garmin_calendar_date = None
                                self.db.commit()
                                results["garmin_synced"].append({
                                    "action": "deleted",
                                    "workout_id": old_garmin_id
                                })
                            except Exception as e:
                                results["garmin_failed"].append({
                                    "action": "delete",
                                    "error": str(e)
                                })
                    else:
                        results["failed"].append({
                            "type": mod_type,
                            "reason": f"Could not find workout: week {week_number}, type {workout_type}"
                        })

                elif mod_type == "intensity" or mod_type == "volume":
                    # Modify the workout intensity/volume
                    if target_workout:
                        # Update the workout data to reflect reduced intensity
                        workout_data = json.loads(target_workout.workout_data_json) if target_workout.workout_data_json else {}
                        workout_data["intensity_modifier"] = 0.85 if mod_type == "intensity" else 0.9
                        workout_data["modification_reason"] = reason
                        target_workout.workout_data_json = json.dumps(workout_data)
                        target_workout.modification_reason = reason
                        target_workout.modified_by = "ai"
                        target_workout.status = "modified"

                        old_garmin_id = target_workout.garmin_workout_id
                        self.db.commit()

                        results["applied"].append({
                            "type": mod_type,
                            "workout": workout_type,
                            "week": week_number,
                            "action": "modified"
                        })

                        # Re-sync to Garmin if it was previously synced
                        if sync_to_garmin and old_garmin_id:
                            try:
                                # Delete old workout
                                self.garmin_manager.delete_workout(old_garmin_id)

                                # Create new workout with modifications
                                garmin_workout = self._create_garmin_workout(target_workout)
                                if garmin_workout:
                                    new_id, scheduled = self.garmin_manager.create_and_schedule_workout(
                                        garmin_workout,
                                        target_workout.scheduled_date
                                    )
                                    if new_id:
                                        target_workout.garmin_workout_id = new_id
                                        target_workout.garmin_calendar_date = target_workout.scheduled_date
                                        self.db.commit()
                                        results["garmin_synced"].append({
                                            "action": "replaced",
                                            "old_id": old_garmin_id,
                                            "new_id": new_id
                                        })
                            except Exception as e:
                                results["garmin_failed"].append({
                                    "action": "replace",
                                    "error": str(e)
                                })

                elif mod_type == "reschedule":
                    # Move workout to a different day
                    new_date_str = mod.get("new_date")
                    if target_workout and new_date_str:
                        try:
                            new_date = date.fromisoformat(new_date_str)
                            old_date = target_workout.scheduled_date
                            old_garmin_id = target_workout.garmin_workout_id

                            target_workout.scheduled_date = new_date
                            target_workout.modification_reason = reason
                            target_workout.modified_by = "ai"
                            self.db.commit()

                            results["applied"].append({
                                "type": mod_type,
                                "workout": workout_type,
                                "from_date": str(old_date),
                                "to_date": str(new_date),
                                "action": "rescheduled"
                            })

                            # Update Garmin calendar
                            if sync_to_garmin and old_garmin_id:
                                try:
                                    # Delete old scheduled workout
                                    self.garmin_manager.delete_workout(old_garmin_id)

                                    # Re-create and schedule on new date
                                    garmin_workout = self._create_garmin_workout(target_workout)
                                    if garmin_workout:
                                        new_id, scheduled = self.garmin_manager.create_and_schedule_workout(
                                            garmin_workout,
                                            new_date
                                        )
                                        if new_id:
                                            target_workout.garmin_workout_id = new_id
                                            target_workout.garmin_calendar_date = new_date
                                            self.db.commit()
                                            results["garmin_synced"].append({
                                                "action": "rescheduled",
                                                "new_date": str(new_date),
                                                "new_id": new_id
                                            })
                                except Exception as e:
                                    results["garmin_failed"].append({
                                        "action": "reschedule",
                                        "error": str(e)
                                    })
                        except ValueError:
                            results["failed"].append({
                                "type": mod_type,
                                "reason": f"Invalid date format: {new_date_str}"
                            })

                elif mod_type == "swap_workout":
                    # Swap one workout type for another
                    new_workout_type = mod.get("new_workout_type")
                    if target_workout and new_workout_type:
                        old_type = target_workout.workout_type
                        old_garmin_id = target_workout.garmin_workout_id

                        target_workout.workout_type = new_workout_type
                        target_workout.workout_name = f"{new_workout_type.replace('_', ' ').title()} - Week {week_number} (swapped)"
                        target_workout.modification_reason = reason
                        target_workout.modified_by = "ai"
                        self.db.commit()

                        results["applied"].append({
                            "type": mod_type,
                            "from_type": old_type,
                            "to_type": new_workout_type,
                            "week": week_number,
                            "action": "swapped"
                        })

                        # Update Garmin
                        if sync_to_garmin and old_garmin_id:
                            try:
                                self.garmin_manager.delete_workout(old_garmin_id)
                                garmin_workout = self._create_garmin_workout(target_workout)
                                if garmin_workout:
                                    new_id, scheduled = self.garmin_manager.create_and_schedule_workout(
                                        garmin_workout,
                                        target_workout.scheduled_date
                                    )
                                    if new_id:
                                        target_workout.garmin_workout_id = new_id
                                        self.db.commit()
                                        results["garmin_synced"].append({
                                            "action": "swapped",
                                            "new_id": new_id
                                        })
                            except Exception as e:
                                results["garmin_failed"].append({
                                    "action": "swap",
                                    "error": str(e)
                                })

                else:
                    results["failed"].append({
                        "type": mod_type,
                        "reason": f"Unknown modification type: {mod_type}"
                    })

            except Exception as e:
                results["failed"].append({
                    "type": mod_type,
                    "reason": str(e)
                })

        return results

    def get_weekly_summary(self, week_number: Optional[int] = None) -> Dict[str, Any]:
        """
        Get a summary of a training week.

        Args:
            week_number: Week to summarize, or current week if None
        """
        if week_number is None:
            week_number = self.get_current_week()

        return self.scheduler.get_weekly_summary(week_number)

    def get_plan_status(self) -> Dict[str, Any]:
        """Get overall status of the training plan."""
        progress = self.scheduler.get_plan_progress()
        current_week = self.get_current_week()
        start_date = self.get_plan_start_date()

        return {
            "initialized": start_date is not None,
            "start_date": start_date.isoformat() if start_date else None,
            "current_week": current_week,
            "progress": progress,
            "is_test_week": current_week in [1, 12, 24]
        }

    def cleanup_stale_reviews(self) -> Dict[str, int]:
        """
        Clean up stale reviews older than 1 day.
        Keeps approved reviews indefinitely for audit trail.
        Deletes: pending, rejected, error, no_changes_needed reviews older than 1 day.

        Returns:
            Count of deleted reviews by status
        """
        cutoff_date = date.today() - timedelta(days=1)

        # Find stale reviews (not approved, older than cutoff)
        stale_reviews = self.db.query(DailyReview).filter(
            DailyReview.athlete_id == self.athlete_id,
            DailyReview.review_date < cutoff_date,
            DailyReview.approval_status.in_(["pending", "rejected", "error", "no_changes_needed"])
        ).all()

        counts = {"pending": 0, "rejected": 0, "error": 0, "no_changes_needed": 0}

        for review in stale_reviews:
            status = review.approval_status or "pending"
            counts[status] = counts.get(status, 0) + 1
            self.db.delete(review)

        self.db.commit()

        return {
            "total_deleted": sum(counts.values()),
            "by_status": counts,
            "cutoff_date": cutoff_date.isoformat()
        }

    @staticmethod
    def calculate_review_status(adjustments: List[Dict[str, Any]]) -> str:
        """
        Calculate overall review status based on individual modification statuses.

        Args:
            adjustments: List of modification dictionaries

        Returns:
            Review status: 'pending', 'approved', 'rejected', or 'no_changes_needed'
        """
        if not adjustments:
            return "no_changes_needed"

        statuses = [adj.get("status", "pending") for adj in adjustments]

        # If all are actioned (approved or rejected)
        if all(s in ("approved", "rejected") for s in statuses):
            # If any were approved, mark review as approved
            if any(s == "approved" for s in statuses):
                return "approved"
            else:
                return "rejected"
        # If any are still pending, review is pending
        elif any(s == "pending" for s in statuses):
            return "pending"
        else:
            return "pending"  # Default fallback

    def action_single_modification(
        self,
        review_id: int,
        mod_index: int,
        action: str
    ) -> Dict[str, Any]:
        """
        Approve or reject a single modification within a review.

        Args:
            review_id: ID of the DailyReview
            mod_index: Index of the modification in the adjustments list
            action: 'approve' or 'reject'

        Returns:
            Result of the action including any Garmin sync results
        """
        from datetime import datetime

        # Get the review
        review = self.db.query(DailyReview).filter(
            DailyReview.id == review_id,
            DailyReview.athlete_id == self.athlete_id
        ).first()

        if not review:
            raise ValueError("Review not found")

        # Parse adjustments
        adjustments = json.loads(review.proposed_adjustments) if review.proposed_adjustments else []

        if not adjustments:
            raise ValueError("No modifications in this review")

        if mod_index < 0 or mod_index >= len(adjustments):
            raise ValueError(f"Invalid modification index: {mod_index}")

        mod = adjustments[mod_index]

        # Check if already actioned
        current_status = mod.get("status", "pending")
        if current_status != "pending":
            raise ValueError(f"Modification already {current_status}")

        result = {
            "status": "success",
            "review_id": review_id,
            "modification_index": mod_index,
            "action": action,
            "garmin_sync": None
        }

        # Update the modification status
        mod["status"] = action + "d"  # 'approved' or 'rejected'
        mod["actioned_at"] = datetime.utcnow().isoformat()

        if action == "approve":
            # Apply this single modification
            try:
                garmin_results = self.apply_approved_modifications([mod], sync_to_garmin=True)
                result["garmin_sync"] = garmin_results

                # Create PlanAdjustment record for audit trail
                plan_adj = PlanAdjustment(
                    plan_id=1,  # Default plan
                    review_id=review.id,
                    adjustment_date=date.today(),
                    adjustment_type=mod.get("type", "unknown"),
                    reasoning=mod.get("reason", ""),
                    changes=json.dumps(mod)
                )
                self.db.add(plan_adj)
            except Exception as e:
                result["garmin_sync"] = {"error": str(e)}

        # Update the review with modified adjustments
        review.proposed_adjustments = json.dumps(adjustments)

        # Recalculate overall review status
        new_review_status = self.calculate_review_status(adjustments)
        review.approval_status = new_review_status

        # If all modifications have been actioned, mark the timestamp
        if new_review_status in ("approved", "rejected"):
            review.approved_at = datetime.utcnow()

        self.db.commit()

        result["new_review_status"] = new_review_status
        return result
