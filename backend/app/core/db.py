"""MongoDB client shared across the application."""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGO_URL)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client()[settings.DB_NAME]


async def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


async def ensure_indexes() -> None:
    db = get_db()
    # Users: unique per email within a tenant scope (platform users have tenant_id=None)
    await db.users.create_index(
        [("email", 1), ("tenant_id", 1)], unique=True, name="uniq_email_per_tenant"
    )
    await db.users.create_index("tenant_id")
    await db.tenants.create_index("slug", unique=True)
    await db.audit_logs.create_index([("tenant_id", 1), ("created_at", -1)])
    await db.audit_logs.create_index("actor_id")
    await db.login_attempts.create_index("identifier")
    await db.password_reset_tokens.create_index(
        "expires_at", expireAfterSeconds=0
    )
    await db.refresh_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.refresh_tokens.create_index("jti", unique=True)
