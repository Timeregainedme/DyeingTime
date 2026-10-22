"""P3 / C6：脚本版本差异与影响范围。

第一版采用可解释的行级 diff + 名称/结构化候选对比：
- 不做不可控的语义模型 Diff；
- 所有影响标记为 possible，不自动删除/覆盖任何正式数据或历史视频。
"""

from __future__ import annotations

import difflib
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
    ScriptDiffReport,
    ScriptDocument,
    ScriptDocumentVersion,
    ScriptParseRun,
    Shot,
)
from app.schemas.studio.script_parse import ScriptDiffReportRead

MAX_DIFF_ROWS = 500


def _line_diff(old_text: str, new_text: str) -> tuple[list[dict[str, Any]], bool]:
    """生成行级差异；超过上限时截断并返回 truncated=True。"""
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    matcher = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
    rows: list[dict[str, Any]] = []
    truncated = False
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace":
            max_len = max(i2 - i1, j2 - j1)
            for offset in range(max_len):
                old_line = old_lines[i1 + offset] if i1 + offset < i2 else None
                new_line = new_lines[j1 + offset] if j1 + offset < j2 else None
                rows.append(
                    {
                        "type": "replace",
                        "old_line_no": i1 + offset + 1 if old_line is not None else None,
                        "new_line_no": j1 + offset + 1 if new_line is not None else None,
                        "old_text": old_line,
                        "new_text": new_line,
                    }
                )
                if len(rows) >= MAX_DIFF_ROWS:
                    truncated = True
                    break
        else:
            for index in range(i1, i2):
                rows.append(
                    {
                        "type": "delete",
                        "old_line_no": index + 1,
                        "new_line_no": None,
                        "old_text": old_lines[index],
                        "new_text": None,
                    }
                )
                if len(rows) >= MAX_DIFF_ROWS:
                    truncated = True
                    break
            for index in range(j1, j2):
                rows.append(
                    {
                        "type": "insert",
                        "old_line_no": None,
                        "new_line_no": index + 1,
                        "old_text": None,
                        "new_text": new_lines[index],
                    }
                )
                if len(rows) >= MAX_DIFF_ROWS:
                    truncated = True
                    break
        if truncated:
            break
    return rows, truncated


async def _project_entities(
    db: AsyncSession, *, project_id: str
) -> tuple[list[str], list[str], list[str], list[str]]:
    """读取项目已有角色/场景/道具/服装名称，用于影响范围匹配。"""
    characters = (
        await db.execute(select(Character.name).where(Character.project_id == project_id))
    ).scalars().all()
    scenes = (
        await db.execute(
            select(Scene.name)
            .join(ProjectSceneLink, ProjectSceneLink.scene_id == Scene.id)
            .where(ProjectSceneLink.project_id == project_id)
            .distinct()
        )
    ).scalars().all()
    props = (
        await db.execute(
            select(Prop.name)
            .join(ProjectPropLink, ProjectPropLink.prop_id == Prop.id)
            .where(ProjectPropLink.project_id == project_id)
            .distinct()
        )
    ).scalars().all()
    costumes = (
        await db.execute(
            select(Costume.name)
            .join(ProjectCostumeLink, ProjectCostumeLink.costume_id == Costume.id)
            .where(ProjectCostumeLink.project_id == project_id)
            .distinct()
        )
    ).scalars().all()
    return list(characters), list(scenes), list(props), list(costumes)


async def _latest_parse_run(
    db: AsyncSession, *, version_id: str
) -> ScriptParseRun | None:
    """读取版本最近一次成功解析，用于结构化候选对比。"""
    return (
        await db.execute(
            select(ScriptParseRun)
            .where(
                ScriptParseRun.version_id == version_id,
                ScriptParseRun.status.in_(["completed", "confirmed"]),
            )
            .order_by(ScriptParseRun.created_at.desc())
            .limit(1)
        )
    ).scalars().first()


def _names_by_type(run: ScriptParseRun | None) -> dict[str, set[str]]:
    """按候选类型收集名称集合；没有 run 时返回空集合。"""
    result = {"character": set(), "scene": set(), "prop": set(), "costume_change": set()}
    if run is None:
        return result
    for candidate in run.candidates:
        payload = candidate.payload or {}
        if candidate.candidate_type == "character":
            name = str(payload.get("name") or "").strip()
            if name:
                result["character"].add(name)
        elif candidate.candidate_type == "scene":
            name = str(payload.get("name") or "").strip()
            if name:
                result["scene"].add(name)
        elif candidate.candidate_type == "prop":
            name = str(payload.get("name") or "").strip()
            if name:
                result["prop"].add(name)
        elif candidate.candidate_type == "costume_change":
            key = f"{payload.get('character_name') or ''}|{payload.get('changed_costume') or ''}"
            if key != "|":
                result["costume_change"].add(key)
    return result


def _mentioned(changed_text: str, names: list[str]) -> list[str]:
    """返回变化文本中精确出现的已有实体名。"""
    return [name for name in names if name and name in changed_text]


async def _impact(
    db: AsyncSession,
    *,
    document: ScriptDocument,
    project: Project,
    added_text: str,
    removed_text: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """计算可能受影响的章节、镜头与资产；当前全部标记为 possible。"""
    characters, scenes, props, costumes = await _project_entities(
        db, project_id=project.id
    )
    changed_text = f"{added_text}\n{removed_text}"
    assets = {
        "characters": _mentioned(changed_text, characters),
        "scenes": _mentioned(changed_text, scenes),
        "props": _mentioned(changed_text, props),
        "costumes": _mentioned(changed_text, costumes),
    }

    chapters_stmt = select(Chapter).where(Chapter.project_id == project.id)
    if document.doc_type == "episode" and document.chapter_id:
        chapters_stmt = chapters_stmt.where(Chapter.id == document.chapter_id)
    chapters = (await db.execute(chapters_stmt.order_by(Chapter.index.asc()))).scalars().all()
    chapter_ids = [item.id for item in chapters]
    shots: list[Shot] = []
    if chapter_ids:
        shots = list(
            (
                await db.execute(
                    select(Shot)
                    .where(Shot.chapter_id.in_(chapter_ids))
                    .order_by(Shot.chapter_id.asc(), Shot.index.asc())
                )
            ).scalars().all()
        )
    impacted_shots = [
        {
            "shot_id": shot.id,
            "chapter_id": shot.chapter_id,
            "index": shot.index,
            "title": shot.title,
            "status": shot.status,
            "has_video": bool(shot.generated_video_file_id),
            "certainty": "possible",
        }
        for shot in shots
    ]
    impact = {
        "document_type": document.doc_type,
        "chapter_id": document.chapter_id,
        "chapters": [
            {
                "chapter_id": item.id,
                "index": item.index,
                "title": item.title,
                "certainty": "possible",
            }
            for item in chapters
        ],
        "shots": impacted_shots,
        "assets": assets,
        "summary": {
            "chapter_count": len(chapters),
            "shot_count": len(impacted_shots),
            "shots_with_video": sum(1 for item in impacted_shots if item["has_video"]),
        },
    }
    structured = {
        "assets": assets,
        "costume_hints": _costume_hints(added_text, characters, costumes),
    }
    return impact, structured


def _costume_hints(added_text: str, characters: list[str], costumes: list[str]) -> list[dict[str, str]]:
    """根据服装/造型关键词给出可能受影响的角色提示（不自动建资产）。"""
    keywords = ("穿", "换", "西装", "卫衣", "风衣", "裙", "外套", "发型", "妆")
    if not any(keyword in added_text for keyword in keywords):
        return []
    hints: list[dict[str, str]] = []
    for character in characters:
        if character and character in added_text:
            hints.append(
                {
                    "character": character,
                    "reason": "新增/修改文本涉及服装或造型关键词，建议重新解析造型候选",
                    "certainty": "possible",
                }
            )
    if not hints and costumes:
        hints.append(
            {
                "character": "",
                "reason": "文本涉及服装/造型关键词，但未能定位到具体角色",
                "certainty": "possible",
            }
        )
    return hints


async def create_diff_report(
    db: AsyncSession,
    *,
    document: ScriptDocument,
    new_version: ScriptDocumentVersion,
    old_version_id: str | None = None,
    created_by: int | None = None,
) -> ScriptDiffReport:
    """生成或复用差异报告；不修改正式业务数据。"""
    old_version = None
    if old_version_id:
        old_version = await db.get(ScriptDocumentVersion, old_version_id)
    elif document.active_version_id and document.active_version_id != new_version.id:
        old_version = await db.get(ScriptDocumentVersion, document.active_version_id)
    if old_version is None:
        raise ValueError("没有可比较的旧版本；首次上传无需差异报告")
    if old_version.id == new_version.id:
        raise ValueError("新旧版本相同，无需差异报告")
    if old_version.document_id != document.id or new_version.document_id != document.id:
        raise ValueError("版本不属于该文档")

    existing = (
        await db.execute(
            select(ScriptDiffReport).where(
                ScriptDiffReport.old_version_id == old_version.id,
                ScriptDiffReport.new_version_id == new_version.id,
            )
        )
    ).scalars().first()
    if existing is not None:
        return existing

    project = await db.get(Project, document.project_id)
    if project is None:
        raise ValueError("项目不存在")

    text_diff, truncated = _line_diff(old_version.raw_text, new_version.raw_text)
    added_text = "\n".join(
        str(item["new_text"]) for item in text_diff if item.get("new_text")
    )
    removed_text = "\n".join(
        str(item["old_text"]) for item in text_diff if item.get("old_text")
    )

    old_run = await _latest_parse_run(db, version_id=old_version.id)
    new_run = await _latest_parse_run(db, version_id=new_version.id)
    old_names = _names_by_type(old_run)
    new_names = _names_by_type(new_run)
    structured_diff = {
        "old_parse_run_id": old_run.id if old_run else None,
        "new_parse_run_id": new_run.id if new_run else None,
        "requires_reparse": new_run is None,
        "characters_added": sorted(new_names["character"] - old_names["character"]),
        "characters_removed": sorted(old_names["character"] - new_names["character"]),
        "scenes_added": sorted(new_names["scene"] - old_names["scene"]),
        "scenes_removed": sorted(old_names["scene"] - new_names["scene"]),
        "props_added": sorted(new_names["prop"] - old_names["prop"]),
        "props_removed": sorted(old_names["prop"] - new_names["prop"]),
        "costume_changes_added": sorted(
            new_names["costume_change"] - old_names["costume_change"]
        ),
        "text_truncated": truncated,
    }
    impact, asset_structured = await _impact(
        db,
        document=document,
        project=project,
        added_text=added_text,
        removed_text=removed_text,
    )
    structured_diff.update(asset_structured)

    report = ScriptDiffReport(
        id=str(uuid.uuid4()),
        document_id=document.id,
        old_version_id=old_version.id,
        new_version_id=new_version.id,
        status="draft",
        text_diff=text_diff,
        structured_diff=structured_diff,
        impact=impact,
        decisions={},
        decided_by=created_by,
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)
    return report


def report_to_read(report: ScriptDiffReport) -> ScriptDiffReportRead:
    """把差异报告 ORM 转为响应模型。"""
    return ScriptDiffReportRead.model_validate(report)


async def get_diff_report(db: AsyncSession, *, report_id: str) -> ScriptDiffReport:
    """读取差异报告；不存在时抛 ValueError。"""
    report = await db.get(ScriptDiffReport, report_id)
    if report is None:
        raise ValueError(f"差异报告不存在：{report_id}")
    return report


async def decide_diff_report(
    db: AsyncSession,
    *,
    report: ScriptDiffReport,
    status_value: str,
    decisions: dict[str, Any],
    decided_by: int | None,
) -> ScriptDiffReport:
    """记录人工接受/忽略；不自动覆盖正式业务数据。"""
    normalized = (status_value or "").strip()
    if normalized not in {"accepted", "ignored"}:
        raise ValueError("status 只支持 accepted / ignored")
    report.status = normalized
    report.decisions = decisions or {}
    report.decided_by = decided_by
    report.decided_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(report)
    return report


__all__ = [
    "create_diff_report",
    "decide_diff_report",
    "get_diff_report",
    "report_to_read",
]
