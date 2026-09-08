"""FastAPI dependencies: authentication, tenant scoping, RBAC."""
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends, HTTPException, Request

from app.core.db import get_db
from app.core.permissions import (
    has_permission,
    is_platform_role,
    permissions_for,
)
from app.core.security import decode_token
import jwt


async def _extract_token(request: Request) -> str:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return token


async def get_current_user(request: Request) -> dict:
    token = await _extract_token(request)
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    try:
        oid = ObjectId(payload["sub"])
    except (InvalidId, KeyError):
        raise HTTPException(status_code=401, detail="Invalid token subject")

    user = await get_db().users.find_one({"_id": oid})
    if not user or user.get("status") != "active":
        raise HTTPException(status_code=401, detail="User not found or disabled")

    user["id"] = str(user.pop("_id"))
    user.pop("password_hash", None)
    return user


def require_permission(*required: str):
    """Dependency factory: authorize if user has ALL listed permissions."""

    async def _dep(user: dict = Depends(get_current_user)) -> dict:
        role = user.get("role", "")
        allowed = permissions_for(role) | set(user.get("extra_permissions", []))
        missing = [p for p in required if p not in allowed]
        if missing:
            raise HTTPException(
                status_code=403,
                detail=f"Missing permission(s): {', '.join(missing)}",
            )
        return user

    return _dep


def require_platform_admin():
    async def _dep(user: dict = Depends(get_current_user)) -> dict:
        if not is_platform_role(user.get("role", "")):
            raise HTTPException(status_code=403, detail="Platform admin only")
        return user

    return _dep


def require_tenant_user():
    """Ensures the user belongs to a tenant AND scopes requests to their tenant.

    Returns a tuple (user, tenant_id).  Rejects platform admins by default —
    platform admins have their own routes.
    """

    async def _dep(user: dict = Depends(get_current_user)) -> dict:
        if is_platform_role(user.get("role", "")):
            raise HTTPException(status_code=403, detail="Tenant users only")
        if not user.get("tenant_id"):
            raise HTTPException(status_code=403, detail="No tenant assignment")
        return user

    return _dep


def enforce_tenant(user: dict, tenant_id: str | None) -> str:
    """Return the tenant_id a tenant-user is allowed to act on.

    - Platform superadmin may act on any tenant_id (must be provided).
    - Tenant users are always locked to their own tenant_id.
    """
    if is_platform_role(user.get("role", "")):
        if not tenant_id:
            raise HTTPException(status_code=400, detail="tenant_id is required")
        return tenant_id
    own = user.get("tenant_id")
    if tenant_id is not None and tenant_id != own:
        raise HTTPException(status_code=403, detail="Cross-tenant access denied")
    return own
