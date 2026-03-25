English | [中文](./README.md)

<div align="center">

# StarMind ⭐🧠

**AI-Powered GitHub Star Manager**

Search your GitHub stars with natural language and let AI help you find the right project.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## ✨ Features

### 🔍 AI Semantic Search
Ask questions in natural language, AI understands your intent and finds the best matches.
> *"Find a UI component library built with React"*
> *"What are some good Python web scraping frameworks"*
> *"What are the trending AI projects recently"*

### 🤖 Smart Analysis
Automatically generates for each repository:
- 📌 Smart tags and categories
- 📝 One-line summary
- 🔧 Feature detection (UI, API, etc.)
- 📈 Activity level assessment

### 📊 Dashboard Insights
- Programming language distribution
- Project category statistics
- Star count distribution
- Activity analysis

### 📁 Collections
- Create custom collections
- Add personal notes to saved repos
- Generate shareable links

### 🔄 Auto Sync
- Scheduled automatic sync (configurable time)
- Incremental sync to save time
- Real-time progress tracking

### 🌙 Dark Mode
Full dark mode support to protect your eyes.

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, Vite, TailwindCSS, Framer Motion, Recharts |
| **Backend** | FastAPI, SQLAlchemy (async), APScheduler |
| **Database** | PostgreSQL + pgvector |
| **AI** | OpenAI (GPT-4o-mini + text-embedding-3-small) |
| **Package Manager** | uv (Python), pnpm (Node.js) |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Node.js 18+ and pnpm
- PostgreSQL with [pgvector](https://github.com/pgvector/pgvector) extension
- OpenAI API Key
- GitHub Personal Access Token

### 1. Clone the Project

```bash
git clone https://github.com/xfrrn/StarMind.git
cd StarMind
```

### 2. Start Backend

```bash
cd backend

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your configuration:
# - GITHUB_TOKEN (GitHub Personal Access Token)
# - OPENAI_API_KEY (OpenAI API Key)
# - DATABASE_URL (PostgreSQL connection string)

# Install dependencies
uv sync

# Start the server
uv run uvicorn main:app --reload --port 8000
```

> **Note**: The backend automatically creates the database, enables pgvector extension, and sets up all tables on startup.

### 3. Start Frontend

```bash
cd packages/frontend

# Install dependencies
pnpm install

# Start dev server
pnpm dev
```

Open http://localhost:5173 to get started!

### 4. Sync Your Stars

1. Go to **Sync Center**
2. Click **Sync Now** to sync repositories
3. Click **Run AI Analysis** to analyze with AI
4. Start searching with natural language! 🚀

---

## 📁 Project Structure

```
StarMind/
├── backend/                    # Python backend
│   ├── routers/               # API routes
│   ├── services/              # Business logic
│   ├── models/                # Database models
│   └── core/                  # Core modules (GitHub API, AI, etc.)
├── packages/
│   └── frontend/              # React frontend
│       └── src/app/
│           ├── pages/         # Page components
│           ├── components/    # Reusable components
│           └── api.ts         # API client
├── CLAUDE.md                  # Claude Code development guide
└── README.md
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GITHUB_TOKEN` | GitHub Personal Access Token | ✅ |
| `OPENAI_API_KEY` | OpenAI API Key | ✅ |
| `DATABASE_URL` | PostgreSQL connection string | ✅ |
| `OPENAI_BASE_URL` | OpenAI API base URL (for compatible APIs) | ❌ |
| `CORS_ORIGINS` | Allowed CORS origins, comma-separated | ❌ |

### In-App Settings

Configure in the **Settings** page:
- 🔑 API Keys management
- 🤖 AI model selection
- ⏰ Auto sync time and timezone
- 🎨 Theme toggle (light/dark/system)

---

## 🐳 Docker Deployment

```bash
# Start all services
pnpm docker:up

# Stop services
pnpm docker:down
```

---

## 🤝 Contributing

Issues and Pull Requests are welcome!

---

## 📄 License

[MIT](LICENSE)

---

<div align="center">

**If this project helps you, please give it a ⭐ Star!**

Made with ❤️ by [xfrrn](https://github.com/xfrrn)

</div>
