"""
Training plan parser.
Extracts structured workout data from the base training plan markdown file.
"""

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum


class WorkoutType(Enum):
    SWIM_A = "swim_a"           # Threshold/CSS development
    SWIM_B = "swim_b"           # VO2 + 400-specific work
    LIFT_A = "lift_a"           # Lower body strength + power
    LIFT_B = "lift_b"           # Upper body + trunk + rotation
    VO2 = "vo2"                 # Run/row/bike intervals
    SWIM_TEST = "swim_test"     # 400 TT test day
    REST = "rest"


@dataclass
class Exercise:
    """Single exercise within a workout."""
    name: str
    sets: Optional[int] = None
    reps: Optional[str] = None  # Can be "8-10" or "30s" or "40 yards"
    rest_seconds: Optional[int] = None
    notes: Optional[str] = None
    intensity: Optional[str] = None  # "RPE 7", "steady", "hard"


@dataclass
class WorkoutPhase:
    """A phase within a workout (warmup, main, cooldown)."""
    name: str
    duration_minutes: Optional[int] = None
    exercises: List[Exercise] = field(default_factory=list)
    notes: Optional[str] = None


@dataclass
class Workout:
    """A complete workout session."""
    workout_type: WorkoutType
    week_number: int
    day_of_week: int  # 1-7
    date: Optional[date] = None
    name: str = ""
    phases: List[WorkoutPhase] = field(default_factory=list)
    is_test_week: bool = False
    notes: Optional[str] = None
    total_duration_minutes: Optional[int] = None


@dataclass
class TrainingPlan:
    """Complete training plan."""
    name: str
    total_weeks: int
    start_date: Optional[date] = None
    workouts: List[Workout] = field(default_factory=list)
    goals: List[str] = field(default_factory=list)
    test_weeks: List[int] = field(default_factory=list)


class PlanParser:
    """
    Parse the base training plan markdown into structured workout data.
    """

    # Default weekly structure (day number -> workout type)
    DEFAULT_WEEKLY_STRUCTURE = {
        1: WorkoutType.SWIM_A,
        2: WorkoutType.LIFT_A,
        3: WorkoutType.VO2,
        4: WorkoutType.SWIM_B,
        5: WorkoutType.LIFT_B,
    }

    TEST_WEEKS = [1, 12, 24]

    def __init__(self, plan_path: str):
        self.plan_path = plan_path
        self.raw_content = ""
        self.plan: Optional[TrainingPlan] = None

    def parse(self) -> TrainingPlan:
        """Parse the training plan file and return structured data."""
        with open(self.plan_path, 'r') as f:
            self.raw_content = f.read()

        self.plan = TrainingPlan(
            name="24-Week Performance Plan",
            total_weeks=24,
            test_weeks=self.TEST_WEEKS,
            goals=self._parse_goals()
        )

        return self.plan

    def _parse_goals(self) -> List[str]:
        """Extract goals from the plan."""
        goals = []
        goals_section = re.search(
            r'\*\*Primary goals.*?\*\*:?\n(.*?)(?=\*\*Program length|---)',
            self.raw_content,
            re.DOTALL
        )
        if goals_section:
            for line in goals_section.group(1).split('\n'):
                line = line.strip()
                if line.startswith('- '):
                    goals.append(line[2:])
        return goals

    def _parse_swim_a_main_sets(self) -> Dict[str, Any]:
        """Parse Swim A main sets by week range."""
        sets_by_week = {}

        # Pattern: **Weeks X-Y:** description
        swim_a_section = re.search(
            r'## Swim A.*?(?=## Swim B|---\s*\n## )',
            self.raw_content,
            re.DOTALL
        )

        if swim_a_section:
            content = swim_a_section.group(0)
            pattern = r'\*\*Weeks? (\d+)(?:–|-)?(\d+)?:\*\* (.+?)(?=\n-|\n\*\*|\n\n)'
            matches = re.findall(pattern, content)

            for match in matches:
                start_week = int(match[0])
                end_week = int(match[1]) if match[1] else start_week
                description = match[2].strip()

                for week in range(start_week, end_week + 1):
                    sets_by_week[week] = self._parse_swim_set_description(description)

        return sets_by_week

    def _parse_swim_b_main_sets(self) -> Dict[str, Any]:
        """Parse Swim B main sets by week range."""
        sets_by_week = {}

        swim_b_section = re.search(
            r'## Swim B.*?(?=## Lift A|---\s*\n## )',
            self.raw_content,
            re.DOTALL
        )

        if swim_b_section:
            content = swim_b_section.group(0)
            pattern = r'\*\*Weeks? (\d+)(?:–|-)?(\d+)?:\*\* (.+?)(?=\n-|\n\*\*|\n\n)'
            matches = re.findall(pattern, content)

            for match in matches:
                start_week = int(match[0])
                end_week = int(match[1]) if match[1] else start_week
                description = match[2].strip()

                for week in range(start_week, end_week + 1):
                    sets_by_week[week] = self._parse_swim_set_description(description)

        return sets_by_week

    def _parse_vo2_main_sets(self) -> Dict[str, Any]:
        """Parse VO2 session main sets by week range."""
        sets_by_week = {}

        vo2_section = re.search(
            r'## VO₂ Session.*?(?=## 400 TT|---\s*\n## )',
            self.raw_content,
            re.DOTALL
        )

        if vo2_section:
            content = vo2_section.group(0)
            pattern = r'\*\*Weeks? (\d+)(?:–|-)?(\d+)?:\*\* (.+?)(?=\n-|\n\*\*|\n\n)'
            matches = re.findall(pattern, content)

            for match in matches:
                start_week = int(match[0])
                end_week = int(match[1]) if match[1] else start_week
                description = match[2].strip()

                for week in range(start_week, end_week + 1):
                    sets_by_week[week] = self._parse_vo2_description(description)

        return sets_by_week

    def _parse_swim_set_description(self, description: str) -> Dict[str, Any]:
        """Parse a swim set description into structured data."""
        result = {
            "raw": description,
            "reps": None,
            "distance": None,
            "intensity": None,
            "rest_seconds": None,
        }

        # Pattern: 10×100 @ steady (RPE 6-7), 15-20s rest
        reps_match = re.search(r'(\d+)×(\d+)', description)
        if reps_match:
            result["reps"] = int(reps_match.group(1))
            result["distance"] = int(reps_match.group(2))

        # Pattern for nested sets: 3×(4×100)
        nested_match = re.search(r'(\d+)×\((\d+)×(\d+)', description)
        if nested_match:
            result["rounds"] = int(nested_match.group(1))
            result["reps"] = int(nested_match.group(2))
            result["distance"] = int(nested_match.group(3))

        # Intensity
        if "RPE" in description:
            rpe_match = re.search(r'RPE (\d+(?:–|-)\d+|\d+)', description)
            if rpe_match:
                result["intensity"] = f"RPE {rpe_match.group(1)}"
        elif "steady" in description.lower():
            result["intensity"] = "steady"
        elif "hard" in description.lower():
            result["intensity"] = "hard"
        elif "moderate-hard" in description.lower():
            result["intensity"] = "moderate-hard"
        elif "CSS pace" in description.lower():
            result["intensity"] = "CSS pace"
        elif "target 400 pace" in description.lower():
            result["intensity"] = "target 400 pace"

        # Rest
        rest_match = re.search(r'(\d+)(?:–|-)?(\d+)?s rest', description)
        if rest_match:
            # Take average of range
            low = int(rest_match.group(1))
            high = int(rest_match.group(2)) if rest_match.group(2) else low
            result["rest_seconds"] = (low + high) // 2

        return result

    def _parse_vo2_description(self, description: str) -> Dict[str, Any]:
        """Parse a VO2 set description into structured data."""
        result = {
            "raw": description,
            "reps": None,
            "duration_minutes": None,
            "intensity": None,
            "rest_minutes": None,
        }

        # Pattern: 6×2 min @ hard
        reps_match = re.search(r'(\d+)×(\d+) min', description)
        if reps_match:
            result["reps"] = int(reps_match.group(1))
            result["duration_minutes"] = int(reps_match.group(2))

        # Intensity
        if "very hard" in description.lower():
            result["intensity"] = "very hard (RPE 9)"
        elif "hard" in description.lower():
            result["intensity"] = "hard (RPE 8)"
        elif "easy" in description.lower():
            result["intensity"] = "easy"

        # Rest
        rest_match = re.search(r'(\d+(?:\.\d+)?)\s*min\s*(?:easy\s*)?between', description)
        if rest_match:
            result["rest_minutes"] = float(rest_match.group(1))

        return result

    def generate_workouts_for_week(self, week_number: int, start_date: date) -> List[Workout]:
        """Generate all workouts for a specific week starting from a given date."""
        workouts = []
        is_test_week = week_number in self.TEST_WEEKS

        # Calculate the Monday of this week
        week_start = start_date + timedelta(weeks=week_number - 1)

        swim_a_sets = self._parse_swim_a_main_sets()
        swim_b_sets = self._parse_swim_b_main_sets()
        vo2_sets = self._parse_vo2_main_sets()

        for day, workout_type in self.DEFAULT_WEEKLY_STRUCTURE.items():
            workout_date = week_start + timedelta(days=day - 1)

            # Handle test week modifications
            if is_test_week and workout_type == WorkoutType.SWIM_B:
                workout_type = WorkoutType.SWIM_TEST

            workout = Workout(
                workout_type=workout_type,
                week_number=week_number,
                day_of_week=day,
                date=workout_date,
                is_test_week=is_test_week,
            )

            # Build workout phases based on type
            if workout_type == WorkoutType.SWIM_A:
                workout.name = f"Swim A - Week {week_number}"
                workout.phases = self._build_swim_a_phases(week_number, swim_a_sets, is_test_week)
                workout.total_duration_minutes = 45

            elif workout_type == WorkoutType.SWIM_B:
                workout.name = f"Swim B - Week {week_number}"
                workout.phases = self._build_swim_b_phases(week_number, swim_b_sets)
                workout.total_duration_minutes = 45

            elif workout_type == WorkoutType.SWIM_TEST:
                workout.name = f"400 TT Test - Week {week_number}"
                workout.phases = self._build_swim_test_phases()
                workout.total_duration_minutes = 45

            elif workout_type == WorkoutType.LIFT_A:
                workout.name = f"Lift A (Lower) - Week {week_number}"
                workout.phases = self._build_lift_a_phases()
                workout.total_duration_minutes = 45

            elif workout_type == WorkoutType.LIFT_B:
                workout.name = f"Lift B (Upper) - Week {week_number}"
                workout.phases = self._build_lift_b_phases()
                workout.total_duration_minutes = 45

            elif workout_type == WorkoutType.VO2:
                workout.name = f"VO2 Session - Week {week_number}"
                workout.phases = self._build_vo2_phases(week_number, vo2_sets)
                workout.total_duration_minutes = 40

            workouts.append(workout)

        return workouts

    def _build_swim_a_phases(self, week: int, sets_by_week: Dict, is_test_week: bool) -> List[WorkoutPhase]:
        """Build Swim A workout phases."""
        phases = []

        # Warmup
        warmup = WorkoutPhase(
            name="Warm-up",
            duration_minutes=12,
            exercises=[
                Exercise(name="Easy swim", sets=1, reps="300", notes="Easy pace"),
                Exercise(name="Drill/swim by 25", sets=6, reps="50", rest_seconds=17,
                        notes="Catch-up, fingertip drag, 6-kick switch"),
            ]
        )
        phases.append(warmup)

        # Main set - varies by week
        if is_test_week:
            # Reduced volume for test week
            main = WorkoutPhase(
                name="Main Set (Test Week - Reduced)",
                exercises=[
                    Exercise(name="CSS/Target 400 pace", sets=6, reps="50",
                            rest_seconds=37, intensity="crisp"),
                ]
            )
        elif week in sets_by_week:
            set_data = sets_by_week[week]
            main = WorkoutPhase(
                name="Main Set",
                exercises=[
                    Exercise(
                        name=f"Freestyle",
                        sets=set_data.get("reps"),
                        reps=str(set_data.get("distance", "")),
                        rest_seconds=set_data.get("rest_seconds"),
                        intensity=set_data.get("intensity"),
                        notes=set_data.get("raw")
                    ),
                ]
            )
        else:
            main = WorkoutPhase(name="Main Set", exercises=[])

        phases.append(main)

        # Cooldown
        cooldown = WorkoutPhase(
            name="Cool-down",
            exercises=[
                Exercise(name="Easy swim", sets=1, reps="200", notes="Easy pace"),
            ]
        )
        phases.append(cooldown)

        return phases

    def _build_swim_b_phases(self, week: int, sets_by_week: Dict) -> List[WorkoutPhase]:
        """Build Swim B workout phases."""
        phases = []

        # Warmup
        warmup = WorkoutPhase(
            name="Warm-up",
            duration_minutes=12,
            exercises=[
                Exercise(name="Easy swim", sets=1, reps="300", notes="Easy pace"),
                Exercise(name="Build swim", sets=4, reps="50", rest_seconds=17,
                        notes="Easy to moderate"),
                Exercise(name="Fast-but-clean", sets=4, reps="25", rest_seconds=37,
                        notes="Crisp speed without stroke failure"),
            ]
        )
        phases.append(warmup)

        # Main set - varies by week
        if week in sets_by_week:
            set_data = sets_by_week[week]
            main = WorkoutPhase(
                name="Main Set",
                exercises=[
                    Exercise(
                        name="Freestyle intervals",
                        sets=set_data.get("reps"),
                        reps=str(set_data.get("distance", "")),
                        rest_seconds=set_data.get("rest_seconds"),
                        intensity=set_data.get("intensity"),
                        notes=set_data.get("raw")
                    ),
                ]
            )
        else:
            main = WorkoutPhase(name="Main Set", exercises=[])

        phases.append(main)

        # Cooldown
        cooldown = WorkoutPhase(
            name="Cool-down",
            exercises=[
                Exercise(name="Easy swim", sets=1, reps="200", notes="Easy pace"),
            ]
        )
        phases.append(cooldown)

        return phases

    def _build_swim_test_phases(self) -> List[WorkoutPhase]:
        """Build 400 TT test day phases."""
        phases = []

        # Warmup
        warmup = WorkoutPhase(
            name="Warm-up",
            duration_minutes=15,
            exercises=[
                Exercise(name="Easy swim", sets=1, reps="300", notes="Easy pace"),
                Exercise(name="Build swim", sets=4, reps="50", rest_seconds=20,
                        notes="Easy to moderate"),
                Exercise(name="Fast-but-clean", sets=4, reps="25", rest_seconds=50,
                        notes="Crisp speed without stroke failure"),
                Exercise(name="Easy swim", sets=2, reps="25", notes="Easy"),
            ],
            notes="Rest 2-3 minutes before TT"
        )
        phases.append(warmup)

        # Test
        test = WorkoutPhase(
            name="400 TT Test",
            exercises=[
                Exercise(name="400y Freestyle Time Trial", sets=1, reps="400",
                        intensity="race pace",
                        notes="Push start. Controlled first 100, build through 200-300, hold form 300-400"),
            ]
        )
        phases.append(test)

        # Cooldown
        cooldown = WorkoutPhase(
            name="Cool-down",
            exercises=[
                Exercise(name="Easy swim", sets=1, reps="200-400", notes="Easy cool-down"),
                Exercise(name="Drill/swim (optional)", sets=4, reps="50",
                        notes="Very easy if tight"),
            ]
        )
        phases.append(cooldown)

        return phases

    def _build_lift_a_phases(self) -> List[WorkoutPhase]:
        """Build Lift A (Lower Body) phases."""
        phases = []

        # Warmup
        warmup = WorkoutPhase(
            name="Warm-up",
            duration_minutes=7,
            exercises=[
                Exercise(name="Foam roll", notes="Quads, glutes, hip flexors"),
                Exercise(name="Leg swings", sets=1, reps="10 each"),
                Exercise(name="Walking lunges", sets=1, reps="10 each"),
                Exercise(name="Hip circles", sets=1, reps="10 each"),
                Exercise(name="Bodyweight squats", sets=2, reps="10"),
            ]
        )
        phases.append(warmup)

        # Main
        main = WorkoutPhase(
            name="Main Work",
            exercises=[
                Exercise(name="Squats/Goblet Squats", sets=3, reps="8-10",
                        notes="Moderate weight"),
                Exercise(name="Romanian Deadlifts", sets=3, reps="10-12"),
                Exercise(name="Bulgarian Split Squats", sets=2, reps="8 each leg"),
                Exercise(name="Box Jumps/Broad Jumps", sets=3, reps="5",
                        notes="Power focus, full recovery"),
                Exercise(name="Single-Leg Balance", sets=2, reps="30s each",
                        notes="On BOSU or unstable surface"),
            ]
        )
        phases.append(main)

        # Finisher
        finisher = WorkoutPhase(
            name="Finisher",
            exercises=[
                Exercise(name="Farmers Carry", sets=2, reps="40 yards"),
            ]
        )
        phases.append(finisher)

        # Cooldown
        cooldown = WorkoutPhase(
            name="Cool-down",
            exercises=[
                Exercise(name="Hip flexor stretch", reps="2 min each side"),
                Exercise(name="Pigeon pose", reps="2 min each side"),
            ]
        )
        phases.append(cooldown)

        return phases

    def _build_lift_b_phases(self) -> List[WorkoutPhase]:
        """Build Lift B (Upper Body) phases."""
        phases = []

        # Warmup
        warmup = WorkoutPhase(
            name="Warm-up",
            duration_minutes=7,
            exercises=[
                Exercise(name="Arm circles", sets=1, reps="20"),
                Exercise(name="Band pull-aparts", sets=1, reps="15"),
                Exercise(name="Cat-cow", sets=1, reps="10"),
                Exercise(name="Push-ups", sets=2, reps="10"),
            ]
        )
        phases.append(warmup)

        # Main
        main = WorkoutPhase(
            name="Main Work",
            exercises=[
                Exercise(name="Bench Press/Push-ups", sets=3, reps="8-10"),
                Exercise(name="Bent-Over Rows", sets=3, reps="10-12"),
                Exercise(name="Overhead Press", sets=3, reps="8-10"),
                Exercise(name="Pull-ups/Lat Pulldowns", sets=3, reps="8-10"),
                Exercise(name="Pallof Press", sets=2, reps="12 each side",
                        notes="Anti-rotation"),
                Exercise(name="Med Ball Rotational Throws", sets=2, reps="8 each side"),
            ]
        )
        phases.append(main)

        # Finisher
        finisher = WorkoutPhase(
            name="Finisher",
            exercises=[
                Exercise(name="Suitcase Carry", sets=2, reps="40 yards each hand"),
            ]
        )
        phases.append(finisher)

        # Cooldown
        cooldown = WorkoutPhase(
            name="Cool-down",
            exercises=[
                Exercise(name="Thoracic spine rotation"),
                Exercise(name="Doorway chest stretch"),
            ]
        )
        phases.append(cooldown)

        return phases

    def _build_vo2_phases(self, week: int, sets_by_week: Dict) -> List[WorkoutPhase]:
        """Build VO2 session phases."""
        phases = []

        # Warmup
        warmup = WorkoutPhase(
            name="Warm-up",
            duration_minutes=9,
            exercises=[
                Exercise(name="Easy jog/row/spin", reps="5 min"),
                Exercise(name="Dynamic stretches", reps="2 min"),
                Exercise(name="Strides/pickups", sets=4, reps="15-20s each"),
            ]
        )
        phases.append(warmup)

        # Main set - varies by week
        if week in sets_by_week:
            set_data = sets_by_week[week]
            rest_desc = f"{set_data.get('rest_minutes', 2)} min easy between" if set_data.get('rest_minutes') else ""
            main = WorkoutPhase(
                name="Main Set",
                exercises=[
                    Exercise(
                        name="Intervals (run/row/bike)",
                        sets=set_data.get("reps"),
                        reps=f"{set_data.get('duration_minutes', 2)} min",
                        intensity=set_data.get("intensity"),
                        notes=f"{set_data.get('raw')}. {rest_desc}"
                    ),
                ]
            )
        else:
            main = WorkoutPhase(name="Main Set", exercises=[])

        phases.append(main)

        # Cooldown
        cooldown = WorkoutPhase(
            name="Cool-down",
            exercises=[
                Exercise(name="Easy pace", reps="5 min"),
                Exercise(name="Stretching"),
            ]
        )
        phases.append(cooldown)

        return phases

    def generate_full_plan(self, start_date: date) -> TrainingPlan:
        """Generate the complete training plan with all workouts dated."""
        if not self.plan:
            self.parse()

        self.plan.start_date = start_date
        self.plan.workouts = []

        for week in range(1, self.plan.total_weeks + 1):
            week_workouts = self.generate_workouts_for_week(week, start_date)
            self.plan.workouts.extend(week_workouts)

        return self.plan

    def to_dict(self) -> Dict[str, Any]:
        """Convert the plan to a dictionary for JSON serialization."""
        if not self.plan:
            self.parse()

        return {
            "name": self.plan.name,
            "total_weeks": self.plan.total_weeks,
            "start_date": self.plan.start_date.isoformat() if self.plan.start_date else None,
            "goals": self.plan.goals,
            "test_weeks": self.plan.test_weeks,
            "workouts": [
                {
                    "workout_type": w.workout_type.value,
                    "week_number": w.week_number,
                    "day_of_week": w.day_of_week,
                    "date": w.date.isoformat() if w.date else None,
                    "name": w.name,
                    "is_test_week": w.is_test_week,
                    "total_duration_minutes": w.total_duration_minutes,
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
                        for p in w.phases
                    ]
                }
                for w in self.plan.workouts
            ]
        }
