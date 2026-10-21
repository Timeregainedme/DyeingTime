"""OpenAI Videos API：创建与查询。"""

from __future__ import annotations

from typing import Any

from app.core.integrations.openai.video_payload import build_create_video_body
from app.core.contracts.provider import ProviderConfig
from app.core.contracts.video_generation import VideoGenerationInput


class OpenAIVideoApiAdapter:
    """OpenAI 视频：POST /videos 与 GET /videos/{id}。"""

    async def create_video(
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

        base_url = (cfg.base_url or "https://api.openai.com/v1").rstrip("/")
        headers = {
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json",
        }
        body = build_create_video_body(input_)

        async with httpx.AsyncClient(timeout=timeout_s) as client:
            r = await client.post(f"{base_url}/videos", headers=headers, json=body)
            r.raise_for_status()
            data: dict[str, Any] = r.json()
            video_id = str(data.get("id") or "")
            if not video_id:
                raise RuntimeError(f"OpenAI /videos missing id: {data!r}")
            return video_id

    async def get_video(
        self,
        *,
        cfg: ProviderConfig,
        video_id: str,
        timeout_s: float,
    ) -> dict[str, Any]:
        try:
            import httpx
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("httpx is required for video generation tasks") from e

        base_url = (cfg.base_url or "https://api.openai.com/v1").rstrip("/")
        headers = {"Authorization": f"Bearer {cfg.api_key}"}

        async with httpx.AsyncClient(timeout=timeout_s) as client:
            rr = await client.get(f"{base_url}/videos/{video_id}", headers=headers)
            rr.raise_for_status()
            return rr.json()
