"""FastAPI application entry point."""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.utils.logger import setup_logging, get_logger
from app.routers import health, upload, jobs, packages, logs, settings as settings_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    app_settings = get_settings()
    logger.info(
        "startup",
        llm_provider=app_settings.llm_provider,
        chroma_dir=app_settings.chroma_persist_dir,
    )

    # Ensure data directories exist
    import pathlib
    pathlib.Path(app_settings.upload_dir).mkdir(parents=True, exist_ok=True)
    pathlib.Path(app_settings.packages_dir).mkdir(parents=True, exist_ok=True)

    # ── KEY FIX ─────────────────────────────────────────────────────────────
    # Pre-load the sentence-transformers embedding model BEFORE the first
    # request arrives.  On Render's free tier, loading ~90 MB of ML model
    # mid-request causes a sudden memory spike that triggers the OOM killer
    # and restarts the server.  Loading it once at startup keeps memory
    # stable and prevents the restart.
    # ────────────────────────────────────────────────────────────────────────
    logger.info("preloading_embedding_model")
    try:
        from app.rag.embedder import warm_up_embedder_async
        await warm_up_embedder_async()
        logger.info("embedding_model_ready")
    except Exception as exc:
        # Non-fatal: hash-based fallback will be used instead
        logger.warning("embedding_model_preload_failed", error=str(exc))

    logger.info("server_ready")
    yield
    logger.info("shutdown")


app = FastAPI(
    title="AI Teacher Platform API",
    description="Converts educational documents into structured Teacher Knowledge Packages",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base path prefix for all routes
BASE_PATH = os.environ.get("BASE_PATH", "/api")


def _with_base(router, prefix: str = ""):
    app.include_router(router, prefix=BASE_PATH + prefix)


_with_base(health.router)
_with_base(upload.router)
_with_base(jobs.router)
_with_base(packages.router)
_with_base(logs.router)
_with_base(settings_router.router)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error("unhandled_exception", error=str(exc), path=str(request.url))
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )
