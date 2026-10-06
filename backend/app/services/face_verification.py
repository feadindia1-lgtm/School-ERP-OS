"""Pluggable face-verification provider interface.

Prompt 6 ships two implementations:
- ``NoOpFaceProvider`` — captures evidence only, returns ``NOT_VERIFIED``.
- Interface for future commercial providers (AWS Rekognition, fal.ai, etc).

The attendance domain **never** fabricates a VERIFIED result — it is up to
the concrete provider to return a score the attendance route can act on.
Admin manual review may upgrade a session to ``VERIFIED`` / ``REJECTED``
via the correction workflow.
"""
from dataclasses import dataclass


@dataclass
class FaceVerificationResult:
    status: str                 # VERIFICATION_STATUS value
    match_score: float | None   # 0..1 confidence, None if provider skipped
    provider: str
    reference: str | None       # provider request/job id


class FaceProvider:
    name = "abstract"

    async def verify(
        self, *, tenant_id: str, employee_id: str, selfie_bytes: bytes,
        reference_storage_key: str | None,
    ) -> FaceVerificationResult:
        raise NotImplementedError


class NoOpFaceProvider(FaceProvider):
    """Default provider — stores the evidence, flags for manual review.

    Returns ``PENDING_REVIEW`` when face_verification_required is on and we
    have evidence; ``NOT_VERIFIED`` otherwise.  Never returns ``VERIFIED``
    — only a real matching provider or an admin override may do that.
    """
    name = "none"

    async def verify(
        self, *, tenant_id: str, employee_id: str, selfie_bytes: bytes,
        reference_storage_key: str | None,
    ) -> FaceVerificationResult:
        has_evidence = bool(selfie_bytes)
        return FaceVerificationResult(
            status="PENDING_REVIEW" if has_evidence else "NOT_VERIFIED",
            match_score=None, provider=self.name, reference=None,
        )


# Module-level registry — swap in a different implementation at wiring time.
_providers: dict[str, FaceProvider] = {"none": NoOpFaceProvider()}


def register_provider(provider: FaceProvider) -> None:
    _providers[provider.name] = provider


def get_provider(name: str) -> FaceProvider:
    return _providers.get(name) or _providers["none"]
