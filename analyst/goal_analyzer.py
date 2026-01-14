"""
Goal progress analyzer and workout recommendation engine.
Analyzes training data to assess progress toward goals and suggest adjustments.
"""

import json
from datetime import date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.models import (
    Athlete, Goal, GoalProgress, ProgressMetric, CompletedActivity,
    DailyWellness, WorkoutAnalysis
)


class GoalAnalyzer:
    """
    Analyze progress toward goals and generate recommendations.
    """

    def __init__(self, db: Session, athlete_id: int):
        self.db = db
        self.athlete_id = athlete_id

    def get_active_goals(self) -> List[Goal]:
        """Get all active goals for the athlete."""
        return self.db.query(Goal).filter(
            Goal.athlete_id == self.athlete_id,
            Goal.status == "active"
        ).all()

    def analyze_goal_progress(self, goal: Goal) -> Dict[str, Any]:
        """
        Analyze progress toward a specific goal.

        Returns dict with:
        - current_value: Latest measurement
        - progress_percent: How far toward goal (0-100)
        - trend: 'improving', 'stable', 'declining'
        - on_track: Boolean
        - days_to_target: Estimated days at current rate
        - recommendation: What to do
        """
        # Get recent metrics for this goal type
        metrics = self.db.query(ProgressMetric).filter(
            ProgressMetric.athlete_id == self.athlete_id,
            ProgressMetric.metric_type == goal.metric_type,
            ProgressMetric.value_numeric.isnot(None)
        ).order_by(ProgressMetric.metric_date.desc()).limit(10).all()

        if not metrics:
            return {
                "goal_id": goal.id,
                "goal_name": goal.name,
                "current_value": None,
                "progress_percent": 0,
                "trend": "unknown",
                "on_track": None,
                "days_to_target": None,
                "recommendation": f"No data yet for {goal.metric_type}. Record a measurement to track progress.",
                "status": "no_data"
            }

        current_value = metrics[0].value_numeric
        baseline = goal.baseline_value or (metrics[-1].value_numeric if len(metrics) > 1 else current_value)

        # Calculate progress percentage
        if goal.direction == "decrease":
            # For decrease goals (e.g., body fat from 20% to 14%)
            total_change_needed = baseline - goal.target_value
            if total_change_needed != 0:
                actual_change = baseline - current_value
                progress_percent = (actual_change / total_change_needed) * 100
            else:
                progress_percent = 100 if current_value <= goal.target_value else 0
        elif goal.direction == "increase":
            # For increase goals (e.g., VO2 max from 45 to 55)
            total_change_needed = goal.target_value - baseline
            if total_change_needed != 0:
                actual_change = current_value - baseline
                progress_percent = (actual_change / total_change_needed) * 100
            else:
                progress_percent = 100 if current_value >= goal.target_value else 0
        else:  # maintain
            # For maintain goals, check if within acceptable range
            if goal.min_acceptable and goal.max_acceptable:
                if goal.min_acceptable <= current_value <= goal.max_acceptable:
                    progress_percent = 100
                else:
                    progress_percent = 50  # Outside range
            else:
                progress_percent = 100 if current_value == goal.target_value else 50

        progress_percent = max(0, min(100, progress_percent))

        # Calculate trend from recent data
        trend = self._calculate_trend(metrics, goal.direction)

        # Estimate days to target
        days_to_target = self._estimate_days_to_target(metrics, goal)

        # Check if on track
        on_track = self._is_on_track(goal, current_value, days_to_target, trend)

        # Generate recommendation
        recommendation = self._generate_recommendation(goal, current_value, progress_percent, trend, on_track)

        return {
            "goal_id": goal.id,
            "goal_name": goal.name,
            "metric_type": goal.metric_type,
            "current_value": current_value,
            "target_value": goal.target_value,
            "baseline_value": baseline,
            "progress_percent": round(progress_percent, 1),
            "trend": trend,
            "on_track": on_track,
            "days_to_target": days_to_target,
            "recommendation": recommendation,
            "status": "achieved" if progress_percent >= 100 else "in_progress"
        }

    def _calculate_trend(self, metrics: List[ProgressMetric], direction: str) -> str:
        """Calculate trend from recent metrics."""
        if len(metrics) < 2:
            return "unknown"

        # Compare recent values
        recent_avg = sum(m.value_numeric for m in metrics[:3]) / min(3, len(metrics))
        older_avg = sum(m.value_numeric for m in metrics[3:6]) / min(3, len(metrics[3:6])) if len(metrics) > 3 else metrics[-1].value_numeric

        diff = recent_avg - older_avg
        threshold = abs(older_avg) * 0.02  # 2% change threshold

        if abs(diff) < threshold:
            return "stable"
        elif direction == "decrease":
            return "improving" if diff < 0 else "declining"
        else:  # increase or maintain
            return "improving" if diff > 0 else "declining"

    def _estimate_days_to_target(self, metrics: List[ProgressMetric], goal: Goal) -> Optional[int]:
        """Estimate days to reach target at current rate."""
        if len(metrics) < 2:
            return None

        # Calculate rate of change per day
        newest = metrics[0]
        oldest = metrics[-1]
        days_diff = (newest.metric_date - oldest.metric_date).days

        if days_diff == 0:
            return None

        value_diff = newest.value_numeric - oldest.value_numeric
        rate_per_day = value_diff / days_diff

        if rate_per_day == 0:
            return None

        # Calculate remaining distance
        remaining = goal.target_value - newest.value_numeric

        if goal.direction == "decrease":
            remaining = newest.value_numeric - goal.target_value

        if remaining <= 0:
            return 0  # Already achieved

        # Check if moving in right direction
        if goal.direction == "decrease" and rate_per_day >= 0:
            return None  # Not improving
        if goal.direction == "increase" and rate_per_day <= 0:
            return None  # Not improving

        days = abs(remaining / rate_per_day)
        return int(days)

    def _is_on_track(self, goal: Goal, current: float, days_to_target: Optional[int], trend: str) -> Optional[bool]:
        """Determine if goal is on track."""
        if goal.target_date is None:
            return trend == "improving"

        days_remaining = (goal.target_date - date.today()).days

        if days_remaining <= 0:
            # Past target date
            if goal.direction == "decrease":
                return current <= goal.target_value
            else:
                return current >= goal.target_value

        if days_to_target is None:
            return trend == "improving"

        return days_to_target <= days_remaining

    def _generate_recommendation(
        self, goal: Goal, current: float, progress: float, trend: str, on_track: Optional[bool]
    ) -> str:
        """Generate actionable recommendation for the goal."""

        if progress >= 100:
            return f"Goal achieved! Consider setting a new target or focusing on maintenance."

        if trend == "unknown":
            return f"Need more data points to analyze trend. Continue tracking {goal.metric_type}."

        recommendations = {
            "body_fat": self._recommend_body_fat(goal, current, progress, trend, on_track),
            "vo2_max": self._recommend_vo2_max(goal, current, progress, trend, on_track),
            "broad_jump": self._recommend_explosive(goal, current, progress, trend, on_track),
            "box_jump": self._recommend_explosive(goal, current, progress, trend, on_track),
            "100yd_freestyle": self._recommend_swim(goal, current, progress, trend, on_track),
        }

        return recommendations.get(goal.metric_type, self._recommend_generic(goal, current, progress, trend, on_track))

    def _recommend_body_fat(self, goal, current, progress, trend, on_track) -> str:
        if trend == "declining":
            return "Body fat trending up. Review nutrition - check calorie intake and protein. Consider adding HIIT sessions."
        elif trend == "stable" and progress < 50:
            return "Progress stalled. Try: 1) Increase cardio volume, 2) Review diet adherence, 3) Add morning fasted cardio."
        elif on_track:
            return "On track. Maintain current approach with consistent nutrition and training."
        else:
            return "Behind schedule. Prioritize: deficit adherence, protein intake (1g/lb), and consistent Zone 2 cardio."

    def _recommend_vo2_max(self, goal, current, progress, trend, on_track) -> str:
        if trend == "declining":
            return "VO2 max declining. Add more aerobic work: 2-3 Zone 2 sessions/week plus one interval session."
        elif trend == "stable":
            return "VO2 max plateaued. Vary intensity: add tempo runs, hill repeats, or longer Zone 2 sessions."
        elif on_track:
            return "VO2 max improving. Continue current cardio mix. Consider adding swimming for cross-training."
        else:
            return "Need more aerobic volume. Target 3-4 cardio sessions/week with mix of Zone 2 and intervals."

    def _recommend_explosive(self, goal, current, progress, trend, on_track) -> str:
        if trend == "declining":
            return "Power output declining. Focus on: plyometrics, box jumps, and explosive lifts (cleans, jumps)."
        elif on_track:
            return "Explosive power improving. Maintain plyometric work 2x/week."
        else:
            return "Add dedicated power work: jump squats, broad jumps, med ball throws. 2-3x/week."

    def _recommend_swim(self, goal, current, progress, trend, on_track) -> str:
        if trend == "declining":
            return "Swim times getting slower. Focus on technique drills and increase pool time."
        elif on_track:
            return "Swim times improving. Continue current program with mix of drills and threshold sets."
        else:
            return "Need more pool time. Add 1-2 swim sessions/week focusing on CSS pace work."

    def _recommend_generic(self, goal, current, progress, trend, on_track) -> str:
        if trend == "improving" and on_track:
            return "Good progress. Maintain current approach."
        elif trend == "declining":
            return f"Trend declining. Review training for {goal.metric_type} and adjust volume/intensity."
        else:
            return f"Focus needed on {goal.metric_type}. Increase training frequency or intensity."


class WorkoutRecommendationEngine:
    """
    Generate workout recommendations based on goals and recent training.
    """

    def __init__(self, db: Session, athlete_id: int):
        self.db = db
        self.athlete_id = athlete_id
        self.goal_analyzer = GoalAnalyzer(db, athlete_id)

    def analyze_recent_training(self, days: int = 14) -> Dict[str, Any]:
        """Analyze recent training patterns."""
        start_date = date.today() - timedelta(days=days)

        activities = self.db.query(CompletedActivity).filter(
            CompletedActivity.athlete_id == self.athlete_id,
            CompletedActivity.activity_date >= start_date
        ).all()

        # Count by type
        by_type = {}
        total_minutes = 0
        for a in activities:
            activity_type = a.activity_type
            by_type[activity_type] = by_type.get(activity_type, 0) + 1
            total_minutes += a.duration_minutes or 0

        return {
            "period_days": days,
            "total_workouts": len(activities),
            "total_minutes": total_minutes,
            "workouts_by_type": by_type,
            "avg_per_week": len(activities) / (days / 7),
            "avg_minutes_per_week": total_minutes / (days / 7)
        }

    def generate_weekly_recommendations(self) -> Dict[str, Any]:
        """
        Generate recommendations for the upcoming week.
        """
        # Get goal analysis
        goals = self.goal_analyzer.get_active_goals()
        goal_analyses = [self.goal_analyzer.analyze_goal_progress(g) for g in goals]

        # Get recent training
        training = self.analyze_recent_training(14)

        # Get latest wellness
        wellness = self.db.query(DailyWellness).filter(
            DailyWellness.athlete_id == self.athlete_id
        ).order_by(DailyWellness.date.desc()).first()

        # Generate recommendations
        recommendations = []
        priority_focus = None

        # Find goals that need attention
        struggling_goals = [g for g in goal_analyses if g.get("trend") == "declining" or g.get("on_track") == False]
        if struggling_goals:
            priority_focus = struggling_goals[0]["metric_type"]
            recommendations.append({
                "priority": "high",
                "area": priority_focus,
                "recommendation": struggling_goals[0]["recommendation"]
            })

        # Check training balance
        cardio_count = training["workouts_by_type"].get("run", 0) + training["workouts_by_type"].get("swim", 0) + training["workouts_by_type"].get("bike", 0)
        strength_count = training["workouts_by_type"].get("strength", 0)

        if cardio_count < 2:
            recommendations.append({
                "priority": "medium",
                "area": "cardio",
                "recommendation": "Low cardio volume. Add 2-3 cardio sessions this week for aerobic development."
            })

        if strength_count < 2:
            recommendations.append({
                "priority": "medium",
                "area": "strength",
                "recommendation": "Low strength volume. Add 2-3 strength sessions to maintain muscle and support goals."
            })

        # Check recovery (if wellness data available)
        recovery_note = None
        if wellness:
            if wellness.training_readiness_score and wellness.training_readiness_score < 50:
                recommendations.append({
                    "priority": "high",
                    "area": "recovery",
                    "recommendation": f"Training readiness low ({wellness.training_readiness_score}). Consider a lighter week or extra rest day."
                })
                recovery_note = "Low readiness - prioritize recovery"

            if wellness.sleep_score and wellness.sleep_score < 60:
                recommendations.append({
                    "priority": "medium",
                    "area": "sleep",
                    "recommendation": f"Sleep quality poor ({wellness.sleep_score}). Prioritize sleep hygiene for better recovery."
                })

        # Generate weekly plan suggestion
        suggested_week = self._suggest_weekly_plan(goal_analyses, training, wellness)

        return {
            "analysis_date": str(date.today()),
            "goal_progress": goal_analyses,
            "training_summary": training,
            "recommendations": recommendations,
            "priority_focus": priority_focus,
            "recovery_note": recovery_note,
            "suggested_week": suggested_week
        }

    def _suggest_weekly_plan(
        self, goal_analyses: List[Dict], training: Dict, wellness: Optional[DailyWellness]
    ) -> List[Dict[str, Any]]:
        """Generate a suggested weekly workout plan."""

        # Determine training readiness
        is_recovered = True
        if wellness and wellness.training_readiness_score:
            is_recovered = wellness.training_readiness_score >= 50

        # Base template (adjust based on goals and recovery)
        if is_recovered:
            plan = [
                {"day": "Monday", "type": "strength", "focus": "Upper body", "duration": 60},
                {"day": "Tuesday", "type": "cardio", "focus": "Zone 2 run or bike", "duration": 45},
                {"day": "Wednesday", "type": "strength", "focus": "Lower body", "duration": 60},
                {"day": "Thursday", "type": "cardio", "focus": "Intervals or swim", "duration": 40},
                {"day": "Friday", "type": "strength", "focus": "Full body or weak points", "duration": 50},
                {"day": "Saturday", "type": "cardio", "focus": "Long Zone 2 session", "duration": 60},
                {"day": "Sunday", "type": "rest", "focus": "Active recovery or rest", "duration": 0},
            ]
        else:
            # Lighter week for recovery
            plan = [
                {"day": "Monday", "type": "cardio", "focus": "Easy Zone 2", "duration": 30},
                {"day": "Tuesday", "type": "rest", "focus": "Recovery", "duration": 0},
                {"day": "Wednesday", "type": "strength", "focus": "Light full body", "duration": 45},
                {"day": "Thursday", "type": "cardio", "focus": "Easy swim or bike", "duration": 30},
                {"day": "Friday", "type": "rest", "focus": "Recovery", "duration": 0},
                {"day": "Saturday", "type": "strength", "focus": "Moderate session", "duration": 45},
                {"day": "Sunday", "type": "rest", "focus": "Full rest", "duration": 0},
            ]

        # Adjust based on struggling goals
        for goal in goal_analyses:
            if goal.get("on_track") == False:
                metric = goal.get("metric_type")
                if metric in ["vo2_max", "100yd_freestyle"]:
                    # Add more cardio
                    for day in plan:
                        if day["day"] == "Sunday" and day["type"] == "rest":
                            day["type"] = "cardio"
                            day["focus"] = "Additional aerobic session"
                            day["duration"] = 30
                            break

        return plan

    def save_analysis(self) -> WorkoutAnalysis:
        """Save the current analysis to database."""
        recommendations = self.generate_weekly_recommendations()
        training = recommendations["training_summary"]

        # Calculate goal alignment
        goal_alignment = {}
        total_alignment = 0
        for goal in recommendations["goal_progress"]:
            alignment = goal.get("progress_percent", 0)
            goal_alignment[goal["goal_id"]] = alignment
            total_alignment += alignment

        avg_alignment = total_alignment / len(recommendations["goal_progress"]) if recommendations["goal_progress"] else 0

        analysis = WorkoutAnalysis(
            athlete_id=self.athlete_id,
            analysis_date=date.today(),
            period_days=14,
            total_workouts=training["total_workouts"],
            total_duration_minutes=training["total_minutes"],
            workouts_by_type_json=json.dumps(training["workouts_by_type"]),
            goal_alignment_json=json.dumps(goal_alignment),
            overall_alignment_score=avg_alignment,
            recommendations_json=json.dumps(recommendations["recommendations"]),
            priority_focus=recommendations["priority_focus"],
            suggested_adjustments=json.dumps(recommendations["suggested_week"])
        )

        self.db.add(analysis)
        self.db.commit()

        return analysis
