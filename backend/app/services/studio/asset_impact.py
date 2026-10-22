"""P4 / C8：资产引用与受影响镜头分析。

两级精度：
- `explicit`：数据库显式关联表（shot_character_links / project_*_links.shot_id）；
- `possible`：章节/项目级关联，或剧本文本出现资产名称。
P4 没有镜头级版本引用，因此所有版本变更的影响精度最多为 `possible`。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.studio import (
    AssetVersionImpactRef,
    Chapter,
    Character,
    Costume,
    ProjectCostumeLink,
    ProjectPropLink,
    ProjectSceneLink,
    Prop,
    Scene,
    Shot,
    ShotCharacterLink,
)
from app.schemas.studio.asset_versions import (
    AssetImpactRead,
    AssetImpactShot,
    AssetVersionImpactRefRead,
)
from app.services.studio.asset_versions import (
    asset_belongs_to_project,
    normalize_asset_type,
)
from app.services.studio.character_aliases import list_aliases

_ASSET_NAME_MODELS = {
    "character": Character,
    "scene": Scene,
    "prop": Prop,
    "costume": Costume,
}


def _shot_dict(shot: Shot, chapter: Chapter) -> dict[str, Any]:
    return {
        "shot_id": shot.id,
        "chapter_id": chapter.id,
        "chapter_index": chapter.index,
        "chapter_title": chapter.title,
        "shot_index": shot.index,
        "shot_title": shot.title,
        "has_video": bool(shot.generated_video_file_id),
        "video_file_id": shot.generated_video_file_id,
    }


async def _asset_names(db: AsyncSession, *, asset_type: str, asset_id: str) -> list[str]:
    model = _ASSET_NAME_MODELS[asset_type]
    row = await db.get(model, asset_id)
    names = [row.name] if row is not None and row.name else []
    if asset_type == "character" and row is not None:
        names.extend(item.alias for item in await list_aliases(db, character_id=asset_id))
    return list(dict.fromkeys(names))


async def _text_possible_shots(
    db: AsyncSession,
    *,
    project_id: str,
    names: list[str],
) -> list[tuple[Shot, Chapter, str]]:
    if not names:
        return []
    chapters = (
        await db.execute(
            select(Chapter).where(
                Chapter.project_id == project_id,
                Chapter.raw_text.is_not(None),
            )
        )
    ).scalars().all()
    matched_chapter_ids = [
        chapter.id
        for chapter in chapters
        if any(name and name in (chapter.raw_text or "") for name in names)
    ]
    if not matched_chapter_ids:
        return []
    rows = (
        await db.execute(
            select(Shot, Chapter)
            .join(Chapter, Chapter.id == Shot.chapter_id)
            .where(Shot.chapter_id.in_(matched_chapter_ids))
        )
    ).all()
    return [(shot, chapter, "script_text_mention") for shot, chapter in rows]


async def _linked_shots(
    db: AsyncSession,
    *,
    project_id: str,
    asset_type: str,
    asset_id: str,
) -> list[tuple[Shot, Chapter, str, str]]:
    """返回 (shot, chapter, certainty, reference_kind) 列表。"""
    if asset_type == "character":
        rows = (
            await db.execute(
                select(Shot, Chapter)
                .join(Chapter, Chapter.id == Shot.chapter_id)
                .join(ShotCharacterLink, ShotCharacterLink.shot_id == Shot.id)
                .where(
                    ShotCharacterLink.character_id == asset_id,
                    Chapter.project_id == project_id,
                )
            )
        ).all()
        return [(shot, chapter, "explicit", "shot_character_link") for shot, chapter in rows]

    link_model, field = {
        "scene": (ProjectSceneLink, "scene_id"),
        "prop": (ProjectPropLink, "prop_id"),
        "costume": (ProjectCostumeLink, "costume_id"),
    }[asset_type]
    links = (
        await db.execute(
            select(link_model).where(
                link_model.project_id == project_id,
                getattr(link_model, field) == asset_id,
            )
        )
    ).scalars().all()
    result: list[tuple[Shot, Chapter, str, str]] = []
    for link in links:
        if link.shot_id:
            row = (
                await db.execute(
                    select(Shot, Chapter)
                    .join(Chapter, Chapter.id == Shot.chapter_id)
                    .where(Shot.id == link.shot_id, Chapter.project_id == project_id)
                )
            ).first()
            if row:
                result.append((row[0], row[1], "explicit", "shot_asset_link"))
        elif link.chapter_id:
            rows = (
                await db.execute(
                    select(Shot, Chapter)
                    .join(Chapter, Chapter.id == Shot.chapter_id)
                    .where(
                        Shot.chapter_id == link.chapter_id,
                        Chapter.project_id == project_id,
                    )
                )
            ).all()
            result.extend(
                (shot, chapter, "possible", "chapter_asset_link")
                for shot, chapter in rows
            )
        else:
            rows = (
                await db.execute(
                    select(Shot, Chapter)
                    .join(Chapter, Chapter.id == Shot.chapter_id)
                    .where(Chapter.project_id == project_id)
                )
            ).all()
            result.extend(
                (shot, chapter, "possible", "project_asset_link")
                for shot, chapter in rows
            )
    return result


async def analyze_asset_impact(
    db: AsyncSession,
    *,
    project_id: str,
    asset_type: str,
    asset_id: str,
    from_version_id: str | None = None,
    to_version_id: str | None = None,
) -> AssetImpactRead:
    """查询资产引用并返回确定/可能受影响镜头；不修改任何正式数据。"""
    normalized = normalize_asset_type(asset_type)
    if not await asset_belongs_to_project(
        db, asset_type=normalized, asset_id=asset_id, project_id=project_id
    ):
        raise ValueError("资产不存在或不属于当前项目")

    links = await _linked_shots(
        db, project_id=project_id, asset_type=normalized, asset_id=asset_id
    )
    names = await _asset_names(db, asset_type=normalized, asset_id=asset_id)
    text_rows = await _text_possible_shots(db, project_id=project_id, names=names)

    merged: dict[str, dict[str, Any]] = {}
    for shot, chapter, certainty, kind in links:
        row = _shot_dict(shot, chapter)
        row.update({"certainty": certainty, "reference_kind": kind, "version_precision": "asset_level"})
        merged[shot.id] = row  # explicit 覆盖 possible
    for shot, chapter, kind in text_rows:
        if shot.id in merged:
            merged[shot.id]["reference_kind"] = (
                merged[shot.id]["reference_kind"] + "+script_text_mention"
            )
            continue
        row = _shot_dict(shot, chapter)
        row.update(
            {
                "certainty": "possible",
                "reference_kind": kind,
                "version_precision": "asset_level",
            }
        )
        merged[shot.id] = row

    shots = sorted(
        merged.values(),
        key=lambda item: (item.get("chapter_index") or 0, item.get("shot_index") or 0),
    )
    chapter_map: dict[str, dict[str, Any]] = {}
    for item in shots:
        chapter = chapter_map.get(item["chapter_id"])
        if chapter is None:
            chapter = {
                "chapter_id": item["chapter_id"],
                "index": item.get("chapter_index"),
                "title": item.get("chapter_title") or "",
                "shot_count": 0,
                "explicit_count": 0,
                "possible_count": 0,
                "video_count": 0,
            }
            chapter_map[item["chapter_id"]] = chapter
        chapter["shot_count"] += 1
        if item["certainty"] == "explicit":
            chapter["explicit_count"] += 1
        else:
            chapter["possible_count"] += 1
        if item["has_video"]:
            chapter["video_count"] += 1

    summary = {
        "shot_count": len(shots),
        "explicit_count": sum(1 for item in shots if item["certainty"] == "explicit"),
        "possible_count": sum(1 for item in shots if item["certainty"] == "possible"),
        "chapter_count": len(chapter_map),
        "video_count": sum(1 for item in shots if item["has_video"]),
        "version_precision": "asset_level",
        "version_reference_established": False,
    }
    return AssetImpactRead(
        project_id=project_id,
        asset_type=normalized,
        asset_id=asset_id,
        from_version_id=from_version_id,
        to_version_id=to_version_id,
        chapters=list(chapter_map.values()),
        shots=[AssetImpactShot.model_validate(item) for item in shots],
        summary=summary,
        notes=[
            "`explicit` 表示数据库显式资产关联；`possible` 表示章节/项目级关联或剧本文本提及。",
            "P4 尚未建立镜头级版本引用，版本变更影响精度为 asset_level；不能声称镜头已引用新版本。",
            "已有视频不会删除、覆盖或自动重新生成。",
        ],
    )


async def record_version_impact(
    db: AsyncSession,
    *,
    project_id: str,
    asset_type: str,
    asset_id: str,
    from_version_id: str | None,
    to_version_id: str | None,
    created_by: int | None = None,
) -> list[AssetVersionImpactRef]:
    """记录版本切换影响快照；同一版本对+镜头幂等。"""
    impact = await analyze_asset_impact(
        db,
        project_id=project_id,
        asset_type=asset_type,
        asset_id=asset_id,
        from_version_id=from_version_id,
        to_version_id=to_version_id,
    )
    created: list[AssetVersionImpactRef] = []
    for shot in impact.shots:
        stmt = select(AssetVersionImpactRef).where(
            AssetVersionImpactRef.from_version_id == from_version_id
            if from_version_id is not None
            else AssetVersionImpactRef.from_version_id.is_(None),
            AssetVersionImpactRef.to_version_id == to_version_id
            if to_version_id is not None
            else AssetVersionImpactRef.to_version_id.is_(None),
            AssetVersionImpactRef.shot_id == shot.shot_id,
        )
        existing = (await db.execute(stmt.limit(1))).scalars().first()
        if existing is not None:
            continue
        row = AssetVersionImpactRef(
            project_id=project_id,
            asset_type=asset_type,
            asset_id=asset_id,
            from_version_id=from_version_id,
            to_version_id=to_version_id,
            shot_id=shot.shot_id,
            chapter_id=shot.chapter_id,
            certainty=shot.certainty,
            reference_kind=shot.reference_kind,
            had_video=shot.has_video,
            created_by=created_by,
        )
        db.add(row)
        created.append(row)
    await db.flush()
    return created


async def list_impact_refs(
    db: AsyncSession,
    *,
    project_id: str,
    asset_type: str,
    asset_id: str,
) -> list[AssetVersionImpactRefRead]:
    rows = (
        await db.execute(
            select(AssetVersionImpactRef)
            .where(
                AssetVersionImpactRef.project_id == project_id,
                AssetVersionImpactRef.asset_type == normalize_asset_type(asset_type),
                AssetVersionImpactRef.asset_id == asset_id,
            )
            .order_by(AssetVersionImpactRef.id.desc())
        )
    ).scalars().all()
    return [AssetVersionImpactRefRead.model_validate(item) for item in rows]


__all__ = [
    "analyze_asset_impact",
    "list_impact_refs",
    "record_version_impact",
]
