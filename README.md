# AI 绘图提示词助手

一个本地运行的 AI 绘图提示词工具，包含三个功能：

1. **生成提示词** — 输入中文描述，DeepSeek 生成可直接用于 Midjourney / Stable Diffusion 的英文提示词
2. **保存提示词** — 把英文提示词按 `,` 切分后入库，自动调用 DeepSeek 翻译为中文
3. **提示词库** — 按使用次数降序展示所有积累的提示词，支持搜索、删除

## 技术栈

- **前端**：Vue 3 + Vite + TypeScript + Element Plus（端口 `4163`）
- **后端**：FastAPI + SQLAlchemy 2.0 async + asyncpg（端口 `4165`）
- **数据库**：PostgreSQL
- **AI**：DeepSeek API（生成 + 翻译复用）

## 仓库结构

```
Project_Prompt/
├── backend/        # FastAPI 后端
└── frontend/       # Vue 3 前端
```

## 启动步骤

### 0. 准备

- Python 3.10+
- Node.js 18+
- PostgreSQL 已启动
- DeepSeek API Key（在 [https://platform.deepseek.com](https://platform.deepseek.com) 申请）

### Windows 11 快速启动

仓库根目录提供了三个 `.bat` 脚本（双击即可运行）：

| 脚本 | 用途 |
|---|---|
| `setup.bat` | 首次配置：创建 venv、装 pip 与 npm 依赖、生成 `.env` 模板 |
| `start.bat` | 日常启动：开两个窗口分别跑后端和前端，5 秒后自动打开浏览器 |
| `stop.bat` | 停止服务：关闭 4165 / 4163 端口的进程和启动窗口 |

**首次使用流程**：
1. 双击 `setup.bat`，按提示把 `backend\.env` 里的 `DEEPSEEK_API_KEY` 和 `DATABASE_URL` 填好
2. 在 PostgreSQL 里创建 `promptdb` 库（`psql -U postgres -c "CREATE DATABASE promptdb;"`）
3. 双击 `start.bat`，浏览器自动打开 [http://localhost:4163](http://localhost:4163)

### macOS / Linux 命令行启动

#### 1. 创建数据库

```bash
psql -U postgres -c "CREATE DATABASE promptdb;"
```

#### 2. 后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY 与 DATABASE_URL
uvicorn app.main:app --reload --port 4165
```

第一次启动时 SQLAlchemy 会自动建表，无需手动跑 migration。

如果偏好 Alembic 管理 schema：

```bash
alembic revision --autogenerate -m "init"
alembic upgrade head
```

#### 3. 前端

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 [http://localhost:4163](http://localhost:4163)。

## 环境变量

`backend/.env`：

| 变量 | 说明 | 默认值 |
|---|---|---|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | （必填） |
| `DEEPSEEK_BASE_URL` | DeepSeek API base URL | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 使用的模型 | `deepseek-chat` |
| `DATABASE_URL` | PostgreSQL 异步连接串 | `postgresql+asyncpg://postgres:postgres@localhost:5432/promptdb` |
| `APP_PORT` | 后端端口 | `4165` |
| `ALLOWED_ORIGIN` | 允许的前端 origin（CORS） | `http://localhost:4163` |
| `TRANSLATE_CONCURRENCY` | 翻译并发上限 | `5` |
| `REQUEST_TIMEOUT` | DeepSeek 请求超时（秒） | `30` |

## API 一览

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/generate` | 调用 DeepSeek 生成英文提示词 |
| `POST` | `/api/prompts/save` | 保存英文提示词（按 `,` 切分 + 翻译） |
| `GET` | `/api/library?page=1&page_size=20&search=` | 提示词库列表（按 `usage_count` 降序） |
| `DELETE` | `/api/library/{id}` | 删除单条提示词 |
| `GET` | `/api/health` | 健康检查 |

Swagger 文档：[http://localhost:4165/docs](http://localhost:4165/docs)

## 端到端验证

```bash
# 1. 生成
curl -X POST http://localhost:4165/api/generate \
     -H "Content-Type: application/json" \
     -d '{"system_prompt":"你是一个AI绘图提示词助手","user_input":"a cat in a hat"}'

# 2. 保存
curl -X POST http://localhost:4165/api/prompts/save \
     -H "Content-Type: application/json" \
     -d '{"raw_text":"masterpiece, best quality, 1girl, red dress, sunset"}'

# 3. 库
curl "http://localhost:4165/api/library?page=1&page_size=20"
```

## 失败兜底

- **DeepSeek 不可达**：`/api/generate` 返回 502；`/api/prompts/save` 仍然入库，但 `text_zh` 为 NULL，响应中 `failed_translations` 大于 0。
- **数据库不可达**：写接口返回 503，读接口返回 500；前端用 `ElMessage.error` 弹窗提示。
- **重复保存**：相同片段（不区分大小写）`usage_count` 自增 1，`last_used_at` 刷新。