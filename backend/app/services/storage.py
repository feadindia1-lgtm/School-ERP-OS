"""Document storage abstraction with a filesystem backend.

Files are stored under `/app/storage/tenants/{tenant_id}/documents/{document_id}` on disk.
Access is always mediated by an authenticated FastAPI endpoint — nothing is served
directly by the web server / CDN, so tenant isolation is enforced.
"""
import os
from pathlib import Path


STORAGE_ROOT = Path(os.environ.get("SCHOOL_OS_STORAGE_DIR", "/app/storage"))


class DocumentStorage:
    """Abstract API — swap this class for S3/GCS backends later without changing routes."""

    async def put(self, tenant_id: str, document_id: str, data: bytes) -> str:
        raise NotImplementedError

    async def get(self, tenant_id: str, storage_key: str) -> bytes:
        raise NotImplementedError

    async def delete(self, tenant_id: str, storage_key: str) -> None:
        raise NotImplementedError


class LocalFilesystemStorage(DocumentStorage):
    def _path(self, tenant_id: str, document_id: str) -> Path:
        p = STORAGE_ROOT / "tenants" / tenant_id / "documents"
        p.mkdir(parents=True, exist_ok=True)
        return p / document_id

    async def put(self, tenant_id: str, document_id: str, data: bytes) -> str:
        path = self._path(tenant_id, document_id)
        path.write_bytes(data)
        # storage_key is the relative filename — enough to re-open when combined with tenant_id
        return f"tenants/{tenant_id}/documents/{document_id}"

    async def get(self, tenant_id: str, storage_key: str) -> bytes:
        # Prevent path traversal — key must start with the caller's tenant prefix.
        expected_prefix = f"tenants/{tenant_id}/documents/"
        if not storage_key.startswith(expected_prefix):
            raise PermissionError("Cross-tenant document access denied")
        path = STORAGE_ROOT / storage_key
        if not path.exists():
            raise FileNotFoundError(storage_key)
        return path.read_bytes()

    async def delete(self, tenant_id: str, storage_key: str) -> None:
        expected_prefix = f"tenants/{tenant_id}/documents/"
        if not storage_key.startswith(expected_prefix):
            raise PermissionError("Cross-tenant document access denied")
        path = STORAGE_ROOT / storage_key
        if path.exists():
            path.unlink()


storage: DocumentStorage = LocalFilesystemStorage()
