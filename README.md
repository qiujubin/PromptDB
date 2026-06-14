# AI 绘图提示词助手

一个本地运行的 AI 绘图提示词工具，四个功能模块：

1. **生成提示词** — 输入中文描述，DeepSeek 生成可直接用于 Midjourney / Stable Diffusion 的英文提示词
2. **保存提示词** — 把英文提示词按 `,` 切分后入库，自动调用 DeepSeek 翻译为中文，并用 AI 分配层级标签
3. **提示词库** — 卡片式浏览所有积累的提示词，支持多选批量操作、按标签筛选、手动编辑标签
4. **标签管理** — 树形维护「分类 → 子标签」两级体系，支持重命名、删除；提供「批量补打标签」按钮为旧数据补全 AI 标签

## 技术栈

- **前端**：Vue 3 + Vite + TypeScript + Element Plus（端口 `4163`）
- **后端**：FastAPI + SQLAlchemy 2.0 async + asyncpg（端口 `4165`）
- **数据库**：PostgreSQL
- **AI**：DeepSeek API（生成 / 翻译 / 打标签复用）

## 仓库结构

```
Project_Prompt/
├── backend/
│   ├── app/
│   │   ├── models.py            # Prompt / Tag / PromptTag
│   │   ├── schemas.py
│   │   ├── routers/
│   │   │   ├── generate.py
│   │   │   ├── prompts.py       # /save 并行调用翻译 + 自动打标
│   │   │   ├── library.py       # 列表 + 单删 + 批量删除
│   │   │   └── tags.py          # 标签 CRUD + 批量补打
│   │   └── services/
│   │       ├── deepseek.py      # generate / translate_batch
│   │       └── tagger.py        # auto_tag_batch（复用 translate_concurrency）
│   ├── alembic/                 # 未启用，schema 由 create_all 管理
│   └── .env
└── frontend/
    └── src/
        ├── api/
        │   ├── generate.ts
        │   ├── prompts.ts
        │   ├── library.ts
        │   └── tags.ts
        ├── components/
        │   ├── CopyButton.vue
        │   ├── PromptOutputCard.vue
        │   └── TagChips.vue
        ├── views/
        │   ├── GeneratorView.vue
        │   ├── SaverView.vue
        │   ├── LibraryView.vue    # 卡片网格 + 多选 + 标签筛选 + 编辑抽屉
        │   └── TagsView.vue       # 分类/子标签管理 + 批量补打
        └── router/index.ts
```

## 启动步骤

### 0. 准备

- Python 3.10+
- Node.js 18+
- PostgreSQL 已启动
- DeepSeek API Key（在 [https://platform.deepseek.com](https://platform.deepseek.com) 申请）

### 1. 创建数据库

```bash
psql -U postgres -c "CREATE DATABASE promptdb;"
```

### 2. 后端

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
# source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY 与 DATABASE_URL

uvicorn app.main:app --reload --port 4165
```

第一次启动时 SQLAlchemy 会自动建表（`prompts` / `tags` / `prompt_tags`），无需手动跑 migration。

如果偏好 Alembic 管理 schema：

```bash
alembic revision --autogenerate -m "init"
alembic upgrade head
```

### 3. 前端

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 [http://localhost:4163](http://localhost:4163)。

也提供了 Windows 一键脚本：`setup.bat`（首次安装） / `start.bat`（启动） / `stop.bat`（停止）。

## 环境变量

`backend/.env`：

| 变量                    | 说明                      | 默认值                                                           |
| ----------------------- | ------------------------- | ---------------------------------------------------------------- |
| `DEEPSEEK_API_KEY`      | DeepSeek API 密钥         | （必填）                                                         |
| `DEEPSEEK_BASE_URL`     | DeepSeek API base URL     | `https://api.deepseek.com`                                       |
| `DEEPSEEK_MODEL`        | 使用的模型                | `deepseek-chat`                                                  |
| `DATABASE_URL`          | PostgreSQL 异步连接串     | `postgresql+asyncpg://postgres:postgres@localhost:5432/promptdb` |
| `APP_PORT`              | 后端端口                  | `4165`                                                           |
| `ALLOWED_ORIGIN`        | 允许的前端 origin（CORS） | `http://localhost:4163`                                          |
| `TRANSLATE_CONCURRENCY` | 翻译 / 打标签并发上限     | `5`                                                              |
| `REQUEST_TIMEOUT`       | DeepSeek 请求超时（秒）   | `30`                                                             |

## API 一览

### 提示词

| 方法     | 路径                                       | 说明                                                                 |
| -------- | ------------------------------------------ | -------------------------------------------------------------------- |
| `POST`   | `/api/generate`                            | 调用 DeepSeek 生成英文提示词                                         |
| `POST`   | `/api/prompts/save`                        | 保存英文提示词（按 `,` 切分 + 翻译 + 自动打标，并行执行）            |
| `GET`    | `/api/library`                             | 提示词库列表，按 `usage_count` 降序，可按 `tag_id` / `search` 过滤   |
| `DELETE` | `/api/library/{id}`                        | 删除单条提示词                                                       |
| `POST`   | `/api/library/bulk-delete`                 | 批量删除，body `{ "ids": [1,2,3] }`，返回 `{ "deleted": N }`         |
| `POST`   | `/api/prompts/{id}/tags`                   | 替换某条提示词的标签集合，body `{ "tag_ids": [3,5] }`                |
| `POST`   | `/api/prompts/bulk-auto-tag`               | 对零标签的提示词批量调用 AI 打标，返回 `{ scanned, tagged, failed }`  |

### 标签

| 方法     | 路径                  | 说明                                                                  |
| -------- | --------------------- | --------------------------------------------------------------------- |
| `GET`    | `/api/tags`           | 标签树（按分类分组，附带每个标签的使用次数）                          |
| `POST`   | `/api/tags`           | 新建标签，body `{ "name": "手部姿势", "parent_id": 1 \| null }`       |
| `PATCH`  | `/api/tags/{id}`      | 重命名或改 parent（应用层校验最多 2 层：不能在叶子下再建子标签）       |
| `DELETE` | `/api/tags/{id}`      | 删除标签（含 `prompt_tags` 关联级联）。若有子标签会返回 400            |

### 健康

| 方法  | 路径            | 说明       |
| ----- | --------------- | ---------- |
| `GET` | `/api/health`   | 健康检查   |

Swagger 文档：[http://localhost:4165/docs](http://localhost:4165/docs)

## 端到端验证

```bash
# 1. 生成
curl -X POST http://localhost:4165/api/generate \
     -H "Content-Type: application/json" \
     -d '{"system_prompt":"你是一个AI绘图提示词助手","user_input":"a cat in a hat"}'

# 2. 保存（自动翻译 + 自动打标）
curl -X POST http://localhost:4165/api/prompts/save \
     -H "Content-Type: application/json" \
     -d '{"raw_text":"masterpiece, best quality, 1girl, red dress, sunset"}'

# 3. 库（按标签过滤示例：tag_id=2）
curl "http://localhost:4165/api/library?page=1&page_size=20&tag_id=2"

# 4. 标签树
curl http://localhost:4165/api/tags

# 5. 给某条 prompt 手动打标签
curl -X POST http://localhost:4165/api/prompts/1/tags \
     -H "Content-Type: application/json" \
     -d '{"tag_ids":[3,5]}'
```

## 失败兜底

- **DeepSeek 不可达**：`/api/generate` 返回 502；`/api/prompts/save` 仍然入库，但 `text_zh` 为 NULL 且提示词无标签，响应中 `failed_translations` / `tag_failures` 大于 0。
- **数据库不可达**：写接口返回 503，读接口返回 500；前端用 `ElMessage.error` 弹窗提示。
- **重复保存**：相同片段（不区分大小写）`usage_count` 自增 1，`last_used_at` 刷新。
- **AI 打标 JSON 解析失败**：单条坏数据被丢弃，其他有效标签仍写入；解析层容错，不会让整批 save 失败。
- **层级越界**：`POST /api/tags` 时若 `parent_id` 是叶子标签，返回 400。

## 数据模型

```
prompts
  id, text_en, text_zh, usage_count, source
  created_at, updated_at, last_used_at

tags
  id, name, parent_id (FK tags.id, ON DELETE CASCADE)
  UNIQUE (parent_id, name)

prompt_tags
  prompt_id (FK prompts.id, ON DELETE CASCADE)
  tag_id    (FK tags.id,    ON DELETE CASCADE)
  PRIMARY KEY (prompt_id, tag_id)
```

层级最多 2 层（顶级分类 → 叶子标签），由应用层在 `routers/tags.py::_check_two_level_parent` 强制。