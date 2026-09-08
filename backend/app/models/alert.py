"""System / tenant alert."""
from app.models.base import BaseDocument


class Alert(BaseDocument):
    tenant_id: str | None = None  # None = platform-wide alert
    level: str = "info"           # info | warning | critical
    title: str
    message: str
    resource: str | None = None   # e.g. "tenant", "subscription"
    resource_id: str | None = None
    acknowledged: bool = False
