"""Seed / update the platform super admin user on startup."""
import logging

from app.core.config import settings
from app.core.db import get_db
from app.core.permissions import ROLE_PLATFORM_SUPERADMIN
from app.core.security import hash_password, verify_password
from app.models.user import User

logger = logging.getLogger(__name__)


async def seed_platform_admin() -> None:
    db = get_db()
    email = settings.PLATFORM_SUPERADMIN_EMAIL.lower()
    existing = await db.users.find_one({"email": email, "tenant_id": None})
    if existing is None:
        doc = User(
            tenant_id=None,
            email=email,
            password_hash=hash_password(settings.PLATFORM_SUPERADMIN_PASSWORD),
            full_name="Platform Super Admin",
            role=ROLE_PLATFORM_SUPERADMIN,
        ).to_mongo()
        await db.users.insert_one(doc)
        logger.info("Seeded platform super admin: %s", email)
        return
    if not verify_password(settings.PLATFORM_SUPERADMIN_PASSWORD, existing["password_hash"]):
        await db.users.update_one(
            {"_id": existing["_id"]},
            {"$set": {"password_hash": hash_password(settings.PLATFORM_SUPERADMIN_PASSWORD)}},
        )
        logger.info("Rotated platform super admin password: %s", email)
