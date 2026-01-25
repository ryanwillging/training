"""
API routes package.
"""

from api.routes.import_routes import router as import_router
from api.routes.metrics_routes import router as metrics_router
from api.routes.reports import router as reports_router
from api.routes.plan import router as plan_router
from api.routes.wellness_routes import router as wellness_router

__all__ = ["import_router", "metrics_router", "reports_router", "plan_router", "wellness_router"]
