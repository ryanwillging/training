"""Training API - Vercel serverless function with PostgreSQL support."""

from http.server import BaseHTTPRequestHandler
import json
import os
from urllib.parse import urlparse, parse_qs
from datetime import date, datetime, timedelta

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
        return f"""<!DOCTYPE html>
<html><head><title>{title}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:600px;margin:40px auto;padding:20px;}}
.notice{{background:#fef3c7;padding:20px;border-radius:8px;border-left:4px solid #d97706;}}</style></head>
<body><h1>{title}</h1>
<div class="notice"><strong>Database Not Configured</strong>
<p>Set DATABASE_URL environment variable to enable this feature.</p></div></body></html>"""

    def _generate_metrics_form(self, db):
        """Generate metrics input form."""
        from database.models import ProgressMetric, Athlete

        athlete = db.query(Athlete).first()
        goals = json.loads(athlete.goals) if athlete and athlete.goals else {}

        # Get recent metrics
        recent = db.query(ProgressMetric).order_by(
            ProgressMetric.metric_date.desc()
        ).limit(20).all()

        recent_html = ""
        if recent:
            recent_html = "<h3>Recent Measurements</h3><table style='width:100%;border-collapse:collapse;'>"
            recent_html += "<tr style='border-bottom:2px solid #333;'><th style='text-align:left;padding:8px;'>Date</th><th style='text-align:left;padding:8px;'>Metric</th><th style='text-align:right;padding:8px;'>Value</th></tr>"
            for m in recent:
                recent_html += f"<tr style='border-bottom:1px solid #eee;'><td style='padding:8px;'>{m.metric_date}</td><td style='padding:8px;'>{m.metric_type}</td><td style='text-align:right;padding:8px;'>{m.value_numeric}</td></tr>"
            recent_html += "</table>"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Record Metrics</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #fafafa;
        }}
        h1 {{ margin-bottom: 8px; }}
        .subtitle {{ color: #666; margin-bottom: 24px; }}
        .nav {{ margin-bottom: 20px; }}
        .nav a {{ color: #2563eb; text-decoration: none; margin-right: 16px; }}
        .nav a:hover {{ text-decoration: underline; }}
        .card {{
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            border: 1px solid #e5e5e5;
        }}
        .card h2 {{ margin-top: 0; font-size: 18px; margin-bottom: 16px; }}
        .form-group {{ margin-bottom: 16px; }}
        label {{ display: block; font-weight: 500; margin-bottom: 4px; font-size: 14px; }}
        .hint {{ font-size: 12px; color: #666; margin-top: 2px; }}
        input[type="text"], input[type="number"], input[type="date"], select, textarea {{
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            font-size: 16px;
        }}
        input:focus, select:focus, textarea:focus {{
            outline: none;
            border-color: #2563eb;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
        @media (max-width: 600px) {{ .grid {{ grid-template-columns: 1fr; }} }}
        button {{
            background: #2563eb;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            width: 100%;
        }}
        button:hover {{ background: #1d4ed8; }}
        .success {{
            background: #d1fae5;
            border: 1px solid #059669;
            color: #065f46;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        table {{ margin-top: 16px; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="nav">
        <a href="/dashboard">← Dashboard</a>
        <a href="/api/metrics/history">View All Metrics (JSON)</a>
    </div>

    <h1>Record Metrics</h1>
    <p class="subtitle">Track your progress by recording baseline measurements</p>

    <form action="/api/metrics/save" method="POST">
        <div class="card">
            <h2>📅 Measurement Date</h2>
            <div class="form-group">
                <label for="date">Date</label>
                <input type="date" id="date" name="date" value="{date.today()}" required>
            </div>
        </div>

        <div class="card">
            <h2>⚖️ Body Composition</h2>
            <div class="grid">
                <div class="form-group">
                    <label for="weight">Weight (lbs)</label>
                    <input type="number" id="weight" name="weight" step="0.1" placeholder="e.g., 175.5">
                </div>
                <div class="form-group">
                    <label for="body_fat">Body Fat (%)</label>
                    <input type="number" id="body_fat" name="body_fat" step="0.1" placeholder="e.g., 18.5">
                    <div class="hint">Target: {goals.get('body_fat', {}).get('target', 14)}%</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>❤️ Cardiovascular</h2>
            <div class="grid">
                <div class="form-group">
                    <label for="vo2_max">VO2 Max (ml/kg/min)</label>
                    <input type="number" id="vo2_max" name="vo2_max" step="0.1" placeholder="e.g., 45">
                    <div class="hint">Target: {goals.get('vo2_max', {}).get('target', 55)}</div>
                </div>
                <div class="form-group">
                    <label for="resting_hr">Resting Heart Rate (bpm)</label>
                    <input type="number" id="resting_hr" name="resting_hr" placeholder="e.g., 58">
                </div>
            </div>
        </div>

        <div class="card">
            <h2>💪 Strength & Power</h2>
            <div class="grid">
                <div class="form-group">
                    <label for="broad_jump">Broad Jump (inches)</label>
                    <input type="number" id="broad_jump" name="broad_jump" step="0.5" placeholder="e.g., 102">
                    <div class="hint">Target: {goals.get('explosive_strength', {}).get('metrics', {}).get('broad_jump', {}).get('target', 108)}"</div>
                </div>
                <div class="form-group">
                    <label for="box_jump">Box Jump (inches)</label>
                    <input type="number" id="box_jump" name="box_jump" step="0.5" placeholder="e.g., 32">
                    <div class="hint">Target: {goals.get('explosive_strength', {}).get('metrics', {}).get('box_jump', {}).get('target', 36)}"</div>
                </div>
                <div class="form-group">
                    <label for="dead_hang">Dead Hang (seconds)</label>
                    <input type="number" id="dead_hang" name="dead_hang" placeholder="e.g., 70">
                </div>
                <div class="form-group">
                    <label for="pull_ups">Max Pull-ups (reps)</label>
                    <input type="number" id="pull_ups" name="pull_ups" placeholder="e.g., 12">
                </div>
            </div>
        </div>

        <div class="card">
            <h2>📝 Notes</h2>
            <div class="form-group">
                <label for="method">Measurement Method</label>
                <select id="method" name="method">
                    <option value="">Select method...</option>
                    <option value="inbody_scale">InBody Scale</option>
                    <option value="garmin_watch">Garmin Watch</option>
                    <option value="manual">Manual Measurement</option>
                    <option value="dexa">DEXA Scan</option>
                    <option value="caliper">Caliper</option>
                </select>
            </div>
            <div class="form-group">
                <label for="notes">Additional Notes</label>
                <textarea id="notes" name="notes" rows="3" placeholder="Any additional context..."></textarea>
            </div>
        </div>

        <button type="submit">💾 Save Measurements</button>
    </form>

    <div class="card" style="margin-top: 24px;">
        {recent_html}
    </div>
</body>
</html>"""

    def _generate_daily_report(self, db, report_date):
        """Generate daily training report."""
        from database.models import CompletedActivity, Athlete

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
            today_html = "<ul>"
            for a in today_activities:
                today_html += f"<li><strong>{a.activity_name or a.activity_type}</strong> - {a.duration_minutes or '?'} min</li>"
            today_html += "</ul>"
        else:
            today_html = "<p style='color:#666;'>Rest day</p>"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Daily Report - {report_date}</title>
    <style>
        body {{ font-family: Georgia, serif; max-width: 720px; margin: 0 auto; padding: 24px; }}
        h1 {{ font-size: 24px; font-weight: 400; }}
        .subtitle {{ color: #666; font-size: 14px; margin-bottom: 24px; }}
        h2 {{ font-size: 16px; border-bottom: 1px solid #eee; padding-bottom: 8px; }}
        .metrics {{ display: flex; gap: 32px; margin: 16px 0; }}
        .metric-value {{ font-size: 32px; font-weight: 300; }}
        .metric-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
        .nav {{ margin-bottom: 16px; }}
        .nav a {{ color: #2563eb; }}
    </style>
</head>
<body>
    <div class="nav"><a href="/dashboard">← Dashboard</a></div>
    <h1>Training Report</h1>
    <p class="subtitle">{athlete_name} | {report_date.strftime('%A, %B %d, %Y')}</p>

    <h2>Today</h2>
    {today_html}

    <h2>Week at a Glance</h2>
    <div class="metrics">
        <div><div class="metric-value">{total_workouts}</div><div class="metric-label">Workouts</div></div>
        <div><div class="metric-value">{total_minutes}</div><div class="metric-label">Minutes</div></div>
    </div>
</body>
</html>"""

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
        """Generate weekly training summary report."""
        from database.models import CompletedActivity, Athlete

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

        # Build activity list HTML
        activity_rows = ""
        for a in activities:
            activity_rows += f"""<tr>
                <td style="padding:8px;border-bottom:1px solid #eee;">{a.activity_date.strftime('%a %m/%d')}</td>
                <td style="padding:8px;border-bottom:1px solid #eee;">{a.activity_name or a.activity_type}</td>
                <td style="padding:8px;border-bottom:1px solid #eee;text-align:right;">{a.duration_minutes or '-'} min</td>
            </tr>"""

        if not activity_rows:
            activity_rows = "<tr><td colspan='3' style='padding:16px;color:#666;'>No activities recorded this week</td></tr>"

        # Week over week comparison
        workout_delta = total_workouts - prev_workouts
        minute_delta = total_minutes - prev_minutes
        workout_arrow = "↑" if workout_delta > 0 else "↓" if workout_delta < 0 else "→"
        minute_arrow = "↑" if minute_delta > 0 else "↓" if minute_delta < 0 else "→"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Weekly Report - {week_start} to {week_end}</title>
    <style>
        body {{ font-family: Georgia, serif; max-width: 720px; margin: 0 auto; padding: 24px; }}
        h1 {{ font-size: 24px; font-weight: 400; }}
        .subtitle {{ color: #666; font-size: 14px; margin-bottom: 24px; }}
        h2 {{ font-size: 16px; border-bottom: 1px solid #eee; padding-bottom: 8px; margin-top: 32px; }}
        .metrics {{ display: flex; gap: 48px; margin: 16px 0; }}
        .metric {{ }}
        .metric-value {{ font-size: 36px; font-weight: 300; }}
        .metric-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
        .metric-delta {{ font-size: 14px; color: #666; }}
        .delta-up {{ color: #059669; }}
        .delta-down {{ color: #dc2626; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
        th {{ text-align: left; padding: 8px; border-bottom: 2px solid #333; font-size: 12px; text-transform: uppercase; }}
        .nav {{ margin-bottom: 16px; }}
        .nav a {{ color: #2563eb; text-decoration: none; margin-right: 16px; }}
    </style>
</head>
<body>
    <div class="nav">
        <a href="/dashboard">← Dashboard</a>
        <a href="/api/reports/daily">Daily Report</a>
    </div>
    <h1>Weekly Training Summary</h1>
    <p class="subtitle">{athlete_name} | {week_start.strftime('%B %d')} - {week_end.strftime('%B %d, %Y')}</p>

    <h2>Week Totals</h2>
    <div class="metrics">
        <div class="metric">
            <div class="metric-value">{total_workouts}</div>
            <div class="metric-label">Workouts</div>
            <div class="metric-delta {'delta-up' if workout_delta > 0 else 'delta-down' if workout_delta < 0 else ''}">{workout_arrow} {abs(workout_delta)} vs last week</div>
        </div>
        <div class="metric">
            <div class="metric-value">{total_minutes}</div>
            <div class="metric-label">Minutes</div>
            <div class="metric-delta {'delta-up' if minute_delta > 0 else 'delta-down' if minute_delta < 0 else ''}">{minute_arrow} {abs(minute_delta)} vs last week</div>
        </div>
    </div>

    <h2>Activity Log</h2>
    <table>
        <thead>
            <tr>
                <th>Date</th>
                <th>Activity</th>
                <th style="text-align:right;">Duration</th>
            </tr>
        </thead>
        <tbody>
            {activity_rows}
        </tbody>
    </table>
</body>
</html>"""

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
