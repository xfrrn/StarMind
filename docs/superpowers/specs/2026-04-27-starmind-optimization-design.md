---
name: StarMind Comprehensive Optimization
description: Three-phase optimization covering security, performance, code quality, and observability
type: design
---

# StarMind Comprehensive Optimization Design

## Overview

This design document outlines a comprehensive optimization plan for the StarMind project, addressing 15 improvement areas across security, performance, code quality, deployment, and user experience. The implementation follows a three-phase approach to minimize risk and ensure each stage is independently testable.

## Goals

1. **Production Readiness**: Secure CORS configuration, rate limiting, enhanced health checks
2. **Performance**: Improved concurrency, database optimization, dependency cleanup
3. **Code Quality**: Linting, type checking, testing infrastructure
4. **Observability**: Structured logging, performance monitoring, error tracking integration points
5. **User Experience**: Frontend performance optimizations (virtual scrolling, skeleton screens)

## Implementation Strategy

**Approach**: Phased rollout (渐进式优化)
- Phase 1: Security & Infrastructure (1-2 hours)
- Phase 2: Performance & Code Quality (2-3 hours)
- Phase 3: Observability & UX (1-2 hours)

Each phase is independently committable and testable.

---

## Phase 1: Security & Infrastructure

### 1.1 CORS Configuration Enhancement

**Current Issue**: Hardcoded origins in `main.py`, not suitable for production.

**Solution**:
- Add `cors_origins` to `config.py` (read from environment variable)
- Restrict `allow_methods` to actual usage: `["GET", "POST", "DELETE"]`
- Restrict `allow_headers` to necessary headers: `["Content-Type", "Authorization"]`
- Keep development permissive, production strict

**Files Modified**:
- `backend/config.py`: Add `cors_origins: str = "http://localhost:5173,http://localhost:3000"`
- `backend/main.py`: Replace hardcoded origins with `settings.cors_origins.split(",")`

**Environment Variable**:
```bash
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### 1.2 API Rate Limiting

**Implementation**: Use `slowapi` library (FastAPI-compatible rate limiter)

**Rate Limits**:
- Global: 100 requests/minute per IP
- `/api/sync/*`: 5 requests/hour (prevent sync abuse)
- `/api/chat/stream`: 20 requests/minute
- Storage: In-memory (development), Redis-ready (production optional)

**Files Created**:
- `backend/middleware/rate_limit.py`: Rate limiting middleware

**Files Modified**:
- `backend/pyproject.toml`: Add `slowapi>=0.1.9`
- `backend/main.py`: Add rate limiting middleware

**Configuration** (`config.py`):
```python
rate_limit_enabled: bool = True
rate_limit_storage_url: str = "memory://"  # or "redis://localhost:6379"
```

### 1.3 Enhanced Health Check

**Current**: `/api/health` returns minimal status.

**Enhancement**: Return comprehensive health information:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "uptime_seconds": 3600,
  "timestamp": "2026-04-27T10:30:00Z",
  "checks": {
    "database": "ok",
    "github_api": "ok",
    "openai_api": "ok"
  }
}
```

**Implementation**:
- Track startup time in `main.py` lifespan
- Add database connection check (simple query)
- Optional: GitHub/OpenAI API checks (cached, not on every request)

**Files Modified**:
- `backend/main.py`: Enhance `/api/health` endpoint
- `backend/routers/health.py` (new): Dedicated health check router with dependency checks

### 1.4 Docker Ignore Files

**Purpose**: Reduce build context size, speed up builds, prevent sensitive files from entering images.

**backend/.dockerignore**:
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
```

**frontend/.dockerignore**:
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
```

### 1.5 Docker Image Optimization

**Backend Dockerfile Improvements**:
- Multi-stage build: separate dependency installation from runtime
- Run as non-root user for security
- Optimize layer caching (copy dependency files first)

**Changes**:
```dockerfile
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM python:3.11-slim
WORKDIR /app
RUN useradd -m -u 1000 appuser
COPY --from=builder /app/.venv /app/.venv
COPY . .
RUN chown -R appuser:appuser /app
USER appuser
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Frontend Dockerfile**: Already optimized with multi-stage build. Add gzip compression to `nginx.conf`:
```nginx
gzip on;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
gzip_min_length 1000;
```

### 1.6 Structured Logging

**Current**: Basic logging with simple format.

**Enhancement**:
- JSON-formatted logs (parseable by log aggregation tools)
- Correlation ID for request tracing
- Log level from environment variable
- Business metrics logging (sync duration, AI call counts)

**Implementation**:
- `backend/utils/logging.py`: JSON formatter, correlation ID middleware
- `backend/middleware/correlation_id.py`: Add `X-Correlation-ID` to requests

**Configuration** (`config.py`):
```python
log_level: str = "INFO"
log_format: str = "json"  # or "text" for development
```

**Log Structure**:
```json
{
  "timestamp": "2026-04-27T10:30:00Z",
  "level": "INFO",
  "correlation_id": "abc123",
  "message": "Repository sync completed",
  "duration_ms": 1234,
  "repos_synced": 50
}
```

---

## Phase 2: Performance & Code Quality

### 2.1 Backend Concurrency Optimization

**Current Issues**:
- `ai_analysis_concurrency: 1` (too conservative)
- Fixed 0.5s delay between requests (unnecessary)

**Solution**:
```python
# config.py
ai_analysis_concurrency: int = 3  # Up from 1
ai_analysis_request_delay_seconds: float = 0.0  # Remove fixed delay

# Add retry configuration
ai_analysis_max_retries: int = 3
ai_analysis_retry_backoff_factor: float = 2.0  # Exponential backoff
```

**Implementation**:
- Modify `services/application/analysis_service.py`: Remove fixed delay
- Add exponential backoff retry logic using `tenacity` library or custom implementation
- Retry on rate limit errors (429) and transient failures (5xx)

**Expected Impact**: 3x faster AI analysis during sync.

### 2.2 Database Optimization

**Add Indexes**:
```python
# models/repository.py
class Repository(Base):
    # ... existing fields ...
    
    __table_args__ = (
        Index('ix_repositories_full_name', 'full_name'),
        Index('ix_repositories_language', 'language'),
        Index('ix_repositories_updated_at', 'updated_at'),
        Index('ix_repositories_stars', 'stars'),
    )

# models/conversation.py
class Conversation(Base):
    # ... existing fields ...
    
    __table_args__ = (
        Index('ix_conversations_created_at', 'created_at'),
    )
```

**Connection Pool Configuration**:
```python
# config.py
database_pool_size: int = 10
database_max_overflow: int = 20
database_pool_timeout: int = 30
database_pool_recycle: int = 3600  # Recycle connections after 1 hour
```

**Apply in `models/database.py`**:
```python
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
    pool_recycle=settings.database_pool_recycle,
    echo=False,
)
```

### 2.3 Frontend Dependency Cleanup

**Current Issue**: 40+ Radix UI packages, many unused. Both MUI and Radix UI installed.

**Analysis Required**:
1. Scan `frontend/src` for actual Radix UI component usage
2. Identify unused `@radix-ui/*` packages
3. Decide: Keep Radix UI (lighter) or MUI (more features)

**Recommendation**: Keep Radix UI, remove MUI (unless heavily used).

**Expected Savings**: 20-30 packages removed, ~50MB smaller `node_modules`.

**Process**:
```bash
# Find actual imports
grep -r "@radix-ui" frontend/src --include="*.tsx" --include="*.ts" | cut -d: -f2 | sort -u

# Compare with package.json dependencies
# Remove unused packages
pnpm remove @radix-ui/react-accordion @radix-ui/react-alert-dialog ...
```

### 2.4 Python Code Quality Tools

**Add to `pyproject.toml`**:
```toml
[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.25.0",
    "pytest-cov>=4.1.0",
    "httpx>=0.28.0",
    "ruff>=0.3.0",
    "mypy>=1.9.0",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]
ignore = ["E501"]  # Line length handled by formatter

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.mypy]
python_version = "3.11"
strict = false  # Start lenient, gradually enable
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true
```

**Commands**:
```bash
uv run ruff check .          # Lint
uv run ruff format .         # Format
uv run mypy .                # Type check
uv run pytest --cov=.        # Test with coverage
```

**Pre-commit Hook** (optional, in `.git/hooks/pre-commit`):
```bash
#!/bin/bash
cd backend
uv run ruff check . || exit 1
uv run mypy . || exit 1
```

### 2.5 Frontend Code Quality Tools

**Add to `package.json`**:
```json
{
  "devDependencies": {
    "eslint": "^8.57.0",
    "@typescript-eslint/eslint-plugin": "^7.0.0",
    "@typescript-eslint/parser": "^7.0.0",
    "prettier": "^3.2.5",
    "eslint-config-prettier": "^9.1.0",
    "eslint-plugin-react": "^7.34.0",
    "eslint-plugin-react-hooks": "^4.6.0"
  },
  "scripts": {
    "lint": "eslint src --ext .ts,.tsx",
    "format": "prettier --write \"src/**/*.{ts,tsx,css}\"",
    "type-check": "tsc --noEmit"
  }
}
```

**Configuration Files**:

`.eslintrc.json`:
```json
{
  "parser": "@typescript-eslint/parser",
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended",
    "prettier"
  ],
  "rules": {
    "react/react-in-jsx-scope": "off",
    "@typescript-eslint/no-unused-vars": ["warn", { "argsIgnorePattern": "^_" }]
  },
  "settings": {
    "react": {
      "version": "detect"
    }
  }
}
```

`.prettierrc`:
```json
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100
}
```

### 2.6 Testing Infrastructure

**Backend Test Structure**:
```
backend/tests/
├── conftest.py              # Shared fixtures
├── test_api/
│   ├── test_health.py       # Health check endpoint
│   ├── test_repositories.py # Repository CRUD
│   ├── test_chat.py         # Chat streaming
│   └── test_sync.py         # Sync endpoints
├── test_services/
│   ├── test_chat_service.py
│   └── test_analysis_service.py
└── test_utils/
    └── test_cache.py
```

**conftest.py** (fixtures):
```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from httpx import AsyncClient
from main import app

@pytest.fixture
async def test_db():
    # Create test database
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    # ... setup tables
    yield engine
    await engine.dispose()

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
```

**Example Test** (`test_api/test_health.py`):
```python
import pytest

@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
```

**Frontend Testing**:

Add to `package.json`:
```json
{
  "devDependencies": {
    "vitest": "^1.4.0",
    "@testing-library/react": "^14.2.0",
    "@testing-library/jest-dom": "^6.4.0",
    "@testing-library/user-event": "^14.5.0"
  },
  "scripts": {
    "test": "vitest",
    "test:ui": "vitest --ui"
  }
}
```

**vitest.config.ts**:
```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
  },
});
```

**Example Test** (`src/app/components/__tests__/RepoCard.test.tsx`):
```typescript
import { render, screen } from '@testing-library/react';
import { RepoCard } from '../RepoCard';

test('renders repository name', () => {
  const repo = { fullName: 'user/repo', description: 'Test' };
  render(<RepoCard repository={repo} />);
  expect(screen.getByText('user/repo')).toBeInTheDocument();
});
```

---

## Phase 3: Observability & User Experience

### 3.1 Performance Monitoring

**Metrics Middleware**:

Create `backend/middleware/metrics.py`:
```python
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start_time
        
        # Log slow requests
        if duration > 1.0:
            logger.warning(f"Slow request: {request.method} {request.url.path} took {duration:.2f}s")
        
        # Add header
        response.headers["X-Response-Time"] = f"{duration:.3f}"
        return response
```

**Metrics Endpoint** (`/api/metrics`):
```python
# In-memory metrics storage
metrics = {
    "requests_total": 0,
    "requests_by_endpoint": {},
    "response_times": [],
    "openai_calls": 0,
    "openai_tokens": 0,
}

@app.get("/api/metrics")
async def get_metrics():
    return {
        "requests_total": metrics["requests_total"],
        "avg_response_time": sum(metrics["response_times"]) / len(metrics["response_times"]),
        "openai_calls": metrics["openai_calls"],
        "openai_tokens": metrics["openai_tokens"],
    }
```

**OpenAI Cost Tracking**:
- Wrap OpenAI calls to count tokens
- Estimate cost based on model pricing
- Log to metrics

### 3.2 Error Tracking Integration

**Sentry Integration** (optional, user-enabled):

Add to `config.py`:
```python
sentry_dsn: str = ""
sentry_environment: str = "production"
sentry_traces_sample_rate: float = 0.1
```

Add to `main.py`:
```python
if settings.sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        integrations=[FastApiIntegration()],
    )
```

**No forced dependency**: Sentry is optional, only imported if DSN is configured.

### 3.3 Frontend Performance Optimization

**Virtual Scrolling** (for large repository lists):

Install:
```bash
pnpm add @tanstack/react-virtual
```

Usage in repository list component:
```typescript
import { useVirtualizer } from '@tanstack/react-virtual';

function RepositoryList({ repositories }) {
  const parentRef = useRef<HTMLDivElement>(null);
  
  const virtualizer = useVirtualizer({
    count: repositories.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 200, // Estimated card height
  });
  
  return (
    <div ref={parentRef} style={{ height: '600px', overflow: 'auto' }}>
      <div style={{ height: `${virtualizer.getTotalSize()}px` }}>
        {virtualizer.getVirtualItems().map((virtualRow) => (
          <div key={virtualRow.index} style={{ transform: `translateY(${virtualRow.start}px)` }}>
            <RepoCard repository={repositories[virtualRow.index]} />
          </div>
        ))}
      </div>
    </div>
  );
}
```

**Skeleton Screens**:

Create `components/RepoCardSkeleton.tsx`:
```typescript
export function RepoCardSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="h-4 bg-gray-300 rounded w-3/4 mb-2"></div>
      <div className="h-3 bg-gray-300 rounded w-full mb-1"></div>
      <div className="h-3 bg-gray-300 rounded w-5/6"></div>
    </div>
  );
}
```

Use during loading:
```typescript
{isLoading ? (
  <RepoCardSkeleton />
) : (
  <RepoCard repository={repo} />
)}
```

**Image Optimization**:

Enhance `ImageWithFallback.tsx`:
```typescript
<img
  src={src}
  alt={alt}
  loading="lazy"  // Native lazy loading
  onError={handleError}
/>
```

Add WebP support:
```typescript
<picture>
  <source srcSet={`${src}.webp`} type="image/webp" />
  <img src={src} alt={alt} loading="lazy" />
</picture>
```

### 3.4 API Response Caching

**Backend Cache Utility**:

Create `backend/utils/cache.py`:
```python
from functools import wraps
from typing import Any, Callable
import time

# Simple in-memory LRU cache
_cache: dict[str, tuple[float, Any]] = {}
MAX_CACHE_SIZE = 100

def cache_response(ttl_seconds: int = 60):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{args}:{kwargs}"
            
            # Check cache
            if cache_key in _cache:
                expires_at, value = _cache[cache_key]
                if time.time() < expires_at:
                    return value
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Store in cache
            _cache[cache_key] = (time.time() + ttl_seconds, result)
            
            # Evict old entries if needed
            if len(_cache) > MAX_CACHE_SIZE:
                oldest = min(_cache.items(), key=lambda x: x[1][0])
                del _cache[oldest[0]]
            
            return result
        return wrapper
    return decorator
```

**Usage**:
```python
@router.get("/api/repositories/stats")
@cache_response(ttl_seconds=300)  # Cache for 5 minutes
async def get_stats(session: AsyncSession = Depends(get_session)):
    # ... expensive query
    return stats
```

**Frontend**: Already has caching in `api.ts`, keep as-is.

---

## Testing Strategy

### Phase 1 Testing
- Verify CORS headers with `curl -H "Origin: https://example.com"`
- Test rate limiting by sending rapid requests
- Check health endpoint returns all fields
- Verify Docker builds succeed with `.dockerignore`
- Inspect logs for JSON format

### Phase 2 Testing
- Run `uv run pytest` to verify tests pass
- Benchmark AI analysis speed (before/after concurrency change)
- Query database to verify indexes exist: `\d repositories` in psql
- Run `ruff check` and `mypy` to verify no errors
- Check `node_modules` size before/after dependency cleanup

### Phase 3 Testing
- Check `/api/metrics` endpoint for data
- Scroll large repository list to verify virtual scrolling
- Verify skeleton screens appear during loading
- Test cache by calling same endpoint twice, check response time

---

## Rollback Plan

Each phase is independently committable:
- **Phase 1**: Revert commit if CORS/rate limiting breaks existing clients
- **Phase 2**: Revert if tests fail or performance degrades
- **Phase 3**: Revert if monitoring overhead is too high

Git branches:
- `feature/optimization-phase1`
- `feature/optimization-phase2`
- `feature/optimization-phase3`

Merge to `master` after each phase is validated.

---

## Success Criteria

### Phase 1
- [ ] CORS origins configurable via environment variable
- [ ] Rate limiting active, returns 429 on excess requests
- [ ] Health check returns database status
- [ ] Docker builds 20%+ faster with `.dockerignore`
- [ ] Logs in JSON format with correlation IDs

### Phase 2
- [ ] AI analysis 2-3x faster (measure sync time)
- [ ] Database queries use indexes (check `EXPLAIN` output)
- [ ] `node_modules` size reduced by 30%+
- [ ] `ruff check` and `mypy` pass with no errors
- [ ] Test coverage >50% for critical paths

### Phase 3
- [ ] `/api/metrics` endpoint returns request stats
- [ ] Virtual scrolling handles 1000+ repositories smoothly
- [ ] Skeleton screens visible during loading
- [ ] Cached endpoints respond in <50ms on cache hit

---

## Future Enhancements (Out of Scope)

- Redis-backed caching for multi-instance deployments
- Full Sentry integration with custom error grouping
- Prometheus metrics export
- Frontend bundle size analysis and optimization
- Database query performance profiling
- Load testing with Locust or k6

---

## Dependencies

### New Python Packages
- `slowapi` - Rate limiting
- `ruff` - Linting and formatting
- `mypy` - Type checking
- `pytest-cov` - Test coverage
- `tenacity` (optional) - Retry logic

### New Node Packages
- `eslint` + plugins - Linting
- `prettier` - Formatting
- `vitest` + `@testing-library/react` - Testing
- `@tanstack/react-virtual` - Virtual scrolling

### Infrastructure
- No new infrastructure required
- Optional: Redis for rate limiting (production)
- Optional: Sentry account for error tracking

---

## Timeline Estimate

- **Phase 1**: 1-2 hours (security & infrastructure)
- **Phase 2**: 2-3 hours (performance & code quality)
- **Phase 3**: 1-2 hours (observability & UX)

**Total**: 4-7 hours for full implementation and testing.

---

## Conclusion

This three-phase optimization plan systematically improves StarMind across security, performance, code quality, and user experience. Each phase is independently valuable and can be deployed separately, minimizing risk while delivering incremental improvements.

The design prioritizes:
1. **Safety first**: Security and infrastructure before performance
2. **Measurable impact**: Each optimization has clear success criteria
3. **Maintainability**: Code quality tools prevent future technical debt
4. **User experience**: Performance improvements directly benefit end users

Next step: Create implementation plan with detailed file-by-file changes.
