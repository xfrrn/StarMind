# SurveyAgent RAG 设计分析

> 本文档详细分析了 SurveyAgent 项目的 RAG（检索增强生成）架构设计，供借鉴学习。

---

## 1. 项目整体结构

**核心组件分布：**

```
app/
├── core/knowledge_base/          # RAG核心模块
│   ├── vec_db/                   # 向量数据库实现
│   ├── retrieval/                # 检索器
│   ├── chunking/                 # 文档分块
│   └── parsers/                  # 文档解析
├── services/                      # 业务服务层
│   ├── knowledge_base_service.py  # 知识库服务
│   ├── embedding_service.py       # 嵌入服务
│   ├── system_kb_service.py       # 系统知识库服务
│   └── document_processor.py      # 文档处理
├── tools/                         # AI工具集成
│   └── builtin/
│       └── knowledge_base.py      # 知识库查询工具
├── api/v1/
│   └── chat.py                    # 聊天API（LLM集成）
└── database.py                    # 数据模型
```

---

## 2. 向量数据库实现

### 2.1 技术选型

| 组件 | 选择 | 说明 |
|------|------|------|
| 数据库 | PostgreSQL + pgvector | 复用现有数据库，无需额外维护 |
| 相似度 | 余弦相似度 | `<=>` 操作符 |
| 索引 | IVFFlat | 适合≤2000维向量 |

### 2.2 核心表结构

```sql
CREATE TABLE kb_chunks (
    chunk_id VARCHAR(36) PRIMARY KEY,
    doc_id VARCHAR(36),           -- 文档ID
    kb_id VARCHAR(36),            -- 知识库ID
    chunk_index INT,              -- 块序号
    content TEXT,                 -- 文本内容
    embedding vector(1024),       -- 向量（可配置维度）
    metadata JSONB                -- 元数据
);
```

### 2.3 检索SQL

```sql
SELECT chunk_id, content, metadata,
       1 - (embedding <=> '{query_vector}'::vector(1024)) as score
FROM kb_chunks
WHERE kb_id = '{kb_id}' AND embedding IS NOT NULL
ORDER BY embedding <=> '{query_vector}'::vector(1024)
LIMIT {top_k}
```

### 2.4 核心方法

| 方法 | 功能 |
|------|------|
| `insert()` | 单条插入，支持冲突更新 |
| `insert_batch()` | 批量插入 |
| `retrieve()` | 余弦相似度检索，支持文档过滤 |
| `delete_by_*` | 级联删除（chunk/doc/kb级别） |

---

## 3. 文档处理流程

### 3.1 文档解析器

| 格式 | 解析器 | 依赖库 | 特性 |
|------|--------|--------|------|
| `.txt/.md` | TextParser | 标准库 | 多编码检测 (utf-8, gbk, gb2312, latin-1) |
| `.pdf` | PDFParser | pypdf | 分页提取，页码标记 |
| `.docx` | DOCXParser | python-docx | 段落+表格提取 |

### 3.2 递归分块策略

**分隔符优先级：**
```
1. \n\n    (段落)
2. \n      (换行)
3. 。      (中文句号)
4. .       (英文句号)
5. ！？；， (中文标点)
6. !?;,    (英文标点)
7. 空格
8. 字符级
```

**关键参数：**
```python
RecursiveCharacterChunker(
    chunk_size: int = 512,      # 块大小（字符）
    chunk_overlap: int = 50,    # 块之间重叠
    keep_separator: bool = True # 保留分隔符
)
```

### 3.3 完整处理链

```
文件上传 → 格式解析 → 递归分块 → 批量获取Embedding → 存入向量DB
    ↓
[音频特殊处理]
音频 → ASR转录 → LLM润色 → 保存MD → 按普通文档处理
```

**处理阶段枚举：**
```python
class ProcessingStage(str, Enum):
    PENDING = "pending"
    PARSING = "parsing"
    TRANSCRIBING = "transcribing"  # ASR
    REFINING = "refining"          # LLM润色
    CHUNKING = "chunking"
    VECTORING = "vectoring"
    COMPLETED = "completed"
    FAILED = "failed"
```

---

## 4. 嵌入服务

### 4.1 支持的模型维度

```python
EMBEDDING_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
    "text-embedding-002": 768,
}
```

### 4.2 批处理机制

```python
batch_size = 100  # 单批100条

for i in range(0, len(texts), batch_size):
    batch = texts[i:i+batch_size]
    embeddings = await embedding_api(batch)
```

---

## 5. 检索策略

### 5.1 三种检索触发场景

| 场景 | 触发方式 | 说明 |
|------|----------|------|
| 工具调用 | LLM主动 | LLM决定何时调用 `query_knowledge_base` |
| 强制查询 | 用户设置 | `force_kb_query=True` 时自动检索 |
| 阶段检索 | 自动 | 根据L1-L5调研阶段自动注入知识库 |

### 5.2 检索参数

```python
KnowledgeRetriever(
    kb_id: str,
    top_k: int = 5,              # 返回结果数
    score_threshold: float = 0.0 # 相似度阈值过滤
)
```

### 5.3 结果格式化

```
[知识库文档1: document_name] (相似度: 0.85)
文档内容片段...

---

[知识库文档2: document_name] (相似度: 0.72)
文档内容片段...
```

---

## 6. LLM集成

### 6.1 消息堆栈结构

```python
context_messages = [
    # 1. 系统消息 - 工具调用指南
    {"role": "system", "content": TOOL_CALL_PROMPT},

    # 2. 系统消息 - 阶段上下文
    {"role": "system", "content": f"当前阶段: {stage}\n{stage_prompt}"},

    # 3. 系统消息 - 知识库检索结果
    {"role": "system", "content": f"参考资料:\n{kb_context}"},

    # 4-N. 历史消息（压缩后）
    {"role": "user/assistant", "content": "..."},

    # N. 当前用户消息
    {"role": "user", "content": request.content}
]
```

### 6.2 工具调用循环

```python
for iteration in range(5):  # 最多5次迭代
    # 1. 调用LLM
    async for chunk in llm_stream():
        accumulate_response()

    # 2. 检测工具调用
    if not tool_calls:
        break

    # 3. 执行工具
    for call in tool_calls:
        result = await execute_tool(call)
        messages.append({"role": "tool", "content": result})

    # 4. 继续迭代（LLM处理工具结果）
```

### 6.3 知识库工具定义

```python
@llm_tool(name="query_knowledge_base")
async def query_knowledge_base(
    query: str,      # 搜索关键词
    top_k: int = 5   # 返回数量
) -> str:
    """从知识库检索信息，当用户提到知识库或上传文档时调用"""
    results = await KnowledgeBaseService.retrieve(query, kb_ids)
    return format_results(results)
```

---

## 7. 上下文压缩

### 7.1 压缩策略

| 策略 | 实现 |
|------|------|
| truncate | 删除最早消息 |
| halving | 保留后半部分 |
| llm_summary | LLM总结前文 |

### 7.2 触发条件

```python
if token_count > max_tokens * compression_threshold:
    apply_compression()
```

### 7.3 Token估算

```python
def estimate_tokens(text: str) -> int:
    # 中文: 1.5 字符/token
    # 英文: 4 字符/token
    # 图片: 85 token
```

---

## 8. 完整RAG工作流

### 8.1 文档上传流程

```
文件上传
    ↓
格式检测 → 选择解析器 → 提取文本
    ↓
递归分块 → 生成chunk列表
    ↓
批量获取Embedding
    ↓
存入PostgreSQL (pgvector)
    ↓
更新知识库统计
```

### 8.2 用户提问流程

```
用户消息
    ↓
获取历史消息（压缩处理）
    ↓
获取阶段上下文（L1-L5系统知识库）
    ↓
注入系统提示词 + 工具Schema
    ↓
LLM处理 → 检测工具调用
    ↓
[query_knowledge_base工具执行]
    ↓
查询文本 → 获取Query Embedding
    ↓
向量相似度检索 (pgvector)
    ↓
返回top-k结果 → 格式化
    ↓
结果注入为工具消息
    ↓
LLM继续处理（再次迭代）
    ↓
流式输出回复
```

---

## 9. 关键配置

```python
# Embedding
EMBEDDING_API_URL: str          # 嵌入API地址
EMBEDDING_API_KEY: str          # API密钥
EMBEDDING_MODEL: str            # 模型名称
EMBEDDING_DIMENSION: int        # 向量维度

# 知识库
KB_UPLOAD_DIR: str              # 上传目录
KB_MAX_FILE_SIZE: int           # 最大文件大小

# 上下文
CONTEXT_MAX_TOKENS: int                    # 消息最大tokens
CONTEXT_COMPRESSION_THRESHOLD: float       # 压缩阈值
CONTEXT_COMPRESSION_STRATEGY: str          # 压缩策略
```

---

## 10. 核心文件索引

| 功能 | 文件路径 |
|------|---------|
| 向量数据库 | `app/core/knowledge_base/vec_db/pgvector_impl/vec_db.py` |
| 检索器 | `app/core/knowledge_base/retrieval/retriever.py` |
| 分块器 | `app/core/knowledge_base/chunking/recursive.py` |
| 文档解析 | `app/core/knowledge_base/parsers/` |
| 嵌入服务 | `app/services/embedding_service.py` |
| 知识库服务 | `app/services/knowledge_base_service.py` |
| 上下文管理 | `app/services/context_manager.py` |
| LLM集成 | `app/api/v1/chat.py` |
| 知识库工具 | `app/tools/builtin/knowledge_base.py` |

---

## 11. 设计亮点总结

### 优势

| 特性 | 说明 |
|------|------|
| **多格式支持** | PDF、DOCX、TXT、Markdown、音频 |
| **递归分块** | 多级分隔符，保留语义完整性 |
| **系统知识库** | 按调研阶段预置领域知识 |
| **三种检索模式** | 工具调用 + 强制查询 + 阶段检索 |
| **音频处理** | ASR + LLM润色整合 |
| **上下文压缩** | 多策略应对长对话 |
| **流式响应** | SSE实时输出 |

### 架构特点

```
分层设计: Parser → Chunker → Embedding → VecDB → Retriever → LLM
全异步: async/await 支持并发
可扩展: 易于添加新解析器、分块策略、压缩策略
阶段感知: 根据L1-L5阶段动态选择知识库
```

---

## 12. 借鉴建议

1. **向量数据库选型**: pgvector适合中小规模，简单部署；大规模考虑 Milvus/Qdrant
2. **分块策略**: 中文场景需特别注意分隔符优先级设置
3. **检索触发**: 多种触发方式结合，兼顾灵活性和可控性
4. **上下文管理**: Token估算和压缩策略对长对话至关重要
5. **工具集成**: 让LLM通过工具主动检索，比纯注入更灵活

---

*文档生成时间: 2026-03-22*
