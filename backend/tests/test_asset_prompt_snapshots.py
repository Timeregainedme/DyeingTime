"""资产提示词审核稿的数据层测试。"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db import Base
from app.services.studio.asset_prompt_snapshots import (
    get_asset_prompt_snapshot,
    list_asset_prompt_snapshots,
    update_asset_prompt_snapshot_prompt,
    upsert_asset_prompt_snapshot,
)


async def _build_session() -> tuple[AsyncSession, object]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_local = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return session_local(), engine


@pytest.mark.asyncio
async def test_upsert_and_update_asset_prompt_snapshot() -> None:
    db, engine = await _build_session()
    async with db:
        first = await upsert_asset_prompt_snapshot(
            db,
            project_id="p1",
            asset_type="character",
            asset_id="c1",
            image_id=1,
            prompt="旧提示词",
        )
        await db.commit()
        assert first.prompt == "旧提示词"

        second = await upsert_asset_prompt_snapshot(
            db,
            project_id="p1",
            asset_type="character",
            asset_id="c1",
            image_id=2,
            prompt="新提示词",
        )
        await db.commit()
        assert second.id == first.id
        assert second.prompt == "新提示词"
        assert second.image_id == 2

        updated = await update_asset_prompt_snapshot_prompt(
            db,
            asset_type="character",
            asset_id="c1",
            prompt="审核后提示词",
        )
        await db.commit()
        assert updated is not None
        assert updated.prompt == "审核后提示词"

        rows = await list_asset_prompt_snapshots(db, project_id="p1")
        assert [row.asset_id for row in rows] == ["c1"]
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_missing_snapshot_returns_none() -> None:
    db, engine = await _build_session()
    async with db:
        assert (
            await get_asset_prompt_snapshot(db, asset_type="scene", asset_id="missing")
        ) is None
    await engine.dispose()
