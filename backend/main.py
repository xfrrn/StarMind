"""StarMind Backend — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models.database import init_db
from routers import chat, conversations, repositories, sync, settings, collections, dashboard, public, backup, archives
from services.application.scheduler_service import init_scheduler, get_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — initialize database on startup."""
    logger.info("🚀 StarMind backend starting up...")
    await init_db()
    logger.info("✅ Database initialized")

    # Initialize scheduler for auto-sync
    try:
        await init_scheduler()
        logger.info("✅ Scheduler initialized")
    except Exception as e:
        logger.warning("Failed to initialize scheduler: %s", e)

    yield

    # Shutdown scheduler
    try:
        get_scheduler().shutdown()
    except Exception:
        pass

    logger.info("👋 StarMind backend shutting down...")


app = FastAPI(
    title="StarMind API",
    description="AI-powered GitHub starred repositories analyzer",
    version="0.1.0",
    lifespan=lifespan,
)

from config import get_settings

# CORS — allow frontend dev server
app_settings = get_settings()
cors_origins = [origin.strip() for origin in app_settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(repositories.router)
app.include_router(sync.router)
app.include_router(settings.router)
app.include_router(collections.router)
app.include_router(dashboard.router)
app.include_router(public.router)
app.include_router(backup.router)
app.include_router(archives.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "starmind-backend"}
