import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Prompt
from ..schemas import LibraryItem, SaveRequest, SaveResponse
from ..services import deepseek

router = APIRouter(prefix="/api/prompts", tags=["prompts"])
logger = logging.getLogger(__name__)


def _split_text(raw: str) -> list[str]:
    parts = [p.strip() for p in raw.split(",")]
    seen: set[str] = set()
    deduped: list[str] = []
    for p in parts:
        if not p:
            continue
        key = p.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(p)
    return deduped


@router.post("/save", response_model=SaveResponse)
async def save_prompts(req: SaveRequest, db: AsyncSession = Depends(get_db)) -> SaveResponse:
    items = _split_text(req.raw_text)
    if not items:
        raise HTTPException(status_code=400, detail="No valid prompts after splitting")

    lowered = [i.lower() for i in items]

    existing_rows = (
        await db.execute(select(Prompt).where(func.lower(Prompt.text_en).in_(lowered)))
    ).scalars().all()
    existing_keys = {r.text_en.lower() for r in existing_rows}

    saved = 0
    incremented = 0
    new_inserts: list[dict] = []
    new_texts: list[str] = []

    for item in items:
        if item.lower() in existing_keys:
            continue
        new_inserts.append({"text_en": item, "usage_count": 1, "source": req.source})
        new_texts.append(item)
        existing_keys.add(item.lower())

    if existing_rows:
        await db.execute(
            text(
                "UPDATE prompts SET usage_count = usage_count + 1, "
                "last_used_at = now() WHERE lower(text_en) = ANY(:keys)"
            ),
            {"keys": [k for k in existing_keys if k in {r.text_en.lower() for r in existing_rows}]},
        )
        incremented = len(existing_rows)

    if new_inserts:
        stmt = (
            pg_insert(Prompt)
            .values(new_inserts)
            .on_conflict_do_nothing(index_elements=[func.lower(Prompt.text_en)])
            .returning(Prompt.id, Prompt.text_en)
        )
        result = await db.execute(stmt)
        inserted_rows = result.all()
        inserted_by_text: dict[str, int] = {row.text_en: row.id for row in inserted_rows}

        translations = await deepseek.translate_batch(new_texts)
        failed = 0
        for text_en, zh in zip(new_texts, translations):
            pid = inserted_by_text.get(text_en)
            if pid is None:
                continue
            if zh is None:
                failed += 1
                continue
            await db.execute(
                text("UPDATE prompts SET text_zh = :zh WHERE id = :id"),
                {"zh": zh, "id": pid},
            )
        saved = len(inserted_rows)
    else:
        failed = 0

    await db.commit()

    saved_items = (
        await db.execute(select(Prompt).where(func.lower(Prompt.text_en).in_(lowered)))
    ).scalars().all()

    return SaveResponse(
        saved=saved,
        incremented=incremented,
        failed_translations=failed,
        items=[LibraryItem.model_validate(p) for p in saved_items],
    )