"""
Data Analyst Agent - Generates Tufte-style training reports.

Creates clean, data-dense HTML reports following Edward Tufte's principles:
- High data-ink ratio: Every element serves a purpose
- No chartjunk: No 3D effects, gradients, or decorative elements
- Small multiples: Repeated small charts for comparison
- Sparklines: Tiny inline time-series graphics
- Integrated text and graphics: Data embedded in narrative
"""

import json
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.models import CompletedActivity, ProgressMetric, Athlete
from analyst.visualizations import (
    generate_sparkline,
    generate_bar_sparkline,
    generate_small_multiples,
    generate_slope_graph,
    generate_data_table
)


class TrainingReportGenerator:
    """Generates clean, data-dense training reports following Tufte principles."""

    def __init__(self, db: Session, athlete_id: int):
        self.db = db
        self.athlete_id = athlete_id
        self.athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()

    def generate_daily_report(self, report_date: date) -> str:
        """
        Generate a daily training report with embedded visualizations.

        Args:
            report_date: The date for the report

        Returns:
            HTML string with inline SVG visualizations
        """
        # Gather data
        week_start = report_date - timedelta(days=6)
        activities = self._get_activities(week_start, report_date)
        today_activities = [a for a in activities if a.activity_date == report_date]

        # Calculate metrics
        weekly_stats = self._calculate_weekly_stats(activities)
        volume_by_day = self._get_daily_volumes(week_start, report_date)
        workout_types = self._get_workout_type_distribution(activities)
        recent_strength = self._get_recent_strength_exercises(report_date, days=7)

        # Build report
        html = self._render_daily_report(
            report_date=report_date,
            today_activities=today_activities,
            weekly_stats=weekly_stats,
            volume_by_day=volume_by_day,
            workout_types=workout_types,
            recent_exercises=recent_strength
        )

        return html

    def generate_weekly_report(self, week_end: date) -> str:
        """
        Generate a weekly training summary report.

        Args:
            week_end: The last day of the week (typically Sunday)

        Returns:
            HTML string with weekly analysis
        """
        week_start = week_end - timedelta(days=6)
        prev_week_start = week_start - timedelta(days=7)
        prev_week_end = week_start - timedelta(days=1)

        # Current week data
        activities = self._get_activities(week_start, week_end)
        prev_activities = self._get_activities(prev_week_start, prev_week_end)

        # Calculate comparisons
        current_stats = self._calculate_weekly_stats(activities)
        prev_stats = self._calculate_weekly_stats(prev_activities)

        # Monthly trend (last 4 weeks)
        monthly_volumes = self._get_weekly_volumes(week_end, weeks=4)

        # Workout breakdown
        workout_breakdown = self._get_workout_breakdown(activities)

        html = self._render_weekly_report(
            week_start=week_start,
            week_end=week_end,
            current_stats=current_stats,
            prev_stats=prev_stats,
            monthly_volumes=monthly_volumes,
            workout_breakdown=workout_breakdown,
            activities=activities
        )

        return html

    # --- Data Gathering Methods ---

    def _get_activities(self, start_date: date, end_date: date) -> List[CompletedActivity]:
        """Get activities within date range."""
        return self.db.query(CompletedActivity).filter(
            CompletedActivity.athlete_id == self.athlete_id,
            CompletedActivity.activity_date >= start_date,
            CompletedActivity.activity_date <= end_date
        ).order_by(CompletedActivity.activity_date.desc()).all()

    def _calculate_weekly_stats(self, activities: List[CompletedActivity]) -> Dict[str, Any]:
        """Calculate summary statistics for a set of activities."""
        total_workouts = len(activities)
        total_duration = sum(a.duration_minutes or 0 for a in activities)
        total_volume = 0

        strength_count = 0
        cardio_count = 0

        for a in activities:
            if a.activity_type == 'strength':
                strength_count += 1
                if a.activity_data:
                    data = json.loads(a.activity_data)
                    total_volume += data.get('total_volume_lbs', 0)
            elif a.activity_type in ('swim', 'run', 'bike'):
                cardio_count += 1

        return {
            'total_workouts': total_workouts,
            'total_duration': total_duration,
            'total_volume': total_volume,
            'strength_count': strength_count,
            'cardio_count': cardio_count,
            'avg_duration': total_duration / total_workouts if total_workouts else 0
        }

    def _get_daily_volumes(self, start_date: date, end_date: date) -> List[float]:
        """Get daily training volumes for sparkline."""
        activities = self._get_activities(start_date, end_date)

        volume_by_day = {}
        current = start_date
        while current <= end_date:
            volume_by_day[current] = 0
            current += timedelta(days=1)

        for a in activities:
            if a.activity_data:
                data = json.loads(a.activity_data)
                volume_by_day[a.activity_date] += data.get('total_volume_lbs', 0)

        return [volume_by_day[d] for d in sorted(volume_by_day.keys())]

    def _get_workout_type_distribution(self, activities: List[CompletedActivity]) -> Dict[str, int]:
        """Get distribution of workout types."""
        distribution = defaultdict(int)
        for a in activities:
            distribution[a.activity_name or a.activity_type] += 1
        return dict(distribution)

    def _get_recent_strength_exercises(self, report_date: date, days: int = 7) -> List[Dict[str, Any]]:
        """Get top exercises from recent strength workouts."""
        start_date = report_date - timedelta(days=days)
        activities = self.db.query(CompletedActivity).filter(
            CompletedActivity.athlete_id == self.athlete_id,
            CompletedActivity.activity_type == 'strength',
            CompletedActivity.activity_date >= start_date,
            CompletedActivity.activity_date <= report_date
        ).all()

        exercise_stats = defaultdict(lambda: {'count': 0, 'total_volume': 0, 'max_weight': 0})

        for a in activities:
            if a.activity_data:
                data = json.loads(a.activity_data)
                for ex in data.get('exercises', []):
                    name = ex.get('title') or ex.get('exercise_name', 'Unknown')
                    exercise_stats[name]['count'] += 1

                    for s in ex.get('sets', []):
                        weight = s.get('weight_lbs', 0) or 0
                        reps = s.get('reps', 0) or 0
                        exercise_stats[name]['total_volume'] += weight * reps
                        exercise_stats[name]['max_weight'] = max(
                            exercise_stats[name]['max_weight'], weight
                        )

        # Sort by volume and return top 10
        sorted_exercises = sorted(
            exercise_stats.items(),
            key=lambda x: x[1]['total_volume'],
            reverse=True
        )[:10]

        return [
            {'name': name, **stats}
            for name, stats in sorted_exercises
        ]

    def _get_weekly_volumes(self, end_date: date, weeks: int = 4) -> List[float]:
        """Get weekly volumes for trend sparkline."""
        volumes = []
        for i in range(weeks - 1, -1, -1):
            week_end = end_date - timedelta(days=i * 7)
            week_start = week_end - timedelta(days=6)

            activities = self._get_activities(week_start, week_end)
            week_volume = 0
            for a in activities:
                if a.activity_data:
                    data = json.loads(a.activity_data)
                    week_volume += data.get('total_volume_lbs', 0)
            volumes.append(week_volume)

        return volumes

    def _get_workout_breakdown(self, activities: List[CompletedActivity]) -> List[Dict[str, Any]]:
        """Get detailed workout breakdown for the week."""
        return [
            {
                'date': a.activity_date.strftime('%a %m/%d'),
                'type': a.activity_type,
                'name': a.activity_name or a.activity_type,
                'duration': a.duration_minutes or 0,
                'volume': json.loads(a.activity_data).get('total_volume_lbs', 0) if a.activity_data else 0
            }
            for a in sorted(activities, key=lambda x: x.activity_date)
        ]

    # --- Report Rendering Methods ---

    def _render_daily_report(
        self,
        report_date: date,
        today_activities: List[CompletedActivity],
        weekly_stats: Dict[str, Any],
        volume_by_day: List[float],
        workout_types: Dict[str, int],
        recent_exercises: List[Dict[str, Any]]
    ) -> str:
        """Render the daily report HTML."""
        athlete_name = self.athlete.name if self.athlete else "Athlete"

        # Generate visualizations
        volume_sparkline = generate_sparkline(volume_by_day, width=120, height=24)
        workout_bar = generate_bar_sparkline(
            [1 if v > 0 else 0 for v in volume_by_day],
            width=80, height=16
        )

        # Today's activity summary
        today_summary = ""
        if today_activities:
            for a in today_activities:
                duration = f"{a.duration_minutes} min" if a.duration_minutes else "--"
                vol = ""
                if a.activity_data:
                    data = json.loads(a.activity_data)
                    if data.get('total_volume_lbs'):
                        vol = f" | {data['total_volume_lbs']:,.0f} lbs"
                today_summary += f"<li><strong>{a.activity_name}</strong> - {duration}{vol}</li>"
        else:
            today_summary = "<li class='muted'>Rest day</li>"

        # Top exercises table
        exercises_table = generate_data_table(
            recent_exercises,
            [
                ('name', 'Exercise'),
                ('count', 'Sessions'),
                ('total_volume', 'Volume (lbs)'),
                ('max_weight', 'Max (lbs)')
            ],
            highlight_column='total_volume'
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Training Report - {report_date}</title>
    <style>
        :root {{
            --text: #333;
            --muted: #666;
            --light: #999;
            --bg: #fff;
            --border: #eee;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            font-family: 'ET Book', 'Palatino Linotype', Palatino, 'Book Antiqua', Georgia, serif;
            max-width: 720px;
            margin: 0 auto;
            padding: 24px 16px;
            color: var(--text);
            line-height: 1.5;
            background: var(--bg);
        }}
        h1 {{ font-size: 24px; font-weight: 400; margin: 0 0 4px 0; }}
        h2 {{ font-size: 16px; font-weight: 600; margin: 24px 0 8px 0; border-bottom: 1px solid var(--border); padding-bottom: 4px; }}
        .subtitle {{ color: var(--muted); font-size: 14px; margin-bottom: 24px; }}
        .muted {{ color: var(--muted); }}
        .metric-row {{ display: flex; gap: 24px; flex-wrap: wrap; margin: 16px 0; }}
        .metric {{
            display: flex;
            flex-direction: column;
        }}
        .metric-value {{ font-size: 28px; font-weight: 300; font-variant-numeric: tabular-nums; }}
        .metric-label {{ font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; }}
        .metric-spark {{ margin-top: 4px; }}
        ul {{ padding-left: 20px; margin: 8px 0; }}
        li {{ margin: 4px 0; }}
        .slope-graph {{ display: flex; align-items: center; gap: 8px; margin: 4px 0; }}
        .slope-label {{ width: 100px; font-size: 13px; }}
        .slope-before, .slope-after {{ font-variant-numeric: tabular-nums; font-size: 13px; }}
        .slope-change {{ font-size: 11px; }}
        footer {{ margin-top: 32px; padding-top: 16px; border-top: 1px solid var(--border); font-size: 12px; color: var(--light); }}
    </style>
</head>
<body>
    <header>
        <h1>Training Report</h1>
        <p class="subtitle">{athlete_name} | {report_date.strftime('%A, %B %d, %Y')}</p>
    </header>

    <section>
        <h2>Today</h2>
        <ul>
            {today_summary}
        </ul>
    </section>

    <section>
        <h2>Week at a Glance</h2>
        <div class="metric-row">
            <div class="metric">
                <span class="metric-value">{weekly_stats['total_workouts']}</span>
                <span class="metric-label">Workouts</span>
                <span class="metric-spark">{workout_bar}</span>
            </div>
            <div class="metric">
                <span class="metric-value">{weekly_stats['total_duration']}</span>
                <span class="metric-label">Minutes</span>
            </div>
            <div class="metric">
                <span class="metric-value">{weekly_stats['total_volume']:,.0f}</span>
                <span class="metric-label">Lbs Lifted</span>
                <span class="metric-spark">{volume_sparkline}</span>
            </div>
        </div>
        <p class="muted" style="font-size: 13px;">
            {weekly_stats['strength_count']} strength | {weekly_stats['cardio_count']} cardio |
            avg {weekly_stats['avg_duration']:.0f} min/session
        </p>
    </section>

    <section>
        <h2>Top Exercises (7 days)</h2>
        {exercises_table}
    </section>

    <footer>
        Generated {date.today().strftime('%Y-%m-%d %H:%M')} | Training Optimization System
    </footer>
</body>
</html>"""

    def _render_weekly_report(
        self,
        week_start: date,
        week_end: date,
        current_stats: Dict[str, Any],
        prev_stats: Dict[str, Any],
        monthly_volumes: List[float],
        workout_breakdown: List[Dict[str, Any]],
        activities: List[CompletedActivity]
    ) -> str:
        """Render the weekly report HTML."""
        athlete_name = self.athlete.name if self.athlete else "Athlete"

        # Generate visualizations
        volume_trend = generate_sparkline(monthly_volumes, width=100, height=24, show_endpoints=True)

        # Week over week comparisons
        workout_slope = generate_slope_graph(
            prev_stats['total_workouts'],
            current_stats['total_workouts'],
            "Workouts",
            good_direction="up"
        )
        volume_slope = generate_slope_graph(
            prev_stats['total_volume'],
            current_stats['total_volume'],
            "Volume",
            good_direction="up"
        )
        duration_slope = generate_slope_graph(
            prev_stats['total_duration'],
            current_stats['total_duration'],
            "Duration",
            good_direction="up"
        )

        # Workout table
        workout_table = generate_data_table(
            workout_breakdown,
            [
                ('date', 'Date'),
                ('name', 'Workout'),
                ('duration', 'Duration'),
                ('volume', 'Volume')
            ]
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Weekly Training Report - Week of {week_start}</title>
    <style>
        :root {{
            --text: #333;
            --muted: #666;
            --light: #999;
            --bg: #fff;
            --border: #eee;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            font-family: 'ET Book', 'Palatino Linotype', Palatino, 'Book Antiqua', Georgia, serif;
            max-width: 720px;
            margin: 0 auto;
            padding: 24px 16px;
            color: var(--text);
            line-height: 1.5;
            background: var(--bg);
        }}
        h1 {{ font-size: 24px; font-weight: 400; margin: 0 0 4px 0; }}
        h2 {{ font-size: 16px; font-weight: 600; margin: 24px 0 8px 0; border-bottom: 1px solid var(--border); padding-bottom: 4px; }}
        .subtitle {{ color: var(--muted); font-size: 14px; margin-bottom: 24px; }}
        .muted {{ color: var(--muted); }}
        .metric-row {{ display: flex; gap: 24px; flex-wrap: wrap; margin: 16px 0; }}
        .metric {{
            display: flex;
            flex-direction: column;
        }}
        .metric-value {{ font-size: 28px; font-weight: 300; font-variant-numeric: tabular-nums; }}
        .metric-label {{ font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; }}
        .comparisons {{ margin: 16px 0; }}
        .slope-graph {{ display: flex; align-items: center; gap: 8px; margin: 8px 0; font-size: 13px; }}
        .slope-label {{ width: 80px; }}
        .slope-before, .slope-after {{ font-variant-numeric: tabular-nums; width: 50px; }}
        .slope-change {{ font-size: 11px; width: 60px; }}
        footer {{ margin-top: 32px; padding-top: 16px; border-top: 1px solid var(--border); font-size: 12px; color: var(--light); }}
    </style>
</head>
<body>
    <header>
        <h1>Weekly Summary</h1>
        <p class="subtitle">{athlete_name} | {week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}</p>
    </header>

    <section>
        <h2>This Week</h2>
        <div class="metric-row">
            <div class="metric">
                <span class="metric-value">{current_stats['total_workouts']}</span>
                <span class="metric-label">Workouts</span>
            </div>
            <div class="metric">
                <span class="metric-value">{current_stats['total_duration']}</span>
                <span class="metric-label">Minutes</span>
            </div>
            <div class="metric">
                <span class="metric-value">{current_stats['total_volume']:,.0f}</span>
                <span class="metric-label">Lbs Lifted</span>
            </div>
        </div>
    </section>

    <section>
        <h2>Week over Week</h2>
        <div class="comparisons">
            {workout_slope}
            {volume_slope}
            {duration_slope}
        </div>
        <p class="muted" style="font-size: 12px; margin-top: 12px;">
            4-week volume trend: {volume_trend}
        </p>
    </section>

    <section>
        <h2>Workout Log</h2>
        {workout_table}
    </section>

    <footer>
        Generated {date.today().strftime('%Y-%m-%d %H:%M')} | Training Optimization System
    </footer>
</body>
</html>"""
