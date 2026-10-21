"""视频 integrations：httpx MockTransport 单测。"""

from __future__ import annotations

import json

import httpx
import pytest
from pydantic import ValidationError

from app.core.integrations.openai.video import OpenAIVideoApiAdapter
from app.core.integrations.volcengine.video import VolcengineVideoApiAdapter
from app.core.contracts.provider import ProviderConfig
from app.core.contracts.video_generation import VideoGenerationInput


def _patch_httpx_client(monkeypatch: pytest.MonkeyPatch, transport: httpx.MockTransport) -> None:
    real_client = httpx.AsyncClient

    def factory(**kwargs: object) -> httpx.AsyncClient:
        timeout = kwargs.get("timeout", 60.0)
        return real_client(transport=transport, timeout=timeout)  # type: ignore[arg-type]

    monkeypatch.setattr(httpx, "AsyncClient", factory)


@pytest.mark.asyncio
async def test_openai_video_create_returns_id(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url).rstrip("/").endswith("/videos")
        payload = json.loads(request.content.decode())
        assert payload["ratio"] == "16:9"
        assert payload["seed"] == 42
        assert payload["watermark"] is False
        assert payload["seconds"] == "6"
        return httpx.Response(200, json={"id": "video-1"})

    _patch_httpx_client(monkeypatch, httpx.MockTransport(handler))
    cfg = ProviderConfig(provider="openai", api_key="sk-test")
    inp = VideoGenerationInput.model_validate(
        {"prompt": "a cat", "ratio": "16:9", "seed": 42, "watermark": False, "seconds": 6}
    )
    vid = await OpenAIVideoApiAdapter().create_video(cfg=cfg, input_=inp, timeout_s=30.0)
    assert vid == "video-1"


@pytest.mark.asyncio
async def test_openai_video_get_returns_meta(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert "/videos/v-99" in str(request.url)
        return httpx.Response(200, json={"status": "completed", "id": "v-99"})

    _patch_httpx_client(monkeypatch, httpx.MockTransport(handler))
    cfg = ProviderConfig(provider="openai", api_key="sk-test")
    meta = await OpenAIVideoApiAdapter().get_video(cfg=cfg, video_id="v-99", timeout_s=30.0)
    assert meta["status"] == "completed"


@pytest.mark.asyncio
async def test_volcengine_video_create_and_get(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            body = json.loads(request.content.decode())
            assert "content" in body
            assert body["ratio"] == "9:16"
            assert body["duration"] == 8
            assert body["seed"] == 7
            assert body["watermark"] is True
            return httpx.Response(200, json={"id": "t-1"})
        if request.method == "GET":
            assert "/contents/generations/tasks/t-1" in str(request.url)
            return httpx.Response(
                200,
                json={"status": "succeeded", "content": {"video_url": "https://v.example/out.mp4"}},
            )
        return httpx.Response(500)

    _patch_httpx_client(monkeypatch, httpx.MockTransport(handler))
    cfg = ProviderConfig(provider="volcengine", api_key="ak-test")
    inp = VideoGenerationInput.model_validate(
        {"prompt": "舞", "ratio": "9:16", "seconds": 8, "seed": 7, "watermark": True}
    )
    tid = await VolcengineVideoApiAdapter().create_contents_task(cfg=cfg, input_=inp, timeout_s=30.0)
    assert tid == "t-1"
    meta = await VolcengineVideoApiAdapter().get_contents_task(cfg=cfg, task_id=tid, timeout_s=30.0)
    assert meta["status"] == "succeeded"
    assert meta["content"]["video_url"] == "https://v.example/out.mp4"


def test_video_input_seed_bounds_validation() -> None:
    # 边界值应可通过：-1 以及 uint32 最大值
    VideoGenerationInput.model_validate({"prompt": "ok", "ratio": "16:9", "seed": -1})
    VideoGenerationInput.model_validate({"prompt": "ok", "ratio": "16:9", "seed": 4294967295})

    # 越界值应被拒绝：小于 -1 或大于 uint32 最大值
    with pytest.raises(ValidationError):
        VideoGenerationInput.model_validate({"prompt": "bad", "ratio": "16:9", "seed": -2})
    with pytest.raises(ValidationError):
        VideoGenerationInput.model_validate({"prompt": "bad", "ratio": "16:9", "seed": 4294967296})
