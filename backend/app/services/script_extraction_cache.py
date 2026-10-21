"""脚本提取缓存：基于请求签名的进程内缓存。"""

from __future__ import annotations

import hashlib
import json
from threading import Lock
from typing import Any

from app.schemas.skills.script_processing import StudioScriptExtractionDraft

_CACHE_LOCK = Lock()
_SCRIPT_EXTRACT_CACHE: dict[str, StudioScriptExtractionDraft] = {}


def build_script_extract_cache_key(
    *,
    project_id: str,
    chapter_id: str,
    script_division: dict[str, Any],
    consistency: dict[str, Any] | None,
) -> str:
    payload = {
        "project_id": project_id,
        "chapter_id": chapter_id,
        "script_division": script_division,
        "consistency": consistency or {},
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_cached_script_extract(cache_key: str) -> StudioScriptExtractionDraft | None:
    with _CACHE_LOCK:
        cached = _SCRIPT_EXTRACT_CACHE.get(cache_key)
        if cached is None:
            return None
        return cached.model_copy(deep=True)


def set_cached_script_extract(cache_key: str, result: StudioScriptExtractionDraft) -> None:
    with _CACHE_LOCK:
        _SCRIPT_EXTRACT_CACHE[cache_key] = result.model_copy(deep=True)


def clear_script_extract_cache() -> None:
    with _CACHE_LOCK:
        _SCRIPT_EXTRACT_CACHE.clear()
