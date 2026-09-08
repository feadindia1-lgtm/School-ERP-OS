"""Tenant-scoped sequential numbering — concurrency-safe via findOneAndUpdate."""
from datetime import datetime, timezone

from app.core.db import get_db


async def next_number(tenant_id: str, prefix: str, width: int = 6) -> str:
    """Generate a human-friendly identifier like INQ-2026-000001, scoped per tenant + prefix + year."""
    year = datetime.now(timezone.utc).year
    key = f"{tenant_id}:{prefix}:{year}"
    doc = await get_db().counters.find_one_and_update(
        {"_id": key},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    seq = doc["seq"] if doc else 1
    return f"{prefix}-{year}-{str(seq).zfill(width)}"
