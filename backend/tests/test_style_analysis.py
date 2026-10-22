"""P2 / C4：风格参考图分析测试（不调用真实模型）。"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db import Base
from app.schemas.studio.projects import StyleStructuredProfile
from app.services.studio import style_analysis as svc


async def _empty_session() -> tuple[AsyncSession, object]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_local = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return session_local(), engine


def test_parse_analysis_json_tolerates_markdown_fence() -> None:
    raw = """```json
{"medium": "实拍", "texture": "真实皮肤"}
```"""
    payload = svc._parse_analysis_json(raw)
    assert payload["medium"] == "实拍"


def test_parse_analysis_json_rejects_non_json() -> None:
    with pytest.raises(ValueError):
        svc._parse_analysis_json("这不是 JSON")


def test_normalize_profile_only_keeps_known_fields() -> None:
    profile = svc._normalize_profile(
        {
            "medium": "实拍",
            "texture": "真实皮肤",
            "unexpected": "ignored",
            "avoid": "塑料感",
        }
    )
    assert isinstance(profile, StyleStructuredProfile)
    assert profile.medium == "实拍"
    assert profile.avoid == "塑料感"


@pytest.mark.asyncio
async def test_analyze_style_images_returns_editable_profile(monkeypatch) -> None:
    db, engine = await _empty_session()
    async with db:
        async def _fake_load(_db, file_ids):
            assert file_ids == ["f1", "f2"]
            return ["data:image/png;base64,AAA", "data:image/png;base64,BBB"]

        async def _fake_build(_db, *, model_id=None, thinking=False):
            return (
                SimpleNamespace(),
                SimpleNamespace(id="m-text", name="vision-model"),
                SimpleNamespace(name="测试供应商"),
            )

        async def _fake_invoke(_chat, *, messages):
            assert len(messages) == 2
            return """{
              "medium": "电影实拍",
              "texture": "真实皮肤与轻微颗粒",
              "color": "低饱和冷调",
              "lighting": "窗光",
              "material": "棉麻",
              "character_rendering": "真实骨相",
              "scene_rendering": "实景",
              "camera": "35mm",
              "keep": "真实肤色",
              "avoid": "塑料感"
            }"""

        monkeypatch.setattr(svc, "_load_image_data_urls", _fake_load)
        monkeypatch.setattr(svc, "build_text_llm", _fake_build)
        monkeypatch.setattr(svc, "_invoke_style_analysis", _fake_invoke)

        result = await svc.analyze_style_images(db, file_ids=["f1", "f2"])

        assert result.profile.medium == "电影实拍"
        assert result.model_id == "m-text"
        assert result.image_count == 2
        assert "视觉媒介：电影实拍" in result.prompt_pack
        assert "避免：塑料感" in result.prompt_pack
    await engine.dispose()


@pytest.mark.asyncio
async def test_style_analysis_capability_reports_missing_model() -> None:
    db, engine = await _empty_session()
    async with db:
        capability = await svc.get_style_analysis_capability(db)
        assert capability.available is False
        assert capability.reason
    await engine.dispose()
