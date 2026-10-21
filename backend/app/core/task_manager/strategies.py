from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, Optional

from app.core.task_manager.types import DeliveryMode, TaskRecord, TaskStatus
from app.core.task_manager.stores import TaskStore


StreamingFn = Callable[[dict[str, Any]], AsyncIterator[Any]]
AsyncWorkerFn = Callable[[TaskRecord, TaskStore], Awaitable[None]]


class DeliveryStrategy(ABC):
    """结果交付策略：将“生成执行”与“任务存储”解耦。

扩展点：
- 新增交付方式：实现一个子类并注册到 TaskManager。
"""

    mode: DeliveryMode

    def __init__(self, store: TaskStore) -> None:
        self.store = store

    @abstractmethod
    async def start(self, task: TaskRecord) -> Optional[AsyncIterator[Any]]:
        """启动任务执行。

返回值：
- 流式模式：返回 async iterator（上层可用于 StreamingResponse/SSE/WebSocket）
- 轮询模式：返回 None（只返回 task_id，前端轮询查询状态）
"""

    async def stream(self, task: TaskRecord) -> AsyncIterator[Any]:
        raise NotImplementedError(f"mode={self.mode} does not support stream()")


class StreamingDeliveryStrategy(DeliveryStrategy):
    mode = DeliveryMode.streaming

    def __init__(self, store: TaskStore, streaming_fn: StreamingFn) -> None:
        super().__init__(store)
        self._streaming_fn = streaming_fn

    async def start(self, task: TaskRecord) -> AsyncIterator[Any]:
        await self.store.set_status(task.id, TaskStatus.streaming)
        await self.store.set_progress(task.id, 0)

        async def _gen() -> AsyncIterator[Any]:
            try:
                async for chunk in self._streaming_fn(task.payload):
                    yield chunk
                await self.store.set_progress(task.id, 100)
                await self.store.set_status(task.id, TaskStatus.succeeded)
            except Exception as exc:  # noqa: BLE001
                await self.store.set_error(task.id, str(exc))
                await self.store.set_status(task.id, TaskStatus.failed)
                raise

        return _gen()

    async def stream(self, task: TaskRecord) -> AsyncIterator[Any]:
        return await self.start(task)


class AsyncPollingDeliveryStrategy(DeliveryStrategy):
    mode = DeliveryMode.async_polling

    def __init__(
        self,
        store: TaskStore,
        worker_fn: AsyncWorkerFn,
        *,
        background_runner: Callable[[Awaitable[None]], None] | None = None,
    ) -> None:
        super().__init__(store)
        self._worker_fn = worker_fn
        def _spawn(coro: Awaitable[None]) -> None:
            asyncio.create_task(coro)

        self._background_runner = background_runner or _spawn

    async def start(self, task: TaskRecord) -> None:
        await self.store.set_status(task.id, TaskStatus.running)
        await self.store.set_progress(task.id, 0)

        async def _run() -> None:
            try:
                await self._worker_fn(task, self.store)
            except Exception as exc:  # noqa: BLE001
                await self.store.set_error(task.id, str(exc))
                await self.store.set_status(task.id, TaskStatus.failed)

        self._background_runner(_run())
        return None

