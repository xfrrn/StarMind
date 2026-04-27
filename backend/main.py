"""StarMind Backend — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from pythonjsonlogger import jsonlogger

from middleware.rate_limit import create_limiter, rate_limit_exceeded_handler
from middleware.logging import LoggingMiddleware, CorrelationIdFilter
from models.database import init_db
from routers import chat, conversations, repositories, sync, settings as settings_router, health
from config import get_settings

settings = get_settings()

# Configure logging based on settings
log_handler = logging.StreamHandler()

if settings.log_format == "json":
    # JSON formatter for production
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s %(correlation_id)s"
    )
else:
    # Human-readable format for development
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s"
    )

log_handler.setFormatter(formatter)
log_handler.addFilter(CorrelationIdFilter())

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    handlers=[log_handler],
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

# Rate limiting
if settings.rate_limit_enabled:
    limiter = create_limiter()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Logging middleware
app.add_middleware(LoggingMiddleware)

# CORS — configurable origins for production
origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
if not origins:
    raise ValueError("No valid CORS origins configured")
logger.info(f"CORS enabled for origins: {origins}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Register routers
app.include_router(health.router, tags=["health"])
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(repositories.router)
app.include_router(sync.router)
app.include_router(settings_router.router)

