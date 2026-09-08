"""Authentication endpoints: register-school, login, logout, refresh, me."""
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response
import jwt

from app.api.v1.schemas import (
    AuthResponse,
    LoginRequest,
    RegisterSchoolRequest,
    TenantOut,
    UserOut,
)
from app.core.config import settings
from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.permissions import (
    ROLE_SCHOOL_OWNER,
    is_platform_role,
    permissions_for,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.tenant import Tenant
from app.models.user import User
from app.services.audit_service import log_event

router = APIRouter(prefix="/auth", tags=["auth"])

LOCKOUT_MINUTES = 15
MAX_ATTEMPTS = 5


def _set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    response.set_cookie(
        "access_token", access, httponly=True, secure=True, samesite="none",
        max_age=settings.ACCESS_TOKEN_MINUTES * 60, path="/",
    )
    response.set_cookie(
        "refresh_token", refresh, httponly=True, secure=True, samesite="none",
        max_age=settings.REFRESH_TOKEN_DAYS * 86400, path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


def _user_to_out(u: dict, tenant_id: str | None = None) -> UserOut:
    role = u.get("role", "")
    perms = sorted(permissions_for(role) | set(u.get("extra_permissions", [])))
    return UserOut(
        id=u["id"],
        email=u["email"],
        full_name=u["full_name"],
        role=role,
        tenant_id=u.get("tenant_id") if tenant_id is None else tenant_id,
        status=u.get("status", "active"),
        permissions=perms,
    )


def _tenant_to_out(t: dict) -> TenantOut:
    return TenantOut(
        id=str(t["_id"]),
        name=t["name"],
        slug=t["slug"],
        short_name=t.get("short_name"),
        school_code=t.get("school_code"),
        board=t.get("board"),
        school_type=t.get("school_type"),
        contact_email=t["contact_email"],
        country=t.get("country"),
        plan=t.get("plan", "trial"),
        status=t.get("status", "active"),
        contact=t.get("contact") or {},
        academic=t.get("academic") or {},
        branding=t.get("branding") or {},
        modules=t.get("modules") or {},
        trial_ends_at=t.get("trial_ends_at"),
        subscription_started_at=t.get("subscription_started_at"),
        created_at=(
            datetime.fromisoformat(t["created_at"])
            if isinstance(t.get("created_at"), str)
            else t.get("created_at") or datetime.now(timezone.utc)
        ),
    )


@router.post("/register-school", response_model=AuthResponse, status_code=201)
async def register_school(payload: RegisterSchoolRequest, request: Request, response: Response):
    db = get_db()

    if await db.tenants.find_one({"slug": payload.slug}):
        raise HTTPException(status_code=409, detail="Slug already in use")

    tenant = Tenant(
        name=payload.school_name,
        slug=payload.slug,
        contact_email=payload.contact_email,
        country=payload.country,
    )
    tenant_res = await db.tenants.insert_one(tenant.to_mongo())
    tenant_id = str(tenant_res.inserted_id)

    owner_email = payload.owner_email.lower()
    if await db.users.find_one({"email": owner_email, "tenant_id": tenant_id}):
        raise HTTPException(status_code=409, detail="Owner email already exists for this school")

    owner = User(
        tenant_id=tenant_id,
        email=owner_email,
        password_hash=hash_password(payload.owner_password),
        full_name=payload.owner_full_name,
        role=ROLE_SCHOOL_OWNER,
    )
    owner_res = await db.users.insert_one(owner.to_mongo())
    owner_id = str(owner_res.inserted_id)

    access = create_access_token(user_id=owner_id, tenant_id=tenant_id, role=ROLE_SCHOOL_OWNER)
    refresh, jti, expires = create_refresh_token(user_id=owner_id, tenant_id=tenant_id)
    await db.refresh_tokens.insert_one({
        "jti": jti, "user_id": owner_id, "tenant_id": tenant_id,
        "expires_at": expires,
    })
    _set_auth_cookies(response, access, refresh)

    tenant_doc = await db.tenants.find_one({"_id": tenant_res.inserted_id})
    actor = {"id": owner_id, "email": owner_email, "role": ROLE_SCHOOL_OWNER}
    await log_event(
        action="tenant.create", resource="tenant", resource_id=tenant_id,
        tenant_id=tenant_id, actor=actor, request=request,
        new_value={"name": payload.school_name, "slug": payload.slug},
    )
    await log_event(
        action="auth.register", resource="user", resource_id=owner_id,
        tenant_id=tenant_id, actor=actor, request=request,
    )

    user_out = _user_to_out({"id": owner_id, **owner.model_dump(exclude={"id"})}, tenant_id)
    return AuthResponse(user=user_out, tenant=_tenant_to_out(tenant_doc))


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, request: Request, response: Response):
    db = get_db()
    email = payload.email.lower()

    client = request.client
    xff = request.headers.get("x-forwarded-for")
    ip = (xff.split(",")[0].strip() if xff else (client.host if client else "0.0.0.0"))
    identifier = f"{ip}:{email}"

    lockout = await db.login_attempts.find_one({"identifier": identifier})
    if lockout and lockout.get("locked_until"):
        locked_until = lockout["locked_until"]
        if isinstance(locked_until, str):
            locked_until = datetime.fromisoformat(locked_until)
        if locked_until.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
            raise HTTPException(status_code=429, detail="Too many failed attempts, try again later")

    query: dict = {"email": email}
    if payload.tenant_slug:
        t = await db.tenants.find_one({"slug": payload.tenant_slug})
        if not t:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        query["tenant_id"] = str(t["_id"])

    users = await db.users.find(query).to_list(5)
    user = None
    for u in users:
        if verify_password(payload.password, u.get("password_hash", "")):
            user = u
            break

    if user is None or user.get("status") != "active":
        await db.login_attempts.update_one(
            {"identifier": identifier},
            {"$inc": {"attempts": 1}, "$set": {"last_attempt": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
        attempts = await db.login_attempts.find_one({"identifier": identifier})
        if attempts and attempts.get("attempts", 0) >= MAX_ATTEMPTS:
            from datetime import timedelta
            await db.login_attempts.update_one(
                {"identifier": identifier},
                {"$set": {"locked_until": (datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()}},
            )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    await db.login_attempts.delete_one({"identifier": identifier})

    user_id = str(user["_id"])
    tenant_id = user.get("tenant_id")
    role = user["role"]
    access = create_access_token(user_id=user_id, tenant_id=tenant_id, role=role)
    refresh, jti, expires = create_refresh_token(user_id=user_id, tenant_id=tenant_id)
    await db.refresh_tokens.insert_one({
        "jti": jti, "user_id": user_id, "tenant_id": tenant_id, "expires_at": expires,
    })
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login_at": datetime.now(timezone.utc).isoformat()}},
    )
    _set_auth_cookies(response, access, refresh)

    actor = {"id": user_id, "email": email, "role": role}
    await log_event(
        action="auth.login", resource="user", resource_id=user_id,
        tenant_id=tenant_id, actor=actor, request=request,
    )

    tenant_out = None
    if tenant_id:
        t = await db.tenants.find_one({"_id": ObjectId(tenant_id)})
        if t:
            tenant_out = _tenant_to_out(t)

    user["id"] = user_id
    user.pop("_id", None)
    return AuthResponse(user=_user_to_out(user, tenant_id), tenant=tenant_out)


@router.post("/logout")
async def logout(request: Request, response: Response, user: dict = Depends(get_current_user)):
    refresh_cookie = request.cookies.get("refresh_token")
    if refresh_cookie:
        try:
            payload = decode_token(refresh_cookie)
            await get_db().refresh_tokens.delete_one({"jti": payload.get("jti")})
        except jwt.InvalidTokenError:
            pass
    _clear_auth_cookies(response)
    await log_event(
        action="auth.logout", resource="user", resource_id=user["id"],
        tenant_id=user.get("tenant_id"), actor=user, request=request,
    )
    return {"ok": True}


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    db = get_db()
    if not await db.refresh_tokens.find_one({"jti": payload.get("jti")}):
        raise HTTPException(status_code=401, detail="Refresh token revoked")

    user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
    if not user or user.get("status") != "active":
        raise HTTPException(status_code=401, detail="User inactive")

    access = create_access_token(
        user_id=str(user["_id"]), tenant_id=user.get("tenant_id"), role=user["role"],
    )
    response.set_cookie(
        "access_token", access, httponly=True, secure=True, samesite="none",
        max_age=settings.ACCESS_TOKEN_MINUTES * 60, path="/",
    )
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(user: dict = Depends(get_current_user)):
    return _user_to_out(user, user.get("tenant_id"))


@router.get("/session", response_model=AuthResponse)
async def session(user: dict = Depends(get_current_user)):
    """Full session context: user, tenant (if any), impersonation info (if active)."""
    tenant_out = None
    if user.get("tenant_id"):
        t = await get_db().tenants.find_one({"_id": ObjectId(user["tenant_id"])})
        if t:
            tenant_out = _tenant_to_out(t)
    imp = None
    if user.get("impersonated_by"):
        plat = await get_db().users.find_one({"_id": ObjectId(user["impersonated_by"])})
        imp = {
            "impersonator_id": user["impersonated_by"],
            "impersonator_email": (plat or {}).get("email"),
            "reason": user.get("impersonation_reason"),
        }
    return AuthResponse(
        user=_user_to_out(user, user.get("tenant_id")),
        tenant=tenant_out,
        impersonation=imp,
    )
