English | [中文](./README.md)

# StarMind ⭐🧠

AI-powered GitHub starred repositories analyzer. Search your stars with natural language and let AI help you find the right project.

## Architecture

```
StarMind/
├── frontend/          # Vite + React + TailwindCSS
├── backend/           # FastAPI + PostgreSQL + pgvector
└── .gitignore
```

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Node.js 18+ & pnpm / npm
- PostgreSQL with [pgvector](https://github.com/pgvector/pgvector) extension
- OpenAI API Key
- GitHub Personal Access Token

### 1. Start Backend

```bash
cd backend

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your GITHUB_TOKEN, OPENAI_API_KEY, DATABASE_URL

# Install dependencies
uv sync

# Start the server (database & tables are auto-created on startup)
uv run uvicorn main:app --reload --port 8000
```

> **Note**: The backend will automatically create the database, enable pgvector extension, and create all required tables on startup. Just make sure PostgreSQL is running and the user in `DATABASE_URL` has permission to create databases.

### 2. Start Frontend

```bash
cd frontend

# Install dependencies
pnpm install   # or npm install

# Start dev server (proxies /api to backend)
pnpm dev       # or npm run dev
```

Open http://localhost:5173

### 3. Sync Your Stars

1. Go to **Sync Center** in the app
2. Click **Force Sync Now**
3. Wait for AI to analyze your starred repositories
4. Start searching with AI! 🚀

## Features

- 🔍 **AI Semantic Search** — Ask natural language questions to find repos
- 🤖 **AI Analysis** — Auto-generates tags, categories, and summaries for each repo
- 📊 **Smart Filtering** — Filter by language, category, features, activity level
- 🔄 **GitHub Sync** — Incremental sync with progress tracking
- ⚙️ **Settings** — Configurable AI preferences

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React, Vite, TailwindCSS, Framer Motion |
| Backend | FastAPI, SQLAlchemy (async) |
| Database | PostgreSQL + pgvector |
| AI | OpenAI (gpt-4o-mini + text-embedding-3-small) |
| Package Manager | uv (Python), pnpm (Node.js) |
