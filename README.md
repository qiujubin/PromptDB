# AI 绘图提示词助手

一个本地运行的 AI 绘图提示词工具，六个功能模块：

1. **生成提示词** — 输入中文描述，DeepSeek 生成可直接用于 Midjourney / Stable Diffusion 的英文提示词；结果卡片支持「一键保存」直接入库并创建历史记录
2. **解析提示词** — 粘贴英文提示词，按 `,` 切分并并发翻译为中文，以紧凑标签云展示；点击「保存到提示词库」可将这些已翻译的片段直接入库（不再重复翻译，但仍自动打标签）
3. **保存提示词** — 把英文提示词按 `,` 切分后入库，自动调用 DeepSeek 翻译为中文并用 AI 分配层级标签；可选填写中文描述，创建一条带原文的「历史记录」归档
4. **提示词库** — 卡片式浏览，支持搜索、分类 / 子标签双 select 筛选、多选批量删除、抽屉式编辑标签
5. **历史记录** — 瀑布流卡片浏览生成归档：评分、收藏、中英文描述、上传参考图、点击编辑；卡片默认显示标题、hover 展示详情
6. **标签管理** — 树形维护「分类 → 子标签」两级体系；分类引用数为其下子标签累加和；点击标签可直接跳转到提示词库查看；提供「批量补打标签」按钮为旧数据补全 AI 标签

## 技术栈

- **前端**：Vue 3 + Vite + TypeScript + Element Plus（端口 `4163`，keep-alive 路由缓存）
- **后端**：FastAPI + SQLAlchemy 2.0 async + asyncpg（端口 `4165`，静态目录挂载 `/static`）
- **数据库**：PostgreSQL
- **AI**：DeepSeek API（生成 / 翻译 / 打标签复用同一客户端）
- **文件存储**：本地 `backend/static/uploads/{record_id}/`，最大单图 10 MB

## 仓库结构

```
Project_Prompt/
├── backend/
│   ├── app/
│   │   ├── models.py            # Prompt / Tag / PromptTag / GenerationRecord / GenerationRecordImage
│   │   ├── schemas.py
│   │   ├── routers/
│   │   │   ├── generate.py      # /api/generate
│   │   │   ├── prompts.py       # /save /parse /import（并行调用翻译 + 自动打标）
│   │   │   ├── library.py       # /api/library 列表 + 单删 + 批量删除
│   │   │   ├── records.py       # /api/records CRUD + 图片上传/排序
│   │   │   └── tags.py          # /api/tags 标签 CRUD + 批量补打
│   │   └── services/
│   │       ├── deepseek.py      # generate / translate_batch
│   │       └── tagger.py        # auto_tag_batch（复用 translate_concurrency）
│   ├── alembic/                 # 未启用，schema 由 create_all 管理
│   ├── static/uploads/          # 历史记录参考图（gitignore）
│   └── .env
└── frontend/
    └── src/
        ├── api/
        │   ├── client.ts
        │   ├── generate.ts
        │   ├── prompts.ts
        │   ├── library.ts
        │   ├── records.ts
        │   └── tags.ts
        ├── components/
        │   ├── CopyButton.vue
        │   ├── PromptOutputCard.vue
        │   ├── TagChips.vue
        │   ├── RecordCard.vue
        │   ├── RecordEditorDialog.vue
        │   └── RecordImageGallery.vue
        ├── views/
        │   ├── GeneratorView.vue
        │   ├── ParserView.vue      # 标签云 + 直存
        │   ├── SaverView.vue
        │   ├── LibraryView.vue     # 卡片网格 + 多选 + 标签筛选 + 编辑抽屉
        │   ├── RecordsView.vue     # 瀑布流卡片 + 评分/收藏 + 图片上传
        │   └── TagsView.vue        # 分类/子标签管理 + 批量补打
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

第一次启动时 SQLAlchemy 会自动建表（`prompts` / `tags` / `prompt_tags` / `generation_records` / `generation_record_images`），无需手动跑 migration。

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
| `DEEPSEEK_MODEL`        | 使用的模型                | `deepseek-v4-pro`                                                |
| `DATABASE_URL`          | PostgreSQL 异步连接串     | `postgresql+asyncpg://postgres:postgres@localhost:5432/promptdb` |
| `APP_PORT`              | 后端端口                  | `4165`                                                           |
| `ALLOWED_ORIGIN`        | 允许的前端 origin（CORS） | `http://localhost:4163`                                          |
| `TRANSLATE_CONCURRENCY` | 翻译 / 打标签并发上限     | `5`                                                              |
| `REQUEST_TIMEOUT`       | DeepSeek 请求超时（秒）   | `30`                                                             |

> 注：`deepseek-chat` / `deepseek-reasoner` 将于 2026/07/24 弃用，已默认切到 `deepseek-v4-pro`。

## 自定义 AI 提示词

四个调用 DeepSeek 的场景，对应四处提示词：

| 场景                         | 文件                                                       | 说明                                                                 |
| ---------------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------- |
| 生成（中文 → 英文绘图提示词） | `frontend/src/views/GeneratorView.vue` `PRESET_SYSTEM_PROMPT` | 前端常量，作为「生成」页系统提示词输入框默认值，用户可临时改写       |
| 英 → 中翻译                  | `backend/app/services/deepseek.py` `_translate_one`        | 保存 / 解析时用，写死在后端                                          |
| 自动打标签                   | `backend/app/services/tagger.py` `_build_system_prompt`    | 含已有分类复用规则与严格 JSON 输出格式                               |

改后端需重启 `uvicorn`；改前端 vite 会热更。

## API 一览

### 提示词

| 方法     | 路径                                       | 说明                                                                 |
| -------- | ------------------------------------------ | -------------------------------------------------------------------- |
| `POST`   | `/api/generate`                            | 调用 DeepSeek 生成英文提示词                                         |
| `POST`   | `/api/prompts/save`                        | 保存英文提示词（按 `,` 切分 + 翻译 + 自动打标，并行执行）；可附 `text_zh` 创建历史记录 |
| `POST`   | `/api/prompts/parse`                       | 解析英文提示词：按 `,` 切分 + 并发翻译，**不写库**，返回 `{items: [{text_en, text_zh}], split_count, translation_failures}` |
| `POST`   | `/api/prompts/import`                      | 直存已翻译片段：`{items: [{text_en, text_zh}], source?}` 跳过翻译，仅对新行自动打标；命中已存在则 `usage_count + 1` |
| `GET`    | `/api/library`                             | 提示词库列表，按 `usage_count` 降序，可按 `tag_id` / `search` 过滤   |
| `DELETE` | `/api/library/{id}`                        | 删除单条提示词                                                       |
| `POST`   | `/api/library/bulk-delete`                 | 批量删除，body `{ "ids": [1,2,3] }`，返回 `{ "deleted": N }`         |
| `POST`   | `/api/prompts/{id}/tags`                   | 替换某条提示词的标签集合，body `{ "tag_ids": [3,5] }`                |
| `POST`   | `/api/prompts/bulk-auto-tag`               | 对零标签的提示词批量调用 AI 打标，返回 `{ scanned, tagged, failed }`  |

### 历史记录

| 方法     | 路径                                          | 说明                                                                       |
| -------- | --------------------------------------------- | -------------------------------------------------------------------------- |
| `GET`    | `/api/records?page&page_size&is_favorite&search` | 列表（按 `created_at` 倒序），可按收藏 / 搜索过滤                          |
| `GET`    | `/api/records/{id}`                           | 详情（含 images、关联 prompts）                                            |
| `PATCH`  | `/api/records/{id}`                           | 更新 name / text_zh / text_en / rating / comment / is_favorite             |
| `DELETE` | `/api/records/{id}`                           | 删除整条（含图片文件清理）                                                 |
| `POST`   | `/api/records/{id}/images`                    | 上传参考图（multipart），允许多文件，单图 ≤ 10 MB，扩展名 jpg/jpeg/png/webp/gif |
| `DELETE` | `/api/records/{id}/images/{image_id}`         | 删除单张参考图                                                             |
| `PATCH`  | `/api/records/{id}/images/order`              | 重排图片顺序，body `{ "image_ids": [...] }`                                 |

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

# 3. 解析（不写库，返回中英对照）
curl -X POST http://localhost:4165/api/prompts/parse \
     -H "Content-Type: application/json" \
     -d '{"raw_text":"masterpiece, best quality, 1girl"}'

# 4. 直存已解析片段（跳过翻译，仍自动打标）
curl -X POST http://localhost:4165/api/prompts/import \
     -H "Content-Type: application/json" \
     -d '{"items":[{"text_en":"neon_alley_xyz","text_zh":"霓虹小巷"}]}'

# 5. 库（按标签过滤示例：tag_id=2）
curl "http://localhost:4165/api/library?page=1&page_size=20&tag_id=2"

# 6. 历史记录列表
curl "http://localhost:4165/api/records?page=1&page_size=20"

# 7. 标签树
curl http://localhost:4165/api/tags

# 8. 给某条 prompt 手动打标签
curl -X POST http://localhost:4165/api/prompts/1/tags \
     -H "Content-Type: application/json" \
     -d '{"tag_ids":[3,5]}'
```

## 失败兜底

- **DeepSeek 不可达**：`/api/generate` 返回 502；`/api/prompts/save` 仍然入库，但 `text_zh` 为 NULL 且提示词无标签，响应中 `failed_translations` / `tag_failures` 大于 0；`/api/prompts/parse` 在翻译失败时仍返回片段，`text_zh` 为 null（前端以红色"翻译失败"标记）。
- **数据库不可达**：写接口返回 503，读接口返回 500；前端用 `ElMessage.error` 弹窗提示。
- **重复保存**：相同片段（不区分大小写）`usage_count` 自增 1，`last_used_at` 刷新。
- **AI 打标 JSON 解析失败**：单条坏数据被丢弃，其他有效标签仍写入；解析层容错，不会让整批 save 失败。
- **层级越界**：`POST /api/tags` 时若 `parent_id` 是叶子标签，返回 400。
- **图片上传超限**：单文件 > 10 MB 或扩展名不在白名单内，后端返回 400；上传后图片存于 `static/uploads/{record_id}/`，删除记录时同步清理。
- **路由缓存**：前端使用 `<keep-alive>` 缓存视图组件；切换 tab 后返回时通过 `onActivated` 钩子自动重新拉取动态数据，避免展示过期列表。

## 数据模型

```
prompts
  id, text_en, text_zh, usage_count, source
  created_at, updated_at, last_used_at
  UNIQUE INDEX lower(text_en)

tags
  id, name, parent_id (FK tags.id, ON DELETE CASCADE)
  UNIQUE (parent_id, name)

prompt_tags
  prompt_id (FK prompts.id, ON DELETE CASCADE)
  tag_id    (FK tags.id,    ON DELETE CASCADE)
  PRIMARY KEY (prompt_id, tag_id)

generation_records
  id, name, text_zh, text_en
  rating (0-5), comment, is_favorite
  created_at, updated_at

generation_record_images
  id, record_id (FK generation_records.id, ON DELETE CASCADE)
  file_path, position
  created_at
  INDEX (record_id, position)

generation_record_prompts   # 历史记录 ↔ 提示词 多对多关联表
  record_id (FK generation_records.id, ON DELETE CASCADE)
  prompt_id (FK prompts.id,            ON DELETE CASCADE)
  PRIMARY KEY (record_id, prompt_id)
```

层级最多 2 层（顶级分类 → 叶子标签），由应用层在 `routers/tags.py::_check_two_level_parent` 强制。