"""P2 / C3：项目生成配置与模型快照服务测试。"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db import Base
from app.bootstrap import bootstrap_all_registries
from app.models.llm import Model, ModelCategoryKey, ModelSettings, Provider, ProviderStatus
from app.models.studio import Project, ProjectStyle, ProjectVisualStyle
from app.schemas.studio.project_generation import ProjectGenerationConfigUpdate
from app.services.studio.project_generation_config import (
    BUSINESS_DURATION_MAX,
    BUSINESS_DURATION_MIN,
    DEFAULT_CONCURRENCY,
    get_project_generation_config,
    resolve_project_model,
    save_project_generation_config,
)


@pytest.fixture(autouse=True)
def _bootstrap_registries() -> None:
    """能力注册表是导入即注册的；测试进程未经过 app lifespan，需要显式引导。"""
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
            Provider(
                id="prov-pix",
                name="PIX",
                base_url="https://pix.example",
                api_key="pix-secret-key",
                status=ProviderStatus.active,
            ),
            Provider(
                id="prov-compshare",
                name="优云智算 模型 API",
                base_url="https://cp.example",
                api_key="compshare-secret-key",
                status=ProviderStatus.active,
            ),
            Model(
                id="m-image",
                name="gpt-image-2.5-flare",
                category=ModelCategoryKey.image,
                provider_id="prov-pix",
            ),
            Model(
                id="m-video",
                name="MiniMax-H3",
                category=ModelCategoryKey.video,
                provider_id="prov-compshare",
            ),
            Model(
                id="m-video-backup",
                name="minimax-h3",
                category=ModelCategoryKey.video,
                provider_id="prov-pix",
            ),
            Model(
                id="m-audio",
                name="IndexTTS-2.5",
                category=ModelCategoryKey.audio,
                provider_id="prov-compshare",
            ),
            ModelSettings(
                id=1,
                default_image_model_id="m-image",
                default_video_model_id="m-video",
                default_audio_model_id="m-audio",
            ),
            Project(
                workspace_id="ws-test",
                id="p1",
                name="项目一",
                description="",
                style=ProjectStyle.real_people_city,
                visual_style=ProjectVisualStyle.live_action,
            ),
        ]
    )
    await db.commit()


@pytest.mark.asyncio
async def test_new_project_defaults_follow_p2_policy() -> None:
    db, engine = await _build_session()
    async with db:
        await _seed(db)
        project = await db.get(Project, "p1")
        assert project is not None
        await db.refresh(project)
        assert project.video_concurrency == DEFAULT_CONCURRENCY == 4
        assert project.use_dialog_audio_as_reference is False
        assert project.default_shot_duration == 5
        assert project.video_duration_min == BUSINESS_DURATION_MIN == 4
        assert project.video_duration_max == BUSINESS_DURATION_MAX == 15
        assert project.default_reference_mode == "reference"
        assert project.generation_config_confirmed_at is None
    await engine.dispose()


@pytest.mark.asyncio
async def test_config_falls_back_to_global_defaults_before_confirmation() -> None:
    db, engine = await _build_session()
    async with db:
        await _seed(db)
        project = await db.get(Project, "p1")
        assert project is not None
        config = await get_project_generation_config(db, project=project)

        assert config.confirmed is False
        assert config.initialized is False
        assert config.image_model.source == "global"
        assert config.video_model.source == "global"
        assert config.audio_model.source == "global"
        assert config.video_model.model_name == "MiniMax-H3"
        assert config.output.video_ratio in config.output.video_ratios
        assert config.policy.duration_min >= 4
        assert config.policy.duration_max <= 15
        assert config.policy.video_concurrency == 4
        assert config.policy.use_dialog_audio_as_reference is False
    await engine.dispose()


@pytest.mark.asyncio
async def test_confirm_writes_snapshot_without_credentials() -> None:
    db, engine = await _build_session()
    async with db:
        await _seed(db)
        project = await db.get(Project, "p1")
        assert project is not None

        config = await save_project_generation_config(
            db,
            project=project,
            body=ProjectGenerationConfigUpdate(confirm=True),
        )
        assert config.confirmed is True
        # 风格锁定是独立的初始化步骤；本用例只确认配置本身。
        assert config.initialized is False
        assert config.version == 1
        assert config.snapshot is not None

        serialized = str(config.snapshot)
        assert "pix-secret-key" not in serialized
        assert "compshare-secret-key" not in serialized
        assert "api_key" not in serialized
        assert "base_url" not in serialized
    await engine.dispose()


@pytest.mark.asyncio
async def test_project_model_wins_over_global_after_confirmation() -> None:
    db, engine = await _build_session()
    async with db:
        await _seed(db)
        project = await db.get(Project, "p1")
        assert project is not None

        await save_project_generation_config(
            db,
            project=project,
            body=ProjectGenerationConfigUpdate(
                default_video_model_id="m-video-backup",
                confirm=True,
            ),
        )
        # 全局默认改成另一个模型，项目仍应使用自己的快照。
        settings = await db.get(ModelSettings, 1)
        assert settings is not None
        settings.default_video_model_id = "m-video"
        await db.commit()

        config = await get_project_generation_config(db, project=project)
        assert config.video_model.source == "project"
        assert config.video_model.model_id == "m-video-backup"

        resolved = await resolve_project_model(
            db, project_id="p1", category=ModelCategoryKey.video
        )
        assert resolved is not None
        assert resolved.id == "m-video-backup"
    await engine.dispose()


@pytest.mark.asyncio
async def test_confirm_rejects_invalid_duration_ratio_and_concurrency() -> None:
    db, engine = await _build_session()
    async with db:
        await _seed(db)
        project = await db.get(Project, "p1")
        assert project is not None

        with pytest.raises(ValueError):
            await save_project_generation_config(
                db,
                project=project,
                body=ProjectGenerationConfigUpdate(default_shot_duration=20, confirm=True),
            )
        with pytest.raises(ValueError):
            await save_project_generation_config(
                db,
                project=project,
                body=ProjectGenerationConfigUpdate(default_video_ratio="5:4", confirm=True),
            )
        with pytest.raises(ValueError):
            await save_project_generation_config(
                db,
                project=project,
                body=ProjectGenerationConfigUpdate(video_concurrency=17, confirm=True),
            )
        # 业务范围不允许擅自扩大到供应商 15 秒以上。
        with pytest.raises(ValueError):
            await save_project_generation_config(
                db,
                project=project,
                body=ProjectGenerationConfigUpdate(
                    video_duration_max=30, confirm=True
                ),
            )
    await engine.dispose()


@pytest.mark.asyncio
async def test_draft_can_be_saved_with_incomplete_config() -> None:
    db, engine = await _build_session()
    async with db:
        await _seed(db)
        project = await db.get(Project, "p1")
        assert project is not None

        # 清空项目覆盖 + 全局默认也不可用时，草稿仍可保存，确认则必须失败。
        settings = await db.get(ModelSettings, 1)
        assert settings is not None
        settings.default_audio_model_id = None
        await db.commit()

        draft = await save_project_generation_config(
            db,
            project=project,
            body=ProjectGenerationConfigUpdate(default_shot_duration=7, confirm=False),
        )
        assert draft.confirmed is False
        assert draft.policy.default_shot_duration == 7
        assert any(not check.ok for check in draft.checks)

        with pytest.raises(ValueError):
            await save_project_generation_config(
                db,
                project=project,
                body=ProjectGenerationConfigUpdate(confirm=True),
            )
    await engine.dispose()
