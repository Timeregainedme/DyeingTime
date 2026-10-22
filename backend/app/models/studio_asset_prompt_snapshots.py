"""资产图片提示词快照。

为什么需要独立表：
- 资产图提示词由模板 + 参考图角色动态渲染；用户需要在“生成图片”前审核、
  修改提示词，并在之后继续编辑；
- 直接把提示词写回资产图片表会污染资产本身的数据语义，也不方便按项目批量查询；
- 独立快照表让“生成提示词”和“生成图片”成为两个可独立重试的阶段。

唯一键为 `(asset_type, asset_id)`：一个资产保留一份当前审核稿。需要历史版本时
可在后续扩展 version 列，本表先保证当前版本可回读。
"""

from __future__ import annotations

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class AssetPromptSnapshot(Base, TimestampMixin):
    """资产图片提示词的当前审核稿。"""

    __tablename__ = "asset_prompt_snapshots"
    __table_args__ = (
        UniqueConstraint("asset_type", "asset_id", name="uq_asset_prompt_snapshot_asset"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="快照 ID")
    project_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="项目 ID")
    asset_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True, comment="资产类型：costume/scene/prop/character"
    )
    asset_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="资产 ID")
    image_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="渲染时使用的图片行 ID")
    prompt: Mapped[str] = mapped_column(Text, nullable=False, comment="审核后的完整提示词")
