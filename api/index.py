"""Training API - Vercel serverless function with PostgreSQL support."""

from http.server import BaseHTTPRequestHandler
import json
import os
from urllib.parse import urlparse, parse_qs
from datetime import date, datetime, timedelta

from api.design_system import (
    wrap_page,
    WORKOUT_STYLES, STATUS_COLORS, EVAL_TYPE_STYLES,
    SEVERITY_STYLES, ASSESSMENT_COLORS, PRIORITY_COLORS,
)
from api.timezone import get_eastern_today

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
            report_date_str = query.get("report_date", [str(get_eastern_today())])[0]
            try:
                report_date = datetime.strptime(report_date_str, "%Y-%m-%d").date()
            except:
                report_date = get_eastern_today()

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
            status_info = {
                "endpoint": "/api/cron/sync",
                "schedule": "0 5 * * * (5:00 UTC daily)",
                "status": "configured",
                "last_run": None
            }
            # Try to get last run from database
            db = get_db_session()
            if db:
                try:
                    from database.models import CronLog
                    last_run = db.query(CronLog).order_by(CronLog.run_date.desc()).first()
                    if last_run:
                        status_info["last_run"] = {
                            "date": last_run.run_date.isoformat() if last_run.run_date else None,
                            "status": last_run.status,
                            "duration_seconds": last_run.duration_seconds,
                            "garmin_activities": last_run.garmin_activities_imported,
                            "garmin_wellness": last_run.garmin_wellness_imported,
                            "hevy": last_run.hevy_imported,
                            "errors": json.loads(last_run.errors_json) if last_run.errors_json else []
                        }
                    db.close()
                except Exception as e:
                    status_info["last_run_error"] = str(e)
                    try:
                        db.close()
                    except:
                        pass
            return self.send_json(200, status_info)

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

        # Upcoming workouts page
        if path == "/upcoming" or path == "/api/plan/upcoming-page":
            db = get_db_session()
            if db:
                try:
                    html = self._generate_upcoming_page(db)
                    db.close()
                    return self.send_html(html)
                except Exception as e:
                    db.close()
                    return self.send_json(500, {"error": str(e)})
            return self.send_html(self._no_db_html("Upcoming Workouts"))

        # Reviews page
        if path == "/reviews" or path == "/api/plan/reviews-page":
            db = get_db_session()
            if db:
                try:
                    html = self._generate_reviews_page(db)
                    db.close()
                    return self.send_html(html)
                except Exception as e:
                    db.close()
                    return self.send_json(500, {"error": str(e)})
            return self.send_html(self._no_db_html("Plan Reviews"))

        # Evaluation context API
        if path == "/api/plan/evaluation-context":
            db = get_db_session()
            if db:
                try:
                    context = self._get_evaluation_context(db)
                    db.close()
                    return self.send_json(200, context)
                except Exception as e:
                    db.close()
                    return self.send_json(500, {"error": str(e)})
            return self.send_json(400, {"error": "Database not configured"})

        # Latest review API
        if path == "/api/plan/reviews/latest":
            db = get_db_session()
            if db:
                try:
                    review = self._get_latest_review(db)
                    db.close()
                    return self.send_json(200, review)
                except Exception as e:
                    db.close()
                    return self.send_json(500, {"error": str(e)})
            return self.send_json(400, {"error": "Database not configured"})

        # Cron sync via GET (Vercel Cron uses GET requests)
        if path == "/api/cron/sync":
            # Check for Vercel Cron header OR Authorization Bearer token
            vercel_cron = self.headers.get("x-vercel-cron")
            auth = self.headers.get("Authorization", "")
            cron_secret = os.environ.get("CRON_SECRET", "")

            # Allow if: Vercel cron header present, OR valid Bearer token, OR no secret configured
            is_authorized = (
                vercel_cron or
                (cron_secret and auth.endswith(cron_secret)) or
                not cron_secret
            )

            if not is_authorized:
                return self.send_json(401, {"error": "Unauthorized"})

            db = get_db_session()
            if not db:
                return self.send_json(400, {"error": "Database not configured"})

            try:
                import time as time_module
                start_time = time_module.time()
                results = self._run_sync(db)
                duration = time_module.time() - start_time

                # Log the cron run
                self._log_cron_run(db, results, duration)

                db.close()
                return self.send_json(200, results)
            except Exception as e:
                db.close()
                return self.send_json(500, {"error": str(e)})

        return self.send_json(404, {"error": "Not found", "path": path})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Dashboard sync (no auth required)
        if path == "/api/sync":
            db = get_db_session()
            if not db:
                return self.send_json(400, {"error": "Database not configured"})
            try:
                results = self._run_sync(db)
                db.close()
                return self.send_json(200, results)
            except Exception as e:
                db.close()
                return self.send_json(500, {"error": str(e)})

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
                    metric_date = datetime.strptime(data.get('date', str(get_eastern_today())), "%Y-%m-%d").date()

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

        # Cron sync - actually runs the sync
        if path == "/api/cron/sync":
            # Check for Vercel Cron header OR Authorization Bearer token
            vercel_cron = self.headers.get("x-vercel-cron")
            auth = self.headers.get("Authorization", "")
            cron_secret = os.environ.get("CRON_SECRET", "")

            # Allow if: Vercel cron header present, OR valid Bearer token, OR no secret configured
            is_authorized = (
                vercel_cron or
                (cron_secret and auth.endswith(cron_secret)) or
                not cron_secret
            )

            if not is_authorized:
                return self.send_json(401, {"error": "Unauthorized"})

            db = get_db_session()
            if not db:
                return self.send_json(400, {"error": "Database not configured"})

            try:
                import time as time_module
                start_time = time_module.time()
                results = self._run_sync(db)
                duration = time_module.time() - start_time

                # Log the cron run
                self._log_cron_run(db, results, duration)

                db.close()
                return self.send_json(200, results)
            except Exception as e:
                db.close()
                return self.send_json(500, {"error": str(e)})

        # Individual modification action (approve/reject single modification)
        # Path: /api/plan/reviews/{id}/modifications/{index}/action
        if "/modifications/" in path and path.endswith("/action"):
            parts = path.split("/")
            try:
                # /api/plan/reviews/{id}/modifications/{index}/action
                review_id = int(parts[4])
                mod_index = int(parts[6])
            except (IndexError, ValueError):
                return self.send_json(400, {"error": "Invalid review ID or modification index"})

            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body)
            except:
                return self.send_json(400, {"error": "Invalid JSON"})

            action = data.get("action")
            if action not in ("approve", "reject"):
                return self.send_json(400, {"error": "Action must be 'approve' or 'reject'"})

            db = get_db_session()
            if db:
                try:
                    result = self._action_single_modification(db, review_id, mod_index, action)
                    db.close()
                    return self.send_json(200, result)
                except ValueError as e:
                    db.close()
                    return self.send_json(400, {"error": str(e)})
                except Exception as e:
                    db.close()
                    return self.send_json(500, {"error": str(e)})
            return self.send_json(400, {"error": "Database not configured"})

        # Review action (approve/reject all pending modifications)
        if path.startswith("/api/plan/reviews/") and path.endswith("/action"):
            # Extract review_id from path
            parts = path.split("/")
            try:
                review_id = int(parts[4])  # /api/plan/reviews/{id}/action
            except (IndexError, ValueError):
                return self.send_json(400, {"error": "Invalid review ID"})

            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body)
            except:
                return self.send_json(400, {"error": "Invalid JSON"})

            action = data.get("action")
            notes = data.get("notes")

            if action not in ("approve", "reject"):
                return self.send_json(400, {"error": "Action must be 'approve' or 'reject'"})

            db = get_db_session()
            if db:
                try:
                    result = self._action_review(db, review_id, action, notes)
                    db.close()
                    return self.send_json(200, result)
                except Exception as e:
                    db.close()
                    return self.send_json(500, {"error": str(e)})
            return self.send_json(400, {"error": "Database not configured"})

        # Run evaluation with context
        if path == "/api/plan/evaluate-with-context":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body)
            except:
                data = {}

            user_context = data.get("user_context")

            db = get_db_session()
            if db:
                try:
                    result = self._run_evaluation(db, user_context)
                    db.close()
                    return self.send_json(200, result)
                except Exception as e:
                    db.close()
                    return self.send_json(500, {"error": str(e)})
            return self.send_json(400, {"error": "Database not configured"})

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

    def _log_cron_run(self, db, results, duration):
        """Log cron run to database for tracking."""
        try:
            from database.models import CronLog
            from api.timezone import get_eastern_now

            # Determine status
            errors = results.get("errors", [])
            if not errors:
                status = "success"
            elif results.get("status") == "completed_with_errors":
                status = "partial"
            else:
                status = "failed"

            log = CronLog(
                run_date=get_eastern_now(),
                job_type="sync",
                status=status,
                garmin_activities_imported=results.get("garmin_activities", {}).get("imported", 0) if isinstance(results.get("garmin_activities"), dict) else 0,
                garmin_wellness_imported=results.get("garmin_wellness", {}).get("imported", 0) if isinstance(results.get("garmin_wellness"), dict) else 0,
                hevy_imported=results.get("hevy", {}).get("imported", 0) if isinstance(results.get("hevy"), dict) else 0,
                errors_json=json.dumps(errors) if errors else None,
                results_json=json.dumps(results, default=str),
                duration_seconds=duration
            )
            db.add(log)
            db.commit()
        except Exception as e:
            # Don't fail the sync if logging fails
            print(f"Failed to log cron run: {e}")
            db.rollback()

    def _run_sync(self, db):
        """Run data sync from Garmin and Hevy."""
        athlete_id = int(os.environ.get("ATHLETE_ID", "1"))
        days = 7  # Sync last 7 days

        results = {
            "date": str(get_eastern_today()),
            "athlete_id": athlete_id,
            "garmin_activities": None,
            "garmin_wellness": None,
            "hevy": None,
            "errors": []
        }

        # Ensure all tables exist (creates daily_wellness if missing)
        try:
            from database.base import Base, engine
            Base.metadata.create_all(bind=engine)
            results["tables"] = "created/verified"
        except Exception as e:
            results["errors"].append(f"Table creation: {str(e)}")

        # Sync Garmin activities
        try:
            from integrations.garmin.activity_importer import GarminActivityImporter
            garmin = GarminActivityImporter(db, athlete_id)
            imported, skipped, errors = garmin.import_recent_activities(days)
            results["garmin_activities"] = {"imported": imported, "skipped": skipped}
            if errors:
                results["errors"].extend(errors)
        except Exception as e:
            results["garmin_activities"] = {"error": str(e)}
            results["errors"].append(f"Garmin activities: {str(e)}")

        # Sync Garmin wellness data
        try:
            from integrations.garmin.wellness_importer import GarminWellnessImporter
            wellness = GarminWellnessImporter(db, athlete_id)
            imported, updated, errors = wellness.import_recent_wellness(days)
            results["garmin_wellness"] = {"imported": imported, "updated": updated}
            if errors:
                results["errors"].extend(errors)
        except Exception as e:
            results["garmin_wellness"] = {"error": str(e)}
            results["errors"].append(f"Garmin wellness: {str(e)}")

        # Sync Hevy workouts
        try:
            from integrations.hevy.activity_importer import HevyActivityImporter
            hevy = HevyActivityImporter(db, athlete_id)
            imported, skipped, errors = hevy.import_recent_workouts(days)
            results["hevy"] = {"imported": imported, "skipped": skipped}
            if errors:
                results["errors"].extend(errors)
        except Exception as e:
            results["hevy"] = {"error": str(e)}
            results["errors"].append(f"Hevy: {str(e)}")

        results["status"] = "completed" if not results["errors"] else "completed_with_errors"
        return results

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
                        <input class="md-input" type="date" id="date" name="date" value="{get_eastern_today()}" required>
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

        today = get_eastern_today()
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

        today = get_eastern_today()
        # Rolling 7 days (today and previous 6 days)
        week_end = today
        week_start = today - timedelta(days=6)

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
        days_elapsed = (get_eastern_today() - start_date).days
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
            days_elapsed = (get_eastern_today() - start_date).days
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

        today = get_eastern_today()
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
            "initialized_at": str(get_eastern_today())
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

    def _get_workout_details(self, workout_type, week_number):
        """Get workout details based on type and week from the training plan."""
        # Swim A - Threshold/CSS Development
        swim_a_main_sets = {
            (1, 2): "10×100 @ steady (RPE 6-7), 15-20s rest",
            (3, 4): "8×125 @ steady, 15-20s rest",
            (5, 6): "6×150 @ steady, 20-25s rest",
            (7, 8): "5×200 @ steady, 20-30s rest",
            (9, 10): "12×100 @ CSS pace, 10-15s rest",
            (11, 12): "8×150 @ CSS pace, 15-20s rest",
            (13, 14): "6×200 @ CSS pace, 20s rest",
            (15, 16): "4×300 @ slightly slower than CSS, 30s rest",
            (17, 18): "3×(4×100 @ target 400 pace), 15-20s rest; 2 min between rounds",
            (19, 20): "6×150 @ target 400 pace, 20-30s rest",
            (21, 22): "3×300 @ target 400 pace, 30-45s rest",
            (23, 23): "6×50 @ target 400 pace, generous rest",
            (24, 24): "Light technique + 400 TT on Swim B day",
        }

        # Swim B - VO2 + 400-Specific
        swim_b_main_sets = {
            (1, 2): "12×50 @ moderate-hard (RPE 7), 20s rest",
            (3, 4): "16×50 @ moderate-hard, 20s rest",
            (5, 6): "8×75 @ moderate-hard, 25s rest",
            (7, 8): "10×50 @ strong (RPE 8), 25s rest",
            (9, 10): "20×25 @ hard (RPE 9), 10-20s rest",
            (11, 12): "10×50 @ hard (RPE 8-9), 30-40s rest",
            (13, 14): "5×100 @ hard (RPE 8-9), 45-60s rest",
            (15, 16): "Broken 400: 4×100 @ target 400 pace, 20-30s rest",
            (17, 18): "12×50 @ hard (RPE 8-9), 30-40s rest",
            (19, 20): "8×75 @ hard, 45s rest",
            (21, 22): "5×100 @ hard, 60s rest",
            (23, 23): "8×25 fast-but-clean, lots of rest",
            (24, 24): "400 TT (push)",
        }

        # VO2 Sessions
        vo2_main_sets = {
            (1, 4): "6×2 min @ hard (RPE 8), 2 min easy between",
            (5, 8): "5×3 min @ hard, 2 min easy between",
            (9, 12): "4×4 min @ hard, 2.5 min easy between",
            (13, 16): "5×3 min @ hard, 90s easy between",
            (17, 20): "6×2 min @ very hard (RPE 9), 2 min easy between",
            (21, 23): "4×3 min @ hard, 2 min easy between",
            (24, 24): "Light 20 min easy (taper)",
        }

        def get_main_set(sets_dict, week):
            for (start, end), main_set in sets_dict.items():
                if start <= week <= end:
                    return main_set
            return None

        if workout_type == "swim_a":
            main_set = get_main_set(swim_a_main_sets, week_number)
            # Test week adjustment
            if week_number in [2, 12, 24]:
                main_set = "6×50 @ CSS/target 400 pace, 30-45s rest (Test week taper)"
            return {
                "warmup": [
                    {"name": "Easy swim", "distance": "300 yards"},
                    {"name": "Drill/swim by 25", "sets": "6×50", "rest": "15-20s", "notes": "Catch-up, fingertip drag, 6-kick switch"}
                ],
                "main": [
                    {"name": "Main Set", "description": main_set}
                ],
                "cooldown": [
                    {"name": "Easy swim", "distance": "200 yards"}
                ]
            }

        elif workout_type == "swim_b":
            main_set = get_main_set(swim_b_main_sets, week_number)
            return {
                "warmup": [
                    {"name": "Easy swim", "distance": "300 yards"},
                    {"name": "Build swims", "sets": "4×50", "rest": "15-20s", "notes": "Easy → moderate"},
                    {"name": "Fast-but-clean", "sets": "4×25", "rest": "30-45s", "notes": "Crisp speed, good form"}
                ],
                "main": [
                    {"name": "Main Set", "description": main_set}
                ],
                "cooldown": [
                    {"name": "Easy swim", "distance": "200 yards"}
                ]
            }

        elif workout_type == "swim_test":
            return {
                "warmup": [
                    {"name": "Easy swim", "distance": "300 yards"},
                    {"name": "Build swims", "sets": "4×50", "rest": "20s", "notes": "Easy → moderate"},
                    {"name": "Fast-but-clean", "sets": "4×25", "rest": "40-60s"},
                    {"name": "Easy swim", "sets": "2×25"},
                    {"name": "Rest before TT", "duration": "2-3 minutes"}
                ],
                "main": [
                    {"name": "400y Freestyle Time Trial", "description": "From a push start", "notes": "Pacing: controlled first 100, build through 200-300, hold form 300-400"}
                ],
                "cooldown": [
                    {"name": "Easy cool-down", "distance": "200-400 yards"},
                    {"name": "Optional drill/swim", "sets": "4×50", "notes": "Very easy if feeling tight"}
                ]
            }

        elif workout_type == "lift_a":
            return {
                "warmup": [
                    {"name": "Foam roll", "duration": "5-8 min", "notes": "Quads, glutes, hip flexors"},
                    {"name": "Dynamic stretches", "notes": "Leg swings, walking lunges, hip circles"},
                    {"name": "Bodyweight squats", "sets": "2×10"}
                ],
                "main": [
                    {"name": "Squats or Goblet Squats", "sets": "3×8-10", "notes": "Moderate weight"},
                    {"name": "Romanian Deadlifts", "sets": "3×10-12"},
                    {"name": "Bulgarian Split Squats", "sets": "2×8", "notes": "Each leg"},
                    {"name": "Box Jumps or Broad Jumps", "sets": "3×5", "notes": "Power focus, full recovery"},
                    {"name": "Single-Leg Balance", "sets": "2×30s", "notes": "Each leg, BOSU or unstable surface"}
                ],
                "finisher": [
                    {"name": "Farmers Carry", "sets": "2×40 yards"}
                ],
                "cooldown": [
                    {"name": "Hip flexor stretch", "duration": "2 min each side"},
                    {"name": "Pigeon pose", "duration": "2 min each side"}
                ]
            }

        elif workout_type == "lift_b":
            return {
                "warmup": [
                    {"name": "Arm circles, band pull-aparts, cat-cow", "duration": "5-8 min"},
                    {"name": "Push-ups", "sets": "2×10"}
                ],
                "main": [
                    {"name": "Bench Press or Push-ups", "sets": "3×8-10"},
                    {"name": "Bent-Over Rows", "sets": "3×10-12"},
                    {"name": "Overhead Press", "sets": "3×8-10"},
                    {"name": "Pull-ups or Lat Pulldowns", "sets": "3×8-10"},
                    {"name": "Pallof Press", "sets": "2×12", "notes": "Each side, anti-rotation"},
                    {"name": "Med Ball Rotational Throws", "sets": "2×8", "notes": "Each side"}
                ],
                "finisher": [
                    {"name": "Suitcase Carry", "sets": "2×40 yards", "notes": "Each hand"}
                ],
                "cooldown": [
                    {"name": "Thoracic spine rotation"},
                    {"name": "Doorway chest stretch"}
                ]
            }

        elif workout_type == "vo2":
            main_set = get_main_set(vo2_main_sets, week_number)
            return {
                "warmup": [
                    {"name": "Easy jog/row/spin", "duration": "8-10 min"},
                    {"name": "Dynamic stretches"},
                    {"name": "Strides or pickups", "sets": "3-4×15-20s"}
                ],
                "main": [
                    {"name": "Intervals", "description": main_set}
                ],
                "cooldown": [
                    {"name": "Easy + stretching", "duration": "5 min"}
                ]
            }

        return None

    def _generate_upcoming_page(self, db):
        """Generate the upcoming workouts HTML page with all future workouts."""
        from database.models import Athlete, ScheduledWorkout

        athlete = db.query(Athlete).first()
        if not athlete:
            return self._no_db_html("Upcoming Workouts")

        today = get_eastern_today()

        # Get ALL future scheduled workouts
        workouts = db.query(ScheduledWorkout).filter(
            ScheduledWorkout.athlete_id == athlete.id,
            ScheduledWorkout.scheduled_date >= today
        ).order_by(ScheduledWorkout.scheduled_date).all()

        # Group by week for better organization
        workouts_by_week = {}
        for w in workouts:
            week_key = w.week_number
            if week_key not in workouts_by_week:
                workouts_by_week[week_key] = []
            workouts_by_week[week_key].append(w)

        if not workouts_by_week:
            content = '''
            <header class="mb-6">
                <h1 class="md-headline-large mb-2">Upcoming Workouts</h1>
                <p class="md-body-large text-secondary">Training Plan</p>
            </header>
            <div class="md-card">
                <div class="md-card-content" style="text-align: center; padding: 48px;">
                    <div style="font-size: 48px; margin-bottom: 16px;">📅</div>
                    <h2 class="md-title-large mb-4">No Upcoming Workouts</h2>
                    <p class="md-body-medium text-secondary">Initialize your training plan to see scheduled workouts.</p>
                </div>
            </div>
            '''
            return wrap_page(content, "Upcoming Workouts", "/upcoming")

        # Build week cards
        weeks_html = ""
        test_weeks = [2, 12, 24]

        for week_num in sorted(workouts_by_week.keys()):
            week_workouts = workouts_by_week[week_num]
            is_test_week = week_num in test_weeks

            # Calculate week date range
            week_dates = [w.scheduled_date for w in week_workouts]
            week_start = min(week_dates)
            week_end = max(week_dates)

            # Check if this is current week
            is_current = any(w.scheduled_date == today for w in week_workouts) or (week_start <= today <= week_end)
            week_class = "current-week" if is_current else ""

            # Build workout items with inline expandable details
            items_html = ""
            for w in sorted(week_workouts, key=lambda x: x.scheduled_date):
                style = WORKOUT_STYLES.get(w.workout_type, {"icon": "💪", "label": w.workout_type, "color": "#666"})

                status_badge = ""
                if w.status == "completed":
                    status_badge = '<span class="workout-status completed">✓ Completed</span>'
                elif w.status == "skipped":
                    status_badge = '<span class="workout-status skipped">Skipped</span>'
                elif w.garmin_workout_id:
                    status_badge = '<span class="workout-status synced">Synced to Garmin</span>'

                is_today = w.scheduled_date == today
                day_label = "Today" if is_today else w.scheduled_date.strftime("%a %m/%d")
                today_class = "is-today" if is_today else ""

                duration_text = f"{w.duration_minutes} min" if w.duration_minutes else ""

                # Get workout details from training plan
                workout_details = self._get_workout_details(w.workout_type, w.week_number)

                # Build details HTML
                details_html = ""
                if workout_details:
                    for phase_name, exercises in workout_details.items():
                        phase_label = phase_name.replace("_", " ").title()
                        details_html += f'<div class="phase-section"><div class="phase-label">{phase_label}</div>'
                        for ex in exercises:
                            ex_name = ex.get("name", "")
                            ex_parts = []
                            if ex.get("sets"):
                                ex_parts.append(ex["sets"])
                            if ex.get("distance"):
                                ex_parts.append(ex["distance"])
                            if ex.get("duration"):
                                ex_parts.append(ex["duration"])
                            if ex.get("description"):
                                ex_parts.append(ex["description"])
                            if ex.get("rest"):
                                ex_parts.append(f"Rest: {ex['rest']}")

                            ex_info = " · ".join(ex_parts) if ex_parts else ""
                            ex_notes = ex.get("notes", "")

                            details_html += f'''
                            <div class="exercise-row">
                                <span class="exercise-name">{ex_name}</span>
                                {f'<span class="exercise-info">{ex_info}</span>' if ex_info else ''}
                                {f'<span class="exercise-notes">{ex_notes}</span>' if ex_notes else ''}
                            </div>
                            '''
                        details_html += '</div>'

                items_html += f'''
                <div class="workout-card {today_class}" data-workout-id="{w.id}">
                    <div class="workout-header" onclick="toggleWorkout(this)" style="border-left-color: {style["color"]};">
                        <div class="workout-icon" style="background: {style["color"]}20; color: {style["color"]};">
                            {style["icon"]}
                        </div>
                        <div class="workout-info">
                            <div class="workout-title">{w.workout_name or style["label"]}</div>
                            <div class="workout-meta">
                                <span class="workout-day">{day_label}</span>
                                {f'<span class="workout-duration">{duration_text}</span>' if duration_text else ''}
                            </div>
                        </div>
                        <div class="workout-actions">
                            {status_badge}
                            <span class="workout-chevron">▼</span>
                        </div>
                    </div>
                    <div class="workout-details">
                        {details_html if details_html else '<p class="no-details">No detailed workout structure available.</p>'}
                    </div>
                </div>
                '''

            test_badge = '<span class="test-week-badge">TEST WEEK</span>' if is_test_week else ""
            completed_count = len([w for w in week_workouts if w.status == "completed"])
            total_count = len(week_workouts)
            progress_text = f"{completed_count}/{total_count} completed" if completed_count > 0 else f"{total_count} workouts"

            weeks_html += f'''
            <div class="week-card {week_class}">
                <div class="week-header" onclick="toggleWeek(this)">
                    <div class="week-title">
                        <span class="week-number">Week {week_num}</span>
                    </div>
                    <div class="week-meta">
                        <span class="week-dates">{week_start.strftime("%b %d")} - {week_end.strftime("%b %d")}</span>
                        <span class="week-progress">{progress_text}</span>
                    </div>
                    <div class="week-right">
                        {test_badge}
                        <span class="week-toggle">▶</span>
                    </div>
                </div>
                <div class="week-workouts">
                    {items_html}
                </div>
            </div>
            '''

        total_workouts = len(workouts)
        total_weeks = len(workouts_by_week)

        content = f'''
        <header class="mb-6">
            <h1 class="md-headline-large mb-2">Upcoming Workouts</h1>
            <p class="md-body-large text-secondary">{total_workouts} workouts across {total_weeks} weeks</p>
        </header>

        <div class="upcoming-grid">
            {weeks_html}
        </div>

        <style>
            .upcoming-grid {{
                display: flex;
                flex-direction: column;
                gap: 12px;
            }}

            /* Week Card */
            .week-card {{
                background: var(--md-surface);
                border-radius: var(--radius-lg);
                border: 1px solid var(--md-outline-variant);
                overflow: hidden;
            }}
            .week-card.current-week {{
                border-color: var(--md-primary);
                box-shadow: 0 0 0 1px var(--md-primary);
            }}
            .week-header {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 16px 20px;
                background: var(--md-surface-variant);
                cursor: pointer;
                user-select: none;
            }}
            .week-header:hover {{
                background: #e8e8e8;
            }}
            .week-card.current-week .week-header {{
                background: rgba(25, 118, 210, 0.08);
            }}
            .week-title {{
                display: flex;
                align-items: center;
                gap: 10px;
                min-width: 80px;
            }}
            .week-number {{
                font-size: 16px;
                font-weight: 600;
                color: var(--md-on-surface);
            }}
            .week-right {{
                display: flex;
                align-items: center;
                justify-content: flex-end;
                gap: 12px;
                min-width: 100px;
            }}
            .test-week-badge {{
                font-size: 10px;
                padding: 3px 8px;
                background: #ff9800;
                color: white;
                border-radius: var(--radius-full);
                font-weight: 600;
                text-transform: uppercase;
            }}
            .week-meta {{
                display: flex;
                gap: 16px;
                align-items: center;
                flex: 1;
            }}
            .week-dates, .week-progress {{
                font-size: 13px;
                color: var(--md-on-surface-variant);
            }}
            .week-toggle {{
                font-size: 12px;
                color: var(--md-on-surface-variant);
                transition: transform 0.2s;
                transform: rotate(90deg);
            }}
            .week-card.collapsed .week-toggle {{
                transform: rotate(0deg);
            }}
            .week-card.collapsed .week-workouts {{
                display: none;
            }}

            /* Workout Cards */
            .week-workouts {{
                padding: 12px;
                display: flex;
                flex-direction: column;
                gap: 8px;
            }}
            .workout-card {{
                background: var(--md-surface);
                border-radius: var(--radius-md);
                overflow: hidden;
            }}
            .workout-card.is-today {{
                box-shadow: 0 0 0 2px var(--md-primary);
            }}
            .workout-header {{
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 12px 16px;
                background: var(--md-surface-variant);
                border-left: 4px solid;
                cursor: pointer;
                transition: background 0.15s;
            }}
            .workout-header:hover {{
                background: #e0e0e0;
            }}
            .workout-icon {{
                width: 40px;
                height: 40px;
                border-radius: var(--radius-full);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 20px;
                flex-shrink: 0;
            }}
            .workout-info {{
                flex: 1;
                min-width: 0;
            }}
            .workout-title {{
                font-weight: 500;
                color: var(--md-on-surface);
                margin-bottom: 2px;
            }}
            .workout-meta {{
                display: flex;
                gap: 12px;
                align-items: center;
            }}
            .workout-day {{
                font-size: 12px;
                color: var(--md-on-surface-variant);
                font-weight: 500;
            }}
            .workout-duration {{
                font-size: 12px;
                color: var(--md-on-surface-variant);
            }}
            .workout-actions {{
                display: flex;
                align-items: center;
                gap: 8px;
                flex-shrink: 0;
            }}
            .workout-chevron {{
                font-size: 12px;
                color: var(--md-on-surface-variant);
                transition: transform 0.2s;
            }}
            .workout-card.collapsed .workout-chevron {{
                transform: rotate(-90deg);
            }}
            .workout-status {{
                font-size: 11px;
                padding: 4px 10px;
                border-radius: var(--radius-full);
                font-weight: 500;
            }}
            .workout-status.completed {{
                background: #e8f5e9;
                color: #2e7d32;
            }}
            .workout-status.skipped {{
                background: #fff3e0;
                color: #e65100;
            }}
            .workout-status.synced {{
                background: #e3f2fd;
                color: #1565c0;
            }}

            /* Workout Details (Expandable) */
            .workout-details {{
                padding: 16px 20px;
                background: #fafafa;
                border-top: 1px solid var(--md-outline-variant);
            }}
            .workout-card.collapsed .workout-details {{
                display: none;
            }}
            .phase-section {{
                margin-bottom: 16px;
            }}
            .phase-section:last-child {{
                margin-bottom: 0;
            }}
            .phase-label {{
                font-size: 11px;
                font-weight: 600;
                color: var(--md-primary);
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 8px;
                padding-bottom: 4px;
                border-bottom: 1px solid var(--md-outline-variant);
            }}
            .exercise-row {{
                padding: 8px 0;
                border-bottom: 1px solid #eee;
            }}
            .exercise-row:last-child {{
                border-bottom: none;
            }}
            .exercise-name {{
                font-weight: 500;
                color: var(--md-on-surface);
                display: block;
            }}
            .exercise-info {{
                font-size: 13px;
                color: var(--md-on-surface-variant);
                display: block;
                margin-top: 2px;
            }}
            .exercise-notes {{
                font-size: 12px;
                color: #666;
                font-style: italic;
                display: block;
                margin-top: 2px;
            }}
            .no-details {{
                color: var(--md-on-surface-variant);
                font-style: italic;
                margin: 0;
            }}

            @media (max-width: 640px) {{
                .week-header {{
                    flex-wrap: wrap;
                    gap: 8px;
                }}
                .week-right {{
                    min-width: auto;
                }}
                .workout-header {{
                    padding: 10px 12px;
                }}
                .workout-icon {{
                    width: 36px;
                    height: 36px;
                    font-size: 18px;
                }}
                .workout-details {{
                    padding: 12px 16px;
                }}
            }}
        </style>

        <script>
            function toggleWeek(header) {{
                const card = header.parentElement;
                card.classList.toggle('collapsed');
            }}

            function toggleWorkout(header) {{
                const card = header.parentElement;
                card.classList.toggle('collapsed');
            }}

            // Collapse future weeks by default (keep current and next week expanded)
            // All workouts start collapsed
            document.addEventListener('DOMContentLoaded', () => {{
                // Collapse weeks after the first 2
                const weekCards = document.querySelectorAll('.week-card');
                weekCards.forEach((card, index) => {{
                    if (index > 1 && !card.classList.contains('current-week')) {{
                        card.classList.add('collapsed');
                    }}
                }});

                // Collapse all workouts by default
                const workoutCards = document.querySelectorAll('.workout-card');
                workoutCards.forEach(card => {{
                    card.classList.add('collapsed');
                }});
            }});
        </script>
        '''
        return wrap_page(content, "Upcoming Workouts", "/upcoming")

    def _generate_reviews_page(self, db):
        """Generate the plan reviews HTML page."""
        from database.models import Athlete, DailyReview

        athlete = db.query(Athlete).first()
        if not athlete:
            return self._no_db_html("Plan Reviews")

        today = get_eastern_today()
        cutoff = today - timedelta(days=30)

        # Get recent reviews
        reviews = db.query(DailyReview).filter(
            DailyReview.athlete_id == athlete.id,
            DailyReview.review_date >= cutoff
        ).order_by(DailyReview.review_date.desc()).all()

        # Count total pending modifications across all reviews
        total_pending_mods = 0
        for r in reviews:
            if r.proposed_adjustments:
                adjustments = json.loads(r.proposed_adjustments)
                total_pending_mods += sum(1 for adj in adjustments if adj.get("status", "pending") == "pending")

        pending_count = total_pending_mods

        # Get plan status
        goals_data = json.loads(athlete.goals) if athlete.goals else {}
        plan_info = goals_data.get("training_plan", {})
        start_date_str = plan_info.get("start_date")

        is_initialized = bool(start_date_str)
        current_week = 1
        if start_date_str:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            days_elapsed = (today - start_date).days
            current_week = min(max(1, (days_elapsed // 7) + 1), 24)

        if not is_initialized:
            content = '''
            <header class="mb-6">
                <h1 class="md-headline-large mb-2">Plan Reviews</h1>
                <p class="md-body-large text-secondary">AI-generated training plan evaluations</p>
            </header>
            <div class="md-card">
                <div class="md-card-content" style="text-align: center; padding: 48px;">
                    <div style="font-size: 48px; margin-bottom: 16px;">📋</div>
                    <h2 class="md-title-large mb-4">Plan Not Initialized</h2>
                    <p class="md-body-medium text-secondary">Initialize your training plan to enable AI evaluations.</p>
                </div>
            </div>
            '''
            return wrap_page(content, "Plan Reviews", "/reviews")

        # Build review cards
        cards_html = ""
        for review in reviews:
            adjustments = json.loads(review.proposed_adjustments) if review.proposed_adjustments else []
            lifestyle_insights = json.loads(review.lifestyle_insights_json) if review.lifestyle_insights_json else {}

            status = review.approval_status or "pending"

            review_date = review.review_date
            if review_date == today:
                date_label = "Today"
            elif review_date == today - timedelta(days=1):
                date_label = "Yesterday"
            else:
                date_label = review_date.strftime("%b %d, %Y")

            # Build modifications list with individual status and actions
            mods_html = ""
            pending_mod_count = 0
            if adjustments:
                for idx, adj in enumerate(adjustments):
                    adj_type = adj.get("type", "unknown")
                    adj_desc = adj.get("description", "No description")
                    adj_reason = adj.get("reason", "")
                    adj_priority = adj.get("priority", "medium")
                    adj_week = adj.get("week", "?")
                    mod_status = adj.get("status", "pending")

                    if mod_status == "pending":
                        pending_mod_count += 1

                    p_style = PRIORITY_COLORS.get(adj_priority, PRIORITY_COLORS["medium"])

                    # Status badge colors
                    mod_status_styles = {
                        "pending": {"bg": "#fff3e0", "text": "#e65100", "label": "Pending"},
                        "approved": {"bg": "#e3f2fd", "text": "#1565c0", "label": "Approved"},
                        "updated": {"bg": "#e8f5e9", "text": "#2e7d32", "label": "Updated"},
                        "rejected": {"bg": "#ffebee", "text": "#c62828", "label": "Rejected"}
                    }
                    s_style = mod_status_styles.get(mod_status, mod_status_styles["pending"])

                    # Add reminder for approved but not synced
                    needs_action_html = ""
                    if mod_status == "approved":
                        needs_action_html = '<div class="mod-needs-action">⚠️ Needs local sync to update Garmin</div>'

                    # Individual action buttons (only for pending modifications)
                    mod_actions_html = ""
                    if mod_status == "pending":
                        mod_actions_html = f'''
                        <div class="mod-actions">
                            <button class="mod-btn approve-mod" onclick="actionModification({review.id}, {idx}, 'approve')" title="Approve this modification">✓</button>
                            <button class="mod-btn reject-mod" onclick="actionModification({review.id}, {idx}, 'reject')" title="Reject this modification">✗</button>
                        </div>
                        '''

                    mods_html += f'''
                    <div class="modification-item {'mod-actioned' if mod_status != 'pending' else ''}" data-review-id="{review.id}" data-mod-index="{idx}">
                        <div class="mod-header">
                            <span class="mod-type">{adj_type.replace("_", " ").title()}</span>
                            <span class="mod-priority" style="background: {p_style["bg"]}; color: {p_style["text"]};">{adj_priority.upper()}</span>
                            <span class="mod-week">Week {adj_week}</span>
                            <span class="mod-status" style="background: {s_style["bg"]}; color: {s_style["text"]};">{s_style["label"]}</span>
                        </div>
                        <div class="mod-content">
                            <div class="mod-details">
                                <div class="mod-description">{adj_desc}</div>
                                {f'<div class="mod-reason">{adj_reason}</div>' if adj_reason else ''}
                                {needs_action_html}
                            </div>
                            {mod_actions_html}
                        </div>
                    </div>
                    '''
            else:
                mods_html = '<p class="text-secondary" style="padding: 16px;">No modifications proposed</p>'

            # Action buttons for bulk approve/reject (only if there are pending modifications)
            actions_html = ""
            if pending_mod_count > 0:
                actions_html = f'''
                <div class="review-actions">
                    <button class="md-btn md-btn-filled approve-btn" onclick="actionReview({review.id}, 'approve')">
                        ✓ Approve All Pending ({pending_mod_count})
                    </button>
                    <button class="md-btn md-btn-outlined reject-btn" onclick="actionReview({review.id}, 'reject')">
                        ✗ Reject All Pending
                    </button>
                </div>
                '''
            elif review.approval_notes:
                actions_html = f'''
                <div class="review-notes">
                    <strong>Notes:</strong> {review.approval_notes}
                </div>
                '''

            # Show user context if provided
            user_context_html = ""
            if review.user_context:
                user_context_html = f'''
                <div class="user-context-section">
                    <span class="context-icon">💬</span>
                    <span class="context-label">Your notes:</span>
                    <span class="context-text">{review.user_context}</span>
                </div>
                '''

            # Build lifestyle insights HTML
            lifestyle_html = ""
            if lifestyle_insights:
                insights_cards = ""
                for category in ["health", "recovery", "nutrition", "sleep"]:
                    if category in lifestyle_insights:
                        insight = lifestyle_insights[category]
                        sev = insight.get("severity", "info")
                        sev_style = SEVERITY_STYLES.get(sev, SEVERITY_STYLES["info"])
                        observation = insight.get("observation", "")
                        actions = insight.get("actions", [])

                        actions_html_list = "".join([f'<li>{action}</li>' for action in actions])

                        insights_cards += f'''
                        <div class="lifestyle-insight-card" style="border-left: 3px solid {sev_style["text"]};">
                            <div class="insight-header">
                                <span class="insight-category">{sev_style["icon"]} {category.title()}</span>
                                <span class="insight-severity" style="background: {sev_style["bg"]}; color: {sev_style["text"]};">{sev.upper()}</span>
                            </div>
                            <p class="insight-observation">{observation}</p>
                            {"<div class='insight-actions'><strong>Actions:</strong><ul>" + actions_html_list + "</ul></div>" if actions else ""}
                        </div>
                        '''

                if insights_cards:
                    lifestyle_html = f'''
                    <div class="lifestyle-insights-section">
                        <h4 class="section-toggle" onclick="toggleSection(this)">
                            <span class="toggle-icon">▶</span> Lifestyle Insights
                        </h4>
                        <div class="section-content collapsed">
                            <div class="lifestyle-insights-grid">
                                {insights_cards}
                            </div>
                        </div>
                    </div>
                    '''

            cards_html += f'''
            <div class="review-card {'pending' if status == 'pending' else ''}" data-review-id="{review.id}">
                <div class="review-header" onclick="toggleReviewDetails(this)">
                    <div class="review-date">
                        <span class="date-label">{date_label}</span>
                        <span class="date-full">{review_date.strftime("%A")}</span>
                    </div>
                    <span class="expand-icon">▼</span>
                </div>
                {user_context_html}
                <div class="review-body collapsed">
                    {f'<div class="review-insights"><h4>Progress Summary</h4><p>{review.insights}</p></div>' if review.insights else ''}
                    {f'<div class="review-recommendations"><h4>Next Week Focus</h4><p>{review.recommendations}</p></div>' if review.recommendations else ''}
                    {lifestyle_html}
                    <div class="review-modifications">
                        <h4>Proposed Modifications ({len(adjustments)})</h4>
                        <div class="modifications-list">
                            {mods_html}
                        </div>
                    </div>
                </div>
                {actions_html}
            </div>
            '''

        # Pending alert
        pending_alert = ""
        if pending_count > 0:
            pending_alert = f'''
            <div class="pending-alert">
                <div class="alert-icon">⚠️</div>
                <div class="alert-content">
                    <strong>{pending_count} modification{"s" if pending_count > 1 else ""} pending approval</strong>
                    <p>Review the AI-suggested modifications and approve or reject them individually or in bulk.</p>
                </div>
            </div>
            '''

        # No reviews message
        if not reviews:
            cards_html = '''
            <div class="md-card">
                <div class="md-card-content" style="text-align: center; padding: 48px;">
                    <div style="font-size: 48px; margin-bottom: 16px;">🤖</div>
                    <h2 class="md-title-large mb-4">No Evaluations Yet</h2>
                    <p class="md-body-medium text-secondary">AI evaluations run nightly after the cron sync.</p>
                    <p class="md-body-small text-secondary mt-2">Use the form above to run a manual evaluation.</p>
                </div>
            </div>
            '''

        content = f'''
        <header class="mb-6">
            <h1 class="md-headline-large mb-2">Plan Reviews</h1>
            <p class="md-body-large text-secondary">Week {current_week} of 24 · {len(reviews)} evaluations</p>
        </header>

        <!-- Manual Evaluation Section -->
        <div class="md-card mb-6">
            <div class="md-card-header">
                <h2 class="md-title-medium">Run AI Evaluation</h2>
            </div>
            <div class="md-card-content">
                <p class="md-body-medium text-secondary mb-4">
                    Add context or notes for the AI to consider when evaluating your training plan.
                </p>
                <div class="context-input-group">
                    <label for="user-context" class="md-label-medium">Your Notes (optional)</label>
                    <textarea
                        id="user-context"
                        class="md-input context-textarea"
                        placeholder="Example: I've been feeling fatigued this week..."
                        rows="3"
                    ></textarea>
                </div>
                <div class="evaluation-actions">
                    <button class="md-btn md-btn-filled" onclick="runEvaluation()" id="eval-btn">
                        🤖 Run Evaluation
                    </button>
                    <button class="md-btn md-btn-outlined" onclick="viewContext()">
                        📊 View Input Data
                    </button>
                </div>
                <div id="eval-status" class="eval-status hidden"></div>
            </div>
        </div>

        <!-- Context Modal -->
        <div id="context-modal" class="modal hidden">
            <div class="modal-content">
                <div class="modal-header">
                    <h3 class="md-title-large">AI Evaluation Input Data</h3>
                    <button class="modal-close" onclick="closeModal()">&times;</button>
                </div>
                <div class="modal-body" id="context-data">Loading...</div>
            </div>
        </div>

        {pending_alert}

        <div class="reviews-list">
            {cards_html}
        </div>

        <script>
        async function actionReview(reviewId, action) {{
            const notes = action === 'reject' ? prompt('Reason for rejection (optional):') : null;
            try {{
                const response = await fetch(`/api/plan/reviews/${{reviewId}}/action`, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{ action, notes }})
                }});
                if (response.ok) {{
                    location.reload();
                }} else {{
                    const data = await response.json();
                    alert('Error: ' + (data.detail || data.error || 'Failed'));
                }}
            }} catch (e) {{
                alert('Error: ' + e.message);
            }}
        }}

        async function actionModification(reviewId, modIndex, action) {{
            // Find the modification item element
            const modItem = document.querySelector(`[data-review-id="${{reviewId}}"][data-mod-index="${{modIndex}}"]`);
            const statusBadge = modItem?.querySelector('.mod-status');
            const actionsDiv = modItem?.querySelector('.mod-actions');

            try {{
                const response = await fetch(`/api/plan/reviews/${{reviewId}}/modifications/${{modIndex}}/action`, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{ action }})
                }});

                const data = await response.json();

                if (response.ok) {{
                    // Update the UI without reloading
                    if (modItem) {{
                        modItem.classList.add('mod-actioned');

                        // Update status badge
                        if (statusBadge) {{
                            if (action === 'approve') {{
                                // Check if Garmin sync was successful
                                const garminSync = data.garmin_sync || {{}};
                                const hasApplied = garminSync.applied && garminSync.applied.length > 0;
                                const hasErrors = garminSync.garmin_failed && garminSync.garmin_failed.length > 0;
                                const isUpdated = hasApplied && !hasErrors;

                                if (isUpdated) {{
                                    statusBadge.style.background = '#e8f5e9';
                                    statusBadge.style.color = '#2e7d32';
                                    statusBadge.textContent = 'Updated';
                                }} else {{
                                    statusBadge.style.background = '#e3f2fd';
                                    statusBadge.style.color = '#1565c0';
                                    statusBadge.textContent = 'Approved';

                                    // Add needs action message
                                    const detailsDiv = modItem.querySelector('.mod-details');
                                    if (detailsDiv && !detailsDiv.querySelector('.mod-needs-action')) {{
                                        const needsAction = document.createElement('div');
                                        needsAction.className = 'mod-needs-action';
                                        needsAction.textContent = '⚠️ Needs local sync to update Garmin';
                                        detailsDiv.appendChild(needsAction);
                                    }}
                                }}
                            }} else {{
                                statusBadge.style.background = '#ffebee';
                                statusBadge.style.color = '#c62828';
                                statusBadge.textContent = 'Rejected';
                            }}
                        }}

                        // Remove action buttons
                        if (actionsDiv) {{
                            actionsDiv.remove();
                        }}

                        // Update pending count in header
                        updatePendingCount();
                    }}
                }} else {{
                    alert('Error: ' + (data.detail || data.error || 'Failed'));
                }}
            }} catch (e) {{
                alert('Error: ' + e.message);
            }}
        }}

        function updatePendingCount() {{
            // Count remaining pending items
            const pendingItems = document.querySelectorAll('.modification-item:not(.mod-actioned)').length;
            const pendingAlert = document.querySelector('.pending-alert');
            const approveAllBtns = document.querySelectorAll('.approve-btn');

            if (pendingItems === 0) {{
                // Hide pending alert and approve all buttons
                if (pendingAlert) pendingAlert.style.display = 'none';
                approveAllBtns.forEach(btn => btn.closest('.review-actions')?.remove());
            }} else {{
                // Update the count text
                const alertContent = pendingAlert?.querySelector('.alert-content strong');
                if (alertContent) {{
                    alertContent.textContent = `${{pendingItems}} modification${{pendingItems > 1 ? 's' : ''}} pending approval`;
                }}
            }}
        }}

        async function runEvaluation() {{
            const userContext = document.getElementById('user-context').value.trim();
            const btn = document.getElementById('eval-btn');
            const status = document.getElementById('eval-status');

            btn.disabled = true;
            btn.textContent = '⏳ Running...';
            status.className = 'eval-status';
            status.innerHTML = '<div class="status-loading">Analyzing training data... This may take 30-60 seconds.</div>';

            try {{
                const response = await fetch('/api/plan/evaluate-with-context', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{ user_context: userContext || null }})
                }});
                const data = await response.json();
                if (response.ok) {{
                    status.innerHTML = '<div class="status-success">✓ Evaluation complete! Refreshing...</div>';
                    setTimeout(() => location.reload(), 1500);
                }} else {{
                    status.innerHTML = '<div class="status-error">✗ Error: ' + (data.detail || data.error || 'Failed') + '</div>';
                    btn.disabled = false;
                    btn.textContent = '🤖 Run Evaluation';
                }}
            }} catch (e) {{
                status.innerHTML = '<div class="status-error">✗ Error: ' + e.message + '</div>';
                btn.disabled = false;
                btn.textContent = '🤖 Run Evaluation';
            }}
        }}

        async function viewContext() {{
            const modal = document.getElementById('context-modal');
            const content = document.getElementById('context-data');
            modal.classList.remove('hidden');
            try {{
                const response = await fetch('/api/plan/evaluation-context');
                const data = await response.json();
                content.innerHTML = `
                    <div class="context-section">
                        <h4>Current Week</h4>
                        <p>Week ${{data.current_week}} of 24</p>
                    </div>
                    <div class="context-section">
                        <h4>AI Instructions</h4>
                        <p class="text-secondary">${{data.ai_instructions}}</p>
                    </div>
                    <div class="context-section">
                        <h4>Wellness Data (7-day average)</h4>
                        <pre>${{JSON.stringify(data.wellness_data, null, 2)}}</pre>
                    </div>
                    <div class="context-section">
                        <h4>Recent Workouts</h4>
                        <pre>${{JSON.stringify(data.recent_workouts, null, 2)}}</pre>
                    </div>
                    <div class="context-section">
                        <h4>Goal Progress</h4>
                        <pre>${{JSON.stringify(data.goal_progress, null, 2)}}</pre>
                    </div>
                    <div class="context-section">
                        <h4>Upcoming Workouts</h4>
                        <pre>${{JSON.stringify(data.upcoming_workouts, null, 2)}}</pre>
                    </div>
                `;
            }} catch (e) {{
                content.innerHTML = '<p class="status-error">Error loading context: ' + e.message + '</p>';
            }}
        }}

        function closeModal() {{
            document.getElementById('context-modal').classList.add('hidden');
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') closeModal();
        }});

        function toggleReviewDetails(header) {{
            const card = header.closest('.review-card');
            const body = card.querySelector('.review-body');
            const icon = card.querySelector('.expand-icon');
            body.classList.toggle('collapsed');
            icon.textContent = body.classList.contains('collapsed') ? '▼' : '▲';
        }}

        function toggleSection(header) {{
            const content = header.nextElementSibling;
            const icon = header.querySelector('.toggle-icon');
            content.classList.toggle('collapsed');
            icon.textContent = content.classList.contains('collapsed') ? '▶' : '▼';
        }}

        // Auto-expand pending reviews
        document.querySelectorAll('.review-card.pending .review-body').forEach(body => {{
            body.classList.remove('collapsed');
            const card = body.closest('.review-card');
            card.querySelector('.expand-icon').textContent = '▲';
        }});
        </script>

        <style>
            .pending-alert {{
                display: flex;
                align-items: flex-start;
                gap: 16px;
                padding: 16px 20px;
                background: #fff3e0;
                border-radius: var(--radius-lg);
                border: 1px solid #ffcc80;
                margin-bottom: 24px;
            }}
            .alert-icon {{ font-size: 24px; }}
            .alert-content strong {{ color: #e65100; }}
            .alert-content p {{ margin: 4px 0 0; color: #bf360c; font-size: 14px; }}

            .reviews-list {{
                display: flex;
                flex-direction: column;
                gap: 20px;
            }}

            .review-card {{
                background: var(--md-surface);
                border-radius: var(--radius-lg);
                border: 1px solid var(--md-outline-variant);
                overflow: hidden;
            }}
            .review-card.pending {{
                border-color: #ffcc80;
                box-shadow: 0 0 0 1px #fff3e0;
            }}

            .review-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 16px 20px;
                background: var(--md-surface-variant);
                border-bottom: 1px solid var(--md-outline-variant);
                flex-wrap: wrap;
                gap: 12px;
            }}

            .review-date {{ display: flex; flex-direction: column; }}
            .date-label {{ font-size: 18px; font-weight: 600; color: var(--md-on-surface); }}
            .date-full {{ font-size: 13px; color: var(--md-on-surface-variant); }}

            .user-context-section {{
                padding: 12px 20px;
                background: #f3e5f5;
                border-bottom: 1px solid var(--md-outline-variant);
                display: flex;
                align-items: flex-start;
                gap: 8px;
                font-size: 14px;
            }}
            .context-icon {{ font-size: 16px; }}
            .context-label {{ font-weight: 600; color: #7b1fa2; white-space: nowrap; }}
            .context-text {{ color: #4a148c; line-height: 1.4; }}

            .review-body {{ padding: 20px; }}
            .review-insights, .review-recommendations {{ margin-bottom: 20px; }}
            .review-body h4 {{
                font-size: 14px;
                font-weight: 600;
                color: var(--md-on-surface);
                margin-bottom: 8px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .review-body p {{ color: var(--md-on-surface-variant); line-height: 1.6; }}

            .review-modifications {{
                margin-top: 20px;
                padding-top: 20px;
                border-top: 1px solid var(--md-outline-variant);
            }}

            .modifications-list {{
                display: flex;
                flex-direction: column;
                gap: 12px;
                margin-top: 12px;
            }}

            .modification-item {{
                padding: 16px;
                background: var(--md-surface-variant);
                border-radius: var(--radius-md);
                border-left: 4px solid var(--md-primary);
            }}
            .modification-item.mod-actioned {{
                opacity: 0.7;
                border-left-color: #9e9e9e;
            }}
            .mod-header {{
                display: flex;
                align-items: center;
                gap: 8px;
                margin-bottom: 8px;
                flex-wrap: wrap;
            }}
            .mod-type {{ font-weight: 600; color: var(--md-on-surface); }}
            .mod-priority {{
                font-size: 10px;
                padding: 2px 8px;
                border-radius: var(--radius-full);
                font-weight: 600;
            }}
            .mod-week {{ font-size: 12px; color: var(--md-on-surface-variant); }}
            .mod-status {{
                font-size: 10px;
                padding: 2px 8px;
                border-radius: var(--radius-full);
                font-weight: 600;
                margin-left: auto;
            }}
            .mod-content {{
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                gap: 16px;
            }}
            .mod-details {{ flex: 1; }}
            .mod-description {{ color: var(--md-on-surface); margin-bottom: 6px; }}
            .mod-reason {{ font-size: 13px; color: var(--md-on-surface-variant); font-style: italic; }}
            .mod-needs-action {{
                font-size: 12px;
                color: #1565c0;
                background: #e3f2fd;
                padding: 6px 10px;
                border-radius: 4px;
                margin-top: 8px;
            }}
            .mod-actions {{
                display: flex;
                gap: 8px;
                flex-shrink: 0;
            }}
            .mod-btn {{
                width: 32px;
                height: 32px;
                border-radius: 50%;
                border: none;
                cursor: pointer;
                font-size: 14px;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: transform 0.1s, background 0.2s;
            }}
            .mod-btn:hover {{ transform: scale(1.1); }}
            .mod-btn.approve-mod {{ background: #e8f5e9; color: #2e7d32; }}
            .mod-btn.approve-mod:hover {{ background: #c8e6c9; }}
            .mod-btn.reject-mod {{ background: #ffebee; color: #c62828; }}
            .mod-btn.reject-mod:hover {{ background: #ffcdd2; }}

            .review-actions {{
                display: flex;
                gap: 12px;
                padding: 16px 20px;
                background: var(--md-surface-variant);
                border-top: 1px solid var(--md-outline-variant);
            }}
            .approve-btn {{ background: #2e7d32 !important; }}
            .approve-btn:hover {{ background: #1b5e20 !important; }}
            .reject-btn {{ color: #c62828 !important; border-color: #c62828 !important; }}
            .reject-btn:hover {{ background: #ffebee !important; }}

            .review-notes {{
                padding: 12px 20px;
                background: var(--md-surface-variant);
                border-top: 1px solid var(--md-outline-variant);
                font-size: 14px;
                color: var(--md-on-surface-variant);
            }}

            /* Context input styles */
            .context-input-group {{ margin-bottom: 16px; }}
            .context-input-group label {{
                display: block;
                margin-bottom: 8px;
                font-weight: 500;
                color: var(--md-on-surface);
            }}
            .context-textarea {{
                width: 100%;
                min-height: 80px;
                resize: vertical;
                font-family: inherit;
            }}
            .evaluation-actions {{ display: flex; gap: 12px; flex-wrap: wrap; }}
            .eval-status {{ margin-top: 16px; }}
            .eval-status.hidden {{ display: none; }}
            .status-loading {{
                padding: 12px 16px;
                background: #e3f2fd;
                color: #1565c0;
                border-radius: var(--radius-md);
            }}
            .status-success {{
                padding: 12px 16px;
                background: #e8f5e9;
                color: #2e7d32;
                border-radius: var(--radius-md);
            }}
            .status-error {{
                padding: 12px 16px;
                background: #ffebee;
                color: #c62828;
                border-radius: var(--radius-md);
            }}

            /* Collapsible sections */
            .review-header {{
                cursor: pointer;
                transition: background 0.2s;
            }}
            .review-header:hover {{
                background: var(--md-surface);
            }}
            .expand-icon {{
                font-size: 12px;
                color: var(--md-on-surface-variant);
                transition: transform 0.2s;
            }}
            .collapsed {{
                display: none !important;
            }}
            .section-toggle {{
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 8px 0;
                user-select: none;
            }}
            .section-toggle:hover {{
                color: var(--md-primary);
            }}
            .toggle-icon {{
                font-size: 12px;
                transition: transform 0.2s;
            }}

            /* Lifestyle insights */
            .lifestyle-insights-section {{
                margin-top: 20px;
                padding-top: 20px;
                border-top: 1px solid var(--md-outline-variant);
            }}
            .lifestyle-insights-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 16px;
                margin-top: 12px;
            }}
            .lifestyle-insight-card {{
                background: var(--md-surface-variant);
                border-radius: var(--radius-md);
                padding: 16px;
            }}
            .insight-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 12px;
            }}
            .insight-category {{
                font-weight: 600;
                font-size: 14px;
                color: var(--md-on-surface);
            }}
            .insight-severity {{
                font-size: 10px;
                padding: 2px 8px;
                border-radius: var(--radius-full);
                font-weight: 600;
            }}
            .insight-observation {{
                color: var(--md-on-surface-variant);
                line-height: 1.5;
                margin-bottom: 12px;
            }}
            .insight-actions {{
                background: var(--md-surface);
                border-radius: var(--radius-sm);
                padding: 12px;
            }}
            .insight-actions strong {{
                display: block;
                margin-bottom: 8px;
                color: var(--md-on-surface);
                font-size: 13px;
            }}
            .insight-actions ul {{
                margin: 0;
                padding-left: 20px;
            }}
            .insight-actions li {{
                color: var(--md-on-surface-variant);
                font-size: 13px;
                line-height: 1.6;
                margin-bottom: 4px;
            }}
            .insight-actions li:last-child {{
                margin-bottom: 0;
            }}

            /* Modal styles */
            .modal {{
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0,0,0,0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1000;
                padding: 20px;
            }}
            .modal.hidden {{ display: none; }}
            .modal-content {{
                background: var(--md-surface);
                border-radius: var(--radius-lg);
                max-width: 800px;
                max-height: 80vh;
                width: 100%;
                overflow: hidden;
                display: flex;
                flex-direction: column;
            }}
            .modal-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 16px 20px;
                border-bottom: 1px solid var(--md-outline-variant);
            }}
            .modal-close {{
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                color: var(--md-on-surface-variant);
                padding: 4px 8px;
            }}
            .modal-close:hover {{ color: var(--md-on-surface); }}
            .modal-body {{ padding: 20px; overflow-y: auto; }}
            .context-section {{ margin-bottom: 24px; }}
            .context-section h4 {{
                font-size: 14px;
                font-weight: 600;
                color: var(--md-on-surface);
                margin-bottom: 8px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .context-section pre {{
                background: var(--md-surface-variant);
                padding: 12px;
                border-radius: var(--radius-md);
                overflow-x: auto;
                font-size: 12px;
                line-height: 1.5;
                max-height: 200px;
                overflow-y: auto;
            }}

            @media (max-width: 640px) {{
                .review-header {{ flex-direction: column; align-items: flex-start; }}
                .review-actions {{ flex-direction: column; }}
                .review-actions button {{ width: 100%; }}
                .evaluation-actions {{ flex-direction: column; }}
                .evaluation-actions button {{ width: 100%; }}
                .modal-content {{ max-height: 90vh; }}
            }}
        </style>
        '''
        return wrap_page(content, "Plan Reviews", "/reviews")

    def _get_evaluation_context(self, db):
        """Get the data that would be sent to the AI for evaluation."""
        from database.models import Athlete, DailyWellness, CompletedActivity, Goal, GoalProgress, ScheduledWorkout

        athlete = db.query(Athlete).first()
        if not athlete:
            return {"status": "error", "message": "No athlete found"}

        goals_data = json.loads(athlete.goals) if athlete.goals else {}
        plan_info = goals_data.get("training_plan", {})
        start_date_str = plan_info.get("start_date")

        if not start_date_str:
            return {"status": "plan_not_initialized", "message": "Initialize your training plan first"}

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        today = get_eastern_today()
        days_elapsed = (today - start_date).days
        current_week = min(max(1, (days_elapsed // 7) + 1), 24)

        # Wellness data (7 days)
        wellness_start = today - timedelta(days=7)
        wellness_records = db.query(DailyWellness).filter(
            DailyWellness.athlete_id == athlete.id,
            DailyWellness.date >= wellness_start,
            DailyWellness.date <= today
        ).all()

        def avg(values):
            valid = [v for v in values if v is not None]
            return round(sum(valid) / len(valid), 1) if valid else None

        wellness_data = {
            "sleep_score_avg": avg([w.sleep_score for w in wellness_records]),
            "training_readiness_avg": avg([w.training_readiness_score for w in wellness_records]),
            "hrv_avg": avg([w.hrv_weekly_avg for w in wellness_records]),
            "stress_avg": avg([w.avg_stress_level for w in wellness_records]),
            "body_battery_avg": avg([w.body_battery_high for w in wellness_records]),
            "days_of_data": len(wellness_records)
        }

        # Recent workouts (14 days)
        workout_start = today - timedelta(days=14)
        activities = db.query(CompletedActivity).filter(
            CompletedActivity.athlete_id == athlete.id,
            CompletedActivity.activity_date >= workout_start,
            CompletedActivity.activity_date <= today
        ).order_by(CompletedActivity.activity_date.desc()).all()

        recent_workouts = [
            {
                "date": str(a.activity_date),
                "type": a.activity_type,
                "name": a.activity_name,
                "duration": a.duration_minutes
            }
            for a in activities
        ]

        # Goal progress
        goals = db.query(Goal).filter(
            Goal.athlete_id == athlete.id,
            Goal.status == "active"
        ).all()

        goal_progress = {}
        for goal in goals:
            latest = db.query(GoalProgress).filter(
                GoalProgress.goal_id == goal.id
            ).order_by(GoalProgress.date.desc()).first()

            goal_progress[goal.name] = {
                "target": goal.target_value,
                "current": latest.current_value if latest else goal.baseline_value,
                "progress_percent": latest.progress_percent if latest else 0,
                "trend": latest.trend if latest else "unknown"
            }

        # Upcoming workouts
        end_date = today + timedelta(days=7)
        scheduled = db.query(ScheduledWorkout).filter(
            ScheduledWorkout.athlete_id == athlete.id,
            ScheduledWorkout.scheduled_date >= today,
            ScheduledWorkout.scheduled_date <= end_date,
            ScheduledWorkout.status == "scheduled"
        ).order_by(ScheduledWorkout.scheduled_date).all()

        upcoming_workouts = [
            {
                "date": str(s.scheduled_date),
                "type": s.workout_type,
                "name": s.workout_name,
                "week": s.week_number
            }
            for s in scheduled
        ]

        return {
            "current_week": current_week,
            "wellness_data": wellness_data,
            "recent_workouts": recent_workouts,
            "goal_progress": goal_progress,
            "upcoming_workouts": upcoming_workouts,
            "ai_instructions": "The AI is instructed to be conservative with modifications - only suggesting changes when clearly warranted. It minimizes the number of workouts affected and always explains its reasoning."
        }

    def _get_latest_review(self, db):
        """Get the most recent AI evaluation review."""
        from database.models import Athlete, DailyReview

        athlete = db.query(Athlete).first()
        if not athlete:
            return {"status": "error", "message": "No athlete found"}

        review = db.query(DailyReview).filter(
            DailyReview.athlete_id == athlete.id
        ).order_by(DailyReview.review_date.desc()).first()

        if not review:
            return {"status": "no_reviews", "message": "No AI evaluations have been run yet"}

        return {
            "id": review.id,
            "date": str(review.review_date),
            "approval_status": review.approval_status,
            "progress_summary": json.loads(review.progress_summary) if review.progress_summary else None,
            "insights": review.insights,
            "recommendations": review.recommendations,
            "proposed_adjustments": json.loads(review.proposed_adjustments) if review.proposed_adjustments else [],
            "created_at": review.created_at.isoformat() if review.created_at else None
        }

    def _action_review(self, db, review_id, action, notes):
        """Approve or reject all pending modifications in a review. When approved, syncs changes to Garmin."""
        from database.models import Athlete, DailyReview, PlanAdjustment
        from analyst.plan_manager import TrainingPlanManager

        athlete = db.query(Athlete).first()
        if not athlete:
            raise Exception("No athlete found")

        review = db.query(DailyReview).filter(
            DailyReview.id == review_id,
            DailyReview.athlete_id == athlete.id
        ).first()

        if not review:
            raise Exception("Review not found")

        # Parse adjustments
        adjustments = json.loads(review.proposed_adjustments) if review.proposed_adjustments else []

        # Find pending modifications
        pending_mods = [adj for adj in adjustments if adj.get("status", "pending") == "pending"]

        if not pending_mods:
            raise Exception("No pending modifications to action")

        garmin_results = None
        action_time = datetime.utcnow().isoformat()

        # Create manager for plan operations
        manager = TrainingPlanManager(db, athlete.id)

        if action == "approve":
            review.approval_notes = notes

            # Ensure a training plan exists for the PlanAdjustment foreign key
            plan_id = manager._ensure_training_plan_exists()

            # Create PlanAdjustment records for tracking (only for pending mods)
            for adj in pending_mods:
                plan_adj = PlanAdjustment(
                    plan_id=plan_id,
                    review_id=review.id,
                    adjustment_date=get_eastern_today(),
                    adjustment_type=adj.get("type", "unknown"),
                    reasoning=adj.get("reason", ""),
                    changes=json.dumps(adj)
                )
                db.add(plan_adj)

            # Apply modifications to ScheduledWorkouts and sync to Garmin
            garmin_success = False
            try:
                garmin_results = manager.apply_approved_modifications(
                    pending_mods,
                    sync_to_garmin=True
                )
                review.adjustments_applied = True

                # Check if Garmin sync was successful
                if garmin_results:
                    has_errors = bool(garmin_results.get("garmin_failed"))
                    has_applied = bool(garmin_results.get("applied"))
                    garmin_success = has_applied and not has_errors
            except Exception as e:
                # Still mark as approved even if Garmin sync fails
                review.adjustments_applied = True
                garmin_results = {"error": str(e)}

            # Update status of pending modifications based on result
            new_status = "updated" if garmin_success else "approved"
            for adj in adjustments:
                if adj.get("status", "pending") == "pending":
                    adj["status"] = new_status
                    adj["actioned_at"] = action_time

        elif action == "reject":
            review.approval_notes = notes
            # Update status for rejected modifications
            for adj in adjustments:
                if adj.get("status", "pending") == "pending":
                    adj["status"] = "rejected"
                    adj["actioned_at"] = action_time

        # Update the review with modified adjustments
        review.proposed_adjustments = json.dumps(adjustments)

        # Recalculate overall review status
        review.approval_status = TrainingPlanManager.calculate_review_status(adjustments)
        review.approved_at = datetime.utcnow()

        db.commit()

        result = {
            "status": "success",
            "review_id": review_id,
            "action": action,
            "modifications_actioned": len(pending_mods),
            "approval_status": review.approval_status
        }

        if garmin_results:
            result["garmin_sync"] = garmin_results

        return result

    def _action_single_modification(self, db, review_id, mod_index, action):
        """Approve or reject a single modification within a review."""
        from database.models import Athlete, DailyReview, PlanAdjustment
        from analyst.plan_manager import TrainingPlanManager

        athlete = db.query(Athlete).first()
        if not athlete:
            raise ValueError("No athlete found")

        review = db.query(DailyReview).filter(
            DailyReview.id == review_id,
            DailyReview.athlete_id == athlete.id
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
        mod["actioned_at"] = datetime.utcnow().isoformat()

        if action == "approve":
            # Apply this single modification
            garmin_success = False
            try:
                manager = TrainingPlanManager(db, athlete.id)
                garmin_results = manager.apply_approved_modifications([mod], sync_to_garmin=True)
                result["garmin_sync"] = garmin_results

                # Check if Garmin sync was successful (no errors and something was synced or applied)
                if garmin_results:
                    has_errors = bool(garmin_results.get("garmin_failed"))
                    has_applied = bool(garmin_results.get("applied"))
                    garmin_success = has_applied and not has_errors

                # Create PlanAdjustment record for audit trail
                plan_id = manager._ensure_training_plan_exists()
                plan_adj = PlanAdjustment(
                    plan_id=plan_id,
                    review_id=review.id,
                    adjustment_date=get_eastern_today(),
                    adjustment_type=mod.get("type", "unknown"),
                    reasoning=mod.get("reason", ""),
                    changes=json.dumps(mod)
                )
                db.add(plan_adj)
            except Exception as e:
                result["garmin_sync"] = {"error": str(e)}

            # Set status based on Garmin sync result
            mod["status"] = "updated" if garmin_success else "approved"
        else:
            mod["status"] = "rejected"

        # Update the review with modified adjustments
        review.proposed_adjustments = json.dumps(adjustments)

        # Recalculate overall review status
        new_review_status = TrainingPlanManager.calculate_review_status(adjustments)
        review.approval_status = new_review_status

        # If all modifications have been actioned, mark the timestamp
        if new_review_status in ("approved", "rejected"):
            review.approved_at = datetime.utcnow()

        db.commit()

        result["new_review_status"] = new_review_status
        return result

    def _run_evaluation(self, db, user_context=None):
        """Run AI evaluation with optional user context."""
        from database.models import Athlete

        athlete = db.query(Athlete).first()
        if not athlete:
            return {"error": "No athlete found"}

        goals_data = json.loads(athlete.goals) if athlete.goals else {}
        plan_info = goals_data.get("training_plan", {})

        if not plan_info.get("start_date"):
            return {"error": "Plan not initialized"}

        # Try to use the plan manager for full evaluation
        try:
            from analyst.plan_manager import TrainingPlanManager
            manager = TrainingPlanManager(db, athlete.id)
            results = manager.run_nightly_evaluation(user_context=user_context)
            return results
        except Exception as e:
            return {
                "error": f"Evaluation failed: {str(e)}",
                "note": "AI evaluation requires OpenAI API key and may not work in serverless environment"
            }
