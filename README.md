[English](./README_EN.md) | 中文

# StarMind ⭐🧠

基于 AI 的 GitHub 标星项目智能分析器。用自然语言搜索你的 Star 收藏，让 AI 帮你快速找到对的项目。

## 项目结构

```
StarMind/
├── frontend/          # Vite + React + TailwindCSS 前端
├── backend/           # FastAPI + PostgreSQL + pgvector 后端
└── .gitignore
```

## 快速开始

### 环境要求

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)（Python 包管理器）
- Node.js 18+ 和 pnpm / npm
- PostgreSQL 并安装 [pgvector](https://github.com/pgvector/pgvector) 扩展
- OpenAI API Key
- GitHub Personal Access Token

### 1. 启动后端

```bash
cd backend

# 复制并配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 GITHUB_TOKEN、OPENAI_API_KEY、DATABASE_URL

# 安装依赖
uv sync

# 启动服务（数据库和表会在启动时自动创建）
uv run uvicorn main:app --reload --port 8000
```

> **提示**：后端启动时会自动创建数据库、启用 pgvector 扩展并建好所有表。只需确保 PostgreSQL 在运行，且 `DATABASE_URL` 中的用户有创建数据库的权限即可。

### 2. 启动前端

```bash
cd frontend

# 安装依赖
pnpm install   # 或 npm install

# 启动开发服务器（/api 请求自动代理到后端）
pnpm dev       # 或 npm run dev
```

打开 http://localhost:5173

### 3. 同步你的 Star

1. 在应用中进入 **Sync Center**
2. 点击 **Force Sync Now**
3. 等待 AI 分析你的标星项目
4. 开始用 AI 搜索吧！🚀

## 功能特性

- 🔍 **AI 语义搜索** — 用自然语言提问，找到匹配的项目
- 🤖 **AI 智能分析** — 自动为每个项目生成标签、分类和摘要
- 📊 **智能筛选** — 按语言、分类、特性、活跃度多维过滤
- 🔄 **GitHub 同步** — 增量同步 + 实时进度追踪
- ⚙️ **偏好设置** — 可配置的 AI 分析选项

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React, Vite, TailwindCSS, Framer Motion |
| 后端 | FastAPI, SQLAlchemy (async) |
| 数据库 | PostgreSQL + pgvector |
| AI | OpenAI (gpt-4o-mini + text-embedding-3-small) |
| 包管理 | uv (Python), pnpm (Node.js) |
