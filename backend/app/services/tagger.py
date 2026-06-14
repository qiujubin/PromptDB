import asyncio
import json
import logging
import re

from ..config import settings
from . import deepseek

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _sanitize(name: str) -> str | None:
    s = name.strip()
    if not s or len(s) > 64:
        return None
    if "/" in s or "\n" in s or "\t" in s:
        return None
    return s


def _strip_fence(text: str) -> str:
    return _FENCE_RE.sub("", text).strip()


def _parse_one(text: str) -> list[dict[str, str]]:
    cleaned = _strip_fence(text)
    if not cleaned:
        return []
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            return []
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []
    raw_tags = data.get("tags") if isinstance(data, dict) else None
    if not isinstance(raw_tags, list):
        return []

    out: list[dict[str, str]] = []
    for item in raw_tags[:6]:
        if not isinstance(item, dict):
            continue
        cat = _sanitize(str(item.get("category", "")))
        leaf = _sanitize(str(item.get("name", "")))
        if not cat or not leaf:
            continue
        out.append({"category": cat, "name": leaf})
    return out


def _build_system_prompt(existing_categories: list[str]) -> str:
    if existing_categories:
        cat_list = "、".join(existing_categories)
        cat_rule = (
            f"优先复用以下已有分类：[{cat_list}]。"
            "如果这些分类都不合适，再创建新分类。分类名应简短（1–4 个汉字或单词）。"
        )
    else:
        cat_rule = "自由选择合适的分类名，分类名应简短（1–4 个汉字或单词）。"
    return (
        "你是一个 AI 绘图提示词分类助手。"
        "为每个英文提示词片段打 1–3 个层级标签。\n"
        f"{cat_rule}\n"
        "子标签（name）描述具体细分（如\"手部姿势\"\"夜景\"）。\n"
        "严格按 JSON 输出，格式：\n"
        '{"tags": [{"category": "姿势", "name": "手部姿势"}, ...]}\n'
        "只输出 JSON，不要任何解释。"
    )


async def _tag_one(text: str, existing_categories: list[str]) -> list[dict[str, str]]:
    if not text.strip():
        return []
    messages = [
        {"role": "system", "content": _build_system_prompt(existing_categories)},
        {"role": "user", "content": text},
    ]
    try:
        result = await deepseek._chat(messages)
        return _parse_one(result)
    except Exception as e:
        logger.warning("Auto-tag failed for '%s': %s", text[:40], e)
        return []


async def auto_tag_batch(
    texts: list[str], existing_categories: list[str]
) -> list[list[dict[str, str]]]:
    if not texts:
        return []
    sem = asyncio.Semaphore(settings.translate_concurrency)

    async def bounded(t: str) -> list[dict[str, str]]:
        async with sem:
            return await _tag_one(t, existing_categories)

    try:
        return list(await asyncio.gather(*(bounded(t) for t in texts)))
    except Exception as e:
        logger.error("auto_tag_batch fatal: %s", e)
        return [[] for _ in texts]