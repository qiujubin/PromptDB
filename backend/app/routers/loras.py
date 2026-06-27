import asyncio
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import LoraConfig, LoraEntry
from ..schemas import (
    LoraConfigOut,
    LoraConfigUpdate,
    LoraEntryUpdate,
    LoraItem,
    LoraListResponse,
    LoraMeta,
    TriggerGroup,
)
from ..services.safetensors_meta import read_safetensors_meta

router = APIRouter(prefix="/api/loras", tags=["loras"])
logger = logging.getLogger(__name__)

LORA_EXTS = {".safetensors", ".pt", ".ckpt"}
SCAN_CONCURRENCY = 8


def _norm_path(raw: str | None) -> str | None:
    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None
    return str(Path(s).expanduser())


async def _get_config(db: AsyncSession) -> LoraConfig:
    row = await db.get(LoraConfig, 1)
    if row is None:
        row = LoraConfig(id=1, folder_path=None)
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


@router.get("/config", response_model=LoraConfigOut)
async def get_lora_config(db: AsyncSession = Depends(get_db)) -> LoraConfigOut:
    row = await _get_config(db)
    return LoraConfigOut(folder_path=row.folder_path, updated_at=row.updated_at)


@router.put("/config", response_model=LoraConfigOut)
async def update_lora_config(
    req: LoraConfigUpdate, db: AsyncSession = Depends(get_db)
) -> LoraConfigOut:
    folder = _norm_path(req.folder_path)
    if folder is not None:
        p = Path(folder)
        if not p.exists() or not p.is_dir():
            raise HTTPException(
                status_code=400, detail=f"目录不存在或不可访问: {folder}"
            )

    row = await _get_config(db)
    row.folder_path = folder or None
    await db.commit()
    await db.refresh(row)
    return LoraConfigOut(folder_path=row.folder_path, updated_at=row.updated_at)


async def _scan_one(path: Path) -> LoraItem:
    try:
        stat = path.stat()
        size = stat.st_size
        mtime = datetime.fromtimestamp(stat.st_mtime)
    except OSError:
        size = 0
        mtime = None

    meta = read_safetensors_meta(path)
    has_meta = any(
        [meta.base_model, meta.trigger_words, meta.network_module, meta.description]
    )

    return LoraItem(
        file_path=str(path),
        file_name=path.name,
        file_size=size,
        file_mtime=mtime,
        meta=LoraMeta(
            base_model=meta.base_model,
            trigger_words=meta.trigger_words,
            network_module=meta.network_module,
            description=meta.description,
            author=meta.author,
        ),
        has_meta=has_meta,
    )


async def _scan_folder(folder: Path) -> list[LoraItem]:
    if not folder.exists() or not folder.is_dir():
        return []

    paths: list[Path] = []
    for ext in LORA_EXTS:
        paths.extend(folder.rglob(f"*{ext}"))

    sem = asyncio.Semaphore(SCAN_CONCURRENCY)

    async def bounded(p: Path) -> LoraItem:
        async with sem:
            return await _scan_one(p)

    return await asyncio.gather(*(bounded(p) for p in paths))


def _coerce_groups(raw) -> list[TriggerGroup]:
    if not raw:
        return []
    out: list[TriggerGroup] = []
    for g in raw:
        if isinstance(g, TriggerGroup):
            out.append(g)
        elif isinstance(g, dict):
            out.append(TriggerGroup.model_validate(g))
    return out


def _entry_to_overrides(entry: LoraEntry | None) -> dict:
    if entry is None:
        return {}
    return {
        "nickname": entry.nickname,
        "rating": entry.rating,
        "comment": entry.comment,
        "lora_type": entry.lora_type,
        "trigger_words_user": entry.trigger_words_user,
        "trigger_groups": _coerce_groups(entry.trigger_groups),
        "updated_at": entry.updated_at,
    }


def _apply_overrides(item: LoraItem, overrides: dict) -> LoraItem:
    if not overrides:
        return item
    return item.model_copy(
        update={
            "nickname": overrides.get("nickname"),
            "rating": overrides.get("rating", 0) or 0,
            "comment": overrides.get("comment"),
            "lora_type": overrides.get("lora_type"),
            "trigger_words_user": overrides.get("trigger_words_user"),
            "trigger_groups": overrides.get("trigger_groups") or [],
            "updated_at": overrides.get("updated_at"),
        }
    )


@router.get("", response_model=LoraListResponse)
async def list_loras(db: AsyncSession = Depends(get_db)) -> LoraListResponse:
    cfg = await _get_config(db)
    folder_path = cfg.folder_path
    if not folder_path:
        return LoraListResponse(folder_path=None, items=[], total=0)

    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(
            status_code=400, detail=f"目录不存在或不可访问: {folder_path}"
        )

    items = await _scan_folder(folder)

    file_paths = [it.file_path for it in items]
    overrides_map: dict[str, LoraEntry] = {}
    if file_paths:
        rows = (
            await db.execute(select(LoraEntry).where(LoraEntry.file_path.in_(file_paths)))
        ).scalars().all()
        overrides_map = {r.file_path: r for r in rows}

    enriched: list[LoraItem] = []
    for it in items:
        entry = overrides_map.get(it.file_path)
        merged = _apply_overrides(it, _entry_to_overrides(entry))
        enriched.append(merged)

    enriched.sort(key=lambda x: x.file_name.lower())
    return LoraListResponse(
        folder_path=folder_path,
        items=enriched,
        total=len(enriched),
    )


@router.patch("/entry", response_model=LoraItem)
async def update_lora_entry(
    req: LoraEntryUpdate,
    file_path: str = Query(..., max_length=1024, description="LoRA 文件绝对路径"),
    db: AsyncSession = Depends(get_db),
) -> LoraItem:
    raw = _norm_path(file_path)
    if not raw:
        raise HTTPException(status_code=400, detail="file_path 不能为空")

    p = Path(raw)
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail=f"文件不存在: {raw}")

    data = req.model_dump(exclude_unset=True)
    if "rating" in data and data["rating"] is not None and not 0 <= data["rating"] <= 5:
        raise HTTPException(status_code=400, detail="rating 必须 0-5")

    fields = {
        "file_path": raw,
        "file_name": p.name,
        "file_size": p.stat().st_size if p.exists() else 0,
        "file_mtime": datetime.fromtimestamp(p.stat().st_mtime) if p.exists() else None,
    }
    fields.update(data)

    stmt = (
        pg_insert(LoraEntry)
        .values(**fields)
        .on_conflict_do_update(
            index_elements=[LoraEntry.file_path],
            set_={k: v for k, v in data.items()},
        )
        .returning(LoraEntry)
    )
    row = (await db.execute(stmt)).scalar_one()
    await db.commit()

    meta = read_safetensors_meta(p)
    has_meta = any(
        [meta.base_model, meta.trigger_words, meta.network_module, meta.description]
    )
    return LoraItem(
        file_path=row.file_path,
        file_name=row.file_name,
        file_size=row.file_size,
        file_mtime=row.file_mtime,
        meta=LoraMeta(
            base_model=meta.base_model,
            trigger_words=meta.trigger_words,
            network_module=meta.network_module,
            description=meta.description,
            author=meta.author,
        ),
        nickname=row.nickname,
        rating=row.rating,
        comment=row.comment,
        lora_type=row.lora_type,
        trigger_words_user=row.trigger_words_user,
        trigger_groups=_coerce_groups(row.trigger_groups),
        has_meta=has_meta,
        updated_at=row.updated_at,
    )


@router.delete("/entry", status_code=204)
async def delete_lora_entry(
    file_path: str = Query(..., max_length=1024),
    db: AsyncSession = Depends(get_db),
) -> None:
    raw = _norm_path(file_path)
    if not raw:
        raise HTTPException(status_code=400, detail="file_path 不能为空")
    row = await db.get(LoraEntry, raw)
    if row is None:
        return
    await db.delete(row)
    await db.commit()
