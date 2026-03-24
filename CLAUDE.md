# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

StarMind is a GitHub starred repository intelligent analyzer. Users can search their starred repos using natural language queries powered by AI semantic search.

## Development Commands

This is a Monorepo with `backend/` (Python/uv) and `packages/frontend/` (React/pnpm).

### Quick Start (Monorepo Root)
```bash
pnpm install:all      # Install frontend + backend dependencies
pnpm dev:all          # Start both frontend and backend dev servers
```

### Frontend (React/Vite)
```bash
pnpm dev:frontend     # Start dev server (port 5173)
pnpm build:frontend   # Production build
pnpm preview:frontend  # Preview production build
```

### Backend (Python/FastAPI)
```bash
pnpm dev:backend      # Start dev server (port 8000)
pnpm sync:backend     # Sync dependencies (uv sync)
pnpm test:backend     # Run tests (pytest)
# Or directly:
cd backend && uv sync
cd backend && uv run uvicorn main:app --reload --port 8000
```

### Docker
```bash
pnpm docker:up        # PostgreSQL + backend + frontend
pnpm docker:down      # Stop all services
pnpm docker:build     # Build images
```

## Architecture

### Request Flow
```
Frontend (Vite :5173) --proxy /api--> Backend (FastAPI :8000) --> PostgreSQL + pgvector
```

### Backend Layer Structure
```
routers/   → HTTP endpoints, param validation, response formatting
services/  → Business logic (GitHub sync, AI analysis, chat pipeline)
models/    → SQLAlchemy ORM models + database connection
config.py  → All settings via pydantic-settings from .env
```

**Key rule:** Routers contain no business logic; services have no FastAPI dependencies.

### Frontend Structure
```
src/app/
├── api.ts         # All API calls centralized here
├── data.ts        # TypeScript interfaces (Repository, etc.)
├── routes.tsx     # React Router configuration
├── pages/         # Page components
└── components/    # Reusable UI components
```

**Key rule:** Pages never call `fetch` directly - all requests go through `api.ts`.

## Key Technical Patterns

### Database
- SQLAlchemy 2.0 async style with `select()`, `await session.execute()`
- Auto-creates database and tables on startup (no manual migrations)
- PostgreSQL with pgvector extension for vector similarity search

### API Conventions
- All endpoints prefixed with `/api/`
- Response fields use **camelCase** (`hasUI`, `aiReason`, `activityLevel`)
- Database columns use **snake_case** (`has_ui`, `ai_reason`, `activity_level`)

### Chat Pipeline (services/chat/)
```
IntentRouter → QueryParser → RetrievalPlanner → QueryRewriter
    → RetrievalService (hybrid: keyword + vector search)
    → Reranker → ContextBuilder → ResponseGenerator (LLM)
```

### Streaming Chat
- `POST /api/chat/stream` returns Server-Sent Events
- Event types: `repositories`, `token`, `done`, `error`
- Frontend uses `fetch` + `ReadableStream` (not EventSource) for POST support

## Environment Variables

Required in `backend/.env`:
- `GITHUB_TOKEN` - GitHub Personal Access Token
- `OPENAI_API_KEY` - OpenAI API key
- `DATABASE_URL` - PostgreSQL connection string with asyncpg driver

## UI Guidelines

- Color palette: zinc grays + blue brand color
- Border radius: `rounded-lg` (small) / `rounded-2xl` (cards)
- Dark mode: every color class needs `dark:` variant
- Animations: use `framer-motion` (imported as `motion`)

## Python Style

- Python 3.11+ with modern syntax (`str | None`, `list[str]`)
- Async/await for all I/O operations
- Type annotations on all function signatures
- Use `logging` module, not `print`
