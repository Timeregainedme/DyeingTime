"""P5 / C10：分镜规划草稿、审核与正式 Shot 写入。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.task_manager import DeliveryMode, SqlAlchemyTaskStore, TaskManager
from app.models.llm import ModelCategoryKey
from app.models.studio import (
    AssetVersion,
    CameraAngle,
    CameraMovement,
    CameraShotType,
    Chapter,
    Character,
    Costume,
    DialogueLineMode,
    Project,
    ProjectCostumeLink,
    ProjectPropLink,
    ProjectSceneLink,
    Prop,
    Scene,
    SceneGroup,
    ScriptDocument,
    ScriptDocumentVersion,
    ScriptParseRun,
    Shot,
    ShotAssetVersion,
    ShotCharacterLink,
    ShotDialogLine,
    ShotPlanAppliedShot,
    ShotPlanCandidate,
    ShotPlanDraft,
    ShotStatus,
)
from app.models.task import GenerationTask, GenerationTaskStatus
from app.models.task_links import GenerationTaskLink
from app.schemas.studio.shot_plans import (
    ShotAssetVersionRead,
    ShotPlanCandidateCreate,
    ShotPlanCandidateRead,
    ShotPlanCandidateUpdate,
    ShotPlanDraftRead,
    ShotPlanPayload,
    ShotPlanRequest,
    ShotPlanStatsRead,
)
from app.services.llm.resolver import get_default_model_by_category
from app.services.studio.asset_versions import asset_belongs_to_project
from app.services.studio.shot_details import build_default_shot_detail
from app.services.studio.shot_plan_runner import PROMPT_VERSION, run_shot_plan_task

SHOT_PLAN_TASK_KIND = "shot_plan"
SHOT_PLAN_RELATION_TYPE = "shot_plan"
_ACTIVE_TASK_STATUSES = (
    GenerationTaskStatus.pending,
    GenerationTaskStatus.running,
    GenerationTaskStatus.streaming,
)


class _CreateOnlyTask:
    """仅用于 TaskManager.create 的占位 task。"""

    async def run(self, *args: object, **kwargs: object):
        return None

    async def status(self) -> dict[str, object]:
        return {}

    async def is_done(self) -> bool:
        return False

    async def get_result(self) -> object:
        return None


def _candidate_read(candidate: ShotPlanCandidate) -> ShotPlanCandidateRead:
    return ShotPlanCandidateRead(
        id=candidate.id,
        draft_id=candidate.draft_id,
        order_index=candidate.order_index,
        scene_group_id=candidate.scene_group_id,
        candidate_key=candidate.candidate_key,
        payload=candidate.payload or {},
        issues=list(candidate.issues or []),
        review_status=candidate.review_status,
        source_key=candidate.source_key,
        created_at=candidate.created_at,
    )


def draft_to_read(draft: ShotPlanDraft) -> ShotPlanDraftRead:
    return ShotPlanDraftRead(
        id=draft.id,
        project_id=draft.project_id,
        chapter_id=draft.chapter_id,
        source_parse_run_id=draft.source_parse_run_id,
        source_script_version_id=draft.source_script_version_id,
        target_duration=draft.target_duration,
        pace=draft.pace,
        status=draft.status,
        model_id=draft.model_id,
        model_name=draft.model_name,
        provider_name=draft.provider_name,
        prompt_version=draft.prompt_version,
        prompt_hash=draft.prompt_hash,
        task_id=draft.task_id,
        error=draft.error,
        scene_group_snapshot=list(draft.scene_group_snapshot or []),
        coverage=dict(draft.coverage or {}),
        applied_at=draft.applied_at,
        applied_by=draft.applied_by,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
        candidates=[_candidate_read(item) for item in draft.candidates],
    )


async def _load_draft(db: AsyncSession, draft_id: str) -> ShotPlanDraft:
    draft = await db.scalar(
        select(ShotPlanDraft)
        .options(selectinload(ShotPlanDraft.candidates))
        .where(ShotPlanDraft.id == draft_id)
        .execution_options(populate_existing=True)
    )
    if draft is None:
        raise ValueError(f"分镜规划草稿不存在：{draft_id}")
    return draft


async def _episode_document_and_version(
    db: AsyncSession, *, chapter_id: str
) -> tuple[ScriptDocument | None, ScriptDocumentVersion | None]:
    document = (
        await db.execute(
            select(ScriptDocument)
            .where(
                ScriptDocument.chapter_id == chapter_id,
                ScriptDocument.doc_type == "episode",
            )
            .order_by(ScriptDocument.updated_at.desc())
            .limit(1)
        )
    ).scalars().first()
    if document is None:
        return None, None
    version_id = document.active_version_id or document.current_version_id
    return (
        document,
        (await db.get(ScriptDocumentVersion, version_id)) if version_id else None,
    )


async def _latest_parse_run(
    db: AsyncSession, *, document: ScriptDocument | None
) -> ScriptParseRun | None:
    if document is None:
        return None
    return (
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


async def _find_active_task(db: AsyncSession, *, chapter_id: str) -> GenerationTask | None:
    return (
        await db.execute(
            select(GenerationTask)
            .join(GenerationTaskLink, GenerationTaskLink.task_id == GenerationTask.id)
            .where(
                GenerationTaskLink.relation_type == SHOT_PLAN_RELATION_TYPE,
                GenerationTaskLink.relation_entity_id == chapter_id,
                GenerationTask.status.in_(_ACTIVE_TASK_STATUSES),
            )
            .limit(1)
        )
    ).scalars().first()


async def create_shot_plan(
    db: AsyncSession,
    *,
    chapter: Chapter,
    project: Project,
    body: ShotPlanRequest,
    created_by: int | None = None,
) -> tuple[ShotPlanDraft, bool]:
    groups = (
        await db.execute(select(SceneGroup).where(SceneGroup.chapter_id == chapter.id))
    ).scalars().all()
    if not groups:
        raise ValueError("剧集还没有正式场次，请先创建或从 P3 场次建议导入")
    document, version = await _episode_document_and_version(db, chapter_id=chapter.id)
    if version is None:
        raise ValueError("当前剧集没有可用剧本版本")
    parse_run = await _latest_parse_run(db, document=document)

    active_task = await _find_active_task(db, chapter_id=chapter.id)
    if active_task is not None:
        draft = (
            await db.execute(
                select(ShotPlanDraft)
                .options(selectinload(ShotPlanDraft.candidates))
                .where(ShotPlanDraft.task_id == active_task.id)
                .limit(1)
            )
        ).scalars().first()
        if draft is not None:
            return draft, True

    if not body.force:
        existing = (
            await db.execute(
                select(ShotPlanDraft)
                .options(selectinload(ShotPlanDraft.candidates))
                .where(
                    ShotPlanDraft.chapter_id == chapter.id,
                    ShotPlanDraft.source_script_version_id == version.id,
                    ShotPlanDraft.target_duration == body.target_duration,
                    ShotPlanDraft.pace == body.pace,
                    ShotPlanDraft.status.in_(["draft", "generating", "review_required", "confirmed"]),
                )
                .order_by(ShotPlanDraft.created_at.desc())
                .limit(1)
            )
        ).scalars().first()
        if existing is not None:
            return existing, True

    model = await get_default_model_by_category(db, ModelCategoryKey.text)
    draft = ShotPlanDraft(
        id=str(uuid.uuid4()),
        project_id=project.id,
        chapter_id=chapter.id,
        source_parse_run_id=parse_run.id if parse_run else None,
        source_script_version_id=version.id,
        target_duration=body.target_duration,
        pace=body.pace,
        status="draft",
        model_id=model.id if model else None,
        prompt_version=PROMPT_VERSION,
        scene_group_snapshot=[],
        coverage={},
        created_by=created_by,
    )
    db.add(draft)
    await db.flush()

    store = SqlAlchemyTaskStore(db)
    tm = TaskManager(store=store, strategies={})
    task = await tm.create(
        task=_CreateOnlyTask(),
        mode=DeliveryMode.async_polling,
        task_kind=SHOT_PLAN_TASK_KIND,
        run_args={"draft_id": draft.id},
        workspace_id=project.workspace_id,
    )
    draft.task_id = task.id
    db.add(
        GenerationTaskLink(
            task_id=task.id,
            resource_type="text",
            relation_type=SHOT_PLAN_RELATION_TYPE,
            relation_entity_id=chapter.id,
        )
    )
    await db.flush()
    # 先提交再入队：worker 是独立进程，若在事务提交前消费到任务，
    # 会查不到 task/draft 而静默成功，任务永久停在 pending。
    await db.commit()

    from app.tasks.execute_task import enqueue_task_execution

    enqueue_task_execution(task.id)
    return await _load_draft(db, draft.id), False


async def list_drafts(db: AsyncSession, *, chapter_id: str) -> list[ShotPlanDraftRead]:
    rows = (
        await db.execute(
            select(ShotPlanDraft)
            .options(selectinload(ShotPlanDraft.candidates))
            .where(ShotPlanDraft.chapter_id == chapter_id)
            .order_by(ShotPlanDraft.created_at.desc())
        )
    ).scalars().all()
    return [draft_to_read(item) for item in rows]


async def get_draft(db: AsyncSession, *, draft_id: str) -> ShotPlanDraftRead:
    return draft_to_read(await _load_draft(db, draft_id))


async def get_stats(db: AsyncSession, *, chapter_id: str) -> ShotPlanStatsRead:
    draft = (
        await db.execute(
            select(ShotPlanDraft)
            .options(selectinload(ShotPlanDraft.candidates))
            .where(ShotPlanDraft.chapter_id == chapter_id)
            .order_by(ShotPlanDraft.created_at.desc())
            .limit(1)
        )
    ).scalars().first()
    if draft is None:
        return ShotPlanStatsRead(chapter_id=chapter_id)
    durations = [
        int((item.payload or {}).get("duration") or 0)
        for item in draft.candidates
        if item.review_status != "ignored"
    ]
    blocking = sum(
        1
        for item in draft.candidates
        for issue in (item.issues or [])
        if issue.get("severity") == "blocking"
    )
    warnings = sum(
        1
        for item in draft.candidates
        for issue in (item.issues or [])
        if issue.get("severity") != "blocking"
    )
    coverage = draft.coverage or {}
    return ShotPlanStatsRead(
        chapter_id=chapter_id,
        latest_draft_id=draft.id,
        status=draft.status,
        target_duration=draft.target_duration,
        shot_count=len(durations),
        total_duration=sum(durations),
        min_duration=min(durations) if durations else None,
        max_duration=max(durations) if durations else None,
        coverage_ratio=float(coverage.get("coverage_ratio") or 0),
        blocking_issue_count=blocking,
        warning_count=warnings,
    )


async def update_candidate(
    db: AsyncSession,
    *,
    draft_id: str,
    candidate_id: str,
    body: ShotPlanCandidateUpdate,
) -> ShotPlanCandidateRead:
    draft = await _load_draft(db, draft_id)
    if draft.applied_at is not None:
        raise ValueError("规划已应用，不能继续修改候选")
    candidate = next((item for item in draft.candidates if item.id == candidate_id), None)
    if candidate is None:
        raise ValueError("镜头候选不存在")
    if body.payload is not None:
        candidate.payload = body.payload
        candidate.review_status = body.review_status or "edited"
    if body.order_index is not None:
        candidate.order_index = body.order_index
    if body.scene_group_id is not None:
        group = await db.get(SceneGroup, body.scene_group_id)
        if group is None or group.chapter_id != draft.chapter_id:
            raise ValueError("场次不属于当前剧集")
        candidate.scene_group_id = body.scene_group_id
        candidate.payload = {**candidate.payload, "scene_group_id": body.scene_group_id}
    if body.review_status is not None:
        if body.review_status not in {"pending", "edited", "accepted", "ignored"}:
            raise ValueError("review_status 只支持 pending/edited/accepted/ignored")
        candidate.review_status = body.review_status
    await db.flush()
    return _candidate_read(candidate)


async def add_candidate(
    db: AsyncSession,
    *,
    draft_id: str,
    body: ShotPlanCandidateCreate,
) -> ShotPlanCandidateRead:
    draft = await _load_draft(db, draft_id)
    if draft.applied_at is not None:
        raise ValueError("规划已应用，不能新增候选")
    groups = (
        await db.execute(
            select(SceneGroup)
            .where(SceneGroup.chapter_id == draft.chapter_id)
            .order_by(SceneGroup.index.asc())
        )
    ).scalars().all()
    group_id = body.scene_group_id or (groups[0].id if groups else None)
    payload = body.payload or {
        "title": "新增镜头",
        "script_excerpt": "",
        "duration": 5,
        "camera_shot": "MS",
        "angle": "EYE_LEVEL",
        "movement": "STATIC",
        "action_beats": [],
        "atmosphere": "",
        "description": "",
        "video_prompt": "",
        "characters": [],
        "scene": None,
        "props": [],
        "costume": None,
        "dialogues": [],
        "issues": [],
    }
    if group_id:
        payload = {**payload, "scene_group_id": group_id}
    max_order = max((item.order_index for item in draft.candidates), default=0)
    candidate = ShotPlanCandidate(
        id=str(uuid.uuid4()),
        draft_id=draft.id,
        order_index=max_order + 1,
        scene_group_id=group_id,
        candidate_key=f"manual:{uuid.uuid4().hex}",
        payload=payload,
        issues=[],
        review_status="edited",
    )
    db.add(candidate)
    await db.flush()
    return _candidate_read(candidate)


async def duplicate_candidate(
    db: AsyncSession, *, draft_id: str, candidate_id: str
) -> ShotPlanCandidateRead:
    draft = await _load_draft(db, draft_id)
    if draft.applied_at is not None:
        raise ValueError("规划已应用，不能复制候选")
    source = next((item for item in draft.candidates if item.id == candidate_id), None)
    if source is None:
        raise ValueError("镜头候选不存在")
    max_order = max((item.order_index for item in draft.candidates), default=0)
    candidate = ShotPlanCandidate(
        id=str(uuid.uuid4()),
        draft_id=draft.id,
        order_index=max_order + 1,
        scene_group_id=source.scene_group_id,
        candidate_key=f"copy:{uuid.uuid4().hex}",
        payload={**(source.payload or {}), "title": f"{source.payload.get('title') or '镜头'}（副本）"},
        issues=list(source.issues or []),
        review_status="edited",
        source_key=source.source_key,
    )
    db.add(candidate)
    await db.flush()
    return _candidate_read(candidate)


async def delete_candidate(
    db: AsyncSession, *, draft_id: str, candidate_id: str
) -> None:
    draft = await _load_draft(db, draft_id)
    if draft.applied_at is not None:
        raise ValueError("规划已应用，不能删除候选")
    candidate = next((item for item in draft.candidates if item.id == candidate_id), None)
    if candidate is None:
        raise ValueError("镜头候选不存在")
    await db.delete(candidate)
    await db.flush()


async def merge_candidates(
    db: AsyncSession, *, draft_id: str, source_id: str, target_id: str
) -> ShotPlanCandidateRead:
    draft = await _load_draft(db, draft_id)
    if draft.applied_at is not None:
        raise ValueError("规划已应用，不能合并候选")
    source = next((item for item in draft.candidates if item.id == source_id), None)
    target = next((item for item in draft.candidates if item.id == target_id), None)
    if source is None or target is None or source.id == target.id:
        raise ValueError("合并候选不存在或相同")
    if source.scene_group_id and source.scene_group_id != target.scene_group_id:
        raise ValueError("只能合并同一场次内的镜头候选")
    source_payload = dict(source.payload or {})
    target_payload = dict(target.payload or {})
    merged = dict(target_payload)
    merged["script_excerpt"] = "\n".join(
        item for item in [target_payload.get("script_excerpt"), source_payload.get("script_excerpt")] if item
    )
    merged["action_beats"] = list(target_payload.get("action_beats") or []) + list(
        source_payload.get("action_beats") or []
    )
    merged["dialogues"] = list(target_payload.get("dialogues") or []) + list(
        source_payload.get("dialogues") or []
    )
    merged["duration"] = int(target_payload.get("duration") or 0) + int(
        source_payload.get("duration") or 0
    )
    merged["issues"] = list(target_payload.get("issues") or []) + list(
        source_payload.get("issues") or []
    )
    target.payload = merged
    target.review_status = "edited"
    source.review_status = "ignored"
    await db.flush()
    return _candidate_read(target)


async def reorder_candidates(
    db: AsyncSession,
    *,
    draft_id: str,
    candidate_ids: list[str],
) -> ShotPlanDraftRead:
    draft = await _load_draft(db, draft_id)
    if draft.applied_at is not None:
        raise ValueError("规划已应用，不能调整顺序")
    if set(candidate_ids) != {item.id for item in draft.candidates}:
        raise ValueError("排序必须包含该草稿全部镜头候选")
    by_id = {item.id: item for item in draft.candidates}
    for index, candidate_id in enumerate(candidate_ids, start=1):
        by_id[candidate_id].order_index = -index
    await db.flush()
    for index, candidate_id in enumerate(candidate_ids, start=1):
        by_id[candidate_id].order_index = index
    await db.flush()
    return draft_to_read(await _load_draft(db, draft_id))


def _version_for_asset(
    version: AssetVersion | None, *, asset_type: str, asset_id: str
) -> bool:
    return bool(version and version.asset_type == asset_type and version.asset_id == asset_id)


async def validate_candidate_payload(
    db: AsyncSession,
    *,
    draft: ShotPlanDraft,
    payload_data: dict[str, Any],
    project: Project,
) -> tuple[ShotPlanPayload, list[dict[str, str]]]:
    payload = ShotPlanPayload.model_validate(payload_data)
    issues: list[dict[str, str]] = []
    group = await db.get(SceneGroup, payload_data.get("scene_group_id")) if payload_data.get("scene_group_id") else None
    if group is None or group.chapter_id != draft.chapter_id:
        issues.append({"code": "unknown_scene_group", "message": "镜头未归属有效场次", "severity": "blocking"})
    minimum = int(project.video_duration_min or 4)
    maximum = int(project.video_duration_max or 15)
    if payload.duration < minimum or payload.duration > maximum:
        issues.append(
            {
                "code": "duration_out_of_range",
                "message": f"时长 {payload.duration}s 超出 {minimum}–{maximum}s",
                "severity": "blocking",
            }
        )
    for character_ref in payload.characters:
        character = await db.get(Character, character_ref.character_id)
        if character is None or character.project_id != project.id:
            issues.append({"code": "unknown_character", "message": f"角色不存在：{character_ref.character_id}", "severity": "blocking"})
            continue
        if character.identity_locked_at is None:
            issues.append({"code": "character_unlocked", "message": f"角色「{character.name}」视觉身份未锁定", "severity": "blocking"})
        # UI 清空版本时回落到角色当前身份/造型，避免正式 Shot 丢失版本选择。
        if not character_ref.identity_version_id and character.identity_version_id:
            character_ref.identity_version_id = character.identity_version_id
        if not character_ref.appearance_version_id:
            character_ref.appearance_version_id = (
                character.current_appearance_version_id or character.identity_version_id
            )
        if not character_ref.identity_version_id:
            issues.append({"code": "identity_version_missing", "message": f"角色「{character.name}」缺少身份版本", "severity": "blocking"})
        identity = await db.get(AssetVersion, character_ref.identity_version_id) if character_ref.identity_version_id else None
        if identity is not None and not _version_for_asset(identity, asset_type="character", asset_id=character.id):
            issues.append({"code": "asset_version_mismatch", "message": f"角色「{character.name}」身份版本不属于该角色", "severity": "blocking"})
        appearance = await db.get(AssetVersion, character_ref.appearance_version_id) if character_ref.appearance_version_id else None
        if appearance is not None and not _version_for_asset(appearance, asset_type="character", asset_id=character.id):
            issues.append({"code": "asset_version_mismatch", "message": f"角色「{character.name}」造型版本不属于该角色", "severity": "blocking"})
    for dialogue in payload.dialogues:
        if dialogue.line_mode == "DIALOGUE" and not dialogue.speaker_character_id:
            issues.append({"code": "unresolved_speaker", "message": "存在未绑定说话人的对白", "severity": "blocking"})
    for ref, asset_type in [
        (payload.scene, "scene"),
        *[(item, "prop") for item in payload.props],
        (payload.costume, "costume"),
    ]:
        if ref is None:
            continue
        if not await asset_belongs_to_project(
            db, asset_type=asset_type, asset_id=ref.asset_id, project_id=project.id
        ):
            issues.append({"code": "unknown_asset", "message": f"资产不存在或不属于项目：{ref.asset_id}", "severity": "blocking"})
            continue
        if not ref.asset_version_id:
            asset = await db.get({"scene": Scene, "prop": Prop, "costume": Costume}[asset_type], ref.asset_id)
            if asset is not None:
                ref.asset_version_id = getattr(asset, "current_version_id", None)
        if ref.asset_version_id:
            version = await db.get(AssetVersion, ref.asset_version_id)
            if version is not None and not _version_for_asset(version, asset_type=asset_type, asset_id=ref.asset_id):
                issues.append({"code": "asset_version_mismatch", "message": f"{asset_type} 版本不属于该资产", "severity": "blocking"})
    if payload.scene is None:
        issues.append({"code": "scene_asset_missing", "message": "镜头未指定场景资产", "severity": "warning"})
    return payload, issues


async def confirm_draft(
    db: AsyncSession,
    *,
    draft: ShotPlanDraft,
    append_to_existing: bool,
    applied_by: int | None = None,
) -> tuple[ShotPlanDraft, list[str], bool, list[str]]:
    """把已审核规划写成正式 Shot；默认仅追加，不覆盖旧镜头。"""
    if draft.applied_at is not None:
        shot_ids = [
            item.shot_id
            for item in (
                await db.execute(
                    select(ShotPlanAppliedShot).where(ShotPlanAppliedShot.draft_id == draft.id)
                )
            ).scalars().all()
        ]
        return draft, shot_ids, True, []
    if draft.status != "review_required":
        raise ValueError("规划尚未完成审核，不能应用")
    pending = [
        item for item in draft.candidates
        if item.review_status == "pending" and item.review_status != "ignored"
    ]
    if pending:
        raise ValueError(f"仍有 {len(pending)} 个镜头候选未审核")
    active_candidates = [
        item for item in draft.candidates if item.review_status not in {"ignored", "pending"}
    ]
    if not active_candidates:
        raise ValueError("没有可应用的镜头候选")
    groups = (
        await db.execute(
            select(SceneGroup).where(SceneGroup.chapter_id == draft.chapter_id).order_by(SceneGroup.index.asc())
        )
    ).scalars().all()
    used_group_ids = {str(item.scene_group_id) for item in active_candidates if item.scene_group_id}
    missing_groups = [item for item in groups if item.id not in used_group_ids]
    if missing_groups:
        raise ValueError(
            "以下场次没有镜头，不能确认："
            + "、".join(item.title or item.location or item.id for item in missing_groups)
        )

    project = await db.get(Project, draft.project_id)
    chapter = await db.get(Chapter, draft.chapter_id)
    if project is None or chapter is None:
        raise ValueError("项目或剧集不存在")
    existing_count = int(
        await db.scalar(select(func.count(Shot.id)).where(Shot.chapter_id == chapter.id)) or 0
    )
    if existing_count and not append_to_existing:
        raise ValueError("当前剧集已有镜头；本阶段禁止覆盖，请确认使用追加模式")
    next_index = int(
        await db.scalar(select(func.coalesce(func.max(Shot.index), 0)).where(Shot.chapter_id == chapter.id))
        or 0
    ) + 1
    warnings: list[str] = []
    shot_ids: list[str] = []
    now = datetime.now(UTC)
    for candidate in sorted(active_candidates, key=lambda item: item.order_index):
        payload, issues = await validate_candidate_payload(
            db,
            draft=draft,
            payload_data={**candidate.payload, "scene_group_id": candidate.scene_group_id},
            project=project,
        )
        blocking = [item for item in issues if item["severity"] == "blocking"]
        if blocking:
            raise ValueError(
                f"镜头「{payload.title}」仍有阻塞问题："
                + "；".join(item["message"] for item in blocking)
            )
        warnings.extend(item["message"] for item in issues if item["severity"] != "blocking")
        shot_id = str(uuid.uuid4())
        shot = Shot(
            id=shot_id,
            chapter_id=chapter.id,
            scene_group_id=candidate.scene_group_id,
            index=next_index,
            title=payload.title or f"镜头 {next_index}",
            script_excerpt=payload.script_excerpt,
            status=ShotStatus.ready,
            skip_extraction=True,
            last_extracted_at=now,
        )
        next_index += 1
        db.add(shot)
        detail = build_default_shot_detail(shot_id)
        detail.duration = payload.duration
        detail.camera_shot = CameraShotType(payload.camera_shot)
        detail.angle = CameraAngle(payload.angle)
        detail.movement = CameraMovement(payload.movement)
        detail.scene_id = payload.scene.asset_id if payload.scene else None
        detail.description = payload.description
        detail.action_beats = payload.action_beats
        detail.atmosphere = payload.atmosphere
        detail.video_prompt_draft = payload.video_prompt
        db.add(detail)
        # 先落 Shot/Detail，再写依赖 shot_id 的关联行。
        # MySQL 会立即校验外键，而 ORM 没有为这些关系声明 relationship，
        # 不 flush 时可能先插 ShotAssetVersion，触发 1452。
        await db.flush()

        for index, character_ref in enumerate(payload.characters):
            db.add(
                ShotCharacterLink(
                    shot_id=shot_id,
                    character_id=character_ref.character_id,
                    index=index,
                )
            )
            identity_id = character_ref.identity_version_id
            if identity_id:
                db.add(
                    ShotAssetVersion(
                        shot_id=shot_id,
                        asset_type="character",
                        asset_id=character_ref.character_id,
                        asset_version_id=identity_id,
                        role="character_identity",
                        slot=index,
                        source="plan",
                        created_at=now,
                    )
                )
            if character_ref.appearance_version_id:
                db.add(
                    ShotAssetVersion(
                        shot_id=shot_id,
                        asset_type="character",
                        asset_id=character_ref.character_id,
                        asset_version_id=character_ref.appearance_version_id,
                        role="character_appearance",
                        slot=index,
                        source="plan",
                        created_at=now,
                    )
                )
        if payload.scene is not None:
            scene_version_id = payload.scene.asset_version_id
            if not scene_version_id:
                scene_asset = await db.get(Scene, payload.scene.asset_id)
                scene_version_id = scene_asset.current_version_id if scene_asset else None
            db.add(
                ProjectSceneLink(
                    project_id=project.id,
                    shot_id=shot_id,
                    scene_id=payload.scene.asset_id,
                )
            )
            db.add(
                ShotAssetVersion(
                    shot_id=shot_id,
                    asset_type="scene",
                    asset_id=payload.scene.asset_id,
                    asset_version_id=scene_version_id,
                    role="scene",
                    source="plan",
                    created_at=now,
                )
            )
        for index, prop in enumerate(payload.props):
            prop_version_id = prop.asset_version_id
            if not prop_version_id:
                prop_asset = await db.get(Prop, prop.asset_id)
                prop_version_id = prop_asset.current_version_id if prop_asset else None
            db.add(
                ProjectPropLink(project_id=project.id, shot_id=shot_id, prop_id=prop.asset_id)
            )
            db.add(
                ShotAssetVersion(
                    shot_id=shot_id,
                    asset_type="prop",
                    asset_id=prop.asset_id,
                    asset_version_id=prop_version_id,
                    role="prop",
                    slot=index,
                    source="plan",
                    created_at=now,
                )
            )
        if payload.costume is not None:
            costume_version_id = payload.costume.asset_version_id
            if not costume_version_id:
                costume_asset = await db.get(Costume, payload.costume.asset_id)
                costume_version_id = costume_asset.current_version_id if costume_asset else None
            db.add(
                ProjectCostumeLink(
                    project_id=project.id,
                    shot_id=shot_id,
                    costume_id=payload.costume.asset_id,
                )
            )
            db.add(
                ShotAssetVersion(
                    shot_id=shot_id,
                    asset_type="costume",
                    asset_id=payload.costume.asset_id,
                    asset_version_id=costume_version_id,
                    role="costume",
                    source="plan",
                    created_at=now,
                )
            )
        for index, dialogue in enumerate(payload.dialogues):
            db.add(
                ShotDialogLine(
                    shot_detail_id=shot_id,
                    index=index,
                    text=dialogue.text,
                    line_mode=DialogueLineMode(dialogue.line_mode),
                    emotion=dialogue.emotion or None,
                    speaker_character_id=dialogue.speaker_character_id,
                    speaker_name=dialogue.speaker_name,
                )
            )
        db.add(
            ShotPlanAppliedShot(
                draft_id=draft.id,
                candidate_id=candidate.id,
                shot_id=shot_id,
                created_at=now,
            )
        )
        candidate.review_status = "accepted"
        shot_ids.append(shot_id)
    draft.status = "confirmed"
    draft.applied_at = now
    draft.applied_by = applied_by
    draft.coverage = {
        **(draft.coverage or {}),
        "applied_shot_count": len(shot_ids),
        "applied_at": now.isoformat(),
    }
    await db.flush()
    return await _load_draft(db, draft.id), shot_ids, False, warnings


async def list_shot_asset_versions(
    db: AsyncSession, *, shot_id: str
) -> list[ShotAssetVersionRead]:
    rows = (
        await db.execute(
            select(ShotAssetVersion)
            .where(ShotAssetVersion.shot_id == shot_id)
            .order_by(ShotAssetVersion.asset_type.asc(), ShotAssetVersion.slot.asc())
        )
    ).scalars().all()
    return [ShotAssetVersionRead.model_validate(item) for item in rows]


__all__ = [
    "SHOT_PLAN_TASK_KIND",
    "add_candidate",
    "confirm_draft",
    "create_shot_plan",
    "delete_candidate",
    "duplicate_candidate",
    "draft_to_read",
    "get_draft",
    "get_stats",
    "list_drafts",
    "list_shot_asset_versions",
    "merge_candidates",
    "reorder_candidates",
    "run_shot_plan_task",
    "update_candidate",
    "validate_candidate_payload",
]
