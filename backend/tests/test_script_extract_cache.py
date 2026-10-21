"""script-processing extract 缓存测试。"""

from __future__ import annotations

import pytest

from app.api.v1.routes import script_processing as route
from app.schemas.skills.script_processing import StudioScriptExtractionDraft
from app.services.script_extraction_cache import (
    build_script_extract_cache_key,
    clear_script_extract_cache,
)


def _build_result() -> StudioScriptExtractionDraft:
    return StudioScriptExtractionDraft(
        project_id="project-1",
        chapter_id="chapter-1",
        script_text="测试文本",
        characters=[],
        scenes=[],
        props=[],
        costumes=[],
        shots=[],
    )


class _FakeDB:
    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True


async def _async_noop(*_args, **_kwargs) -> None:
    return None


@pytest.mark.asyncio
async def test_extract_script_uses_cache_by_default(monkeypatch):
    clear_script_extract_cache()
    calls: list[str] = []
    db = _FakeDB()

    class _FakeAgent:
        def __init__(self, _llm):
            pass

        def extract(self, **_kwargs):
            calls.append("extract")
            return _build_result()

    monkeypatch.setattr(route, "ElementExtractorAgent", _FakeAgent)
    monkeypatch.setattr(route, "sync_shot_extracted_candidates_from_draft", _async_noop)
    monkeypatch.setattr(route, "sync_shot_extracted_dialogue_candidates_from_draft", _async_noop)
    monkeypatch.setattr(route, "apply_shot_semantic_defaults_from_draft", _async_noop)

    request = route.ScriptExtractRequest(
        project_id="project-1",
        chapter_id="chapter-1",
        script_division={"total_shots": 1, "shots": [{"index": 1, "script_excerpt": "a", "shot_name": "s"}]},
        consistency=None,
        refresh_cache=False,
    )

    first = await route.extract_script(request, llm=None, db=db)
    second = await route.extract_script(request, llm=None, db=db)

    assert first.data is not None
    assert second.data is not None
    assert first.meta == {"from_cache": False}
    assert second.meta == {"from_cache": True}
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_extract_script_refresh_cache_forces_recompute(monkeypatch):
    clear_script_extract_cache()
    calls: list[str] = []
    db = _FakeDB()

    class _FakeAgent:
        def __init__(self, _llm):
            pass

        def extract(self, **_kwargs):
            calls.append("extract")
            return _build_result()

    monkeypatch.setattr(route, "ElementExtractorAgent", _FakeAgent)
    monkeypatch.setattr(route, "sync_shot_extracted_candidates_from_draft", _async_noop)
    monkeypatch.setattr(route, "sync_shot_extracted_dialogue_candidates_from_draft", _async_noop)
    monkeypatch.setattr(route, "apply_shot_semantic_defaults_from_draft", _async_noop)

    request = route.ScriptExtractRequest(
        project_id="project-1",
        chapter_id="chapter-1",
        script_division={"total_shots": 1, "shots": [{"index": 1, "script_excerpt": "a", "shot_name": "s"}]},
        consistency=None,
        refresh_cache=False,
    )
    refresh_request = request.model_copy(update={"refresh_cache": True})

    await route.extract_script(request, llm=None, db=db)
    refreshed = await route.extract_script(refresh_request, llm=None, db=db)

    assert refreshed.meta == {"from_cache": False}
    assert len(calls) == 2


def test_build_script_extract_cache_key_changes_when_payload_changes():
    key1 = build_script_extract_cache_key(
        project_id="project-1",
        chapter_id="chapter-1",
        script_division={"total_shots": 1, "shots": [{"index": 1}]},
        consistency=None,
    )
    key2 = build_script_extract_cache_key(
        project_id="project-1",
        chapter_id="chapter-1",
        script_division={"total_shots": 2, "shots": [{"index": 1}, {"index": 2}]},
        consistency=None,
    )

    assert key1 != key2
