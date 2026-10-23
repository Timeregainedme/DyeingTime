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
                type("M", (), {"name": "MiniMax-H3", "id": "m1"})(),
                type("P", (), {"provider": "compshare_model_api", "base_url": None})(),
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


@pytest.mark.asyncio
async def test_submit_rejects_stale_preview_hash(monkeypatch) -> None:
    from app.schemas.studio.shot_references import GenerationPreviewRead, P6VideoGenerateRequest

    db, engine = await _build_session()
    async with db:
        await _seed(db)

        async def _fake_preview(*args, **kwargs):
            return GenerationPreviewRead(
                shot_id="ref-shot",
                images=["ref-file-front"],
                prompt="stable prompt",
                input_hash="preview-hash",
            )

        monkeypatch.setattr(shot_references, "build_generation_preview", _fake_preview)
        with pytest.raises(ValueError, match="刷新预览"):
            await shot_references.create_video_task(
                db,
                shot_id="ref-shot",
                body=P6VideoGenerateRequest(
                    prompt="changed after preview",
                    expected_input_hash="stale-hash",
                ),
            )
    await engine.dispose()


@pytest.mark.asyncio
async def test_prompt_reference_survives_character_rename() -> None:
    from sqlalchemy import delete

    from app.models.studio import CharacterAlias

    db, engine = await _build_session()
    async with db:
        seed = await _seed(db)
        await auto_recommend(db, shot_id="ref-shot")
        await shot_references.save_prompt(
            db, shot_id="ref-shot", prompt="@沈总 看向窗外。"
        )
        character = await db.get(Character, seed["character"].id)
        assert character is not None
        character.name = "沈知微改名"
        await db.execute(
            delete(CharacterAlias).where(CharacterAlias.character_id == character.id)
        )
        await db.flush()
        result = await resolve_prompt_references(
            db, shot_id="ref-shot", prompt="@沈总 看向窗外。"
        )
        assert result.unresolved == []
        assert result.resolved[0].asset_id == character.id
        assert result.resolved[0].asset_name == "沈知微改名"
    await engine.dispose()


@pytest.mark.asyncio
async def test_request_key_returns_existing_task_and_rejects_payload_change(monkeypatch) -> None:
    from app.schemas.studio.shot_references import GenerationPreviewRead, P6VideoGenerateRequest
    from app.schemas.studio.shots import ShotVideoReadinessRead

    db, engine = await _build_session()
    async with db:
        await _seed(db)
        await auto_recommend(db, shot_id="ref-shot")
        refs, manifest, _warnings = await build_manifest(db, shot_id="ref-shot")
        preview = GenerationPreviewRead(
            shot_id="ref-shot",
            manifest=[],
            images=[item.file_id for item in refs if item.file_id],
            prompt="stable prompt",
            input_hash="hash-1",
            duration=5,
            ratio="9:16",
        )
        snapshot = await create_snapshot(
            db,
            shot_id="ref-shot",
            preview=preview,
            task_id="existing-task",
            created_by=1,
            request_key="req-1",
        )
        await db.commit()

        async def _fake_preview(*args, **kwargs):
            return preview

        async def _fake_ready(*args, **kwargs):
            return ShotVideoReadinessRead(
                shot_id="ref-shot", reference_mode="reference", ready=True, checks=[]
            )

        monkeypatch.setattr(shot_references, "build_generation_preview", _fake_preview)
        monkeypatch.setattr(shot_references, "get_p6_readiness", _fake_ready)
        task_id, existing, _ = await shot_references.create_video_task(
            db,
            shot_id="ref-shot",
            body=P6VideoGenerateRequest(
                prompt="same",
                expected_input_hash="hash-1",
                request_key="req-1",
            ),
        )
        assert task_id == "existing-task"
        assert existing.id == snapshot.id

        changed = preview.model_copy(update={"input_hash": "hash-2"})

        async def _changed_preview(*args, **kwargs):
            return changed

        monkeypatch.setattr(shot_references, "build_generation_preview", _changed_preview)
        with pytest.raises(ValueError, match="不同生成输入"):
            await shot_references.create_video_task(
                db,
                shot_id="ref-shot",
                body=P6VideoGenerateRequest(
                    prompt="different",
                    expected_input_hash="hash-2",
                    request_key="req-1",
                ),
            )
    await engine.dispose()


def test_legacy_generating_status_is_read_as_pending() -> None:
    from app.services.studio.shot_status import normalize_shot_status

    assert normalize_shot_status("generating") == "pending"
    assert normalize_shot_status("ready") == "ready"
    assert normalize_shot_status("pending") == "pending"


@pytest.mark.asyncio
async def test_p6_readiness_uses_active_bindings_not_old_ir(monkeypatch) -> None:
    from app.schemas.studio.shots import ShotVideoReadinessCheck, ShotVideoReadinessRead
    from app.services.studio import shot_video_readiness as base_readiness

    db, engine = await _build_session()
    async with db:
        await _seed(db)
        await auto_recommend(db, shot_id="ref-shot")

        async def _fake_base(*args, **kwargs):
            return ShotVideoReadinessRead(
                shot_id="ref-shot",
                reference_mode="reference",
                ready=False,
                checks=[
                    ShotVideoReadinessCheck(
                        key="reference_images_ready",
                        ok=False,
                        message="旧 IR 自动收集不到参考图",
                    )
                ],
            )

        monkeypatch.setattr(base_readiness, "get_shot_video_readiness", _fake_base)
        result = await shot_references.get_p6_readiness(db, shot_id="ref-shot")
        reference_check = next(item for item in result.checks if item.key == "reference_images_ready")
        assert reference_check.ok is True
        assert "有序参考图" in reference_check.message
    await engine.dispose()


@pytest.mark.asyncio
async def test_generation_quality_checks_cover_voice_and_continuity() -> None:
    from app.models.studio import ShotDialogLine

    db, engine = await _build_session()
    async with db:
        seed = await _seed(db)
        detail = await db.get(ShotDetail, "ref-shot")
        assert detail is not None
        detail.scene_id = "ref-scene"
        character = seed["character"]
        character.voice_description = "年轻成年男性声音，音色清晰，语速适中。"
        db.add(
            ShotDialogLine(
                shot_detail_id="ref-shot",
                index=1,
                text="你先听我解释。",
                speaker_character_id=character.id,
                speaker_name="沈知微",
            )
        )
        await auto_recommend(db, shot_id="ref-shot")
        await db.flush()
        checks = await shot_references.collect_generation_quality_checks(
            db,
            shot_id="ref-shot",
            advanced_prompt="<Subject 1> talks to the camera.",
        )
        codes = {item.code: item for item in checks}
        assert codes["advanced_prompt_missing_dialogue"].level == "warning"
        assert codes["advanced_prompt_missing_continuity"].level == "warning"
        assert codes["scene_reference_ready"].level == "info"
        assert "prompt_voice_gender_conflict" not in codes
        assert not any(item.level == "blocking" for item in checks)

        # 短镜头多机位线索应提示拆分，而不是简单禁用“切”字。
        detail = await db.get(ShotDetail, "ref-shot")
        assert detail is not None
        detail.video_prompt_draft = "先特写男性，再切双人远景，最后切女性面部特写。"
        await db.flush()
        checks = await shot_references.collect_generation_quality_checks(
            db, shot_id="ref-shot"
        )
        assert any(item.code == "short_shot_multi_camera" and item.level == "warning" for item in checks)

        # 用户主动移除场景参考后保留其选择，但明确提示空间连续性风险。
        active = await shot_references.list_bindings(db, shot_id="ref-shot", active_only=True)
        scene_binding = next(item for item in active if item.file_id == "ref-file-scene")
        await remove_binding(db, binding_id=scene_binding.id, shot_id="ref-shot")
        checks = await shot_references.collect_generation_quality_checks(
            db, shot_id="ref-shot"
        )
        assert any(item.code == "scene_reference_missing" and item.level == "warning" for item in checks)

        # 声音描述缺失是 warning，而不是把镜头直接判死。
        character.voice_description = ""
        await db.flush()
        checks = await shot_references.collect_generation_quality_checks(
            db, shot_id="ref-shot", advanced_prompt=""
        )
        assert any(item.code == "character_voice_missing" and item.level == "warning" for item in checks)
    await engine.dispose()


@pytest.mark.asyncio
async def test_generation_quality_blocking_for_unknown_speaker() -> None:
    from app.models.studio import ShotDialogLine

    db, engine = await _build_session()
    async with db:
        await _seed(db)
        db.add(
            ShotDialogLine(
                shot_detail_id="ref-shot",
                index=1,
                text="无效说话人。",
                speaker_character_id="missing-char",
                speaker_name="未知",
            )
        )
        await db.flush()
        checks = await shot_references.collect_generation_quality_checks(
            db, shot_id="ref-shot"
        )
        blocking = [item for item in checks if item.level == "blocking"]
        assert any(item.code == "dialogue_speaker_unknown" for item in blocking)
    await engine.dispose()


@pytest.mark.asyncio
async def test_preview_input_hash_changes_with_voice_and_continuity(monkeypatch) -> None:
    from app.chains.prompts import ir as ir_module
    from app.models.studio import ShotDialogLine

    db, engine = await _build_session()
    async with db:
        seed = await _seed(db)
        detail = await db.get(ShotDetail, "ref-shot")
        assert detail is not None
        detail.scene_id = "ref-scene"
        character = seed["character"]
        character.voice_description = "年轻成年男性声音，音色清晰，语速适中。"
        db.add(
            ShotDialogLine(
                shot_detail_id="ref-shot",
                index=1,
                text="你先听我解释。",
                speaker_character_id=character.id,
                speaker_name="沈知微",
            )
        )
        await auto_recommend(db, shot_id="ref-shot")
        await db.flush()

        async def _fake_options(_db, *, shot_id, ratio, resolution):
            return (
                type("M", (), {"name": "MiniMax-H3", "id": "m1"})(),
                type("P", (), {"provider": "compshare_model_api", "base_url": None})(),
                ratio or "9:16",
                resolution or "768p",
                5,
            )

        monkeypatch.setattr(shot_references, "_resolve_options", _fake_options)
        first = await build_generation_preview(
            db, shot_id="ref-shot", natural_prompt="@沈总 看着窗外。"
        )
        assert "using this voice profile" in first.prompt
        assert "do not cut to another location" in first.prompt
        assert first.input_hash

        character.voice_description = "成年女性声音，冷静。"
        await db.flush()
        second = await build_generation_preview(
            db, shot_id="ref-shot", natural_prompt="@沈总 看着窗外。"
        )
        assert second.input_hash != first.input_hash

        monkeypatch.setattr(
            ir_module,
            "DEFAULT_CONTINUITY_WITH_SCENE",
            "Keep one locked office background; use a continuous camera and no cut.",
        )
        third = await build_generation_preview(
            db, shot_id="ref-shot", natural_prompt="@沈总 看着窗外。"
        )
        assert third.input_hash != second.input_hash
        assert "locked office background" in third.prompt
    await engine.dispose()


@pytest.mark.asyncio
async def test_generation_quality_blocking_for_unknown_scene() -> None:
    db, engine = await _build_session()
    async with db:
        await _seed(db)
        row = (
            await db.execute(
                select(ShotAssetVersion).where(
                    ShotAssetVersion.shot_id == "ref-shot",
                    ShotAssetVersion.asset_type == "scene",
                )
            )
        ).scalars().first()
        assert row is not None
        row.asset_id = "missing-scene"
        await db.flush()
        checks = await shot_references.collect_generation_quality_checks(
            db, shot_id="ref-shot"
        )
        blocking = [item for item in checks if item.level == "blocking"]
        assert any(item.code == "scene_asset_unknown" for item in blocking)
    await engine.dispose()
