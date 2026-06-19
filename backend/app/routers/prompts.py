import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import GenerationRecord, Prompt, PromptTag, Tag
from ..schemas import (
    ImportRequest,
    ImportResponse,
    LibraryItem,
    ParseItem,
    ParseRequest,
    ParseResponse,
    SaveRequest,
    SaveResponse,
)
from ..services import deepseek, tagger

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


async def _upsert_tag(
    db: AsyncSession, name: str, parent_id: int | None
) -> Tag:
    existing = (
        await db.execute(
            select(Tag).where(
                Tag.parent_id.is_(parent_id) if parent_id is None else Tag.parent_id == parent_id,
                func.lower(Tag.name) == name.lower(),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    row = Tag(name=name, parent_id=parent_id)
    db.add(row)
    await db.flush()
    return row


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
            {"keys": [r.text_en.lower() for r in existing_rows]},
        )
        incremented = len(existing_rows)
    else:
        incremented = 0

    saved = 0
    failed = 0
    tag_failures = 0
    inserted_by_text: dict[str, int] = {}

    if new_inserts:
        stmt = (
            pg_insert(Prompt)
            .values(new_inserts)
            .on_conflict_do_nothing(index_elements=[func.lower(Prompt.text_en)])
            .returning(Prompt.id, Prompt.text_en)
        )
        result = await db.execute(stmt)
        inserted_rows = result.all()
        inserted_by_text = {row.text_en: row.id for row in inserted_rows}
        saved = len(inserted_rows)

        categories_rows = (
            await db.execute(select(Tag.name).where(Tag.parent_id.is_(None)))
        ).all()
        existing_categories = [r[0] for r in categories_rows]

        translations, tagging = await asyncio.gather(
            deepseek.translate_batch(new_texts),
            tagger.auto_tag_batch(new_texts, existing_categories),
            return_exceptions=False,
        )

        for text_en, zh in zip(new_texts, translations):
            pid = inserted_by_text.get(text_en)
            if pid is None or zh is None:
                if zh is None:
                    failed += 1
                continue
            await db.execute(
                text("UPDATE prompts SET text_zh = :zh WHERE id = :id"),
                {"zh": zh, "id": pid},
            )

        for text_en, tag_list in zip(new_texts, tagging):
            pid = inserted_by_text.get(text_en)
            if pid is None or not tag_list:
                if not tag_list:
                    tag_failures += 1
                continue
            for tag_info in tag_list:
                try:
                    cat = await _upsert_tag(db, tag_info["category"], None)
                    leaf = await _upsert_tag(db, tag_info["name"], cat.id)
                    db.add(PromptTag(prompt_id=pid, tag_id=leaf.id))
                except Exception as e:
                    logger.warning("Tag upsert failed for prompt %d: %s", pid, e)
                    tag_failures += 1

    await db.commit()

    saved_items = (
        await db.execute(
            select(Prompt).where(func.lower(Prompt.text_en).in_(lowered))
        )
    ).scalars().all()

    record_id_out: int | None = None
    if req.text_zh and req.text_zh.strip() and saved_items:
        zh = req.text_zh.strip()
        default_name = (zh[:30] + ("…" if len(zh) > 30 else "")).strip()
        record = GenerationRecord(
            name=default_name or None,
            text_zh=zh,
            text_en=", ".join([p.text_en for p in saved_items]),
            rating=0,
            is_favorite=False,
        )
        record.prompts = list(saved_items)
        db.add(record)
        await db.commit()
        await db.refresh(record)
        record_id_out = record.id

    return SaveResponse(
        saved=saved,
        incremented=incremented,
        failed_translations=failed,
        tag_failures=tag_failures,
        items=[LibraryItem.model_validate(p) for p in saved_items],
        record_id=record_id_out,
    )


@router.post("/parse", response_model=ParseResponse)
async def parse_prompts(req: ParseRequest) -> ParseResponse:
    items = _split_text(req.raw_text)
    if not items:
        raise HTTPException(status_code=400, detail="No valid prompts after splitting")

    translations = await deepseek.translate_batch(items)
    failures = sum(1 for zh in translations if zh is None)

    parsed = [
        ParseItem(text_en=en, text_zh=zh)
        for en, zh in zip(items, translations)
    ]
    return ParseResponse(
        items=parsed,
        split_count=len(items),
        translation_failures=failures,
    )


@router.post("/import", response_model=ImportResponse)
async def import_prompts(
    req: ImportRequest, db: AsyncSession = Depends(get_db)
) -> ImportResponse:
    seen: set[str] = set()
    deduped: list[ParseItem] = []
    for it in req.items:
        key = it.text_en.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(
            ParseItem(text_en=it.text_en.strip(), text_zh=(it.text_zh or None))
        )

    if not deduped:
        raise HTTPException(status_code=400, detail="No valid prompts to import")

    lowered = [d.text_en.lower() for d in deduped]

    existing_rows = (
        await db.execute(
            select(Prompt).where(func.lower(Prompt.text_en).in_(lowered))
        )
    ).scalars().all()
    existing_keys = {r.text_en.lower() for r in existing_rows}

    new_inserts: list[dict] = []
    new_texts: list[str] = []
    for d in deduped:
        if d.text_en.lower() in existing_keys:
            continue
        new_inserts.append(
            {
                "text_en": d.text_en,
                "text_zh": d.text_zh,
                "usage_count": 1,
                "source": req.source,
            }
        )
        new_texts.append(d.text_en)
        existing_keys.add(d.text_en.lower())

    tag_failures = 0

    if existing_rows:
        await db.execute(
            text(
                "UPDATE prompts SET usage_count = usage_count + 1, "
                "last_used_at = now() WHERE lower(text_en) = ANY(:keys)"
            ),
            {"keys": [r.text_en.lower() for r in existing_rows]},
        )
    incremented = len(existing_rows)

    inserted_by_text: dict[str, int] = {}
    if new_inserts:
        stmt = (
            pg_insert(Prompt)
            .values(new_inserts)
            .on_conflict_do_nothing(index_elements=[func.lower(Prompt.text_en)])
            .returning(Prompt.id, Prompt.text_en)
        )
        result = await db.execute(stmt)
        inserted_rows = result.all()
        inserted_by_text = {row.text_en: row.id for row in inserted_rows}
        saved = len(inserted_rows)

        if new_texts:
            categories_rows = (
                await db.execute(select(Tag.name).where(Tag.parent_id.is_(None)))
            ).all()
            existing_categories = [r[0] for r in categories_rows]

            tagging = await tagger.auto_tag_batch(new_texts, existing_categories)

            for text_en, tag_list in zip(new_texts, tagging):
                pid = inserted_by_text.get(text_en)
                if pid is None or not tag_list:
                    if not tag_list:
                        tag_failures += 1
                    continue
                for tag_info in tag_list:
                    try:
                        cat = await _upsert_tag(db, tag_info["category"], None)
                        leaf = await _upsert_tag(db, tag_info["name"], cat.id)
                        db.add(PromptTag(prompt_id=pid, tag_id=leaf.id))
                    except Exception as e:
                        logger.warning("Tag upsert failed for prompt %d: %s", pid, e)
                        tag_failures += 1
    else:
        saved = 0

    await db.commit()

    saved_items = (
        await db.execute(
            select(Prompt).where(func.lower(Prompt.text_en).in_(lowered))
        )
    ).scalars().all()

    return ImportResponse(
        saved=saved,
        incremented=incremented,
        tag_failures=tag_failures,
        items=[LibraryItem.model_validate(p) for p in saved_items],
    )