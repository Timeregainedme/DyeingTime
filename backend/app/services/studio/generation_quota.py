"""P6 / C12：开发验收测试额度的原子预留与结算。

生产用户额度与本次 V2 验收预算分离：默认 scope `v2-acceptance`；
运行时只有显式开启 `generation_test_quota_enabled` 才拦截真实调用。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.studio import GenerationQuota, GenerationUsageReservation

DEFAULT_SCOPE = "v2-acceptance"
DEFAULT_LIMITS = {"image": 20, "video": 4, "audio": 500}
MEDIA_TYPES = {"image", "video", "audio"}


class QuotaExceeded(ValueError):
    """额度不足；调用方应转换为 409/任务失败，而不是继续提交供应商。"""


async def _get_quota(
    db: AsyncSession, *, scope: str, media_type: str
) -> GenerationQuota:
    row = (
        await db.execute(
            select(GenerationQuota).where(
                GenerationQuota.scope == scope,
                GenerationQuota.media_type == media_type,
            )
        )
    ).scalars().first()
    if row is None:
        limit = DEFAULT_LIMITS.get(media_type, 0)
        row = GenerationQuota(
            scope=scope,
            media_type=media_type,
            limit_amount=limit,
            consumed_amount=0,
            reserved_amount=0,
        )
        db.add(row)
        await db.flush()
    return row


async def get_quota_status(
    db: AsyncSession, *, scope: str = DEFAULT_SCOPE
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for media_type in ("image", "video", "audio"):
        row = await _get_quota(db, scope=scope, media_type=media_type)
        rows.append(
            {
                "scope": row.scope,
                "media_type": row.media_type,
                "limit": row.limit_amount,
                "consumed": row.consumed_amount,
                "reserved": row.reserved_amount,
                "remaining": max(
                    0, row.limit_amount - row.consumed_amount - row.reserved_amount
                ),
            }
        )
    return rows


async def reserve(
    db: AsyncSession,
    *,
    media_type: str,
    amount: int,
    scope: str = DEFAULT_SCOPE,
    task_id: str | None = None,
    provider: str = "",
    model: str = "",
    note: str = "",
) -> GenerationUsageReservation:
    if media_type not in MEDIA_TYPES:
        raise QuotaExceeded(f"未知媒体类型：{media_type}")
    if amount <= 0:
        raise QuotaExceeded("额度预留数量必须大于 0")
    quota = await _get_quota(db, scope=scope, media_type=media_type)
    # 原子 UPDATE：仅当 consumed + reserved + amount 不超过 limit 才成功。
    result = await db.execute(
        update(GenerationQuota)
        .where(
            GenerationQuota.id == quota.id,
            GenerationQuota.consumed_amount
            + GenerationQuota.reserved_amount
            + amount
            <= GenerationQuota.limit_amount,
        )
        .values(reserved_amount=GenerationQuota.reserved_amount + amount)
    )
    if result.rowcount != 1:
        raise QuotaExceeded(
            f"{scope}/{media_type} 测试额度不足：需要 {amount}，"
            f"剩余 {max(0, quota.limit_amount - quota.consumed_amount - quota.reserved_amount)}"
        )
    reservation = GenerationUsageReservation(
        scope=scope,
        media_type=media_type,
        amount=amount,
        status="reserved",
        task_id=task_id,
        provider=provider,
        model=model,
        note=note,
    )
    db.add(reservation)
    await db.flush()
    return reservation


async def settle(
    db: AsyncSession,
    reservation: GenerationUsageReservation,
    *,
    commit: bool,
) -> GenerationUsageReservation:
    """结算预留；commit=True 表示供应商请求已发送/可能计费。"""
    if reservation.status != "reserved":
        return reservation
    quota = await _get_quota(
        db, scope=reservation.scope, media_type=reservation.media_type
    )
    if commit:
        quota.consumed_amount += reservation.amount
        reservation.status = "committed"
    else:
        reservation.status = "released"
    quota.reserved_amount = max(0, quota.reserved_amount - reservation.amount)
    reservation.settled_at = datetime.now(UTC)
    await db.flush()
    return reservation


async def settle_task(
    db: AsyncSession, *, task_id: str, media_type: str, commit: bool
) -> None:
    row = (
        await db.execute(
            select(GenerationUsageReservation)
            .where(
                GenerationUsageReservation.task_id == task_id,
                GenerationUsageReservation.media_type == media_type,
                GenerationUsageReservation.status == "reserved",
            )
            .order_by(GenerationUsageReservation.id.desc())
            .limit(1)
        )
    ).scalars().first()
    if row is not None:
        await settle(db, row, commit=commit)


def quota_enabled() -> bool:
    return bool(getattr(settings, "generation_test_quota_enabled", False))


async def reserve_for_task(
    db: AsyncSession,
    *,
    task_id: str,
    media_type: str,
    amount: int,
    provider: str = "",
    model: str = "",
    note: str = "",
) -> GenerationUsageReservation | None:
    """执行层入口：未启用测试预算时返回 None。"""
    if not quota_enabled():
        return None
    existing = (
        await db.execute(
            select(GenerationUsageReservation)
            .where(
                GenerationUsageReservation.task_id == task_id,
                GenerationUsageReservation.media_type == media_type,
                GenerationUsageReservation.status.in_(["reserved", "committed"]),
            )
            .limit(1)
        )
    ).scalars().first()
    if existing is not None:
        return existing
    return await reserve(
        db,
        media_type=media_type,
        amount=amount,
        scope=getattr(settings, "generation_test_quota_scope", DEFAULT_SCOPE),
        task_id=task_id,
        provider=provider,
        model=model,
        note=note,
    )


async def list_reservations(
    db: AsyncSession, *, scope: str = DEFAULT_SCOPE, limit: int = 100
) -> list[GenerationUsageReservation]:
    return list(
        (
            await db.execute(
                select(GenerationUsageReservation)
                .where(GenerationUsageReservation.scope == scope)
                .order_by(GenerationUsageReservation.id.desc())
                .limit(limit)
            )
        ).scalars().all()
    )


__all__ = [
    "DEFAULT_SCOPE",
    "QuotaExceeded",
    "get_quota_status",
    "list_reservations",
    "quota_enabled",
    "reserve",
    "reserve_for_task",
    "settle",
    "settle_task",
]
