"""Alert service — writes system/tenant alerts."""
from app.core.db import get_db
from app.models.alert import Alert


async def create_alert(
    *,
    title: str,
    message: str,
    level: str = "info",
    tenant_id: str | None = None,
    resource: str | None = None,
    resource_id: str | None = None,
) -> str:
    doc = Alert(
        tenant_id=tenant_id,
        level=level,
        title=title,
        message=message,
        resource=resource,
        resource_id=resource_id,
    ).to_mongo()
    res = await get_db().alerts.insert_one(doc)
    return str(res.inserted_id)
