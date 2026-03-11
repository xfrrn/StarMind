# StarMind AI 编程规范

本文档为 AI 编程助手提供项目上下文和编码规范，以确保代码风格一致、结构清晰。

---

## 项目概述

StarMind 是一个 GitHub 标星项目智能分析工具，帮助用户通过 AI 语义搜索快速找到自己收藏的项目。

### 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React 18 + Vite + TailwindCSS 4 + Framer Motion |
| 后端 | Python 3.11+ / FastAPI / SQLAlchemy (async) |
| 数据库 | PostgreSQL + pgvector |
| AI | OpenAI API (gpt-4o-mini + text-embedding-3-small) |
| 包管理 | uv (Python), pnpm (Node.js) |

### 仓库结构

```
StarMind/
├── frontend/                # React 前端
│   ├── src/app/
│   │   ├── api.ts           # 统一 API 客户端
│   │   ├── data.ts          # 类型定义
│   │   ├── routes.tsx       # 路由配置
│   │   ├── pages/           # 页面组件
│   │   └── components/      # 可复用组件
│   └── vite.config.ts       # Vite 配置（含 /api 代理）
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 环境变量配置
│   ├── models/              # 数据库模型
│   ├── services/            # 业务逻辑
│   └── routers/             # API 路由
└── README.md
```

---

## 后端编码规范

### Python 风格

- Python 版本 ≥ 3.11，使用现代语法（`str | None`、`list[str]` 等）
- 使用 **async/await** 贯穿所有数据库和外部调用
- 使用 **类型注解** 标注所有函数签名
- 模块顶部写 **docstring** 说明模块职责
- 日志使用 `logging` 标准库，不使用 `print`

### 项目分层

```
routers/  → 接收 HTTP 请求、参数校验、调用 service、返回响应
services/ → 核心业务逻辑（GitHub API、AI 分析、同步流程）
models/   → SQLAlchemy 模型定义 + 数据库连接管理
config.py → 所有配置集中管理，通过 pydantic-settings 从 .env 加载
```

**规则：**
- Router 层不包含业务逻辑，仅做参数校验和调用 service
- Service 层不直接依赖 FastAPI（不导入 Request、Response 等）
- 数据库 session 通过 FastAPI Depends 注入，service 接收 `AsyncSession` 参数

### API 设计

- 所有 API 路径以 `/api/` 开头
- 使用 Pydantic `BaseModel` 定义请求和响应 schema
- 响应字段名使用 **camelCase** 以匹配前端（如 `hasUI`、`aiReason`、`activityLevel`）
- 列表接口统一返回 `{ items: [...], total: int, page: int, limit: int }` 格式
- 错误使用 `HTTPException` 抛出，附带有意义的 `detail`

### 数据库

- 使用 **SQLAlchemy 2.0 async** 风格（`select()`, `await session.execute()`）
- 表名使用 **小写复数**（`repositories`、`sync_logs`）
- 列名使用 **snake_case**
- 向量字段类型为 `Vector(1536)`（匹配 OpenAI text-embedding-3-small）
- JSONB 类型用于存储列表/字典数据（如 `tags`、`topics`）
- 数据库和表在启动时自动创建，参见 `models/database.py` 的 `init_db()`

### 新增 API 路由模板

```python
# routers/new_feature.py
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from models.database import get_db

router = APIRouter(prefix="/api", tags=["feature_name"])

class FeatureResponse(BaseModel):
    # 字段名用 camelCase
    fieldName: str = ""

@router.get("/feature", response_model=FeatureResponse)
async def get_feature(db: AsyncSession = Depends(get_db)):
    """简要描述此端点的作用。"""
    # 调用 service 层
    ...
```

新路由需在 `main.py` 中通过 `app.include_router(...)` 注册。

---

## 前端编码规范

### React / TypeScript

- 使用 **函数式组件** + **Hooks**
- 组件文件使用 **PascalCase**（`SearchPage.tsx`），工具文件使用 **camelCase**（`api.ts`）
- 所有 API 调用集中在 `api.ts`，页面组件不直接 `fetch`
- 类型定义在 `data.ts`，所有组件共享 `Repository` 接口
- 样式使用 **TailwindCSS 4**，遵循现有的 dark mode 模式（`dark:` 前缀）

### 页面组件模式

```tsx
// pages/NewPage.tsx
import React, { useState, useEffect } from 'react';
import { fetchSomething } from '../api';

export function NewPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSomething()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <LoadingSpinner />;
  }

  return <div>...</div>;
}
```

新页面需在 `routes.tsx` 中添加路由。

### API 客户端模式

```typescript
// 在 api.ts 中新增
export async function fetchNewThing(): Promise<NewType> {
  const resp = await fetch(`${API_BASE}/new-endpoint`);
  if (!resp.ok) throw new Error(`Failed: ${resp.statusText}`);
  return resp.json();
}
```

### UI 规范

- 配色：zinc 灰色系 + blue 品牌色
- 圆角：`rounded-lg`（小元素）/ `rounded-2xl`（卡片容器）
- 间距：`gap-6`、`p-6` 为基础单位
- 动画：使用 `framer-motion`（已安装为 `motion`）
- 加载态：统一使用 spinning border 动画
- 深色模式：每个颜色类都需要对应的 `dark:` 变体

---

## 环境配置

所有配置通过环境变量管理，定义在 `backend/config.py`：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `GITHUB_TOKEN` | GitHub PAT | 无 |
| `OPENAI_API_KEY` | OpenAI Key | 无 |
| `OPENAI_BASE_URL` | API 地址 | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | 聊天模型 | `gpt-4o-mini` |
| `OPENAI_EMBEDDING_MODEL` | 向量模型 | `text-embedding-3-small` |
| `DATABASE_URL` | PostgreSQL 连接串 | `postgresql+asyncpg://postgres:postgres@localhost:5432/starmind` |

新增配置项时：在 `config.py` 的 `Settings` 类中添加字段，在 `.env.example` 中添加示例。

---

## 关键约定总结

1. **后端 async 优先** — 所有 I/O 操作必须 async
2. **前后端字段名映射** — DB 用 snake_case，API 响应用 camelCase
3. **API 集中管理** — 前端所有请求经过 `api.ts`，后端路由经过 `routers/`
4. **类型安全** — Python 用类型注解，TypeScript 用接口定义
5. **自动化数据库** — 启动时自动建库建表，不依赖手动迁移
6. **新增功能流程** — 新 model → 新 service → 新 router → `main.py` 注册 → 前端 `api.ts` + 页面
