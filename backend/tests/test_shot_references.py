"""P6 / C11：参考绑定、@ 引用、H3 预览与快照测试。"""

from __future__ import annotations

import io

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.datastructures import UploadFile

from app.core.db import Base
from app.core.storage import StoredFileInfo
from app.models.studio import (
    AssetImageCandidate,
    AssetVersion,
    Chapter,
    Character,
    CharacterAlias,
    FileItem,
    Project,
    ProjectSceneLink,
    ProjectStyle,
    ProjectVisualStyle,
    Scene,
    Shot,
    ShotAssetVersion,
    ShotDetail,
    ShotGenerationSnapshot,
    ShotReferenceBinding,
)
from app.services.studio import shot_references
from app.services.studio.shot_references import (
    auto_recommend,
    build_generation_preview,
    build_manifest,
    create_snapshot,
    remove_binding,
    reorder_bindings,
    resolve_prompt_references,
    update_binding,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"reference"


async def _build_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return maker(), engine


@pytest.fixture(autouse=True)
def _storage(monkeypatch):
    async def _fake(*, key, data, content_type=None, extra_args=None):
        return StoredFileInfo(key=key, url=f"https://mock.local/{key}", size=len(data))

    monkeypatch.setattr(shot_references.storage, "upload_file", _fake)


async def _seed(db: AsyncSession) -> dict[str, object]:
    project = Project(
        id="ref-project",
        workspace_id="ws-ref",
        name="都市短剧",
        description="",
        style=ProjectStyle.real_people_city,
        visual_style=ProjectVisualStyle.live_action,
    )
    chapter = Chapter(id="ref-chapter", project_id=project.id, index=1, title="第1集", raw_text="沈知微看窗外。")
    shot = Shot(id="ref-shot", chapter_id=chapter.id, index=1, title="窗边", script_excerpt="沈知微看窗外。")
    detail = ShotDetail(
        id=shot.id,
        camera_shot="MS",
        angle="EYE_LEVEL",
        movement="STATIC",
        duration=5,
    )
    identity = AssetVersion(
        id="ref-identity",
        project_id=project.id,
        asset_type="character",
        asset_id="ref-char",
        version_no=1,
        version_kind="identity",
        variant_type="base",
        name="沈知微身份",
        status="active",
    )
    character = Character(
        id="ref-char",
        project_id=project.id,
        name="沈知微",
        description="",
        style=project.style,
        visual_style=project.visual_style,
        identity_version_id=identity.id,
    )
    scene = Scene(id="ref-scene", name="办公室", description="", style=project.style, visual_style=project.visual_style)
    scene_version = AssetVersion(
        id="ref-scene-version",
        project_id=project.id,
        asset_type="scene",
        asset_id=scene.id,
        version_no=1,
        version_kind="base",
        variant_type="base",
        name="办公室基础",
        status="active",
    )
    scene.current_version_id = scene_version.id
    files = [
        FileItem(id="ref-file-front", type="image", name="front", thumbnail="https://mock/front.png", tags=[], storage_key="k1"),
        FileItem(id="ref-file-left", type="image", name="left", thumbnail="https://mock/left.png", tags=[], storage_key="k2"),
        FileItem(id="ref-file-scene", type="image", name="scene", thumbnail="https://mock/scene.png", tags=[], storage_key="k3"),
    ]
    db.add_all(
        [
            project,
            chapter,
            shot,
            detail,
            identity,
            character,
            CharacterAlias(character_id=character.id, alias="沈总", normalized_alias="沈总"),
            scene,
            scene_version,
            *files,
            ProjectSceneLink(project_id=project.id, scene_id=scene.id),
            AssetImageCandidate(
                project_id=project.id,
                asset_type="character",
                asset_id=character.id,
                asset_version_id=identity.id,
                candidate_batch_id="b1",
                view_angle="FRONT",
                source="uploaded",
                file_id="ref-file-front",
                status="adopted",
                is_adopted=True,
                prompt="",
                generation_params={},
                format="png",
            ),
            AssetImageCandidate(
                project_id=project.id,
                asset_type="character",
                asset_id=character.id,
                asset_version_id=identity.id,
                candidate_batch_id="b1",
                view_angle="LEFT",
                source="uploaded",
                file_id="ref-file-left",
                status="adopted",
                is_adopted=True,
                prompt="",
                generation_params={},
                format="png",
            ),
            AssetImageCandidate(
                project_id=project.id,
                asset_type="scene",
                asset_id=scene.id,
                asset_version_id=scene_version.id,
                candidate_batch_id="b2",
                view_angle="FRONT",
                source="uploaded",
                file_id="ref-file-scene",
                status="adopted",
                is_adopted=True,
                prompt="",
                generation_params={},
                format="png",
            ),
            ShotAssetVersion(
                shot_id=shot.id,
                asset_type="character",
                asset_id=character.id,
                asset_version_id=identity.id,
                role="character_identity",
                created_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
            ),
            ShotAssetVersion(
                shot_id=shot.id,
                asset_type="scene",
                asset_id=scene.id,
                asset_version_id=scene_version.id,
                role="scene",
                created_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
            ),
        ]
    )
    await db.commit()
    return {"project": project, "shot": shot, "character": character, "scene": scene}


@pytest.mark.asyncio
async def test_auto_recommend_respects_version_and_manual_remove() -> None:
    db, engine = await _build_session()
    async with db:
        await _seed(db)
        rows = await auto_recommend(db, shot_id="ref-shot")
        assert [item.file_id for item in rows] == [
            "ref-file-front",
            "ref-file-left",
            "ref-file-scene",
        ]
        assert rows[0].asset_version_id == "ref-identity"
        assert rows[2].asset_version_id == "ref-scene-version"
        # 删除自动项后再次推荐不会恢复。
        await remove_binding(db, binding_id=rows[1].id, shot_id="ref-shot")
        await auto_recommend(db, shot_id="ref-shot")
        active = [item for item in await shot_references.list_bindings(db, shot_id="ref-shot", active_only=True)]
        assert "ref-file-left" not in {item.file_id for item in active}

        # 人工锁定后不能直接删除；排序必须包含全部启用项。
        pinned = await shot_references.update_binding(
            db, binding_id=rows[0].id, shot_id="ref-shot", is_pinned=True
        )
        assert pinned.is_pinned
        with pytest.raises(ValueError, match="锁定"):
            await remove_binding(db, binding_id=rows[0].id, shot_id="ref-shot")
        ordered = await reorder_bindings(
            db, shot_id="ref-shot", binding_ids=[rows[2].id, rows[0].id]
        )
        assert [item.file_id for item in ordered] == ["ref-file-scene", "ref-file-front"]
    await engine.dispose()


@pytest.mark.asyncio
async def test_at_reference_and_preview_snapshot_consistent() -> None:
    db, engine = await _build_session()
    async with db:
        await _seed(db)
        await auto_recommend(db, shot_id="ref-shot")
        resolved = await resolve_prompt_references(
            db, shot_id="ref-shot", prompt="@沈总 看着窗外，@办公室 灯光变暗。"
        )
        assert [item.asset_id for item in resolved.resolved] == ["ref-char", "ref-scene"]
        assert resolved.unresolved == []

        # 避免测试依赖真实视频/文本模型配置。
        async def _fake_options(_db, *, shot_id, ratio, resolution):
            return (
                type("M", (), {"name": "mock-video", "id": "m1"})(),
                type("P", (), {"provider": "mock", "base_url": None})(),
                ratio or "9:16",
                resolution or "768p",
                5,
            )

        original = shot_references._resolve_options
        shot_references._resolve_options = _fake_options
        try:
            preview = await build_generation_preview(
                db,
                shot_id="ref-shot",
                natural_prompt="@沈总 看着窗外。",
                advanced_prompt="<Picture 1> and <Picture 2> preserve identity.",
                ratio="9:16",
                resolution="768p",
            )
        finally:
            shot_references._resolve_options = original
        assert preview.blocking_errors == []
        assert preview.images[:2] == ["ref-file-front", "ref-file-left"]
        assert preview.prompt.startswith("<Picture 1>")
        refs, manifest, warnings = await build_manifest(db, shot_id="ref-shot")
        assert [item.file_id for item in refs] == preview.images
        assert warnings == []

        snapshot = await create_snapshot(
            db, shot_id="ref-shot", preview=preview, task_id=None, created_by=1
        )
        assert snapshot.manifest[0]["file_id"] == "ref-file-front"
        # 资产版本变化不应修改历史快照。
        snapshot_id = snapshot.id
        asset = await db.get(AssetVersion, "ref-scene-version")
        assert asset is not None
        asset.description = "changed later"
        await db.flush()
        old = await db.get(ShotGenerationSnapshot, snapshot_id)
        assert old is not None
        assert old.manifest[2]["asset_version_id"] == "ref-scene-version"
    await engine.dispose()


@pytest.mark.asyncio
async def test_uploaded_reference_is_pinned() -> None:
    db, engine = await _build_session()
    async with db:
        await _seed(db)
        upload = UploadFile(file=io.BytesIO(PNG), filename="镜头参考.png")
        binding = await shot_references.upload_reference(
            db, shot_id="ref-shot", file=upload, created_by=1
        )
        assert binding.source == "uploaded"
        assert binding.is_pinned is True
        assert binding.file_url
    await engine.dispose()
