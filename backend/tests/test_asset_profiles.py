"""P4 / C7：角色别名、资产版本、候选图、身份锁定与音色测试（Mock 媒体）。"""

from __future__ import annotations

import io
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.datastructures import UploadFile

from app.core.db import Base
from app.core.storage import StoredFileInfo
from app.models.studio import (
    Actor,
    AssetImageCandidate,
    AssetVersion,
    Character,
    CharacterAlias,
    Project,
    ProjectSceneLink,
    ProjectStyle,
    ProjectVisualStyle,
    Scene,
)
from app.schemas.studio.asset_versions import (
    AssetProfileUpdate,
    CreateDerivedVersionRequest,
    VoiceBindingUpdate,
)
from app.services.studio import asset_image_candidates as candidate_svc
from app.services.studio.asset_image_candidates import (
    adopt_candidate,
    delete_candidate,
    generate_candidates,
    upload_candidate,
)
from app.services.studio.asset_profiles import (
    build_asset_profile,
    update_asset_profile,
)
from app.services.studio.script_parse_runner import ParseMergeAccumulator
from app.schemas.skills.script_parse import ParsedCharacter, ScriptParseResult
from app.services.studio.script_parse_chunking import split_script_for_parse
from app.services.studio.asset_versions import (
    create_derived_version,
    delete_version,
    ensure_base_version,
    list_versions,
)
from app.services.studio.character_aliases import add_alias, import_aliases
from app.services.common.workspace import resolve_workspace_id
from app.services.studio.project_generation_config import (
    resolve_project_id_for_image_relation,
)
from app.services.studio.entity_crud import list_entities_paginated
from app.services.studio.character_identity import (
    get_voice_binding,
    lock_identity,
    update_voice_binding,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"p4-test-image-bytes"


async def _build_session() -> tuple[AsyncSession, object]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return maker(), engine


async def _seed(db: AsyncSession) -> tuple[Project, Character, Scene]:
    project = Project(
        id="p4-project",
        workspace_id="ws-p4",
        name="都市短剧",
        description="",
        style=ProjectStyle.real_people_city,
        visual_style=ProjectVisualStyle.live_action,
    )
    actor = Actor(
        id="actor-1",
        name="演员甲",
        description="",
        style=ProjectStyle.real_people_city,
        visual_style=ProjectVisualStyle.live_action,
        voice_id="actor-voice",
        voice_source="preset",
    )
    character = Character(
        id="char-1",
        project_id=project.id,
        name="沈知微",
        description="职业女性",
        style=project.style,
        visual_style=project.visual_style,
        appearance="黑色西装，短发",
        actor_id=actor.id,
    )
    scene = Scene(
        id="scene-1",
        name="总裁办公室",
        description="落地窗办公室",
        style=project.style,
        visual_style=project.visual_style,
    )
    db.add_all(
        [
            project,
            actor,
            character,
            scene,
            ProjectSceneLink(project_id=project.id, scene_id=scene.id),
        ]
    )
    await db.commit()
    return project, character, scene


def _upload(name: str = "角色.png") -> UploadFile:
    return UploadFile(file=io.BytesIO(PNG), filename=name)


@pytest.fixture(autouse=True)
def _mock_storage(monkeypatch):
    async def _fake_upload(*, key, data, content_type=None, extra_args=None):
        return StoredFileInfo(key=key, url=f"https://mock.local/{key}", size=len(data))

    monkeypatch.setattr(candidate_svc.storage, "upload_file", _fake_upload)
    return _fake_upload


@pytest.mark.asyncio
async def test_alias_persistence_and_conflict() -> None:
    db, engine = await _build_session()
    async with db:
        project, character, _scene = await _seed(db)
        other = Character(
            id="char-2",
            project_id=project.id,
            name="江屿",
            description="",
            style=project.style,
            visual_style=project.visual_style,
        )
        db.add(other)
        await db.commit()

        alias = await add_alias(db, character=character, alias="沈总", source="manual")
        assert alias is not None
        assert alias.normalized_alias == "沈总"
        duplicate = await add_alias(db, character=character, alias=" 沈总 ")
        assert duplicate is not None and duplicate.id == alias.id

        with pytest.raises(ValueError, match="已被角色"):
            await add_alias(db, character=other, alias="沈总")
        skipped = await import_aliases(
            db, character=other, aliases=["沈总", "小江"], source="p3_parse"
        )
        assert "沈总" in skipped
        aliases = (
            await db.execute(
                select(CharacterAlias).where(CharacterAlias.character_id == other.id)
            )
        ).scalars().all()
        assert [item.alias for item in aliases] == ["小江"]
    await engine.dispose()


@pytest.mark.asyncio
async def test_profile_upload_adopt_lock_and_voice() -> None:
    db, engine = await _build_session()
    async with db:
        project, character, _scene = await _seed(db)
        profile = await build_asset_profile(
            db, project_id=project.id, asset_type="character", asset_id=character.id
        )
        assert profile.versions and profile.identity_version_id
        assert profile.identity_locked is False

        uploaded = await upload_candidate(
            db,
            project=project,
            asset_type="character",
            asset_id=character.id,
            view_angle="front",
            file=_upload(),
        )
        assert uploaded.source == "uploaded"
        assert uploaded.status == "succeeded"
        await adopt_candidate(
            db, candidate=uploaded, project=project, adopted_by=1
        )
        await db.flush()

        locked = await lock_identity(
            db, character=character, expected_lock_version=0, locked_by=1
        )
        assert locked.identity_locked_at is not None
        assert locked.identity_lock_version == 1

        with pytest.raises(ValueError, match="视觉身份已锁定"):
            await update_asset_profile(
                db,
                project_id=project.id,
                asset_type="character",
                asset_id=character.id,
                body=AssetProfileUpdate(name="改名"),
            )

        # 音色未绑定也能锁定；音色回退到 Actor，绑定后角色覆盖 Actor。
        voice = await get_voice_binding(db, character=character)
        assert voice.effective_voice_id == "actor-voice"
        assert voice.effective_from == "actor"
        await update_voice_binding(
            db,
            character=character,
            body=VoiceBindingUpdate(voice_id="char-voice", voice_source="preset"),
            bound_by=1,
        )
        voice = await get_voice_binding(db, character=character)
        assert voice.effective_voice_id == "char-voice"
        assert voice.effective_from == "character"
        assert character.identity_locked_at is not None

        refreshed = await build_asset_profile(
            db, project_id=project.id, asset_type="character", asset_id=character.id
        )
        assert refreshed.identity_locked is True
        assert refreshed.thumbnail
        assert any(item.is_adopted for item in refreshed.candidates)
    await engine.dispose()


@pytest.mark.asyncio
async def test_generate_two_candidates_without_auto_adopt(monkeypatch) -> None:
    db, engine = await _build_session()
    async with db:
        project, character, _scene = await _seed(db)

        async def _fake_model(_db, _model_id, project_id=None):
            return type("M", (), {"id": "img-model", "name": "mock-image", "provider_id": "prov"})()

        async def _fake_stage(**kwargs):
            return f"task-{uuid.uuid4().hex}"

        monkeypatch.setattr(candidate_svc, "resolve_image_model", _fake_model)
        monkeypatch.setattr(candidate_svc, "stage_image_task_and_link", _fake_stage)

        rows = await generate_candidates(
            db,
            project=project,
            asset_type="character",
            asset_id=character.id,
            candidate_count=2,
        )
        assert len(rows) == 2
        assert all(item.status == "pending" for item in rows)
        assert all(item.generation_task_id for item in rows)
        assert len({item.candidate_batch_id for item in rows}) == 1
        assert not any(item.is_adopted for item in rows)
        await db.flush()
        candidates = (
            await db.execute(
                select(AssetImageCandidate).where(
                    AssetImageCandidate.asset_id == character.id
                )
            )
        ).scalars().all()
        assert len(candidates) == 2
    await engine.dispose()


@pytest.mark.asyncio
async def test_scene_derived_version_switch_and_delete_protection() -> None:
    db, engine = await _build_session()
    async with db:
        project, _character, scene = await _seed(db)
        base = await ensure_base_version(
            db, asset_type="scene", asset_id=scene.id, source="p3_confirm"
        )
        assert base.version_kind == "base"
        derived = await create_derived_version(
            db,
            asset_type="scene",
            asset_id=scene.id,
            body=CreateDerivedVersionRequest(
                name="夜晚办公室",
                description="灯光关闭，窗外霓虹",
                variant_type="lighting",
                activate=True,
            ),
            created_by=1,
        )
        assert derived.version_kind == "derived"
        assert scene.current_version_id == derived.id
        versions = await list_versions(db, asset_type="scene", asset_id=scene.id)
        statuses = {item.id: item.status for item in versions}
        assert statuses[base.id] == "superseded"
        assert statuses[derived.id] == "active"

        with pytest.raises(ValueError, match="不可删除"):
            await delete_version(
                db,
                asset_type="scene",
                asset_id=scene.id,
                version_id=derived.id,
            )
    await engine.dispose()


@pytest.mark.asyncio
async def test_adopted_candidate_cannot_be_deleted() -> None:
    db, engine = await _build_session()
    async with db:
        project, character, _scene = await _seed(db)
        uploaded = await upload_candidate(
            db,
            project=project,
            asset_type="character",
            asset_id=character.id,
            view_angle="front",
            file=_upload(),
        )
        await adopt_candidate(db, candidate=uploaded, project=project, adopted_by=1)
        with pytest.raises(ValueError, match="已采纳"):
            await delete_candidate(db, candidate=uploaded)
    await engine.dispose()


@pytest.mark.asyncio
async def test_candidate_relation_resolves_project_and_workspace() -> None:
    db, engine = await _build_session()
    async with db:
        project, character, _scene = await _seed(db)
        uploaded = await upload_candidate(
            db,
            project=project,
            asset_type="character",
            asset_id=character.id,
            view_angle="front",
            file=_upload(),
        )
        assert (
            await resolve_project_id_for_image_relation(
                db,
                relation_type="asset_image_candidate",
                relation_entity_id=str(uploaded.id),
            )
            == project.id
        )
        assert (
            await resolve_workspace_id(
                db,
                relation_type="asset_image_candidate",
                relation_entity_id=str(uploaded.id),
            )
            == "ws-p4"
        )
    await engine.dispose()


@pytest.mark.asyncio
async def test_existing_alias_prematches_p3_character_candidate() -> None:
    db, engine = await _build_session()
    async with db:
        _project, character, _scene = await _seed(db)
        await add_alias(db, character=character, alias="沈总")
        from sqlalchemy.orm import selectinload

        loaded = (
            await db.execute(
                select(Character)
                .options(selectinload(Character.aliases))
                .where(Character.id == character.id)
            )
        ).scalars().first()
        assert loaded is not None
        accumulator = ParseMergeAccumulator(
            existing_characters=[loaded],
            existing_scenes=[],
            existing_props=[],
            existing_costumes=[],
        )
        chunk = split_script_for_parse("沈总：你来了。")[0]
        accumulator.merge_result(
            ScriptParseResult(
                characters=[ParsedCharacter(name="沈总", aliases=["沈知微"])],
            ),
            chunk,
        )
        result = accumulator.result()
        assert result.characters[0].matched_character_id == character.id
    await engine.dispose()


@pytest.mark.asyncio
async def test_project_level_asset_query_filters_without_cross_project_leak() -> None:
    db, engine = await _build_session()
    async with db:
        project, character, scene = await _seed(db)
        other = Project(
            id="p4-project-2",
            workspace_id="ws-p4",
            name="另一项目",
            description="",
            style=ProjectStyle.real_people_city,
            visual_style=ProjectVisualStyle.live_action,
        )
        other_scene = Scene(
            id="scene-other",
            name="另一办公室",
            description="",
            style=project.style,
            visual_style=project.visual_style,
        )
        db.add_all(
            [
                other,
                other_scene,
                ProjectSceneLink(project_id=other.id, scene_id=other_scene.id),
            ]
        )
        await db.commit()

        chars, char_total = await list_entities_paginated(
            db,
            entity_type="character",
            q=None,
            style=None,
            visual_style=None,
            order="name",
            is_desc=False,
            page=1,
            page_size=100,
            workspace_id="ws-p4",
            project_id=project.id,
        )
        scenes, scene_total = await list_entities_paginated(
            db,
            entity_type="scene",
            q=None,
            style=None,
            visual_style=None,
            order="name",
            is_desc=False,
            page=1,
            page_size=100,
            workspace_id="ws-p4",
            project_id=project.id,
        )
        assert char_total == 1 and chars[0]["id"] == character.id
        assert scene_total == 1 and scenes[0]["id"] == scene.id
    await engine.dispose()


@pytest.mark.asyncio
async def test_adopted_front_candidate_wins_over_old_image_slot() -> None:
    """采纳的正面候选必须成为资产缩略图。

    回归背景：`_thumbnail_file_id` 用小写 "front" 与数据库大写 "FRONT" 比较，
    场景已有旧 image 槽位时会永远显示旧图，采纳新图后档案看起来「没变化」。
    """
    from app.models.studio_asset_versions import AssetImageCandidate
    from app.services.studio.asset_profiles import _thumbnail_file_id

    db, engine = await _build_session()
    async with db:
        candidate = AssetImageCandidate(
            project_id="p1",
            asset_type="scene",
            asset_id="scene-1",
            candidate_batch_id="batch",
            view_angle="FRONT",
            quality_level="low",
            file_id="new-file",
            status="adopted",
            is_adopted=True,
        )
        file_id = await _thumbnail_file_id(
            db, asset_type="scene", asset_id="scene-1", candidates=[candidate]
        )
        assert file_id == "new-file"
    await engine.dispose()
