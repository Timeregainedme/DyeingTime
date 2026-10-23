"""P6 / C12：测试额度预留、结算与防超额测试。"""

from __future__ import annotations

import asyncio
import os
import tempfile

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db import Base
from app.services.studio.generation_quota import (
    QuotaExceeded,
    get_quota_status,
    reserve,
    reserve_for_task,
    settle,
)


async def _make_engine():
    fd, path = tempfile.mkstemp(prefix="quota-", suffix=".db")
    os.close(fd)
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine, path


@pytest.mark.asyncio
async def test_quota_reserve_settle_and_exhaustion() -> None:
    engine, path = await _make_engine()
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with maker() as db:
            status = await get_quota_status(db)
            assert [item["remaining"] for item in status] == [20, 4, 500]
            reservation = await reserve(
                db, media_type="image", amount=20, note="test image"
            )
            await db.commit()
            assert reservation.status == "reserved"
            status = await get_quota_status(db)
            assert status[0]["remaining"] == 0
            with pytest.raises(QuotaExceeded):
                await reserve(db, media_type="image", amount=1)
            await settle(db, reservation, commit=True)
            await db.commit()
            status = await get_quota_status(db)
            assert status[0]["consumed"] == 20
            assert status[0]["reserved"] == 0
            assert status[0]["remaining"] == 0
    finally:
        await engine.dispose()
        os.unlink(path)


@pytest.mark.asyncio
async def test_reservation_release_and_task_idempotency(monkeypatch) -> None:
    engine, path = await _make_engine()
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with maker() as db:
            # 默认关闭时不拦截。
            first = await reserve_for_task(
                db, task_id="task-1", media_type="video", amount=1
            )
            assert first is None
            from app.services.studio import generation_quota

            monkeypatch.setattr(generation_quota.settings, "generation_test_quota_enabled", True)
            first = await reserve_for_task(
                db, task_id="task-1", media_type="video", amount=1
            )
            second = await reserve_for_task(
                db, task_id="task-1", media_type="video", amount=1
            )
            assert first is not None and second is not None
            assert first.id == second.id
            await settle(db, first, commit=False)
            await db.commit()
            status = await get_quota_status(db)
            assert status[1]["consumed"] == 0
            assert status[1]["reserved"] == 0
    finally:
        await engine.dispose()
        os.unlink(path)


@pytest.mark.asyncio
async def test_concurrent_last_video_credit_only_one_wins() -> None:
    engine, path = await _make_engine()
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with maker() as db:
            # 先占用 3 个视频额度，剩最后 1 个。
            await reserve(db, media_type="video", amount=3, note="prefill")
            await db.commit()

        async def _try_reserve() -> bool:
            async with maker() as db:
                try:
                    await reserve(db, media_type="video", amount=1, note="race")
                    await db.commit()
                    return True
                except QuotaExceeded:
                    await db.rollback()
                    return False

        results = await asyncio.gather(_try_reserve(), _try_reserve())
        assert sum(1 for item in results if item) == 1
        async with maker() as db:
            status = await get_quota_status(db)
            assert status[1]["reserved"] == 4
    finally:
        await engine.dispose()
        os.unlink(path)
