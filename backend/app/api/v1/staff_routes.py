"""Staff Master + Leave Foundation — Prompt 5.

Routes:
- /school/staff/departments               [GET/POST]  · /{id} [GET/PATCH/DELETE]
- /school/staff/designations              [GET/POST]  · /{id} [GET/PATCH/DELETE]
- /school/staff/employees                 [GET/POST]  · /{id} [GET/PATCH/DELETE]
- /school/staff/employees/{id}/status     [POST]
- /school/staff/employees/{id}/documents  [GET/POST]  · /docs/{did} [DELETE]
- /school/staff/employees/{id}/qualifications [GET/POST] · /qualifications/{qid} [DELETE]
- /school/staff/leave-types               [GET/POST]  · /{id} [PATCH/DELETE]
- /school/staff/leave-balances            [GET]
- /school/staff/leave-balances/adjust     [POST]      (LEAVE_ADJUST)
- /school/staff/leave-applications        [GET/POST]  · /{id} [GET]
- /school/staff/leave-applications/{id}/approve [POST]
- /school/staff/leave-applications/{id}/reject  [POST]
- /school/staff/leave-applications/{id}/cancel  [POST]
- /school/staff/overview                  [GET]
"""
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr, Field

from app.core.db import get_db
from app.core.deps import require_permission
from app.core.permissions import (
    P_LEAVE_ADJUST, P_LEAVE_APPLY, P_LEAVE_APPROVE, P_LEAVE_BALANCE_VIEW,
    P_LEAVE_TYPE_MANAGE, P_LEAVE_VIEW, P_STAFF_CREATE, P_STAFF_DEPARTMENT_MANAGE,
    P_STAFF_DESIGNATION_MANAGE, P_STAFF_DOC_UPLOAD, P_STAFF_DOC_VIEW,
    P_STAFF_QUALIFICATION_MANAGE, P_STAFF_STATUS_MANAGE, P_STAFF_UPDATE,
    P_STAFF_VIEW,
)
from app.models.staff import (
    EMPLOYMENT_STATUSES, EMPLOYMENT_TYPES, LEAVE_ACCRUAL_FREQ,
    LEAVE_APPLICABLE_TO, LEAVE_STATUS, Department, Designation, Employee,
    EmployeeDocument, EmployeeQualification, LeaveAdjustment, LeaveApplication,
    LeaveBalance, LeaveType,
)
from app.services.audit_service import log_event
from app.services.numbering import next_number

router = APIRouter(prefix="/school/staff", tags=["staff"])


def _oid(v: str) -> ObjectId:
    try: return ObjectId(v)
    except InvalidId: raise HTTPException(status_code=404, detail="Not found")


def _out(d: dict) -> dict:
    d = dict(d); d["id"] = str(d.pop("_id")); return d


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _days_between(start: str, end: str) -> int:
    """Inclusive calendar-day count between two ISO dates."""
    a = datetime.fromisoformat(start).date()
    b = datetime.fromisoformat(end).date()
    return (b - a).days + 1


# ============================================================
# Departments
# ============================================================
class DepartmentIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=40)
    head_user_id: str | None = None
    description: str | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    head_user_id: str | None = None
    description: str | None = None


@router.get("/departments")
async def list_departments(user: dict = Depends(require_permission(P_STAFF_VIEW))):
    docs = await get_db().staff_departments.find({"tenant_id": user["tenant_id"]}).sort("name", 1).to_list(500)
    return [_out(d) for d in docs]


@router.post("/departments", status_code=201)
async def create_department(payload: DepartmentIn, request: Request, user: dict = Depends(require_permission(P_STAFF_DEPARTMENT_MANAGE))):
    db = get_db()
    if await db.staff_departments.find_one({"tenant_id": user["tenant_id"], "code": payload.code}):
        raise HTTPException(status_code=409, detail={"code": "duplicate_department", "message": "Department code exists"})
    doc = Department(tenant_id=user["tenant_id"], **payload.model_dump()).to_mongo()
    res = await db.staff_departments.insert_one(doc); doc["_id"] = res.inserted_id
    await log_event(action="staff.department.create", resource="staff_department",
                    resource_id=str(res.inserted_id), tenant_id=user["tenant_id"],
                    actor=user, request=request, new_value={"code": payload.code})
    return _out(doc)


@router.patch("/departments/{did}")
async def update_department(did: str, payload: DepartmentUpdate, request: Request, user: dict = Depends(require_permission(P_STAFF_DEPARTMENT_MANAGE))):
    db = get_db()
    old = await db.staff_departments.find_one({"_id": _oid(did), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Department not found")
    updates = payload.model_dump(exclude_none=True)
    if not updates: raise HTTPException(status_code=400, detail="No fields")
    if "code" in updates and updates["code"] != old["code"]:
        if await db.staff_departments.find_one({"tenant_id": user["tenant_id"], "code": updates["code"]}):
            raise HTTPException(status_code=409, detail="Department code exists")
    updates["updated_at"] = _now()
    await db.staff_departments.update_one({"_id": old["_id"]}, {"$set": updates})
    await log_event(action="staff.department.update", resource="staff_department",
                    resource_id=did, tenant_id=user["tenant_id"], actor=user, request=request,
                    new_value=updates)
    return _out(await db.staff_departments.find_one({"_id": old["_id"]}))


@router.delete("/departments/{did}")
async def delete_department(did: str, request: Request, user: dict = Depends(require_permission(P_STAFF_DEPARTMENT_MANAGE))):
    db = get_db()
    old = await db.staff_departments.find_one({"_id": _oid(did), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Department not found")
    if await db.employees.count_documents({"tenant_id": user["tenant_id"], "department_id": did}):
        raise HTTPException(status_code=409, detail={"code": "department_in_use", "message": "Employees reference this department"})
    await db.staff_departments.delete_one({"_id": old["_id"]})
    await log_event(action="staff.department.delete", resource="staff_department",
                    resource_id=did, tenant_id=user["tenant_id"], actor=user, request=request)
    return {"ok": True}


# ============================================================
# Designations
# ============================================================
class DesignationIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=40)
    department_id: str | None = None
    is_teaching: bool = False
    grade: str | None = None
    description: str | None = None


class DesignationUpdate(BaseModel):
    title: str | None = None
    code: str | None = None
    department_id: str | None = None
    is_teaching: bool | None = None
    grade: str | None = None
    description: str | None = None


@router.get("/designations")
async def list_designations(user: dict = Depends(require_permission(P_STAFF_VIEW))):
    docs = await get_db().staff_designations.find({"tenant_id": user["tenant_id"]}).sort("title", 1).to_list(500)
    return [_out(d) for d in docs]


@router.post("/designations", status_code=201)
async def create_designation(payload: DesignationIn, request: Request, user: dict = Depends(require_permission(P_STAFF_DESIGNATION_MANAGE))):
    db = get_db()
    if await db.staff_designations.find_one({"tenant_id": user["tenant_id"], "code": payload.code}):
        raise HTTPException(status_code=409, detail={"code": "duplicate_designation", "message": "Designation code exists"})
    if payload.department_id and not await db.staff_departments.find_one({"_id": _oid(payload.department_id), "tenant_id": user["tenant_id"]}):
        raise HTTPException(status_code=400, detail="department_id not found")
    doc = Designation(tenant_id=user["tenant_id"], **payload.model_dump()).to_mongo()
    res = await db.staff_designations.insert_one(doc); doc["_id"] = res.inserted_id
    await log_event(action="staff.designation.create", resource="staff_designation",
                    resource_id=str(res.inserted_id), tenant_id=user["tenant_id"],
                    actor=user, request=request, new_value={"code": payload.code})
    return _out(doc)


@router.patch("/designations/{did}")
async def update_designation(did: str, payload: DesignationUpdate, request: Request, user: dict = Depends(require_permission(P_STAFF_DESIGNATION_MANAGE))):
    db = get_db()
    old = await db.staff_designations.find_one({"_id": _oid(did), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Designation not found")
    updates = payload.model_dump(exclude_none=True)
    if not updates: raise HTTPException(status_code=400, detail="No fields")
    if "code" in updates and updates["code"] != old["code"]:
        if await db.staff_designations.find_one({"tenant_id": user["tenant_id"], "code": updates["code"]}):
            raise HTTPException(status_code=409, detail="Designation code exists")
    updates["updated_at"] = _now()
    await db.staff_designations.update_one({"_id": old["_id"]}, {"$set": updates})
    return _out(await db.staff_designations.find_one({"_id": old["_id"]}))


@router.delete("/designations/{did}")
async def delete_designation(did: str, request: Request, user: dict = Depends(require_permission(P_STAFF_DESIGNATION_MANAGE))):
    db = get_db()
    old = await db.staff_designations.find_one({"_id": _oid(did), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Designation not found")
    if await db.employees.count_documents({"tenant_id": user["tenant_id"], "designation_id": did}):
        raise HTTPException(status_code=409, detail={"code": "designation_in_use", "message": "Employees reference this designation"})
    await db.staff_designations.delete_one({"_id": old["_id"]})
    return {"ok": True}


# ============================================================
# Employees
# ============================================================
class EmployeeIn(BaseModel):
    employee_code: str | None = None       # optional override
    user_id: str | None = None
    first_name: str = Field(min_length=1, max_length=80)
    middle_name: str | None = None
    last_name: str | None = None
    preferred_name: str | None = None
    gender: str | None = None
    date_of_birth: str | None = None
    blood_group: str | None = None
    nationality: str | None = None
    photo_url: str | None = None
    mobile_primary: str | None = None
    mobile_secondary: str | None = None
    email_personal: EmailStr | None = None
    address: dict | None = None
    department_id: str | None = None
    designation_id: str | None = None
    employment_type: str = "full_time"
    joining_date: str | None = None
    probation_end_date: str | None = None
    confirmation_date: str | None = None
    reporting_to_employee_id: str | None = None
    biometric_id: str | None = None
    attendance_number: str | None = None
    is_teaching_staff: bool = False
    subjects_qualified: list[str] = Field(default_factory=list)
    classes_eligible: list[str] = Field(default_factory=list)
    emergency_contact: dict | None = None
    kyc: dict = Field(default_factory=dict)
    notes: str | None = None


class EmployeeUpdate(BaseModel):
    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None
    preferred_name: str | None = None
    gender: str | None = None
    date_of_birth: str | None = None
    blood_group: str | None = None
    nationality: str | None = None
    photo_url: str | None = None
    mobile_primary: str | None = None
    mobile_secondary: str | None = None
    email_personal: EmailStr | None = None
    address: dict | None = None
    department_id: str | None = None
    designation_id: str | None = None
    employment_type: str | None = None
    joining_date: str | None = None
    probation_end_date: str | None = None
    confirmation_date: str | None = None
    reporting_to_employee_id: str | None = None
    biometric_id: str | None = None
    attendance_number: str | None = None
    is_teaching_staff: bool | None = None
    subjects_qualified: list[str] | None = None
    classes_eligible: list[str] | None = None
    emergency_contact: dict | None = None
    kyc: dict | None = None
    notes: str | None = None
    user_id: str | None = None


class StatusChange(BaseModel):
    status: str
    reason: str | None = None
    effective_date: str | None = None
    exit_date: str | None = None
    exit_reason: str | None = None


@router.get("/employees")
async def list_employees(
    q: str | None = None,
    status: str | None = None,
    department_id: str | None = None,
    designation_id: str | None = None,
    is_teaching_staff: bool | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200),
    user: dict = Depends(require_permission(P_STAFF_VIEW)),
):
    import re
    query: dict = {"tenant_id": user["tenant_id"]}
    if status: query["status"] = status
    if department_id: query["department_id"] = department_id
    if designation_id: query["designation_id"] = designation_id
    if is_teaching_staff is not None: query["is_teaching_staff"] = is_teaching_staff
    if q:
        rx = {"$regex": re.escape(q), "$options": "i"}
        query["$or"] = [{"first_name": rx}, {"last_name": rx}, {"employee_code": rx}, {"mobile_primary": rx}, {"email_personal": rx}]
    db = get_db()
    total = await db.employees.count_documents(query)
    docs = await db.employees.find(query).sort("created_at", -1).skip((page-1)*page_size).limit(page_size).to_list(page_size)
    return {"items": [_out(d) for d in docs], "total": total, "page": page, "page_size": page_size}


@router.get("/overview")
async def staff_overview(user: dict = Depends(require_permission(P_STAFF_VIEW))):
    db = get_db()
    tid = user["tenant_id"]
    base = {"tenant_id": tid}
    total = await db.employees.count_documents(base)
    active = await db.employees.count_documents({**base, "status": "active"})
    teaching = await db.employees.count_documents({**base, "is_teaching_staff": True})
    on_leave = await db.employees.count_documents({**base, "status": "on_leave"})
    resigned = await db.employees.count_documents({**base, "status": {"$in": ["resigned", "terminated", "retired"]}})
    pending_leave = await db.leave_applications.count_documents({**base, "status": {"$in": ["pending", "approved_l1"]}})
    return {
        "total": total, "active": active, "teaching": teaching,
        "non_teaching": total - teaching, "on_leave": on_leave,
        "resigned": resigned, "pending_leave_applications": pending_leave,
    }


@router.post("/employees", status_code=201)
async def create_employee(payload: EmployeeIn, request: Request, user: dict = Depends(require_permission(P_STAFF_CREATE))):
    db = get_db()
    if payload.department_id and not await db.staff_departments.find_one({"_id": _oid(payload.department_id), "tenant_id": user["tenant_id"]}):
        raise HTTPException(status_code=400, detail="department_id not found")
    if payload.designation_id and not await db.staff_designations.find_one({"_id": _oid(payload.designation_id), "tenant_id": user["tenant_id"]}):
        raise HTTPException(status_code=400, detail="designation_id not found")
    if payload.user_id and not await db.users.find_one({"_id": _oid(payload.user_id), "tenant_id": user["tenant_id"]}):
        raise HTTPException(status_code=400, detail="user_id not found")
    if payload.employment_type not in EMPLOYMENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Allowed employment_type: {EMPLOYMENT_TYPES}")
    if payload.employee_code:
        if await db.employees.find_one({"tenant_id": user["tenant_id"], "employee_code": payload.employee_code}):
            raise HTTPException(status_code=409, detail={"code": "duplicate_employee_code", "message": "Employee code exists"})
        code = payload.employee_code
    else:
        code = await next_number(user["tenant_id"], "EMP", width=4)
    body = payload.model_dump(exclude={"employee_code"})
    doc = Employee(tenant_id=user["tenant_id"], employee_code=code, **body).to_mongo()
    doc["status"] = "active"
    doc["status_effective_date"] = _now()
    res = await db.employees.insert_one(doc); doc["_id"] = res.inserted_id
    # If linked to a login user, back-reference (idempotent)
    if payload.user_id:
        await db.users.update_one({"_id": _oid(payload.user_id)}, {"$set": {"employee_id": str(res.inserted_id)}})
    await log_event(action="staff.employee.create", resource="employee",
                    resource_id=str(res.inserted_id), tenant_id=user["tenant_id"],
                    actor=user, request=request, new_value={"employee_code": code})
    return _out(doc)


@router.get("/employees/{eid}")
async def get_employee(eid: str, user: dict = Depends(require_permission(P_STAFF_VIEW))):
    d = await get_db().employees.find_one({"_id": _oid(eid), "tenant_id": user["tenant_id"]})
    if not d: raise HTTPException(status_code=404, detail="Employee not found")
    return _out(d)


@router.patch("/employees/{eid}")
async def update_employee(eid: str, payload: EmployeeUpdate, request: Request, user: dict = Depends(require_permission(P_STAFF_UPDATE))):
    db = get_db()
    old = await db.employees.find_one({"_id": _oid(eid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Employee not found")
    updates = payload.model_dump(exclude_none=True)
    if not updates: raise HTTPException(status_code=400, detail="No fields")
    if updates.get("employment_type") and updates["employment_type"] not in EMPLOYMENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Allowed employment_type: {EMPLOYMENT_TYPES}")
    if updates.get("department_id") and not await db.staff_departments.find_one({"_id": _oid(updates["department_id"]), "tenant_id": user["tenant_id"]}):
        raise HTTPException(status_code=400, detail="department_id not found")
    if updates.get("designation_id") and not await db.staff_designations.find_one({"_id": _oid(updates["designation_id"]), "tenant_id": user["tenant_id"]}):
        raise HTTPException(status_code=400, detail="designation_id not found")
    if updates.get("user_id") and not await db.users.find_one({"_id": _oid(updates["user_id"]), "tenant_id": user["tenant_id"]}):
        raise HTTPException(status_code=400, detail="user_id not found")
    updates["updated_at"] = _now()
    await db.employees.update_one({"_id": old["_id"]}, {"$set": updates})
    if updates.get("user_id"):
        await db.users.update_one({"_id": _oid(updates["user_id"])}, {"$set": {"employee_id": eid}})
    await log_event(action="staff.employee.update", resource="employee",
                    resource_id=eid, tenant_id=user["tenant_id"], actor=user, request=request,
                    old_value={k: old.get(k) for k in updates if k != "updated_at"},
                    new_value={k: v for k, v in updates.items() if k != "updated_at"})
    return _out(await db.employees.find_one({"_id": old["_id"]}))


@router.post("/employees/{eid}/status")
async def change_employee_status(eid: str, payload: StatusChange, request: Request, user: dict = Depends(require_permission(P_STAFF_STATUS_MANAGE))):
    if payload.status not in EMPLOYMENT_STATUSES:
        raise HTTPException(status_code=400, detail=f"Allowed status: {EMPLOYMENT_STATUSES}")
    db = get_db()
    old = await db.employees.find_one({"_id": _oid(eid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Employee not found")
    updates = {
        "status": payload.status, "status_reason": payload.reason,
        "status_effective_date": payload.effective_date or _now(),
        "updated_at": _now(),
    }
    if payload.status in {"resigned", "terminated", "retired"}:
        updates["exit_date"] = payload.exit_date or _now()
        updates["exit_reason"] = payload.exit_reason or payload.reason
    await db.employees.update_one({"_id": old["_id"]}, {"$set": updates})
    await log_event(action="staff.employee.status.change", resource="employee",
                    resource_id=eid, tenant_id=user["tenant_id"], actor=user, request=request,
                    old_value={"status": old.get("status")}, new_value={"status": payload.status},
                    metadata={"reason": payload.reason})
    return _out(await db.employees.find_one({"_id": old["_id"]}))


@router.delete("/employees/{eid}")
async def delete_employee(eid: str, request: Request, user: dict = Depends(require_permission(P_STAFF_STATUS_MANAGE))):
    """Soft-delete → status archived. Hard delete blocked."""
    db = get_db()
    old = await db.employees.find_one({"_id": _oid(eid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Employee not found")
    await db.employees.update_one({"_id": old["_id"]}, {"$set": {"status": "terminated", "exit_date": _now(), "updated_at": _now()}})
    await log_event(action="staff.employee.archive", resource="employee",
                    resource_id=eid, tenant_id=user["tenant_id"], actor=user, request=request)
    return {"ok": True}


# ============================================================
# Employee documents
# ============================================================
class DocIn(BaseModel):
    doc_type: str
    filename: str
    storage_key: str
    size_bytes: int | None = None
    mime_type: str | None = None
    notes: str | None = None


@router.get("/employees/{eid}/documents")
async def list_employee_docs(eid: str, user: dict = Depends(require_permission(P_STAFF_DOC_VIEW))):
    db = get_db()
    if not await db.employees.find_one({"_id": _oid(eid), "tenant_id": user["tenant_id"]}):
        raise HTTPException(status_code=404, detail="Employee not found")
    docs = await db.employee_documents.find({"tenant_id": user["tenant_id"], "employee_id": eid}).sort("created_at", -1).to_list(200)
    return [_out(d) for d in docs]


@router.post("/employees/{eid}/documents", status_code=201)
async def add_employee_doc(eid: str, payload: DocIn, request: Request, user: dict = Depends(require_permission(P_STAFF_DOC_UPLOAD))):
    db = get_db()
    if not await db.employees.find_one({"_id": _oid(eid), "tenant_id": user["tenant_id"]}):
        raise HTTPException(status_code=404, detail="Employee not found")
    doc = EmployeeDocument(
        tenant_id=user["tenant_id"], employee_id=eid,
        uploaded_by_user_id=user["id"], **payload.model_dump(),
    ).to_mongo()
    res = await db.employee_documents.insert_one(doc); doc["_id"] = res.inserted_id
    await log_event(action="staff.document.upload", resource="employee_document",
                    resource_id=str(res.inserted_id), tenant_id=user["tenant_id"],
                    actor=user, request=request, metadata={"employee_id": eid})
    return _out(doc)


@router.delete("/documents/{did}")
async def delete_employee_doc(did: str, request: Request, user: dict = Depends(require_permission(P_STAFF_DOC_UPLOAD))):
    db = get_db()
    old = await db.employee_documents.find_one({"_id": _oid(did), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Document not found")
    await db.employee_documents.delete_one({"_id": old["_id"]})
    await log_event(action="staff.document.delete", resource="employee_document",
                    resource_id=did, tenant_id=user["tenant_id"], actor=user, request=request)
    return {"ok": True}


# ============================================================
# Qualifications
# ============================================================
class QualIn(BaseModel):
    kind: str = "subject"                  # subject | degree | certification
    subject_id: str | None = None
    class_id: str | None = None
    degree_name: str | None = None
    institution: str | None = None
    year_of_completion: str | None = None
    grade: str | None = None
    notes: str | None = None


@router.get("/employees/{eid}/qualifications")
async def list_qualifications(eid: str, user: dict = Depends(require_permission(P_STAFF_VIEW))):
    db = get_db()
    if not await db.employees.find_one({"_id": _oid(eid), "tenant_id": user["tenant_id"]}):
        raise HTTPException(status_code=404, detail="Employee not found")
    docs = await db.employee_qualifications.find({"tenant_id": user["tenant_id"], "employee_id": eid}).sort("created_at", -1).to_list(200)
    return [_out(d) for d in docs]


@router.post("/employees/{eid}/qualifications", status_code=201)
async def add_qualification(eid: str, payload: QualIn, request: Request, user: dict = Depends(require_permission(P_STAFF_QUALIFICATION_MANAGE))):
    db = get_db()
    if not await db.employees.find_one({"_id": _oid(eid), "tenant_id": user["tenant_id"]}):
        raise HTTPException(status_code=404, detail="Employee not found")
    if payload.subject_id and not await db.subjects.find_one({"_id": _oid(payload.subject_id), "tenant_id": user["tenant_id"]}):
        raise HTTPException(status_code=400, detail="subject_id not found")
    if payload.class_id and not await db.academic_classes.find_one({"_id": _oid(payload.class_id), "tenant_id": user["tenant_id"]}):
        raise HTTPException(status_code=400, detail="class_id not found")
    doc = EmployeeQualification(tenant_id=user["tenant_id"], employee_id=eid, **payload.model_dump()).to_mongo()
    res = await db.employee_qualifications.insert_one(doc); doc["_id"] = res.inserted_id
    # Denormalise subject_id / class_id onto the Employee hint arrays
    if payload.kind == "subject":
        push_updates = {}
        if payload.subject_id: push_updates["subjects_qualified"] = payload.subject_id
        if payload.class_id: push_updates["classes_eligible"] = payload.class_id
        if push_updates:
            await db.employees.update_one({"_id": _oid(eid)}, {"$addToSet": push_updates, "$set": {"is_teaching_staff": True}})
    await log_event(action="staff.qualification.add", resource="employee_qualification",
                    resource_id=str(res.inserted_id), tenant_id=user["tenant_id"],
                    actor=user, request=request, metadata={"employee_id": eid})
    return _out(doc)


@router.delete("/qualifications/{qid}")
async def delete_qualification(qid: str, request: Request, user: dict = Depends(require_permission(P_STAFF_QUALIFICATION_MANAGE))):
    db = get_db()
    old = await db.employee_qualifications.find_one({"_id": _oid(qid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Qualification not found")
    await db.employee_qualifications.delete_one({"_id": old["_id"]})
    return {"ok": True}


# ============================================================
# Leave types
# ============================================================
LEAVE_PRESETS = [
    {"name": "Casual Leave", "code": "CL", "is_paid": True, "max_per_year": 12, "approval_steps": 1},
    {"name": "Sick Leave", "code": "SL", "is_paid": True, "max_per_year": 12, "approval_steps": 1, "requires_document": True},
    {"name": "Earned Leave", "code": "EL", "is_paid": True, "max_per_year": 21, "approval_steps": 2, "carry_forward": True, "carry_forward_max": 30},
    {"name": "Comp-Off", "code": "CO", "is_paid": True, "max_per_year": None, "approval_steps": 1},
    {"name": "Maternity Leave", "code": "ML", "is_paid": True, "max_per_year": 182, "approval_steps": 2, "applicable_to": "female"},
    {"name": "Paternity Leave", "code": "PL", "is_paid": True, "max_per_year": 15, "approval_steps": 1, "applicable_to": "male"},
    {"name": "Unpaid Leave", "code": "LWP", "is_paid": False, "max_per_year": None, "approval_steps": 2},
]


class LeaveTypeIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=20)
    is_paid: bool = True
    max_per_year: float | None = None
    accrual_frequency: str = "yearly"
    carry_forward: bool = False
    carry_forward_max: float | None = None
    applicable_to: str = "all"
    approval_steps: int = 1
    requires_document: bool = False
    description: str | None = None
    color: str | None = None


class LeaveTypeUpdate(BaseModel):
    name: str | None = None
    is_paid: bool | None = None
    max_per_year: float | None = None
    accrual_frequency: str | None = None
    carry_forward: bool | None = None
    carry_forward_max: float | None = None
    applicable_to: str | None = None
    approval_steps: int | None = None
    requires_document: bool | None = None
    description: str | None = None
    color: str | None = None
    is_active: bool | None = None


@router.get("/leave-types")
async def list_leave_types(user: dict = Depends(require_permission(P_LEAVE_VIEW))):
    docs = await get_db().leave_types.find({"tenant_id": user["tenant_id"]}).sort("code", 1).to_list(200)
    return {"items": [_out(d) for d in docs], "presets": LEAVE_PRESETS}


@router.post("/leave-types", status_code=201)
async def create_leave_type(payload: LeaveTypeIn, request: Request, user: dict = Depends(require_permission(P_LEAVE_TYPE_MANAGE))):
    db = get_db()
    if payload.accrual_frequency not in LEAVE_ACCRUAL_FREQ:
        raise HTTPException(status_code=400, detail=f"Allowed accrual: {LEAVE_ACCRUAL_FREQ}")
    if payload.applicable_to not in LEAVE_APPLICABLE_TO:
        raise HTTPException(status_code=400, detail=f"Allowed applicable_to: {LEAVE_APPLICABLE_TO}")
    if payload.approval_steps not in (1, 2):
        raise HTTPException(status_code=400, detail="approval_steps must be 1 or 2")
    if await db.leave_types.find_one({"tenant_id": user["tenant_id"], "code": payload.code}):
        raise HTTPException(status_code=409, detail={"code": "duplicate_leave_type", "message": "Leave type code exists"})
    doc = LeaveType(tenant_id=user["tenant_id"], **payload.model_dump()).to_mongo()
    res = await db.leave_types.insert_one(doc); doc["_id"] = res.inserted_id
    await log_event(action="staff.leave_type.create", resource="leave_type",
                    resource_id=str(res.inserted_id), tenant_id=user["tenant_id"],
                    actor=user, request=request, new_value={"code": payload.code})
    return _out(doc)


@router.patch("/leave-types/{ltid}")
async def update_leave_type(ltid: str, payload: LeaveTypeUpdate, request: Request, user: dict = Depends(require_permission(P_LEAVE_TYPE_MANAGE))):
    db = get_db()
    old = await db.leave_types.find_one({"_id": _oid(ltid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Leave type not found")
    updates = payload.model_dump(exclude_none=True)
    if not updates: raise HTTPException(status_code=400, detail="No fields")
    if updates.get("approval_steps") not in (None, 1, 2):
        raise HTTPException(status_code=400, detail="approval_steps must be 1 or 2")
    updates["updated_at"] = _now()
    await db.leave_types.update_one({"_id": old["_id"]}, {"$set": updates})
    return _out(await db.leave_types.find_one({"_id": old["_id"]}))


@router.delete("/leave-types/{ltid}")
async def delete_leave_type(ltid: str, user: dict = Depends(require_permission(P_LEAVE_TYPE_MANAGE))):
    db = get_db()
    old = await db.leave_types.find_one({"_id": _oid(ltid), "tenant_id": user["tenant_id"]})
    if not old: raise HTTPException(status_code=404, detail="Leave type not found")
    used = await db.leave_applications.count_documents({"tenant_id": user["tenant_id"], "leave_type_id": ltid})
    if used:
        # Soft-deactivate rather than delete
        await db.leave_types.update_one({"_id": old["_id"]}, {"$set": {"is_active": False, "updated_at": _now()}})
        return {"ok": True, "soft_deactivated": True}
    await db.leave_types.delete_one({"_id": old["_id"]})
    return {"ok": True}


# ============================================================
# Leave balances
# ============================================================
async def _ensure_balance(db, tid: str, employee_id: str, leave_type_id: str, year: str) -> dict:
    b = await db.leave_balances.find_one({
        "tenant_id": tid, "employee_id": employee_id,
        "leave_type_id": leave_type_id, "year": year,
    })
    if b: return b
    lt = await db.leave_types.find_one({"_id": _oid(leave_type_id), "tenant_id": tid})
    allocated = float((lt or {}).get("max_per_year") or 0)
    doc = LeaveBalance(
        tenant_id=tid, employee_id=employee_id, leave_type_id=leave_type_id,
        year=year, allocated=allocated, used=0, adjustment=0,
        balance=allocated, last_updated_at=_now(),
    ).to_mongo()
    res = await db.leave_balances.insert_one(doc); doc["_id"] = res.inserted_id
    return doc


@router.get("/leave-balances")
async def list_leave_balances(
    employee_id: str | None = None, year: str | None = None,
    user: dict = Depends(require_permission(P_LEAVE_BALANCE_VIEW)),
):
    q: dict = {"tenant_id": user["tenant_id"]}
    if employee_id: q["employee_id"] = employee_id
    if year: q["year"] = year
    docs = await get_db().leave_balances.find(q).sort("year", -1).to_list(500)
    return [_out(d) for d in docs]


class AdjustIn(BaseModel):
    employee_id: str
    leave_type_id: str
    year: str
    amount: float
    reason: str = "correction"
    notes: str | None = None


@router.post("/leave-balances/adjust", status_code=201)
async def adjust_balance(payload: AdjustIn, request: Request, user: dict = Depends(require_permission(P_LEAVE_ADJUST))):
    db = get_db()
    tid = user["tenant_id"]
    if not await db.employees.find_one({"_id": _oid(payload.employee_id), "tenant_id": tid}):
        raise HTTPException(status_code=404, detail="Employee not found")
    if not await db.leave_types.find_one({"_id": _oid(payload.leave_type_id), "tenant_id": tid}):
        raise HTTPException(status_code=404, detail="Leave type not found")
    b = await _ensure_balance(db, tid, payload.employee_id, payload.leave_type_id, payload.year)
    new_adj = float(b.get("adjustment") or 0) + payload.amount
    new_bal = float(b.get("allocated") or 0) + new_adj - float(b.get("used") or 0)
    await db.leave_balances.update_one({"_id": b["_id"]}, {"$set": {
        "adjustment": new_adj, "balance": new_bal, "last_updated_at": _now(),
    }})
    adj = LeaveAdjustment(
        tenant_id=tid, employee_id=payload.employee_id,
        leave_type_id=payload.leave_type_id, year=payload.year,
        amount=payload.amount, reason=payload.reason, notes=payload.notes,
        actor_user_id=user["id"],
    ).to_mongo()
    await db.leave_adjustments.insert_one(adj)
    await log_event(action="staff.leave_balance.adjust", resource="leave_balance",
                    resource_id=str(b["_id"]), tenant_id=tid, actor=user, request=request,
                    new_value={"amount": payload.amount, "new_balance": new_bal})
    return {"ok": True, "balance": new_bal, "adjustment_total": new_adj}


# ============================================================
# Leave applications
# ============================================================
class LeaveApplyIn(BaseModel):
    employee_id: str
    leave_type_id: str
    start_date: str
    end_date: str
    reason: str = Field(min_length=1, max_length=500)
    is_half_day: bool = False
    supporting_document_id: str | None = None
    year: str | None = None
    approver_l1_user_id: str | None = None
    approver_l2_user_id: str | None = None


@router.get("/leave-applications")
async def list_leave_applications(
    status: str | None = None, employee_id: str | None = None,
    year: str | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200),
    user: dict = Depends(require_permission(P_LEAVE_VIEW)),
):
    q: dict = {"tenant_id": user["tenant_id"]}
    if status: q["status"] = status
    if employee_id: q["employee_id"] = employee_id
    if year: q["year"] = year
    db = get_db()
    total = await db.leave_applications.count_documents(q)
    docs = await db.leave_applications.find(q).sort("created_at", -1).skip((page-1)*page_size).limit(page_size).to_list(page_size)
    return {"items": [_out(d) for d in docs], "total": total, "page": page, "page_size": page_size}


@router.post("/leave-applications", status_code=201)
async def apply_leave(payload: LeaveApplyIn, request: Request, user: dict = Depends(require_permission(P_LEAVE_APPLY))):
    db = get_db()
    tid = user["tenant_id"]
    emp = await db.employees.find_one({"_id": _oid(payload.employee_id), "tenant_id": tid})
    if not emp: raise HTTPException(status_code=404, detail="Employee not found")
    lt = await db.leave_types.find_one({"_id": _oid(payload.leave_type_id), "tenant_id": tid})
    if not lt: raise HTTPException(status_code=404, detail="Leave type not found")
    if not lt.get("is_active", True):
        raise HTTPException(status_code=400, detail="Leave type is inactive")
    if payload.start_date > payload.end_date:
        raise HTTPException(status_code=400, detail="start_date must be <= end_date")
    if lt.get("requires_document") and not payload.supporting_document_id:
        raise HTTPException(status_code=400, detail={"code": "document_required", "message": "This leave type requires a supporting document"})
    days = 0.5 if payload.is_half_day else float(_days_between(payload.start_date, payload.end_date))
    # Balance check
    year = payload.year or str(datetime.fromisoformat(payload.start_date).year)
    bal = await _ensure_balance(db, tid, payload.employee_id, payload.leave_type_id, year)
    if lt.get("max_per_year") is not None and (bal["balance"] < days) and lt.get("is_paid", True):
        raise HTTPException(status_code=409, detail={"code": "insufficient_balance", "message": "Insufficient leave balance", "balance": bal["balance"], "requested": days})
    # Overlap check
    overlap = await db.leave_applications.find_one({
        "tenant_id": tid, "employee_id": payload.employee_id,
        "status": {"$in": ["pending", "approved_l1", "approved"]},
        "start_date": {"$lte": payload.end_date},
        "end_date": {"$gte": payload.start_date},
    })
    if overlap:
        raise HTTPException(status_code=409, detail={"code": "leave_overlap", "message": "Overlapping leave already exists"})
    approval_steps = int(lt.get("approval_steps") or 1)
    doc = LeaveApplication(
        tenant_id=tid, employee_id=payload.employee_id,
        leave_type_id=payload.leave_type_id, start_date=payload.start_date,
        end_date=payload.end_date, days=days, is_half_day=payload.is_half_day,
        reason=payload.reason, supporting_document_id=payload.supporting_document_id,
        year=year, status="pending", approval_steps_required=approval_steps,
        approver_l1_user_id=payload.approver_l1_user_id,
        approver_l2_user_id=payload.approver_l2_user_id,
        applied_by_user_id=user["id"],
    ).to_mongo()
    res = await db.leave_applications.insert_one(doc); doc["_id"] = res.inserted_id
    await log_event(action="staff.leave.apply", resource="leave_application",
                    resource_id=str(res.inserted_id), tenant_id=tid, actor=user, request=request,
                    metadata={"employee_id": payload.employee_id, "days": days})
    return _out(doc)


@router.get("/leave-applications/{lid}")
async def get_leave_application(lid: str, user: dict = Depends(require_permission(P_LEAVE_VIEW))):
    d = await get_db().leave_applications.find_one({"_id": _oid(lid), "tenant_id": user["tenant_id"]})
    if not d: raise HTTPException(status_code=404, detail="Leave application not found")
    return _out(d)


class DecisionIn(BaseModel):
    reason: str | None = None


@router.post("/leave-applications/{lid}/approve")
async def approve_leave(lid: str, payload: DecisionIn, request: Request, user: dict = Depends(require_permission(P_LEAVE_APPROVE))):
    db = get_db()
    tid = user["tenant_id"]
    old = await db.leave_applications.find_one({"_id": _oid(lid), "tenant_id": tid})
    if not old: raise HTTPException(status_code=404, detail="Leave application not found")
    if old["status"] in {"approved", "rejected", "cancelled", "withdrawn"}:
        raise HTTPException(status_code=409, detail=f"Cannot approve — current status {old['status']}")
    steps_required = int(old.get("approval_steps_required") or 1)
    new_status = "approved" if steps_required == 1 else ("approved_l1" if old["status"] == "pending" else "approved")
    updates = {"status": new_status, "decision_reason": payload.reason, "decision_at": _now(), "updated_at": _now()}
    if new_status == "approved":
        updates["approved_by_user_id"] = user["id"]
        # Debit balance
        bal = await _ensure_balance(db, tid, old["employee_id"], old["leave_type_id"], old["year"])
        new_used = float(bal.get("used") or 0) + float(old["days"])
        new_bal = float(bal.get("allocated") or 0) + float(bal.get("adjustment") or 0) - new_used
        await db.leave_balances.update_one({"_id": bal["_id"]}, {"$set": {"used": new_used, "balance": new_bal, "last_updated_at": _now()}})
    await db.leave_applications.update_one({"_id": old["_id"]}, {"$set": updates})
    await log_event(action="staff.leave.approve", resource="leave_application",
                    resource_id=lid, tenant_id=tid, actor=user, request=request,
                    old_value={"status": old.get("status")}, new_value={"status": new_status})
    return _out(await db.leave_applications.find_one({"_id": old["_id"]}))


@router.post("/leave-applications/{lid}/reject")
async def reject_leave(lid: str, payload: DecisionIn, request: Request, user: dict = Depends(require_permission(P_LEAVE_APPROVE))):
    db = get_db()
    tid = user["tenant_id"]
    old = await db.leave_applications.find_one({"_id": _oid(lid), "tenant_id": tid})
    if not old: raise HTTPException(status_code=404, detail="Leave application not found")
    if old["status"] in {"approved", "rejected", "cancelled", "withdrawn"}:
        raise HTTPException(status_code=409, detail=f"Cannot reject — current status {old['status']}")
    await db.leave_applications.update_one({"_id": old["_id"]}, {"$set": {
        "status": "rejected", "rejected_by_user_id": user["id"],
        "decision_reason": payload.reason, "decision_at": _now(), "updated_at": _now(),
    }})
    await log_event(action="staff.leave.reject", resource="leave_application",
                    resource_id=lid, tenant_id=tid, actor=user, request=request,
                    old_value={"status": old.get("status")}, new_value={"status": "rejected"},
                    metadata={"reason": payload.reason})
    return _out(await db.leave_applications.find_one({"_id": old["_id"]}))


@router.post("/leave-applications/{lid}/cancel")
async def cancel_leave(lid: str, request: Request, user: dict = Depends(require_permission(P_LEAVE_APPLY))):
    db = get_db()
    tid = user["tenant_id"]
    old = await db.leave_applications.find_one({"_id": _oid(lid), "tenant_id": tid})
    if not old: raise HTTPException(status_code=404, detail="Leave application not found")
    if old["status"] in {"rejected", "cancelled", "withdrawn"}:
        raise HTTPException(status_code=409, detail=f"Cannot cancel — current status {old['status']}")
    was_approved = old["status"] == "approved"
    await db.leave_applications.update_one({"_id": old["_id"]}, {"$set": {
        "status": "cancelled", "decision_at": _now(), "updated_at": _now(),
    }})
    # Restore balance if it had been debited
    if was_approved:
        bal = await db.leave_balances.find_one({
            "tenant_id": tid, "employee_id": old["employee_id"],
            "leave_type_id": old["leave_type_id"], "year": old["year"],
        })
        if bal:
            new_used = max(0.0, float(bal.get("used") or 0) - float(old["days"]))
            new_bal = float(bal.get("allocated") or 0) + float(bal.get("adjustment") or 0) - new_used
            await db.leave_balances.update_one({"_id": bal["_id"]}, {"$set": {"used": new_used, "balance": new_bal, "last_updated_at": _now()}})
    await log_event(action="staff.leave.cancel", resource="leave_application",
                    resource_id=lid, tenant_id=tid, actor=user, request=request)
    return _out(await db.leave_applications.find_one({"_id": old["_id"]}))
