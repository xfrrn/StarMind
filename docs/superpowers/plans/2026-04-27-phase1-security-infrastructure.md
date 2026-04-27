# Phase 1: Security & Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement security hardening (CORS, rate limiting), enhanced health checks, Docker optimizations, and structured logging for production readiness.

**Architecture:** Add configuration-driven CORS and rate limiting middleware, create dedicated health check router with dependency checks, optimize Docker builds with .dockerignore and multi-stage builds, implement JSON-structured logging with correlation IDs.

**Tech Stack:** FastAPI, slowapi (rate limiting), SQLAlchemy (health checks), Docker multi-stage builds, Python logging with JSON formatter

---

## File Structure

### New Files
- `backend/middleware/__init__.py` - Middleware package
- `backend/middleware/rate_limit.py` - Rate limiting middleware using slowapi
- `backend/middleware/correlation_id.py` - Request correlation ID tracking
- `backend/routers/health.py` - Enhanced health check endpoint
- `backend/utils/__init__.py` - Utils package (if not exists)
- `backend/utils/logging_config.py` - JSON logging configuration
- `backend/.dockerignore` - Docker build exclusions
- `frontend/.dockerignore` - Frontend Docker build exclusions

### Modified Files
- `backend/config.py` - Add CORS, rate limiting, logging config
- `backend/main.py` - Apply middleware, update health endpoint
- `backend/pyproject.toml` - Add slowapi dependency
- `backend/Dockerfile` - Multi-stage build with non-root user
- `frontend/nginx.conf` - Add gzip compression

---

## Task 1: CORS Configuration Enhancement

**Files:**
- Modify: `backend/config.py`
- Modify: `backend/main.py:36-43`

- [ ] **Step 1: Add CORS configuration to config.py**

```python
# backend/config.py
# Add after line 10 (after github_readme_concurrency)

# CORS
cors_origins: str = "http://localhost:5173,http://localhost:3000"
cors_allow_credentials: bool = True
cors_allow_methods: list[str] = ["GET", "POST", "DELETE"]
cors_allow_headers: list[str] = ["Content-Type", "Authorization", "X-Correlation-ID"]
```

- [ ] **Step 2: Update CORS middleware in main.py**

Replace lines 36-43 in `backend/main.py`:

```python
# CORS — configurable origins for production
origins = [origin.strip() for origin in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)
```

- [ ] **Step 3: Update .env.example with CORS config**

Add to `backend/.env.example`:

```bash
# CORS Configuration
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

- [ ] **Step 4: Test CORS configuration**

Run:
```bash
cd backend
uv run uvicorn main:app --reload --port 8000
```

In another terminal:
```bash
curl -H "Origin: http://localhost:5173" -H "Access-Control-Request-Method: POST" -X OPTIONS http://localhost:8000/api/health -v
```

Expected: Response includes `Access-Control-Allow-Origin: http://localhost:5173`

- [ ] **Step 5: Commit CORS changes**

```bash
git add backend/config.py backend/main.py backend/.env.example
git commit -m "feat(security): add configurable CORS with restricted methods and headers

- Add cors_origins, cors_allow_methods, cors_allow_headers to config
- Replace hardcoded CORS origins with environment variable
- Restrict methods to GET, POST, DELETE
- Restrict headers to Content-Type, Authorization, X-Correlation-ID"
```

---

## Task 2: Rate Limiting Middleware

**Files:**
- Create: `backend/middleware/__init__.py`
- Create: `backend/middleware/rate_limit.py`
- Modify: `backend/config.py`
- Modify: `backend/pyproject.toml`
- Modify: `backend/main.py`

- [ ] **Step 1: Add slowapi dependency**

Add to `backend/pyproject.toml` dependencies array (after line 21):

```toml
"slowapi>=0.1.9",
```

- [ ] **Step 2: Install dependency**

Run:
```bash
cd backend
uv sync
```

Expected: slowapi installed successfully

- [ ] **Step 3: Add rate limit configuration to config.py**

Add after CORS configuration in `backend/config.py`:

```python
# Rate Limiting
rate_limit_enabled: bool = True
rate_limit_default: str = "100/minute"
rate_limit_sync: str = "5/hour"
rate_limit_chat: str = "20/minute"
```

- [ ] **Step 4: Create middleware package**

```bash
mkdir -p backend/middleware
touch backend/middleware/__init__.py
```

- [ ] **Step 5: Create rate_limit.py**

Create `backend/middleware/rate_limit.py`:

```python
"""Rate limiting middleware using slowapi."""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Custom handler for rate limit exceeded errors."""
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": exc.detail,
        },
    )


def create_limiter() -> Limiter:
    """Create and configure rate limiter."""
    return Limiter(
        key_func=get_remote_address,
        default_limits=["100/minute"],
        storage_uri="memory://",
    )
```

- [ ] **Step 6: Integrate rate limiter in main.py**

Add imports at top of `backend/main.py` (after line 7):

```python
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from middleware.rate_limit import create_limiter, rate_limit_exceeded_handler
```

Add after app creation (after line 34):

```python
# Rate limiting
if settings.rate_limit_enabled:
    limiter = create_limiter()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
```

- [ ] **Step 7: Add rate limits to sync router**

Modify `backend/routers/sync.py` - add import at top:

```python
from slowapi import Limiter
from fastapi import Request
```

Add rate limit decorator to sync endpoint (before `@router.post("/sync")`):

```python
@router.post("/sync")
async def trigger_sync(request: Request, session: AsyncSession = Depends(get_session)):
    limiter: Limiter = request.app.state.limiter
    await limiter.limit("5/hour")(request)
    # ... existing code
```

- [ ] **Step 8: Test rate limiting**

Start server:
```bash
cd backend
uv run uvicorn main:app --reload --port 8000
```

Test with rapid requests:
```bash
for i in {1..10}; do curl http://localhost:8000/api/health; done
```

Expected: After ~100 requests in a minute, receive 429 status with rate limit message

- [ ] **Step 9: Commit rate limiting**

```bash
git add backend/middleware/ backend/config.py backend/pyproject.toml backend/main.py backend/routers/sync.py uv.lock
git commit -m "feat(security): add API rate limiting with slowapi

- Add slowapi dependency for rate limiting
- Create rate_limit middleware with custom error handler
- Configure global limit: 100/minute per IP
- Add strict limit for sync endpoint: 5/hour
- Use in-memory storage (production can use Redis)"
```

---

## Task 3: Enhanced Health Check

**Files:**
- Create: `backend/routers/health.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Create health check router**

Create `backend/routers/health.py`:

```python
"""Enhanced health check endpoint with dependency checks."""

import logging
from datetime import datetime, timezone
from time import time

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["health"])

# Track startup time
_startup_time = time()


@router.get("/health")
async def health_check(session: AsyncSession = Depends(get_session)):
    """
    Comprehensive health check endpoint.
    
    Returns service status, version, uptime, and dependency checks.
    """
    checks = {}
    overall_status = "healthy"
    
    # Database check
    try:
        result = await session.execute(text("SELECT 1"))
        result.scalar()
        checks["database"] = "ok"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        checks["database"] = "error"
        overall_status = "degraded"
    
    # Calculate uptime
    uptime_seconds = int(time() - _startup_time)
    
    return {
        "status": overall_status,
        "version": "0.1.0",
        "uptime_seconds": uptime_seconds,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }
```

- [ ] **Step 2: Register health router in main.py**

Replace the existing health endpoint (lines 53-56) in `backend/main.py`:

Remove:
```python
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "starmind-backend"}
```

Add import at top (after line 10):
```python
from routers import chat, conversations, repositories, sync, settings, health
```

Update router registration (after line 50):
```python
# Register routers
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(repositories.router)
app.include_router(sync.router)
app.include_router(settings.router)
```

- [ ] **Step 3: Test health check endpoint**

Run:
```bash
cd backend
uv run uvicorn main:app --reload --port 8000
```

Test:
```bash
curl http://localhost:8000/api/health | jq
```

Expected output:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "uptime_seconds": 5,
  "timestamp": "2026-04-27T10:30:00+00:00",
  "checks": {
    "database": "ok"
  }
}
```

- [ ] **Step 4: Commit health check enhancement**

```bash
git add backend/routers/health.py backend/main.py
git commit -m "feat(monitoring): add enhanced health check endpoint

- Create dedicated health router with dependency checks
- Add database connection check
- Track and report service uptime
- Return structured health status with timestamp
- Replace simple health endpoint with comprehensive checks"
```

---

## Task 4: Structured Logging

**Files:**
- Create: `backend/utils/logging_config.py`
- Create: `backend/middleware/correlation_id.py`
- Modify: `backend/main.py`
- Modify: `backend/config.py`

- [ ] **Step 1: Add logging configuration to config.py**

Add after rate limiting config in `backend/config.py`:

```python
# Logging
log_level: str = "INFO"
log_format: str = "json"  # "json" or "text"
```

- [ ] **Step 2: Create logging configuration utility**

Create `backend/utils/__init__.py` if it doesn't exist:
```bash
touch backend/utils/__init__.py
```

Create `backend/utils/logging_config.py`:

```python
"""Structured logging configuration with JSON formatter."""

import logging
import json
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add correlation ID if present
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id
        
        # Add extra fields
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def configure_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """
    Configure application logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ("json" or "text")
    """
    # Remove existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    handler = logging.StreamHandler()
    
    # Set formatter
    if log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper()))
```

- [ ] **Step 3: Create correlation ID middleware**

Create `backend/middleware/correlation_id.py`:

```python
"""Correlation ID middleware for request tracing."""

import uuid
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Add correlation ID to requests for distributed tracing."""
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Get or generate correlation ID
        correlation_id = request.headers.get(
            "X-Correlation-ID", str(uuid.uuid4())
        )
        
        # Store in request state
        request.state.correlation_id = correlation_id
        
        # Add to logging context
        old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.correlation_id = correlation_id
            return record
        
        logging.setLogRecordFactory(record_factory)
        
        try:
            response = await call_next(request)
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        finally:
            # Restore original factory
            logging.setLogRecordFactory(old_factory)
```

- [ ] **Step 4: Integrate structured logging in main.py**

Add imports at top of `backend/main.py`:

```python
from utils.logging_config import configure_logging
from middleware.correlation_id import CorrelationIdMiddleware
```

Replace logging configuration (lines 12-16) with:

```python
# Configure structured logging
from config import get_settings
settings = get_settings()
configure_logging(log_level=settings.log_level, log_format=settings.log_format)
logger = logging.getLogger(__name__)
```

Add correlation ID middleware after CORS (after line ~43):

```python
# Correlation ID for request tracing
app.add_middleware(CorrelationIdMiddleware)
```

- [ ] **Step 5: Test structured logging**

Start server:
```bash
cd backend
LOG_FORMAT=json uv run uvicorn main:app --reload --port 8000
```

Make a request:
```bash
curl http://localhost:8000/api/health
```

Expected: Logs in JSON format with correlation_id field

Test with custom correlation ID:
```bash
curl -H "X-Correlation-ID: test-123" http://localhost:8000/api/health -v
```

Expected: Response header includes `X-Correlation-ID: test-123`

- [ ] **Step 6: Commit structured logging**

```bash
git add backend/utils/logging_config.py backend/middleware/correlation_id.py backend/config.py backend/main.py
git commit -m "feat(observability): add structured JSON logging with correlation IDs

- Create JSONFormatter for structured log output
- Add configurable log level and format (json/text)
- Implement correlation ID middleware for request tracing
- Propagate correlation IDs through request lifecycle
- Add correlation ID to response headers for debugging"
```

---

## Task 5: Docker Optimization

**Files:**
- Create: `backend/.dockerignore`
- Create: `frontend/.dockerignore`
- Modify: `backend/Dockerfile`
- Modify: `frontend/nginx.conf`

- [ ] **Step 1: Create backend .dockerignore**

Create `backend/.dockerignore`:

```
.venv/
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.env
.env.*
logs/
*.log
.git/
.gitignore
tests/
*.md
blueprint/
.ruff_cache/
.mypy_cache/
```

- [ ] **Step 2: Create frontend .dockerignore**

Create `frontend/.dockerignore`:

```
node_modules/
dist/
.git/
.gitignore
*.log
.env
.env.local
.env.*.local
*.md
guidelines/
.vite/
coverage/
```

- [ ] **Step 3: Optimize backend Dockerfile**

Replace `backend/Dockerfile` content:

```dockerfile
# Build stage - install dependencies
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (no dev packages)
RUN uv sync --frozen --no-dev

# Runtime stage - minimal image
FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Expose FastAPI port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

# Run FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 4: Add gzip compression to nginx.conf**

Add to `frontend/nginx.conf` inside the `server` block (after line 10):

```nginx
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1000;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript image/svg+xml;
    gzip_comp_level 6;
```

- [ ] **Step 5: Test Docker builds**

Build backend:
```bash
cd backend
docker build -t starmind-backend:test .
```

Expected: Build completes successfully, smaller context size

Build frontend:
```bash
cd frontend
docker build -t starmind-frontend:test .
```

Expected: Build completes successfully

Check image sizes:
```bash
docker images | grep starmind
```

- [ ] **Step 6: Test Docker containers**

Run backend:
```bash
docker run -p 8000:8000 -e DATABASE_URL=postgresql+asyncpg://postgres:postgres@host.docker.internal:5432/starmind starmind-backend:test
```

Test health:
```bash
curl http://localhost:8000/api/health
```

Expected: Health check returns successfully

- [ ] **Step 7: Commit Docker optimizations**

```bash
git add backend/.dockerignore frontend/.dockerignore backend/Dockerfile frontend/nginx.conf
git commit -m "feat(docker): optimize Docker builds and add security hardening

Backend:
- Add .dockerignore to reduce build context
- Implement multi-stage build for smaller images
- Run as non-root user (appuser) for security
- Add health check to Dockerfile
- Optimize layer caching

Frontend:
- Add .dockerignore to exclude dev files
- Add gzip compression to nginx config
- Compress text, CSS, JS, JSON, XML, SVG"
```

---

## Task 6: Update Environment Variables Documentation

**Files:**
- Modify: `backend/.env.example`

- [ ] **Step 1: Update .env.example with all new variables**

Add to `backend/.env.example`:

```bash
# CORS Configuration
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=100/minute
RATE_LIMIT_SYNC=5/hour
RATE_LIMIT_CHAT=20/minute

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

- [ ] **Step 2: Commit documentation update**

```bash
git add backend/.env.example
git commit -m "docs: update .env.example with Phase 1 configuration options

- Add CORS configuration variables
- Add rate limiting settings
- Add logging configuration
- Document all new environment variables"
```

---

## Task 7: Integration Testing

**Files:**
- Test all Phase 1 features together

- [ ] **Step 1: Start fresh server with all features**

```bash
cd backend
# Set environment variables
export LOG_FORMAT=json
export RATE_LIMIT_ENABLED=true
export CORS_ORIGINS=http://localhost:5173

uv run uvicorn main:app --reload --port 8000
```

- [ ] **Step 2: Test CORS with restricted origin**

```bash
curl -H "Origin: http://evil.com" -H "Access-Control-Request-Method: POST" -X OPTIONS http://localhost:8000/api/health -v
```

Expected: No `Access-Control-Allow-Origin` header (origin rejected)

```bash
curl -H "Origin: http://localhost:5173" -H "Access-Control-Request-Method: POST" -X OPTIONS http://localhost:8000/api/health -v
```

Expected: `Access-Control-Allow-Origin: http://localhost:5173` present

- [ ] **Step 3: Test rate limiting**

```bash
for i in {1..105}; do curl -s http://localhost:8000/api/health > /dev/null && echo "Request $i: OK" || echo "Request $i: RATE LIMITED"; done
```

Expected: First ~100 requests succeed, then 429 errors

- [ ] **Step 4: Test health check with all fields**

```bash
curl http://localhost:8000/api/health | jq
```

Expected output includes:
- `status`: "healthy"
- `version`: "0.1.0"
- `uptime_seconds`: positive integer
- `timestamp`: ISO 8601 format
- `checks.database`: "ok"

- [ ] **Step 5: Test correlation ID propagation**

```bash
curl -H "X-Correlation-ID: test-correlation-123" http://localhost:8000/api/health -v
```

Expected: Response header includes `X-Correlation-ID: test-correlation-123`

Check logs for correlation ID in JSON output

- [ ] **Step 6: Test structured logging output**

Check server logs - should see JSON formatted logs like:
```json
{"timestamp": "2026-04-27T10:30:00+00:00", "level": "INFO", "logger": "uvicorn.access", "message": "...", "correlation_id": "..."}
```

- [ ] **Step 7: Verify Docker builds work**

```bash
cd backend
docker build -t starmind-backend:phase1 .

cd ../frontend
docker build -t starmind-frontend:phase1 .
```

Expected: Both builds complete successfully

- [ ] **Step 8: Document test results**

Create test summary:
```bash
echo "Phase 1 Integration Test Results - $(date)" > phase1-test-results.txt
echo "✓ CORS configuration working" >> phase1-test-results.txt
echo "✓ Rate limiting active" >> phase1-test-results.txt
echo "✓ Enhanced health check operational" >> phase1-test-results.txt
echo "✓ Correlation IDs propagating" >> phase1-test-results.txt
echo "✓ Structured logging enabled" >> phase1-test-results.txt
echo "✓ Docker builds optimized" >> phase1-test-results.txt
```

---

## Task 8: Final Review and Merge Preparation

**Files:**
- Review all changes

- [ ] **Step 1: Review all commits**

```bash
git log master..feature/optimization-phase1 --oneline
```

Expected: 7 commits covering all Phase 1 features

- [ ] **Step 2: Run final checks**

```bash
cd backend
# Check for syntax errors
uv run python -m py_compile main.py config.py
uv run python -m py_compile middleware/*.py
uv run python -m py_compile routers/health.py
uv run python -m py_compile utils/logging_config.py
```

Expected: No syntax errors

- [ ] **Step 3: Verify all files are committed**

```bash
git status
```

Expected: "nothing to commit, working tree clean"

- [ ] **Step 4: Create summary of changes**

```bash
git diff master --stat
```

Review the file change summary

- [ ] **Step 5: Push branch to remote**

```bash
git push -u origin feature/optimization-phase1
```

Expected: Branch pushed successfully

- [ ] **Step 6: Document completion**

Phase 1 is complete and ready for review. All security and infrastructure improvements are implemented:

✅ CORS configuration (environment-driven)
✅ API rate limiting (slowapi)
✅ Enhanced health checks (database status)
✅ Structured logging (JSON format)
✅ Correlation ID tracking
✅ Docker optimizations (.dockerignore, multi-stage, non-root user)
✅ Documentation updates

Next steps:
- Review and test the branch
- Merge to master when approved
- Proceed to Phase 2: Performance & Code Quality

---

## Success Criteria Checklist

- [ ] CORS origins configurable via `CORS_ORIGINS` environment variable
- [ ] Rate limiting returns 429 after exceeding limits
- [ ] Health check endpoint returns database status and uptime
- [ ] Logs output in JSON format with correlation IDs
- [ ] Correlation IDs propagate through request/response cycle
- [ ] Docker builds complete without errors
- [ ] Backend runs as non-root user in container
- [ ] Frontend nginx serves with gzip compression
- [ ] All changes committed and pushed to feature branch

---

## Rollback Plan

If issues are discovered:

1. **Revert specific feature:**
   ```bash
   git revert <commit-hash>
   ```

2. **Revert entire phase:**
   ```bash
   git checkout master
   git branch -D feature/optimization-phase1
   ```

3. **Disable features via environment variables:**
   ```bash
   RATE_LIMIT_ENABLED=false
   LOG_FORMAT=text
   ```

---

## Notes

- Rate limiting uses in-memory storage. For production with multiple instances, configure Redis: `RATE_LIMIT_STORAGE_URL=redis://localhost:6379`
- Structured logging can be disabled by setting `LOG_FORMAT=text` for local development
- CORS origins should be set to actual production domains before deployment
- Health check can be extended with GitHub/OpenAI API checks if needed (currently only checks database)
