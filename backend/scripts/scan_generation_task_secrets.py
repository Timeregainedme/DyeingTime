"""只读扫描 GenerationTask.payload 中可能的历史供应商机密。

用途：P8 安全检查。只输出任务 ID、命中路径和键名，不打印任何值。
不修改数据库，不自动清理历史任务。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from sqlalchemy import select

from app.core.db import async_session_maker
from app.models.task import GenerationTask

SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "access_token",
    "refresh_token",
    "secret",
    "client_secret",
    "bearer",
}


def _hits(value: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if str(key).lower() in SENSITIVE_KEYS and child not in (None, ""):
                found.append(child_path)
            found.extend(_hits(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_hits(child, f"{path}[{index}]"))
    return found


async def main() -> None:
    hits: list[dict[str, Any]] = []
    async with async_session_maker() as db:
        tasks = (await db.execute(select(GenerationTask))).scalars().all()
        for task in tasks:
            paths = _hits(task.payload or {})
            if paths:
                hits.append({"task_id": task.id, "paths": paths})
    print(json.dumps({"scanned_tasks": len(tasks), "hits": hits}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
