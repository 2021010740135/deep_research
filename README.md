下面是适合放到 GitHub 根目录的 `README.md` 内容。它只描述项目、架构与本地部署，不包含简历话术、量化成果、测试结果或你的实际内部资料。

```markdown
# DeepResearch

基于 LangGraph 的多 Agent 深度研究助手。系统将用户问题路由到直接问答或研究工作流；对于研究型问题，会结合网络搜索与本地 RAG 知识库收集证据，经过分析与必要的补充检索后生成结构化回答。

## 功能概览

- 意图路由：区分直接问答与需要深入调研的问题。
- 多 Agent 工作流：规划、网络检索、本地知识检索、证据处理、分析、反思补搜与报告生成。
- 双源检索：
  - 网络检索：通过博查搜索获取公开网页资料。
  - 本地检索：将内部文档向量化后写入 Milvus，通过 RAG 召回相关片段。
- 本地知识库入库：支持 `.md`、`.markdown`、`.txt` 和文本型 `.pdf`。
- 会话与记忆：使用 PostgreSQL 持久化会话相关数据，可选 Redis 作为相关后端能力。
- Web 界面：Vue 3 + Vite 前端，通过 FastAPI 调用后端接口。

## 架构

```text
用户请求
  |
  v
FastAPI API
  |
  v
Intent Router
  |------------------------------|
  |                              |
直接问答                    研究工作流
                                 |
                                 v
                              Planner
                                 |
                 |---------------|---------------|
                 v                               v
            Web Search                       Local RAG
                 |                               |
                 |---------------|---------------|
                                 v
                          Evidence Judge
                                 |
                                 v
                              Analyst
                                 |
                    证据不足？--- 是 ---> Reflect / 补充检索
                                 |
                                否
                                 |
                                 v
                               Writer
                                 |
                                 v
                              最终回答
```

核心组件：

| 模块 | 职责 |
| --- | --- |
| `app/mult_agents/graph.py` | 定义 LangGraph 工作流、节点和条件路由 |
| `app/mult_agents/nodes.py` | 实现各 Agent 节点的具体处理逻辑 |
| `app/mult_agents/tools.py` | 封装网络搜索、本地检索等工具 |
| `app/mult_agents/rag/` | 本地文档分块、向量化、Milvus 检索与入库 |
| `app/mult_agents/memory/` | 短期记忆、长期记忆与会话上下文管理 |
| `app/backend/` | FastAPI 路由、请求模型和工作流服务 |
| `front/agent_front/` | Vue 前端应用 |

## 技术栈

- Python 3.10+
- FastAPI / Uvicorn
- LangGraph / LangChain
- 通义千问 DashScope
- Milvus
- PostgreSQL
- Redis
- Vue 3 / Vite
- Docker

## 前置条件

本地需要安装：

- Python 3.10 或更高版本
- [uv](https://docs.astral.sh/uv/)
- Node.js `20.19+` 或 `22.12+`
- Docker Desktop

系统依赖服务：

- Milvus：本地知识库向量检索
- PostgreSQL：会话、检查点和长期记忆存储
- Redis：可选的缓存/检查点相关后端
- DashScope API Key：LLM 与 Embedding 调用
- 博查 API Key：可选；未配置时跳过网络搜索

> Neo4j、MySQL 不属于当前主流程的必要依赖，不需要为了启动本项目额外部署。

## 1. 克隆并安装依赖

```bash
git clone <YOUR_REPOSITORY_URL>
cd deep_research
```

安装 Python 依赖：

```bash
uv sync
```

安装前端依赖：

```bash
cd front/agent_front
npm install
cd ../..
```

## 2. 启动基础服务

### PostgreSQL

```bash
docker run -d \
  --name deepresearch-postgres \
  --restart unless-stopped \
  -p 5432:5432 \
  -e POSTGRES_USER=deepresearch \
  -e POSTGRES_PASSWORD=change-me \
  -e POSTGRES_DB=deepresearch \
  -v deepresearch-postgres:/var/lib/postgresql/data \
  postgres:16
```

### Redis

```bash
docker run -d \
  --name deepresearch-redis \
  --restart unless-stopped \
  -p 6379:6379 \
  -e ALLOW_EMPTY_PASSWORD=yes \
  bitnami/redis:latest
```

### Milvus

Milvus 依赖 `etcd` 和 `MinIO`。可使用官方 Standalone Docker Compose 部署方式启动，确保以下端口可访问：

- `19530`：Milvus gRPC
- `9091`：Milvus 健康检查
- `9000`、`9001`：MinIO
- `8000`：Attu 可视化管理界面，可选

启动后检查容器：

```bash
docker ps
```

确认 PostgreSQL、Redis、Milvus 相关容器均为运行状态。

## 3. 配置环境变量

复制环境变量模板：

```bash
cp .env.example .env
```

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

编辑 `.env`，至少配置以下内容：

```dotenv
# DashScope：必填
DASHSCOPE_API_KEY=your_dashscope_api_key
MODEL=qwen-plus

# 博查网络搜索：可选；未配置时系统跳过网络检索
BOCHA_API_KEY=your_bocha_api_key

# 用户与会话标识
TENANT_ID=default_tenant
USER_ID=default_user
THREAD_ID=default

# 工作流
MAX_ITERATIONS=3

# Memory
ENABLE_MEMORY=true
SHORT_TERM_BACKEND=postgres
LONG_TERM_BACKEND=postgres
CHECKPOINTER_BACKEND=postgres

# PostgreSQL
POSTGRES_DSN=postgresql://deepresearch:change-me@127.0.0.1:5432/deepresearch

# Redis
REDIS_URL=redis://127.0.0.1:6379/0

# Milvus
ENABLE_MILVUS=true
MILVUS_HOST=127.0.0.1
MILVUS_PORT=19530
MILVUS_COLLECTION=mult_agent_memory
```

如果本机开启了系统代理，建议额外添加：

```dotenv
NO_PROXY=localhost,127.0.0.1,dashscope.aliyuncs.com,.aliyuncs.com,api.bocha.cn,.bocha.cn
no_proxy=localhost,127.0.0.1,dashscope.aliyuncs.com,.aliyuncs.com,api.bocha.cn,.bocha.cn
```

## 4. 准备并导入本地知识库

本地资料默认按主题存放：

```text
data/
└── rag/
    └── topics/
        └── <topic-name>/
            ├── papers/
            ├── notes/
            ├── competitors/
            └── web_clips/
```

例如：

```text
data/rag/topics/ai-agent/
├── papers/
│   └── agent-survey.pdf
├── notes/
│   └── research-notes.md
└── competitors/
    └── product-comparison.txt
```

支持的格式：

- Markdown：`.md`、`.markdown`
- 纯文本：`.txt`
- PDF：仅支持可提取文字的文本型 PDF；扫描件 PDF 需要先经过 OCR

先检查待入库文件，不写入数据库：

```bash
uv run python app/mult_agents/rag/ingest.py --topic ai-agent --dry-run
```

执行入库：

```bash
uv run python app/mult_agents/rag/ingest.py --topic ai-agent
```

也可以指定任意文件或目录：

```bash
uv run python app/mult_agents/rag/ingest.py --input data/rag/topics/ai-agent
```

> 实际业务资料、内部文档和私有 PDF 建议只保存在本地或对象存储中，不提交到 Git 仓库。

## 5. 启动后端

在项目根目录执行：

```bash
uv run uvicorn app_main:app --app-dir app --host 0.0.0.0 --port 8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

预期接口地址：

- `GET /health`
- `POST /api/v1/research/run`
- `POST /api/v1/research/stream`

## 6. 启动前端

打开新的终端：

```bash
cd front/agent_front
npm run dev
```

访问：

```text
http://localhost:5173
```

Vite 已配置代理：

- `/api` 转发到后端 `http://127.0.0.1:8000`
- `/health` 转发到后端 `http://127.0.0.1:8000`

## 常见问题

### 后端提示缺少 `DASHSCOPE_API_KEY`

确认项目根目录存在 `.env`，并且其中配置了有效的：

```dotenv
DASHSCOPE_API_KEY=your_dashscope_api_key
```

### `vite` 不是内部或外部命令

前端依赖没有安装完成。在 `front/agent_front` 下执行：

```bash
npm install
npm run dev
```

### PDF 无法入库

当前仅支持带文字层的 PDF。若为扫描版或图片型 PDF，需要先通过 OCR 转为文本，再走现有入库流程。

### 无法连接 Milvus、PostgreSQL 或 Redis

先检查 Docker 服务状态：

```bash
docker ps
```

并确认 `.env` 中的主机、端口、用户名和密码与容器配置一致。

## 许可证

本项目仅用于学习与研究用途。使用前请根据实际情况补充许可证文件。
```
