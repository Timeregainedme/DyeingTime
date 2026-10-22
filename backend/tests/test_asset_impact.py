"""P4 / C8：资产引用与受影响镜头分析测试。"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import pytest

from app.core.db import Base
from app.models.studio import (
    AssetVersion,
    Chapter,
    Character,
    Project,
    ProjectPropLink,
    ProjectSceneLink,
    ProjectStyle,
    ProjectVisualStyle,
    Prop,
    Scene,
    Shot,
    ShotCharacterLink,
)
from app.services.studio.asset_impact import (
    analyze_asset_impact,
    list_impact_refs,
    record_version_impact,
)


async def _build_session() -> tuple[AsyncSession, object]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return maker(), engine


async def _seed(db: AsyncSession) -> tuple[Project, Character, Scene, Prop]:
    project = Project(
        id="impact-project",
        workspace_id="ws-impact",
        name="都市短剧",
        description="",
        style=ProjectStyle.real_people_city,
        visual_style=ProjectVisualStyle.live_action,
    )
    character = Character(
        id="impact-char",
        project_id=project.id,
        name="沈知微",
        description="",
        style=project.style,
        visual_style=project.visual_style,
    )
    scene = Scene(
        id="impact-scene",
        name="办公室",
        description="",
        style=project.style,
        visual_style=project.visual_style,
    )
    prop = Prop(
        id="impact-prop",
        name="笔记本",
        description="",
        style=project.style,
        visual_style=project.visual_style,
    )
    chapters = [
        Chapter(
            id="impact-ch1",
            project_id=project.id,
            index=1,
            title="第1集",
            raw_text="沈知微走进办公室。",
        ),
        Chapter(
            id="impact-ch2",
            project_id=project.id,
            index=2,
            title="第2集",
            raw_text="办公室夜景。",
        ),
        Chapter(
            id="impact-ch3",
            project_id=project.id,
            index=3,
            title="第3集",
            raw_text="沈总只被提及。",
        ),
    ]
    shots = [
        Shot(
            id="impact-shot1",
            chapter_id="impact-ch1",
            index=1,
            title="开场",
            generated_video_file_id="video-1",
        ),
        Shot(id="impact-shot2", chapter_id="impact-ch2", index=1, title="夜景"),
        Shot(id="impact-shot3", chapter_id="impact-ch3", index=1, title="提及"),
    ]
    db.add_all(
        [
            project,
            character,
            scene,
            prop,
            *chapters,
            *shots,
            ShotCharacterLink(shot_id="impact-shot1", character_id=character.id, index=0),
            ProjectSceneLink(
                project_id=project.id,
                chapter_id="impact-ch2",
                scene_id=scene.id,
            ),
            ProjectPropLink(
                project_id=project.id,
                shot_id="impact-shot2",
                prop_id=prop.id,
            ),
        ]
    )
    await db.commit()
    return project, character, scene, prop


@pytest.mark.asyncio
async def test_character_impact_separates_explicit_from_possible() -> None:
    db, engine = await _build_session()
    async with db:
        project, character, _scene, _prop = await _seed(db)
        from app.services.studio.character_aliases import add_alias

        await add_alias(db, character=character, alias="沈总")
        result = await analyze_asset_impact(
            db,
            project_id=project.id,
            asset_type="character",
            asset_id=character.id,
        )
        by_shot = {item.shot_id: item for item in result.shots}
        assert by_shot["impact-shot1"].certainty == "explicit"
        assert by_shot["impact-shot1"].has_video is True
        assert by_shot["impact-shot3"].certainty == "possible"
        assert by_shot["impact-shot3"].reference_kind == "script_text_mention"
        assert result.summary["explicit_count"] == 1
        assert result.summary["possible_count"] >= 1
        assert result.summary["version_reference_established"] is False
        shot = await db.get(Shot, "impact-shot1")
        assert shot is not None and shot.generated_video_file_id == "video-1"
    await engine.dispose()


@pytest.mark.asyncio
async def test_scene_chapter_link_is_possible_and_shot_link_explicit() -> None:
    db, engine = await _build_session()
    async with db:
        project, _character, scene, _prop = await _seed(db)
        # ch2 是章节级关联，shot2 从未直接引用场景；只能标 possible。
        result = await analyze_asset_impact(
            db, project_id=project.id, asset_type="scene", asset_id=scene.id
        )
        by_shot = {item.shot_id: item for item in result.shots}
        assert by_shot["impact-shot2"].certainty == "possible"
        assert by_shot["impact-shot2"].reference_kind in {"chapter_asset_link", "chapter_asset_link+script_text_mention"}
    await engine.dispose()


@pytest.mark.asyncio
async def test_version_impact_history_is_idempotent() -> None:
    db, engine = await _build_session()
    async with db:
        project, character, _scene, _prop = await _seed(db)
        old = AssetVersion(
            id="version-old",
            project_id=project.id,
            asset_type="character",
            asset_id=character.id,
            version_no=1,
            version_kind="identity",
            variant_type="base",
            name="旧身份",
            status="active",
        )
        new = AssetVersion(
            id="version-new",
            project_id=project.id,
            asset_type="character",
            asset_id=character.id,
            version_no=2,
            version_kind="identity",
            variant_type="base",
            name="新身份",
            status="active",
        )
        db.add_all([old, new])
        await db.commit()

        first = await record_version_impact(
            db,
            project_id=project.id,
            asset_type="character",
            asset_id=character.id,
            from_version_id=old.id,
            to_version_id=new.id,
            created_by=1,
        )
        second = await record_version_impact(
            db,
            project_id=project.id,
            asset_type="character",
            asset_id=character.id,
            from_version_id=old.id,
            to_version_id=new.id,
            created_by=1,
        )
        assert first
        assert second == []
        history = await list_impact_refs(
            db, project_id=project.id, asset_type="character", asset_id=character.id
        )
        assert len(history) == len(first)
        assert all(item.shot_id for item in history)
    await engine.dispose()


@pytest.mark.asyncio
async def test_impact_rejects_cross_project_asset() -> None:
    db, engine = await _build_session()
    async with db:
        _project, character, _scene, _prop = await _seed(db)
        other = Project(
            id="other-project",
            workspace_id="ws-impact",
            name="其它",
            description="",
            style=ProjectStyle.real_people_city,
            visual_style=ProjectVisualStyle.live_action,
        )
        db.add(other)
        await db.commit()
        with pytest.raises(ValueError, match="不属于当前项目"):
            await analyze_asset_impact(
                db,
                project_id=other.id,
                asset_type="character",
                asset_id=character.id,
            )
    await engine.dispose()
