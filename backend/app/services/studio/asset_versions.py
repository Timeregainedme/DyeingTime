"""P4：资产基础版本、角色身份版本与衍生版本。

版本是业务主实体的快照，不是第二套资产实体：
- Character 的 identity 版本 = 视觉身份基准；appearance 版本 = 造型变体；
- Scene/Prop/Costume 的 base 版本 = 当前基础资产；derived 版本 = 光照/破损/雨淋等变体；
- 正式采纳版本不原地覆盖；切换只移动当前指针，旧版本保留。
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.studio import (
    AssetImageCandidate,
    AssetVersion,
    Character,
    Costume,
    ProjectCostumeLink,
    ProjectPropLink,
    ProjectSceneLink,
    Prop,
    Scene,
)
from app.schemas.studio.asset_versions import (
    AssetVersionRead,
    CreateDerivedVersionRequest,
    SwitchVersionRequest,
)

ASSET_MODELS = {
    "character": Character,
    "scene": Scene,
    "prop": Prop,
    "costume": Costume,
}
_ASSET_LINK_MODELS = {
    "scene": (ProjectSceneLink, "scene_id"),
    "prop": (ProjectPropLink, "prop_id"),
    "costume": (ProjectCostumeLink, "costume_id"),
}


def normalize_asset_type(asset_type: str) -> str:
    value = (asset_type or "").strip().lower()
    if value not in ASSET_MODELS:
        raise ValueError("asset_type 只支持 character / scene / prop / costume")
    return value


async def get_asset(db: AsyncSession, *, asset_type: str, asset_id: str):
    """读取主实体；不存在返回 None。"""
    return await db.get(ASSET_MODELS[normalize_asset_type(asset_type)], asset_id)


async def asset_belongs_to_project(
    db: AsyncSession,
    *,
    asset_type: str,
    asset_id: str,
    project_id: str,
) -> bool:
    """校验资产属于项目：Character 直挂 project_id，其余经项目关联表。"""
    normalized = normalize_asset_type(asset_type)
    asset = await get_asset(db, asset_type=normalized, asset_id=asset_id)
    if asset is None:
        return False
    if normalized == "character":
        return asset.project_id == project_id
    link_model, field = _ASSET_LINK_MODELS[normalized]
    row = (
        await db.execute(
            select(link_model.id)
            .where(
                link_model.project_id == project_id,
                getattr(link_model, field) == asset_id,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    return row is not None


def _character_attributes(character: Character) -> dict[str, Any]:
    return {
        "age_range": character.age_range or "",
        "appearance": character.appearance or "",
        "face_features": character.face_features or "",
        "body_type": character.body_type or "",
        "identity_features": character.identity_features or "",
    }


async def _next_version_no(
    db: AsyncSession, *, asset_type: str, asset_id: str
) -> int:
    current = (
        await db.execute(
            select(func.max(AssetVersion.version_no)).where(
                AssetVersion.asset_type == asset_type,
                AssetVersion.asset_id == asset_id,
            )
        )
    ).scalar_one_or_none()
    return int(current or 0) + 1


async def _find_active_version(
    db: AsyncSession, *, asset_type: str, asset_id: str
) -> AssetVersion | None:
    return (
        await db.execute(
            select(AssetVersion)
            .where(
                AssetVersion.asset_type == asset_type,
                AssetVersion.asset_id == asset_id,
                AssetVersion.status == "active",
            )
            .order_by(AssetVersion.version_no.desc())
            .limit(1)
        )
    ).scalars().first()


async def ensure_base_version(
    db: AsyncSession,
    *,
    asset_type: str,
    asset_id: str,
    source: str = "manual",
    created_by: int | None = None,
) -> AssetVersion:
    """按需补齐基础版本；存量资产没有版本时仍可读取并自动初始化。

    角色初始化 identity 版本，场景/道具/服装初始化 base 版本。
    """
    normalized = normalize_asset_type(asset_type)
    asset = await get_asset(db, asset_type=normalized, asset_id=asset_id)
    if asset is None:
        raise ValueError("资产不存在")

    pointer = (
        asset.identity_version_id if normalized == "character" else asset.current_version_id
    )
    if pointer:
        existing = await db.get(AssetVersion, pointer)
        if existing is not None:
            return existing

    active = await _find_active_version(db, asset_type=normalized, asset_id=asset_id)
    if active is not None:
        if normalized == "character":
            asset.identity_version_id = active.id
        else:
            asset.current_version_id = active.id
        await db.flush()
        return active

    version_no = await _next_version_no(
        db, asset_type=normalized, asset_id=asset_id
    )
    description = (
        (asset.description or "")
        if normalized != "character"
        else (asset.description or asset.appearance or "")
    )
    version = AssetVersion(
        id=str(uuid.uuid4()),
        project_id=asset.project_id
        if normalized == "character"
        else await _first_project_id(db, asset_type=normalized, asset_id=asset_id),
        asset_type=normalized,
        asset_id=asset_id,
        version_no=version_no,
        version_kind="identity" if normalized == "character" else "base",
        variant_type="base",
        name=asset.name,
        description=description,
        attributes=_character_attributes(asset) if normalized == "character" else {},
        source=source,
        status="active",
        created_by=created_by,
    )
    if not version.project_id:
        raise ValueError("无法确定资产所属项目")
    db.add(version)
    await db.flush()
    if normalized == "character":
        asset.identity_version_id = version.id
    else:
        asset.current_version_id = version.id
    await db.flush()
    return version


async def _first_project_id(
    db: AsyncSession, *, asset_type: str, asset_id: str
) -> str | None:
    link_model, field = _ASSET_LINK_MODELS[normalize_asset_type(asset_type)]
    return (
        await db.execute(
            select(link_model.project_id)
            .where(getattr(link_model, field) == asset_id)
            .order_by(link_model.id.asc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def list_versions(
    db: AsyncSession,
    *,
    asset_type: str,
    asset_id: str,
) -> list[AssetVersion]:
    return list(
        (
            await db.execute(
                select(AssetVersion)
                .where(
                    AssetVersion.asset_type == normalize_asset_type(asset_type),
                    AssetVersion.asset_id == asset_id,
                )
                .order_by(AssetVersion.version_no.desc())
            )
        ).scalars().all()
    )


async def version_to_read(
    db: AsyncSession, version: AssetVersion
) -> AssetVersionRead:
    adopted = (
        await db.execute(
            select(func.count(AssetImageCandidate.id)).where(
                AssetImageCandidate.asset_version_id == version.id,
                AssetImageCandidate.is_adopted.is_(True),
            )
        )
    ).scalar_one()
    return AssetVersionRead(
        **{
            **AssetVersionRead.model_validate(version).model_dump(),
            "adopted_image_count": int(adopted or 0),
        }
    )


async def create_derived_version(
    db: AsyncSession,
    *,
    asset_type: str,
    asset_id: str,
    body: CreateDerivedVersionRequest,
    created_by: int | None = None,
) -> AssetVersion:
    """从当前版本创建造型/衍生版本；默认激活，但绝不修改父版本内容。"""
    normalized = normalize_asset_type(asset_type)
    base = await ensure_base_version(db, asset_type=normalized, asset_id=asset_id)
    parent_id = body.parent_version_id or base.id
    parent = await db.get(AssetVersion, parent_id)
    if parent is None or parent.asset_type != normalized or parent.asset_id != asset_id:
        raise ValueError("父版本不属于当前资产")
    if normalized == "character":
        version_kind = "appearance"
    else:
        version_kind = "derived"
    attributes = dict(body.attributes or {})
    if body.costume_id:
        if await db.get(Costume, body.costume_id) is None:
            raise ValueError("服装不存在")
        attributes["costume_id"] = body.costume_id
    version = AssetVersion(
        id=str(uuid.uuid4()),
        project_id=base.project_id,
        asset_type=normalized,
        asset_id=asset_id,
        version_no=await _next_version_no(db, asset_type=normalized, asset_id=asset_id),
        parent_version_id=parent.id,
        version_kind=version_kind,
        variant_type=body.variant_type,
        name=body.name.strip(),
        description=body.description or "",
        attributes=attributes,
        source="manual",
        status="active" if body.activate else "draft",
        created_by=created_by,
    )
    db.add(version)
    await db.flush()
    if body.activate:
        await switch_current_version(
            db,
            asset_type=normalized,
            asset_id=asset_id,
            body=SwitchVersionRequest(version_id=version.id),
            switched_by=created_by,
        )
        await db.refresh(version)
    return version


async def create_identity_version(
    db: AsyncSession,
    *,
    asset_id: str,
    name: str,
    description: str = "",
    attributes: dict[str, Any] | None = None,
    created_by: int | None = None,
) -> AssetVersion:
    """为角色创建新的身份草稿版本；旧身份版本保留。

    新版本必须补采纳正面图后，才能通过 switch 切换并递增 identity_lock_version。
    """
    asset = await db.get(Character, asset_id)
    if asset is None:
        raise ValueError("角色不存在")
    parent = await ensure_base_version(
        db, asset_type="character", asset_id=asset_id
    )
    version = AssetVersion(
        id=str(uuid.uuid4()),
        project_id=asset.project_id,
        asset_type="character",
        asset_id=asset_id,
        version_no=await _next_version_no(
            db, asset_type="character", asset_id=asset_id
        ),
        parent_version_id=parent.id,
        version_kind="identity",
        variant_type="base",
        name=name.strip() or asset.name,
        description=description or "",
        attributes=dict(attributes or {}),
        source="manual",
        status="draft",
        created_by=created_by,
    )
    db.add(version)
    await db.flush()
    return version


async def switch_current_version(
    db: AsyncSession,
    *,
    asset_type: str,
    asset_id: str,
    body: SwitchVersionRequest,
    switched_by: int | None = None,
) -> AssetVersion:
    """切换当前版本指针；旧版本保留，不删除历史。"""
    normalized = normalize_asset_type(asset_type)
    asset = await get_asset(db, asset_type=normalized, asset_id=asset_id)
    if asset is None:
        raise ValueError("资产不存在")
    version = await db.get(AssetVersion, body.version_id)
    if version is None or version.asset_type != normalized or version.asset_id != asset_id:
        raise ValueError("版本不属于当前资产")
    has_adopted_front = (
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
    if version.status == "draft":
        # 身份草稿只有在已有采纳正面图时才允许通过「切换」完成确认；
        # 造型/资产草稿不能绕过采纳直接生效。
        if not (
            normalized == "character"
            and version.version_kind == "identity"
            and has_adopted_front is not None
        ):
            raise ValueError("草稿版本尚未确认，不能切换为当前版本")

    if normalized == "character":
        expected = body.expected_lock_version
        if expected is not None and int(asset.identity_lock_version or 0) != expected:
            raise ValueError("角色身份已被其他操作修改，请刷新后重试")
        if version.version_kind == "identity":
            if has_adopted_front is None:
                raise ValueError("身份版本缺少已采纳正面图，不能切换")
            if asset.identity_version_id != version.id:
                asset.identity_version_id = version.id
                asset.identity_lock_version = int(asset.identity_lock_version or 0) + 1
        else:
            asset.current_appearance_version_id = version.id
            if version.status != "active":
                version.status = "active"
    else:
        if version.status != "active":
            version.status = "active"
        asset.current_version_id = version.id

    if normalized == "character" and version.version_kind == "identity":
        # 同资产其它 identity 版本只保留历史，不自动删除。
        rows = (
            await db.execute(
                select(AssetVersion).where(
                    AssetVersion.asset_type == normalized,
                    AssetVersion.asset_id == asset_id,
                    AssetVersion.version_kind == "identity",
                    AssetVersion.id != version.id,
                    AssetVersion.status == "active",
                )
            )
        ).scalars().all()
        for row in rows:
            row.status = "superseded"
    elif normalized != "character":
        rows = (
            await db.execute(
                select(AssetVersion).where(
                    AssetVersion.asset_type == normalized,
                    AssetVersion.asset_id == asset_id,
                    AssetVersion.id != version.id,
                    AssetVersion.status == "active",
                )
            )
        ).scalars().all()
        for row in rows:
            row.status = "superseded"
    version.status = "active"
    await db.flush()
    return version


async def delete_version(
    db: AsyncSession,
    *,
    asset_type: str,
    asset_id: str,
    version_id: str,
) -> None:
    """删除未被引用的草稿版本；当前/身份版本拒绝删除。"""
    normalized = normalize_asset_type(asset_type)
    asset = await get_asset(db, asset_type=normalized, asset_id=asset_id)
    if asset is None:
        raise ValueError("资产不存在")
    version = await db.get(AssetVersion, version_id)
    if version is None or version.asset_type != normalized or version.asset_id != asset_id:
        raise ValueError("版本不属于当前资产")
    if version.status == "active" or getattr(asset, "identity_version_id", None) == version.id:
        raise ValueError("当前/身份版本不可删除，请保留历史")
    adopted_count = (
        await db.execute(
            select(func.count(AssetImageCandidate.id)).where(
                AssetImageCandidate.asset_version_id == version.id,
                AssetImageCandidate.is_adopted.is_(True),
            )
        )
    ).scalar_one()
    if adopted_count:
        raise ValueError("版本已有采纳图片，不能删除")
    await db.delete(version)
    await db.flush()


__all__ = [
    "ASSET_MODELS",
    "asset_belongs_to_project",
    "create_derived_version",
    "create_identity_version",
    "delete_version",
    "ensure_base_version",
    "get_asset",
    "list_versions",
    "normalize_asset_type",
    "switch_current_version",
    "version_to_read",
]
