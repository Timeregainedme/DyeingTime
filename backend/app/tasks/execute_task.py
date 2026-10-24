"""统一 Celery 执行入口。

职责：
- Celery 统一只接收业务 task_id；
- 通过 GenerationTask.task_kind + registry 找到具体 WorkerTaskExecutor；
- 回写 executor_type / executor_task_id，便于排障。
"""

from __future__ import annotations

import logging
import time

from celery.result import AsyncResult

from app.core.celery_app import celery_app
from app.core.db_sync import sync_session_maker
from app.models.task import GenerationTask
from app.services.worker.task_registry import task_executor_registry

logger = logging.getLogger(__name__)


def _record_executor_dispatch(task_id: str, *, executor_type: str, executor_task_id: str | None) -> None:
    with sync_session_maker() as db:
        row = db.get(GenerationTask, task_id)
        if row is None:
            return
        row.executor_type = executor_type
        row.executor_task_id = executor_task_id
        db.commit()


# 队列划分：图片与视频的并发需求不同（出图多而快、出片少而慢），
# 用独立队列 + 独立 worker 才能分别设定并发，而不是共用一个 prefork 池。
QUEUE_IMAGE = "image"
QUEUE_VIDEO = "video"

# task_kind → 队列。未列出的类型走默认队列（脚本处理、音频等）。
_QUEUE_BY_TASK_KIND: dict[str, str] = {
    "image_generation": QUEUE_IMAGE,
    "video_generation": QUEUE_VIDEO,
}


def _resolve_queue(task_id: str) -> str | None:
    """按任务类型选队列；读不到任务时返回 None（走默认队列）。"""
    with sync_session_maker() as db:
        row = db.get(GenerationTask, task_id)
        if row is None:
            return None
        kind = (row.task_kind or "").strip() or str((row.payload or {}).get("task_kind") or "").strip()
    return _QUEUE_BY_TASK_KIND.get(kind)


def enqueue_task_execution(task_id: str) -> AsyncResult:
    queue = _resolve_queue(task_id)
    if queue:
        async_result = run_task_celery.apply_async(args=[task_id], queue=queue)
    else:
        async_result = run_task_celery.delay(task_id)
    _record_executor_dispatch(
        task_id,
        executor_type="celery",
        executor_task_id=async_result.id,
    )
    return async_result


def revoke_task_execution(task_id: str, *, terminate: bool = True, signal: str = "SIGTERM") -> bool:
    with sync_session_maker() as db:
        row = db.get(GenerationTask, task_id)
        if row is None:
            return False
        if (row.executor_type or "").strip() != "celery":
            return False
        executor_task_id = (row.executor_task_id or "").strip()
        if not executor_task_id:
            return False

    try:
        AsyncResult(executor_task_id, app=celery_app).revoke(terminate=terminate, signal=signal)
    except Exception:  # noqa: BLE001
        logger.exception("failed to revoke celery task: task_id=%s executor_task_id=%s", task_id, executor_task_id)
        return False
    return True


def _load_task_kind(task_id: str, *, attempts: int = 10, delay_s: float = 0.3) -> str | None:
    """读取任务类型；任务行暂时不可见时短暂重试。

    为什么需要重试：部分业务在事务提交前就调用了 enqueue，worker 可能抢先消费。
    不重试会让 `row is None` 直接 return，Celery 仍显示成功，而任务永久 pending。
    重新提交点已经改为 commit→enqueue；这里作为跨模块兜底，持续时间不超过 3 秒。
    """
    for attempt in range(attempts):
        with sync_session_maker() as db:
            row = db.get(GenerationTask, task_id)
            if row is not None:
                return (row.task_kind or "").strip() or str((row.payload or {}).get("task_kind") or "").strip()
        if attempt < attempts - 1:
            time.sleep(delay_s)
    return None


@celery_app.task(name="task.execute")
def run_task_celery(task_id: str) -> None:
    task_kind = _load_task_kind(task_id)
    if not task_kind:
        logger.error("task not found after retries: task_id=%s", task_id)
        return
    executor = task_executor_registry.resolve(task_kind)
    executor.run(task_id)
