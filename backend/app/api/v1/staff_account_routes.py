"""Stabilization Workstream B — Employee ↔ login User linking.

Canonical identities: Employee (HR record) · User (login) · TeacherAssignment
(academic allocation, keyed by teacher_user_id). Linking never creates a
second person record; it only joins the two existing rows and back-fills
employee_id on teacher assignments + timetable slots.
"""
import re
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from app.core.db import get_db
from app.core.deps import require_permission
from app.core.permissions import (
    ALL_ROLES, P_STAFF_UPDATE, P_STAFF_VIEW, P_USER_CREATE, P_USER_VIEW,
    ROLE_PLATFORM_SUPERADMIN, ROLE_SCHOOL_OWNER,
)
from app.core.security import hash_password
from app.models.user import User
from app.services.audit_service import log_event

router = APIRouter(prefix="/school/staff", tags=["staff-accounts"])

ASSIGNABLE_ROLES = [r for r in ALL_ROLES if r not in {ROLE_PLATFORM_SUPERADMIN, ROLE_SCHOOL_OWNER, "parent", "student"}]


def _oid(v: str) -> ObjectId:
    try: return ObjectId(v)
    except InvalidId: raise HTTPException(status_code=404, detail="Not found")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _user_summary(u: dict | None) -> dict | None:
    if not u: return None
    return {"id": str(u["_id"]), "email": u.get("email"), "full_name": u.get("full_name"),
            "role": u.get("role"), "status": u.get("status", "active")}


def _emp_name(e: dict) -> str:
    return " ".join(x for x in [e.get("first_name"), e.get("last_name")] if x).strip()


async def _get_emp(db, tid: str, eid: str) -> dict:
    e = await db.employees.find_one({"_id": _oid(eid), "tenant_id": tid})
    if not e: raise HTTPException(status_code=404, detail="Employee not found")
    return e


def _norm(s: str | None) -> str:
    return re.sub(r"[^a-z]", "", (s or "").lower())


def _score(emp: dict, u: dict) -> int:
    score = 0
    email = (u.get("email") or "").lower()
    local = _norm(email.split("@")[0])
    if emp.get("email_personal") and emp["email_personal"].lower() == email:
        score += 100
    full = " ".join(x for x in [emp.get("first_name"), emp.get("middle_name"), emp.get("last_name")] if x)
    if _norm(full) and _norm(full) == _norm(u.get("full_name")):
        score += 100
    user_words = {_norm(w) for w in re.split(r"[\s.]+", u.get("full_name") or "")}
    for w in re.split(r"[\s.]+", full):
        tok = _norm(w)
        if len(tok) >= 3 and (tok in user_words or tok in local):
            score += 30
    return score


async def _unlinked_users(db, tid: str) -> list[dict]:
    linked = {e["user_id"] for e in await db.employees.find(
        {"tenant_id": tid, "user_id": {"$ne": None}}, {"user_id": 1}).to_list(5000)}
    users = await db.users.find({"tenant_id": tid, "role": {"$nin": [ROLE_SCHOOL_OWNER, "parent", "student"]}}).to_list(5000)
    return [u for u in users if str(u["_id"]) not in linked]


async def _suggest(db, tid: str, emp: dict, pool: list[dict] | None = None) -> list[dict]:
    pool = pool if pool is not None else await _unlinked_users(db, tid)
    ranked = sorted(((_score(emp, u), u) for u in pool), key=lambda x: -x[0])
    return [{**_user_summary(u), "match_score": s} for s, u in ranked if s > 0][:3]


async def link_employee_user(db, tid: str, emp: dict, uid: str, actor: dict, request: Request | None) -> dict:
    """Join an Employee to an existing User. Enforces 1:1 and back-fills references."""
    u = await db.users.find_one({"_id": _oid(uid), "tenant_id": tid})
    if not u: raise HTTPException(status_code=400, detail="user_id not found")
    if u.get("role") in {"parent", "student"}:
        raise HTTPException(status_code=400, detail={"code": "role_not_linkable",
                            "message": f"A {u.get('role')} login cannot be linked to an employee"})
    eid = str(emp["_id"])
    if emp.get("user_id") == uid:
        return emp
    if emp.get("user_id"):
        raise HTTPException(status_code=409, detail={"code": "employee_already_linked",
                            "message": "This employee already has a login. Unlink it first."})
    other = await db.employees.find_one({"tenant_id": tid, "user_id": uid, "_id": {"$ne": emp["_id"]}})
    if other:
        raise HTTPException(status_code=409, detail={"code": "user_already_linked",
                            "message": f"This login is already linked to {_emp_name(other)} ({other.get('employee_code')})"})
    await db.employees.update_one({"_id": emp["_id"]}, {"$set": {"user_id": uid, "updated_at": _now()}})
    await db.users.update_one({"_id": u["_id"]}, {"$set": {"employee_id": eid}})
    ta = await db.teacher_assignments.update_many({"tenant_id": tid, "teacher_user_id": uid}, {"$set": {"employee_id": eid}})
    ts = await db.timetable_slots.update_many({"tenant_id": tid, "teacher_user_id": uid}, {"$set": {"teacher_employee_id": eid}})
    await log_event(action="staff.employee.account.link", resource="employee", resource_id=eid,
                    tenant_id=tid, actor=actor, request=request,
                    new_value={"user_id": uid, "email": u.get("email"),
                               "assignments_backfilled": ta.modified_count, "slots_backfilled": ts.modified_count})
    return await db.employees.find_one({"_id": emp["_id"]})


class LinkIn(BaseModel):
    user_id: str


class CreateAccountIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str | None = None
    full_name: str | None = None


@router.get("/employees/{eid}/account")
async def get_employee_account(eid: str, user: dict = Depends(require_permission(P_STAFF_VIEW))):
    db = get_db(); tid = user["tenant_id"]
    emp = await _get_emp(db, tid, eid)
    linked = await db.users.find_one({"_id": _oid(emp["user_id"]), "tenant_id": tid}) if emp.get("user_id") else None
    assignments = await db.teacher_assignments.count_documents({"tenant_id": tid, "teacher_user_id": emp["user_id"]}) if linked else 0
    return {
        "employee_id": eid, "linked_user": _user_summary(linked), "teacher_assignment_count": assignments,
        "suggestions": [] if linked else await _suggest(db, tid, emp),
        "assignable_roles": ASSIGNABLE_ROLES,
        "default_role": "teacher" if emp.get("is_teaching_staff") else "school_admin",
    }


@router.post("/employees/{eid}/account/link")
async def link_account(eid: str, payload: LinkIn, request: Request,
                       user: dict = Depends(require_permission(P_STAFF_UPDATE, P_USER_VIEW))):
    db = get_db(); tid = user["tenant_id"]
    emp = await _get_emp(db, tid, eid)
    emp = await link_employee_user(db, tid, emp, payload.user_id, user, request)
    return {"ok": True, "employee_id": eid, "user_id": emp["user_id"]}


@router.post("/employees/{eid}/account/create", status_code=201)
async def create_account(eid: str, payload: CreateAccountIn, request: Request,
                         user: dict = Depends(require_permission(P_STAFF_UPDATE, P_USER_CREATE))):
    db = get_db(); tid = user["tenant_id"]
    emp = await _get_emp(db, tid, eid)
    if emp.get("user_id"):
        raise HTTPException(status_code=409, detail={"code": "employee_already_linked", "message": "This employee already has a login"})
    role = payload.role or ("teacher" if emp.get("is_teaching_staff") else "school_admin")
    if role not in ASSIGNABLE_ROLES:
        raise HTTPException(status_code=400, detail=f"Allowed roles: {ASSIGNABLE_ROLES}")
    email = payload.email.lower()
    existing = await db.users.find_one({"tenant_id": tid, "email": email})
    if existing:
        raise HTTPException(status_code=409, detail={"code": "email_in_use", "user_id": str(existing["_id"]),
                            "message": "A login with this email already exists — link it instead of creating a duplicate"})
    doc = User(tenant_id=tid, email=email, password_hash=hash_password(payload.password),
               full_name=payload.full_name or _emp_name(emp) or email, role=role).to_mongo()
    res = await db.users.insert_one(doc)
    await log_event(action="user.create", resource="user", resource_id=str(res.inserted_id), tenant_id=tid,
                    actor=user, request=request, new_value={"email": email, "role": role, "employee_id": eid})
    await link_employee_user(db, tid, emp, str(res.inserted_id), user, request)
    return {"ok": True, "employee_id": eid, "user": _user_summary(await db.users.find_one({"_id": res.inserted_id}))}


@router.post("/employees/{eid}/account/unlink")
async def unlink_account(eid: str, request: Request, user: dict = Depends(require_permission(P_STAFF_UPDATE))):
    db = get_db(); tid = user["tenant_id"]
    emp = await _get_emp(db, tid, eid)
    uid = emp.get("user_id")
    if not uid:
        raise HTTPException(status_code=409, detail={"code": "not_linked", "message": "Employee has no linked login"})
    await db.employees.update_one({"_id": emp["_id"]}, {"$set": {"user_id": None, "updated_at": _now()}})
    await db.users.update_one({"_id": _oid(uid), "tenant_id": tid}, {"$unset": {"employee_id": ""}})
    await db.teacher_assignments.update_many({"tenant_id": tid, "teacher_user_id": uid}, {"$set": {"employee_id": None}})
    await db.timetable_slots.update_many({"tenant_id": tid, "teacher_user_id": uid}, {"$set": {"teacher_employee_id": None}})
    await log_event(action="staff.employee.account.unlink", resource="employee", resource_id=eid,
                    tenant_id=tid, actor=user, request=request, old_value={"user_id": uid})
    return {"ok": True}


@router.get("/account-links")
async def account_links(user: dict = Depends(require_permission(P_STAFF_VIEW, P_USER_VIEW))):
    """Reconciliation view: employees without logins (with suggested matches) and logins without employees."""
    db = get_db(); tid = user["tenant_id"]
    emps = await db.employees.find({"tenant_id": tid, "user_id": None,
                                    "status": {"$nin": ["resigned", "terminated", "retired"]}}).sort("first_name", 1).to_list(2000)
    pool = await _unlinked_users(db, tid)
    rows = [{"employee_id": str(e["_id"]), "employee_code": e.get("employee_code"), "name": _emp_name(e),
             "is_teaching_staff": e.get("is_teaching_staff", False),
             "suggestions": await _suggest(db, tid, e, pool)} for e in emps]
    linked_count = await db.employees.count_documents({"tenant_id": tid, "user_id": {"$ne": None}})
    return {"unlinked_employees": rows, "unlinked_users": [_user_summary(u) for u in pool], "linked_count": linked_count}
