"""将提取草稿中的镜头语言默认建议回写到 ShotDetail。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.studio import CameraAngle, CameraMovement, CameraShotType, Shot, ShotDetail


def _get_value(obj: Any, key: str) -> Any:
    """兼容 dict / Pydantic model / 普通对象的字段读取。"""

    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _coerce_enum(enum_cls: type, value: Any) -> Any:
    """将提取结果里的字符串安全转换为枚举；非法值直接忽略。"""

    if value in (None, ""):
        return None
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except Exception:
        return None


def _coerce_duration(value: Any) -> int | None:
    """将提取结果里的时长安全转换为正整数秒数。"""

    if value in (None, ""):
        return None
    try:
        duration = int(value)
    except Exception:
        return None
    return duration if duration > 0 else None


def _apply_detail_defaults_from_shot_draft(detail: ShotDetail, shot_draft: Any) -> None:
    """将单镜提取草稿中的默认镜头语言写入到现有 ShotDetail。"""

    semantic = _get_value(shot_draft, "semantic_suggestion")
    source = semantic or shot_draft

    camera_shot = _coerce_enum(CameraShotType, _get_value(source, "camera_shot"))
    angle = _coerce_enum(CameraAngle, _get_value(source, "angle"))
    movement = _coerce_enum(CameraMovement, _get_value(source, "movement"))
    duration = _coerce_duration(_get_value(source, "duration"))
    action_beats = [
        str(item).strip()
        for item in list(_get_value(source, "action_beats") or [])
        if str(item).strip()
    ]

    if camera_shot is not None:
        detail.camera_shot = camera_shot
    if angle is not None:
        detail.angle = angle
    if movement is not None:
        detail.movement = movement
    if duration is not None:
        detail.duration = duration
    if action_beats:
        detail.action_beats = action_beats


async def apply_shot_semantic_defaults_from_draft(
    db: AsyncSession,
    *,
    chapter_id: str,
    draft: Any,
) -> None:
    """按镜头序号匹配草稿，并将镜头语言默认建议回写到 ShotDetail。"""

    shot_rows = (
        await db.execute(
            select(Shot.id, Shot.index).where(Shot.chapter_id == chapter_id)
        )
    ).all()
    shot_id_by_index = {int(row.index): str(row.id) for row in shot_rows}

    for shot_draft in list(_get_value(draft, "shots") or []):
        shot_index = _coerce_duration(_get_value(shot_draft, "index"))
        if shot_index is None:
            continue
        shot_id = shot_id_by_index.get(shot_index)
        if not shot_id:
            continue
        detail = await db.get(ShotDetail, shot_id)
        if detail is None:
            continue
        _apply_detail_defaults_from_shot_draft(detail, shot_draft)


def apply_shot_semantic_defaults_from_draft_sync(
    db: Session,
    *,
    chapter_id: str,
    draft: Any,
) -> None:
    """同步任务执行器版本：将镜头语言默认建议回写到 ShotDetail。"""

    shot_rows = db.execute(select(Shot.id, Shot.index).where(Shot.chapter_id == chapter_id)).all()
    shot_id_by_index = {int(row.index): str(row.id) for row in shot_rows}

    for shot_draft in list(_get_value(draft, "shots") or []):
        shot_index = _coerce_duration(_get_value(shot_draft, "index"))
        if shot_index is None:
            continue
        shot_id = shot_id_by_index.get(shot_index)
        if not shot_id:
            continue
        detail = db.get(ShotDetail, shot_id)
        if detail is None:
            continue
        _apply_detail_defaults_from_shot_draft(detail, shot_draft)
