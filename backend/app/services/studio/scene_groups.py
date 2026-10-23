"""P5 / C9：正式场次 CRUD、排序、镜头归属与 P3 场次建议导入。"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.studio import (
    Chapter,
    ProjectSceneLink,
    Scene,
    SceneGroup,
    ScriptDocument,
    ScriptParseRun,
    Shot,
    ShotDetail,
)
from app.schemas.studio.scene_groups import (
    SceneBeatSuggestion,
    SceneGroupCreate,
    SceneGroupImportItem,
    SceneGroupImportRead,
    SceneGroupRead,
    SceneGroupSuggestionRead,
    SceneGroupUpdate,
    ShotOrderItem,
)
from app.schemas.studio.shots import ShotRead
from app.services.studio.asset_versions import asset_belongs_to_project
from app.services.studio.entity_thumbnails import resolve_thumbnails
from app.services.studio.shots import build_shot_reads

DOC_TYPE_EPISODE = "episode"


async def _chapter(db: AsyncSession, chapter_id: str) -> Chapter:
    chapter = await db.get(Chapter, chapter_id)
    if chapter is None:
        raise ValueError("章节不存在")
    return chapter


async def _scene_map(
    db: AsyncSession, *, project_id: str
) -> dict[str, Scene]:
    rows = (
        await db.execute(
            select(Scene)
            .join(ProjectSceneLink, ProjectSceneLink.scene_id == Scene.id)
            .where(ProjectSceneLink.project_id == project_id)
            .distinct()
        )
    ).scalars().all()
    return {item.name: item for item in rows}


async def _group_counts(
    db: AsyncSession, *, group_ids: list[str]
) -> dict[str, tuple[int, int]]:
    if not group_ids:
        return {}
    rows = (
        await db.execute(
            select(
                Shot.scene_group_id,
                func.count(Shot.id),
                func.coalesce(func.sum(ShotDetail.duration), 0),
            )
            .outerjoin(ShotDetail, ShotDetail.id == Shot.id)
            .where(Shot.scene_group_id.in_(group_ids))
            .group_by(Shot.scene_group_id)
        )
    ).all()
    return {
        str(group_id): (int(count or 0), int(duration or 0))
        for group_id, count, duration in rows
    }


async def group_to_read(
    db: AsyncSession, *, group: SceneGroup, scene: Scene | None = None, counts: tuple[int, int] | None = None
) -> SceneGroupRead:
    if scene is None and group.primary_scene_id:
        scene = await db.get(Scene, group.primary_scene_id)
    if counts is None:
        counts = (await _group_counts(db, group_ids=[group.id])).get(group.id, (0, 0))
    thumbnail = ""
    if scene is not None:
        # 场景缩略图走既有 SceneImage 解析；没有图时前端显示占位图。
        from app.models.studio import SceneImage

        thumbnails = await resolve_thumbnails(
            db,
            image_model=SceneImage,
            parent_field_name="scene_id",
            parent_ids=[scene.id],
        )
        thumbnail = thumbnails.get(scene.id, "")
    return SceneGroupRead(
        id=group.id,
        project_id=group.project_id,
        chapter_id=group.chapter_id,
        index=group.index,
        title=group.title,
        description=group.description,
        location=group.location,
        time_of_day=group.time_of_day,
        story_event=group.story_event,
        primary_scene_id=group.primary_scene_id,
        primary_scene_name=scene.name if scene else None,
        primary_scene_thumbnail=thumbnail,
        shot_count=counts[0],
        total_duration=counts[1],
        source_parse_run_id=group.source_parse_run_id,
        source_beat_key=group.source_beat_key,
        source_start_char=group.source_start_char,
        source_end_char=group.source_end_char,
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


async def list_groups(db: AsyncSession, *, chapter_id: str) -> list[SceneGroupRead]:
    groups = (
        await db.execute(
            select(SceneGroup)
            .where(SceneGroup.chapter_id == chapter_id)
            .order_by(SceneGroup.index.asc())
        )
    ).scalars().all()
    counts = await _group_counts(db, group_ids=[item.id for item in groups])
    scene_ids = {item.primary_scene_id for item in groups if item.primary_scene_id}
    scenes: dict[str, Scene] = {}
    if scene_ids:
        scenes = {
            item.id: item
            for item in (
                await db.execute(select(Scene).where(Scene.id.in_(scene_ids)))
            ).scalars().all()
        }
    return [
        await group_to_read(
            db,
            group=item,
            scene=scenes.get(item.primary_scene_id or ""),
            counts=counts.get(item.id, (0, 0)),
        )
        for item in groups
    ]


async def get_group(db: AsyncSession, *, group_id: str) -> SceneGroupRead:
    group = await db.get(SceneGroup, group_id)
    if group is None:
        raise ValueError("场次不存在")
    return await group_to_read(db, group=group)


async def _validate_scene(
    db: AsyncSession, *, project_id: str, scene_id: str | None
) -> None:
    if scene_id and not await asset_belongs_to_project(
        db, asset_type="scene", asset_id=scene_id, project_id=project_id
    ):
        raise ValueError("主场景资产不属于当前项目")


async def _shift_indexes_for_insert(
    db: AsyncSession, *, chapter_id: str, index: int
) -> None:
    groups = (
        await db.execute(
            select(SceneGroup)
            .where(SceneGroup.chapter_id == chapter_id, SceneGroup.index >= index)
            .order_by(SceneGroup.index.desc())
        )
    ).scalars().all()
    for item in groups:
        item.index += 1
    if groups:
        await db.flush()


async def create_group(
    db: AsyncSession,
    *,
    chapter_id: str,
    body: SceneGroupCreate,
    created_by: int | None = None,
) -> SceneGroupRead:
    chapter = await _chapter(db, chapter_id)
    await _validate_scene(db, project_id=chapter.project_id, scene_id=body.primary_scene_id)
    next_index = (
        await db.execute(
            select(func.max(SceneGroup.index)).where(SceneGroup.chapter_id == chapter_id)
        )
    ).scalar_one_or_none()
    index = body.index or int(next_index or 0) + 1
    if body.index:
        await _shift_indexes_for_insert(db, chapter_id=chapter_id, index=index)
    group = SceneGroup(
        id=str(uuid.uuid4()),
        project_id=chapter.project_id,
        chapter_id=chapter_id,
        index=index,
        title=body.title.strip() or f"场次 {index}",
        description=body.description or "",
        location=body.location or "",
        time_of_day=body.time_of_day or "",
        story_event=body.story_event or "",
        primary_scene_id=body.primary_scene_id,
        created_by=created_by,
    )
    db.add(group)
    await db.flush()
    await db.refresh(group)
    return await group_to_read(db, group=group)


async def update_group(
    db: AsyncSession,
    *,
    group_id: str,
    body: SceneGroupUpdate,
) -> SceneGroupRead:
    group = await db.get(SceneGroup, group_id)
    if group is None:
        raise ValueError("场次不存在")
    data = body.model_dump(exclude_unset=True)
    if "primary_scene_id" in data:
        await _validate_scene(
            db, project_id=group.project_id, scene_id=data["primary_scene_id"]
        )
    if "index" in data and data["index"] is not None and data["index"] != group.index:
        target = int(data["index"])
        old_index = group.index
        # 先把自身移出唯一约束范围，避免移动时与其它场次临时撞 index。
        group.index = -1
        await db.flush()
        if target < old_index:
            rows = (
                await db.execute(
                    select(SceneGroup)
                    .where(
                        SceneGroup.chapter_id == group.chapter_id,
                        SceneGroup.index >= target,
                        SceneGroup.id != group.id,
                    )
                    .order_by(SceneGroup.index.desc())
                )
            ).scalars().all()
            for item in rows:
                item.index += 1
            group.index = target
        else:
            rows = (
                await db.execute(
                    select(SceneGroup)
                    .where(
                        SceneGroup.chapter_id == group.chapter_id,
                        SceneGroup.index > old_index,
                        SceneGroup.index <= target,
                        SceneGroup.id != group.id,
                    )
                    .order_by(SceneGroup.index.asc())
                )
            ).scalars().all()
            for item in rows:
                item.index -= 1
            group.index = target
        await db.flush()
    for key in (
        "title",
        "description",
        "location",
        "time_of_day",
        "story_event",
        "primary_scene_id",
    ):
        if key in data:
            setattr(group, key, data[key])
    await db.flush()
    await db.refresh(group)
    return await group_to_read(db, group=group)


async def delete_group(db: AsyncSession, *, group_id: str) -> None:
    group = await db.get(SceneGroup, group_id)
    if group is None:
        return
    count = int(
        await db.scalar(select(func.count(Shot.id)).where(Shot.scene_group_id == group_id))
        or 0
    )
    if count:
        raise ValueError("场次内仍有镜头，请先移动或删除镜头")
    chapter_id = group.chapter_id
    await db.delete(group)
    await db.flush()
    rows = (
        await db.execute(
            select(SceneGroup)
            .where(SceneGroup.chapter_id == chapter_id)
            .order_by(SceneGroup.index.asc())
        )
    ).scalars().all()
    for index, item in enumerate(rows, start=1):
        item.index = -index
    await db.flush()
    for index, item in enumerate(rows, start=1):
        item.index = index
    await db.flush()


async def reorder_groups(
    db: AsyncSession, *, chapter_id: str, group_ids: list[str]
) -> list[SceneGroupRead]:
    rows = (
        await db.execute(select(SceneGroup).where(SceneGroup.chapter_id == chapter_id))
    ).scalars().all()
    if set(group_ids) != {item.id for item in rows}:
        raise ValueError("排序必须包含该章节全部场次，且不能包含其它章节场次")
    by_id = {item.id: item for item in rows}
    for index, group_id in enumerate(group_ids, start=1):
        by_id[group_id].index = -index
    await db.flush()
    for index, group_id in enumerate(group_ids, start=1):
        by_id[group_id].index = index
    await db.flush()
    return await list_groups(db, chapter_id=chapter_id)


async def _validate_group_for_chapter(
    db: AsyncSession, *, group_id: str | None, chapter_id: str
) -> None:
    if group_id is None:
        return
    group = await db.get(SceneGroup, group_id)
    if group is None or group.chapter_id != chapter_id:
        raise ValueError("场次不属于当前剧集")


async def reorder_chapter_shots(
    db: AsyncSession,
    *,
    chapter_id: str,
    items: list[ShotOrderItem],
) -> list[ShotRead]:
    chapter = await _chapter(db, chapter_id)
    all_shots = (
        await db.execute(
            select(Shot).where(Shot.chapter_id == chapter_id).order_by(Shot.index.asc())
        )
    ).scalars().all()
    by_id = {item.id: item for item in all_shots}
    ordered_ids = [item.shot_id for item in items]
    if len(set(ordered_ids)) != len(ordered_ids):
        raise ValueError("镜头顺序中存在重复镜头")
    if any(shot_id not in by_id for shot_id in ordered_ids):
        raise ValueError("排序包含不属于当前剧集的镜头")
    # 未列出的镜头追加到末尾，保持存量镜头不丢失。
    ordered_ids.extend(item.id for item in all_shots if item.id not in ordered_ids)
    item_map = {item.shot_id: item for item in items}
    for shot_id in ordered_ids:
        shot = by_id[shot_id]
        item = item_map.get(shot_id)
        if item is not None:
            await _validate_group_for_chapter(
                db, group_id=item.scene_group_id, chapter_id=chapter_id
            )
            shot.scene_group_id = item.scene_group_id
    for index, shot_id in enumerate(ordered_ids, start=1):
        by_id[shot_id].index = -index
    await db.flush()
    for index, shot_id in enumerate(ordered_ids, start=1):
        by_id[shot_id].index = index
    await db.flush()
    # 触发章节项目校验，避免空章节被静默当作成功。
    _ = chapter
    return await build_shot_reads(db, shots=[by_id[shot_id] for shot_id in ordered_ids])


async def list_group_shots(db: AsyncSession, *, group_id: str) -> list[ShotRead]:
    shots = (
        await db.execute(
            select(Shot).where(Shot.scene_group_id == group_id).order_by(Shot.index.asc())
        )
    ).scalars().all()
    return await build_shot_reads(db, shots=list(shots))


async def _latest_episode_run(
    db: AsyncSession, *, chapter_id: str, parse_run_id: str | None = None
) -> tuple[ScriptParseRun | None, ScriptDocument | None]:
    document = (
        await db.execute(
            select(ScriptDocument)
            .where(
                ScriptDocument.chapter_id == chapter_id,
                ScriptDocument.doc_type == DOC_TYPE_EPISODE,
            )
            .order_by(ScriptDocument.updated_at.desc())
            .limit(1)
        )
    ).scalars().first()
    if parse_run_id:
        run = await db.get(ScriptParseRun, parse_run_id)
        if run is None or document is None or run.document_id != document.id:
            raise ValueError("解析运行不属于当前剧集")
        return run, document
    if document is None:
        return None, None
    run = (
        await db.execute(
            select(ScriptParseRun)
            .where(
                ScriptParseRun.document_id == document.id,
                ScriptParseRun.status.in_(["completed", "confirmed"]),
            )
            .order_by(ScriptParseRun.created_at.desc())
            .limit(1)
        )
    ).scalars().first()
    return run, document


def _beat_key(index: int) -> str:
    return f"beat:{index}"


def _beats_from_run(run: ScriptParseRun | None) -> list[dict[str, Any]]:
    if run is None:
        return []
    confirmed = run.confirmed_result or {}
    episode = confirmed.get("episode") if isinstance(confirmed, dict) else None
    if isinstance(episode, dict) and isinstance(episode.get("scene_beats"), list):
        return [item for item in episode["scene_beats"] if isinstance(item, dict)]
    if isinstance(confirmed, dict) and isinstance(confirmed.get("scene_beats"), list):
        return [item for item in confirmed["scene_beats"] if isinstance(item, dict)]
    return []


def _beat_to_item(beat: dict[str, Any], *, index: int) -> dict[str, Any]:
    events = beat.get("events") or beat.get("major_events") or []
    if isinstance(events, list):
        story_event = "；".join(str(item) for item in events)
    else:
        story_event = str(events)
    return {
        "beat_key": str(beat.get("beat_key") or _beat_key(index)),
        "index": index,
        "title": str(beat.get("title") or f"场次 {index}"),
        "description": str(beat.get("description") or ""),
        "location": str(beat.get("location") or ""),
        "time_of_day": str(beat.get("time_of_day") or ""),
        "story_event": story_event,
        "source_start_char": beat.get("source_start_char") or beat.get("start_char"),
        "source_end_char": beat.get("source_end_char") or beat.get("end_char"),
        "evidence": beat.get("evidence") if isinstance(beat.get("evidence"), list) else [],
    }


async def get_scene_group_suggestions(
    db: AsyncSession,
    *,
    chapter_id: str,
    parse_run_id: str | None = None,
) -> SceneGroupSuggestionRead:
    chapter = await _chapter(db, chapter_id)
    run, document = await _latest_episode_run(
        db, chapter_id=chapter_id, parse_run_id=parse_run_id
    )
    warnings: list[str] = []
    if run is None:
        warnings.append("当前剧集还没有已完成的 P3 解析结果，请先在剧本页完成解析与确认。")
    beats = _beats_from_run(run)
    if run is not None and not beats:
        warnings.append("该解析结果没有场次建议（scene_beats），可以手工创建场次。")
    existing_keys = {
        item.source_beat_key
        for item in (
            await db.execute(
                select(SceneGroup).where(
                    SceneGroup.chapter_id == chapter_id,
                    SceneGroup.source_parse_run_id == (run.id if run else None),
                )
            )
        ).scalars().all()
        if item.source_beat_key
    } if run else set()
    scenes = await _scene_map(db, project_id=chapter.project_id)
    items: list[SceneBeatSuggestion] = []
    for index, beat in enumerate(beats, start=1):
        item = _beat_to_item(beat, index=index)
        location = item["location"]
        primary = next(
            (scene for name, scene in scenes.items() if location and name == location),
            None,
        )
        if primary is None and location:
            primary = next(
                (scene for name, scene in scenes.items() if location and name in location),
                None,
            )
        if primary is None and location:
            warnings.append(f"场次「{item['title']}」地点「{location}」未匹配到场景资产。")
        items.append(
            SceneBeatSuggestion(
                beat_key=item["beat_key"],
                index=item["index"],
                title=item["title"],
                description=item["description"],
                location=item["location"],
                time_of_day=item["time_of_day"],
                story_event=item["story_event"],
                primary_scene_id=primary.id if primary else None,
                primary_scene_name=primary.name if primary else "",
                source_start_char=item["source_start_char"],
                source_end_char=item["source_end_char"],
                already_imported=item["beat_key"] in existing_keys,
                evidence=item["evidence"],
            )
        )
    current_active = document.active_version_id if document else None
    return SceneGroupSuggestionRead(
        chapter_id=chapter_id,
        parse_run_id=run.id if run else None,
        source_script_version_id=run.version_id if run else None,
        current_active_version_id=current_active,
        script_version_changed=bool(
            run and document and current_active and current_active != run.version_id
        ),
        existing_group_count=len(
            (await db.execute(select(SceneGroup.id).where(SceneGroup.chapter_id == chapter_id))).scalars().all()
        ),
        items=items,
        warnings=warnings,
    )


async def import_scene_group_suggestions(
    db: AsyncSession,
    *,
    chapter_id: str,
    parse_run_id: str | None,
    items: list[SceneGroupImportItem] | None,
    skip_existing: bool = True,
    created_by: int | None = None,
) -> SceneGroupImportRead:
    chapter = await _chapter(db, chapter_id)
    run, document = await _latest_episode_run(
        db, chapter_id=chapter_id, parse_run_id=parse_run_id
    )
    if run is None:
        raise ValueError("没有可用于导入的已确认解析结果")
    beats = _beats_from_run(run)
    source_items = items
    if source_items is None:
        source_items = [
            SceneGroupImportItem(**_beat_to_item(beat, index=index))
            for index, beat in enumerate(beats, start=1)
        ]
    if not source_items:
        raise ValueError("没有可导入的场次建议")
    existing = (
        await db.execute(
            select(SceneGroup).where(
                SceneGroup.chapter_id == chapter_id,
                SceneGroup.source_parse_run_id == run.id,
            )
        )
    ).scalars().all()
    existing_keys = {item.source_beat_key for item in existing}
    max_index = (
        await db.execute(
            select(func.max(SceneGroup.index)).where(SceneGroup.chapter_id == chapter_id)
        )
    ).scalar_one_or_none()
    next_index = int(max_index or 0) + 1
    created: list[SceneGroup] = []
    skipped = 0
    warnings: list[str] = []
    scenes = await _scene_map(db, project_id=chapter.project_id)
    for index, item in enumerate(source_items, start=1):
        beat_key = (item.beat_key or _beat_key(index)).strip()
        if skip_existing and beat_key in existing_keys:
            skipped += 1
            continue
        primary_id = item.primary_scene_id
        if primary_id:
            await _validate_scene(db, project_id=chapter.project_id, scene_id=primary_id)
        else:
            primary = next(
                (scene for name, scene in scenes.items() if item.location and name == item.location),
                None,
            )
            primary_id = primary.id if primary else None
        if item.location and primary_id is None:
            warnings.append(f"场次「{item.title or beat_key}」未匹配到主场景资产，可稍后补选。")
        group = SceneGroup(
            id=str(uuid.uuid4()),
            project_id=chapter.project_id,
            chapter_id=chapter_id,
            index=next_index,
            title=item.title.strip() or f"场次 {next_index}",
            description=item.description or "",
            location=item.location or "",
            time_of_day=item.time_of_day or "",
            story_event=item.story_event or "",
            primary_scene_id=primary_id,
            source_parse_run_id=run.id,
            source_beat_key=beat_key,
            source_start_char=item.source_start_char,
            source_end_char=item.source_end_char,
            created_by=created_by,
        )
        db.add(group)
        await db.flush()
        await db.refresh(group)
        created.append(group)
        existing_keys.add(beat_key)
        next_index += 1
    reads = [await group_to_read(db, group=item) for item in created]
    _ = document
    return SceneGroupImportRead(created=reads, skipped=skipped, warnings=warnings)


__all__ = [
    "create_group",
    "delete_group",
    "get_group",
    "get_scene_group_suggestions",
    "import_scene_group_suggestions",
    "list_group_shots",
    "list_groups",
    "reorder_chapter_shots",
    "reorder_groups",
    "update_group",
]
