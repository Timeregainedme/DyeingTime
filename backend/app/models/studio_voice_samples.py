"""P6：角色固定音色样本文件（与供应商 voice_id 区分）。"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class CharacterVoiceSample(Base, TimestampMixin):
    """可提交给 H3 做音色参考的固定音频样本。"""

    __tablename__ = "character_voice_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("files.id", ondelete="SET NULL"), nullable=True, index=True
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (Index("ix_character_voice_samples_char_active", "character_id", "is_active"),)


__all__ = ["CharacterVoiceSample"]
