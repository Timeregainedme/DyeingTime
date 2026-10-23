"""P6 / C12：开发验收测试额度与原子预留记录。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class GenerationQuota(Base, TimestampMixin):
    """按 scope + media_type 聚合的额度。"""

    __tablename__ = "generation_quotas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    media_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    limit_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    consumed_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("scope", "media_type", name="uq_generation_quotas_scope_media"),
    )


class GenerationUsageReservation(Base, TimestampMixin):
    """一次供应商调用前的额度预留与结算。"""

    __tablename__ = "generation_usage_reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    media_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="reserved", index=True,
        comment="reserved/committed/released",
    )
    task_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("generation_tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    model: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_generation_usage_reservations_task_media", "task_id", "media_type"),
    )


__all__ = ["GenerationQuota", "GenerationUsageReservation"]
