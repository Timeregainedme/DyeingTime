#!/usr/bin/env python3
"""一次性回填 file_usages（从现有业务表推导 project/chapter/shot）。

用法（在项目根目录 backend 下）::

    uv run python scripts/backfill_file_usages.py

需在配置好 DATABASE_URL 的环境中执行。
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.db import async_session_maker
from app.models.studio import (
    CharacterImage,
    FileItem,
    Shot,
    ShotDetail,
    ShotFrameImage,
)
from app.models.types import FileUsageKind
from app.services.studio.file_usages import (
    first_project_id_for_actor,
    first_project_id_for_costume,
    first_project_id_for_prop,
    first_project_id_for_scene,
    sync_usage_from_character,
    sync_usage_from_shot_context,
    upsert_file_usage,
)


async def main() -> None:
    async with async_session_maker() as session:
        # 分镜帧
        r1 = await session.execute(
            select(ShotFrameImage).where(ShotFrameImage.file_id.is_not(None))
        )
        for row in r1.scalars().all():
            fid = row.file_id
            if not fid:
                continue
            detail = await session.get(ShotDetail, row.shot_detail_id)
            if detail is None:
                continue
            await sync_usage_from_shot_context(
                session,
                file_id=fid,
                shot_id=detail.id,
                usage_kind=FileUsageKind.shot_frame,
                source_ref=f"shot_frame_image:{row.id}",
            )

        # 镜头生成视频
        r2 = await session.execute(select(Shot).where(Shot.generated_video_file_id.is_not(None)))
        for shot in r2.scalars().all():
            fid = shot.generated_video_file_id
            if not fid:
                continue
            await sync_usage_from_shot_context(
                session,
                file_id=fid,
                shot_id=shot.id,
                usage_kind=FileUsageKind.generated_video,
                source_ref=f"shot:{shot.id}:generated_video",
            )

        # 角色图
        r3 = await session.execute(
            select(CharacterImage).where(CharacterImage.file_id.is_not(None))
        )
        for ci in r3.scalars().all():
            fid = ci.file_id
            if not fid:
                continue
            await sync_usage_from_character(
                session,
                file_id=fid,
                character_id=ci.character_id,
                usage_kind=FileUsageKind.character_image,
                source_ref=f"character_image:{ci.id}",
            )

        # 资产图（取任意一条 project 链接）
        from app.models.studio import ActorImage, CostumeImage, PropImage, SceneImage

        for model, fk, first_fn, prefix in [
            (SceneImage, "scene_id", first_project_id_for_scene, "scene_image"),
            (PropImage, "prop_id", first_project_id_for_prop, "prop_image"),
            (CostumeImage, "costume_id", first_project_id_for_costume, "costume_image"),
            (ActorImage, "actor_id", first_project_id_for_actor, "actor_image"),
        ]:
            r = await session.execute(select(model).where(model.file_id.is_not(None)))
            for img in r.scalars().all():
                fid = img.file_id
                if not fid:
                    continue
                asset_id = getattr(img, fk)
                pid = await first_fn(session, asset_id)
                if pid:
                    await upsert_file_usage(
                        session,
                        file_id=fid,
                        project_id=pid,
                        chapter_id=None,
                        shot_id=None,
                        usage_kind=FileUsageKind.asset_image,
                        source_ref=f"{prefix}:{img.id}",
                    )

        await session.commit()
        print("backfill_file_usages: done")


if __name__ == "__main__":
    asyncio.run(main())
