"""P5 / C9：正式场次、排序、镜头移动与 P3 场次建议导入测试。"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db import Base
from app.models.studio import (
    Chapter,
    Project,
    ProjectStyle,
    ProjectVisualStyle,
    Scene,
    SceneGroup,
    ScriptDocument,
    ScriptDocumentVersion,
    ScriptParseRun,
    Shot,
    ShotDetail,
)
from app.schemas.studio.scene_groups import (
    SceneGroupCreate,
    SceneGroupImportRequest,
    SceneGroupUpdate,
    ShotOrderItem,
)
from app.services.studio.scene_groups import (
    create_group,
    delete_group,
    get_scene_group_suggestions,
    import_scene_group_suggestions,
    list_groups,
    reorder_chapter_shots,
    reorder_groups,
    update_group,
)
from app.services.studio.shots import create as create_shot

PROJECT = "p5-project"
CHAPTER = "p5-chapter"


async def _build_session() -> tuple[AsyncSession, object]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return maker(), engine


async def _seed(db: AsyncSession) -> tuple[Project, Chapter]:
    project = Project(
        id=PROJECT,
        workspace_id="ws-p5",
        name="都市短剧",
        description="",
        style=ProjectStyle.real_people_city,
        visual_style=ProjectVisualStyle.live_action,
    )
    chapter = Chapter(
        id=CHAPTER,
        project_id=PROJECT,
        index=1,
        title="第1集",
        raw_text="办公室夜归。",
    )
    db.add_all([project, chapter])
    await db.commit()
    return project, chapter


async def _add_shot(db: AsyncSession, shot_id: str, index: int, group_id: str | None = None) -> Shot:
    from app.schemas.studio.shots import ShotCreate

    shot = await create_shot(
        db,
        body=ShotCreate(
            id=shot_id,
            chapter_id=CHAPTER,
            scene_group_id=group_id,
            index=index,
            title=f"镜头{index}",
            script_excerpt=f"镜头{index}",
        ),
    )
    await db.commit()
    return shot


@pytest.mark.asyncio
async def test_scene_group_crud_reorder_and_move_shots() -> None:
    db, engine = await _build_session()
    async with db:
        await _seed(db)
        first = await create_group(
            db, chapter_id=CHAPTER, body=SceneGroupCreate(title="办公室·白天", location="办公室")
        )
        second = await create_group(
            db, chapter_id=CHAPTER, body=SceneGroupCreate(title="走廊·傍晚", location="走廊")
        )
        assert first.index == 1 and second.index == 2
        updated = await update_group(
            db,
            group_id=second.id,
            body=SceneGroupUpdate(title="办公室·夜晚", time_of_day="夜"),
        )
        assert updated.title == "办公室·夜晚"
        groups = await reorder_groups(
            db, chapter_id=CHAPTER, group_ids=[second.id, first.id]
        )
        assert [item.id for item in groups] == [second.id, first.id]

        shot1 = await _add_shot(db, "p5-shot1", 1, first.id)
        shot2 = await _add_shot(db, "p5-shot2", 2, first.id)
        shot3 = await _add_shot(db, "p5-shot3", 3, None)
        moved = await reorder_chapter_shots(
            db,
            chapter_id=CHAPTER,
            items=[
                ShotOrderItem(shot_id=shot1.id, scene_group_id=first.id),
                ShotOrderItem(shot_id=shot3.id, scene_group_id=second.id),
                ShotOrderItem(shot_id=shot2.id, scene_group_id=second.id),
            ],
        )
        assert [item.id for item in moved] == [shot1.id, shot3.id, shot2.id]
        assert [item.index for item in moved] == [1, 2, 3]
        assert moved[1].scene_group_id == second.id

        with pytest.raises(ValueError, match="仍有镜头"):
            await delete_group(db, group_id=first.id)
        # second 现在含两个镜头，同样应拒绝。
        with pytest.raises(ValueError, match="仍有镜头"):
            await delete_group(db, group_id=second.id)
    await engine.dispose()


@pytest.mark.asyncio
async def test_empty_group_delete_and_unassigned_history_compatible() -> None:
    db, engine = await _build_session()
    async with db:
        await _seed(db)
        group = await create_group(
            db, chapter_id=CHAPTER, body=SceneGroupCreate(title="空场次")
        )
        # 存量镜头没有 scene_group_id 仍可读取。
        old_shot = await _add_shot(db, "old-shot", 1, None)
        assert old_shot.scene_group_id is None
        await delete_group(db, group_id=group.id)
        assert (
            await db.execute(select(SceneGroup).where(SceneGroup.id == group.id))
        ).scalar_one_or_none() is None
    await engine.dispose()


@pytest.mark.asyncio
async def test_p3_scene_beats_import_is_idempotent_and_preserves_manual_group() -> None:
    db, engine = await _build_session()
    async with db:
        project, _chapter = await _seed(db)
        scene = Scene(
            id="p5-scene-office",
            name="办公室",
            description="",
            style=project.style,
            visual_style=project.visual_style,
        )
        db.add(scene)
        from app.models.studio import ProjectSceneLink

        db.add(ProjectSceneLink(project_id=PROJECT, scene_id=scene.id))
        document = ScriptDocument(
            id="p5-doc",
            project_id=PROJECT,
            chapter_id=CHAPTER,
            doc_type="episode",
            title="第1集剧本",
        )
        version = ScriptDocumentVersion(
            id="p5-version",
            document_id=document.id,
            version_no=1,
            file_name="第1集.docx",
            file_type="docx",
            content_hash="p5-hash",
            raw_text="办公室夜归。",
            text_length=8,
            status="active",
        )
        document.current_version_id = version.id
        document.active_version_id = version.id
        run = ScriptParseRun(
            id="p5-run",
            document_id=document.id,
            version_id=version.id,
            status="confirmed",
            progress=100,
            confirmed_result={
                "episode": {
                    "scene_beats": [
                        {
                            "index": 1,
                            "title": "办公室夜归",
                            "location": "办公室",
                            "time_of_day": "夜",
                            "events": ["江屿修复系统"],
                        }
                    ]
                }
            },
        )
        db.add_all([document, version, run])
        await db.commit()

        suggestions = await get_scene_group_suggestions(db, chapter_id=CHAPTER)
        assert suggestions.parse_run_id == run.id
        assert suggestions.items[0].primary_scene_id == scene.id
        assert suggestions.items[0].title == "办公室夜归"

        imported = await import_scene_group_suggestions(
            db, chapter_id=CHAPTER, parse_run_id=run.id, items=None
        )
        assert len(imported.created) == 1
        assert imported.created[0].primary_scene_id == scene.id
        again = await import_scene_group_suggestions(
            db, chapter_id=CHAPTER, parse_run_id=run.id, items=None
        )
        assert again.created == []
        assert again.skipped == 1

        # 人工修改已导入场次，再次导入不覆盖。
        await update_group(
            db,
            group_id=imported.created[0].id,
            body=SceneGroupUpdate(title="人工修订场次"),
        )
        await import_scene_group_suggestions(
            db,
            chapter_id=CHAPTER,
            parse_run_id=run.id,
            items=None,
        )
        groups = await list_groups(db, chapter_id=CHAPTER)
        assert groups[0].title == "人工修订场次"
    await engine.dispose()
