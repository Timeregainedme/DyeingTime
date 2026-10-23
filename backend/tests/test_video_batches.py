"""P6 / C13：视频批量创建、并发参数与取消测试（Mock 子任务）。"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db import Base
from app.models.studio import Chapter, Project, ProjectStyle, ProjectVisualStyle, Shot, ShotDetail
from app.schemas.studio.shot_references import GenerationPreviewRead
from app.schemas.studio.video_batches import VideoBatchCreate
from app.services.studio import video_batches


async def _build():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return maker, engine


async def _seed(db: AsyncSession) -> tuple[Project, Chapter]:
    project = Project(
        id="batch-project",
        workspace_id="ws-batch",
        name="批量短剧",
        description="",
        style=ProjectStyle.real_people_city,
        visual_style=ProjectVisualStyle.live_action,
        video_concurrency=4,
    )
    chapter = Chapter(id="batch-chapter", project_id=project.id, index=1, title="第1集", raw_text="")
    shots = [
        Shot(id="batch-shot1", chapter_id=chapter.id, index=1, title="镜头一", status="ready"),
        Shot(id="batch-shot2", chapter_id=chapter.id, index=2, title="镜头二", status="ready"),
    ]
    db.add_all([project, chapter, *shots, ShotDetail(id="batch-shot1", camera_shot="MS", angle="EYE_LEVEL", movement="STATIC", duration=5), ShotDetail(id="batch-shot2", camera_shot="MS", angle="EYE_LEVEL", movement="STATIC", duration=5)])
    await db.commit()
    return project, chapter


@pytest.mark.asyncio
async def test_create_batch_stages_candidates_and_cancel(monkeypatch) -> None:
    maker, engine = await _build()
    async with maker() as db:
        project, chapter = await _seed(db)

        async def _fake_preview(_db, *, shot_id, **kwargs):
            return GenerationPreviewRead(
                shot_id=shot_id,
                manifest=[],
                images=[],
                prompt="mock h3 prompt",
                duration=5,
                ratio="9:16",
                input_hash="hash",
            )

        counter = {"n": 0}

        async def _fake_stage(_db, *, shot_id, **kwargs):
            counter["n"] += 1
            return f"batch-task-{counter['n']}", type("S", (), {"id": f"snapshot-{counter['n']}"})()

        monkeypatch.setattr(video_batches, "build_generation_preview", _fake_preview)
        monkeypatch.setattr(video_batches, "stage_video_from_preview", _fake_stage)
        monkeypatch.setattr(video_batches, "_enqueue", lambda task_id: None)

        batch = await video_batches.create_video_batch(
            db,
            chapter=chapter,
            project=project,
            body=VideoBatchCreate(
                shot_ids=["batch-shot1", "batch-shot2"],
                candidate_count=2,
                concurrency=2,
            ),
        )
        assert batch.total_count == 4
        assert batch.queued_count == 4
        assert batch.concurrency == 2
        assert len(batch.items) == 4
        assert {item.status for item in batch.items} == {"queued"}

        cancelled = await video_batches.cancel_batch(db, batch_id=batch.id, reason="test")
        assert cancelled.status == "cancelled"
        assert cancelled.cancelled_count == 4
        assert all(item.status == "cancelled" for item in cancelled.items)
    await engine.dispose()


@pytest.mark.asyncio
async def test_batch_requires_owned_shots(monkeypatch) -> None:
    maker, engine = await _build()
    async with maker() as db:
        project, chapter = await _seed(db)
        other = Chapter(id="other-chapter", project_id=project.id, index=2, title="第2集", raw_text="")
        db.add(other)
        db.add(Shot(id="other-shot", chapter_id=other.id, index=1, title="其它", status="ready"))
        await db.commit()
        with pytest.raises(ValueError, match="属于当前剧集"):
            await video_batches.create_video_batch(
                db,
                chapter=chapter,
                project=project,
                body=VideoBatchCreate(shot_ids=["other-shot"]),
            )
    await engine.dispose()


@pytest.mark.asyncio
async def test_retry_failed_creates_new_child_task(monkeypatch) -> None:
    from datetime import UTC, datetime
    from app.models.task import GenerationTask

    maker, engine = await _build()
    async with maker() as db:
        project, chapter = await _seed(db)

        async def _fake_preview(_db, *, shot_id, **kwargs):
            return GenerationPreviewRead(shot_id=shot_id, prompt="mock", duration=5, ratio="9:16")

        counter = {"n": 0}

        async def _fake_stage(_db, *, shot_id, **kwargs):
            counter["n"] += 1
            return f"retry-old-{counter['n']}", type("S", (), {"id": f"snap-{counter['n']}"})()

        monkeypatch.setattr(video_batches, "build_generation_preview", _fake_preview)
        monkeypatch.setattr(video_batches, "stage_video_from_preview", _fake_stage)
        monkeypatch.setattr(video_batches, "_enqueue", lambda task_id: None)
        batch = await video_batches.create_video_batch(
            db,
            chapter=chapter,
            project=project,
            body=VideoBatchCreate(shot_ids=["batch-shot1"], concurrency=1),
        )
        item = batch.items[0]
        old_task_id = item.task_id
        old_task = GenerationTask(
            id=item.task_id,
            workspace_id="ws-batch",
            mode="async_polling",
            task_kind="video_generation",
            status="failed",
            progress=0,
            error="mock failed",
            payload={"run_args": {"shot_id": "batch-shot1", "input": {"prompt": "p", "seconds": 5, "ratio": "9:16"}}},
            created_at=datetime.now(UTC),
        )
        db.add(old_task)
        item.status = "failed"
        item.error = "mock failed"
        batch.status = "partial_success"
        await db.commit()
        retried = await video_batches.retry_failed(db, batch_id=batch.id)
        retried_item = retried.items[0]
        assert retried_item.status == "queued"
        assert retried_item.task_id != old_task_id
        assert retried_item.enqueued_at is None
    await engine.dispose()
