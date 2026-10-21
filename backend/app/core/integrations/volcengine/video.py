"""火山方舟：内容生成任务创建与查询。"""

from __future__ import annotations

from typing import Any

from app.core.integrations.volcengine.video_payload import build_create_task_body
from app.core.contracts.provider import ProviderConfig
from app.core.contracts.video_generation import VideoGenerationInput


class VolcengineVideoApiAdapter:
    """火山视频任务 HTTP。"""

    async def create_contents_task(
        self,
        *,
        cfg: ProviderConfig,
        input_: VideoGenerationInput,
        timeout_s: float,
    ) -> str:
        try:
            import httpx
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("httpx is required for video generation tasks") from e

        base_url = (cfg.base_url or "https://ark.cn-beijing.volces.com/api/v3").rstrip("/")
        headers = {
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json",
        }
        body = build_create_task_body(input_)

        async with httpx.AsyncClient(timeout=timeout_s) as client:
            r = await client.post(f"{base_url}/contents/generations/tasks", headers=headers, json=body)
            r.raise_for_status()
            data: dict[str, Any] = r.json()
            task_id = str(data.get("id") or data.get("task_id") or "")
            if not task_id:
                raise RuntimeError(f"Volcengine create missing id: {data!r}")
            return task_id

    async def get_contents_task(
        self,
        *,
        cfg: ProviderConfig,
        task_id: str,
        timeout_s: float,
    ) -> dict[str, Any]:
        try:
            import httpx
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("httpx is required for video generation tasks") from e

        base_url = (cfg.base_url or "https://ark.cn-beijing.volces.com/api/v3").rstrip("/")
        headers = {
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=timeout_s) as client:
            rr = await client.get(f"{base_url}/contents/generations/tasks/{task_id}", headers=headers)
            rr.raise_for_status()
            return rr.json()
