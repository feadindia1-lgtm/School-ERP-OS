"""Aggregate v1 routers."""
from fastapi import APIRouter

from app.api.v1 import (
    admission_routes, auth_routes, crm_routes, meta_routes, platform_routes, school_routes,
)

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(meta_routes.router)
api_v1.include_router(auth_routes.router)
api_v1.include_router(platform_routes.router)
api_v1.include_router(school_routes.router)
api_v1.include_router(crm_routes.router)
api_v1.include_router(admission_routes.router)
