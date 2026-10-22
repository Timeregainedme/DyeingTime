"""P2 / C4：项目风格选择、锁定与快照测试。"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.bootstrap import bootstrap_all_registries
from app.core.db import Base
from app.models.studio import (
    FileItem,
    Project,
    ProjectStyle,
    ProjectStyleOption,
    ProjectStyleSnapshot,
    ProjectVisualStyle,
)
from app.models.types import FileType
from app.services.studio.project_style import (
    get_project_style_state,
    lock_project_style,
    select_project_style,
)
from app.services.studio.style_catalog import (
    build_prompt_pack_from_profile,
    resolve_style_motif,
    update_style_option,
)


@pytest.fixture(autouse=True)
def _bootstrap() -> None:
    bootstrap_all_registries()


async def _build_session() -> tuple[AsyncSession, object]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_local = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return session_local(), engine


async def _seed(db: AsyncSession) -> None:
    db.add_all(
        [
            Project(
                workspace_id="ws-test",
                id="p1",
                name="项目一",
                description="",
                style="真人都市",
                visual_style=ProjectVisualStyle.live_action,
            ),
            ProjectStyleOption(
                id="style-a",
                visual_style="现实",
                name="真人都市",
                description="都市实拍",
                prompt_pack="旧提示词包",
                structured_profile={
                    "medium": "实拍",
                    "texture": "真实皮肤",
                    "color": "低饱和",
                    "lighting": "自然光",
                    "material": "棉麻",
                    "character_rendering": "真实骨相",
                    "scene_rendering": "生活痕迹",
                    "camera": "35mm",
                    "keep": "真实肤色",
                    "avoid": "塑料感",
                },
                reference_file_ids=[],
                sample_file_ids=[],
                analysis_status="analyzed",
            ),
            ProjectStyleOption(
                id="style-b",
                visual_style="动漫",
                name="2D 动画",
                description="二维动画",
                prompt_pack="",
                structured_profile=None,
                reference_file_ids=[],
                sample_file_ids=[],
                analysis_status="draft",
            ),
            FileItem(
                id="file-sample",
                type=FileType.image,
                name="sample.png",
                thumbnail="",
                tags=[],
                storage_key="styles/sample.png",
            ),
            FileItem(
                id="file-audio",
                type=FileType.audio,
                name="sample.wav",
                thumbnail="",
                tags=[],
                storage_key="styles/sample.wav",
            ),
        ]
    )
    await db.commit()


async def test_select_then_lock_creates_snapshot_and_blocks_switch() -> None:
    db, engine = await _build_session()
    async with db:
        await _seed(db)
        project = await db.get(Project, "p1")
        assert project is not None

        state = await select_project_style(db, project=project, style_id="style-b")
        assert state.locked is False
        assert state.style is not None
        assert state.style.name == "2D 动画"
        assert project.style == "2D 动画"

        locked = await lock_project_style(
            db, project=project, style_id="style-b", sample_file_ids=["file-sample"]
        )
        assert locked.locked is True
        assert locked.snapshot is not None
        assert locked.snapshot.style_name == "2D 动画"
        assert locked.snapshot.sample_file_ids == ["file-sample"]
        # 目录里 prompt_pack 为空 → 锁定快照必须落内置兜底，而不是空串
        assert locked.snapshot.prompt_pack
        assert "动画" in locked.snapshot.prompt_pack or "赛璐璐" in locked.snapshot.prompt_pack

        with pytest.raises(ValueError):
            await select_project_style(db, project=project, style_id="style-a")
        with pytest.raises(ValueError):
            await lock_project_style(db, project=project, style_id="style-a")
    await engine.dispose()


async def test_snapshot_survives_catalog_edit_and_delete() -> None:
    db, engine = await _build_session()
    async with db:
        await _seed(db)
        project = await db.get(Project, "p1")
        assert project is not None
        await lock_project_style(db, project=project, style_id="style-a")
        snapshot = await db.get(ProjectStyleSnapshot, "p1")
        assert snapshot is not None
        assert snapshot.prompt_pack == "旧提示词包"

        # 改全局目录：快照不变
        await update_style_option(db, style_id="style-a", prompt_pack="新提示词包")
        await db.commit()
        await db.refresh(snapshot)
        assert snapshot.prompt_pack == "旧提示词包"

        # 生成链路读项目快照优先
        motif = await resolve_style_motif(db, style="真人都市", project_id="p1")
        assert motif == "旧提示词包"

        # 删除目录项：快照仍保留（source_style_id 可为空）
        catalog = await db.get(ProjectStyleOption, "style-a")
        assert catalog is not None
        await db.delete(catalog)
        await db.commit()
        await db.refresh(snapshot)
        assert snapshot.style_name == "真人都市"
        assert snapshot.prompt_pack == "旧提示词包"
    await engine.dispose()


async def test_lock_rejects_invalid_sample_files() -> None:
    db, engine = await _build_session()
    async with db:
        await _seed(db)
        project = await db.get(Project, "p1")
        assert project is not None

        with pytest.raises(ValueError):
            await lock_project_style(
                db, project=project, style_id="style-a", sample_file_ids=["file-audio"]
            )
        with pytest.raises(ValueError):
            await lock_project_style(
                db,
                project=project,
                style_id="style-a",
                sample_file_ids=["f1", "f2", "f3", "f4"],
            )
    await engine.dispose()


async def test_state_shape_and_prompt_pack_builder() -> None:
    db, engine = await _build_session()
    async with db:
        await _seed(db)
        project = await db.get(Project, "p1")
        assert project is not None

        state = await get_project_style_state(db, project=project)
        assert state.locked is False
        assert state.style is not None
        assert state.style.id == "style-a"
        assert {item.name for item in state.styles} == {"真人都市", "2D 动画"}
        assert "现实" in state.visual_styles

        prompt = build_prompt_pack_from_profile(
            {
                "medium": "实拍",
                "texture": "真实皮肤",
                "color": "低饱和",
                "lighting": "自然光",
                "material": "棉麻",
                "character_rendering": "",
                "scene_rendering": "",
                "camera": "35mm",
                "keep": "真实肤色",
                "avoid": "塑料感",
            }
        )
        assert "视觉媒介：实拍" in prompt
        assert "避免：塑料感" in prompt
        assert "人物渲染" not in prompt
    await engine.dispose()
