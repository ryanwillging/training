"""
Training plan manager.
Orchestrates plan parsing, scheduling, Garmin sync, and AI evaluation.
"""

import json
import os
from datetime import date, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from analyst.plan_parser import PlanParser, Workout, WorkoutType, TrainingPlan
from analyst.workout_scheduler import WorkoutScheduler, PlanAdjuster
from analyst.chatgpt_evaluator import ChatGPTEvaluator, PlanEvaluation, PlanModification
from integrations.garmin.workout_manager import (
    GarminWorkoutManager, GarminWorkout, WorkoutSportType
)
from database.models import (
    Athlete, DailyWellness, ScheduledWorkout, DailyReview, Goal, GoalProgress,
    CompletedActivity, WorkoutAnalysis
)


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
    def garmin_manager(self) -> GarminWorkoutManager:
        """Lazy load Garmin workout manager."""
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

    def _create_garmin_workout(self, scheduled: ScheduledWorkout) -> Optional[GarminWorkout]:
        """Convert a scheduled workout to Garmin format."""
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

    def run_nightly_evaluation(self) -> Dict[str, Any]:
        """
        Run the nightly AI evaluation of training progress.

        This is called by the cron job after data sync.

        Returns:
            Evaluation results and any proposed modifications
        """
        results = {
            "evaluation_date": date.today().isoformat(),
            "current_week": self.get_current_week(),
            "evaluation": None,
            "modifications_proposed": 0,
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
                plan_summary=plan_summary
            )

            results["evaluation"] = {
                "overall_assessment": evaluation.overall_assessment,
                "progress_summary": evaluation.progress_summary,
                "next_week_focus": evaluation.next_week_focus,
                "warnings": evaluation.warnings,
                "confidence_score": evaluation.confidence_score
            }
            results["modifications_proposed"] = len(evaluation.modifications)

            # Store evaluation in daily review
            self._store_daily_review(evaluation)

            # If modifications are needed and confidence is high, apply them
            if evaluation.modifications and evaluation.confidence_score >= 0.7:
                for mod in evaluation.modifications:
                    if mod.priority == "high":
                        self._apply_modification(mod)

        except Exception as e:
            results["errors"].append(f"Evaluation error: {str(e)}")

        return results

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

    def _store_daily_review(self, evaluation: PlanEvaluation) -> None:
        """Store the evaluation in the daily_reviews table."""
        review = DailyReview(
            athlete_id=self.athlete_id,
            review_date=date.today(),
            progress_summary=json.dumps({
                "overall_assessment": evaluation.overall_assessment,
                "confidence_score": evaluation.confidence_score
            }),
            insights=evaluation.progress_summary,
            recommendations=evaluation.next_week_focus,
            proposed_adjustments=json.dumps([
                {
                    "type": m.modification_type,
                    "week": m.week_number,
                    "description": m.description,
                    "reason": m.reason,
                    "priority": m.priority
                }
                for m in evaluation.modifications
            ]),
            approval_status="pending" if evaluation.modifications else "no_changes_needed"
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
