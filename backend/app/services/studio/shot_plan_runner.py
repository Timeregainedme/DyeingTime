"""P5 / C10：AI 分镜规划任务执行与资产解析。

复用现有文本 LLM、AgentBase、GenerationTask/Celery、P3 分镜分块工具；
AI 只写 shot_plan_candidates，确认后才写正式 Shot。
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.chains.agents.scene_shot_planner_agent import SceneShotPlannerAgent
from app.core.db import async_session_maker
from app.core.task_manager import SqlAlchemyTaskStore
from app.core.task_manager.types import TaskStatus
from app.models.studio import (
    CameraAngle,
    CameraMovement,
    CameraShotType,
    Chapter,
    Character,
    Costume,
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
    ShotPlanCandidate,
    ShotPlanDraft,
)
from app.schemas.skills.shot_planning import PlannedShot, ShotPlanResult
from app.schemas.studio.shot_plans import (
    PlanAssetRef,
    PlanCharacterRef,
    PlanDialogueLine,
    ShotPlanPayload,
)
from app.services.llm.resolver import build_text_llm
from app.services.studio.script_parse_chunking import ScriptChunk, split_script_for_parse

PROMPT_VERSION = "episode_shot_plan@v1"
DEFAULT_MIN_DURATION = 4
DEFAULT_MAX_DURATION = 15
_WHITESPACE = re.compile(r"\s+")


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)


def _norm(value: str | None) -> str:
    return _WHITESPACE.sub(" ", (value or "").strip()).lower()


def _issue(code: str, message: str, severity: str) -> dict[str, str]:
    return {"code": code, "message": message, "severity": severity}


def _camera_value(value: str, enum_type: type, fallback: str) -> tuple[str, str | None]:
    raw = (value or "").strip().upper()
    allowed = {item.value for item in enum_type}
    if raw in allowed:
        return raw, None
    return fallback, f"未知镜头语言代码「{value}」，已使用默认 {fallback}"


async def _active_world_text(db: AsyncSession, *, project_id: str) -> str:
    from app.models.studio import ScriptDocument as Doc

    document = (
        await db.execute(
            select(Doc).where(
                Doc.project_id == project_id,
                Doc.doc_type == "worldbuilding",
                Doc.chapter_id.is_(None),
            )
        )
    ).scalars().first()
    if document is None or not document.active_version_id:
        return ""
    version = await db.get(ScriptDocumentVersion, document.active_version_id)
    return version.raw_text if version else ""


async def _episode_version(
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
    if not version_id:
        return document, None
    return document, await db.get(ScriptDocumentVersion, version_id)


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


async def _load_context(
    db: AsyncSession, *, project_id: str, chapter_id: str
) -> dict[str, Any]:
    groups = list(
        (
            await db.execute(
                select(SceneGroup)
                .where(SceneGroup.chapter_id == chapter_id)
                .order_by(SceneGroup.index.asc())
            )
        ).scalars().all()
    )
    characters = list(
        (
            await db.execute(
                select(Character)
                .options(selectinload(Character.aliases))
                .where(Character.project_id == project_id)
            )
        ).scalars().all()
    )
    scenes = list(
        (
            await db.execute(
                select(Scene)
                .join(ProjectSceneLink, ProjectSceneLink.scene_id == Scene.id)
                .where(ProjectSceneLink.project_id == project_id)
                .distinct()
            )
        ).scalars().all()
    )
    props = list(
        (
            await db.execute(
                select(Prop)
                .join(ProjectPropLink, ProjectPropLink.prop_id == Prop.id)
                .where(ProjectPropLink.project_id == project_id)
                .distinct()
            )
        ).scalars().all()
    )
    costumes = list(
        (
            await db.execute(
                select(Costume)
                .join(ProjectCostumeLink, ProjectCostumeLink.costume_id == Costume.id)
                .where(ProjectCostumeLink.project_id == project_id)
                .distinct()
            )
        ).scalars().all()
    )
    return {
        "groups": groups,
        "characters": characters,
        "scenes": scenes,
        "props": props,
        "costumes": costumes,
    }


def _character_brief(item: Character) -> dict[str, Any]:
    return {
        "name": item.name,
        "aliases": [alias.alias for alias in getattr(item, "aliases", None) or []],
        "identity_version_id": item.identity_version_id,
        "appearance_version_id": item.current_appearance_version_id,
        "locked": item.identity_locked_at is not None,
        "base_costume_id": item.costume_id,
    }


def _asset_brief(items: list[Any]) -> list[dict[str, Any]]:
    return [
        {"name": item.name, "version_id": getattr(item, "current_version_id", None)}
        for item in items
    ]


def _group_brief(item: SceneGroup) -> dict[str, Any]:
    return {
        "id": item.id,
        "index": item.index,
        "title": item.title,
        "location": item.location,
        "time_of_day": item.time_of_day,
        "story_event": item.story_event,
        "primary_scene_id": item.primary_scene_id,
    }


def _resolve_name(mapping: dict[str, Any], name: str | None) -> Any | None:
    key = _norm(name)
    return mapping.get(key)


def _dialogue_line(
    planned,
    *,
    character_map: dict[str, Character],
    alias_map: dict[str, Character],
) -> tuple[PlanDialogueLine, list[dict[str, str]]]:
    speaker_name = (planned.speaker_name or "").strip() or None
    character = (
        _resolve_name(character_map, speaker_name)
        or _resolve_name(alias_map, speaker_name)
        if speaker_name
        else None
    )
    issues: list[dict[str, str]] = []
    mode = (planned.line_mode or "DIALOGUE").strip().upper()
    if mode not in {"DIALOGUE", "VOICE_OVER", "OFF_SCREEN", "PHONE"}:
        mode = "DIALOGUE"
    if mode == "DIALOGUE" and character is None:
        issues.append(
            _issue(
                "unresolved_speaker",
                f"对白「{planned.text[:30]}」说话人未识别或不存在",
                "blocking",
            )
        )
    return (
        PlanDialogueLine(
            text=planned.text,
            speaker_character_id=character.id if character else None,
            speaker_name=character.name if character else speaker_name,
            emotion=planned.emotion or "",
            line_mode=mode,
        ),
        issues,
    )


def _resolve_planned_shot(
    planned: PlannedShot,
    *,
    chunk: ScriptChunk,
    groups: list[SceneGroup],
    characters: list[Character],
    scenes: list[Scene],
    props: list[Prop],
    costumes: list[Costume],
    project: Project,
) -> tuple[dict[str, Any], list[dict[str, str]], int | None, int | None]:
    character_map = {_norm(item.name): item for item in characters}
    alias_map: dict[str, Character] = {}
    for item in characters:
        for alias in getattr(item, "aliases", None) or []:
            alias_map[_norm(alias.alias)] = item
    scene_map = {_norm(item.name): item for item in scenes}
    prop_map = {_norm(item.name): item for item in props}
    costume_map = {_norm(item.name): item for item in costumes}
    issues: list[dict[str, str]] = []

    # P10-C：默认值会让「模型漏输出场次」看起来像第 1 场。
    # 用 model_fields_set 区分「显式写了 1」和「根本没写」，后者必须人工确认。
    if "scene_group_index" not in planned.model_fields_set:
        issues.append(
            _issue(
                "scene_group_missing",
                "模型未输出场次序号，已按第 1 场处理；请人工确认场景切换",
                "blocking",
            )
        )

    group = groups[planned.scene_group_index - 1] if 1 <= planned.scene_group_index <= len(groups) else None
    if group is None:
        issues.append(
            _issue(
                "unknown_scene_group",
                f"生成结果引用了不存在的场次序号 {planned.scene_group_index}",
                "blocking",
            )
        )

    resolved_characters: list[PlanCharacterRef] = []
    seen_characters: set[str] = set()
    for name in planned.character_names:
        character = _resolve_name(character_map, name) or _resolve_name(alias_map, name)
        if character is None:
            issues.append(
                _issue("unknown_character", f"生成结果出现未知角色「{name}」", "blocking")
            )
            continue
        if character.id in seen_characters:
            continue
        seen_characters.add(character.id)
        if character.identity_locked_at is None:
            issues.append(
                _issue(
                    "character_unlocked",
                    f"角色「{character.name}」视觉身份尚未锁定，不能正式应用",
                    "blocking",
                )
            )
        resolved_characters.append(
            PlanCharacterRef(
                character_id=character.id,
                name=character.name,
                identity_version_id=character.identity_version_id,
                appearance_version_id=(
                    character.current_appearance_version_id or character.identity_version_id
                ),
            )
        )

    scene = _resolve_name(scene_map, planned.scene_name) or (
        next((item for item in scenes if group and item.id == group.primary_scene_id), None)
    )
    if scene is None:
        issues.append(
            _issue(
                "scene_asset_missing",
                f"镜头「{planned.title or planned.script_excerpt[:20]}」没有匹配到场景资产",
                "warning",
            )
        )

    resolved_props: list[PlanAssetRef] = []
    for name in planned.prop_names:
        prop = _resolve_name(prop_map, name)
        if prop is None:
            issues.append(_issue("unknown_prop", f"未找到道具「{name}」", "warning"))
            continue
        resolved_props.append(
            PlanAssetRef(asset_id=prop.id, name=prop.name, asset_version_id=prop.current_version_id)
        )

    costume = _resolve_name(costume_map, planned.costume_name)
    if planned.costume_name and costume is None:
        issues.append(
            _issue("unknown_costume", f"未找到服装「{planned.costume_name}」", "warning")
        )

    minimum = int(project.video_duration_min or DEFAULT_MIN_DURATION)
    maximum = int(project.video_duration_max or DEFAULT_MAX_DURATION)
    duration = int(planned.duration_seconds or 0)
    if duration < minimum or duration > maximum:
        issues.append(
            _issue(
                "duration_out_of_range",
                f"镜头时长 {duration}s 超出项目范围 {minimum}–{maximum}s",
                "blocking",
            )
        )

    camera_shot, camera_warning = _camera_value(
        planned.camera_shot, CameraShotType, CameraShotType.ms.value
    )
    angle, angle_warning = _camera_value(planned.angle, CameraAngle, CameraAngle.eye_level.value)
    movement, movement_warning = _camera_value(
        planned.movement, CameraMovement, CameraMovement.static.value
    )
    for warning in (camera_warning, angle_warning, movement_warning):
        if warning:
            issues.append(_issue("invalid_camera_language", warning, "warning"))

    dialogues: list[PlanDialogueLine] = []
    for planned_line in planned.dialogues:
        line, line_issues = _dialogue_line(
            planned_line, character_map=character_map, alias_map=alias_map
        )
        dialogues.append(line)
        issues.extend(line_issues)

    quote = (planned.source_quote or planned.script_excerpt or "").strip()
    local = chunk.text.find(quote) if quote else -1
    source_start = chunk.start_char + local if local >= 0 else None
    source_end = source_start + len(quote) if source_start is not None else None
    if quote and local < 0:
        issues.append(
            _issue(
                "source_quote_not_found",
                "镜头原文摘录未能在当前剧本块中定位",
                "warning",
            )
        )

    payload = ShotPlanPayload(
        title=planned.title or f"镜头 {planned.order}",
        script_excerpt=planned.script_excerpt or quote,
        source_start_char=source_start,
        source_end_char=source_end,
        duration=duration,
        camera_shot=camera_shot,
        angle=angle,
        movement=movement,
        action_beats=planned.action_beats,
        atmosphere=planned.atmosphere,
        description=planned.visual_description,
        video_prompt=planned.video_prompt_draft,
        characters=resolved_characters,
        scene=(
            PlanAssetRef(
                asset_id=scene.id,
                name=scene.name,
                asset_version_id=scene.current_version_id,
            )
            if scene
            else None
        ),
        props=resolved_props,
        costume=(
            PlanAssetRef(
                asset_id=costume.id,
                name=costume.name,
                asset_version_id=costume.current_version_id,
            )
            if costume
            else None
        ),
        dialogues=dialogues,
        issues=[item["message"] for item in issues],
    )
    return payload.model_dump(), issues, source_start, source_end


async def _persist_candidates(
    db: AsyncSession,
    *,
    draft: ShotPlanDraft,
    rows: list[tuple[dict[str, Any], list[dict[str, str]], str]],
) -> None:
    existing = (
        await db.execute(
            select(ShotPlanCandidate).where(ShotPlanCandidate.draft_id == draft.id)
        )
    ).scalars().all()
    by_key = {item.candidate_key: item for item in existing}
    for order, (payload, issues, key) in enumerate(rows, start=1):
        candidate_key = key[:128] or f"plan:{order}"
        current = by_key.get(candidate_key)
        if current is not None:
            if current.review_status not in {"edited", "accepted", "ignored"}:
                current.payload = payload
                current.issues = issues
                current.order_index = order
            continue
        candidate = ShotPlanCandidate(
            id=str(uuid.uuid4()),
            draft_id=draft.id,
            order_index=order,
            scene_group_id=payload.get("scene_group_id"),
            candidate_key=candidate_key,
            payload=payload,
            issues=issues,
            review_status="pending",
            source_key=key[:128],
        )
        db.add(candidate)
        by_key[candidate_key] = candidate
    await db.flush()


def _coverage(
    *,
    script: str,
    rows: list[tuple[dict[str, Any], list[dict[str, str]], str]],
    target_duration: int,
    failed_chunks: list[int],
    groups: list[SceneGroup] | None = None,
) -> dict[str, Any]:
    durations = [int(item[0].get("duration") or 0) for item in rows]
    ranges = [
        (item[0].get("source_start_char"), item[0].get("source_end_char"))
        for item in rows
        if item[0].get("source_start_char") is not None
    ]
    covered = 0
    if ranges:
        merged = sorted((int(a), int(b)) for a, b in ranges if a is not None and b is not None)
        cursor = 0
        for start, end in merged:
            if end <= cursor:
                continue
            covered += end - max(start, cursor)
            cursor = max(cursor, end)
    blocking = sum(
        1
        for item in rows
        for issue in item[1]
        if issue.get("severity") == "blocking"
    )
    warnings = sum(
        1
        for item in rows
        for issue in item[1]
        if issue.get("severity") != "blocking"
    )
    coverage_ratio = round(covered / len(script), 4) if script else 0
    coverage_warnings: list[str] = []
    if coverage_ratio < 0.6:
        coverage_warnings.append(
            f"原文覆盖率仅 {round(coverage_ratio * 100)}%，可能存在未拆入镜头的剧情或对白，请人工检查。"
        )
    if abs(sum(durations) - target_duration) > max(10, target_duration * 0.25):
        coverage_warnings.append(
            f"镜头总时长 {sum(durations)}s 与目标 {target_duration}s 差距较大。"
        )
    if groups:
        used = {str(item[0].get("scene_group_id") or "") for item in rows}
        missing = [group.title or group.location or group.id for group in groups if group.id not in used]
        if missing:
            coverage_warnings.append(
                "以下场次没有任何镜头覆盖：" + "、".join(missing) + "。请人工补拆后再确认。"
            )
    return {
        "script_length": len(script),
        "covered_chars": covered,
        "coverage_ratio": coverage_ratio,
        "shot_count": len(rows),
        "total_duration": sum(durations),
        "target_duration": target_duration,
        "min_duration": min(durations) if durations else None,
        "max_duration": max(durations) if durations else None,
        "blocking_issue_count": blocking,
        "warning_count": warnings,
        "failed_chunks": failed_chunks,
        "warnings": coverage_warnings,
    }


async def run_shot_plan_task(task_id: str, run_args: dict) -> None:
    """Celery worker 入口：AI 规划 → 候选落库 → 更新 draft/task。"""
    draft_id = str(run_args.get("draft_id") or "")
    async with async_session_maker() as session:
        store = SqlAlchemyTaskStore(session)
        try:
            await store.set_status(task_id, TaskStatus.running)
            await store.set_progress(task_id, 5)
            draft = await session.get(ShotPlanDraft, draft_id)
            if draft is None:
                raise RuntimeError(f"分镜规划草稿不存在：{draft_id}")
            draft.status = "generating"
            await session.commit()

            chapter = await session.get(Chapter, draft.chapter_id)
            project = await session.get(Project, draft.project_id)
            if chapter is None or project is None:
                raise RuntimeError("剧集或项目不存在")
            document, version = await _episode_version(session, chapter_id=chapter.id)
            if version is None:
                raise RuntimeError("当前剧集没有可用剧本版本")
            parse_run = await _latest_parse_run(session, document=document)
            draft.source_parse_run_id = parse_run.id if parse_run else None
            draft.source_script_version_id = version.id
            context = await _load_context(session, project_id=project.id, chapter_id=chapter.id)
            groups: list[SceneGroup] = context["groups"]
            if not groups:
                raise RuntimeError("剧集还没有正式场次，请先创建/导入场次")

            world_text = await _active_world_text(session, project_id=project.id)
            chat_model, model, provider = await build_text_llm(
                session, model_id=draft.model_id, thinking=False
            )
            agent = SceneShotPlannerAgent(chat_model)
            prompt_hash = hashlib.sha256((agent.system_prompt or "").encode("utf-8")).hexdigest()
            draft.model_name = model.name
            draft.provider_name = provider.name
            draft.prompt_version = PROMPT_VERSION
            draft.prompt_hash = prompt_hash
            draft.scene_group_snapshot = [_group_brief(item) for item in groups]
            await session.commit()

            chunks = split_script_for_parse(version.raw_text, max_chars=3000, overlap_lines=2)
            if not chunks:
                raise RuntimeError("剧本文本为空，无法规划分镜")
            collected: list[tuple[dict[str, Any], list[dict[str, str]], str]] = []
            failed_chunks: list[int] = []
            previous_context = ""
            seen_quotes: set[str] = set()
            for chunk in chunks:
                try:
                    result: ShotPlanResult = await agent.aplan(
                        project_name=project.name,
                        chapter_title=chapter.title,
                        target_duration=str(draft.target_duration),
                        pace=draft.pace,
                        scene_groups_json=_json([_group_brief(item) for item in groups]),
                        characters_json=_json(
                            [_character_brief(item) for item in context["characters"]]
                        ),
                        assets_json=_json(
                            {
                                "scenes": _asset_brief(context["scenes"]),
                                "props": _asset_brief(context["props"]),
                                "costumes": _asset_brief(context["costumes"]),
                            }
                        ),
                        worldbuilding_text=world_text,
                        script_text=chunk.text,
                        previous_context=previous_context,
                    )
                    for planned in result.shots:
                        payload, issues, _start, _end = _resolve_planned_shot(
                            planned,
                            chunk=chunk,
                            groups=groups,
                            characters=context["characters"],
                            scenes=context["scenes"],
                            props=context["props"],
                            costumes=context["costumes"],
                            project=project,
                        )
                        if planned.scene_group_index and 1 <= planned.scene_group_index <= len(groups):
                            payload["scene_group_id"] = groups[planned.scene_group_index - 1].id
                        quote_key = _norm(str(payload.get("script_excerpt") or ""))
                        if quote_key and quote_key in seen_quotes:
                            continue
                        if quote_key:
                            seen_quotes.add(quote_key)
                        key = f"plan:{len(collected) + 1}"
                        collected.append((payload, issues, key))
                    previous_context = _json(
                        [
                            {
                                "title": item[0].get("title"),
                                "excerpt": item[0].get("script_excerpt"),
                            }
                            for item in collected[-6:]
                        ]
                    )
                except Exception as exc:  # noqa: BLE001 - 单块失败保留其它块
                    failed_chunks.append(chunk.index)
                    draft.error = f"第 {chunk.index} 块规划失败：{exc}"
                await store.set_progress(task_id, min(90, 5 + int((chunk.index / len(chunks)) * 85)))
                await session.commit()

            if not collected:
                raise RuntimeError(draft.error or "AI 没有返回任何镜头候选")
            for order, (payload, _issues, _key) in enumerate(collected, start=1):
                payload["order"] = order
            await _persist_candidates(session, draft=draft, rows=collected)
            coverage = _coverage(
                script=version.raw_text,
                groups=groups,
                rows=collected,
                target_duration=draft.target_duration,
                failed_chunks=failed_chunks,
            )
            draft.coverage = coverage
            draft.error = (
                f"以下块失败：{failed_chunks}；已保留其它块候选" if failed_chunks else ""
            )
            draft.status = "failed" if failed_chunks else "review_required"
            await store.set_result(task_id, {"draft_id": draft.id, "coverage": coverage})
            await store.set_status(
                task_id, TaskStatus.failed if failed_chunks else TaskStatus.succeeded
            )
            await store.set_progress(task_id, 100)
            await session.commit()
        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            async with async_session_maker() as s2:
                store2 = SqlAlchemyTaskStore(s2)
                await store2.set_error(task_id, str(exc))
                await store2.set_status(task_id, TaskStatus.failed)
                draft2 = await s2.get(ShotPlanDraft, draft_id)
                if draft2 is not None:
                    draft2.status = "failed"
                    draft2.error = str(exc)
                await s2.commit()


__all__ = ["PROMPT_VERSION", "run_shot_plan_task"]
