import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Prompt
from ..schemas import LibraryItem, LibraryResponse

router = APIRouter(prefix="/api/library", tags=["library"])
logger = logging.getLogger(__name__)


@router.get("", response_model=LibraryResponse)
async def list_library(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=200),
    db: AsyncSession = Depends(get_db),
) -> LibraryResponse:
    base = select(Prompt)
    count_base = select(func.count()).select_from(Prompt)
    if search:
        like = f"%{search}%"
        base = base.where(Prompt.text_en.ilike(like))
        count_base = count_base.where(Prompt.text_en.ilike(like))

    total = (await db.execute(count_base)).scalar_one()

    base = base.order_by(text("usage_count DESC"), Prompt.id.desc())
    base = base.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(base)).scalars().all()

    return LibraryResponse(
        items=[LibraryItem.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete("/{prompt_id}", status_code=204)
async def delete_prompt(prompt_id: int, db: AsyncSession = Depends(get_db)) -> None:
    row = await db.get(Prompt, prompt_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    await db.delete(row)
    await db.commit()