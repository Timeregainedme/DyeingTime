"""P6 / C14：视频候选审核、显式采纳与历史保护测试。"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db import Base
from app.models.studio import FileItem, Shot
from app.models.task import GenerationTask
from app.models.task_links import GenerationTaskLink
from app.services.studio.shot_video_versions import (
    adopt_shot_video_version_by_task,
    list_shot_video_versions,
    review_shot_video_version,
)


async def _build():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return maker, engine


async def _seed(db: AsyncSession) -> None:
    shot = Shot(id="video-shot", chapter_id="video-chapter", index=1, title="镜头")
    # Shot has chapter FK; SQLite fk off, but create a chapter for completeness.
    from app.models.studio import Chapter, Project, ProjectStyle, ProjectVisualStyle

    project = Project(
        id="video-project",
        workspace_id="ws-video",
        name="视频",
        description="",
        style=ProjectStyle.real_people_city,
        visual_style=ProjectVisualStyle.live_action,
    )
    chapter = Chapter(id="video-chapter", project_id=project.id, index=1, title="第1集", raw_text="")
    db.add_all([project, chapter, shot])
    task1 = GenerationTask(
        id="video-task1",
        workspace_id="ws-video",
        mode="async_polling",
        task_kind="video_generation",
        status="succeeded",
        progress=100,
        payload={"run_args": {"input": {"prompt": "p1", "seconds": 5, "ratio": "9:16"}}},
        created_at=datetime.now(UTC),
    )
    task2 = GenerationTask(
        id="video-task2",
        workspace_id="ws-video",
        mode="async_polling",
        task_kind="video_generation",
        status="succeeded",
        progress=100,
        payload={"run_args": {"input": {"prompt": "p2", "seconds": 5, "ratio": "9:16"}}},
        created_at=datetime.now(UTC),
    )
    db.add_all(
        [
            task1,
            task2,
            FileItem(id="video-file1", type="video", name="v1", thumbnail="https://mock/v1.mp4", tags=[], storage_key="v1"),
            FileItem(id="video-file2", type="video", name="v2", thumbnail="https://mock/v2.mp4", tags=[], storage_key="v2"),
            GenerationTaskLink(task_id="video-task1", resource_type="video", relation_type="video", relation_entity_id="video-shot", file_id="video-file1"),
            GenerationTaskLink(task_id="video-task2", resource_type="video", relation_type="video", relation_entity_id="video-shot", file_id="video-file2"),
        ]
    )
    shot.generated_video_file_id = "video-file1"
    await db.commit()


@pytest.mark.asyncio
async def test_review_and_explicit_adoption_never_auto_overwrites() -> None:
    maker, engine = await _build()
    async with maker() as db:
        await _seed(db)
        versions = await list_shot_video_versions(db, shot_id="video-shot")
        assert len(versions) == 2
        assert {item.file_id for item in versions} == {"video-file1", "video-file2"}
        current = next(item for item in versions if item.is_current)
        assert current.file_id == "video-file1"

        review = await review_shot_video_version(
            db,
            shot_id="video-shot",
            task_id="video-task2",
            review_status="unsatisfied",
            issue_tags=["人物脸部漂移", "动作错误"],
            note="脸部不一致",
            reviewed_by=1,
        )
        assert review.review_status == "unsatisfied"
        await db.commit()
        versions = await list_shot_video_versions(db, shot_id="video-shot")
        reviewed = next(item for item in versions if item.task_id == "video-task2")
        assert reviewed.review_status == "unsatisfied"
        assert "人物脸部漂移" in reviewed.issue_tags
        assert reviewed.note == "脸部不一致"
        assert reviewed.file_url == "https://mock/v2.mp4"

        # 后续任务完成不自动替换 V1。
        shot = await db.get(Shot, "video-shot")
        assert shot is not None and shot.generated_video_file_id == "video-file1"

        await adopt_shot_video_version_by_task(
            db, shot_id="video-shot", task_id="video-task2"
        )
        await db.commit()
        shot = await db.get(Shot, "video-shot")
        assert shot is not None and shot.generated_video_file_id == "video-file2"

        # 切回旧版本，旧文件仍保留。
        await adopt_shot_video_version_by_task(
            db, shot_id="video-shot", task_id="video-task1"
        )
        await db.commit()
        shot = await db.get(Shot, "video-shot")
        assert shot is not None and shot.generated_video_file_id == "video-file1"
        files = (await db.execute(select(FileItem))).scalars().all()
        assert len(files) == 2
    await engine.dispose()
