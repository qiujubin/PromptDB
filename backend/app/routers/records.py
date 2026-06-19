import logging
import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import and_, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import (
    GenerationRecord,
    GenerationRecordImage,
    PromptTag,
    generation_record_prompts,
)
from ..schemas import (
    GenerationRecordImageOut,
    GenerationRecordListResponse,
    GenerationRecordOut,
    GenerationRecordUpdate,
    ImageOrderUpdate,
    LibraryItem,
)

router = APIRouter(prefix="/api/records", tags=["records"])
logger = logging.getLogger(__name__)

STATIC_ROOT = Path("static")
UPLOAD_ROOT = STATIC_ROOT / "uploads"

ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024


def _to_image_out(img: GenerationRecordImage) -> GenerationRecordImageOut:
    out = GenerationRecordImageOut.model_validate(img)
    out.url = f"/static/uploads/{img.record_id}/{Path(img.file_path).name}"
    return out


def _to_record_out(rec: GenerationRecord) -> GenerationRecordOut:
    out = GenerationRecordOut.model_validate(rec)
    out.images = [_to_image_out(i) for i in rec.images]
    out.prompts = [LibraryItem.model_validate(p) for p in rec.prompts]
    return out


@router.get("", response_model=GenerationRecordListResponse)
async def list_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=200),
    search: str | None = Query(None, max_length=200),
    min_rating: int | None = Query(None, ge=0, le=5),
    favorites_only: bool = Query(False),
    tag_id: int | None = Query(None, ge=1),
    sort: str = Query("favorites_first"),
    db: AsyncSession = Depends(get_db),
) -> GenerationRecordListResponse:
    base = select(GenerationRecord)
    count_base = select(func.count()).select_from(GenerationRecord)

    if search:
        like = f"%{search}%"
        cond = GenerationRecord.text_zh.ilike(like) | GenerationRecord.text_en.ilike(like)
        base = base.where(cond)
        count_base = count_base.where(cond)

    if min_rating is not None:
        base = base.where(GenerationRecord.rating >= min_rating)
        count_base = count_base.where(GenerationRecord.rating >= min_rating)

    if favorites_only:
        base = base.where(GenerationRecord.is_favorite.is_(True))
        count_base = count_base.where(GenerationRecord.is_favorite.is_(True))

    if tag_id is not None:
        has_prompt_with_tag = exists().where(
            and_(
                generation_record_prompts.c.record_id == GenerationRecord.id,
                generation_record_prompts.c.prompt_id == PromptTag.prompt_id,
                PromptTag.tag_id == tag_id,
            )
        )
        base = base.where(has_prompt_with_tag)
        count_base = count_base.where(has_prompt_with_tag)

    total = (await db.execute(count_base)).scalar_one()

    if sort == "created_desc":
        base = base.order_by(GenerationRecord.created_at.desc())
    else:
        base = base.order_by(
            GenerationRecord.is_favorite.desc(),
            GenerationRecord.created_at.desc(),
        )

    base = base.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(base)).scalars().unique().all()
    for r in rows:
        _ = r.images
        _ = r.prompts

    return GenerationRecordListResponse(
        items=[_to_record_out(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{record_id}", response_model=GenerationRecordOut)
async def get_record(record_id: int, db: AsyncSession = Depends(get_db)) -> GenerationRecordOut:
    rec = await db.get(GenerationRecord, record_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return _to_record_out(rec)


@router.patch("/{record_id}", response_model=GenerationRecordOut)
async def update_record(
    record_id: int,
    req: GenerationRecordUpdate,
    db: AsyncSession = Depends(get_db),
) -> GenerationRecordOut:
    rec = await db.get(GenerationRecord, record_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Record not found")

    data = req.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(rec, k, v)
    await db.commit()
    await db.refresh(rec)
    return _to_record_out(rec)


@router.delete("/{record_id}", status_code=204)
async def delete_record(record_id: int, db: AsyncSession = Depends(get_db)) -> None:
    rec = await db.get(GenerationRecord, record_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Record not found")
    rec_dir = UPLOAD_ROOT / str(record_id)
    await db.delete(rec)
    await db.commit()
    if rec_dir.exists():
        try:
            shutil.rmtree(rec_dir)
        except OSError as e:
            logger.warning("Failed to remove dir %s: %s", rec_dir, e)


@router.post("/{record_id}/images", response_model=GenerationRecordOut)
async def upload_record_images(
    record_id: int,
    files: list[UploadFile] = File(..., description="一个或多个图片文件"),
    db: AsyncSession = Depends(get_db),
) -> GenerationRecordOut:
    rec = await db.get(GenerationRecord, record_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Record not found")

    rec_dir = UPLOAD_ROOT / str(record_id)
    rec_dir.mkdir(parents=True, exist_ok=True)

    next_pos = max([i.position for i in rec.images], default=-1) + 1
    for f in files:
        if not f.filename:
            continue
        ext = Path(f.filename).suffix.lower()
        if ext not in ALLOWED_IMAGE_EXTS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {ext}. Allowed: {sorted(ALLOWED_IMAGE_EXTS)}",
            )
        data = await f.read()
        if len(data) > MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"File '{f.filename}' exceeds 10MB limit",
            )
        new_name = f"{uuid.uuid4().hex}{ext}"
        target = rec_dir / new_name
        with open(target, "wb") as out:
            out.write(data)
        rel_path = f"uploads/{record_id}/{new_name}"
        db.add(
            GenerationRecordImage(
                record_id=record_id, file_path=rel_path, position=next_pos
            )
        )
        next_pos += 1

    await db.commit()
    await db.refresh(rec)
    return _to_record_out(rec)


@router.delete("/{record_id}/images/{image_id}", status_code=204)
async def delete_record_image(
    record_id: int, image_id: int, db: AsyncSession = Depends(get_db)
) -> None:
    img = await db.get(GenerationRecordImage, image_id)
    if img is None or img.record_id != record_id:
        raise HTTPException(status_code=404, detail="Image not found")

    abs_path = STATIC_ROOT / img.file_path
    await db.delete(img)
    await db.commit()

    if abs_path.exists():
        try:
            os.remove(abs_path)
        except OSError as e:
            logger.warning("Failed to remove file %s: %s", abs_path, e)


@router.patch("/{record_id}/images/order", response_model=GenerationRecordOut)
async def reorder_record_images(
    record_id: int,
    req: ImageOrderUpdate,
    db: AsyncSession = Depends(get_db),
) -> GenerationRecordOut:
    rec = await db.get(GenerationRecord, record_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Record not found")

    images = {img.id: img for img in rec.images}
    if set(req.image_ids) != set(images.keys()):
        raise HTTPException(
            status_code=400,
            detail="image_ids must include every image exactly once",
        )

    for pos, iid in enumerate(req.image_ids):
        images[iid].position = pos
    await db.commit()
    await db.refresh(rec)
    return _to_record_out(rec)
