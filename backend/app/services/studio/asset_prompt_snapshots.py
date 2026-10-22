"""资产图片提示词快照的数据层能力。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.studio import AssetPromptSnapshot


async def get_asset_prompt_snapshot(
    db: AsyncSession,
    *,
    asset_type: str,
    asset_id: str,
) -> AssetPromptSnapshot | None:
    """读取单个资产的当前提示词审核稿。"""
    stmt = select(AssetPromptSnapshot).where(
        AssetPromptSnapshot.asset_type == asset_type.strip().lower(),
        AssetPromptSnapshot.asset_id == asset_id,
    )
    return (await db.execute(stmt)).scalars().first()


async def upsert_asset_prompt_snapshot(
    db: AsyncSession,
    *,
    project_id: str,
    asset_type: str,
    asset_id: str,
    image_id: int | None,
    prompt: str,
) -> AssetPromptSnapshot:
    """写入或更新单个资产的提示词审核稿。"""
    normalized_type = asset_type.strip().lower()
    snapshot = await get_asset_prompt_snapshot(
        db,
        asset_type=normalized_type,
        asset_id=asset_id,
    )
    if snapshot is None:
        snapshot = AssetPromptSnapshot(
            project_id=project_id,
            asset_type=normalized_type,
            asset_id=asset_id,
            image_id=image_id,
            prompt=prompt,
        )
        db.add(snapshot)
    else:
        snapshot.project_id = project_id
        snapshot.image_id = image_id
        snapshot.prompt = prompt
    await db.flush()
    return snapshot


async def list_asset_prompt_snapshots(
    db: AsyncSession,
    *,
    project_id: str,
    asset_type: str | None = None,
) -> list[AssetPromptSnapshot]:
    """按项目（可选资产类型）列出提示词审核稿。"""
    stmt = select(AssetPromptSnapshot).where(AssetPromptSnapshot.project_id == project_id)
    if asset_type:
        stmt = stmt.where(AssetPromptSnapshot.asset_type == asset_type.strip().lower())
    stmt = stmt.order_by(AssetPromptSnapshot.asset_type.asc(), AssetPromptSnapshot.asset_id.asc())
    return list((await db.execute(stmt)).scalars().all())


async def update_asset_prompt_snapshot_prompt(
    db: AsyncSession,
    *,
    asset_type: str,
    asset_id: str,
    prompt: str,
) -> AssetPromptSnapshot | None:
    """更新审核稿正文；不存在时返回 None。"""
    snapshot = await get_asset_prompt_snapshot(db, asset_type=asset_type, asset_id=asset_id)
    if snapshot is None:
        return None
    snapshot.prompt = prompt
    await db.flush()
    return snapshot
