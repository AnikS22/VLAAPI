"""Admin API routers."""

from src.api.routers.admin.stats import router as stats_router
from src.api.routers.admin.customers import router as customers_router
from src.api.routers.admin.safety import router as safety_router
from src.api.routers.admin.monitoring import router as monitoring_router

__all__ = ["stats_router", "customers_router", "safety_router", "monitoring_router"]
