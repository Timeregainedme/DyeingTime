"""章节制作阶段状态聚合。

四个独立按钮需要一份共同的状态来源：分镜数、候选数、资产数、提示词审核稿数、
分镜帧提示词/图片数。这里只做轻量计数，不触发任何生成。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.studio import (
    Chapter,
    Character,
    Costume,
    ProjectCostumeLink,
    ProjectPropLink,
    ProjectSceneLink,
    Prop,
    Scene,
    Shot,
    ShotDetail,
    ShotExtractedCandidate,
    ShotFrameImage,
)
from app.models.studio_asset_prompt_snapshots import AssetPromptSnapshot


async def build_chapter_production_status(
    db: AsyncSession,
    *,
    chapter_id: str,
) -> dict[str, Any]:
    """返回章节制作状态；找不到章节时抛 ValueError。"""
    chapter = await db.get(Chapter, chapter_id)
    if chapter is None:
        raise ValueError("chapter not found")

    shot_ids = [
        str(item)
        for item in (
            await db.execute(select(Shot.id).where(Shot.chapter_id == chapter_id))
        ).scalars().all()
    ]
    shots_count = len(shot_ids)

    candidate_counts = {"pending": 0, "linked": 0, "ignored": 0}
    if shot_ids:
        rows = (
            await db.execute(
                select(ShotExtractedCandidate.candidate_status, func.count(ShotExtractedCandidate.id))
                .where(ShotExtractedCandidate.shot_id.in_(shot_ids))
                .group_by(ShotExtractedCandidate.candidate_status)
            )
        ).all()
        for status, count in rows:
            key = getattr(status, "value", status)
            candidate_counts[str(key)] = int(count)

    assets: dict[str, int] = {}
    assets["character"] = int(
        (await db.execute(select(func.count(Character.id)).where(Character.project_id == chapter.project_id))).scalar_one()
    )
    for asset_type, model, link_model, field in (
        ("costume", Costume, ProjectCostumeLink, "costume_id"),
        ("scene", Scene, ProjectSceneLink, "scene_id"),
        ("prop", Prop, ProjectPropLink, "prop_id"),
    ):
        assets[asset_type] = int(
            (
                await db.execute(
                    select(func.count(func.distinct(getattr(link_model, field)))).where(
                        link_model.project_id == chapter.project_id
                    )
                )
            ).scalar_one()
        )

    missing_actor_rows = (
        await db.execute(
            select(Character.name).where(
                Character.project_id == chapter.project_id,
                Character.actor_id.is_(None),
            )
        )
    ).scalars().all()

    snapshot_rows = (
        await db.execute(
            select(AssetPromptSnapshot.asset_type, func.count(AssetPromptSnapshot.id))
            .where(AssetPromptSnapshot.project_id == chapter.project_id)
            .group_by(AssetPromptSnapshot.asset_type)
        )
    ).all()
    prompt_snapshots = {"costume": 0, "scene": 0, "prop": 0, "character": 0}
    for asset_type, count in snapshot_rows:
        prompt_snapshots[str(asset_type)] = int(count)

    frame_prompts = {"first": 0, "last": 0, "key": 0}
    frame_images = {"first": 0, "last": 0, "key": 0}
    if shot_ids:
        details = (
            await db.execute(select(ShotDetail).where(ShotDetail.id.in_(shot_ids)))
        ).scalars().all()
        for detail in details:
            if str(getattr(detail, "first_frame_prompt", "") or "").strip():
                frame_prompts["first"] += 1
            if str(getattr(detail, "last_frame_prompt", "") or "").strip():
                frame_prompts["last"] += 1
            if str(getattr(detail, "key_frame_prompt", "") or "").strip():
                frame_prompts["key"] += 1

        image_rows = (
            await db.execute(
                select(ShotFrameImage.frame_type, func.count(ShotFrameImage.id))
                .where(
                    ShotFrameImage.shot_detail_id.in_(shot_ids),
                    ShotFrameImage.file_id.is_not(None),
                )
                .group_by(ShotFrameImage.frame_type)
            )
        ).all()
        for frame_type, count in image_rows:
            key = getattr(frame_type, "value", frame_type)
            frame_images[str(key)] = int(count)

    return {
        "chapter_id": chapter_id,
        "project_id": chapter.project_id,
        "shots": shots_count,
        "candidates": candidate_counts,
        "assets": assets,
        "character_actor_missing": [str(name) for name in missing_actor_rows if name],
        "asset_prompt_snapshots": prompt_snapshots,
        "frame_prompts": frame_prompts,
        "frame_images": frame_images,
    }
