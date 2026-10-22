"""P3 / C6：解析运行创建、候选审核与确认落库。

解析任务只写候选；确认才创建/关联正式资产，并同步章节正文。
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.task_manager import DeliveryMode, SqlAlchemyTaskStore, TaskManager
from app.models.llm import ModelCategoryKey
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
    ScriptDocument,
    ScriptDocumentVersion,
    ScriptParseCandidate,
    ScriptParseRun,
)
from app.models.task import GenerationTask, GenerationTaskStatus
from app.models.task_links import GenerationTaskLink
from app.schemas.skills.script_parse import (
    ParsedCharacter,
    ParsedCostumeChange,
    ParsedDialogue,
    ParsedEpisode,
    ParsedIssue,
    ParsedProp,
    ParsedScene,
    ParsedSceneBeat,
)
from app.schemas.studio.script_parse import (
    ScriptParseCandidateCreate,
    ScriptParseCandidateRead,
    ScriptParseCandidateUpdate,
    ScriptParseRunRead,
)
from app.services.llm.resolver import get_default_model_by_category
from app.services.studio.script_documents import DOC_TYPE_EPISODE, DOC_TYPE_WORLD
from app.services.studio.script_parse_runner import PROMPT_VERSION

PARSE_RELATION_TYPE = "script_parse"
PARSE_TASK_KIND = "script_parse"
_ACTIVE_STATUSES = (
    GenerationTaskStatus.pending,
    GenerationTaskStatus.running,
    GenerationTaskStatus.streaming,
)
_CANDIDATE_VALIDATORS = {
    "character": ParsedCharacter,
    "scene": ParsedScene,
    "prop": ParsedProp,
    "costume_change": ParsedCostumeChange,
    "scene_beat": ParsedSceneBeat,
    "dialogue": ParsedDialogue,
    "episode": ParsedEpisode,
    "issue": ParsedIssue,
}


class _CreateOnlyTask:
    """仅用于 TaskManager.create 的占位 task，实际执行由 Celery executor 分派。"""

    async def run(self, *args: object, **kwargs: object):
        return None

    async def status(self) -> dict[str, object]:
        return {}

    async def is_done(self) -> bool:
        return False

    async def get_result(self) -> object:
        return None


def run_to_read(run: ScriptParseRun) -> ScriptParseRunRead:
    """把 ORM run 转为带候选的响应模型。"""
    return ScriptParseRunRead(
        id=run.id,
        document_id=run.document_id,
        version_id=run.version_id,
        worldbuilding_version_id=run.worldbuilding_version_id,
        task_id=run.task_id,
        status=run.status,
        progress=run.progress,
        model_id=run.model_id,
        model_name=run.model_name,
        provider_name=run.provider_name,
        prompt_version=run.prompt_version,
        prompt_hash=run.prompt_hash,
        chunk_count=run.chunk_count,
        failed_chunks=list(run.failed_chunks or []),
        error=run.error,
        started_at=run.started_at,
        finished_at=run.finished_at,
        confirmed_at=run.confirmed_at,
        confirmed_by=run.confirmed_by,
        applied_summary=run.applied_summary,
        confirmed_result=run.confirmed_result,
        candidates=[ScriptParseCandidateRead.model_validate(item) for item in run.candidates],
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


async def _load_run(db: AsyncSession, run_id: str) -> ScriptParseRun:
    """读取 run 并预加载候选，避免序列化时触发异步懒加载。"""
    run = await db.scalar(
        select(ScriptParseRun)
        .options(selectinload(ScriptParseRun.candidates))
        .where(ScriptParseRun.id == run_id)
        .execution_options(populate_existing=True)
    )
    if run is None:
        raise ValueError(f"解析运行不存在：{run_id}")
    return run


async def _find_active_task(
    db: AsyncSession, *, version_id: str
) -> GenerationTask | None:
    """查找同一剧本版本正在排队/执行的任务，用于点击幂等。"""
    return (
        await db.execute(
            select(GenerationTask)
            .join(GenerationTaskLink, GenerationTaskLink.task_id == GenerationTask.id)
            .where(
                GenerationTaskLink.relation_type == PARSE_RELATION_TYPE,
                GenerationTaskLink.relation_entity_id == version_id,
                GenerationTask.status.in_(_ACTIVE_STATUSES),
            )
            .limit(1)
        )
    ).scalars().first()


async def _find_reusable_run(
    db: AsyncSession, *, version_id: str, input_hash: str
) -> ScriptParseRun | None:
    """查找同输入的已完成 run；force=true 时跳过复用。"""
    return (
        await db.execute(
            select(ScriptParseRun)
            .options(selectinload(ScriptParseRun.candidates))
            .where(
                ScriptParseRun.version_id == version_id,
                ScriptParseRun.input_hash == input_hash,
                ScriptParseRun.status.in_(["completed", "confirmed"]),
            )
            .order_by(ScriptParseRun.created_at.desc())
            .limit(1)
        )
    ).scalars().first()


async def _active_worldbuilding_version(
    db: AsyncSession, *, project_id: str
) -> ScriptDocumentVersion | None:
    """读取项目当前生效的世界观版本；没有则返回 None。"""
    document = (
        await db.execute(
            select(ScriptDocument).where(
                ScriptDocument.project_id == project_id,
                ScriptDocument.doc_type == DOC_TYPE_WORLD,
                ScriptDocument.chapter_id.is_(None),
            )
        )
    ).scalars().first()
    if document is None or not document.active_version_id:
        return None
    return await db.get(ScriptDocumentVersion, document.active_version_id)


async def create_parse_run(
    db: AsyncSession,
    *,
    document: ScriptDocument,
    version: ScriptDocumentVersion,
    project: Project,
    model_id: str | None = None,
    force: bool = False,
) -> tuple[ScriptParseRun, bool]:
    """创建解析运行与异步任务；重复点击复用活动任务/同输入结果。"""
    if document.doc_type != DOC_TYPE_EPISODE:
        raise ValueError("只支持解析每集剧本；世界观文档作为上下文使用")
    # 候选版本也允许先解析；确认前不会同步章节正文。

    model = (
        await get_default_model_by_category(db, ModelCategoryKey.text)
        if model_id is None
        else None
    )
    resolved_model_id = model.id if model is not None else model_id
    world_version = await _active_worldbuilding_version(db, project_id=project.id)
    input_source = "|".join(
        [
            version.content_hash,
            world_version.content_hash if world_version else "",
            resolved_model_id or "",
            PROMPT_VERSION,
        ]
    )
    input_hash = hashlib.sha256(input_source.encode("utf-8")).hexdigest()

    active_task = await _find_active_task(db, version_id=version.id)
    if active_task is not None:
        run = (
            await db.execute(
                select(ScriptParseRun)
                .options(selectinload(ScriptParseRun.candidates))
                .where(ScriptParseRun.task_id == active_task.id)
                .limit(1)
            )
        ).scalars().first()
        if run is not None:
            return run, True

    if not force:
        reusable = await _find_reusable_run(
            db, version_id=version.id, input_hash=input_hash
        )
        if reusable is not None:
            return reusable, True

    run = ScriptParseRun(
        id=str(uuid.uuid4()),
        document_id=document.id,
        version_id=version.id,
        worldbuilding_version_id=world_version.id if world_version else None,
        status="pending",
        progress=0,
        model_id=resolved_model_id,
        model_name=model.name if model is not None else "",
        input_hash=input_hash,
        prompt_version=PROMPT_VERSION,
    )
    db.add(run)
    await db.flush()

    store = SqlAlchemyTaskStore(db)
    tm = TaskManager(store=store, strategies={})
    task = await tm.create(
        task=_CreateOnlyTask(),
        mode=DeliveryMode.async_polling,
        task_kind=PARSE_TASK_KIND,
        run_args={
            "run_id": run.id,
            "document_id": document.id,
            "version_id": version.id,
            "worldbuilding_version_id": world_version.id if world_version else None,
        },
        workspace_id=project.workspace_id,
    )
    run.task_id = task.id
    db.add(
        GenerationTaskLink(
            task_id=task.id,
            resource_type="text",
            relation_type=PARSE_RELATION_TYPE,
            relation_entity_id=version.id,
        )
    )
    await db.flush()

    from app.tasks.execute_task import enqueue_task_execution

    enqueue_task_execution(task.id)
    run = await _load_run(db, run.id)
    return run, False


async def list_document_runs(
    db: AsyncSession, *, document_id: str
) -> list[ScriptParseRunRead]:
    runs = (
        await db.execute(
            select(ScriptParseRun)
            .options(selectinload(ScriptParseRun.candidates))
            .where(ScriptParseRun.document_id == document_id)
            .order_by(ScriptParseRun.created_at.desc())
        )
    ).scalars().all()
    return [run_to_read(item) for item in runs]


async def get_run(db: AsyncSession, *, run_id: str) -> ScriptParseRunRead:
    return run_to_read(await _load_run(db, run_id))


async def update_candidate(
    db: AsyncSession,
    *,
    run_id: str,
    candidate_id: str,
    body: ScriptParseCandidateUpdate,
) -> ScriptParseCandidateRead:
    run = await _load_run(db, run_id)
    if run.confirmed_at is not None:
        raise ValueError("解析结果已确认，不能继续修改候选")
    candidate = next((item for item in run.candidates if item.id == candidate_id), None)
    if candidate is None:
        raise ValueError(f"候选不存在：{candidate_id}")
    if body.payload is not None:
        candidate.payload = body.payload
        if body.review_status is None:
            candidate.review_status = "edited"
    if body.review_status is not None:
        status_value = body.review_status.strip()
        if status_value not in {"pending", "edited", "accepted", "ignored"}:
            raise ValueError("review_status 只支持 pending / edited / accepted / ignored")
        candidate.review_status = status_value
    if "matched_entity_id" in body.model_fields_set:
        candidate.matched_entity_id = body.matched_entity_id or None
    if body.issue is not None:
        candidate.issue = body.issue[:255]
    await db.flush()
    return ScriptParseCandidateRead.model_validate(candidate)


async def add_candidate(
    db: AsyncSession,
    *,
    run_id: str,
    body: ScriptParseCandidateCreate,
) -> ScriptParseCandidateRead:
    """人工新增候选；payload 必须符合对应类型的 Schema。

    新增候选默认标记为 edited（已由人工创建），仍可在确认前继续修改或忽略。
    """
    run = await _load_run(db, run_id)
    if run.confirmed_at is not None:
        raise ValueError("解析结果已确认，不能新增候选")
    validator = _CANDIDATE_VALIDATORS.get(body.candidate_type)
    if validator is None:
        raise ValueError("不支持的候选类型")
    try:
        validated = validator.model_validate(body.payload)
    except Exception as exc:  # noqa: BLE001 - 返回可读的 409
        raise ValueError(f"候选内容不符合 {body.candidate_type} 结构：{exc}") from exc
    max_order = max((item.order_index for item in run.candidates), default=0)
    candidate = ScriptParseCandidate(
        id=str(uuid.uuid4()),
        run_id=run.id,
        candidate_type=body.candidate_type,
        candidate_key=f"manual:{uuid.uuid4().hex}",
        order_index=max_order + 1,
        payload=validated.model_dump(),
        evidence=list(body.evidence or []),
        review_status="edited",
    )
    db.add(candidate)
    await db.flush()
    return ScriptParseCandidateRead.model_validate(candidate)


async def delete_candidate(
    db: AsyncSession,
    *,
    run_id: str,
    candidate_id: str,
) -> ScriptParseRunRead:
    """删除一条候选（软忽略之外的真实删除，仅限未确认 run）。"""
    run = await _load_run(db, run_id)
    if run.confirmed_at is not None:
        raise ValueError("解析结果已确认，不能删除候选")
    candidate = next((item for item in run.candidates if item.id == candidate_id), None)
    if candidate is None:
        raise ValueError(f"候选不存在：{candidate_id}")
    await db.delete(candidate)
    await db.flush()
    run = await _load_run(db, run_id)
    return run_to_read(run)


async def merge_candidates(
    db: AsyncSession,
    *,
    run_id: str,
    source_candidate_id: str,
    target_candidate_id: str,
) -> ScriptParseRunRead:
    """合并两个同类型候选：source 标记 merged，名称/别名/证据并入 target。"""
    run = await _load_run(db, run_id)
    if run.confirmed_at is not None:
        raise ValueError("解析结果已确认，不能继续合并候选")
    source = next((item for item in run.candidates if item.id == source_candidate_id), None)
    target = next((item for item in run.candidates if item.id == target_candidate_id), None)
    if source is None or target is None:
        raise ValueError("合并候选不存在")
    if source.candidate_type != target.candidate_type:
        raise ValueError("只能合并同类型候选")
    if source.id == target.id:
        raise ValueError("不能合并到自身")

    payload = dict(target.payload or {})
    source_payload = dict(source.payload or {})
    if source.candidate_type == "character":
        aliases = list(payload.get("aliases") or [])
        source_name = str(source_payload.get("name") or "").strip()
        if source_name and source_name != payload.get("name"):
            aliases.append(source_name)
        aliases.extend(source_payload.get("aliases") or [])
        payload["aliases"] = list(dict.fromkeys(aliases))
    target.evidence = list(target.evidence or []) + list(source.evidence or [])
    for key in ("issues",):
        merged = list(payload.get(key) or []) + list(source_payload.get(key) or [])
        if merged:
            payload[key] = list(dict.fromkeys(merged))
    target.payload = payload
    if not target.matched_entity_id and source.matched_entity_id:
        target.matched_entity_id = source.matched_entity_id
    source.review_status = "merged"
    source.merged_into_id = target.id
    await db.flush()
    return run_to_read(run)


def _compose_character_description(payload: ParsedCharacter) -> str:
    """把角色候选的设定字段拼成可读描述，不改写已有角色。"""
    parts = [
        payload.role,
        payload.age_range,
        payload.appearance,
        payload.hairstyle,
        payload.body_type,
        payload.base_costume,
    ]
    return "；".join(item.strip() for item in parts if item and item.strip())


async def _find_or_create_scene(
    db: AsyncSession, *, project: Project, payload: ParsedScene, matched_id: str | None = None
) -> tuple[Scene, str]:
    """优先使用人工匹配的场景，其次精确名称，最后创建并关联项目。"""
    name = payload.name.strip()
    if not name:
        raise ValueError("场景名称为空，请先补全候选")
    scene = await db.get(Scene, matched_id) if matched_id else None
    if scene is None:
        scene = (await db.execute(select(Scene).where(Scene.name == name))).scalars().first()
    action = "linked"
    if scene is None:
        scene = Scene(
            id=str(uuid.uuid4()),
            name=name,
            description=payload.spatial_features or payload.location_type or "",
            style=project.style,
            visual_style=project.visual_style,
            view_count=1,
        )
        db.add(scene)
        await db.flush()
        action = "created"
    link = (
        await db.execute(
            select(ProjectSceneLink).where(
                ProjectSceneLink.project_id == project.id,
                ProjectSceneLink.scene_id == scene.id,
                ProjectSceneLink.chapter_id.is_(None),
                ProjectSceneLink.shot_id.is_(None),
            )
        )
    ).scalars().first()
    if link is None:
        db.add(ProjectSceneLink(project_id=project.id, scene_id=scene.id))
    return scene, action


async def _find_or_create_prop(
    db: AsyncSession, *, project: Project, payload: ParsedProp, matched_id: str | None = None
) -> tuple[Prop, str]:
    """优先使用人工匹配的道具，其次精确名称，最后创建并关联项目。"""
    name = payload.name.strip()
    if not name:
        raise ValueError("道具名称为空，请先补全候选")
    prop = await db.get(Prop, matched_id) if matched_id else None
    if prop is None:
        prop = (await db.execute(select(Prop).where(Prop.name == name))).scalars().first()
    action = "linked"
    if prop is None:
        prop = Prop(
            id=str(uuid.uuid4()),
            name=name,
            description=payload.appearance or payload.story_usage or "",
            style=project.style,
            visual_style=project.visual_style,
            view_count=1,
        )
        db.add(prop)
        await db.flush()
        action = "created"
    link = (
        await db.execute(
            select(ProjectPropLink).where(
                ProjectPropLink.project_id == project.id,
                ProjectPropLink.prop_id == prop.id,
                ProjectPropLink.chapter_id.is_(None),
                ProjectPropLink.shot_id.is_(None),
            )
        )
    ).scalars().first()
    if link is None:
        db.add(ProjectPropLink(project_id=project.id, prop_id=prop.id))
    return prop, action


async def _find_or_create_costume(
    db: AsyncSession,
    *,
    project: Project,
    name: str,
    description: str = "",
    matched_id: str | None = None,
) -> tuple[Costume, str]:
    """优先使用人工匹配的服装，其次精确名称，最后创建并关联项目。"""
    normalized = (name or "").strip()
    if not normalized:
        raise ValueError("服装名称为空")
    costume = await db.get(Costume, matched_id) if matched_id else None
    if costume is None:
        costume = (
            await db.execute(select(Costume).where(Costume.name == normalized))
        ).scalars().first()
    action = "linked"
    if costume is None:
        costume = Costume(
            id=str(uuid.uuid4()),
            name=normalized,
            description=description,
            style=project.style,
            visual_style=project.visual_style,
            view_count=1,
        )
        db.add(costume)
        await db.flush()
        action = "created"
    link = (
        await db.execute(
            select(ProjectCostumeLink).where(
                ProjectCostumeLink.project_id == project.id,
                ProjectCostumeLink.costume_id == costume.id,
                ProjectCostumeLink.chapter_id.is_(None),
                ProjectCostumeLink.shot_id.is_(None),
            )
        )
    ).scalars().first()
    if link is None:
        db.add(ProjectCostumeLink(project_id=project.id, costume_id=costume.id))
    return costume, action


async def _find_or_create_character(
    db: AsyncSession,
    *,
    project: Project,
    payload: ParsedCharacter,
    matched_id: str | None = None,
) -> tuple[Character, str]:
    """优先使用人工匹配的角色，其次同项目精确名称；已有角色不覆盖。"""
    name = payload.name.strip()
    if not name:
        raise ValueError("角色名称为空，请先补全候选")
    character = await db.get(Character, matched_id) if matched_id else None
    if character is not None and character.project_id != project.id:
        character = None
    if character is None:
        character = (
            await db.execute(
                select(Character).where(
                    Character.project_id == project.id, Character.name == name
                )
            )
        ).scalars().first()
    if character is not None:
        return character, "linked"
    character = Character(
        id=str(uuid.uuid4()),
        project_id=project.id,
        name=name,
        description=_compose_character_description(payload),
        style=project.style,
        visual_style=project.visual_style,
        voice_description=(payload.voice_description or "")[:2000],
    )
    db.add(character)
    await db.flush()
    return character, "created"


async def confirm_parse_run(
    db: AsyncSession,
    *,
    run: ScriptParseRun,
    confirmed_by: int | None = None,
) -> tuple[ScriptParseRun, dict[str, Any], bool]:
    """确认候选并落正式数据；重复确认幂等。"""
    if run.confirmed_at is not None:
        return run, dict(run.applied_summary or {}), True
    if run.status != "completed":
        raise ValueError("解析尚未成功完成，不能确认")

    pending = [
        item
        for item in run.candidates
        if item.review_status == "pending" and item.candidate_type != "issue"
    ]
    if pending:
        raise ValueError(f"仍有 {len(pending)} 条候选未处理，请接受、编辑或忽略后再确认")

    document = await db.get(ScriptDocument, run.document_id)
    version = await db.get(ScriptDocumentVersion, run.version_id)
    if document is None or version is None:
        raise ValueError("剧本文档或版本不存在")
    project = await db.get(Project, document.project_id)
    if project is None:
        raise ValueError("项目不存在")
    chapter = await db.get(Chapter, document.chapter_id) if document.chapter_id else None

    summary: dict[str, Any] = {
        "characters_created": 0,
        "characters_linked": 0,
        "scenes_created": 0,
        "scenes_linked": 0,
        "props_created": 0,
        "props_linked": 0,
        "costumes_created": 0,
        "costumes_linked": 0,
        "dialogues_stored": 0,
        "scene_beats_stored": 0,
        "ignored": 0,
        "merged": 0,
    }
    confirmed_result: dict[str, Any] = {
        "characters": [],
        "scenes": [],
        "props": [],
        "costume_changes": [],
        "episode": None,
        "scene_beats": [],
        "dialogues": [],
        "issues": [],
    }

    def count(action: str, kind: str) -> None:
        summary[f"{kind}_{action}"] = int(summary.get(f"{kind}_{action}", 0)) + 1

    # 先场景/道具/服装，再角色（角色基础服装需要先存在）。
    for candidate in run.candidates:
        if candidate.review_status in {"ignored", "merged"}:
            if candidate.review_status == "ignored":
                summary["ignored"] += 1
            else:
                summary["merged"] += 1
            continue
        payload = dict(candidate.payload or {})
        try:
            if candidate.candidate_type == "scene":
                scene_payload = ParsedScene.model_validate(payload)
                scene, action = await _find_or_create_scene(
                    db,
                    project=project,
                    payload=scene_payload,
                    matched_id=candidate.matched_entity_id,
                )
                count(action, "scenes")
                confirmed_result["scenes"].append({"candidate_id": candidate.id, "entity_id": scene.id, "name": scene.name, "action": action})
            elif candidate.candidate_type == "prop":
                prop_payload = ParsedProp.model_validate(payload)
                prop, action = await _find_or_create_prop(
                    db,
                    project=project,
                    payload=prop_payload,
                    matched_id=candidate.matched_entity_id,
                )
                count(action, "props")
                confirmed_result["props"].append({"candidate_id": candidate.id, "entity_id": prop.id, "name": prop.name, "action": action})
            elif candidate.candidate_type == "costume_change":
                costume_payload = ParsedCostumeChange.model_validate(payload)
                costume, action = await _find_or_create_costume(
                    db,
                    project=project,
                    name=costume_payload.changed_costume,
                    description=costume_payload.reason or costume_payload.story_position,
                    matched_id=candidate.matched_entity_id,
                )
                count(action, "costumes")
                confirmed_result["costume_changes"].append(
                    {
                        "candidate_id": candidate.id,
                        "entity_id": costume.id,
                        "character_name": costume_payload.character_name,
                        "name": costume.name,
                        "action": action,
                    }
                )
        except Exception as exc:  # noqa: BLE001 - 单条失败整体回滚
            raise ValueError(f"候选 {candidate.id} 落库失败：{exc}") from exc

    for candidate in run.candidates:
        if candidate.review_status in {"ignored", "merged"}:
            continue
        payload = dict(candidate.payload or {})
        if candidate.candidate_type == "character":
            character_payload = ParsedCharacter.model_validate(payload)
            character, action = await _find_or_create_character(
                db,
                project=project,
                payload=character_payload,
                matched_id=candidate.matched_entity_id,
            )
            count(action, "characters")
            if not character.costume_id and character_payload.base_costume:
                costume, costume_action = await _find_or_create_costume(
                    db,
                    project=project,
                    name=character_payload.base_costume,
                    description="角色基础服装",
                )
                count(costume_action, "costumes")
                character.costume_id = costume.id
            confirmed_result["characters"].append(
                {
                    "candidate_id": candidate.id,
                    "entity_id": character.id,
                    "name": character.name,
                    "action": action,
                }
            )
        elif candidate.candidate_type == "scene_beat":
            confirmed_result["scene_beats"].append(payload)
            summary["scene_beats_stored"] += 1
        elif candidate.candidate_type == "episode":
            episode_payload = ParsedEpisode.model_validate(payload)
            confirmed_result["episode"] = episode_payload.model_dump()
        elif candidate.candidate_type == "dialogue":
            dialogue = ParsedDialogue.model_validate(payload)
            confirmed_result["dialogues"].append(dialogue.model_dump())
            summary["dialogues_stored"] += 1
        elif candidate.candidate_type == "issue":
            confirmed_result["issues"].append(payload)

    # episode 候选由 scene_beat 汇总；摘要/标题只写有值且不覆盖非空人工内容。
    if chapter is not None:
        if version.raw_text.strip():
            chapter.raw_text = version.raw_text
            chapter.condensed_text = ""
        episode_data = confirmed_result.get("episode")
        if episode_data:
            episode_payload = ParsedEpisode.model_validate(episode_data)
            if episode_payload.summary and not (chapter.summary or "").strip():
                chapter.summary = episode_payload.summary
        elif confirmed_result.get("scene_beats"):
            confirmed_result["episode"] = {
                "title": document.title,
                "summary": "",
                "scene_beats": confirmed_result["scene_beats"],
            }

    for candidate in run.candidates:
        if candidate.review_status not in {"ignored", "merged"}:
            candidate.review_status = "accepted"

    # 同步生效版本（与 C5 activate 语义一致，但保留解析结果）。
    versions = (
        await db.execute(
            select(ScriptDocumentVersion).where(
                ScriptDocumentVersion.document_id == document.id
            )
        )
    ).scalars().all()
    for item in versions:
        if item.status == "active" and item.id != version.id:
            item.status = "superseded"
    version.status = "active"
    document.active_version_id = version.id
    document.current_version_id = version.id

    run.confirmed_at = datetime.now(UTC)
    run.confirmed_by = confirmed_by
    run.status = "confirmed"
    run.applied_summary = summary
    run.confirmed_result = confirmed_result
    await db.flush()
    run = await _load_run(db, run.id)
    return run, summary, False
