"""镜头运行时任务态聚合。"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.studio import Shot, ShotFrameImage
from app.models.task import GenerationTask, GenerationTaskStatus
from app.models.task_links import GenerationTaskLink
from app.schemas.studio.shots import ShotRuntimeSummaryRead


_ACTIVE_TASK_STATUSES = (
    GenerationTaskStatus.pending,
    GenerationTaskStatus.running,
    GenerationTaskStatus.streaming,
)


async def list_shot_runtime_summary_by_chapter(
    db: AsyncSession,
    *,
    chapter_id: str,
) -> list[ShotRuntimeSummaryRead]:
    shot_stmt = select(Shot.id).where(Shot.chapter_id == chapter_id).order_by(Shot.index.asc())
    shot_ids = [str(x) for x in (await db.execute(shot_stmt)).scalars().all()]
    if not shot_ids:
        return []

    frame_stmt = select(ShotFrameImage.id, ShotFrameImage.shot_detail_id).where(
        ShotFrameImage.shot_detail_id.in_(shot_ids)
    )
    frame_rows = (await db.execute(frame_stmt)).all()
    frame_id_to_shot_id = {str(frame_id): str(shot_id) for frame_id, shot_id in frame_rows}
    frame_ids = list(frame_id_to_shot_id.keys())
    frame_ids_filter = frame_ids if frame_ids else ["__never__"]

    link_stmt = (
        select(
            GenerationTaskLink.task_id,
            GenerationTaskLink.resource_type,
            GenerationTaskLink.relation_type,
            GenerationTaskLink.relation_entity_id,
        )
        .join(GenerationTask, GenerationTask.id == GenerationTaskLink.task_id)
        .where(GenerationTask.status.in_(_ACTIVE_TASK_STATUSES))
        .where(
            or_(
                GenerationTaskLink.relation_entity_id.in_(shot_ids),
                (
                    (GenerationTaskLink.relation_type == "shot_frame_image")
                    & GenerationTaskLink.relation_entity_id.in_(frame_ids_filter)
                ),
            )
        )
    )
    rows = (await db.execute(link_stmt)).all()

    task_ids_by_shot: dict[str, set[str]] = defaultdict(set)
    video_by_shot: dict[str, bool] = defaultdict(bool)
    prompt_by_shot: dict[str, bool] = defaultdict(bool)
    frame_by_shot: dict[str, bool] = defaultdict(bool)

    for task_id, resource_type, relation_type, relation_entity_id in rows:
        relation_entity_id = str(relation_entity_id)
        shot_id = relation_entity_id if relation_entity_id in shot_ids else frame_id_to_shot_id.get(relation_entity_id)
        if not shot_id:
            continue
        task_ids_by_shot[shot_id].add(str(task_id))
        if str(resource_type) == "video" or str(relation_type) == "video":
            video_by_shot[shot_id] = True
        elif str(resource_type) == "prompt":
            prompt_by_shot[shot_id] = True
        elif str(relation_type) == "shot_frame_image" or str(resource_type) == "image":
            frame_by_shot[shot_id] = True

    return [
        ShotRuntimeSummaryRead(
            shot_id=shot_id,
            has_active_tasks=bool(task_ids_by_shot.get(shot_id)),
            has_active_video_tasks=bool(video_by_shot.get(shot_id)),
            has_active_prompt_tasks=bool(prompt_by_shot.get(shot_id)),
            has_active_frame_tasks=bool(frame_by_shot.get(shot_id)),
            active_task_count=len(task_ids_by_shot.get(shot_id, set())),
        )
        for shot_id in shot_ids
    ]
