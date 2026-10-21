"""Async worker 任务的通用辅助函数。"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.task_manager import SqlAlchemyTaskStore


async def cancel_if_requested_async(
    *,
    store: SqlAlchemyTaskStore,
    task_id: str,
    session: AsyncSession,
) -> bool:
    """在 async service 阶段边界执行协作式取消检查。"""

    if not await store.is_cancel_requested(task_id):
        return False
    await store.mark_cancelled(task_id)
    await session.commit()
    return True
