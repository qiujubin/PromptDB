import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Prompt, PromptTag, Tag
from ..schemas import (
    BulkAutoTagResponse,
    PromptTagsUpdate,
    TagCreate,
    TagOut,
    TagTreeNode,
    TagUpdate,
)
from ..services import tagger

router = APIRouter(prefix="/api", tags=["tags"])
logger = logging.getLogger(__name__)


class TagTreeResponse(BaseModel):
    categories: list[TagTreeNode]


async def _load_tree(db: AsyncSession) -> list[TagTreeNode]:
    counts_subq = (
        select(PromptTag.tag_id, func.count(PromptTag.prompt_id).label("cnt"))
        .group_by(PromptTag.tag_id)
        .subquery()
    )
    rows = (
        await db.execute(
            select(
                Tag.id,
                Tag.name,
                Tag.parent_id,
                func.coalesce(counts_subq.c.cnt, 0).label("usage_count"),
            )
            .select_from(Tag)
            .outerjoin(counts_subq, counts_subq.c.tag_id == Tag.id)
            .order_by(Tag.parent_id.is_(None).desc(), Tag.parent_id, Tag.id)
        )
    ).all()

    by_id: dict[int, TagTreeNode] = {
        r.id: TagTreeNode(
            id=r.id, name=r.name, parent_id=r.parent_id, usage_count=r.usage_count, children=[]
        )
        for r in rows
    }
    roots: list[TagTreeNode] = []
    for r in rows:
        node = by_id[r.id]
        if r.parent_id is None:
            roots.append(node)
        else:
            parent = by_id.get(r.parent_id)
            if parent is not None:
                parent.children.append(node)
    return roots


async def _check_two_level_parent(
    db: AsyncSession, parent_id: int | None
) -> None:
    if parent_id is None:
        return
    parent = await db.get(Tag, parent_id)
    if parent is None:
        raise HTTPException(status_code=400, detail="parent_id 不存在")
    if parent.parent_id is not None:
        raise HTTPException(
            status_code=400, detail="标签层级最多 2 层，不能在叶子标签下再创建子标签"
        )


@router.get("/tags", response_model=TagTreeResponse)
async def list_tags(db: AsyncSession = Depends(get_db)) -> TagTreeResponse:
    categories = await _load_tree(db)
    return TagTreeResponse(categories=categories)


@router.post("/tags", response_model=TagOut, status_code=201)
async def create_tag(
    req: TagCreate, db: AsyncSession = Depends(get_db)
) -> TagOut:
    await _check_two_level_parent(db, req.parent_id)
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="名称不能为空")
    existing = (
        await db.execute(
            select(Tag).where(
                Tag.parent_id.is_(req.parent_id) if req.parent_id is None else Tag.parent_id == req.parent_id,
                func.lower(Tag.name) == name.lower(),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="同名标签已存在")
    row = Tag(name=name, parent_id=req.parent_id)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return TagOut.model_validate(row)


@router.patch("/tags/{tag_id}", response_model=TagOut)
async def update_tag(
    tag_id: int, req: TagUpdate, db: AsyncSession = Depends(get_db)
) -> TagOut:
    row = await db.get(Tag, tag_id)
    if row is None:
        raise HTTPException(status_code=404, detail="标签不存在")

    if req.parent_id is not None and req.parent_id != row.parent_id:
        if req.parent_id == tag_id:
            raise HTTPException(status_code=400, detail="不能将标签设为自己的父标签")
        await _check_two_level_parent(db, req.parent_id)

    if req.name is not None:
        name = req.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="名称不能为空")
        existing = (
            await db.execute(
                select(Tag).where(
                    Tag.id != tag_id,
                    Tag.parent_id.is_(row.parent_id) if row.parent_id is None else Tag.parent_id == row.parent_id,
                    func.lower(Tag.name) == name.lower(),
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(status_code=409, detail="同名标签已存在")
        row.name = name

    if req.parent_id is not None:
        row.parent_id = req.parent_id if req.parent_id != 0 else None

    await db.commit()
    await db.refresh(row)
    return TagOut.model_validate(row)


@router.delete("/tags/{tag_id}", status_code=204)
async def delete_tag(tag_id: int, db: AsyncSession = Depends(get_db)) -> None:
    row = await db.get(Tag, tag_id)
    if row is None:
        raise HTTPException(status_code=404, detail="标签不存在")
    children = (
        await db.execute(select(func.count()).select_from(Tag).where(Tag.parent_id == tag_id))
    ).scalar_one()
    if children > 0:
        raise HTTPException(
            status_code=400,
            detail="该标签下还有子标签，请先删除子标签",
        )
    await db.delete(row)
    await db.commit()


@router.post("/prompts/{prompt_id}/tags", response_model=list[TagOut])
async def set_prompt_tags(
    prompt_id: int, req: PromptTagsUpdate, db: AsyncSession = Depends(get_db)
) -> list[TagOut]:
    prompt = await db.get(Prompt, prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="提示词不存在")
    if req.tag_ids:
        valid = (
            await db.execute(select(Tag.id).where(Tag.id.in_(req.tag_ids), Tag.parent_id.is_not(None)))
        ).scalars().all()
        valid_ids = set(valid)
        if len(valid_ids) != len(set(req.tag_ids)):
            raise HTTPException(status_code=400, detail="部分 tag_id 无效或不是叶子标签")

    await db.execute(delete(PromptTag).where(PromptTag.prompt_id == prompt_id))
    for tag_id in set(req.tag_ids):
        db.add(PromptTag(prompt_id=prompt_id, tag_id=tag_id))
    await db.commit()

    rows = (
        await db.execute(
            select(Tag).where(Tag.id.in_(req.tag_ids)) if req.tag_ids else select(Tag).where(Tag.id == -1)
        )
    ).scalars().all()
    return [TagOut.model_validate(r) for r in rows]


async def _bulk_auto_tag_impl(db: AsyncSession) -> BulkAutoTagResponse:
    untagged_ids = (
        await db.execute(
            select(Prompt.id, Prompt.text_en)
            .outerjoin(PromptTag, PromptTag.prompt_id == Prompt.id)
            .where(PromptTag.tag_id.is_(None))
            .order_by(Prompt.id)
        )
    ).all()

    if not untagged_ids:
        return BulkAutoTagResponse(scanned=0, tagged=0, failed=0)

    categories_rows = (
        await db.execute(select(Tag.name).where(Tag.parent_id.is_(None)))
    ).all()
    existing_categories = [r[0] for r in categories_rows]

    batch_size = 8
    tagged = 0
    failed = 0

    for i in range(0, len(untagged_ids), batch_size):
        batch = untagged_ids[i : i + batch_size]
        texts = [r.text_en for r in batch]
        results = await tagger.auto_tag_batch(texts, existing_categories)
        for (pid, text_en), tag_list in zip(batch, results):
            if not tag_list:
                failed += 1
                continue
            try:
                has_any = False
                for tag_info in tag_list:
                    cat = (
                        await db.execute(
                            select(Tag).where(
                                Tag.parent_id.is_(None),
                                func.lower(Tag.name) == tag_info["category"].lower(),
                            )
                        )
                    ).scalar_one_or_none()
                    if cat is None:
                        cat = Tag(name=tag_info["category"], parent_id=None)
                        db.add(cat)
                        await db.flush()
                    leaf = (
                        await db.execute(
                            select(Tag).where(
                                Tag.parent_id == cat.id,
                                func.lower(Tag.name) == tag_info["name"].lower(),
                            )
                        )
                    ).scalar_one_or_none()
                    if leaf is None:
                        leaf = Tag(name=tag_info["name"], parent_id=cat.id)
                        db.add(leaf)
                        await db.flush()
                    db.add(PromptTag(prompt_id=pid, tag_id=leaf.id))
                    has_any = True
                if has_any:
                    tagged += 1
            except Exception as e:
                logger.warning("Bulk auto-tag failed for prompt %d: %s", pid, e)
                failed += 1
        await db.commit()

    return BulkAutoTagResponse(scanned=len(untagged_ids), tagged=tagged, failed=failed)


@router.post("/prompts/bulk-auto-tag", response_model=BulkAutoTagResponse)
async def bulk_auto_tag(db: AsyncSession = Depends(get_db)) -> BulkAutoTagResponse:
    return await _bulk_auto_tag_impl(db)