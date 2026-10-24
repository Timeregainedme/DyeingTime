"""创作工作台首页的聚合服务。

存在意义：
首页需要同时回答「有哪些项目」「哪个该继续做」「哪些任务在跑」「哪些视频待审」。
如果把这些查询放在前端逐个循环，会退化成 N+1 请求，并且四个数字来自不同时刻，
刷新时容易出现互相矛盾的快照。这里在服务端一次取齐，并把统计口径集中在一处。

口径约定（与页面文案一致）：
- `pending_review_shots`：存在已成功生成视频、但对应任务没有审核记录或仍为
  `unrated` 的镜头数。一个镜头有多条已生成视频时，只要存在未审核任务就计入。
- `running_tasks`：`pending / running / streaming`，跨全部任务类型。
- `adopted_videos`：`shots.generated_video_file_id` 非空的镜头数，即人工采纳结果。
- `pending_reviews` 只返回有真实业务入口的条目，没有可靠统计口径的项不虚构。

所有查询都以 `ctx.workspace_id` 为边界；不依赖调用方传入的项目 ID。
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import WorkspaceContext
from app.models.studio import (
    Chapter,
    Character,
    Costume,
    Project,
    ProjectCostumeLink,
    ProjectPropLink,
    ProjectSceneLink,
    Prop,
    Scene,
    Shot,
)
from app.models.studio_shot_plans import ShotPlanCandidate, ShotPlanDraft
from app.models.studio_video_reviews import ShotVideoReview
from app.models.task import GenerationTask
from app.models.task_links import GenerationTaskLink
from app.schemas.studio.dashboard import (
    DashboardChapterRead,
    DashboardProjectRead,
    DashboardRead,
    DashboardReviewRead,
    DashboardStatsRead,
    DashboardTaskRead,
)

# 与前端 stage 顺序一致：越靠前越应该先处理。
_ACTIVE_TASK_STATUSES = ("pending", "running", "streaming")
_RECENT_TASK_LIMIT = 8


def is_pending_review(
    *,
    file_id: str | None,
    adopted_file_id: str | None,
    review_status: str | None,
) -> bool:
    """判断一个已成功的视频任务是否仍需要人工审核。

    规则（与页面文案一致）：
    - 该任务的产物就是当前采纳版本 → 不需要审核（采纳本身就是确认）；
    - 没有审核记录或仍为 `unrated` → 需要审核；
    - `satisfied` / `unsatisfied` 都算已审核，未采纳的 `unsatisfied` 仍是用户已表态。
    """
    if file_id and adopted_file_id and str(file_id) == str(adopted_file_id):
        return False
    return review_status is None or review_status == "unrated"


async def _load_shots(
    db: AsyncSession, project_ids: list[str]
) -> list[tuple[str, str, str, str | None]]:
    """返回 (project_id, shot_id, status, generated_video_file_id) 列表。"""
    rows = (
        await db.execute(
            select(
                Chapter.project_id,
                Shot.id,
                Shot.status,
                Shot.generated_video_file_id,
            )
            .join(Chapter, Chapter.id == Shot.chapter_id)
            .where(Chapter.project_id.in_(project_ids))
        )
    ).all()
    return [(str(r[0]), str(r[1]), str(r[2]), r[3]) for r in rows]


async def _load_unreviewed_video_shots(
    db: AsyncSession,
    workspace_id: str,
    adopted_file_by_shot: dict[str, str],
) -> set[str]:
    """找出「视频已成功生成但该任务尚未人工审核」的镜头集合。

    已采纳版本不计入待审核：人工点过「采纳」本身就是一次确认。
    只有「不是当前采纳版本，且没有审核记录 / 仍为 unrated」的候选才需要审核。
    """
    rows = (
        await db.execute(
            select(
                GenerationTaskLink.relation_entity_id,
                GenerationTask.id,
                GenerationTaskLink.file_id,
                ShotVideoReview.id,
                ShotVideoReview.review_status,
            )
            .join(GenerationTask, GenerationTask.id == GenerationTaskLink.task_id)
            .outerjoin(ShotVideoReview, ShotVideoReview.task_id == GenerationTask.id)
            .where(
                GenerationTask.workspace_id == workspace_id,
                GenerationTask.task_kind == "video_generation",
                GenerationTask.status == "succeeded",
                GenerationTaskLink.resource_type == "video",
                GenerationTaskLink.relation_type == "video",
            )
        )
    ).all()
    pending: set[str] = set()
    for shot_id, _task_id, file_id, _review_id, review_status in rows:
        if is_pending_review(
            file_id=file_id,
            adopted_file_id=adopted_file_by_shot.get(str(shot_id)),
            review_status=review_status,
        ):
            pending.add(str(shot_id))
    return pending


async def _load_pending_shot_plan_counts(
    db: AsyncSession, project_ids: list[str]
) -> dict[str, int]:
    """按项目统计「分镜规划候选待审核」数量。"""
    rows = (
        await db.execute(
            select(ShotPlanDraft.project_id, func.count(ShotPlanCandidate.id))
            .join(ShotPlanCandidate, ShotPlanCandidate.draft_id == ShotPlanDraft.id)
            .where(
                ShotPlanDraft.project_id.in_(project_ids),
                ShotPlanCandidate.review_status == "pending",
            )
            .group_by(ShotPlanDraft.project_id)
        )
    ).all()
    return {str(project_id): int(count) for project_id, count in rows}


async def _resolve_task_projects(
    db: AsyncSession, task_ids: list[str]
) -> dict[str, str]:
    """把最近任务映射到项目 ID。

    任务表本身不持有项目归属（一次任务可能跨项目产出文件），归属只存在于
    `generation_task_links`。这里按关联类型分别解析：
    - video → 镜头 → 章节 → 项目
    - chapter_division / script_* / consistency_check → 章节 → 项目
    - *_image → 资产 → 所属项目（场景通过 project_scene_links）
    """
    if not task_ids:
        return {}

    links = (
        await db.execute(
            select(GenerationTaskLink).where(GenerationTaskLink.task_id.in_(task_ids))
        )
    ).scalars().all()

    shot_ids: set[str] = set()
    chapter_ids: set[str] = set()
    image_ids: dict[str, set[str]] = defaultdict(set)
    for link in links:
        relation = link.relation_type or ""
        if link.resource_type == "video" and relation == "video":
            shot_ids.add(link.relation_entity_id)
        elif link.resource_type == "task_link" and relation in {
            "chapter_division",
            "script_extraction",
            "script_optimization",
            "consistency_check",
        }:
            chapter_ids.add(link.relation_entity_id)
        elif relation.endswith("_image"):
            image_ids[relation].add(link.relation_entity_id)

    entity_to_project: dict[str, str] = {}

    if shot_ids:
        rows = (
            await db.execute(
                select(Shot.id, Chapter.project_id)
                .join(Chapter, Chapter.id == Shot.chapter_id)
                .where(Shot.id.in_(shot_ids))
            )
        ).all()
        entity_to_project.update({str(shot_id): str(pid) for shot_id, pid in rows})

    if chapter_ids:
        rows = (
            await db.execute(
                select(Chapter.id, Chapter.project_id).where(Chapter.id.in_(chapter_ids))
            )
        ).all()
        entity_to_project.update({str(cid): str(pid) for cid, pid in rows})

    # 资产 → 项目：角色/道具/服装直接挂在项目上，场景走关联表。
    for relation, ids in image_ids.items():
        if relation == "character_image":
            rows = (
                await db.execute(
                    select(Character.id, Character.project_id).where(Character.id.in_(ids))
                )
            ).all()
            entity_to_project.update({str(aid): str(pid) for aid, pid in rows})
        elif relation == "prop_image":
            rows = (
                await db.execute(
                    select(ProjectPropLink.prop_id, ProjectPropLink.project_id)
                    .where(ProjectPropLink.prop_id.in_(ids))
                    .distinct()
                )
            ).all()
            entity_to_project.update({str(aid): str(pid) for aid, pid in rows})
        elif relation == "costume_image":
            rows = (
                await db.execute(
                    select(ProjectCostumeLink.costume_id, ProjectCostumeLink.project_id)
                    .where(ProjectCostumeLink.costume_id.in_(ids))
                    .distinct()
                )
            ).all()
            entity_to_project.update({str(aid): str(pid) for aid, pid in rows})
        elif relation == "scene_image":
            rows = (
                await db.execute(
                    select(ProjectSceneLink.scene_id, ProjectSceneLink.project_id)
                    .where(ProjectSceneLink.scene_id.in_(ids))
                    .distinct()
                )
            ).all()
            entity_to_project.update({str(aid): str(pid) for aid, pid in rows})

    result: dict[str, str] = {}
    for link in links:
        project_id = entity_to_project.get(link.relation_entity_id)
        if project_id:
            result.setdefault(link.task_id, project_id)
    return result


def empty_dashboard(*, can_edit: bool) -> DashboardRead:
    """空工作区的零值快照。

    单独抽函数是为了让「没有任何项目」也走同一份必填字段集合；
    之前直接 `DashboardStatsRead()` 会在 schema 改成必填后返回 400。
    """
    return DashboardRead(
        can_edit=can_edit,
        stats=DashboardStatsRead(
            project_count=0,
            pending_review_shots=0,
            running_tasks=0,
            adopted_videos=0,
        ),
    )


async def build_dashboard(db: AsyncSession, *, ctx: WorkspaceContext) -> DashboardRead:
    """构建工作台首页快照（单次请求、单一时刻、工作区隔离）。"""
    workspace_id = ctx.workspace_id

    projects = (
        await db.execute(
            select(Project)
            .where(Project.workspace_id == workspace_id)
            .order_by(Project.updated_at.desc())
        )
    ).scalars().all()
    can_edit = ctx.role.value in {"editor", "admin", "owner"}
    if not projects:
        return empty_dashboard(can_edit=can_edit)

    project_ids = [project.id for project in projects]
    project_names = {project.id: project.name for project in projects}

    chapters = (
        await db.execute(
            select(Chapter)
            .where(Chapter.project_id.in_(project_ids))
            .order_by(Chapter.project_id, Chapter.index)
        )
    ).scalars().all()
    chapters_by_project: dict[str, list[Chapter]] = defaultdict(list)
    for chapter in chapters:
        chapters_by_project[chapter.project_id].append(chapter)

    # 章节的 `storyboard_count` 是写入时的冗余计数，历史数据可能与 shots 表不一致。
    # 首页阶段判断直接以真实镜头行数为准，避免出现「12/12 就绪却仍提示提取分镜」。
    chapter_shot_counts = {
        str(chapter_id): int(count)
        for chapter_id, count in (
            await db.execute(
                select(Shot.chapter_id, func.count(Shot.id))
                .join(Chapter, Chapter.id == Shot.chapter_id)
                .where(Chapter.project_id.in_(project_ids))
                .group_by(Shot.chapter_id)
            )
        ).all()
    }

    shots = await _load_shots(db, project_ids)
    adopted_file_by_shot = {
        shot_id: str(video_file_id).strip()
        for _project_id, shot_id, _status, video_file_id in shots
        if video_file_id and str(video_file_id).strip()
    }
    unreviewed_shot_ids = await _load_unreviewed_video_shots(
        db, workspace_id, adopted_file_by_shot
    )
    shot_plan_pending = await _load_pending_shot_plan_counts(db, project_ids)

    shot_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "total": 0,
            "pending": 0,
            "ready": 0,
            "review": 0,
            "adopted": 0,
        }
    )
    for project_id, shot_id, status, video_file_id in shots:
        bucket = shot_stats[project_id]
        bucket["total"] += 1
        if status == "ready":
            bucket["ready"] += 1
        else:
            bucket["pending"] += 1
        if video_file_id:
            bucket["adopted"] += 1
        if shot_id in unreviewed_shot_ids:
            bucket["review"] += 1

    active_tasks = (
        await db.execute(
            select(GenerationTask)
            .where(
                GenerationTask.workspace_id == workspace_id,
                GenerationTask.status.in_(_ACTIVE_TASK_STATUSES),
            )
            .order_by(GenerationTask.updated_at.desc())
        )
    ).scalars().all()
    active_task_projects = await _resolve_task_projects(
        db, [task.id for task in active_tasks]
    )
    running_by_project: dict[str, int] = defaultdict(int)
    for task in active_tasks:
        project_id = active_task_projects.get(task.id)
        if project_id:
            running_by_project[project_id] += 1

    recent_tasks = (
        await db.execute(
            select(GenerationTask)
            .where(GenerationTask.workspace_id == workspace_id)
            .order_by(GenerationTask.updated_at.desc())
            .limit(_RECENT_TASK_LIMIT)
        )
    ).scalars().all()
    recent_task_projects = await _resolve_task_projects(
        db, [task.id for task in recent_tasks]
    )

    project_items: list[DashboardProjectRead] = []
    pending_reviews: list[DashboardReviewRead] = []
    for project in projects:
        bucket = shot_stats[project.id]
        project_chapters = chapters_by_project.get(project.id, [])
        project_items.append(
            DashboardProjectRead(
                id=project.id,
                name=project.name,
                description=project.description or "",
                style=project.style or "",
                visual_style=str(project.visual_style or "现实"),
                updated_at=project.updated_at,
                chapter_count=len(project_chapters),
                chapters=[
                    DashboardChapterRead(
                        id=chapter.id,
                        index=chapter.index,
                        title=chapter.title,
                        has_raw_text=bool((chapter.raw_text or "").strip()),
                        storyboard_count=chapter_shot_counts.get(
                            chapter.id, chapter.storyboard_count or 0
                        ),
                        status=str(chapter.status or "draft"),
                    )
                    for chapter in project_chapters
                ],
                total_shots=bucket["total"],
                pending_shots=bucket["pending"],
                ready_shots=bucket["ready"],
                pending_review_shots=bucket["review"],
                adopted_videos=bucket["adopted"],
                running_tasks=running_by_project.get(project.id, 0),
            )
        )

        # 待审核事项：只按有真实入口的类别生成，数量为 0 的不展示。
        if bucket["review"] > 0:
            pending_reviews.append(
                DashboardReviewRead(
                    kind="video_candidate",
                    label=f"{project.name} · 视频候选待审核",
                    count=bucket["review"],
                    project_id=project.id,
                    project_name=project.name,
                    chapter_id=project_chapters[0].id if project_chapters else None,
                )
            )
        plan_pending = shot_plan_pending.get(project.id, 0)
        if plan_pending > 0:
            pending_reviews.append(
                DashboardReviewRead(
                    kind="shot_plan",
                    label=f"{project.name} · 分镜规划待审核",
                    count=plan_pending,
                    project_id=project.id,
                    project_name=project.name,
                    chapter_id=project_chapters[0].id if project_chapters else None,
                )
            )
        if bucket["pending"] > 0:
            pending_reviews.append(
                DashboardReviewRead(
                    kind="shot_extraction",
                    label=f"{project.name} · 镜头信息待确认",
                    count=bucket["pending"],
                    project_id=project.id,
                    project_name=project.name,
                    chapter_id=project_chapters[0].id if project_chapters else None,
                )
            )

    pending_reviews.sort(key=lambda item: item.count, reverse=True)

    stats = DashboardStatsRead(
        project_count=len(projects),
        pending_review_shots=sum(1 for shot in shots if shot[1] in unreviewed_shot_ids),
        running_tasks=len(active_tasks),
        adopted_videos=sum(1 for shot in shots if shot[3]),
    )

    return DashboardRead(
        can_edit=can_edit,
        stats=stats,
        projects=project_items,
        recent_tasks=[
            DashboardTaskRead(
                id=task.id,
                task_kind=task.task_kind,
                status=str(task.status),
                progress=task.progress or 0,
                created_at=_as_datetime(task.created_at),
                updated_at=_as_datetime(task.updated_at),
                project_id=recent_task_projects.get(task.id),
                project_name=project_names.get(recent_task_projects.get(task.id) or ""),
            )
            for task in recent_tasks
        ],
        pending_reviews=pending_reviews[:6],
    )


def _as_datetime(value: Any) -> datetime | None:
    """SQLAlchemy 可能返回字符串（历史 SQLite）或 datetime，这里统一收窄。"""
    return value if isinstance(value, datetime) else None


__all__ = ["build_dashboard", "empty_dashboard", "is_pending_review"]
