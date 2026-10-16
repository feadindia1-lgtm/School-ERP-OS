"""Stabilization Workstream C — single source of truth for CRM lead stage progression.

Lead stage is advanced by real events (contact logged, visit booked, application
status changes, conversion). Application-driven stages cannot be set by hand.
"""
from datetime import datetime, timezone

from bson import ObjectId

from app.models.admission import (
    APP_APPROVED, APP_CONVERTED, APP_DOCUMENTS_PENDING, APP_DRAFT, APP_REJECTED,
    APP_SUBMITTED, APP_UNDER_REVIEW, APP_WITHDRAWN,
)
from app.models.crm import (
    CrmActivity, DEFAULT_PIPELINE, STAGE_ADMITTED, STAGE_APPROVED, STAGE_CONTACTED,
    STAGE_FEE_PENDING, STAGE_FORM_FILLED, STAGE_LOST, STAGE_UNDER_REVIEW,
)

ORDER = {s["code"]: s["order"] for s in DEFAULT_PIPELINE}
APPLICATION_DRIVEN_STAGES = {STAGE_FORM_FILLED, STAGE_UNDER_REVIEW, STAGE_APPROVED, STAGE_FEE_PENDING, STAGE_ADMITTED}
CONTACT_ACTIVITY_TYPES = {"phone_call", "whatsapp", "sms", "email", "meeting", "campus_visit"}

FEE_PENDING = "pending"
FEE_RECEIVED = "received"

APP_TO_STAGE = {
    APP_DRAFT: STAGE_FORM_FILLED,
    APP_SUBMITTED: STAGE_FORM_FILLED,
    APP_UNDER_REVIEW: STAGE_UNDER_REVIEW,
    APP_DOCUMENTS_PENDING: STAGE_UNDER_REVIEW,
    APP_CONVERTED: STAGE_ADMITTED,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def set_lead_stage(db, tid: str, lead_id: str | None, stage: str, *, actor_id: str | None,
                         note: str | None = None, forward_only: bool = True) -> bool:
    """Move a lead to `stage`. forward_only skips moves that would go backwards in the funnel."""
    if not lead_id or not ObjectId.is_valid(lead_id):
        return False
    lead = await db.crm_leads.find_one({"_id": ObjectId(lead_id), "tenant_id": tid})
    if not lead or lead.get("stage") == stage:
        return False
    current = lead.get("stage")
    if forward_only and (current in {STAGE_ADMITTED, STAGE_LOST} or ORDER.get(stage, 0) <= ORDER.get(current, 0)):
        return False
    now = _now()
    updates = {"stage": stage, "updated_at": now}
    if stage == STAGE_LOST and note:
        updates["lost_reason"] = note
    await db.crm_leads.update_one({"_id": lead["_id"]}, {"$set": updates})
    await db.crm_activities.insert_one(CrmActivity(
        tenant_id=tid, lead_id=lead_id, activity_type="application_update", is_system=True,
        subject=f"Stage → {stage}", notes=note, activity_at=now, user_id=actor_id,
    ).to_mongo())
    return True


async def sync_lead_from_application(db, tid: str, app: dict, status: str, *, actor_id: str | None,
                                     fee_required: bool, note: str | None = None) -> None:
    lead_id = app.get("lead_id")
    if status in {APP_REJECTED, APP_WITHDRAWN}:
        await set_lead_stage(db, tid, lead_id, STAGE_LOST, actor_id=actor_id,
                             note=note or f"Application {status.lower()}", forward_only=False)
    elif status == APP_APPROVED:
        await set_lead_stage(db, tid, lead_id, STAGE_FEE_PENDING if fee_required else STAGE_APPROVED,
                             actor_id=actor_id, note=note)
    elif status in APP_TO_STAGE:
        await set_lead_stage(db, tid, lead_id, APP_TO_STAGE[status], actor_id=actor_id, note=note)


async def admission_settings(db, tid: str) -> dict:
    from app.api.v1.crm_routes import _ensure_settings
    return await _ensure_settings(tid)


def fee_required(settings: dict) -> bool:
    return settings.get("require_fee_before_conversion", True)
