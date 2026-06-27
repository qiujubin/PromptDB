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


@asynccontextmanager
async def lifespan(_: FastAPI):
    (STATIC_DIR / "uploads").mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        try:
            await _migrate_records(conn)
            await _migrate_lora_entries(conn)
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