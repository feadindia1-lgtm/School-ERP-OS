"""Subscription plan pricing map (monthly USD)."""

PLAN_PRICING = {
    "trial": 0,
    "starter": 49,
    "standard": 149,
    "premium": 349,
    "enterprise": 899,
}


def mrr_from_tenants(tenants: list[dict]) -> float:
    total = 0.0
    for t in tenants:
        if t.get("status") in {"active"}:
            total += PLAN_PRICING.get(t.get("plan", "trial"), 0)
    return round(total, 2)
