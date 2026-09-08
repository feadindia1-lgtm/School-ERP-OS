"""School OS backend entrypoint."""
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# Make app package importable
sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402

from app.api.v1.router import api_v1  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.db import close_client, ensure_indexes  # noqa: E402
from app.core.errors import register_exception_handlers  # noqa: E402
from app.services.seed import seed_platform_admin  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("school_os")

app = FastAPI(title="School OS API", version="0.1.0")

register_exception_handlers(app)

# CORS — use explicit origins if provided, else allow all in dev.
_cors = settings.CORS_ORIGINS
_allow_all = _cors == ["*"] or _cors == []
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors if not _allow_all else ["*"],
    allow_credentials=not _allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(api_v1)


# Legacy compatibility so /api/health & /api/ still respond
@app.get("/api/")
async def api_root():
    return {"product": "School OS", "api_versions": ["/api/v1"]}


@app.get("/api/health")
async def legacy_health():
    from app.api.v1.meta_routes import health
    return await health()


@app.on_event("startup")
async def _startup():
    await ensure_indexes()
    await seed_platform_admin()
    logger.info("School OS API ready — env=%s db=%s", os.environ.get("ENV", "dev"), settings.DB_NAME)


@app.on_event("shutdown")
async def _shutdown():
    await close_client()
