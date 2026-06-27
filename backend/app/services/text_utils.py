"""Prompt text helpers."""

from __future__ import annotations

import re

_EMPHASIS_RE = re.compile(
    r"[\(\[]([^\(\)\[\]]*?)(?:\s*:\s*\d+(?:\.\d+)?)?[\)\]]"
)
_BARE_WEIGHT_RE = re.compile(r"\s*:\s*\d+(?:\.\d+)?\s*")
_WS_RE = re.compile(r"\s+")
_ANGLE_RE = re.compile(r"<[^>\n]+>")


def strip_prompt_weight(text: str) -> str:
    """Strip SD/A1111 emphasis and numeric weights from a prompt segment.

    - Iteratively unwrap nested ``(...)`` / ``[...]`` blocks, removing any
      ``:1.2`` weight that lives inside the block.
    - After unwrapping, strip any leftover ``:1.2`` weight.
    - Angle-bracket tokens like ``<lora:foo:0.8>`` are preserved verbatim.
    """
    placeholders: list[str] = []
    def _mask(m: re.Match[str]) -> str:
        placeholders.append(m.group(0))
        return f"\x00{len(placeholders) - 1}\x00"

    text = _ANGLE_RE.sub(_mask, text)
    while True:
        prev = text
        text = _EMPHASIS_RE.sub(r"\1", text)
        if text == prev:
            break
    text = _BARE_WEIGHT_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()
    for i, ph in enumerate(placeholders):
        text = text.replace(f"\x00{i}\x00", ph)
    return text