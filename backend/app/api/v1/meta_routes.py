"""Health and metadata endpoints."""
from fastapi import APIRouter

from app.core.db import get_db
from app.core.permissions import ALL_PERMISSIONS, ALL_ROLES

router = APIRouter(tags=["meta"])


@router.get("/health")
async def health():
    try:
        await get_db().command("ping")
        db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": "up" if db_ok else "down"}


@router.get("/meta")
async def meta():
    return {
        "product": "School OS",
        "version": "0.1.0-foundation",
        "roles": ALL_ROLES,
        "permissions": ALL_PERMISSIONS,
    }
