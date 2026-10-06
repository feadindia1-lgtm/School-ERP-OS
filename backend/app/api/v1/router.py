"""Aggregate v1 routers."""
from fastapi import APIRouter

from app.api.v1 import (
    academic_routes, admission_routes, attendance_routes, auth_routes,
    crm_routes, meta_routes, platform_routes, school_routes, staff_routes,
    student_routes,
)

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(meta_routes.router)
api_v1.include_router(auth_routes.router)
api_v1.include_router(platform_routes.router)
api_v1.include_router(school_routes.router)
api_v1.include_router(crm_routes.router)
api_v1.include_router(admission_routes.router)
api_v1.include_router(student_routes.router)
api_v1.include_router(academic_routes.router)
api_v1.include_router(staff_routes.router)
api_v1.include_router(attendance_routes.router)
