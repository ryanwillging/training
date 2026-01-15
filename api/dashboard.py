"""Dashboard generation for the Training Optimization System.

Uses Material Design-inspired components for consistent styling.
"""

import json
from datetime import date, datetime, timedelta
from collections import defaultdict

from api.design_system import wrap_page, get_stat_card, get_progress_card


def generate_dashboard_html(db):
    """Generate comprehensive fitness dashboard HTML with Material Design styling."""
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
    weekly_chart = _generate_weekly_volume_chart(weekly_hours, goals.get("weekly_volume", {}).get("target", 4))
    monthly_chart = _generate_monthly_chart(monthly_counts, monthly_minutes)
    day_chart = _generate_day_of_week_chart(day_counts)
    type_chart = _generate_type_breakdown(type_counts)
    recent_html = _generate_recent_activities(activities[:10])

    # Build stat cards
    stat_cards = f'''
    <div class="md-grid md-grid-cols-4 mb-6">
        {get_stat_card(str(total_workouts), "Total Workouts")}
        {get_stat_card(f"{total_minutes // 60}h", "Total Time")}
        {get_stat_card(str(streak), "Current Streak")}
        {get_stat_card(str(len(monthly_counts)), "Active Months")}
    </div>
    '''

    content = f'''
    <header class="mb-6">
        <h1 class="md-headline-large mb-2">Training Dashboard</h1>
        <p class="md-body-large text-secondary">{athlete_name} · Updated {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
    </header>

    {stat_cards}

    <div class="md-card mb-6">
        <div class="md-card-header">
            <h2 class="md-title-large">Activity Calendar</h2>
        </div>
        <div class="md-card-content">
            <div class="calendar-container">
                {calendar_html}
                <div class="activity-details empty" id="activity-details">
                    <div>
                        <div style="font-size: 24px; margin-bottom: 8px;">📅</div>
                        <div class="md-body-medium text-secondary">Click a day to see activity details</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="md-card mb-6">
        <div class="md-card-header">
            <h2 class="md-title-large">Goals Progress</h2>
        </div>
        <div class="md-card-content">
            {goals_html}
        </div>
    </div>

    <div class="md-card mb-6">
        <div class="md-card-header">
            <h2 class="md-title-large">Weekly Volume (Last 12 Weeks)</h2>
        </div>
        <div class="md-card-content">
            {weekly_chart}
        </div>
    </div>

    <div class="md-grid md-grid-cols-2 mb-6">
        <div class="md-card">
            <div class="md-card-header">
                <h2 class="md-title-large">Monthly Activity</h2>
            </div>
            <div class="md-card-content">
                {monthly_chart}
            </div>
        </div>
        <div class="md-card">
            <div class="md-card-header">
                <h2 class="md-title-large">Day of Week</h2>
            </div>
            <div class="md-card-content">
                {day_chart}
            </div>
        </div>
    </div>

    <div class="md-grid md-grid-cols-2 mb-6">
        <div class="md-card">
            <div class="md-card-header">
                <h2 class="md-title-large">Workout Types</h2>
            </div>
            <div class="md-card-content">
                {type_chart}
            </div>
        </div>
        <div class="md-card">
            <div class="md-card-header">
                <h2 class="md-title-large">Recent Activity</h2>
            </div>
            <div class="md-card-content">
                {recent_html}
            </div>
        </div>
    </div>

    <style>
        /* Calendar-specific styles */
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
            background: var(--md-outline-variant);
            cursor: default;
            transition: transform 0.1s;
        }}
        .calendar-day.has-activity {{ cursor: pointer; }}
        .calendar-day.has-activity:hover {{ transform: scale(1.3); }}
        .calendar-day.selected {{ outline: 2px solid var(--md-primary); outline-offset: 1px; }}
        .calendar-day.l1 {{ background: #6fbf73; }}
        .calendar-day.l2 {{ background: #4caf50; }}
        .calendar-day.l3 {{ background: #2e7d32; }}
        .calendar-wrapper {{ display: flex; align-items: flex-start; }}
        .calendar-day-labels {{
            display: flex;
            flex-direction: column;
            gap: 3px;
            font-size: 10px;
            color: var(--md-on-surface-variant);
            padding-right: 6px;
            flex-shrink: 0;
        }}
        .calendar-day-labels span {{
            height: 12px;
            line-height: 12px;
            text-align: right;
        }}
        .calendar-month-labels {{
            display: flex;
            gap: 3px;
            font-size: 10px;
            color: var(--md-on-surface-variant);
            margin-bottom: 4px;
            margin-left: 30px;
        }}
        .calendar-month-labels span {{
            width: 12px;
            text-align: left;
            white-space: nowrap;
            overflow: visible;
        }}
        .calendar-legend {{ display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--md-on-surface-variant); margin-top: 8px; margin-left: 30px; }}

        /* Activity Details Panel */
        .activity-details {{
            background: var(--md-surface-variant);
            border-radius: var(--radius-md);
            padding: 20px;
            min-height: 200px;
        }}
        .activity-details.empty {{
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
        }}
        .details-header {{
            font-size: 18px;
            font-weight: 500;
            margin-bottom: 4px;
        }}
        .details-date {{
            font-size: 13px;
            color: var(--md-on-surface-variant);
            margin-bottom: 16px;
        }}
        .details-workout {{
            background: var(--md-surface);
            border-radius: var(--radius-sm);
            padding: 14px;
            margin-bottom: 12px;
            border: 1px solid var(--md-outline-variant);
        }}
        .details-workout:last-child {{ margin-bottom: 0; }}
        .details-workout-name {{ font-weight: 500; margin-bottom: 4px; }}
        .details-workout-meta {{
            font-size: 13px;
            color: var(--md-on-surface-variant);
            display: flex;
            gap: 16px;
            flex-wrap: wrap;
        }}
        .details-exercises {{
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid var(--md-outline-variant);
        }}
        .details-exercise {{
            font-size: 13px;
            padding: 4px 0;
            display: flex;
            justify-content: space-between;
        }}

        /* Charts */
        .bar-chart {{ display: flex; align-items: flex-end; gap: 4px; height: 100px; }}
        .bar {{
            flex: 1;
            background: var(--md-primary);
            border-radius: 2px 2px 0 0;
            min-width: 20px;
            position: relative;
            opacity: 0.7;
            transition: opacity var(--transition-fast);
        }}
        .bar:hover {{ opacity: 1; }}
        .bar-label {{
            position: absolute;
            bottom: -18px;
            left: 50%;
            transform: translateX(-50%);
            font-size: 9px;
            color: var(--md-on-surface-variant);
            white-space: nowrap;
        }}

        .horizontal-bar {{ display: flex; align-items: center; gap: 8px; margin: 8px 0; }}
        .horizontal-bar-label {{ width: 80px; font-size: 12px; }}
        .horizontal-bar-track {{ flex: 1; height: 20px; background: var(--md-surface-variant); border-radius: var(--radius-xs); overflow: hidden; }}
        .horizontal-bar-fill {{
            height: 100%;
            background: var(--md-primary);
            border-radius: var(--radius-xs);
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding-right: 8px;
            transition: width var(--transition-medium);
        }}
        .horizontal-bar-value {{ font-size: 11px; color: white; font-weight: 500; }}

        /* Activity List */
        .activity-item {{
            border-bottom: 1px solid var(--md-outline-variant);
            cursor: pointer;
            transition: background var(--transition-fast);
        }}
        .activity-item:last-child {{ border-bottom: none; }}
        .activity-item:hover {{ background: var(--md-surface-variant); }}
        .activity-item.expanded {{ background: var(--md-surface-variant); }}
        .activity-header {{
            display: flex;
            align-items: center;
            padding: 10px 0;
        }}
        .activity-date {{ width: 60px; font-size: 12px; color: var(--md-on-surface-variant); }}
        .activity-name {{ flex: 1; font-weight: 500; }}
        .activity-meta {{ font-size: 12px; color: var(--md-on-surface-variant); }}
        .activity-type {{
            font-size: 10px;
            padding: 2px 8px;
            border-radius: var(--radius-full);
            background: var(--md-surface-variant);
            margin-left: 8px;
        }}
        .activity-expand-icon {{
            margin-left: 8px;
            color: var(--md-on-surface-variant);
            transition: transform var(--transition-fast);
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
            background: var(--md-surface);
            border-radius: var(--radius-sm);
            border: 1px solid var(--md-outline-variant);
            display: flex;
            justify-content: space-between;
        }}
    </style>
    '''

    return wrap_page(content, "Dashboard", "/dashboard")


def _generate_calendar_heatmap(activity_by_date, min_date):
    """Generate GitHub-style calendar heatmap for the past year with click interaction."""
    today = date.today()
    start_date = today - timedelta(days=365)
    start_date = start_date - timedelta(days=(start_date.weekday() + 1) % 7)

    weeks_html = []
    current_date = start_date
    month_labels = []
    last_month = None
    week_idx = 0
    activity_data = {}

    while current_date <= today:
        week_days = []
        for day in range(7):
            if current_date <= today:
                activities = activity_by_date.get(current_date, [])
                count = len(activities)
                level = ""
                if count == 1:
                    level = "l1"
                elif count == 2:
                    level = "l2"
                elif count >= 3:
                    level = "l3"

                date_str = current_date.strftime('%Y-%m-%d')
                title = f"{current_date.strftime('%b %d, %Y')}: {count} workout{'s' if count != 1 else ''}"

                css_classes = ["calendar-day"]
                if count > 0:
                    css_classes.append(level)
                    css_classes.append("has-activity")
                    activity_data[date_str] = []
                    for a in activities:
                        workout_info = {
                            "name": a.activity_name or a.activity_type or "Workout",
                            "type": a.activity_type or "other",
                            "duration": a.duration_minutes or 0,
                            "source": a.source or "unknown",
                            "exercises": []
                        }
                        if a.activity_data:
                            try:
                                data = json.loads(a.activity_data) if isinstance(a.activity_data, str) else a.activity_data
                                if "exercises" in data:
                                    for ex in data["exercises"][:8]:
                                        ex_info = {
                                            "name": ex.get("exercise_name", ex.get("title", ex.get("name", "Exercise"))),
                                            "sets": len(ex.get("sets", [])) if "sets" in ex else ex.get("sets", 0)
                                        }
                                        workout_info["exercises"].append(ex_info)
                                elif "laps" in data and data["laps"]:
                                    workout_info["swim_data"] = {
                                        "distance": data.get("distance_meters"),
                                        "pace": data.get("avg_pace_per_100y"),
                                        "calories": data.get("calories"),
                                        "avg_hr": data.get("avg_heart_rate"),
                                        "max_hr": data.get("max_heart_rate"),
                                    }
                            except (json.JSONDecodeError, TypeError):
                                pass
                        activity_data[date_str].append(workout_info)

                week_days.append(f'<div class="{" ".join(css_classes)}" data-date="{date_str}" title="{title}"></div>')

                if current_date.month != last_month:
                    month_labels.append((week_idx, current_date.strftime('%b')))
                    last_month = current_date.month
            else:
                week_days.append('<div class="calendar-day" style="visibility:hidden;"></div>')
            current_date += timedelta(days=1)

        weeks_html.append(f'<div class="calendar-week">{"".join(week_days)}</div>')
        week_idx += 1

    # Build month labels - only show label at first week of each month
    month_label_html = '<div class="calendar-month-labels">'
    label_positions = {pos: label for pos, label in month_labels}
    for i in range(len(weeks_html)):
        if i in label_positions:
            month_label_html += f'<span>{label_positions[i]}</span>'
        else:
            month_label_html += '<span></span>'
    month_label_html += '</div>'

    activity_json = json.dumps(activity_data)

    js_code = f"""
    <script>
    const activityData = {activity_json};
    document.querySelectorAll('.calendar-day.has-activity').forEach(day => {{
        day.addEventListener('click', function() {{
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
                if (workout.duration) html += '<span>⏱️ ' + workout.duration + ' min</span>';
                html += '<span>📍 ' + workout.source + '</span>';
                html += '</div>';
                if (workout.swim_data) {{
                    html += '<div style="margin-top: 8px; padding: 8px; background: rgba(25, 118, 210, 0.08); border-radius: 8px; font-size: 13px;">';
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
                        html += '<span>' + ex.name + '</span>';
                        if (ex.sets) html += '<span style="color: var(--md-on-surface-variant);">' + ex.sets + ' sets</span>';
                        html += '</div>';
                    }});
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

    # Day labels on the left - all 7 days aligned 1:1 with rows
    day_labels_html = '''
        <div class="calendar-day-labels">
            <span>Sun</span>
            <span>Mon</span>
            <span>Tue</span>
            <span>Wed</span>
            <span>Thu</span>
            <span>Fri</span>
            <span>Sat</span>
        </div>
    '''

    return f"""
    <div class="calendar">
        {month_label_html}
        <div class="calendar-wrapper">
            {day_labels_html}
            <div class="calendar-grid">{"".join(weeks_html)}</div>
        </div>
        <div class="calendar-legend">
            <span>0</span>
            <div class="calendar-day"></div>
            <span>1</span>
            <div class="calendar-day l1"></div>
            <span>2</span>
            <div class="calendar-day l2"></div>
            <span>3</span>
            <div class="calendar-day l3"></div>
        </div>
    </div>
    {js_code}
    """


def _generate_goals_section(goals, activities, weekly_hours):
    """Generate goals progress cards using Material Design components."""
    html = ""

    if "weekly_volume" in goals:
        target = goals["weekly_volume"].get("target", 4)
        recent_weeks = weekly_hours[:4]
        avg_hours = sum(h for _, h in recent_weeks) / len(recent_weeks) if recent_weeks else 0
        html += get_progress_card("Weekly Training Volume", round(avg_hours, 1), target, "h")

    if "body_fat" in goals:
        target = goals["body_fat"].get("target", 14)
        current = goals["body_fat"].get("current") or 0
        html += get_progress_card("Body Fat %", current, target, "%")

    if "vo2_max" in goals:
        target = goals["vo2_max"].get("target", 55)
        current = goals["vo2_max"].get("current") or 0
        html += get_progress_card("VO2 Max", current, target, " ml/kg/min")

    if "explosive_strength" in goals:
        metrics = goals["explosive_strength"].get("metrics", {})
        for name, data in metrics.items():
            current = data.get("current", 0) or 0
            target = data.get("target", 0) or 0
            unit = data.get("unit", "")
            html += get_progress_card(name.replace('_', ' ').title(), current, target, f" {unit}")

    return html if html else '<p class="md-body-medium text-secondary">No goals configured</p>'


def _generate_weekly_volume_chart(weekly_hours, target):
    """Generate weekly volume bar chart with target line."""
    if not weekly_hours:
        return '<p class="md-body-medium text-secondary">No data available</p>'

    max_hours = max(max(h for _, h in weekly_hours), target) or 1

    bars = []
    for week_start, hours in reversed(weekly_hours):
        height_pct = (hours / max_hours) * 100
        color = "var(--md-success)" if hours >= target else "var(--md-primary)"
        label = week_start.strftime("%m/%d")
        bars.append(f'''
            <div class="bar" style="height: {height_pct}%; background: {color};" title="{hours:.1f}h">
                <span class="bar-label">{label}</span>
            </div>
        ''')

    target_pct = (target / max_hours) * 100

    return f"""
    <div style="position: relative; padding-bottom: 24px;">
        <div style="position: absolute; left: 0; right: 0; bottom: calc({target_pct}% + 24px); border-top: 2px dashed var(--md-warning); z-index: 1;">
            <span style="position: absolute; right: 0; top: -16px; font-size: 10px; color: var(--md-warning);">Target: {target}h</span>
        </div>
        <div class="bar-chart">{"".join(bars)}</div>
    </div>
    """


def _generate_monthly_chart(monthly_counts, monthly_minutes):
    """Generate monthly activity bar chart."""
    months = sorted(monthly_counts.keys())[-12:]
    if not months:
        return '<p class="md-body-medium text-secondary">No data available</p>'

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

    return f'<div class="bar-chart" style="padding-bottom: 24px;">{"".join(bars)}</div>'


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
        return '<p class="md-body-medium text-secondary">No data available</p>'

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
        return '<p class="md-body-medium text-secondary">No recent activities</p>'

    items = []
    for idx, a in enumerate(activities):
        date_str = a.activity_date.strftime("%b %d")
        duration = f"{a.duration_minutes}min" if a.duration_minutes else ""

        exercises_html = ""
        has_exercises = False
        if a.activity_data:
            try:
                data = json.loads(a.activity_data) if isinstance(a.activity_data, str) else a.activity_data
                if "exercises" in data and data["exercises"]:
                    has_exercises = True
                    exercise_items = []
                    for ex in data["exercises"]:
                        ex_name = ex.get("exercise_name", ex.get("title", ex.get("name", "Exercise")))
                        ex_sets = len(ex.get("sets", [])) if "sets" in ex else ex.get("sets", 0)
                        sets_text = f"{ex_sets} sets" if ex_sets else ""
                        exercise_items.append(f'''
                            <div class="activity-exercise-item">
                                <span>{ex_name}</span>
                                <span style="color: var(--md-on-surface-variant);">{sets_text}</span>
                            </div>
                        ''')
                    exercises_html = f'<div class="activity-exercise-list">{"".join(exercise_items)}</div>'
                elif "laps" in data and data["laps"]:
                    has_exercises = True
                    distance_yards = int(data.get("distance_meters", 0) * 1.09361)
                    pace = data.get("avg_pace_per_100y", "?")
                    exercises_html = f'''
                        <div style="background: rgba(25, 118, 210, 0.08); border-radius: 8px; padding: 12px; font-size: 13px;">
                            <div>🏊 {distance_yards} yards · {pace}/100y avg pace</div>
                        </div>
                    '''
            except (json.JSONDecodeError, TypeError):
                pass

        expand_icon = '<span class="activity-expand-icon">▼</span>' if has_exercises else ''
        click_handler = 'onclick="this.classList.toggle(\'expanded\')"' if has_exercises else ''

        items.append(f'''
            <div class="activity-item" data-idx="{idx}" {click_handler}>
                <div class="activity-header">
                    <span class="activity-date">{date_str}</span>
                    <span class="activity-name">{a.activity_name or a.activity_type}</span>
                    <span class="activity-meta">{duration}</span>
                    <span class="activity-type">{a.source}</span>
                    {expand_icon}
                </div>
                <div class="activity-details-expand">{exercises_html}</div>
            </div>
        ''')

    return f'<div class="activity-list">{"".join(items)}</div>'


def _empty_dashboard_html(athlete_name):
    """Return empty dashboard HTML using design system."""
    content = '''
    <header class="mb-6">
        <h1 class="md-headline-large mb-2">Training Dashboard</h1>
        <p class="md-body-large text-secondary">''' + athlete_name + '''</p>
    </header>

    <div class="md-card">
        <div class="md-card-content" style="text-align: center; padding: 48px;">
            <div style="font-size: 48px; margin-bottom: 16px;">📊</div>
            <h2 class="md-title-large mb-4">No Data Yet</h2>
            <p class="md-body-medium text-secondary">Sync your Garmin and Hevy data to see your dashboard.</p>
        </div>
    </div>
    '''
    return wrap_page(content, "Dashboard", "/dashboard")
