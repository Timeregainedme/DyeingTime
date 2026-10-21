from __future__ import annotations

from types import SimpleNamespace

from app.schemas.studio.shots import ShotPreparationLinkEntityType
from app.services.studio import shot_preparation_state as svc


def test_link_existing_asset_for_preparation_accepts_enum_value(monkeypatch) -> None:
    calls: dict[str, object] = {}

    async def _fake_create_project_asset_link(db, *, entity_type, body):
        calls["entity_type"] = entity_type
        calls["body"] = body

    async def _fake_build_state(db, *, shot_id: str):
        return SimpleNamespace(shot_id=shot_id)

    monkeypatch.setattr(svc, "create_project_asset_link", _fake_create_project_asset_link)
    monkeypatch.setattr(svc, "build_shot_preparation_state", _fake_build_state)

    import asyncio

    result = asyncio.run(
        svc.link_existing_asset_for_preparation(
            None,
            project_id="project-1",
            chapter_id="chapter-1",
            shot_id="shot-1",
            entity_type=ShotPreparationLinkEntityType.scene,
            linked_entity_id="scene-1",
        )
    )

    assert calls["entity_type"] == "scene"
    assert calls["body"].asset_id == "scene-1"
    assert result.shot_id == "shot-1"
