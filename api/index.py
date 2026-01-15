"""Training API - Vercel serverless function with PostgreSQL support."""

from http.server import BaseHTTPRequestHandler
import json
import os
from urllib.parse import urlparse, parse_qs
from datetime import date, datetime, timedelta

from api.design_system import wrap_page, get_base_css, get_nav_css

# Database imports
DB_AVAILABLE = False
try:
    from sqlalchemy import create_engine, func
    from sqlalchemy.orm import sessionmaker
    DB_AVAILABLE = True
except ImportError:
    pass


def get_db_session():
    """Get database session if configured."""
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        return None
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    engine = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    return Session()


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler."""

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # Root - redirect to dashboard
        if path == "/":
            return self.redirect("/dashboard")

        # Dashboard
        if path == "/dashboard":
            db = get_db_session()
            if db:
                try:
                    from api.dashboard import generate_dashboard_html
                    html = generate_dashboard_html(db)
                    db.close()
                    return self.send_html(html)
                except Exception as e:
                    db.close()
                    return self.send_json(500, {"error": str(e), "trace": str(type(e))})
            return self.send_html(self._no_db_html("Dashboard"))

        # Metrics input form
        if path == "/metrics" or path == "/api/metrics/input":
            db = get_db_session()
            if db:
                try:
                    html = self._generate_metrics_form(db)
                    db.close()
                    return self.send_html(html)
                except Exception as e:
                    db.close()
                    return self.send_json(500, {"error": str(e)})
            return self.send_html(self._no_db_html("Metrics"))

        # Health check
        if path == "/health":
            db = get_db_session()
            if db:
                try:
                    from database.models import CompletedActivity
                    count = db.query(CompletedActivity).count()
                    db.close()
                    return self.send_json(200, {"status": "healthy", "database": "connected", "activities": count})
                except Exception as e:
                    return self.send_json(200, {"status": "healthy", "database": "error", "error": str(e)})
            return self.send_json(200, {"status": "healthy", "database": "not_configured"})

        # Daily report
        if path == "/api/reports/daily":
            report_date_str = query.get("report_date", [str(date.today())])[0]
            try:
                report_date = datetime.strptime(report_date_str, "%Y-%m-%d").date()
            except:
                report_date = date.today()

            db = get_db_session()
            if db:
                try:
                    html = self._generate_daily_report(db, report_date)
                    db.close()
                    return self.send_html(html)
                except Exception as e:
                    db.close()
                    return self.send_json(500, {"error": str(e)})
            return self.send_html(self._no_db_html("Daily Report"))

        # Weekly report
        if path == "/api/reports/weekly":
            db = get_db_session()
            if db:
                try:
                    html = self._generate_weekly_report(db)
                    db.close()
                    return self.send_html(html)
                except Exception as e:
                    db.close()
                    return self.send_json(500, {"error": str(e)})
            return self.send_html(self._no_db_html("Weekly Report"))

        # Report list
        if path == "/api/reports/list":
            db = get_db_session()
            if db:
                try:
                    reports = self._get_report_list(db)
                    db.close()
                    return self.send_json(200, reports)
                except Exception as e:
                    db.close()
                    return self.send_json(500, {"error": str(e)})
            return self.send_json(200, {"reports": [], "count": 0, "error": "Database not configured"})

        # Stats API
        if path == "/api/stats":
            db = get_db_session()
            if db:
                try:
                    stats = self._get_stats(db)
                    db.close()
                    return self.send_json(200, stats)
                except Exception as e:
                    db.close()
                    return self.send_json(500, {"error": str(e)})
            return self.send_json(200, {"error": "Database not configured"})

        # Metrics history
        if path == "/api/metrics/history":
            db = get_db_session()
            if db:
                try:
                    from database.models import ProgressMetric
                    metrics = db.query(ProgressMetric).order_by(
                        ProgressMetric.metric_date.desc()
                    ).limit(50).all()
                    result = [
                        {
                            "date": str(m.metric_date),
                            "type": m.metric_type,
                            "value": m.value_numeric,
                            "method": m.measurement_method,
                            "notes": m.notes
                        }
                        for m in metrics
                    ]
                    db.close()
                    return self.send_json(200, {"metrics": result})
                except Exception as e:
                    db.close()
                    return self.send_json(500, {"error": str(e)})
            return self.send_json(200, {"error": "Database not configured"})

        # Cron status
        if path == "/api/cron/sync/status":
            return self.send_json(200, {
                "endpoint": "/api/cron/sync",
                "schedule": "0 5 * * * (5:00 UTC daily)",
                "status": "configured"
            })

        # Plan status
        if path == "/api/plan/status":
            db = get_db_session()
            if db:
                try:
                    status = self._get_plan_status(db)
                    db.close()
                    return self.send_json(200, status)
                except Exception as e:
                    db.close()
                    return self.send_json(500, {"error": str(e)})
            return self.send_json(200, {"error": "Database not configured"})

        # Plan week summary
        if path == "/api/plan/week":
            db = get_db_session()
            if db:
                try:
                    summary = self._get_week_summary(db)
                    db.close()
                    return self.send_json(200, summary)
                except Exception as e:
                    db.close()
                    return self.send_json(500, {"error": str(e)})
            return self.send_json(200, {"error": "Database not configured"})

        # Plan upcoming workouts
        if path == "/api/plan/upcoming":
            days = int(query.get("days", ["7"])[0])
            db = get_db_session()
            if db:
                try:
                    workouts = self._get_upcoming_workouts(db, days)
                    db.close()
                    return self.send_json(200, {"days_ahead": days, "workouts": workouts})
                except Exception as e:
                    db.close()
                    return self.send_json(500, {"error": str(e)})
            return self.send_json(200, {"error": "Database not configured"})

        return self.send_json(404, {"error": "Not found", "path": path})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Save metrics
        if path == "/api/metrics/save":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')

            # Parse form data or JSON
            try:
                if 'application/json' in self.headers.get('Content-Type', ''):
                    data = json.loads(body)
                else:
                    # Parse form data
                    data = {}
                    for pair in body.split('&'):
                        if '=' in pair:
                            key, value = pair.split('=', 1)
                            from urllib.parse import unquote_plus
                            data[unquote_plus(key)] = unquote_plus(value)
            except Exception as e:
                return self.send_json(400, {"error": f"Invalid data: {e}"})

            db = get_db_session()
            if db:
                try:
                    from database.models import ProgressMetric, Athlete
                    athlete = db.query(Athlete).first()

                    # Save each metric
                    saved = []
                    metric_date = datetime.strptime(data.get('date', str(date.today())), "%Y-%m-%d").date()

                    metric_fields = [
                        ('weight', 'weight_lbs', None),
                        ('body_fat', 'body_fat', None),
                        ('vo2_max', 'vo2_max', 'garmin_estimate'),
                        ('resting_hr', 'resting_hr', None),
                        ('broad_jump', 'broad_jump', None),
                        ('box_jump', 'box_jump', None),
                        ('dead_hang', 'dead_hang', None),
                        ('pull_ups', 'pull_ups', None),
                    ]

                    for form_field, metric_type, method in metric_fields:
                        value = data.get(form_field)
                        if value and value.strip():
                            try:
                                numeric_value = float(value)
                                metric = ProgressMetric(
                                    athlete_id=athlete.id if athlete else 1,
                                    metric_date=metric_date,
                                    metric_type=metric_type,
                                    value_numeric=numeric_value,
                                    measurement_method=method or data.get('method'),
                                    notes=data.get('notes')
                                )
                                db.add(metric)
                                saved.append(metric_type)
                            except ValueError:
                                pass

                    db.commit()
                    db.close()

                    # Redirect back to metrics page with success
                    self.send_response(302)
                    self.send_header('Location', '/metrics?saved=' + ','.join(saved))
                    self.end_headers()
                    return
                except Exception as e:
                    db.close()
                    return self.send_json(500, {"error": str(e)})
            return self.send_json(400, {"error": "Database not configured"})

        # Cron sync
        if path == "/api/cron/sync":
            auth = self.headers.get("Authorization", "")
            cron_secret = os.environ.get("CRON_SECRET", "")
            if cron_secret and not auth.endswith(cron_secret):
                return self.send_json(401, {"error": "Unauthorized"})
            return self.send_json(200, {"status": "success", "message": "Sync endpoint ready"})

        # Plan initialize
        if path == "/api/plan/initialize":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body)
            except:
                return self.send_json(400, {"error": "Invalid JSON"})

            start_date_str = data.get("start_date")
            if not start_date_str:
                return self.send_json(400, {"error": "start_date required"})

            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                if start_date.weekday() != 0:
                    return self.send_json(400, {
                        "error": f"Start date should be a Monday. {start_date_str} is a {start_date.strftime('%A')}"
                    })
            except ValueError as e:
                return self.send_json(400, {"error": f"Invalid date format: {e}"})

            db = get_db_session()
            if db:
                try:
                    result = self._initialize_plan(db, start_date)
                    db.close()
                    return self.send_json(200, result)
                except Exception as e:
                    db.close()
                    return self.send_json(500, {"error": str(e)})
            return self.send_json(400, {"error": "Database not configured"})

        return self.send_json(404, {"error": "Not found"})

    def send_json(self, status, data):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def send_html(self, html):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode())

    def redirect(self, location):
        self.send_response(302)
        self.send_header('Location', location)
        self.end_headers()

    def log_message(self, format, *args):
        pass

    def _no_db_html(self, title):
        content = f'''
        <header class="mb-6">
            <h1 class="md-headline-large">{title}</h1>
        </header>
        <div class="md-alert md-alert-warning">
            <div>
                <strong class="md-title-medium">Database Not Configured</strong>
                <p class="md-body-medium mt-2">Set DATABASE_URL environment variable to enable this feature.</p>
            </div>
        </div>
        '''
        return wrap_page(content, title, None)

    def _generate_metrics_form(self, db):
        """Generate metrics input form using Material Design."""
        from database.models import ProgressMetric, Athlete

        athlete = db.query(Athlete).first()
        goals = json.loads(athlete.goals) if athlete and athlete.goals else {}

        # Get recent metrics
        recent = db.query(ProgressMetric).order_by(
            ProgressMetric.metric_date.desc()
        ).limit(20).all()

        recent_rows = ""
        if recent:
            for m in recent:
                recent_rows += f'''
                <tr>
                    <td>{m.metric_date}</td>
                    <td>{m.metric_type.replace('_', ' ').title()}</td>
                    <td class="text-right">{m.value_numeric}</td>
                </tr>
                '''

        recent_html = f'''
        <div class="md-card mt-6">
            <div class="md-card-header">
                <h2 class="md-title-large">Recent Measurements</h2>
            </div>
            <div class="md-card-content">
                <div class="md-table-container">
                    <table class="md-table">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Metric</th>
                                <th class="text-right">Value</th>
                            </tr>
                        </thead>
                        <tbody>
                            {recent_rows if recent_rows else '<tr><td colspan="3" class="text-secondary">No measurements recorded yet</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        ''' if recent else ''

        content = f'''
        <header class="mb-6">
            <h1 class="md-headline-large mb-2">Record Metrics</h1>
            <p class="md-body-large text-secondary">Track your progress by recording baseline measurements</p>
        </header>

        <form action="/api/metrics/save" method="POST">
            <div class="md-card mb-4">
                <div class="md-card-header">
                    <h2 class="md-title-large">Measurement Date</h2>
                </div>
                <div class="md-card-content">
                    <div class="md-form-group">
                        <label class="md-label" for="date">Date</label>
                        <input class="md-input" type="date" id="date" name="date" value="{date.today()}" required>
                    </div>
                </div>
            </div>

            <div class="md-card mb-4">
                <div class="md-card-header">
                    <h2 class="md-title-large">Body Composition</h2>
                </div>
                <div class="md-card-content">
                    <div class="md-grid md-grid-cols-2">
                        <div class="md-form-group">
                            <label class="md-label" for="weight">Weight (lbs)</label>
                            <input class="md-input" type="number" id="weight" name="weight" step="0.1" placeholder="e.g., 175.5">
                        </div>
                        <div class="md-form-group">
                            <label class="md-label" for="body_fat">Body Fat (%)</label>
                            <input class="md-input" type="number" id="body_fat" name="body_fat" step="0.1" placeholder="e.g., 18.5">
                            <p class="md-hint">Target: {goals.get('body_fat', {}).get('target', 14)}%</p>
                        </div>
                    </div>
                </div>
            </div>

            <div class="md-card mb-4">
                <div class="md-card-header">
                    <h2 class="md-title-large">Cardiovascular</h2>
                </div>
                <div class="md-card-content">
                    <div class="md-grid md-grid-cols-2">
                        <div class="md-form-group">
                            <label class="md-label" for="vo2_max">VO2 Max (ml/kg/min)</label>
                            <input class="md-input" type="number" id="vo2_max" name="vo2_max" step="0.1" placeholder="e.g., 45">
                            <p class="md-hint">Target: {goals.get('vo2_max', {}).get('target', 55)}</p>
                        </div>
                        <div class="md-form-group">
                            <label class="md-label" for="resting_hr">Resting Heart Rate (bpm)</label>
                            <input class="md-input" type="number" id="resting_hr" name="resting_hr" placeholder="e.g., 58">
                        </div>
                    </div>
                </div>
            </div>

            <div class="md-card mb-4">
                <div class="md-card-header">
                    <h2 class="md-title-large">Strength & Power</h2>
                </div>
                <div class="md-card-content">
                    <div class="md-grid md-grid-cols-2">
                        <div class="md-form-group">
                            <label class="md-label" for="broad_jump">Broad Jump (inches)</label>
                            <input class="md-input" type="number" id="broad_jump" name="broad_jump" step="0.5" placeholder="e.g., 102">
                            <p class="md-hint">Target: {goals.get('explosive_strength', {}).get('metrics', {}).get('broad_jump', {}).get('target', 108)}"</p>
                        </div>
                        <div class="md-form-group">
                            <label class="md-label" for="box_jump">Box Jump (inches)</label>
                            <input class="md-input" type="number" id="box_jump" name="box_jump" step="0.5" placeholder="e.g., 32">
                            <p class="md-hint">Target: {goals.get('explosive_strength', {}).get('metrics', {}).get('box_jump', {}).get('target', 36)}"</p>
                        </div>
                        <div class="md-form-group">
                            <label class="md-label" for="dead_hang">Dead Hang (seconds)</label>
                            <input class="md-input" type="number" id="dead_hang" name="dead_hang" placeholder="e.g., 70">
                        </div>
                        <div class="md-form-group">
                            <label class="md-label" for="pull_ups">Max Pull-ups (reps)</label>
                            <input class="md-input" type="number" id="pull_ups" name="pull_ups" placeholder="e.g., 12">
                        </div>
                    </div>
                </div>
            </div>

            <div class="md-card mb-4">
                <div class="md-card-header">
                    <h2 class="md-title-large">Notes</h2>
                </div>
                <div class="md-card-content">
                    <div class="md-form-group">
                        <label class="md-label" for="method">Measurement Method</label>
                        <select class="md-select" id="method" name="method">
                            <option value="">Select method...</option>
                            <option value="inbody_scale">InBody Scale</option>
                            <option value="garmin_watch">Garmin Watch</option>
                            <option value="manual">Manual Measurement</option>
                            <option value="dexa">DEXA Scan</option>
                            <option value="caliper">Caliper</option>
                        </select>
                    </div>
                    <div class="md-form-group">
                        <label class="md-label" for="notes">Additional Notes</label>
                        <textarea class="md-textarea" id="notes" name="notes" rows="3" placeholder="Any additional context..."></textarea>
                    </div>
                </div>
            </div>

            <button type="submit" class="md-btn md-btn-filled w-full">Save Measurements</button>
        </form>

        {recent_html}
        '''
        return wrap_page(content, "Record Metrics", "/metrics")

    def _generate_daily_report(self, db, report_date):
        """Generate daily training report using Material Design."""
        from database.models import CompletedActivity, Athlete
        from api.design_system import get_stat_card

        athlete = db.query(Athlete).first()
        athlete_name = athlete.name if athlete else "Athlete"

        today_activities = db.query(CompletedActivity).filter(
            CompletedActivity.activity_date == report_date
        ).all()

        week_start = report_date - timedelta(days=report_date.weekday())
        week_activities = db.query(CompletedActivity).filter(
            CompletedActivity.activity_date >= week_start,
            CompletedActivity.activity_date <= report_date
        ).all()

        total_workouts = len(week_activities)
        total_minutes = sum(a.duration_minutes or 0 for a in week_activities)

        if today_activities:
            today_items = ""
            for a in today_activities:
                duration = f"{a.duration_minutes} min" if a.duration_minutes else ""
                today_items += f'''
                <div class="md-list-item">
                    <div class="md-list-item-content">
                        <div class="md-list-item-primary">{a.activity_name or a.activity_type}</div>
                        <div class="md-list-item-secondary">{a.source or 'Unknown source'}</div>
                    </div>
                    <span class="md-chip">{duration}</span>
                </div>
                '''
            today_html = f'<div class="md-list">{today_items}</div>'
        else:
            today_html = '<div class="md-alert md-alert-info"><p class="md-body-medium">Rest day - no activities recorded</p></div>'

        content = f'''
        <header class="mb-6">
            <h1 class="md-headline-large mb-2">Daily Training Report</h1>
            <p class="md-body-large text-secondary">{athlete_name} &middot; {report_date.strftime('%A, %B %d, %Y')}</p>
        </header>

        <div class="md-card mb-6">
            <div class="md-card-header">
                <h2 class="md-title-large">Today's Activity</h2>
            </div>
            <div class="md-card-content">
                {today_html}
            </div>
        </div>

        <div class="md-card mb-6">
            <div class="md-card-header">
                <h2 class="md-title-large">Week at a Glance</h2>
            </div>
            <div class="md-card-content">
                <div class="md-grid md-grid-cols-2">
                    {get_stat_card(str(total_workouts), "Workouts")}
                    {get_stat_card(f"{total_minutes}", "Minutes")}
                </div>
            </div>
        </div>
        '''
        return wrap_page(content, f"Daily Report - {report_date}", "/api/reports/daily")

    def _get_stats(self, db):
        """Get training statistics."""
        from database.models import CompletedActivity

        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        activities = db.query(CompletedActivity).filter(
            CompletedActivity.activity_date >= week_start
        ).all()

        recent = db.query(CompletedActivity).order_by(
            CompletedActivity.activity_date.desc()
        ).limit(7).all()

        return {
            "week": {
                "workouts": len(activities),
                "duration_minutes": sum(a.duration_minutes or 0 for a in activities),
                "week_start": str(week_start)
            },
            "recent": [
                {"date": str(a.activity_date), "name": a.activity_name, "type": a.activity_type, "duration": a.duration_minutes}
                for a in recent
            ]
        }

    def _generate_weekly_report(self, db):
        """Generate weekly training summary report using Material Design."""
        from database.models import CompletedActivity, Athlete
        from api.design_system import get_stat_card

        athlete = db.query(Athlete).first()
        athlete_name = athlete.name if athlete else "Athlete"

        today = date.today()
        # Week ends on Sunday
        days_until_sunday = (6 - today.weekday()) % 7
        week_end = today + timedelta(days=days_until_sunday)
        week_start = week_end - timedelta(days=6)

        # Current week activities
        activities = db.query(CompletedActivity).filter(
            CompletedActivity.activity_date >= week_start,
            CompletedActivity.activity_date <= week_end
        ).order_by(CompletedActivity.activity_date).all()

        # Previous week for comparison
        prev_week_start = week_start - timedelta(days=7)
        prev_week_end = week_start - timedelta(days=1)
        prev_activities = db.query(CompletedActivity).filter(
            CompletedActivity.activity_date >= prev_week_start,
            CompletedActivity.activity_date <= prev_week_end
        ).all()

        total_workouts = len(activities)
        total_minutes = sum(a.duration_minutes or 0 for a in activities)
        prev_workouts = len(prev_activities)
        prev_minutes = sum(a.duration_minutes or 0 for a in prev_activities)

        # Build activity table rows
        activity_rows = ""
        for a in activities:
            activity_rows += f'''
            <tr>
                <td>{a.activity_date.strftime('%a %m/%d')}</td>
                <td>{a.activity_name or a.activity_type}</td>
                <td class="text-right">{a.duration_minutes or '-'} min</td>
            </tr>
            '''

        if not activity_rows:
            activity_rows = '<tr><td colspan="3" class="text-secondary">No activities recorded this week</td></tr>'

        # Week over week comparison
        workout_delta = total_workouts - prev_workouts
        minute_delta = total_minutes - prev_minutes
        workout_change = f"+{workout_delta}" if workout_delta > 0 else str(workout_delta)
        minute_change = f"+{minute_delta}" if minute_delta > 0 else str(minute_delta)

        content = f'''
        <header class="mb-6">
            <h1 class="md-headline-large mb-2">Weekly Training Summary</h1>
            <p class="md-body-large text-secondary">{athlete_name} &middot; {week_start.strftime('%B %d')} - {week_end.strftime('%B %d, %Y')}</p>
        </header>

        <div class="md-card mb-6">
            <div class="md-card-header">
                <h2 class="md-title-large">Week Totals</h2>
            </div>
            <div class="md-card-content">
                <div class="md-grid md-grid-cols-2">
                    {get_stat_card(str(total_workouts), "Workouts", f"{workout_change} vs last week", workout_delta > 0 if workout_delta != 0 else None)}
                    {get_stat_card(str(total_minutes), "Minutes", f"{minute_change} vs last week", minute_delta > 0 if minute_delta != 0 else None)}
                </div>
            </div>
        </div>

        <div class="md-card mb-6">
            <div class="md-card-header">
                <h2 class="md-title-large">Activity Log</h2>
            </div>
            <div class="md-card-content">
                <div class="md-table-container">
                    <table class="md-table">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Activity</th>
                                <th class="text-right">Duration</th>
                            </tr>
                        </thead>
                        <tbody>
                            {activity_rows}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        '''
        return wrap_page(content, f"Weekly Report", "/api/reports/weekly")

    def _get_report_list(self, db):
        """Get list of available reports."""
        from database.models import CompletedActivity

        # Get dates with activities (potential report dates)
        activities = db.query(CompletedActivity.activity_date).distinct().order_by(
            CompletedActivity.activity_date.desc()
        ).limit(30).all()

        reports = []
        for (activity_date,) in activities:
            reports.append({
                "date": str(activity_date),
                "type": "daily",
                "url": f"/api/reports/daily?report_date={activity_date}"
            })

        return {
            "reports": reports,
            "count": len(reports),
            "weekly_url": "/api/reports/weekly"
        }

    def _get_plan_status(self, db):
        """Get training plan status."""
        from database.models import Athlete, ScheduledWorkout

        athlete = db.query(Athlete).first()
        if not athlete:
            return {"initialized": False, "error": "No athlete found"}

        goals_data = json.loads(athlete.goals) if athlete.goals else {}
        plan_info = goals_data.get("training_plan", {})
        start_date_str = plan_info.get("start_date")

        if not start_date_str:
            return {
                "initialized": False,
                "start_date": None,
                "current_week": None,
                "progress": {}
            }

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        days_elapsed = (date.today() - start_date).days
        current_week = min(max(1, (days_elapsed // 7) + 1), 24)

        # Get progress stats
        scheduled = db.query(ScheduledWorkout).filter(
            ScheduledWorkout.athlete_id == athlete.id
        ).all()

        completed = len([s for s in scheduled if s.status == "completed"])
        total = len(scheduled)

        return {
            "initialized": True,
            "start_date": start_date_str,
            "current_week": current_week,
            "is_test_week": current_week in [1, 12, 24],
            "progress": {
                "total_scheduled": total,
                "completed": completed,
                "adherence_rate": round((completed / total * 100) if total > 0 else 0, 1)
            }
        }

    def _get_week_summary(self, db, week_number=None):
        """Get summary for a specific week or current week."""
        from database.models import Athlete, ScheduledWorkout

        athlete = db.query(Athlete).first()
        if not athlete:
            return {"error": "No athlete found"}

        goals_data = json.loads(athlete.goals) if athlete.goals else {}
        plan_info = goals_data.get("training_plan", {})
        start_date_str = plan_info.get("start_date")

        if not start_date_str:
            return {"error": "Plan not initialized"}

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        if week_number is None:
            days_elapsed = (date.today() - start_date).days
            week_number = min(max(1, (days_elapsed // 7) + 1), 24)

        workouts = db.query(ScheduledWorkout).filter(
            ScheduledWorkout.athlete_id == athlete.id,
            ScheduledWorkout.week_number == week_number
        ).order_by(ScheduledWorkout.scheduled_date).all()

        return {
            "week": week_number,
            "is_test_week": week_number in [1, 12, 24],
            "workouts": [
                {
                    "type": w.workout_type,
                    "name": w.workout_name,
                    "date": str(w.scheduled_date) if w.scheduled_date else None,
                    "status": w.status,
                    "duration_minutes": w.duration_minutes
                }
                for w in workouts
            ],
            "completed": len([w for w in workouts if w.status == "completed"]),
            "total": len(workouts)
        }

    def _get_upcoming_workouts(self, db, days=7):
        """Get upcoming scheduled workouts."""
        from database.models import Athlete, ScheduledWorkout

        athlete = db.query(Athlete).first()
        if not athlete:
            return []

        today = date.today()
        end_date = today + timedelta(days=days)

        workouts = db.query(ScheduledWorkout).filter(
            ScheduledWorkout.athlete_id == athlete.id,
            ScheduledWorkout.scheduled_date >= today,
            ScheduledWorkout.scheduled_date <= end_date,
            ScheduledWorkout.status == "scheduled"
        ).order_by(ScheduledWorkout.scheduled_date).all()

        return [
            {
                "date": str(w.scheduled_date),
                "type": w.workout_type,
                "name": w.workout_name,
                "week": w.week_number,
                "is_test_week": w.is_test_week
            }
            for w in workouts
        ]

    def _initialize_plan(self, db, start_date):
        """Initialize the 24-week training plan."""
        from database.models import Athlete, ScheduledWorkout

        athlete = db.query(Athlete).first()
        if not athlete:
            return {"error": "No athlete found"}

        # Update athlete goals with plan info
        goals_data = json.loads(athlete.goals) if athlete.goals else {}
        goals_data["training_plan"] = {
            "name": "24-Week Performance Plan",
            "start_date": str(start_date),
            "total_weeks": 24,
            "test_weeks": [1, 12, 24],
            "initialized_at": str(date.today())
        }
        athlete.goals = json.dumps(goals_data)

        # Generate scheduled workouts for all 24 weeks
        workout_types = [
            ("swim_a", "Swim A", 45),
            ("lift_a", "Lift A (Lower)", 45),
            ("vo2", "VO2 Session", 40),
            ("swim_b", "Swim B", 45),
            ("lift_b", "Lift B (Upper)", 45)
        ]
        test_weeks = [1, 12, 24]
        total_scheduled = 0

        for week in range(1, 25):
            week_start = start_date + timedelta(weeks=week - 1)
            is_test = week in test_weeks

            for day_idx, (wtype, wname, duration) in enumerate(workout_types):
                workout_date = week_start + timedelta(days=day_idx)

                # On test weeks, Swim B becomes swim_test
                actual_type = wtype
                actual_name = wname
                if is_test and wtype == "swim_b":
                    actual_type = "swim_test"
                    actual_name = f"400 TT Test - Week {week}"
                else:
                    actual_name = f"{wname} - Week {week}"

                # Check if already exists
                existing = db.query(ScheduledWorkout).filter(
                    ScheduledWorkout.athlete_id == athlete.id,
                    ScheduledWorkout.scheduled_date == workout_date,
                    ScheduledWorkout.workout_type == actual_type
                ).first()

                if not existing:
                    scheduled = ScheduledWorkout(
                        athlete_id=athlete.id,
                        scheduled_date=workout_date,
                        workout_type=actual_type,
                        workout_name=actual_name,
                        week_number=week,
                        day_of_week=day_idx + 1,
                        duration_minutes=duration,
                        is_test_week=is_test,
                        status="scheduled"
                    )
                    db.add(scheduled)
                    total_scheduled += 1

        db.commit()

        return {
            "plan_name": "24-Week Performance Plan",
            "start_date": str(start_date),
            "total_weeks": 24,
            "total_workouts_scheduled": total_scheduled,
            "test_weeks": test_weeks,
            "status": "initialized"
        }
