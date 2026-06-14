import asyncio
import logging

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=settings.deepseek_base_url,
            timeout=settings.request_timeout,
            headers={
                "Authorization": f"Bearer {settings.deepseek_api_key}",
                "Content-Type": "application/json",
            },
        )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def _chat(messages: list[dict], retries: int = 1) -> str:
    if not settings.deepseek_api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")

    payload = {"model": settings.deepseek_model, "messages": messages, "temperature": 0.7}
    last_err: Exception | None = None

    for attempt in range(retries + 1):
        try:
            client = _get_client()
            resp = await client.post("/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.RequestError) as e:
            last_err = e
            logger.warning("DeepSeek call failed (attempt %d): %s", attempt + 1, e)
            if attempt < retries:
                await asyncio.sleep(0.5 * (attempt + 1))

    raise RuntimeError(f"DeepSeek call failed after retries: {last_err}")


async def generate(system_prompt: str, user_input: str) -> str:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]
    return await _chat(messages)


async def _translate_one(text: str) -> str | None:
    if not text.strip():
        return None
    messages = [
        {
            "role": "system",
            "content": (
                "你是一个翻译助手。把用户提供的英文 AI 绘图提示词片段翻译为简洁准确的中文，"
                "只输出译文，不要任何解释、标点修饰或换行。"
            ),
        },
        {"role": "user", "content": text},
    ]
    try:
        result = await _chat(messages)
        return result.strip() or None
    except Exception as e:
        logger.warning("Translation failed for '%s': %s", text[:40], e)
        return None


async def translate_batch(texts: list[str]) -> list[str | None]:
    if not texts:
        return []
    sem = asyncio.Semaphore(settings.translate_concurrency)

    async def bounded(t: str) -> str | None:
        async with sem:
            return await _translate_one(t)

    return await asyncio.gather(*(bounded(t) for t in texts))