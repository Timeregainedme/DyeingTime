"""P4：角色视觉身份锁定与音色绑定。

锁定只保护视觉身份核心字段与当前身份版本；别名、音色、造型和辅助视角仍可修改。
音色继续复用 characters.voice_id → actors.voice_id 的既有回退顺序。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.studio import Actor, AssetImageCandidate, Character
from app.schemas.studio.asset_versions import VoiceBindingRead, VoiceBindingUpdate
from app.services.studio.asset_versions import ensure_base_version

# 锁定后不可直接覆盖的身份核心字段。
LOCKED_IDENTITY_FIELDS = {
    "name",
    "description",
    "age_range",
    "appearance",
    "face_features",
    "body_type",
    "identity_features",
    "identity_version_id",
}


def is_identity_locked(character: Character) -> bool:
    return character.identity_locked_at is not None


def assert_identity_fields_editable(
    character: Character, update_data: dict[str, Any]
) -> None:
    """服务端强制锁定；前端禁用不能作为唯一约束。"""
    if not is_identity_locked(character):
        return
    attempted = sorted(set(update_data) & LOCKED_IDENTITY_FIELDS)
    if attempted:
        raise ValueError(
            "视觉身份已锁定，不能直接修改基础身份字段："
            + "、".join(attempted)
            + "；请创建新的身份版本"
        )


async def lock_identity(
    db: AsyncSession,
    *,
    character: Character,
    expected_lock_version: int | None = None,
    locked_by: int | None = None,
) -> Character:
    """锁定视觉身份；音色不是前置条件。"""
    if character.identity_locked_at is not None:
        return character
    if expected_lock_version is not None and int(character.identity_lock_version or 0) != expected_lock_version:
        raise ValueError("角色身份已被其他操作修改，请刷新后重试")
    if not (character.name or "").strip():
        raise ValueError("角色名称不能为空，不能锁定视觉身份")
    if not (character.appearance or character.description or "").strip():
        raise ValueError("基础外貌设定不能为空，不能锁定视觉身份")

    version = await ensure_base_version(
        db, asset_type="character", asset_id=character.id
    )
    front = (
        await db.execute(
            select(AssetImageCandidate.id)
            .where(
                AssetImageCandidate.asset_version_id == version.id,
                AssetImageCandidate.view_angle == "FRONT",
                AssetImageCandidate.is_adopted.is_(True),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if front is None:
        raise ValueError("至少需要一张已采纳的基础身份正面图，才能锁定视觉身份")

    character.identity_version_id = version.id
    character.identity_locked_at = datetime.now(UTC)
    character.identity_locked_by = locked_by
    character.identity_lock_version = int(character.identity_lock_version or 0) + 1
    await db.flush()
    return character


async def get_voice_binding(
    db: AsyncSession, *, character: Character
) -> VoiceBindingRead:
    """返回角色音色与既有回退链的最终生效值。"""
    actor = await db.get(Actor, character.actor_id) if character.actor_id else None
    effective_voice = (character.voice_id or "").strip() or None
    effective_source = (character.voice_source or "").strip() or None
    effective_from = "character" if effective_voice else "unbound"
    if not effective_voice and actor is not None:
        actor_voice = (actor.voice_id or "").strip() or None
        if actor_voice:
            effective_voice = actor_voice
            effective_source = (actor.voice_source or "").strip() or None
            effective_from = "actor"
    return VoiceBindingRead(
        character_id=character.id,
        voice_id=character.voice_id,
        voice_source=character.voice_source,
        voice_description=character.voice_description or "",
        bound_at=character.voice_bound_at,
        actor_id=character.actor_id,
        actor_voice_id=actor.voice_id if actor else None,
        actor_voice_source=actor.voice_source if actor else None,
        effective_voice_id=effective_voice,
        effective_voice_source=effective_source,
        effective_from=effective_from,
    )


async def update_voice_binding(
    db: AsyncSession,
    *,
    character: Character,
    body: VoiceBindingUpdate,
    bound_by: int | None = None,
) -> Character:
    """绑定/修改/解除角色音色；不触碰视觉身份锁定。"""
    if body.voice_id is not None:
        voice_id = body.voice_id.strip()
        character.voice_id = voice_id or None
    if body.voice_source is not None:
        source = body.voice_source.strip()
        if source and source not in {"preset", "custom"}:
            raise ValueError("voice_source 只支持 preset / custom")
        character.voice_source = source or None
    if body.voice_description is not None:
        character.voice_description = body.voice_description
    character.voice_bound_at = datetime.now(UTC)
    character.voice_bound_by = bound_by
    await db.flush()
    return character


__all__ = [
    "LOCKED_IDENTITY_FIELDS",
    "assert_identity_fields_editable",
    "get_voice_binding",
    "is_identity_locked",
    "lock_identity",
    "update_voice_binding",
]
