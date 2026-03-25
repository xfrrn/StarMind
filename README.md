[English](./README_EN.md) | 中文

<div align="center">

# StarMind ⭐🧠

**AI-Powered GitHub Star Manager**

用自然语言搜索你的 GitHub Star 收藏，让 AI 帮你快速找到对的项目。

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## ✨ 功能特性

### 🔍 AI 语义搜索
用自然语言提问，AI 理解你的意图并找到最匹配的项目。
> *"找一个用 React 做的 UI 组件库"*
> *"有什么好用的 Python 爬虫框架"*
> *"最近很火的 AI 项目有哪些"*

### 🤖 智能分析
自动为每个仓库生成：
- 📌 智能标签和分类
- 📝 一句话摘要
- 🔧 特性识别（是否有 UI、API 等）
- 📈 活跃度评估

### 📊 Dashboard 数据洞察
- 编程语言分布
- 项目分类统计
- Star 数分布
- 活跃度分析

### 📁 Collection 收藏夹
- 创建自定义收藏夹
- 为收藏的项目添加个人笔记
- 生成分享链接

### 🔄 自动同步
- 定时自动同步（可配置时间）
- 增量同步，节省时间
- 实时进度追踪

### 🌙 深色模式
完整的深色模式支持，保护你的眼睛。

---

## 🛠 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | React 18, Vite, TailwindCSS, Framer Motion, Recharts |
| **后端** | FastAPI, SQLAlchemy (async), APScheduler |
| **数据库** | PostgreSQL + pgvector |
| **AI** | OpenAI (GPT-4o-mini + text-embedding-3-small) |
| **包管理** | uv (Python), pnpm (Node.js) |

---

## 🚀 快速开始

### 环境要求

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)（Python 包管理器）
- Node.js 18+ 和 pnpm
- PostgreSQL 并安装 [pgvector](https://github.com/pgvector/pgvector) 扩展
- OpenAI API Key
- GitHub Personal Access Token

### 1. 克隆项目

```bash
git clone https://github.com/xfrrn/StarMind.git
cd StarMind
```

### 2. 启动后端

```bash
cd backend

# 复制并配置环境变量
cp .env.example .env
# 编辑 .env，填入你的配置：
# - GITHUB_TOKEN (GitHub Personal Access Token)
# - OPENAI_API_KEY (OpenAI API Key)
# - DATABASE_URL (PostgreSQL 连接字符串)

# 安装依赖
uv sync

# 启动服务
uv run uvicorn main:app --reload --port 8000
```

> **提示**：后端启动时会自动创建数据库、启用 pgvector 扩展并建好所有表。

### 3. 启动前端

```bash
cd packages/frontend

# 安装依赖
pnpm install

# 启动开发服务器
pnpm dev
```

打开 http://localhost:5173 开始使用！

### 4. 同步你的 Star

1. 进入 **Sync Center**
2. 点击 **Sync Now** 同步仓库
3. 点击 **Run AI Analysis** 进行 AI 分析
4. 开始用自然语言搜索吧！🚀

---

## 📁 项目结构

```
StarMind/
├── backend/                    # Python 后端
│   ├── routers/               # API 路由
│   ├── services/              # 业务逻辑
│   ├── models/                # 数据库模型
│   └── core/                  # 核心模块（GitHub API、AI 等）
├── packages/
│   └── frontend/              # React 前端
│       └── src/app/
│           ├── pages/         # 页面组件
│           ├── components/    # 通用组件
│           └── api.ts         # API 客户端
├── CLAUDE.md                  # Claude Code 开发指南
└── README.md
```

---

## ⚙️ 配置说明

### 环境变量

| 变量 | 说明 | 必填 |
|------|------|------|
| `GITHUB_TOKEN` | GitHub Personal Access Token | ✅ |
| `OPENAI_API_KEY` | OpenAI API Key | ✅ |
| `DATABASE_URL` | PostgreSQL 连接字符串 | ✅ |
| `OPENAI_BASE_URL` | OpenAI API 地址（用于兼容 API） | ❌ |
| `CORS_ORIGINS` | CORS 允许的源，逗号分隔 | ❌ |

### 应用内设置

在 **Settings** 页面可以配置：
- 🔑 API Keys 管理
- 🤖 AI 模型选择
- ⏰ 自动同步时间和时区
- 🎨 主题切换（亮色/暗色/跟随系统）

---

## 🐳 Docker 部署

```bash
# 启动所有服务
pnpm docker:up

# 停止服务
pnpm docker:down
```

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 License

[MIT](LICENSE)

---

<div align="center">

**如果这个项目对你有帮助，请给一个 ⭐ Star！**

Made with ❤️ by [xfrrn](https://github.com/xfrrn)

</div>
