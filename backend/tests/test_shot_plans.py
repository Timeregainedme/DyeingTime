"""P5 / C10：Mock AI 分镜规划、候选审核与正式 Shot 写入测试。"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db import Base
from app.models.studio import (
    AssetVersion,
    Chapter,
    Character,
    CharacterAlias,
    Costume,
    Project,
    ProjectCostumeLink,
    ProjectPropLink,
    ProjectSceneLink,
    ProjectStyle,
    ProjectVisualStyle,
    Prop,
    Scene,
    SceneGroup,
    ScriptDocument,
    ScriptDocumentVersion,
    Shot,
    ShotAssetVersion,
    ShotCharacterLink,
    ShotDialogLine,
    ShotDetail,
    ShotPlanCandidate,
    ShotPlanDraft,
)
from app.models.task import GenerationTask
from app.schemas.skills.shot_planning import PlannedDialogue, PlannedShot, ShotPlanResult
from app.schemas.studio.shot_plans import ShotPlanConfirmRequest
from app.services.studio import shot_plan_runner
from app.services.studio.shot_plan_runner import run_shot_plan_task
from app.services.studio.shot_plans import confirm_draft, get_draft


async def _build_maker():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine, maker


async def _seed(db: AsyncSession) -> dict[str, object]:
    project = Project(
        id="plan-project",
        workspace_id="ws-plan",
        name="都市短剧",
        description="",
        style=ProjectStyle.real_people_city,
        visual_style=ProjectVisualStyle.live_action,
    )
    chapter = Chapter(
        id="plan-chapter",
        project_id=project.id,
        index=1,
        title="第1集",
        raw_text="沈知微走进办公室。\n沈知微：你来了。\n江屿：嗯。",
    )
    group = SceneGroup(
        id="plan-group",
        project_id=project.id,
        chapter_id=chapter.id,
        index=1,
        title="办公室",
        location="办公室",
        time_of_day="夜",
        story_event="沈知微发现江屿",
    )
    scene = Scene(
        id="plan-scene",
        name="办公室",
        description="",
        style=project.style,
        visual_style=project.visual_style,
    )
    prop = Prop(
        id="plan-prop",
        name="笔记本电脑",
        description="",
        style=project.style,
        visual_style=project.visual_style,
    )
    costume = Costume(
        id="plan-costume",
        name="黑色西装",
        description="",
        style=project.style,
        visual_style=project.visual_style,
    )
    identity = AssetVersion(
        id="plan-identity",
        project_id=project.id,
        asset_type="character",
        asset_id="plan-char",
        version_no=1,
        version_kind="identity",
        variant_type="base",
        name="沈知微",
        status="active",
    )
    character = Character(
        id="plan-char",
        project_id=project.id,
        name="沈知微",
        description="职业女性",
        appearance="黑色西装",
        style=project.style,
        visual_style=project.visual_style,
        identity_version_id=identity.id,
        identity_locked_at=datetime.now(UTC),
        identity_lock_version=1,
    )
    document = ScriptDocument(
        id="plan-doc",
        project_id=project.id,
        chapter_id=chapter.id,
        doc_type="episode",
        title="第1集",
    )
    version = ScriptDocumentVersion(
        id="plan-version",
        document_id=document.id,
        version_no=1,
        file_name="第1集.docx",
        file_type="docx",
        content_hash="plan-hash",
        raw_text=chapter.raw_text,
        text_length=len(chapter.raw_text),
        status="active",
    )
    document.current_version_id = version.id
    document.active_version_id = version.id
    task = GenerationTask(
        id="plan-task",
        workspace_id=project.workspace_id,
        mode="async_polling",
        task_kind="shot_plan",
        status="pending",
        progress=0,
        payload={},
    )
    draft = ShotPlanDraft(
        id="plan-draft",
        project_id=project.id,
        chapter_id=chapter.id,
        source_script_version_id=version.id,
        target_duration=90,
        pace="standard",
        status="draft",
        task_id=task.id,
        scene_group_snapshot=[],
        coverage={},
    )
    db.add_all(
        [
            project,
            chapter,
            group,
            scene,
            prop,
            costume,
            identity,
            character,
            CharacterAlias(character_id=character.id, alias="沈总", normalized_alias="沈总"),
            document,
            version,
            task,
            draft,
            ProjectSceneLink(project_id=project.id, scene_id=scene.id),
            ProjectPropLink(project_id=project.id, prop_id=prop.id),
            ProjectCostumeLink(project_id=project.id, costume_id=costume.id),
        ]
    )
    await db.commit()
    return {
        "project": project,
        "chapter": chapter,
        "draft": draft,
        "group": group,
        "scene": scene,
        "prop": prop,
        "costume": costume,
        "character": character,
    }


def _fake_result(duration: int = 5) -> ShotPlanResult:
    return ShotPlanResult(
        shots=[
            PlannedShot(
                order=1,
                scene_group_index=1,
                title="办公室对峙",
                script_excerpt="沈知微走进办公室。",
                source_quote="沈知微走进办公室。",
                duration_seconds=duration,
                camera_shot="MS",
                angle="EYE_LEVEL",
                movement="STATIC",
                action_beats=["沈知微推门", "江屿抬头"],
                visual_description="沈知微推门进入办公室，江屿从电脑前抬头，侧逆光。",
                video_prompt_draft="中景，沈知微推门进入办公室，江屿抬头看向她，侧逆光。",
                character_names=["沈知微", "沈总"],
                scene_name="办公室",
                prop_names=["笔记本电脑"],
                costume_name="黑色西装",
                dialogues=[
                    PlannedDialogue(
                        text="你来了。", speaker_name="沈总", emotion="平静"
                    )
                ],
            )
        ]
    )


@pytest.mark.asyncio
async def test_mock_plan_runner_and_confirm_creates_shots(monkeypatch) -> None:
    engine, maker = await _build_maker()
    async with maker() as db:
        seeded = await _seed(db)

    async def _fake_build(_db, *, model_id=None, thinking=False):
        return (
            object(),
            type("M", (), {"id": "mock-text", "name": "mock-text-model"})(),
            type("P", (), {"name": "mock-provider"})(),
        )

    async def _fake_plan(self, **kwargs):
        return _fake_result()

    monkeypatch.setattr(shot_plan_runner, "async_session_maker", maker)
    monkeypatch.setattr(shot_plan_runner, "build_text_llm", _fake_build)
    monkeypatch.setattr(shot_plan_runner.SceneShotPlannerAgent, "aplan", _fake_plan)

    await run_shot_plan_task("plan-task", {"draft_id": "plan-draft"})
    async with maker() as db:
        draft = await get_draft(db, draft_id="plan-draft")
        assert draft.status == "review_required", draft.error
        assert len(draft.candidates) == 1
        candidate = draft.candidates[0]
        assert candidate.payload["characters"][0]["character_id"] == "plan-char"
        assert candidate.payload["scene"]["asset_id"] == "plan-scene"
        assert candidate.payload["dialogues"][0]["speaker_character_id"] == "plan-char"
        assert candidate.scene_group_id == "plan-group"
        assert candidate.issues == []

        from app.services.studio.shot_plans import _load_draft

        loaded = await _load_draft(db, "plan-draft")
        for item in loaded.candidates:
            item.review_status = "accepted"
        await db.flush()
        confirmed, shot_ids, reused, warnings = await confirm_draft(
            db, draft=loaded, append_to_existing=False, applied_by=1
        )
        await db.commit()
        assert reused is False
        assert len(shot_ids) == 1
        assert warnings == []
        shot = await db.get(Shot, shot_ids[0])
        assert shot is not None and shot.scene_group_id == "plan-group"
        detail = await db.get(ShotDetail, shot.id)
        assert detail is not None
        assert detail.duration == 5
        assert detail.video_prompt_draft.startswith("中景")
        assert (
            await db.execute(
                select(ShotCharacterLink).where(ShotCharacterLink.shot_id == shot.id)
            )
        ).scalars().first() is not None
        assert (
            await db.execute(
                select(ShotAssetVersion).where(ShotAssetVersion.shot_id == shot.id)
            )
        ).scalars().all()
        dialog = (
            await db.execute(
                select(ShotDialogLine).where(ShotDialogLine.shot_detail_id == shot.id)
            )
        ).scalars().first()
        assert dialog is not None and dialog.speaker_character_id == "plan-char"
        assert confirmed.status == "confirmed"

        again, same_ids, reused2, _ = await confirm_draft(
            db, draft=confirmed, append_to_existing=False, applied_by=1
        )
        assert reused2 is True
        assert same_ids == shot_ids
    await engine.dispose()


@pytest.mark.asyncio
async def test_invalid_duration_blocks_confirm(monkeypatch) -> None:
    engine, maker = await _build_maker()
    async with maker() as db:
        await _seed(db)

    async def _fake_build(_db, *, model_id=None, thinking=False):
        return object(), type("M", (), {"id": "mock", "name": "mock"})(), type("P", (), {"name": "mock"})()

    async def _fake_plan(self, **kwargs):
        return _fake_result(duration=22)

    monkeypatch.setattr(shot_plan_runner, "async_session_maker", maker)
    monkeypatch.setattr(shot_plan_runner, "build_text_llm", _fake_build)
    monkeypatch.setattr(shot_plan_runner.SceneShotPlannerAgent, "aplan", _fake_plan)
    await run_shot_plan_task("plan-task", {"draft_id": "plan-draft"})
    async with maker() as db:
        from app.services.studio.shot_plans import _load_draft

        draft = await _load_draft(db, "plan-draft")
        candidate = draft.candidates[0]
        candidate.review_status = "accepted"
        await db.flush()
        assert any(
            issue.get("code") == "duration_out_of_range" for issue in candidate.issues
        )
        with pytest.raises(ValueError, match="阻塞问题"):
            await confirm_draft(db, draft=draft, append_to_existing=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_existing_shots_require_append_and_video_not_deleted(monkeypatch) -> None:
    engine, maker = await _build_maker()
    async with maker() as db:
        seeded = await _seed(db)
        db.add(
            Shot(
                id="old-shot",
                chapter_id="plan-chapter",
                index=1,
                title="旧镜头",
                script_excerpt="旧",
                generated_video_file_id="old-video",
            )
        )
        await db.commit()

    async def _fake_build(_db, *, model_id=None, thinking=False):
        return object(), type("M", (), {"id": "mock", "name": "mock"})(), type("P", (), {"name": "mock"})()

    async def _fake_plan(self, **kwargs):
        return _fake_result()

    monkeypatch.setattr(shot_plan_runner, "async_session_maker", maker)
    monkeypatch.setattr(shot_plan_runner, "build_text_llm", _fake_build)
    monkeypatch.setattr(shot_plan_runner.SceneShotPlannerAgent, "aplan", _fake_plan)
    await run_shot_plan_task("plan-task", {"draft_id": "plan-draft"})
    async with maker() as db:
        from app.services.studio.shot_plans import _load_draft

        draft = await _load_draft(db, "plan-draft")
        for item in draft.candidates:
            item.review_status = "accepted"
        await db.flush()
        with pytest.raises(ValueError, match="追加模式"):
            await confirm_draft(db, draft=draft, append_to_existing=False)
        _, shot_ids, _, _ = await confirm_draft(
            db, draft=draft, append_to_existing=True, applied_by=1
        )
        await db.commit()
        assert len(shot_ids) == 1
        old = await db.get(Shot, "old-shot")
        assert old is not None and old.generated_video_file_id == "old-video"
    await engine.dispose()


def test_coverage_warns_when_scene_group_has_no_shot() -> None:
    """场景覆盖检查：多个正式场次时，任何一个没有镜头都必须显式提示。"""
    from app.services.studio.shot_plan_runner import _coverage

    groups = [
        SceneGroup(id="g1", project_id="p", chapter_id="c", index=1, title="办公室"),
        SceneGroup(id="g2", project_id="p", chapter_id="c", index=2, title="地下车库"),
    ]
    rows = [
        (
            {"duration": 5, "scene_group_id": "g1", "source_start_char": 0, "source_end_char": 10},
            [],
            "k1",
        )
    ]
    coverage = _coverage(
        script="x" * 20,
        rows=rows,
        target_duration=5,
        failed_chunks=[],
        groups=groups,
    )
    assert any("地下车库" in item for item in coverage["warnings"])
