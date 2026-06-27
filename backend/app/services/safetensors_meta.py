"""Safetensors header parser.

Reads only the JSON header at the start of a .safetensors file without loading
any tensor data, so we can extract LoRA metadata (base model, trigger words,
training module, description, author) quickly.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_HEADER_BYTES = 8 * 1024 * 1024


@dataclass(slots=True)
class SafetensorsMeta:
    base_model: str | None = None
    trigger_words: str | None = None
    network_module: str | None = None
    description: str | None = None
    author: str | None = None


def _coerce_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return str(value).strip() or None


def _extract_from_metadata(meta: dict) -> SafetensorsMeta:
    """Pull LoRA-relevant fields out of a safetensors ``__metadata__`` dict.

    Covers:
      - kohya_ss / a1111 style keys (``ss_base_model_version``, ``ss_tag_frequency``,
        ``ss_network_module``, ``ss_network_dim``)
      - the newer ``modelspec.*`` block defined by the SAIModelSpec
      - civitai-style ``modelspec.title`` / ``modelspec.trigger_phrase``
    """
    lower_map = {k.lower(): k for k in meta.keys()}

    def get(*names: str) -> str | None:
        for n in names:
            real = lower_map.get(n.lower())
            if real is not None:
                v = _coerce_str(meta.get(real))
                if v:
                    return v
        return None

    base_model = get(
        "ss_base_model_version",
        "modelspec.ss_base_model_version",
        "modelspec.base_model",
        "base_model",
    )

    network_module = get(
        "ss_network_module",
        "modelspec.network_module",
    )

    description = get(
        "modelspec.description",
        "ss_training_description",
        "description",
    )

    author = get(
        "modelspec.author",
        "ss_artist",
        "trained_by",
        "author",
    )

    trigger = get(
        "modelspec.trigger_phrase",
        "ss_trigger_words",
    )
    if not trigger:
        tag_freq_raw = meta.get(lower_map.get("ss_tag_frequency", "ss_tag_frequency"))
        if isinstance(tag_freq_raw, str) and tag_freq_raw.strip():
            try:
                parsed = json.loads(tag_freq_raw)
                if isinstance(parsed, dict):
                    keys = [k for k in parsed.keys() if k]
                    trigger = ", ".join(keys) if keys else None
            except json.JSONDecodeError:
                trigger = tag_freq_raw.strip() or None

    return SafetensorsMeta(
        base_model=base_model,
        trigger_words=trigger,
        network_module=network_module,
        description=description,
        author=author,
    )


def read_safetensors_meta(path: Path) -> SafetensorsMeta:
    """Read the safetensors header and extract LoRA metadata.

    Returns an empty :class:`SafetensorsMeta` if the file is unreadable, the
    header is malformed, or the file simply has no ``__metadata__`` block.
    Never raises.
    """
    try:
        with open(path, "rb") as f:
            header_size_bytes = f.read(8)
            if len(header_size_bytes) < 8:
                return SafetensorsMeta()
            header_size = int.from_bytes(header_size_bytes, "little")
            if header_size <= 0 or header_size > MAX_HEADER_BYTES:
                logger.debug(
                    "Skip %s: header size %s out of range", path, header_size
                )
                return SafetensorsMeta()
            header_bytes = f.read(header_size)
            if len(header_bytes) < header_size:
                return SafetensorsMeta()
            header = json.loads(header_bytes.decode("utf-8", errors="replace"))
    except (OSError, ValueError, json.JSONDecodeError) as e:
        logger.debug("Safetensors header read failed for %s: %s", path, e)
        return SafetensorsMeta()

    meta = header.get("__metadata__") if isinstance(header, dict) else None
    if not isinstance(meta, dict):
        return SafetensorsMeta()
    return _extract_from_metadata(meta)
