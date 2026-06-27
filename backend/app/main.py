import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from .config import settings
from .db import Base, engine
from .routers import generate as generate_router
from .routers import library as library_router
from .routers import loras as loras_router
from .routers import prompts as prompts_router
from .routers import records as records_router
from .routers import tags as tags_router
from .services import deepseek
from .services.text_utils import strip_prompt_weight

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATIC_DIR = Path("static")
STATIC_DIR.mkdir(exist_ok=True)


async def _migrate_records(conn) -> None:
    await conn.execute(
        text(
            "ALTER TABLE generation_records "
            "ADD COLUMN IF NOT EXISTS name VARCHAR(255)"
        )
    )
    await conn.execute(
        text(
            "UPDATE generation_records SET text_en = REPLACE(text_en, chr(10), ', ')"
        )
    )
    await conn.execute(
        text(
            "UPDATE generation_records SET name = COALESCE("
            "  CASE WHEN text_zh IS NOT NULL AND length(text_zh) > 0 "
            "       THEN CASE WHEN length(text_zh) > 30 "
            "                 THEN substr(text_zh, 1, 30) || '…' "
            "                 ELSE text_zh END "
            "       ELSE NULL END,"
            "  CASE WHEN text_en IS NOT NULL AND length(text_en) > 0 "
            "       THEN CASE WHEN length(text_en) > 30 "
            "                 THEN substr(text_en, 1, 30) || '…' "
            "                 ELSE text_en END "
            "       ELSE NULL END,"
            "  '记录'"
            ") WHERE name IS NULL"
        )
    )


async def _migrate_lora_entries(conn) -> None:
    await conn.execute(
        text(
            "ALTER TABLE lora_entries "
            "ADD COLUMN IF NOT EXISTS trigger_words_user TEXT"
        )
    )
    await conn.execute(
        text(
            "ALTER TABLE lora_entries "
            "ADD COLUMN IF NOT EXISTS trigger_groups JSONB"
        )
    )


async def _migrate_strip_weights(conn) -> None:
    rows = (
        await conn.execute(text("SELECT id, text_en, usage_count FROM prompts"))
    ).fetchall()
    if not rows:
        return

    proposed: dict[int, str] = {}
    group: dict[str, list[tuple[int, int]]] = {}
    for r in rows:
        new = strip_prompt_weight(r.text_en)
        if not new or new == r.text_en:
            continue
        proposed[r.id] = new
        group.setdefault(new.lower(), []).append((r.id, r.usage_count))

    losers: set[int] = set()
    for items in group.values():
        if len(items) <= 1:
            continue
        items.sort(key=lambda x: (-x[1], x[0]))
        winner_id = items[0][0]
        for loser_id, loser_uc in items[1:]:
            losers.add(loser_id)
            await conn.execute(
                text(
                    "INSERT INTO prompt_tags (prompt_id, tag_id, created_at) "
                    "SELECT :w, tag_id, now() FROM prompt_tags "
                    "WHERE prompt_id = :l ON CONFLICT DO NOTHING"
                ),
                {"w": winner_id, "l": loser_id},
            )
            await conn.execute(
                text(
                    "INSERT INTO generation_record_prompts "
                    "(record_id, prompt_id, created_at) "
                    "SELECT record_id, :w, now() "
                    "FROM generation_record_prompts "
                    "WHERE prompt_id = :l ON CONFLICT DO NOTHING"
                ),
                {"w": winner_id, "l": loser_id},
            )
            await conn.execute(
                text(
                    "UPDATE prompts SET usage_count = usage_count + :uc "
                    "WHERE id = :w"
                ),
                {"uc": loser_uc, "w": winner_id},
            )
            await conn.execute(
                text("DELETE FROM prompts WHERE id = :l"), {"l": loser_id}
            )

    updated = 0
    for pid, new in proposed.items():
        if pid in losers:
            continue
        await conn.execute(
            text("UPDATE prompts SET text_en = :n WHERE id = :id"),
            {"n": new, "id": pid},
        )
        updated += 1
    if updated or losers:
        logger.info(
            "strip-weights migration: updated=%d merged_losers=%d",
            updated,
            len(losers),
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    (STATIC_DIR / "uploads").mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        try:
            await _migrate_records(conn)
            await _migrate_lora_entries(conn)
            await _migrate_strip_weights(conn)
        except Exception as e:
            logger.warning("Migration skipped: %s", e)
    yield
    await deepseek.close_client()
    await engine.dispose()


app = FastAPI(title="AI 绘图提示词助手", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.allowed_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(generate_router.router)
app.include_router(prompts_router.router)
app.include_router(library_router.router)
app.include_router(tags_router.router)
app.include_router(records_router.router)
app.include_router(loras_router.router)

app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.app_port, reload=True)