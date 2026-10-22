"""P4：资产档案聚合读取与文字字段更新。"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.studio import (
    AssetImageCandidate,
    AssetVersion,
    Character,
    CharacterImage,
    CostumeImage,
    FileItem,
    PropImage,
    SceneImage,
)
from app.schemas.studio.asset_versions import (
    AssetImageCandidateRead,
    AssetProfileRead,
    AssetProfileUpdate,
    CharacterAliasRead,
)
from app.services.studio.asset_versions import (
    asset_belongs_to_project,
    ensure_base_version,
    get_asset,
    list_versions,
    normalize_asset_type,
    version_to_read,
)
from app.services.studio.character_aliases import list_aliases
from app.services.studio.character_identity import (
    assert_identity_fields_editable,
    get_voice_binding,
    is_identity_locked,
)

_IMAGE_MODELS = {
    "character": (CharacterImage, "character_id"),
    "scene": (SceneImage, "scene_id"),
    "prop": (PropImage, "prop_id"),
    "costume": (CostumeImage, "costume_id"),
}


def _candidate_read(
    candidate: AssetImageCandidate, file_urls: dict[str, str]
) -> AssetImageCandidateRead:
    return AssetImageCandidateRead(
        **{
            **AssetImageCandidateRead.model_validate(candidate).model_dump(),
            "file_url": file_urls.get(candidate.file_id or "", ""),
        }
    )


async def _thumbnail_file_id(
    db: AsyncSession, *, asset_type: str, asset_id: str, candidates: list[AssetImageCandidate]
) -> str | None:
    for candidate in candidates:
        if candidate.is_adopted and candidate.view_angle == "front" and candidate.file_id:
            return candidate.file_id
    image_model, parent_field = _IMAGE_MODELS[asset_type]
    row = (
        await db.execute(
            select(image_model)
            .where(getattr(image_model, parent_field) == asset_id)
            .order_by(
                getattr(image_model, "is_primary").desc()
                if hasattr(image_model, "is_primary")
                else image_model.id.asc()
            )
            .limit(1)
        )
    ).scalars().first()
    return getattr(row, "file_id", None) if row is not None else None


async def build_asset_profile(
    db: AsyncSession,
    *,
    project_id: str,
    asset_type: str,
    asset_id: str,
) -> AssetProfileRead:
    """聚合主实体、当前版本、版本历史、候选图、别名与音色。"""
    normalized = normalize_asset_type(asset_type)
    if not await asset_belongs_to_project(
        db, asset_type=normalized, asset_id=asset_id, project_id=project_id
    ):
        raise ValueError("资产不存在或不属于当前项目")
    asset = await get_asset(db, asset_type=normalized, asset_id=asset_id)
    if asset is None:
        raise ValueError("资产不存在")
    await ensure_base_version(db, asset_type=normalized, asset_id=asset_id)
    versions = await list_versions(db, asset_type=normalized, asset_id=asset_id)
    versions_read = [await version_to_read(db, item) for item in versions]
    candidates = list(
        (
            await db.execute(
                select(AssetImageCandidate)
                .where(
                    AssetImageCandidate.asset_type == normalized,
                    AssetImageCandidate.asset_id == asset_id,
                )
                .order_by(
                    AssetImageCandidate.created_at.desc(),
                    AssetImageCandidate.id.desc(),
                )
            )
        ).scalars().all()
    )
    file_ids = [item.file_id for item in candidates if item.file_id]
    thumbnail_file_id = await _thumbnail_file_id(
        db, asset_type=normalized, asset_id=asset_id, candidates=candidates
    )
    if thumbnail_file_id:
        file_ids.append(thumbnail_file_id)
    file_urls: dict[str, str] = {}
    if file_ids:
        rows = (
            await db.execute(select(FileItem).where(FileItem.id.in_(set(file_ids))))
        ).scalars().all()
        file_urls = {item.id: item.thumbnail or "" for item in rows}

    base = AssetProfileRead(
        project_id=project_id,
        asset_type=normalized,
        asset_id=asset_id,
        name=asset.name or "",
        description=asset.description or "",
        style=str(getattr(asset.style, "value", asset.style) or ""),
        visual_style=str(
            getattr(asset.visual_style, "value", asset.visual_style) or ""
        ),
        tags=list(getattr(asset, "tags", None) or []),
        thumbnail=file_urls.get(thumbnail_file_id or "", ""),
        current_version_id=(
            asset.identity_version_id
            if normalized == "character"
            else asset.current_version_id
        ),
        versions=versions_read,
        candidates=[_candidate_read(item, file_urls) for item in candidates],
    )
    if normalized != "character":
        return base

    character: Character = asset
    aliases = await list_aliases(db, character_id=character.id)
    voice = await get_voice_binding(db, character=character)
    return base.model_copy(
        update={
            "age_range": character.age_range or "",
            "appearance": character.appearance or "",
            "face_features": character.face_features or "",
            "body_type": character.body_type or "",
            "identity_features": character.identity_features or "",
            "aliases": [
                CharacterAliasRead.model_validate(item) for item in aliases
            ],
            "identity_version_id": character.identity_version_id,
            "current_appearance_version_id": character.current_appearance_version_id,
            "identity_locked_at": character.identity_locked_at,
            "identity_lock_version": int(character.identity_lock_version or 0),
            "identity_locked": is_identity_locked(character),
            "voice_id": character.voice_id,
            "voice_source": character.voice_source,
            "voice_description": character.voice_description or "",
            "effective_voice_id": voice.effective_voice_id,
            "effective_voice_source": voice.effective_voice_source,
            "voice_bound_at": character.voice_bound_at,
        }
    )


async def _create_refresh_base_version(
    db: AsyncSession,
    *,
    asset_type: str,
    asset: Any,
    created_by: int | None = None,
) -> AssetVersion:
    """非角色资产文字变化时生成新基础版本，保留旧版本快照。"""
    current = (
        await db.get(AssetVersion, asset.current_version_id)
        if asset.current_version_id
        else None
    )
    if current is None:
        current = await ensure_base_version(
            db, asset_type=asset_type, asset_id=asset.id
        )
    max_no = (
        await db.execute(
            select(func.max(AssetVersion.version_no)).where(
                AssetVersion.asset_type == asset_type,
                AssetVersion.asset_id == asset.id,
            )
        )
    ).scalar_one_or_none()
    version = AssetVersion(
        id=str(uuid.uuid4()),
        project_id=current.project_id,
        asset_type=asset_type,
        asset_id=asset.id,
        version_no=int(max_no or 0) + 1,
        parent_version_id=current.id,
        version_kind=current.version_kind,
        variant_type=current.variant_type,
        name=asset.name,
        description=asset.description or "",
        attributes=dict(current.attributes or {}),
        source="manual",
        status="active",
        created_by=created_by,
    )
    db.add(version)
    await db.flush()
    current.status = "superseded"
    asset.current_version_id = version.id
    await db.flush()
    return version


async def update_asset_profile(
    db: AsyncSession,
    *,
    project_id: str,
    asset_type: str,
    asset_id: str,
    body: AssetProfileUpdate,
    updated_by: int | None = None,
) -> AssetProfileRead:
    """更新文字字段；锁定角色拒绝核心身份字段，旧版本内容不被修改。"""
    normalized = normalize_asset_type(asset_type)
    if not await asset_belongs_to_project(
        db, asset_type=normalized, asset_id=asset_id, project_id=project_id
    ):
        raise ValueError("资产不存在或不属于当前项目")
    asset = await get_asset(db, asset_type=normalized, asset_id=asset_id)
    if asset is None:
        raise ValueError("资产不存在")
    await ensure_base_version(db, asset_type=normalized, asset_id=asset_id)
    data = body.model_dump(exclude_unset=True)

    if normalized == "character":
        assert_identity_fields_editable(asset, data)
        identity = await db.get(AssetVersion, asset.identity_version_id)
        for key in (
            "name",
            "description",
            "age_range",
            "appearance",
            "face_features",
            "body_type",
            "identity_features",
            "tags",
            "costume_id",
            "actor_id",
        ):
            if key in data:
                if data[key] is None and key not in {"costume_id", "actor_id"}:
                    continue
                setattr(asset, key, data[key])
        if identity is not None and asset.identity_locked_at is None:
            identity.name = asset.name
            identity.description = asset.description or asset.appearance or ""
            identity.attributes = {
                "age_range": asset.age_range or "",
                "appearance": asset.appearance or "",
                "face_features": asset.face_features or "",
                "body_type": asset.body_type or "",
                "identity_features": asset.identity_features or "",
            }
        await db.flush()
    else:
        core_changed = any(
            key in data and data[key] != getattr(asset, key)
            for key in ("name", "description")
        )
        for key in ("name", "description", "tags"):
            if key in data and data[key] is not None:
                setattr(asset, key, data[key])
        await db.flush()
        if core_changed:
            await _create_refresh_base_version(
                db, asset_type=normalized, asset=asset, created_by=updated_by
            )
    return await build_asset_profile(
        db,
        project_id=project_id,
        asset_type=normalized,
        asset_id=asset_id,
    )


__all__ = ["build_asset_profile", "update_asset_profile"]
