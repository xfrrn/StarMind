"""StarMind Backend — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models.database import init_db
from routers import chat, conversations, repositories, sync, settings as settings_router
from config import get_settings

settings = get_settings()

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
    yield
    logger.info("👋 StarMind backend shutting down...")


app = FastAPI(
    title="StarMind API",
    description="AI-powered GitHub starred repositories analyzer",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — configurable origins for production
origins = [origin.strip() for origin in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Register routers
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(repositories.router)
app.include_router(sync.router)
app.include_router(settings_router.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "starmind-backend"}
