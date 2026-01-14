"""Dashboard generation for the Training Optimization System."""

import json
from datetime import date, datetime, timedelta
from collections import defaultdict


def generate_dashboard_html(db):
    """Generate comprehensive fitness dashboard HTML."""
    from database.models import CompletedActivity, Athlete

    # Get athlete info
    athlete = db.query(Athlete).first()
    athlete_name = athlete.name if athlete else "Athlete"
    goals = json.loads(athlete.goals) if athlete and athlete.goals else {}

    # Get all activities
    activities = db.query(CompletedActivity).order_by(
        CompletedActivity.activity_date.desc()
    ).all()

    if not activities:
        return _empty_dashboard_html(athlete_name)

    # Calculate statistics
    total_workouts = len(activities)
    total_minutes = sum(a.duration_minutes or 0 for a in activities)

    # Date range
    dates = [a.activity_date for a in activities]
    min_date = min(dates)
    max_date = max(dates)

    # Activity by date for calendar
    activity_by_date = defaultdict(list)
    for a in activities:
        activity_by_date[a.activity_date].append(a)

    # Monthly breakdown
    monthly_counts = defaultdict(int)
    monthly_minutes = defaultdict(int)
    for a in activities:
        month_key = a.activity_date.strftime("%Y-%m")
        monthly_counts[month_key] += 1
        monthly_minutes[month_key] += a.duration_minutes or 0

    # Day of week breakdown
    day_counts = defaultdict(int)
    for a in activities:
        day_counts[a.activity_date.weekday()] += 1

    # Activity type breakdown
    type_counts = defaultdict(int)
    for a in activities:
        type_counts[a.activity_type or "other"] += 1

    # Calculate current streak
    streak = 0
    check_date = date.today()
    while check_date >= min_date:
        if check_date in activity_by_date:
            streak += 1
            check_date -= timedelta(days=1)
        elif (date.today() - check_date).days <= 1:
            # Allow one rest day
            check_date -= timedelta(days=1)
        else:
            break

    # Weekly volume (last 12 weeks)
    weekly_hours = []
    for i in range(12):
        week_end = date.today() - timedelta(days=date.today().weekday()) - timedelta(weeks=i)
        week_start = week_end - timedelta(days=6)
        week_minutes = sum(
            a.duration_minutes or 0 for a in activities
            if week_start <= a.activity_date <= week_end
        )
        weekly_hours.append((week_start, week_minutes / 60))

    # Generate HTML sections
    calendar_html = _generate_calendar_heatmap(activity_by_date, min_date)
    goals_html = _generate_goals_section(goals, activities, weekly_hours)
    monthly_chart = _generate_monthly_chart(monthly_counts, monthly_minutes)
    day_chart = _generate_day_of_week_chart(day_counts)
    type_chart = _generate_type_breakdown(type_counts)
    recent_html = _generate_recent_activities(activities[:10])
    weekly_chart = _generate_weekly_volume_chart(weekly_hours, goals.get("weekly_volume", {}).get("target", 4))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Training Dashboard - {athlete_name}</title>
    <style>
        :root {{
            --text: #1a1a1a;
            --muted: #666;
            --light: #999;
            --bg: #fafafa;
            --card: #fff;
            --border: #e5e5e5;
            --accent: #2563eb;
            --success: #059669;
            --warning: #d97706;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.5;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{ margin-bottom: 24px; }}
        h1 {{ font-size: 28px; font-weight: 600; margin-bottom: 4px; }}
        .subtitle {{ color: var(--muted); font-size: 14px; }}

        .stats-row {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .stat-card {{
            background: var(--card);
            border-radius: 12px;
            padding: 16px;
            border: 1px solid var(--border);
        }}
        .stat-value {{ font-size: 32px; font-weight: 600; color: var(--accent); }}
        .stat-label {{ font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; }}

        .section {{
            background: var(--card);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid var(--border);
        }}
        .section-title {{
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        /* Calendar Heatmap */
        .calendar-container {{
            display: grid;
            grid-template-columns: 1fr 320px;
            gap: 24px;
        }}
        @media (max-width: 900px) {{
            .calendar-container {{ grid-template-columns: 1fr; }}
        }}
        .calendar {{ overflow-x: auto; }}
        .calendar-grid {{
            display: flex;
            gap: 3px;
            padding: 8px 0;
        }}
        .calendar-week {{ display: flex; flex-direction: column; gap: 3px; }}
        .calendar-day {{
            width: 12px;
            height: 12px;
            border-radius: 2px;
            background: #ebedf0;
            cursor: pointer;
            transition: transform 0.1s;
        }}
        .calendar-day.has-activity {{ cursor: pointer; }}
        .calendar-day.has-activity:hover {{ transform: scale(1.3); }}
        .calendar-day.selected {{ outline: 2px solid var(--accent); outline-offset: 1px; }}
        .calendar-day.l1 {{ background: #9be9a8; }}
        .calendar-day.l2 {{ background: #40c463; }}
        .calendar-day.l3 {{ background: #30a14e; }}
        .calendar-day.l4 {{ background: #216e39; }}
        .calendar-labels {{ display: flex; gap: 3px; font-size: 10px; color: var(--muted); margin-bottom: 4px; }}
        .calendar-month-labels {{ display: flex; font-size: 10px; color: var(--muted); margin-bottom: 8px; }}
        .calendar-legend {{ display: flex; align-items: center; gap: 4px; font-size: 11px; color: var(--muted); margin-top: 8px; }}
        .calendar-legend span {{ display: flex; align-items: center; gap: 2px; }}

        /* Activity Details Panel */
        .activity-details {{
            background: #f8fafc;
            border-radius: 12px;
            padding: 20px;
            min-height: 200px;
        }}
        .activity-details.empty {{
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--muted);
            text-align: center;
        }}
        .details-header {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 4px;
        }}
        .details-date {{
            font-size: 13px;
            color: var(--muted);
            margin-bottom: 16px;
        }}
        .details-workout {{
            background: white;
            border-radius: 8px;
            padding: 14px;
            margin-bottom: 12px;
            border: 1px solid var(--border);
        }}
        .details-workout:last-child {{ margin-bottom: 0; }}
        .details-workout-name {{
            font-weight: 600;
            margin-bottom: 4px;
        }}
        .details-workout-meta {{
            font-size: 13px;
            color: var(--muted);
            display: flex;
            gap: 16px;
            flex-wrap: wrap;
        }}
        .details-workout-meta span {{
            display: flex;
            align-items: center;
            gap: 4px;
        }}
        .details-exercises {{
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid var(--border);
        }}
        .details-exercise {{
            font-size: 13px;
            padding: 4px 0;
            display: flex;
            justify-content: space-between;
        }}
        .details-exercise-name {{ color: var(--text); }}
        .details-exercise-sets {{ color: var(--muted); }}

        /* Goals */
        .goal-card {{
            background: #f8fafc;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
        }}
        .goal-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
        .goal-name {{ font-weight: 500; }}
        .goal-values {{ font-size: 13px; color: var(--muted); }}
        .progress-bar {{ height: 8px; background: #e5e7eb; border-radius: 4px; overflow: hidden; }}
        .progress-fill {{ height: 100%; border-radius: 4px; transition: width 0.3s; }}
        .progress-fill.good {{ background: var(--success); }}
        .progress-fill.warning {{ background: var(--warning); }}
        .progress-fill.accent {{ background: var(--accent); }}

        /* Charts */
        .chart-container {{ padding: 8px 0; }}
        .bar-chart {{ display: flex; align-items: flex-end; gap: 4px; height: 100px; }}
        .bar {{
            flex: 1;
            background: var(--accent);
            border-radius: 2px 2px 0 0;
            min-width: 20px;
            position: relative;
            opacity: 0.7;
        }}
        .bar:hover {{ opacity: 1; }}
        .bar-label {{
            position: absolute;
            bottom: -18px;
            left: 50%;
            transform: translateX(-50%);
            font-size: 9px;
            color: var(--muted);
            white-space: nowrap;
        }}

        .horizontal-bar {{ display: flex; align-items: center; gap: 8px; margin: 8px 0; }}
        .horizontal-bar-label {{ width: 80px; font-size: 12px; }}
        .horizontal-bar-track {{ flex: 1; height: 20px; background: #e5e7eb; border-radius: 4px; overflow: hidden; }}
        .horizontal-bar-fill {{ height: 100%; background: var(--accent); border-radius: 4px; display: flex; align-items: center; justify-content: flex-end; padding-right: 8px; }}
        .horizontal-bar-value {{ font-size: 11px; color: white; font-weight: 500; }}

        /* Recent Activities */
        .activity-list {{ }}
        .activity-item {{
            border-bottom: 1px solid var(--border);
            cursor: pointer;
            transition: background 0.15s;
        }}
        .activity-item:last-child {{ border-bottom: none; }}
        .activity-item:hover {{ background: #f8fafc; }}
        .activity-item.expanded {{ background: #f8fafc; }}
        .activity-header {{
            display: flex;
            align-items: center;
            padding: 10px 0;
        }}
        .activity-date {{ width: 60px; font-size: 12px; color: var(--muted); }}
        .activity-name {{ flex: 1; font-weight: 500; }}
        .activity-meta {{ font-size: 12px; color: var(--muted); }}
        .activity-type {{
            font-size: 10px;
            padding: 2px 8px;
            border-radius: 12px;
            background: #e5e7eb;
            margin-left: 8px;
        }}
        .activity-expand-icon {{
            margin-left: 8px;
            color: var(--muted);
            transition: transform 0.2s;
        }}
        .activity-item.expanded .activity-expand-icon {{ transform: rotate(180deg); }}
        .activity-details-expand {{
            display: none;
            padding: 0 0 12px 60px;
        }}
        .activity-item.expanded .activity-details-expand {{ display: block; }}
        .activity-exercise-list {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 8px;
        }}
        .activity-exercise-item {{
            font-size: 12px;
            padding: 6px 10px;
            background: white;
            border-radius: 6px;
            border: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
        }}
        .activity-exercise-item .ex-name {{ color: var(--text); }}
        .activity-exercise-item .ex-sets {{ color: var(--muted); }}

        /* Grid layout */
        .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        @media (max-width: 768px) {{
            .two-col {{ grid-template-columns: 1fr; }}
        }}

        footer {{
            text-align: center;
            padding: 20px;
            color: var(--light);
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Training Dashboard</h1>
            <p class="subtitle">{athlete_name} · Updated {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        </header>

        <div class="stats-row">
            <div class="stat-card">
                <div class="stat-value">{total_workouts}</div>
                <div class="stat-label">Total Workouts</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{total_minutes // 60}h</div>
                <div class="stat-label">Total Time</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{streak}</div>
                <div class="stat-label">Current Streak</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(monthly_counts)}</div>
                <div class="stat-label">Active Months</div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">📅 Activity Calendar</div>
            <div class="calendar-container">
                {calendar_html}
                <div class="activity-details empty" id="activity-details">
                    <div>
                        <div style="font-size: 24px; margin-bottom: 8px;">📅</div>
                        <div>Click a day to see activity details</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">🎯 Goals Progress</div>
            {goals_html}
        </div>

        <div class="section">
            <div class="section-title">📊 Weekly Volume (Last 12 Weeks)</div>
            {weekly_chart}
        </div>

        <div class="two-col">
            <div class="section">
                <div class="section-title">📈 Monthly Activity</div>
                {monthly_chart}
            </div>
            <div class="section">
                <div class="section-title">📅 Day of Week</div>
                {day_chart}
            </div>
        </div>

        <div class="two-col">
            <div class="section">
                <div class="section-title">💪 Workout Types</div>
                {type_chart}
            </div>
            <div class="section">
                <div class="section-title">🏃 Recent Activity</div>
                {recent_html}
            </div>
        </div>

        <footer>
            Training Optimization System · Data from {min_date.strftime('%b %Y')} to {max_date.strftime('%b %Y')}
        </footer>
    </div>
</body>
</html>"""


def _generate_calendar_heatmap(activity_by_date, min_date):
    """Generate GitHub-style calendar heatmap for the past year with click interaction."""
    today = date.today()
    start_date = today - timedelta(days=365)

    # Align to start of week (Sunday)
    start_date = start_date - timedelta(days=(start_date.weekday() + 1) % 7)

    weeks_html = []
    current_date = start_date
    month_labels = []
    last_month = None
    week_idx = 0

    # Build activity data for JavaScript
    activity_data = {}

    while current_date <= today:
        week_days = []
        for day in range(7):
            if current_date <= today:
                activities = activity_by_date.get(current_date, [])
                count = len(activities)
                level = "l0"
                if count == 1:
                    level = "l1"
                elif count == 2:
                    level = "l2"
                elif count == 3:
                    level = "l3"
                elif count >= 4:
                    level = "l4"

                date_str = current_date.strftime('%Y-%m-%d')
                title = f"{current_date.strftime('%b %d, %Y')}: {count} workout{'s' if count != 1 else ''}"

                css_classes = ["calendar-day"]
                if count > 0:
                    css_classes.append(level)
                    css_classes.append("has-activity")
                    # Store activity data for this date
                    activity_data[date_str] = []
                    for a in activities:
                        workout_info = {
                            "name": a.activity_name or a.activity_type or "Workout",
                            "type": a.activity_type or "other",
                            "duration": a.duration_minutes or 0,
                            "source": a.source or "unknown",
                            "exercises": []
                        }
                        # Parse exercises/laps from activity_data if available
                        if a.activity_data:
                            try:
                                data = json.loads(a.activity_data) if isinstance(a.activity_data, str) else a.activity_data
                                # Handle strength exercises from Hevy
                                if "exercises" in data:
                                    for ex in data["exercises"][:8]:  # Limit to 8 exercises
                                        ex_info = {
                                            "name": ex.get("exercise_name", ex.get("title", ex.get("name", "Exercise"))),
                                            "sets": len(ex.get("sets", [])) if "sets" in ex else ex.get("sets", 0)
                                        }
                                        workout_info["exercises"].append(ex_info)
                                # Handle swim laps from Garmin
                                elif "laps" in data and data["laps"]:
                                    workout_info["swim_data"] = {
                                        "distance": data.get("distance_meters"),
                                        "pace": data.get("avg_pace_per_100y"),
                                        "calories": data.get("calories"),
                                        "avg_hr": data.get("avg_heart_rate"),
                                        "max_hr": data.get("max_heart_rate"),
                                    }
                                    for lap in data["laps"][:12]:  # Limit to 12 laps
                                        if lap.get("distance_meters", 0) > 0:  # Skip rest laps
                                            lap_info = {
                                                "name": f"Lap {lap.get('lap_number', '?')}",
                                                "detail": f"{int(lap.get('distance_meters', 0) * 1.09361)}yd @ {lap.get('pace_per_100y', '?')}/100y"
                                            }
                                            workout_info["exercises"].append(lap_info)
                            except (json.JSONDecodeError, TypeError):
                                pass
                        activity_data[date_str].append(workout_info)

                week_days.append(f'<div class="{" ".join(css_classes)}" data-date="{date_str}" title="{title}"></div>')

                # Track month changes for labels
                if current_date.month != last_month:
                    month_labels.append((week_idx, current_date.strftime('%b')))
                    last_month = current_date.month
            else:
                week_days.append('<div class="calendar-day" style="visibility:hidden;"></div>')
            current_date += timedelta(days=1)

        weeks_html.append(f'<div class="calendar-week">{"".join(week_days)}</div>')
        week_idx += 1

    # Generate month labels row
    month_label_html = '<div class="calendar-month-labels">'
    label_positions = {pos: label for pos, label in month_labels}
    for i in range(len(weeks_html)):
        if i in label_positions:
            month_label_html += f'<span style="width:15px;text-align:left;">{label_positions[i]}</span>'
        else:
            month_label_html += '<span style="width:15px;"></span>'
    month_label_html += '</div>'

    # JavaScript for interactivity
    activity_json = json.dumps(activity_data)

    js_code = f"""
    <script>
    const activityData = {activity_json};

    document.querySelectorAll('.calendar-day.has-activity').forEach(day => {{
        day.addEventListener('click', function() {{
            // Remove previous selection
            document.querySelectorAll('.calendar-day.selected').forEach(d => d.classList.remove('selected'));
            this.classList.add('selected');

            const dateStr = this.getAttribute('data-date');
            const activities = activityData[dateStr] || [];
            const detailsPanel = document.getElementById('activity-details');

            if (activities.length === 0) {{
                detailsPanel.className = 'activity-details empty';
                detailsPanel.innerHTML = '<div><div style="font-size: 24px; margin-bottom: 8px;">📅</div><div>No activities on this day</div></div>';
                return;
            }}

            const dateObj = new Date(dateStr + 'T12:00:00');
            const formattedDate = dateObj.toLocaleDateString('en-US', {{ weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }});

            let html = '<div class="details-header">' + activities.length + ' Workout' + (activities.length > 1 ? 's' : '') + '</div>';
            html += '<div class="details-date">' + formattedDate + '</div>';

            activities.forEach(workout => {{
                html += '<div class="details-workout">';
                html += '<div class="details-workout-name">' + workout.name + '</div>';
                html += '<div class="details-workout-meta">';
                if (workout.duration) {{
                    html += '<span>⏱️ ' + workout.duration + ' min</span>';
                }}
                html += '<span>📍 ' + workout.source + '</span>';
                html += '</div>';

                // Show swim summary if available
                if (workout.swim_data) {{
                    html += '<div style="margin-top: 8px; padding: 8px; background: #f0f9ff; border-radius: 6px; font-size: 13px;">';
                    const swim = workout.swim_data;
                    if (swim.distance) html += '<div>🏊 ' + Math.round(swim.distance * 1.09361) + ' yards</div>';
                    if (swim.pace) html += '<div>⚡ ' + swim.pace + '/100y avg pace</div>';
                    if (swim.avg_hr) html += '<div>❤️ ' + swim.avg_hr + ' avg / ' + (swim.max_hr || '?') + ' max HR</div>';
                    if (swim.calories) html += '<div>🔥 ' + swim.calories + ' calories</div>';
                    html += '</div>';
                }}

                if (workout.exercises && workout.exercises.length > 0) {{
                    html += '<div class="details-exercises">';
                    workout.exercises.forEach(ex => {{
                        html += '<div class="details-exercise">';
                        html += '<span class="details-exercise-name">' + ex.name + '</span>';
                        if (ex.sets) {{
                            html += '<span class="details-exercise-sets">' + ex.sets + ' sets</span>';
                        }} else if (ex.detail) {{
                            html += '<span class="details-exercise-sets">' + ex.detail + '</span>';
                        }}
                        html += '</div>';
                    }});
                    if (workout.exercises.length >= 8) {{
                        html += '<div style="font-size: 11px; color: var(--muted); margin-top: 4px;">+ more...</div>';
                    }}
                    html += '</div>';
                }}
                html += '</div>';
            }});

            detailsPanel.className = 'activity-details';
            detailsPanel.innerHTML = html;
        }});
    }});
    </script>
    """

    return f"""
    <div class="calendar">
        {month_label_html}
        <div class="calendar-labels">
            <span style="width:12px;"></span>
            <span style="width:15px;">M</span>
            <span style="width:15px;"></span>
            <span style="width:15px;">W</span>
            <span style="width:15px;"></span>
            <span style="width:15px;">F</span>
            <span style="width:15px;"></span>
        </div>
        <div class="calendar-grid">
            {"".join(weeks_html)}
        </div>
        <div class="calendar-legend">
            <span>Less</span>
            <div class="calendar-day"></div>
            <div class="calendar-day l1"></div>
            <div class="calendar-day l2"></div>
            <div class="calendar-day l3"></div>
            <div class="calendar-day l4"></div>
            <span>More</span>
        </div>
    </div>
    {js_code}
    """


def _generate_goals_section(goals, activities, weekly_hours):
    """Generate goals progress cards."""
    html = ""

    # Weekly Volume Goal
    if "weekly_volume" in goals:
        target = goals["weekly_volume"].get("target", 4)
        recent_weeks = weekly_hours[:4]  # Last 4 weeks
        avg_hours = sum(h for _, h in recent_weeks) / len(recent_weeks) if recent_weeks else 0
        pct = min(100, (avg_hours / target) * 100)
        color = "good" if pct >= 80 else "warning" if pct >= 50 else "accent"
        html += f"""
        <div class="goal-card">
            <div class="goal-header">
                <span class="goal-name">Weekly Training Volume</span>
                <span class="goal-values">{avg_hours:.1f}h / {target}h target</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill {color}" style="width: {pct}%"></div>
            </div>
        </div>
        """

    # Body Fat Goal
    if "body_fat" in goals:
        target = goals["body_fat"].get("target", 14)
        current = goals["body_fat"].get("current") or "Not measured"
        html += f"""
        <div class="goal-card">
            <div class="goal-header">
                <span class="goal-name">Body Fat %</span>
                <span class="goal-values">{current} → {target}%</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill accent" style="width: 0%"></div>
            </div>
            <div style="font-size: 11px; color: var(--muted); margin-top: 4px;">Add measurement to track progress</div>
        </div>
        """

    # VO2 Max Goal
    if "vo2_max" in goals:
        target = goals["vo2_max"].get("target", 55)
        current = goals["vo2_max"].get("current") or "Not measured"
        html += f"""
        <div class="goal-card">
            <div class="goal-header">
                <span class="goal-name">VO2 Max</span>
                <span class="goal-values">{current} → {target} ml/kg/min</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill accent" style="width: 0%"></div>
            </div>
            <div style="font-size: 11px; color: var(--muted); margin-top: 4px;">Sync from Garmin to track progress</div>
        </div>
        """

    # 400yd Freestyle Goal
    if "400yd_freestyle" in goals:
        target = goals["400yd_freestyle"].get("target", 300)  # ~5 min target
        current = goals["400yd_freestyle"].get("current") or "Not timed"
        # Format time nicely for display
        def format_swim_time(seconds):
            if isinstance(seconds, (int, float)):
                mins = int(seconds // 60)
                secs = int(seconds % 60)
                return f"{mins}:{secs:02d}"
            return seconds
        current_display = format_swim_time(current) if current != "Not timed" else current
        target_display = format_swim_time(target)
        html += f"""
        <div class="goal-card">
            <div class="goal-header">
                <span class="goal-name">400yd Freestyle</span>
                <span class="goal-values">{current_display} → {target_display}</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill accent" style="width: 0%"></div>
            </div>
        </div>
        """

    # Explosive Strength
    if "explosive_strength" in goals:
        metrics = goals["explosive_strength"].get("metrics", {})
        for name, data in metrics.items():
            current = data.get("current", "?")
            target = data.get("target", "?")
            unit = data.get("unit", "")
            pct = 0
            if isinstance(current, (int, float)) and isinstance(target, (int, float)) and target > 0:
                pct = min(100, (current / target) * 100)
            color = "good" if pct >= 90 else "warning" if pct >= 70 else "accent"
            html += f"""
            <div class="goal-card">
                <div class="goal-header">
                    <span class="goal-name">{name.replace('_', ' ').title()}</span>
                    <span class="goal-values">{current} → {target} {unit}</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill {color}" style="width: {pct}%"></div>
                </div>
            </div>
            """

    return html if html else "<p style='color: var(--muted);'>No goals configured</p>"


def _generate_weekly_volume_chart(weekly_hours, target):
    """Generate weekly volume bar chart with target line."""
    if not weekly_hours:
        return "<p>No data available</p>"

    max_hours = max(max(h for _, h in weekly_hours), target) or 1

    bars = []
    for week_start, hours in reversed(weekly_hours):
        height_pct = (hours / max_hours) * 100
        color = "#059669" if hours >= target else "#2563eb"
        label = week_start.strftime("%m/%d")
        bars.append(f'''
            <div class="bar" style="height: {height_pct}%; background: {color};" title="{hours:.1f}h">
                <span class="bar-label">{label}</span>
            </div>
        ''')

    target_pct = (target / max_hours) * 100

    return f"""
    <div class="chart-container" style="position: relative;">
        <div style="position: absolute; left: 0; right: 0; bottom: {target_pct}%; border-top: 2px dashed #d97706; z-index: 1;">
            <span style="position: absolute; right: 0; top: -16px; font-size: 10px; color: #d97706;">Target: {target}h</span>
        </div>
        <div class="bar-chart" style="padding-bottom: 24px;">
            {"".join(bars)}
        </div>
    </div>
    """


def _generate_monthly_chart(monthly_counts, monthly_minutes):
    """Generate monthly activity bar chart."""
    # Last 12 months
    months = sorted(monthly_counts.keys())[-12:]
    if not months:
        return "<p>No data available</p>"

    max_count = max(monthly_counts[m] for m in months) or 1

    bars = []
    for month in months:
        count = monthly_counts[month]
        height_pct = (count / max_count) * 100
        label = datetime.strptime(month, "%Y-%m").strftime("%b")
        bars.append(f'''
            <div class="bar" style="height: {height_pct}%;" title="{count} workouts">
                <span class="bar-label">{label}</span>
            </div>
        ''')

    return f"""
    <div class="chart-container">
        <div class="bar-chart" style="padding-bottom: 24px;">
            {"".join(bars)}
        </div>
    </div>
    """


def _generate_day_of_week_chart(day_counts):
    """Generate day of week horizontal bar chart."""
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    max_count = max(day_counts.values()) if day_counts else 1

    bars = []
    for i, day in enumerate(days):
        count = day_counts.get(i, 0)
        width_pct = (count / max_count) * 100 if max_count > 0 else 0
        bars.append(f'''
            <div class="horizontal-bar">
                <span class="horizontal-bar-label">{day}</span>
                <div class="horizontal-bar-track">
                    <div class="horizontal-bar-fill" style="width: {width_pct}%;">
                        <span class="horizontal-bar-value">{count}</span>
                    </div>
                </div>
            </div>
        ''')

    return "".join(bars)


def _generate_type_breakdown(type_counts):
    """Generate workout type breakdown."""
    if not type_counts:
        return "<p>No data available</p>"

    total = sum(type_counts.values())

    bars = []
    for activity_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        pct = (count / total) * 100
        bars.append(f'''
            <div class="horizontal-bar">
                <span class="horizontal-bar-label">{activity_type.title()}</span>
                <div class="horizontal-bar-track">
                    <div class="horizontal-bar-fill" style="width: {pct}%;">
                        <span class="horizontal-bar-value">{count} ({pct:.0f}%)</span>
                    </div>
                </div>
            </div>
        ''')

    return "".join(bars)


def _generate_recent_activities(activities):
    """Generate recent activities list with expandable exercise details."""
    if not activities:
        return "<p>No recent activities</p>"

    items = []
    for idx, a in enumerate(activities):
        date_str = a.activity_date.strftime("%b %d")
        duration = f"{a.duration_minutes}min" if a.duration_minutes else ""

        # Parse exercises/laps from activity_data
        exercises_html = ""
        has_exercises = False
        if a.activity_data:
            try:
                data = json.loads(a.activity_data) if isinstance(a.activity_data, str) else a.activity_data
                # Handle strength exercises from Hevy
                if "exercises" in data and data["exercises"]:
                    has_exercises = True
                    exercise_items = []
                    for ex in data["exercises"]:
                        ex_name = ex.get("exercise_name", ex.get("title", ex.get("name", "Exercise")))
                        ex_sets = len(ex.get("sets", [])) if "sets" in ex else ex.get("sets", 0)
                        sets_text = f"{ex_sets} sets" if ex_sets else ""
                        exercise_items.append(f'''
                            <div class="activity-exercise-item">
                                <span class="ex-name">{ex_name}</span>
                                <span class="ex-sets">{sets_text}</span>
                            </div>
                        ''')
                    exercises_html = f'<div class="activity-exercise-list">{"".join(exercise_items)}</div>'
                # Handle swim laps from Garmin
                elif "laps" in data and data["laps"]:
                    has_exercises = True
                    # Swim summary
                    distance_yards = int(data.get("distance_meters", 0) * 1.09361)
                    pace = data.get("avg_pace_per_100y", "?")
                    calories = data.get("calories", 0)
                    avg_hr = data.get("avg_heart_rate", 0)
                    max_hr = data.get("max_heart_rate", 0)

                    summary_html = f'''
                        <div style="background: #f0f9ff; border-radius: 8px; padding: 12px; margin-bottom: 12px;">
                            <div style="font-weight: 600; margin-bottom: 8px;">🏊 Swim Summary</div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 13px;">
                                <div>Distance: {distance_yards} yards</div>
                                <div>Avg Pace: {pace}/100y</div>
                                <div>Avg HR: {avg_hr} bpm</div>
                                <div>Max HR: {max_hr} bpm</div>
                                <div>Calories: {calories}</div>
                            </div>
                        </div>
                    '''

                    # Lap details
                    lap_items = []
                    for lap in data["laps"]:
                        if lap.get("distance_meters", 0) > 0:  # Skip rest intervals
                            lap_num = lap.get("lap_number", "?")
                            lap_dist = int(lap.get("distance_meters", 0) * 1.09361)
                            lap_pace = lap.get("pace_per_100y", "?")
                            lap_hr = lap.get("avg_heart_rate", "")
                            hr_text = f"{int(lap_hr)} bpm" if lap_hr else ""
                            lap_items.append(f'''
                                <div class="activity-exercise-item">
                                    <span class="ex-name">Lap {lap_num} ({lap_dist}yd)</span>
                                    <span class="ex-sets">{lap_pace}/100y {hr_text}</span>
                                </div>
                            ''')
                    exercises_html = summary_html + f'<div class="activity-exercise-list">{"".join(lap_items)}</div>'
            except (json.JSONDecodeError, TypeError):
                pass

        expand_icon = '<span class="activity-expand-icon">▼</span>' if has_exercises else ''

        items.append(f'''
            <div class="activity-item" data-idx="{idx}" {"onclick=\"this.classList.toggle('expanded')\"" if has_exercises else ""}>
                <div class="activity-header">
                    <span class="activity-date">{date_str}</span>
                    <span class="activity-name">{a.activity_name or a.activity_type}</span>
                    <span class="activity-meta">{duration}</span>
                    <span class="activity-type">{a.source}</span>
                    {expand_icon}
                </div>
                <div class="activity-details-expand">
                    {exercises_html}
                </div>
            </div>
        ''')

    return f'<div class="activity-list">{"".join(items)}</div>'


def _empty_dashboard_html(athlete_name):
    """Return empty dashboard HTML."""
    return f"""<!DOCTYPE html>
<html><head><title>Dashboard - {athlete_name}</title></head>
<body style="font-family: sans-serif; padding: 40px; text-align: center;">
<h1>No Data Yet</h1>
<p>Sync your Garmin and Hevy data to see your dashboard.</p>
</body></html>"""
