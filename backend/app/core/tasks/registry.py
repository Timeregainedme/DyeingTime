"""任务执行器注册中心：按 task_kind + provider_key 分派。"""

from __future__ import annotations

from collections.abc import Callable
from threading import RLock

from app.core.task_manager.types import BaseTask

TaskFactory = Callable[..., BaseTask]

_FACTORIES: dict[tuple[str, str], TaskFactory] = {}
_LOCK = RLock()


def _norm(value: str) -> str:
    return (value or "").strip().lower()


def register_task_adapter(task_kind: str, provider_key: str, factory: TaskFactory) -> None:
    """注册任务执行器；相同 key+factory 重复注册视为幂等。"""

    tk = _norm(task_kind)
    pk = _norm(provider_key)
    if not tk or not pk:
        raise ValueError("task_kind and provider_key must be non-empty")
    key = (tk, pk)
    with _LOCK:
        existing = _FACTORIES.get(key)
        if existing is not None and existing is not factory:
            raise ValueError(f"task adapter conflict for task_kind={tk!r}, provider_key={pk!r}")
        _FACTORIES[key] = factory


def resolve_task_adapter(task_kind: str, provider_key: str) -> TaskFactory:
    """解析任务执行器；未注册时抛出清晰错误。"""

    key = (_norm(task_kind), _norm(provider_key))
    with _LOCK:
        factory = _FACTORIES.get(key)
    if factory is None:
        raise ValueError(f"Unsupported provider/task adapter: task_kind={key[0]!r}, provider={key[1]!r}")
    return factory


def list_registered_task_adapters(task_kind: str | None = None) -> list[tuple[str, str]]:
    """返回已注册适配器列表（用于诊断/测试）。"""

    tk = _norm(task_kind) if task_kind else None
    with _LOCK:
        keys = list(_FACTORIES.keys())
    if tk is not None:
        keys = [item for item in keys if item[0] == tk]
    return sorted(keys)
