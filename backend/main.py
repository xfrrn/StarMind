"""StarMind Backend — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models.database import init_db
from routers import chat, conversations, repositories, sync, settings

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

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "starmind-backend"}
