"""通用 CRUD 助手：减少路由层样板代码。"""

from __future__ import annotations

from typing import Any, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.common.validators import require_entity

ModelT = TypeVar("ModelT")


async def create_and_refresh(db: AsyncSession, obj: ModelT) -> ModelT:
    """写入对象并刷新，返回最新状态。"""
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


def patch_model(obj: Any, data: dict[str, Any]) -> Any:
    """将字典字段更新到模型实例。"""
    for field, value in data.items():
        setattr(obj, field, value)
    return obj


async def get_or_404(
    db: AsyncSession,
    model: type[ModelT],
    entity_id: Any,
    *,
    detail: str,
) -> ModelT:
    """获取实体，不存在时抛出 404。"""
    return await require_entity(db, model, entity_id, detail=detail)


async def flush_and_refresh(db: AsyncSession, obj: ModelT) -> ModelT:
    """刷新已更新对象并返回。"""
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_if_exists(
    db: AsyncSession,
    model: type[Any],
    entity_id: Any,
) -> None:
    """若实体存在则删除；不存在时静默返回。"""
    obj = await db.get(model, entity_id)
    if obj is None:
        return
    await db.delete(obj)
    await db.flush()
