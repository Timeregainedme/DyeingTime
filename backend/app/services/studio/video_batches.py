"""P6 / C13：批量视频任务创建与并发协调。"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import async_session_maker
from app.core.task_manager import DeliveryMode, SqlAlchemyTaskStore, TaskManager
from app.core.task_manager.types import TaskStatus
from app.models.studio import (
    Chapter,
    Project,
    Shot,
    ShotDetail,
    VideoGenerationBatch,
    VideoGenerationBatchItem,
)
from app.models.task import GenerationTask, GenerationTaskStatus
from app.models.task_links import GenerationTaskLink
from app.schemas.studio.shot_references import P6VideoGenerateRequest
from app.schemas.studio.shot_plans import ShotPlanStatsRead
from app.schemas.studio.video_batches import VideoBatchCreate
from app.services.studio.shot_references import (
    build_generation_preview,
    stage_video_from_preview,
)

BATCH_TASK_KIND = "video_batch"
BATCH_RELATION_TYPE = "video_batch"
ACTIVE_ITEM_STATUSES = {"queued", "running"}


def _enqueue(task_id: str) -> None:
    """延迟导入 Celery 入口，避免 task_registry 初始化时的循环导入。"""
    from app.tasks.execute_task import enqueue_task_execution

    enqueue_task_execution(task_id)


class _CreateOnlyTask:
    async def run(self, *args: object, **kwargs: object):
        return None

    async def status(self) -> dict[str, object]:
        return {}

    async def is_done(self) -> bool:
        return False

    async def get_result(self) -> object:
        return None


async def _load_batch(db: AsyncSession, batch_id: str) -> VideoGenerationBatch:
    batch = await db.scalar(
        select(VideoGenerationBatch)
        .options(selectinload(VideoGenerationBatch.items))
        .where(VideoGenerationBatch.id == batch_id)
        .execution_options(populate_existing=True)
    )
    if batch is None:
        raise ValueError(f"批量任务不存在：{batch_id}")
    return batch


def _counts(batch: VideoGenerationBatch) -> None:
    counts = {key: 0 for key in ("queued", "running", "succeeded", "failed", "cancelled")}
    for item in batch.items:
        if item.status in counts:
            counts[item.status] += 1
    batch.total_count = len(batch.items)
    batch.queued_count = counts["queued"]
    batch.running_count = counts["running"]
    batch.succeeded_count = counts["succeeded"]
    batch.failed_count = counts["failed"]
    batch.cancelled_count = counts["cancelled"]


async def create_video_batch(
    db: AsyncSession,
    *,
    chapter: Chapter,
    project: Project,
    body: VideoBatchCreate,
    requested_by: int | None = None,
) -> VideoGenerationBatch:
    """创建批次并 staging 子任务；实际排队由 batch coordinator 控制并发。"""
    shots = (
        await db.execute(
            select(Shot).where(
                Shot.id.in_(body.shot_ids), Shot.chapter_id == chapter.id
            )
        )
    ).scalars().all()
    if len(shots) != len(set(body.shot_ids)):
        raise ValueError("批量镜头必须全部属于当前剧集")
    if body.scene_group_id:
        shots = [item for item in shots if item.scene_group_id == body.scene_group_id]
        if not shots:
            raise ValueError("所选场次没有可生成的镜头")

    from app.services.studio.shot_plans import get_stats

    stats: ShotPlanStatsRead = await get_stats(db, chapter_id=chapter.id)
    coverage = {
        "shot_count": stats.shot_count,
        "total_duration": stats.total_duration,
        "coverage_ratio": stats.coverage_ratio,
        "blocking_issue_count": stats.blocking_issue_count,
        "warning_count": stats.warning_count,
    }
    if stats.coverage_ratio and stats.coverage_ratio < 0.6 and not body.allow_low_coverage:
        raise ValueError(
            f"分镜覆盖率仅 {round(stats.coverage_ratio * 100)}%，请先在剧集页检查未覆盖剧情，"
            "或显式确认低覆盖风险后继续"
        )

    concurrency = min(
        max(1, body.concurrency or project.video_concurrency or 4), 8
    )
    batch = VideoGenerationBatch(
        id=str(uuid.uuid4()),
        project_id=project.id,
        chapter_id=chapter.id,
        scene_group_id=body.scene_group_id,
        requested_by=requested_by,
        status="queued",
        candidate_count=body.candidate_count,
        concurrency=concurrency,
        coverage_snapshot=coverage,
        queued_count=0,
        total_count=0,
    )
    db.add(batch)
    await db.flush()

    for shot in shots:
        detail = await db.get(ShotDetail, shot.id)
        preview = await build_generation_preview(
            db,
            shot_id=shot.id,
            natural_prompt=(detail.video_prompt_draft if detail else "") or "",
            reference_mode="reference",
        )
        if preview.blocking_errors:
            raise ValueError(f"镜头 {shot.id} 准备失败：" + "；".join(preview.blocking_errors))
        for candidate_index in range(1, body.candidate_count + 1):
            task_id, _snapshot = await stage_video_from_preview(
                db,
                shot_id=shot.id,
                preview=preview,
                auto_adopt=False,
                created_by=requested_by,
            )
            db.add(
                VideoGenerationBatchItem(
                    batch_id=batch.id,
                    shot_id=shot.id,
                    candidate_index=candidate_index,
                    task_id=task_id,
                    status="queued",
                )
            )
    await db.flush()
    batch = await _load_batch(db, batch.id)
    _counts(batch)
    # 先提交批次与子任务，再创建 coordinator，避免 coordinator 查不到数据。
    await db.commit()
    store = SqlAlchemyTaskStore(db)
    tm = TaskManager(store=store, strategies={})
    coordinator = await tm.create(
        task=_CreateOnlyTask(),
        mode=DeliveryMode.async_polling,
        task_kind=BATCH_TASK_KIND,
        run_args={"batch_id": batch.id},
        workspace_id=project.workspace_id,
    )
    batch = await _load_batch(db, batch.id)
    batch.coordinator_task_id = coordinator.id
    db.add(
        GenerationTaskLink(
            task_id=coordinator.id,
            resource_type="video",
            relation_type=BATCH_RELATION_TYPE,
            relation_entity_id=batch.id,
        )
    )
    await db.commit()
    _enqueue(coordinator.id)
    return await _load_batch(db, batch.id)


async def list_batches(
    db: AsyncSession, *, chapter_id: str
) -> list[VideoGenerationBatch]:
    return list(
        (
            await db.execute(
                select(VideoGenerationBatch)
                .options(selectinload(VideoGenerationBatch.items))
                .where(VideoGenerationBatch.chapter_id == chapter_id)
                .order_by(VideoGenerationBatch.created_at.desc())
            )
        ).scalars().all()
    )


async def get_batch(db: AsyncSession, *, batch_id: str) -> VideoGenerationBatch:
    return await _load_batch(db, batch_id)


async def cancel_batch(db: AsyncSession, *, batch_id: str, reason: str = "") -> VideoGenerationBatch:
    batch = await _load_batch(db, batch_id)
    batch.status = "cancelled"
    batch.error = reason
    store = SqlAlchemyTaskStore(db)
    for item in batch.items:
        if item.status in ACTIVE_ITEM_STATUSES:
            if item.task_id:
                await store.request_cancel(item.task_id, reason or "batch cancelled")
            item.status = "cancelled"
            item.completed_at = datetime.now(UTC)
    _counts(batch)
    await db.commit()
    return await _load_batch(db, batch_id)


async def retry_failed(
    db: AsyncSession, *, batch_id: str, item_ids: list[int] | None = None
) -> VideoGenerationBatch:
    """失败子任务创建新 GenerationTask；沿用原任务输入。"""
    batch = await _load_batch(db, batch_id)
    targets = [
        item
        for item in batch.items
        if item.status == "failed" and (not item_ids or item.id in item_ids)
    ]
    if not targets:
        raise ValueError("没有可重试的失败子任务")
    store = SqlAlchemyTaskStore(db)
    for item in targets:
        old = await db.get(GenerationTask, item.task_id) if item.task_id else None
        if old is None:
            item.status = "failed"
            item.error = "原任务不存在，无法重试"
            continue
        payload = dict(old.payload or {})
        run_args = payload.get("run_args") if isinstance(payload, dict) else None
        if not isinstance(run_args, dict):
            item.error = "原任务没有可复用输入"
            continue
        tm = TaskManager(store=store, strategies={})
        task = await tm.create(
            task=_CreateOnlyTask(),
            mode=DeliveryMode.async_polling,
            task_kind="video_generation",
            run_args=run_args,
            workspace_id=old.workspace_id,
        )
        db.add(
            GenerationTaskLink(
                task_id=task.id,
                resource_type="video",
                relation_type="video",
                relation_entity_id=item.shot_id,
            )
        )
        item.task_id = task.id
        item.status = "queued"
        item.error = ""
        item.enqueued_at = None
    batch.status = "queued"
    batch.error = ""
    _counts(batch)
    await db.commit()
    # 重新唤起 coordinator。
    if batch.coordinator_task_id:
        _enqueue(batch.coordinator_task_id)
    return await _load_batch(db, batch_id)


def _child_status(task: GenerationTask | None) -> str:
    if task is None:
        return "failed"
    if task.status == GenerationTaskStatus.succeeded:
        return "succeeded"
    if task.status in (GenerationTaskStatus.failed, GenerationTaskStatus.cancelled):
        return "failed" if task.status == GenerationTaskStatus.failed else "cancelled"
    return "running" if task.status in (GenerationTaskStatus.running, GenerationTaskStatus.streaming) else "queued"


async def run_video_batch_task(task_id: str, run_args: dict) -> None:
    """Coordinator：按 concurrency 启动子任务，轮询到全部终态。"""
    batch_id = str(run_args.get("batch_id") or "")
    async with async_session_maker() as session:
        store = SqlAlchemyTaskStore(session)
        try:
            await store.set_status(task_id, TaskStatus.running)
            batch = await _load_batch(session, batch_id)
            batch.status = "running"
            batch.started_at = batch.started_at or datetime.now(UTC)
            await session.commit()
            while True:
                batch = await _load_batch(session, batch_id)
                if batch.status == "cancelled":
                    break
                # 刷新子任务状态
                for item in batch.items:
                    if item.status in {"succeeded", "failed", "cancelled"}:
                        continue
                    child = await session.get(GenerationTask, item.task_id) if item.task_id else None
                    item.status = _child_status(child)
                    if item.status in {"succeeded", "failed", "cancelled"}:
                        item.completed_at = datetime.now(UTC)
                        item.error = (child.error if child else "") or item.error
                _counts(batch)
                # 启动 queued，直到达到并发上限
                running = [item for item in batch.items if item.status == "running"]
                slots = max(0, batch.concurrency - len(running))
                for item in batch.items:
                    if slots <= 0:
                        break
                    if item.status != "queued" or not item.task_id or item.enqueued_at:
                        continue
                    _enqueue(item.task_id)
                    item.status = "running"
                    item.enqueued_at = datetime.now(UTC)
                    slots -= 1
                _counts(batch)
                await session.commit()
                if not any(item.status in ACTIVE_ITEM_STATUSES for item in batch.items):
                    break
                await asyncio.sleep(2)
            batch = await _load_batch(session, batch_id)
            if batch.status != "cancelled":
                if batch.failed_count == 0 and batch.cancelled_count == 0:
                    batch.status = "succeeded"
                elif batch.succeeded_count > 0:
                    batch.status = "partial_success"
                elif batch.cancelled_count and not batch.failed_count:
                    batch.status = "cancelled"
                else:
                    batch.status = "failed"
            batch.finished_at = datetime.now(UTC)
            _counts(batch)
            await session.commit()
            await store.set_status(task_id, TaskStatus.succeeded)
            await store.set_progress(task_id, 100)
            await session.commit()
        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            async with async_session_maker() as s2:
                batch2 = await s2.get(VideoGenerationBatch, batch_id)
                if batch2 is not None:
                    batch2.status = "failed"
                    batch2.error = str(exc)
                    batch2.finished_at = datetime.now(UTC)
                st2 = SqlAlchemyTaskStore(s2)
                await st2.set_error(task_id, str(exc))
                await st2.set_status(task_id, TaskStatus.failed)
                await s2.commit()


__all__ = [
    "BATCH_TASK_KIND",
    "cancel_batch",
    "create_video_batch",
    "get_batch",
    "list_batches",
    "retry_failed",
    "run_video_batch_task",
]
