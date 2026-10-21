"""通用校验工具：实体存在性与重复性检查。"""

from __future__ import annotations

from typing import Any, TypeVar

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


async def require_entity(
    db: AsyncSession,
    model: type[ModelT],
    entity_id: Any,
    *,
    detail: str,
    status_code: int = status.HTTP_404_NOT_FOUND,
) -> ModelT:
    """确保实体存在，并返回实体对象。"""
    obj = await db.get(model, entity_id)
    if obj is None:
        raise HTTPException(status_code=status_code, detail=detail)
    return obj


async def require_optional_entity(
    db: AsyncSession,
    model: type[ModelT],
    entity_id: Any | None,
    *,
    detail: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> ModelT | None:
    """如果传入了实体 ID，则校验其存在性。"""
    if entity_id is None:
        return None
    return await require_entity(
        db,
        model,
        entity_id,
        detail=detail,
        status_code=status_code,
    )


async def ensure_not_exists(
    db: AsyncSession,
    model: type[Any],
    entity_id: Any,
    *,
    detail: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> None:
    """确保给定主键对应的实体不存在。"""
    obj = await db.get(model, entity_id)
    if obj is not None:
        raise HTTPException(status_code=status_code, detail=detail)
