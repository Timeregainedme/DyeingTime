"""P3 / C6：剧本解析任务执行与候选合并。

复用现有 LLM 基础设施（`build_text_llm` + AgentBase），不新建模型调用框架。
AI 输出只写候选表，不直接改正式资产。
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chains.agents.episode_script_parser_agent import EpisodeScriptParserAgent
from app.core.db import async_session_maker
from app.core.task_manager import SqlAlchemyTaskStore
from app.core.task_manager.types import TaskStatus
from app.models.studio import (
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
from app.schemas.skills.script_parse import (
    ParsedCharacter,
    ParsedCostumeChange,
    ParsedDialogue,
    ParsedEpisode,
    ParsedIssue,
    ParsedProp,
    ParsedScene,
    ParsedSceneBeat,
    ParseEvidence,
    ScriptParseResult,
)
from app.services.llm.resolver import build_text_llm
from app.services.studio.script_parse_chunking import ScriptChunk, split_script_for_parse

PROMPT_VERSION = "episode_script_parse@v1"


def _json(data: Any) -> str:
    """紧凑 JSON 序列化，保留中文。"""
    return json.dumps(data, ensure_ascii=False)


def _normalize_name(value: str | None) -> str:
    """统一名称首尾空白；不改变大小写/内部字符。"""
    return (value or "").strip()


def _merge_unique(items: list[str]) -> list[str]:
    """按出现顺序去重并过滤空字符串。"""
    return list(dict.fromkeys(item for item in items if item))


async def _load_existing_entities(
    db: AsyncSession, *, project_id: str
) -> tuple[list[Character], list[Scene], list[Prop], list[Costume]]:
    """读取项目已有角色与关联场景/道具/服装，供预匹配与提示词上下文。"""
    characters = (
        await db.execute(select(Character).where(Character.project_id == project_id))
    ).scalars().all()
    scenes = (
        await db.execute(
            select(Scene)
            .join(ProjectSceneLink, ProjectSceneLink.scene_id == Scene.id)
            .where(ProjectSceneLink.project_id == project_id)
            .distinct()
        )
    ).scalars().all()
    props = (
        await db.execute(
            select(Prop)
            .join(ProjectPropLink, ProjectPropLink.prop_id == Prop.id)
            .where(ProjectPropLink.project_id == project_id)
            .distinct()
        )
    ).scalars().all()
    costumes = (
        await db.execute(
            select(Costume)
            .join(ProjectCostumeLink, ProjectCostumeLink.costume_id == Costume.id)
            .where(ProjectCostumeLink.project_id == project_id)
            .distinct()
        )
    ).scalars().all()
    return list(characters), list(scenes), list(props), list(costumes)


def _entity_brief(items: list[Any]) -> list[dict[str, str]]:
    """只传名称/描述给模型，避免把无关内部字段暴露给 LLM。"""
    return [{"name": item.name, "description": item.description or ""} for item in items[:200]]


def _normalize_evidence(
    evidence: list[ParseEvidence], chunk: ScriptChunk
) -> list[ParseEvidence]:
    """把模型引用的原文短句映射到完整原文的全局字符偏移。"""
    rows: list[ParseEvidence] = []
    for item in evidence:
        quote = (item.quote or "").strip()[:200]
        if not quote:
            continue
        start = item.start_char
        end = item.end_char
        local = chunk.text.find(quote)
        if local >= 0:
            start = chunk.start_char + local
            end = start + len(quote)
        else:
            start = start if start is not None else None
            end = end if end is not None else None
        rows.append(
            ParseEvidence(
                chunk_id=item.chunk_id or chunk.id,
                start_char=start,
                end_char=end,
                quote=quote,
            )
        )
    return rows


class ParseMergeAccumulator:
    """跨块合并结果，按名称保守去重，不做模糊自动合并。"""

    def __init__(
        self,
        *,
        existing_characters: list[Character],
        existing_scenes: list[Scene],
        existing_props: list[Prop],
        existing_costumes: list[Costume],
    ):
        """保存已有实体名称→ID 映射，用于生成候选时预匹配。"""
        self.characters: dict[str, ParsedCharacter] = {}
        self.scenes: dict[str, ParsedScene] = {}
        self.props: dict[str, ParsedProp] = {}
        self.costumes: dict[str, ParsedCostumeChange] = {}
        self.dialogues: list[ParsedDialogue] = []
        self.scene_beats: list[ParsedSceneBeat] = []
        self.issues: list[ParsedIssue] = []
        self.episode: ParsedEpisode | None = None
        self.character_ids = {item.name: item.id for item in existing_characters}
        self.scene_ids = {item.name: item.id for item in existing_scenes}
        self.prop_ids = {item.name: item.id for item in existing_props}
        self.costume_ids = {item.name: item.id for item in existing_costumes}

    def merge_result(self, result: ScriptParseResult, chunk: ScriptChunk) -> None:
        """把单块结果合并进累加器；名称/别名去重，不做模糊匹配。"""
        for item in result.characters:
            name = _normalize_name(item.name)
            if not name:
                continue
            target_key = name
            if target_key not in self.characters:
                alias_key = next(
                    (alias for alias in item.aliases if _normalize_name(alias) in self.characters),
                    None,
                )
                if alias_key:
                    target_key = _normalize_name(alias_key)
            current = self.characters.get(target_key)
            item.evidence = _normalize_evidence(item.evidence, chunk)
            item.matched_character_id = self.character_ids.get(name)
            if current is None:
                self.characters[target_key] = item
            else:
                self._merge_character(current, item)

        for item in result.scenes:
            name = _normalize_name(item.name)
            if not name:
                continue
            item.evidence = _normalize_evidence(item.evidence, chunk)
            item.matched_scene_id = self.scene_ids.get(name)
            item.is_existing = item.matched_scene_id is not None
            current = self.scenes.get(name)
            if current is None:
                self.scenes[name] = item
            else:
                current.evidence.extend(item.evidence)
                current.issues = _merge_unique([*current.issues, *item.issues])

        for item in result.props:
            name = _normalize_name(item.name)
            if not name:
                continue
            item.evidence = _normalize_evidence(item.evidence, chunk)
            item.matched_prop_id = self.prop_ids.get(name)
            item.is_existing = item.matched_prop_id is not None
            current = self.props.get(name)
            if current is None:
                self.props[name] = item
            else:
                current.evidence.extend(item.evidence)
                current.issues = _merge_unique([*current.issues, *item.issues])

        for item in result.costume_changes:
            key = f"{_normalize_name(item.character_name)}|{_normalize_name(item.changed_costume)}"
            if key == "|":
                continue
            item.evidence = _normalize_evidence(item.evidence, chunk)
            current = self.costumes.get(key)
            if current is None:
                self.costumes[key] = item
            else:
                current.evidence.extend(item.evidence)
                current.issues = _merge_unique([*current.issues, *item.issues])

        for item in result.dialogues:
            item.evidence = _normalize_evidence(item.evidence, chunk)
            if not item.speaker_name:
                item.speaker_unresolved = True
            self.dialogues.append(item)

        if result.episode.title or result.episode.summary or result.episode.scene_beats:
            if self.episode is None:
                self.episode = ParsedEpisode()
            if not self.episode.title:
                self.episode.title = result.episode.title
            if not self.episode.summary:
                self.episode.summary = result.episode.summary
            self.episode.major_events = _merge_unique(
                [*self.episode.major_events, *result.episode.major_events]
            )
            for beat in result.episode.scene_beats:
                beat.evidence = _normalize_evidence(beat.evidence, chunk)
                self.scene_beats.append(beat)
        for issue in result.issues:
            issue.evidence = _normalize_evidence(issue.evidence, chunk)
            self.issues.append(issue)

    def _merge_character(self, current: ParsedCharacter, incoming: ParsedCharacter) -> None:
        """同名角色只补空字段与证据，不覆盖已有非空设定。"""
        current.aliases = _merge_unique([*current.aliases, *incoming.aliases])
        for field in (
            "role",
            "age_range",
            "appearance",
            "hairstyle",
            "body_type",
            "base_costume",
            "voice_description",
        ):
            if not getattr(current, field) and getattr(incoming, field):
                setattr(current, field, getattr(incoming, field))
        current.episodes = sorted({*current.episodes, *incoming.episodes})
        current.evidence.extend(incoming.evidence)
        current.issues = _merge_unique([*current.issues, *incoming.issues])

    def result(self) -> ScriptParseResult:
        """生成最终候选结果；场次按块顺序合并。"""
        episode = self.episode or ParsedEpisode()
        if self.scene_beats:
            episode.scene_beats = self.scene_beats
        return ScriptParseResult(
            characters=list(self.characters.values()),
            scenes=list(self.scenes.values()),
            props=list(self.props.values()),
            costume_changes=list(self.costumes.values()),
            episode=episode,
            dialogues=self.dialogues,
            issues=self.issues,
        )

    def previous_context(self) -> str:
        """给下一块提供已识别实体名，降低跨块同名分裂。"""
        names = list(self.characters.keys())[-30:]
        scenes = list(self.scenes.keys())[-20:]
        return _json({"characters": names, "scenes": scenes})


def _summarize_prompt(agent: EpisodeScriptParserAgent) -> tuple[str, str]:
    """返回提示词版本标识与系统提示词哈希，供 run 追溯。"""
    prompt = agent.system_prompt or ""
    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    return PROMPT_VERSION, digest


async def _persist_candidates(
    db: AsyncSession,
    *,
    run: ScriptParseRun,
    result: ScriptParseResult,
) -> None:
    """写入候选；同 key 已存在时保留人工编辑，只补 AI 原始字段。

    同一 run 被任务重试时，不能因为重新持久化而覆盖已有 edited/accepted/
    ignored/merged 候选。新 run 仍会得到全新的候选集合。
    """
    existing_rows = (
        await db.execute(
            select(ScriptParseCandidate).where(ScriptParseCandidate.run_id == run.id)
        )
    ).scalars().all()
    by_key = {
        (item.candidate_type, item.candidate_key): item for item in existing_rows
    }
    rows: list[ScriptParseCandidate] = []
    order = max((item.order_index for item in existing_rows), default=0)

    def add(
        candidate_type: str,
        key: str,
        payload: dict[str, Any],
        evidence: list[dict[str, Any]],
        issue: str = "",
        matched: str | None = None,
    ) -> None:
        nonlocal order
        candidate_key = key[:160]
        current = by_key.get((candidate_type, candidate_key))
        if current is not None:
            if current.review_status not in {"edited", "accepted", "ignored", "merged"}:
                current.payload = payload
                current.evidence = evidence
                current.issue = issue[:255]
                if matched:
                    current.matched_entity_id = matched
            return
        order += 1
        row = ScriptParseCandidate(
            id=str(uuid.uuid4()),
            run_id=run.id,
            candidate_type=candidate_type,
            candidate_key=candidate_key,
            order_index=order,
            payload=payload,
            evidence=evidence,
            review_status="pending",
            matched_entity_id=matched,
            issue=issue[:255],
        )
        by_key[(candidate_type, candidate_key)] = row
        rows.append(row)

    for item in result.characters:
        add(
            "character",
            f"character:{item.name}",
            item.model_dump(),
            [e.model_dump() for e in item.evidence],
            "；".join(item.issues),
            item.matched_character_id,
        )
    for item in result.scenes:
        add(
            "scene",
            f"scene:{item.name}",
            item.model_dump(),
            [e.model_dump() for e in item.evidence],
            "；".join(item.issues),
            item.matched_scene_id,
        )
    for item in result.props:
        add(
            "prop",
            f"prop:{item.name}",
            item.model_dump(),
            [e.model_dump() for e in item.evidence],
            "；".join(item.issues),
            item.matched_prop_id,
        )
    for item in result.costume_changes:
        add(
            "costume_change",
            f"costume:{item.character_name}:{item.changed_costume}",
            item.model_dump(),
            [e.model_dump() for e in item.evidence],
            "；".join(item.issues),
        )
    for index, beat in enumerate(result.episode.scene_beats, start=1):
        payload = beat.model_dump()
        payload["index"] = index
        add(
            "scene_beat",
            f"scene_beat:{index}",
            payload,
            [e.model_dump() for e in beat.evidence],
            "；".join(beat.issues),
        )
    add(
        "episode",
        "episode:1",
        result.episode.model_dump(),
        [],
        result.notes,
    )
    for index, dialogue in enumerate(result.dialogues, start=1):
        payload = dialogue.model_dump()
        payload["order"] = index
        add(
            "dialogue",
            f"dialogue:{index}",
            payload,
            [e.model_dump() for e in dialogue.evidence],
            "说话人未识别" if dialogue.speaker_unresolved else "；".join(dialogue.issues),
        )
    for index, issue in enumerate(result.issues, start=1):
        add(
            "issue",
            f"issue:{index}",
            issue.model_dump(),
            [e.model_dump() for e in issue.evidence],
            issue.message,
        )
    db.add_all(rows)
    await db.flush()


async def run_script_parse_task(task_id: str, run_args: dict) -> None:
    """Celery worker 入口：解析 → 写候选 → 更新 run/version/task 状态。"""
    run_id = str(run_args.get("run_id") or "")
    async with async_session_maker() as session:
        store = SqlAlchemyTaskStore(session)
        try:
            await store.set_status(task_id, TaskStatus.running)
            await store.set_progress(task_id, 5)
            run = await session.get(ScriptParseRun, run_id)
            if run is None:
                raise RuntimeError(f"解析运行不存在：{run_id}")
            run.status = "running"
            run.progress = 5
            run.started_at = datetime.now(UTC)
            await session.commit()

            version = await session.get(ScriptDocumentVersion, run.version_id)
            document = await session.get(ScriptDocument, run.document_id)
            if version is None or document is None:
                raise RuntimeError("剧本版本或文档不存在")
            version.parse_status = "parsing"
            await session.flush()
            project = await session.get(Project, document.project_id)
            if project is None:
                raise RuntimeError("项目不存在")

            world_text = ""
            if run.worldbuilding_version_id:
                world_version = await session.get(ScriptDocumentVersion, run.worldbuilding_version_id)
                if world_version is not None:
                    world_text = world_version.raw_text

            existing = await _load_existing_entities(session, project_id=project.id)
            characters, scenes, props, costumes = existing
            accumulator = ParseMergeAccumulator(
                existing_characters=characters,
                existing_scenes=scenes,
                existing_props=props,
                existing_costumes=costumes,
            )

            chat_model, model, provider = await build_text_llm(
                session, model_id=run.model_id, thinking=False
            )
            agent = EpisodeScriptParserAgent(chat_model)
            prompt_version, prompt_hash = _summarize_prompt(agent)
            run.model_name = model.name
            run.provider_name = provider.name
            run.prompt_version = prompt_version
            run.prompt_hash = prompt_hash

            chunks = split_script_for_parse(version.raw_text)
            run.chunk_count = max(1, len(chunks))
            await session.commit()

            failed_chunks: list[int] = []
            for chunk in chunks:
                try:
                    parsed = await agent.aparse(
                        project_name=project.name,
                        episode_title=document.title,
                        chunk_id=chunk.id,
                        worldbuilding_text=world_text,
                        script_text=chunk.text,
                        previous_context=accumulator.previous_context(),
                        existing_characters_json=_json(_entity_brief(characters)),
                        existing_scenes_json=_json(_entity_brief(scenes)),
                        existing_props_json=_json(_entity_brief(props)),
                        existing_costumes_json=_json(_entity_brief(costumes)),
                    )
                    accumulator.merge_result(parsed, chunk)
                except Exception:  # noqa: BLE001 - 单块失败继续，最终显式暴露
                    failed_chunks.append(chunk.index)
                run.progress = min(90, 5 + int((chunk.index / max(1, len(chunks))) * 85))
                await store.set_progress(task_id, run.progress)
                await session.commit()

            result = accumulator.result()
            await _persist_candidates(session, run=run, result=result)
            run.failed_chunks = failed_chunks
            run.progress = 100
            run.finished_at = datetime.now(UTC)
            version.parse_status = "failed" if failed_chunks else "parsed"

            summary = {
                "characters": len(result.characters),
                "scenes": len(result.scenes),
                "props": len(result.props),
                "costume_changes": len(result.costume_changes),
                "scene_beats": len(result.episode.scene_beats),  # pylint: disable=no-member
                "dialogues": len(result.dialogues),
                "issues": len(result.issues),
                "failed_chunks": failed_chunks,
            }
            if failed_chunks:
                run.status = "failed"
                run.error = f"以下文本块解析失败：{failed_chunks}；已保留成功块的候选，请重试或人工补全"
                await store.set_error(task_id, run.error)
                await store.set_status(task_id, TaskStatus.failed)
            else:
                run.status = "completed"
                run.error = ""
                await store.set_result(task_id, summary)
                await store.set_status(task_id, TaskStatus.succeeded)
            await store.set_progress(task_id, 100)
            await session.commit()
        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            async with async_session_maker() as s2:
                store2 = SqlAlchemyTaskStore(s2)
                await store2.set_error(task_id, str(exc))
                await store2.set_status(task_id, TaskStatus.failed)
                run2 = await s2.get(ScriptParseRun, run_id)
                if run2 is not None:
                    run2.status = "failed"
                    run2.error = str(exc)
                    run2.finished_at = datetime.now(UTC)
                    version2 = await s2.get(ScriptDocumentVersion, run2.version_id)
                    if version2 is not None:
                        version2.parse_status = "failed"
                await s2.commit()


__all__ = [
    "PROMPT_VERSION",
    "ParseMergeAccumulator",
    "run_script_parse_task",
]
