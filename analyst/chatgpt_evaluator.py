"""
ChatGPT integration for training plan evaluation.
Uses OpenAI's reasoning models (o1) for deep analysis of workout modifications.
"""

import os
import json
from datetime import date, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


@dataclass
class PlanModification:
    """A proposed modification to the training plan."""
    modification_type: str  # "intensity", "volume", "reschedule", "add_rest", "swap_workout"
    week_number: int
    day_of_week: Optional[int] = None
    workout_type: Optional[str] = None
    description: str = ""
    reason: str = ""
    priority: str = "medium"  # "high", "medium", "low"
    ai_confidence: float = 0.0  # 0-1 confidence score


@dataclass
class PlanEvaluation:
    """Result of AI evaluation of the training plan."""
    overall_assessment: str  # "on_track", "needs_adjustment", "significant_changes_needed"
    progress_summary: str
    modifications: List[PlanModification]
    next_week_focus: str
    warnings: List[str]
    confidence_score: float


class ChatGPTEvaluator:
    """
    Uses ChatGPT (o1 reasoning model) to evaluate training progress
    and recommend plan modifications.
    """

    # System context for the AI
    SYSTEM_CONTEXT = """You are an expert sports science coach and training plan analyst.
Your role is to evaluate an athlete's training progress against their 24-week performance plan
and recommend modifications when necessary.

The athlete's primary goals are:
1. Maintain ~14% body fat
2. Increase VO2 max (multi-modal: run/row/bike/swim)
3. Maintain explosiveness and flexibility for sports (snowboarding, golf, wakeboarding)
4. Improve 400-yard freestyle time in a 25-yard pool (from a push, no dive starts)

Training structure is 3-5 hours/week:
- Swim 2 days/week (Swim A: threshold/CSS, Swim B: VO2/400-specific)
- Other workouts 2-3 days/week (Lift A: lower body, Lift B: upper body, VO2 sessions)

Test weeks (400 TT) occur in weeks 1, 12, and 24.

When evaluating, consider:
- Wellness data (sleep, HRV, training readiness, body battery)
- Workout completion and adherence
- Performance trends (improving, maintaining, declining)
- Recovery status
- Goal alignment

IMPORTANT GUIDELINES:
- Be VERY conservative with modifications - only suggest changes when clearly warranted
- Minimize the number of workouts affected - prefer surgical, targeted changes over broad modifications
- Always explain your reasoning clearly and specifically
- If no changes are needed, say so - don't suggest changes just for the sake of it
- Consider the athlete's user notes/context if provided"""

    def __init__(self, model: str = "o1-preview"):
        """
        Initialize the ChatGPT evaluator.

        Args:
            model: OpenAI model to use. Default is o1-preview for reasoning tasks.
                   Can also use "gpt-4-turbo-preview" or "gpt-4o" for faster responses.
        """
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = OpenAI(api_key=self.api_key)
        self.model = model

    def evaluate_progress(
        self,
        current_week: int,
        wellness_data: Dict[str, Any],
        recent_workouts: List[Dict[str, Any]],
        goal_progress: Dict[str, Any],
        scheduled_workouts: List[Dict[str, Any]],
        plan_summary: str,
        user_context: Optional[str] = None
    ) -> PlanEvaluation:
        """
        Evaluate current training progress and recommend modifications.

        Args:
            current_week: Current week number in the 24-week plan
            wellness_data: Recent wellness metrics (sleep, HRV, readiness, etc.)
            recent_workouts: Completed workouts from past 7-14 days
            goal_progress: Progress toward each goal
            scheduled_workouts: Upcoming scheduled workouts
            plan_summary: Summary of the training plan for context
            user_context: Optional user-provided notes or context to consider

        Returns:
            PlanEvaluation with assessment and recommended modifications
        """
        # Build the prompt
        prompt = self._build_evaluation_prompt(
            current_week,
            wellness_data,
            recent_workouts,
            goal_progress,
            scheduled_workouts,
            plan_summary,
            user_context
        )

        try:
            # Call the OpenAI API
            # For o1 models, we use user messages only (no system message)
            if self.model.startswith("o1"):
                messages = [
                    {"role": "user", "content": f"{self.SYSTEM_CONTEXT}\n\n{prompt}"}
                ]
            else:
                messages = [
                    {"role": "system", "content": self.SYSTEM_CONTEXT},
                    {"role": "user", "content": prompt}
                ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_completion_tokens=4096,
            )

            # Parse the response
            response_text = response.choices[0].message.content
            return self._parse_evaluation_response(response_text)

        except Exception as e:
            print(f"✗ Error calling OpenAI API: {e}")
            # Return a safe default evaluation
            return PlanEvaluation(
                overall_assessment="error",
                progress_summary=f"Error evaluating progress: {str(e)}",
                modifications=[],
                next_week_focus="Continue as planned",
                warnings=[f"AI evaluation failed: {str(e)}"],
                confidence_score=0.0
            )

    def _build_evaluation_prompt(
        self,
        current_week: int,
        wellness_data: Dict[str, Any],
        recent_workouts: List[Dict[str, Any]],
        goal_progress: Dict[str, Any],
        scheduled_workouts: List[Dict[str, Any]],
        plan_summary: str,
        user_context: Optional[str] = None
    ) -> str:
        """Build the evaluation prompt with all context."""
        # Include user context section if provided
        user_context_section = ""
        if user_context:
            user_context_section = f"""
## Athlete Notes (User-Provided Context)
{user_context}

**IMPORTANT**: Please consider the above notes from the athlete when making your evaluation.
"""

        prompt = f"""# Training Progress Evaluation Request

## Current Status
- **Week**: {current_week} of 24
- **Phase**: {"Test/Baseline" if current_week == 1 else "Build Phase 1 (Weeks 1-8)" if current_week <= 8 else "Build Phase 2 (Weeks 9-16)" if current_week <= 16 else "Peak Phase (Weeks 17-24)"}
- **Is Test Week**: {"Yes" if current_week in [1, 12, 24] else "No"}

## Wellness Data (Last 7 Days Average)
{json.dumps(wellness_data, indent=2, default=str)}

## Recent Completed Workouts
{json.dumps(recent_workouts, indent=2, default=str)}

## Goal Progress
{json.dumps(goal_progress, indent=2, default=str)}

## Upcoming Scheduled Workouts (Next 7 Days)
{json.dumps(scheduled_workouts, indent=2, default=str)}

## Plan Summary
{plan_summary}
{user_context_section}
---

Please analyze this data and provide:

1. **Overall Assessment**: Is the athlete on track, needs minor adjustments, or needs significant changes?

2. **Progress Summary**: Brief summary of how the athlete is progressing toward each goal.

3. **Recommended Modifications** (if any): For each modification, specify:
   - Type (intensity, volume, reschedule, add_rest, swap_workout)
   - Week and day affected
   - Description of the change
   - Reason for the change
   - Priority (high/medium/low)

4. **Next Week Focus**: What should be the primary focus for the upcoming week?

5. **Warnings**: Any concerns or red flags to watch.

Please respond in the following JSON format:
```json
{{
    "overall_assessment": "on_track|needs_adjustment|significant_changes_needed",
    "progress_summary": "...",
    "modifications": [
        {{
            "modification_type": "...",
            "week_number": N,
            "day_of_week": N or null,
            "workout_type": "..." or null,
            "description": "...",
            "reason": "...",
            "priority": "high|medium|low"
        }}
    ],
    "next_week_focus": "...",
    "warnings": ["..."],
    "confidence_score": 0.0-1.0
}}
```
"""
        return prompt

    def _parse_evaluation_response(self, response_text: str) -> PlanEvaluation:
        """Parse the AI response into a PlanEvaluation object."""
        try:
            # Extract JSON from the response
            # Look for JSON block in markdown code block
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to parse the whole response as JSON
                json_str = response_text

            data = json.loads(json_str)

            # Parse modifications
            modifications = []
            for mod in data.get("modifications", []):
                modifications.append(PlanModification(
                    modification_type=mod.get("modification_type", "unknown"),
                    week_number=mod.get("week_number", 0),
                    day_of_week=mod.get("day_of_week"),
                    workout_type=mod.get("workout_type"),
                    description=mod.get("description", ""),
                    reason=mod.get("reason", ""),
                    priority=mod.get("priority", "medium"),
                    ai_confidence=data.get("confidence_score", 0.5)
                ))

            return PlanEvaluation(
                overall_assessment=data.get("overall_assessment", "unknown"),
                progress_summary=data.get("progress_summary", ""),
                modifications=modifications,
                next_week_focus=data.get("next_week_focus", ""),
                warnings=data.get("warnings", []),
                confidence_score=data.get("confidence_score", 0.5)
            )

        except json.JSONDecodeError as e:
            print(f"⚠ Failed to parse JSON response: {e}")
            # Return a basic evaluation with the raw response
            return PlanEvaluation(
                overall_assessment="parse_error",
                progress_summary=response_text[:500],
                modifications=[],
                next_week_focus="Review AI response manually",
                warnings=["Failed to parse AI response as JSON"],
                confidence_score=0.0
            )

    def evaluate_modification(
        self,
        proposed_modification: PlanModification,
        current_plan_state: Dict[str, Any],
        wellness_context: Dict[str, Any]
    ) -> Tuple[bool, str, float]:
        """
        Evaluate a specific proposed modification.

        Args:
            proposed_modification: The modification to evaluate
            current_plan_state: Current state of the training plan
            wellness_context: Current wellness data

        Returns:
            Tuple of (approved, reasoning, confidence)
        """
        prompt = f"""# Modification Evaluation Request

## Proposed Modification
- Type: {proposed_modification.modification_type}
- Week: {proposed_modification.week_number}
- Day: {proposed_modification.day_of_week or "N/A"}
- Workout Type: {proposed_modification.workout_type or "N/A"}
- Description: {proposed_modification.description}
- Reason: {proposed_modification.reason}
- Priority: {proposed_modification.priority}

## Current Plan State
{json.dumps(current_plan_state, indent=2, default=str)}

## Wellness Context
{json.dumps(wellness_context, indent=2, default=str)}

---

Should this modification be approved? Consider:
1. Is the modification necessary and well-justified?
2. Does it align with the athlete's goals?
3. Are there any risks or downsides?
4. Is there a better alternative?

Respond with:
```json
{{
    "approved": true/false,
    "reasoning": "...",
    "confidence": 0.0-1.0,
    "alternative": "..." or null
}}
```
"""

        try:
            if self.model.startswith("o1"):
                messages = [
                    {"role": "user", "content": f"{self.SYSTEM_CONTEXT}\n\n{prompt}"}
                ]
            else:
                messages = [
                    {"role": "system", "content": self.SYSTEM_CONTEXT},
                    {"role": "user", "content": prompt}
                ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_completion_tokens=1024,
            )

            response_text = response.choices[0].message.content

            # Parse response
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                data = json.loads(response_text)

            return (
                data.get("approved", False),
                data.get("reasoning", ""),
                data.get("confidence", 0.5)
            )

        except Exception as e:
            print(f"✗ Error evaluating modification: {e}")
            return False, f"Error during evaluation: {str(e)}", 0.0

    def generate_weekly_plan_summary(
        self,
        week_number: int,
        workouts: List[Dict[str, Any]],
        focus_areas: List[str]
    ) -> str:
        """
        Generate a human-readable summary of the weekly plan.

        Args:
            week_number: Week number
            workouts: List of workouts for the week
            focus_areas: Key focus areas for the week

        Returns:
            Markdown summary of the week
        """
        prompt = f"""Generate a brief, motivating weekly training summary for week {week_number}.

Workouts this week:
{json.dumps(workouts, indent=2, default=str)}

Key focus areas: {', '.join(focus_areas)}

Write 2-3 sentences summarizing the week's training goals and key workouts.
Be encouraging but specific. No fluff."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Use faster model for summaries
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            # Fallback summary
            workout_types = [w.get("workout_type", "workout") for w in workouts]
            return f"Week {week_number}: {len(workouts)} workouts planned including {', '.join(set(workout_types))}. Focus on {focus_areas[0] if focus_areas else 'consistent execution'}."
