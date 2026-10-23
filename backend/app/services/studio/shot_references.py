"""P6 / C11：镜头参考绑定、@ 引用、H3 同源预览与生成快照。"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.chains.prompts.ir import IRAudioReference, IRReference
from app.core import storage
from app.models.studio import (
    AssetImageCandidate,
    AssetVersion,
    Chapter,
    Character,
    CharacterImage,
    Costume,
    CostumeImage,
    FileItem,
    FileType,
    FileUsageKind,
    Project,
    Prop,
    PropImage,
    Scene,
    SceneImage,
    Shot,
    ShotAssetVersion,
    ShotDetail,
    ShotDialogLine,
    ShotGenerationSnapshot,
    ShotPromptReference,
    ShotReferenceBinding,
)
from app.schemas.studio.shots import ShotVideoQualityCheck
from app.schemas.studio.shot_references import (
    GenerationPreviewRead,
    GenerationSnapshotRead,
    P6VideoGenerateRequest,
    PromptReferenceRead,
    PromptResolveRead,
    ReferenceBindingRead,
)
from app.services.studio.character_aliases import list_aliases
from app.services.studio.file_usages import upsert_file_usage
from app.services.studio.generation.video import (
    REFERENCE_MODE,
    build_video_base_draft,
    build_video_context,
    derive_video_preview,
)
from app.services.studio.generation.video.build_base import VideoBaseDraft
from app.services.studio.shot_video_prompt_pack import build_shot_video_prompt_pack

MAX_REFERENCE_IMAGES = 9
MAX_REFERENCE_AUDIOS = 3
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_IMAGE_CT = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}
_ASSET_MODELS = {
    "character": Character,
    "scene": Scene,
    "prop": Prop,
    "costume": Costume,
}
_ROLE_PRIORITY = {
    "character_identity": 0,
    "character_appearance": 1,
    "scene": 2,
    "prop": 3,
    "costume": 4,
    "shot_composition": 5,
    "previous_shot": 6,
}


def _normalize(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _sha(data: Any) -> str:
    return hashlib.sha256(
        (data if isinstance(data, str) else str(data)).encode("utf-8")
    ).hexdigest()


def _image_suffix(filename: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in _IMAGE_EXT:
        raise ValueError("只支持 jpg/jpeg/png/webp/gif")
    return ".jpg" if suffix == ".jpeg" else suffix


def _validate_image(filename: str, content: bytes) -> str:
    suffix = _image_suffix(filename)
    if not content or len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("图片为空或超过 15MB")
    head = content[:16]
    ok = (
        (suffix in {".jpg"} and head.startswith(b"\xff\xd8\xff"))
        or (suffix == ".png" and head.startswith(b"\x89PNG\r\n\x1a\n"))
        or (suffix == ".gif" and head[:6] in {b"GIF87a", b"GIF89a"})
        or (suffix == ".webp" and head[:4] == b"RIFF" and head[8:12] == b"WEBP")
    )
    if not ok:
        raise ValueError("图片内容与扩展名不匹配")
    return suffix


async def _file_urls(db: AsyncSession, ids: list[str]) -> dict[str, str]:
    if not ids:
        return {}
    rows = (await db.execute(select(FileItem).where(FileItem.id.in_(set(ids))))).scalars().all()
    return {item.id: item.thumbnail or "" for item in rows}


async def list_bindings(
    db: AsyncSession, *, shot_id: str, active_only: bool = False
) -> list[ReferenceBindingRead]:
    stmt = select(ShotReferenceBinding).where(ShotReferenceBinding.shot_id == shot_id)
    if active_only:
        stmt = stmt.where(ShotReferenceBinding.is_active.is_(True))
    rows = (
        await db.execute(
            stmt.order_by(ShotReferenceBinding.is_active.desc(), ShotReferenceBinding.sort_order.asc(), ShotReferenceBinding.id.asc())
        )
    ).scalars().all()
    urls = await _file_urls(db, [item.file_id for item in rows if item.file_id])
    names: dict[tuple[str, str], str] = {}
    for row in rows:
        if not row.asset_id or not row.asset_type:
            continue
        key = (row.asset_type, row.asset_id)
        if key in names:
            continue
        model = _ASSET_MODELS.get(row.asset_type)
        if model is not None:
            asset = await db.get(model, row.asset_id)
            if asset is not None:
                names[key] = asset.name
    return [
        ReferenceBindingRead(
            id=item.id,
            shot_id=item.shot_id,
            file_id=item.file_id,
            file_url=urls.get(item.file_id or "", ""),
            asset_type=item.asset_type,
            asset_id=item.asset_id,
            asset_name=names.get((item.asset_type, item.asset_id or ""), ""),
            asset_version_id=item.asset_version_id,
            reference_role=item.reference_role,
            source=item.source,
            sort_order=item.sort_order,
            is_pinned=item.is_pinned,
            is_active=item.is_active,
        )
        for item in rows
    ]


async def _version_file_ids(
    db: AsyncSession, *, asset_type: str, asset_id: str, version_id: str | None
) -> list[str]:
    if version_id:
        rows = (
            await db.execute(
                select(AssetImageCandidate)
                .where(
                    AssetImageCandidate.asset_version_id == version_id,
                    AssetImageCandidate.is_adopted.is_(True),
                    AssetImageCandidate.file_id.is_not(None),
                )
                .order_by(AssetImageCandidate.view_angle.asc(), AssetImageCandidate.id.asc())
            )
        ).scalars().all()
        if rows:
            # 身份版本最多两张（正面 + 一个辅助视角），其它版本一张。
            if asset_type == "character":
                return [row.file_id for row in rows[:2] if row.file_id]
            return [rows[0].file_id] if rows[0].file_id else []
    # 旧资产兜底只在该版本是当前版本时使用，避免把旧版本绑定到最新图。
    if asset_type == "character":
        character = await db.get(Character, asset_id)
        if character is None:
            return []
        if version_id and version_id not in {
            character.identity_version_id,
            character.current_appearance_version_id,
        }:
            return []
        image = (
            await db.execute(
                select(CharacterImage)
                .where(CharacterImage.character_id == asset_id, CharacterImage.file_id.is_not(None))
                .order_by(CharacterImage.is_primary.desc(), CharacterImage.id.asc())
                .limit(1)
            )
        ).scalars().first()
        return [image.file_id] if image and image.file_id else []
    model, image_model, field = {
        "scene": (Scene, SceneImage, "scene_id"),
        "prop": (Prop, PropImage, "prop_id"),
        "costume": (Costume, CostumeImage, "costume_id"),
    }[asset_type]
    asset = await db.get(model, asset_id)
    current = getattr(asset, "current_version_id", None) if asset else None
    if version_id and current and version_id != current:
        return []
    if version_id and current is None:
        return []
    image = (
        await db.execute(
            select(image_model)
            .where(getattr(image_model, field) == asset_id, image_model.file_id.is_not(None))
            .order_by(image_model.id.asc())
            .limit(1)
        )
    ).scalars().first()
    return [image.file_id] if image and image.file_id else []


async def auto_recommend(
    db: AsyncSession, *, shot_id: str, created_by: int | None = None
) -> list[ReferenceBindingRead]:
    """按 P5 镜头资产版本推荐参考图；不覆盖人工绑定/删除决定。"""
    shot = await db.get(Shot, shot_id)
    if shot is None:
        raise ValueError("镜头不存在")
    rows = (
        await db.execute(
            select(ShotAssetVersion)
            .where(ShotAssetVersion.shot_id == shot_id)
            .order_by(ShotAssetVersion.asset_type.asc(), ShotAssetVersion.slot.asc())
        )
    ).scalars().all()
    recommendations: list[tuple[Any, str]] = []
    for row in sorted(rows, key=lambda item: _ROLE_PRIORITY.get(item.role, 9)):
        files = await _version_file_ids(
            db,
            asset_type=row.asset_type,
            asset_id=row.asset_id,
            version_id=row.asset_version_id,
        )
        for file_id in files[:2] if row.asset_type == "character" else files[:1]:
            recommendations.append((row, file_id))
    if not recommendations:
        raise ValueError("镜头还没有可用的资产版本参考图，请先完成 P4/P5 资产图与版本")

    existing = (
        await db.execute(select(ShotReferenceBinding).where(ShotReferenceBinding.shot_id == shot_id))
    ).scalars().all()
    by_file = {item.file_id: item for item in existing if item.file_id}
    next_order = max((item.sort_order for item in existing if item.is_active), default=-1) + 1
    active_count = sum(1 for item in existing if item.is_active)
    for row, file_id in recommendations:
        current = by_file.get(file_id)
        if current is not None:
            # 人工删除过的自动项不会因再次推荐而恢复。
            continue
        if active_count >= MAX_REFERENCE_IMAGES:
            break
        binding = ShotReferenceBinding(
            shot_id=shot_id,
            file_id=file_id,
            asset_type=row.asset_type,
            asset_id=row.asset_id,
            asset_version_id=row.asset_version_id,
            reference_role=row.role,
            source="auto",
            sort_order=next_order,
            is_pinned=False,
            is_active=True,
            created_by=created_by,
        )
        db.add(binding)
        by_file[file_id] = binding
        next_order += 1
        active_count += 1
    await db.flush()
    return await active_bindings(db, shot_id=shot_id)


async def active_bindings(db: AsyncSession, *, shot_id: str) -> list[ReferenceBindingRead]:
    rows = await list_bindings(db, shot_id=shot_id, active_only=True)
    return [item for item in rows if item.is_active]


async def update_binding(
    db: AsyncSession,
    *,
    binding_id: int,
    shot_id: str,
    is_pinned: bool | None = None,
    is_active: bool | None = None,
    reference_role: str | None = None,
) -> ReferenceBindingRead:
    binding = await db.get(ShotReferenceBinding, binding_id)
    if binding is None or binding.shot_id != shot_id:
        raise ValueError("参考绑定不存在")
    if is_active is False and binding.is_pinned:
        raise ValueError("已锁定参考图不能直接删除，请先取消锁定")
    if is_pinned is not None:
        binding.is_pinned = is_pinned
    if is_active is not None:
        binding.is_active = is_active
    if reference_role is not None:
        binding.reference_role = reference_role
    await db.flush()
    result = await list_bindings(db, shot_id=shot_id)
    return next(item for item in result if item.id == binding.id)


async def remove_binding(db: AsyncSession, *, binding_id: int, shot_id: str) -> None:
    binding = await db.get(ShotReferenceBinding, binding_id)
    if binding is None or binding.shot_id != shot_id:
        raise ValueError("参考绑定不存在")
    if binding.is_pinned:
        raise ValueError("已锁定参考图不能直接删除，请先取消锁定")
    binding.is_active = False
    await db.flush()


async def reorder_bindings(
    db: AsyncSession, *, shot_id: str, binding_ids: list[int]
) -> list[ReferenceBindingRead]:
    rows = (
        await db.execute(select(ShotReferenceBinding).where(ShotReferenceBinding.shot_id == shot_id))
    ).scalars().all()
    by_id = {item.id: item for item in rows}
    if set(binding_ids) != {item.id for item in rows if item.is_active}:
        raise ValueError("排序必须包含全部启用中的参考绑定")
    for index, binding_id in enumerate(binding_ids):
        by_id[binding_id].sort_order = -index - 1
    await db.flush()
    for index, binding_id in enumerate(binding_ids):
        by_id[binding_id].sort_order = index
    await db.flush()
    return await active_bindings(db, shot_id=shot_id)


async def upload_reference(
    db: AsyncSession,
    *,
    shot_id: str,
    file: UploadFile,
    reference_role: str = "shot_composition",
    created_by: int | None = None,
) -> ReferenceBindingRead:
    content = await file.read()
    suffix = _validate_image(file.filename or "", content)
    shot = await db.get(Shot, shot_id)
    if shot is None:
        raise ValueError("镜头不存在")
    key = f"shot-references/{shot.chapter_id}/{shot_id}/{uuid.uuid4().hex}{suffix}"
    info = await storage.upload_file(
        key=key,
        data=content,
        content_type=_IMAGE_CT.get(suffix, "application/octet-stream"),
        extra_args={"ACL": "public-read"},
    )
    file_item = FileItem(
        id=str(uuid.uuid4()),
        type=FileType.image,
        name=Path(file.filename or f"reference{suffix}").name,
        thumbnail=info.url,
        tags=[],
        storage_key=key,
    )
    db.add(file_item)
    await db.flush()
    project_id = await _project_id_for_shot(db, shot_id)
    if project_id:
        await upsert_file_usage(
            db,
            file_id=file_item.id,
            project_id=project_id,
            chapter_id=shot.chapter_id,
            shot_id=shot_id,
            usage_kind=FileUsageKind.asset_image,
            source_ref=f"shot_reference:{shot_id}:{file_item.id}",
        )
    max_order = int(
        await db.scalar(
            select(ShotReferenceBinding.sort_order)
            .where(ShotReferenceBinding.shot_id == shot_id)
            .order_by(ShotReferenceBinding.sort_order.desc())
            .limit(1)
        )
        or -1
    )
    binding = ShotReferenceBinding(
        shot_id=shot_id,
        file_id=file_item.id,
        asset_type="shot_reference",
        reference_role=reference_role,
        source="uploaded",
        sort_order=max_order + 1,
        is_pinned=True,
        is_active=True,
        created_by=created_by,
    )
    db.add(binding)
    await db.flush()
    result = await list_bindings(db, shot_id=shot_id)
    return next(item for item in result if item.id == binding.id)


async def _project_id_for_shot(db: AsyncSession, shot_id: str) -> str | None:
    from app.models.studio import Chapter

    shot = await db.get(Shot, shot_id)
    if shot is None:
        return None
    chapter = await db.get(Chapter, shot.chapter_id)
    return chapter.project_id if chapter else None


async def _asset_name_version(
    db: AsyncSession, *, asset_type: str, asset_id: str
) -> tuple[str, str | None]:
    model = _ASSET_MODELS.get(asset_type)
    if model is None:
        return "", None
    asset = await db.get(model, asset_id)
    if asset is None:
        return "", None
    version = (
        asset.identity_version_id
        if asset_type == "character"
        else getattr(asset, "current_version_id", None)
    )
    return asset.name, version


async def build_manifest(
    db: AsyncSession, *, shot_id: str
) -> tuple[list[IRReference], list[dict[str, Any]], list[str]]:
    rows = (
        await db.execute(
            select(ShotReferenceBinding)
            .where(
                ShotReferenceBinding.shot_id == shot_id,
                ShotReferenceBinding.is_active.is_(True),
            )
            .order_by(ShotReferenceBinding.sort_order.asc(), ShotReferenceBinding.id.asc())
        )
    ).scalars().all()
    warnings: list[str] = []
    if len(rows) > MAX_REFERENCE_IMAGES:
        warnings.append(
            f"参考图超过 H3 上限：{len(rows)} > {MAX_REFERENCE_IMAGES}，请先删除/禁用低优先级参考图"
        )
    manifest: list[dict[str, Any]] = []
    refs: list[IRReference] = []
    for index, row in enumerate(rows, start=1):
        if not row.file_id:
            warnings.append(f"参考绑定 #{row.id} 缺少文件")
            continue
        file_item = await db.get(FileItem, row.file_id)
        if file_item is None:
            warnings.append(f"参考文件不存在：{row.file_id}")
            continue
        name = ""
        if row.asset_id:
            name, _ = await _asset_name_version(
                db, asset_type=row.asset_type, asset_id=row.asset_id
            )
        if not name:
            name = row.reference_role or "镜头参考"
        token = f"图{index}"
        kind = "frame" if row.reference_role in {"shot_composition", "previous_shot"} else row.asset_type
        binding_line = f"{token} 为「{name}」的{row.reference_role}参考。"
        refs.append(
            IRReference(
                token=token,
                kind=kind,  # type: ignore[arg-type]
                name=name,
                ref_id=row.asset_id or "",
                file_id=row.file_id,
                binding=binding_line,
            )
        )
        manifest.append(
            {
                "binding_id": row.id,
                "file_id": row.file_id,
                "file_url": file_item.thumbnail or "",
                "asset_type": row.asset_type,
                "asset_id": row.asset_id,
                "asset_version_id": row.asset_version_id,
                "reference_role": row.reference_role,
                "source": row.source,
                "sort_order": row.sort_order,
                "is_pinned": row.is_pinned,
            }
        )
    return refs, manifest, warnings


_AT_REF_RE = re.compile(r"@([^\s@，。,.!?;；：:（）()\[\]【】]+)")


async def resolve_prompt_references(
    db: AsyncSession, *, shot_id: str, prompt: str
) -> PromptResolveRead:
    shot = await db.get(Shot, shot_id)
    if shot is None:
        raise ValueError("镜头不存在")
    project_id = await _project_id_for_shot(db, shot_id)
    if project_id is None:
        raise ValueError("镜头缺少项目归属")
    characters = (
        await db.execute(select(Character).where(Character.project_id == project_id))
    ).scalars().all()
    lookup: dict[str, list[tuple[str, str, str | None]]] = {}

    def _add(name: str, target: tuple[str, str, str | None]) -> None:
        key = _normalize(name)
        if not key:
            return
        bucket = lookup.setdefault(key, [])
        if target not in bucket:
            bucket.append(target)

    for item in characters:
        target = ("character", item.id, item.identity_version_id)
        _add(item.name, target)
        for alias in await list_aliases(db, character_id=item.id):
            _add(alias.alias, target)
    for asset_type in ("scene", "prop", "costume"):
        model = _ASSET_MODELS[asset_type]
        rows = (
            await db.execute(select(model).where(model.name.is_not(None)))
        ).scalars().all()
        for item in rows:
            if await _project_asset(db, asset_type=asset_type, asset_id=item.id, project_id=project_id):
                _add(
                    item.name,
                    (asset_type, item.id, getattr(item, "current_version_id", None)),
                )
    # 角色改名后，历史 @ 引用仍按已保存的稳定对象解析。
    persisted_rows = (
        await db.execute(
            select(ShotPromptReference).where(ShotPromptReference.shot_id == shot_id)
        )
    ).scalars().all()
    persisted: dict[str, tuple[str, str, str | None]] = {}
    for item in persisted_rows:
        persisted.setdefault(
            _normalize(item.mention),
            (item.asset_type, item.asset_id, item.asset_version_id),
        )

    resolved: list[PromptReferenceRead] = []
    unresolved: list[str] = []
    warnings: list[str] = []
    for match in _AT_REF_RE.finditer(prompt or ""):
        mention = match.group(1)
        key = _normalize(mention)
        candidates = lookup.get(key, [])
        unique = list(dict.fromkeys(candidates))
        target: tuple[str, str, str | None] | None = None
        if len(unique) == 1:
            target = unique[0]
        elif len(unique) > 1:
            saved = persisted.get(key)
            if saved is not None and saved in unique:
                target = saved
            else:
                warnings.append(
                    f"@ {mention} 对应多个同名/别名资产，请人工选择后再生成"
                )
        if target is None:
            # 仅使用该镜头已保存的 @ 引用兜底，避免按名字猜测到别家资产。
            target = persisted.get(key)
        if target is None:
            unresolved.append(mention)
            continue
        asset_type, asset_id, version_id = target
        name, temp_version = await _asset_name_version(
            db, asset_type=asset_type, asset_id=asset_id
        )
        if version_id is None:
            version_id = temp_version
        resolved.append(
            PromptReferenceRead(
                asset_type=asset_type,
                asset_id=asset_id,
                asset_name=name,
                asset_version_id=version_id,
                mention=mention,
                start_index=match.start(),
                end_index=match.end(),
            )
        )
    if unresolved:
        warnings.append("以下 @ 引用无法解析：" + "、".join(unresolved))
    return PromptResolveRead(
        prompt=prompt or "", resolved=resolved, unresolved=unresolved, warnings=warnings
    )


async def _project_asset(
    db: AsyncSession, *, asset_type: str, asset_id: str, project_id: str
) -> bool:
    from app.services.studio.asset_versions import asset_belongs_to_project

    return await asset_belongs_to_project(
        db, asset_type=asset_type, asset_id=asset_id, project_id=project_id
    )


async def save_prompt(
    db: AsyncSession, *, shot_id: str, prompt: str
) -> PromptResolveRead:
    detail = await db.get(ShotDetail, shot_id)
    if detail is None:
        raise ValueError("镜头详情不存在")
    detail.video_prompt_draft = prompt or ""
    result = await resolve_prompt_references(db, shot_id=shot_id, prompt=prompt)
    await db.execute(
        ShotPromptReference.__table__.delete().where(ShotPromptReference.shot_id == shot_id)
    )
    now = datetime.now(UTC)
    for item in result.resolved:
        db.add(
            ShotPromptReference(
                shot_id=shot_id,
                asset_type=item.asset_type,
                asset_id=item.asset_id,
                asset_version_id=item.asset_version_id,
                mention=item.mention,
                start_index=item.start_index,
                end_index=item.end_index,
                created_at=now,
            )
        )
    await db.flush()
    return result


async def _resolve_options(
    db: AsyncSession, *, shot_id: str, ratio: str | None, resolution: str | None
) -> tuple[Any, Any, str, str | None, int]:
    from app.services.film.generated_video import (
        load_provider_config_by_model,
        resolve_default_video_model,
        resolve_effective_video_options,
        resolve_effective_video_resolution,
    )

    shot_detail = await db.get(ShotDetail, shot_id)
    if shot_detail is None:
        raise ValueError("镜头详情不存在")
    project_id = await _project_id_for_shot(db, shot_id)
    model = await resolve_default_video_model(db, project_id=project_id)
    provider_cfg = await load_provider_config_by_model(db, model)
    resolved_ratio = await resolve_effective_video_options(
        db, shot_id=shot_id, shot_detail=shot_detail, requested_ratio=ratio
    )
    resolved_resolution = await resolve_effective_video_resolution(
        db, shot_id=shot_id, requested_resolution=resolution
    )
    return model, provider_cfg, resolved_ratio, resolved_resolution, int(shot_detail.duration or 0)


def _validate_advanced_prompt(prompt: str, manifest: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    max_picture = len(manifest)
    for label, number in re.findall(r"<(Picture|Subject|Audio) (\d+)>", prompt or ""):
        if label == "Picture" and int(number) > max_picture:
            errors.append(f"高级提示词引用了不存在的 <Picture {number}>")
        if label == "Subject" and int(number) > max_picture:
            errors.append(f"高级提示词引用了不存在的 <Subject {number}>")
        if label == "Audio" and int(number) > MAX_REFERENCE_AUDIOS:
            errors.append(f"高级提示词引用了不存在的 <Audio {number}>")
        if label == "Video":
            errors.append("P6 高级提示词不支持 <Video N> 参考视频")
    return errors


async def build_generation_preview(
    db: AsyncSession,
    *,
    shot_id: str,
    natural_prompt: str = "",
    advanced_prompt: str = "",
    reference_mode: str = REFERENCE_MODE,
    ratio: str | None = None,
    resolution: str | None = None,
    reference_audio_file_ids: list[str] | None = None,
) -> GenerationPreviewRead:
    shot = await db.get(Shot, shot_id)
    if shot is None:
        raise ValueError("镜头不存在")
    bindings = await active_bindings(db, shot_id=shot_id)
    if not bindings:
        return GenerationPreviewRead(
            shot_id=shot_id,
            reference_mode=reference_mode,
            prompt=advanced_prompt or natural_prompt,
            natural_prompt=natural_prompt,
            advanced_prompt=advanced_prompt,
            blocking_errors=["镜头没有启用中的参考图，请先自动推荐或人工添加。"],
        )
    refs, manifest, manifest_warnings = await build_manifest(db, shot_id=shot_id)
    ref_result = await resolve_prompt_references(
        db, shot_id=shot_id, prompt=natural_prompt or ""
    )
    errors: list[str] = list(ref_result.warnings if ref_result.unresolved else [])
    errors.extend(
        warning
        for warning in manifest_warnings
        if "不存在" in warning or "缺少文件" in warning
    )
    if len(manifest) > MAX_REFERENCE_IMAGES:
        errors.append(f"参考图超过 {MAX_REFERENCE_IMAGES} 张上限")
    if advanced_prompt:
        errors.extend(_validate_advanced_prompt(advanced_prompt, manifest))
    from app.services.studio.voice_samples import resolve_p6_audio_references

    audio_details: list[dict[str, Any]] = []
    if reference_mode == REFERENCE_MODE:
        try:
            audio_details = await resolve_p6_audio_references(
                db,
                shot_id=shot_id,
                explicit_file_ids=reference_audio_file_ids,
            )
        except ValueError as exc:
            errors.append(str(exc))
    audio_ids = [str(item["file_id"]) for item in audio_details]
    try:
        model, provider_cfg, resolved_ratio, resolved_resolution, duration = await _resolve_options(
            db, shot_id=shot_id, ratio=ratio, resolution=resolution
        )
    except Exception as exc:  # noqa: BLE001 - 预览仍需显示素材问题
        model = provider_cfg = None
        resolved_ratio = ratio or ""
        resolved_resolution = resolution
        duration = 0
        errors.append(f"模型配置不可用：{exc}")
    if duration and not 4 <= int(duration) <= 15:
        errors.append(f"镜头时长 {duration}s 超出项目 4–15 秒业务限制")
    prompt = advanced_prompt.strip() if advanced_prompt.strip() else ""
    warnings = list(manifest_warnings) + list(ref_result.warnings)
    quality_checks = await collect_generation_quality_checks(
        db, shot_id=shot_id, advanced_prompt=advanced_prompt
    )
    warnings.extend(
        item.message for item in quality_checks if item.level in {"blocking", "warning"}
    )
    # blocking 级质量项必须参与提交拦截，不能只作为展示建议。
    errors.extend(item.message for item in quality_checks if item.level == "blocking")
    if not prompt:
        try:
            context = await build_video_context(
                db,
                shot_id=shot_id,
                reference_mode=reference_mode,
                images=[item.file_id for item in refs if item.file_id],
                provider=getattr(provider_cfg, "provider", "") or "",
                model=getattr(model, "name", "") or "",
                ratio=resolved_ratio,
                reference_audio_file_ids=audio_ids,
                audio_references=[
                    IRAudioReference(
                        label=str(item["label"]),
                        file_id=str(item["file_id"]),
                        speaker_name=str(item.get("speaker_name") or ""),
                        speaker_id=str(item.get("speaker_id") or ""),
                        source_line_index=item.get("line_index"),
                    )
                    for item in audio_details
                ] if audio_details else None,
                reference_manifest=refs,
                natural_prompt=natural_prompt,
            )
            derived = await derive_video_preview(
                db,
                base=build_video_base_draft(shot_id=shot_id, prompt=None),
                context=context,
            )
            prompt = derived.rendered_prompt
            warnings.extend(derived.warnings)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"提示词渲染失败：{exc}")
    input_hash = _sha(
        {
            "manifest": [item.file_id for item in refs],
            "prompt": prompt,
            "audio": audio_ids,
            "ratio": resolved_ratio,
            "resolution": resolved_resolution,
            "duration": duration,
        }
    )
    return GenerationPreviewRead(
        shot_id=shot_id,
        reference_mode=reference_mode,
        manifest=bindings,
        images=[item.file_id for item in refs if item.file_id],
        audio_file_ids=audio_ids,
        audio_refs=audio_details,
        prompt=prompt,
        natural_prompt=natural_prompt,
        advanced_prompt=advanced_prompt,
        prompt_refs=ref_result.resolved,
        warnings=warnings,
        blocking_errors=errors,
        model_name=getattr(model, "name", "") or "",
        provider_name=getattr(provider_cfg, "provider", "") or "",
        ratio=resolved_ratio,
        resolution=resolved_resolution,
        duration=duration,
        input_hash=input_hash,
    )


async def create_snapshot(
    db: AsyncSession,
    *,
    shot_id: str,
    preview: GenerationPreviewRead,
    task_id: str | None,
    created_by: int | None,
    request_key: str | None = None,
) -> ShotGenerationSnapshot:
    shot = await db.get(Shot, shot_id)
    if shot is None:
        raise ValueError("镜头不存在")
    from app.models.studio import Chapter

    chapter = await db.get(Chapter, shot.chapter_id)
    if chapter is None:
        raise ValueError("章节不存在")
    from app.models.studio import Project

    project = await db.get(Project, chapter.project_id)
    style_snapshot = (
        {
            "style": str(project.style or ""),
            "visual_style": str(project.visual_style or ""),
            "unify_style": bool(project.unify_style),
            "default_reference_mode": str(project.default_reference_mode or ""),
            "default_video_ratio": project.default_video_ratio,
            "default_video_resolution": project.default_video_resolution,
        }
        if project is not None
        else {}
    )
    rows = (
        await db.execute(select(ShotAssetVersion).where(ShotAssetVersion.shot_id == shot_id))
    ).scalars().all()
    snapshot = ShotGenerationSnapshot(
        id=str(uuid.uuid4()),
        shot_id=shot_id,
        project_id=chapter.project_id,
        chapter_id=chapter.id,
        scene_group_id=shot.scene_group_id,
        task_id=task_id,
        model_name=preview.model_name,
        provider_name=preview.provider_name,
        reference_mode=preview.reference_mode,
        manifest=[item.model_dump() for item in preview.manifest],
        prompt=preview.prompt,
        natural_prompt=preview.natural_prompt,
        advanced_prompt=preview.advanced_prompt,
        prompt_refs=[item.model_dump() for item in preview.prompt_refs],
        audio_refs=list(preview.audio_refs),
        asset_versions=[
            {
                "asset_type": item.asset_type,
                "asset_id": item.asset_id,
                "asset_version_id": item.asset_version_id,
                "role": item.role,
            }
            for item in rows
        ],
        generation_params={
            "ratio": preview.ratio,
            "resolution": preview.resolution,
            "duration": preview.duration,
        },
        style_snapshot=style_snapshot,
        duration=preview.duration,
        ratio=preview.ratio,
        resolution=preview.resolution,
        input_hash=preview.input_hash,
        request_key=request_key,
        created_by=created_by,
        created_at=datetime.now(UTC),
    )
    db.add(snapshot)
    await db.flush()
    return snapshot


async def snapshot_to_read(
    db: AsyncSession, snapshot: ShotGenerationSnapshot
) -> GenerationSnapshotRead:
    return GenerationSnapshotRead.model_validate(snapshot)


_CUT_CUE_RE = re.compile(
    r"(切镜|切到|切换镜头|镜头切换|多机位|分镜切换|\bcut to\b|\bmulti-camera\b|\bmulti-shot\b|"
    r"特写[^。；;]{0,30}(然后|再|随后)|远景[^。；;]{0,30}(然后|再|随后))",
    re.IGNORECASE,
)
_MULTI_LOCATION_RE = re.compile(
    r"(在|到|进入|来到|回到)[^，。；;]{1,12}(然后|随后|接着|再|又|切到|转到|换到)"
    r"(在|到|进入|来到|回到)"
    r"|(同一镜头|一条视频|同一段视频)[^。；;]{0,24}(两个|多个|不同)(地点|场景|环境)",
    re.IGNORECASE,
)
_SILENCE_RE = re.compile(
    r"no spoken dialogue|do not speak|characters do not speak|silent|不说话|无对白|保持沉默",
    re.IGNORECASE,
)
_CONTINUITY_RE = re.compile(
    r"continuous|same scene|one scene|no cut|background.{0,12}(consistent|same)"
    r"|不切|同一(个)?场景|场景.{0,6}(一致|保持)|连续镜头",
    re.IGNORECASE,
)
_MALE_VOICE_RE = re.compile(r"男|male\b|masculine", re.IGNORECASE)
_FEMALE_VOICE_RE = re.compile(r"女|female\b|feminine", re.IGNORECASE)
_MALE_PRONOUN_RE = re.compile(r"\b(he|him|his)\b|他", re.IGNORECASE)
_FEMALE_PRONOUN_RE = re.compile(r"\b(she|her|hers)\b|她", re.IGNORECASE)


def _quality_check(
    code: str,
    level: Literal["blocking", "warning", "info"],
    message: str,
    fix_hint: str = "",
) -> ShotVideoQualityCheck:
    """构造一条质量检查项，统一字段含义，避免调用处拼错级别。"""
    return ShotVideoQualityCheck(
        code=code,
        level=level,
        message=message,
        fix_hint=fix_hint,
    )


async def collect_generation_quality_checks(
    db: AsyncSession,
    *,
    shot_id: str,
    advanced_prompt: str = "",
) -> list[ShotVideoQualityCheck]:
    """收集声音与场景连续性质量风险。

    设计原则：
    - 只读取当前真实输入，不按角色名、照片或性别刻板印象推断声音；
    - blocking 仅用于输入数据无法正确构建（如说话角色/场景资产不存在、跨项目引用），
      warning 表示高概率质量风险，info 表示已满足的可解释建议；
    - 所有规则都不静默修改用户输入，也不自动替换历史快照。

    参数：
        db: 异步数据库会话。
        shot_id: 镜头 ID。
        advanced_prompt: 用户手写的高级 H3 提示词；非空时会绕过 IR 自动拼装，
            因此需要额外检查是否丢失说话人/连续性约束。

    返回：
        按发现顺序排列的质量检查项；同一 code + message 只保留一次。
    """
    detail = await db.get(ShotDetail, shot_id)
    if detail is None:
        return []

    checks: list[ShotVideoQualityCheck] = []
    seen: set[tuple[str, str]] = set()

    def add(
        code: str,
        level: Literal["blocking", "warning", "info"],
        message: str,
        fix_hint: str = "",
    ) -> None:
        key = (code, message)
        if key in seen:
            return
        seen.add(key)
        checks.append(_quality_check(code, level, message, fix_hint))

    shot = await db.get(Shot, shot_id)
    project: Project | None = None
    if shot is not None:
        chapter = await db.get(Chapter, shot.chapter_id)
        if chapter is not None:
            project = await db.get(Project, chapter.project_id)

    lines = (
        await db.execute(
            select(ShotDialogLine)
            .where(ShotDialogLine.shot_detail_id == shot_id)
            .order_by(ShotDialogLine.index.asc(), ShotDialogLine.id.asc())
        )
    ).scalars().all()
    speaker_ids = {
        str(line.speaker_character_id or "").strip()
        for line in lines
        if str(line.speaker_character_id or "").strip()
    }
    speakers = {
        item.id: item
        for item in (
            await db.execute(select(Character).where(Character.id.in_(speaker_ids)))
        ).scalars().all()
    } if speaker_ids else {}
    version_rows = (
        await db.execute(select(ShotAssetVersion).where(ShotAssetVersion.shot_id == shot_id))
    ).scalars().all()
    character_version_ids = {
        row.asset_id for row in version_rows if row.asset_type == "character"
    }
    scene_version = next((row for row in version_rows if row.asset_type == "scene"), None)
    if scene_version is not None and await db.get(Scene, str(scene_version.asset_id)) is None:
        add(
            "scene_asset_unknown",
            "blocking",
            f"ShotAssetVersion(scene) 引用的场景 {scene_version.asset_id} 不存在，无法构建空间约束。",
            "重新选择有效场景，或清理失效的场景资产版本。",
        )
    active_binding_rows = (
        await db.execute(
            select(ShotReferenceBinding).where(
                ShotReferenceBinding.shot_id == shot_id,
                ShotReferenceBinding.is_active.is_(True),
            )
        )
    ).scalars().all()
    scene_refs = [
        row
        for row in active_binding_rows
        if row.reference_role == "scene" or row.asset_type == "scene"
    ]
    has_scene_ref = bool(scene_refs)

    script_text = " ".join(
        [
            str(getattr(detail, "video_prompt_draft", "") or ""),
            str(getattr(detail, "description", "") or ""),
            advanced_prompt,
        ]
    )

    # ---- 声音与说话人 ---------------------------------------------------- #
    if lines:
        unconfirmed = [
            line for line in lines if not str(line.speaker_character_id or "").strip()
        ]
        if unconfirmed:
            add(
                "dialogue_speaker_missing",
                "warning",
                "存在对白但未确认说话人；系统不会按角色名猜测，H3 可能自由分配声音。",
                "在镜头编辑页为每条台词选择 ShotDialogLine.speaker_character_id。",
            )
        for line in lines:
            speaker_id = str(line.speaker_character_id or "").strip()
            if not speaker_id:
                continue
            speaker = speakers.get(speaker_id)
            if speaker is None:
                add(
                    "dialogue_speaker_unknown",
                    "blocking",
                    f"台词行 {line.index} 引用的说话角色 {speaker_id} 不存在，无法构建声音约束。",
                    "重新选择有效说话角色或清理失效台词行。",
                )
                continue
            if project is not None and speaker.project_id != project.id:
                add(
                    "dialogue_speaker_project_mismatch",
                    "blocking",
                    f"说话角色「{speaker.name}」不属于当前项目，无法安全生成。",
                    "改为当前项目的角色，或先修正角色归属。",
                )
            if speaker_id not in character_version_ids:
                if str(line.line_mode or "DIALOGUE").upper() == "DIALOGUE":
                    add(
                        "dialogue_speaker_not_linked",
                        "warning",
                        f"对白说话人「{speaker.name}」未出现在镜头角色资产版本中，口型与画面可能不一致。",
                        "在镜头角色中补充该角色，或确认该台词是画外音。",
                    )
                else:
                    add(
                        "dialogue_speaker_offscreen",
                        "info",
                        f"说话人「{speaker.name}」未出现在画面角色中，已按画外音/旁白处理；请确认符合预期。",
                        "如是画外音可保留；否则补充镜头角色。",
                    )
            if not str(speaker.voice_description or "").strip():
                add(
                    "character_voice_missing",
                    "warning",
                    f"角色「{speaker.name}」没有声音描述；H3 只能根据画面/文字自由分配声音。",
                    "在角色详情填写用户确认的声音描述，例如年龄感、音色、语速和情绪。",
                )

        if unconfirmed and len(lines) > 1:
            add(
                "dialogue_speaker_ambiguous",
                "warning",
                "对白包含多个说话人，但部分台词未确认归属，轮流说话时容易串音。",
                "逐条确认说话人，尤其是双人对白。",
            )

        if advanced_prompt and "<d>" not in advanced_prompt:
            add(
                "advanced_prompt_missing_dialogue",
                "warning",
                "高级 H3 提示词没有 <d> 台词块；结构化对白与口型约束可能丢失。",
                "在高级提示词中逐字写入 <d>[Chinese] 台词</d>，或清空高级提示词改用自动渲染。",
            )
        if advanced_prompt and not _CONTINUITY_RE.search(advanced_prompt):
            add(
                "advanced_prompt_missing_continuity",
                "warning",
                "高级 H3 提示词未明确保持同一场景/连续镜头；可能出现背景不连续。",
                "补充同一场景、固定背景布局和 no cut to another location 约束。",
            )

        # 只用用户提供的声音描述与 Prompt 中的性别指代做一致性比对；
        # 不根据姓名、照片或演员资料推断性别。
        for speaker in speakers.values():
            voice = str(speaker.voice_description or "").strip()
            if not voice:
                continue
            if _MALE_VOICE_RE.search(voice) and _FEMALE_PRONOUN_RE.search(script_text):
                add(
                    "prompt_voice_gender_conflict",
                    "warning",
                    f"角色「{speaker.name}」的声音描述为男性，但 Prompt 含女性指代；声音可能被错误分配。",
                    "统一 Prompt 中的性别指代，或修正角色声音描述。",
                )
            if _FEMALE_VOICE_RE.search(voice) and _MALE_PRONOUN_RE.search(script_text):
                add(
                    "prompt_voice_gender_conflict",
                    "warning",
                    f"角色「{speaker.name}」的声音描述为女性，但 Prompt 含男性指代；声音可能被错误分配。",
                    "统一 Prompt 中的性别指代，或修正角色声音描述。",
                )
    else:
        if advanced_prompt:
            add(
                "advanced_prompt_without_structured_dialogue",
                "warning",
                "高级 H3 提示词没有结构化 ShotDialogLine；模型可能自由生成对白或声音。",
                "如需对白请先补结构化台词；如无对白请明确写 no spoken dialogue。",
            )
            if not _SILENCE_RE.search(advanced_prompt):
                add(
                    "advanced_prompt_may_invent_speech",
                    "warning",
                    "高级提示词既没有 <d> 台词块，也没有明确无对白；H3 可能自行生成说话和口型。",
                    "补充 No spoken dialogue; characters do not speak，或清空高级提示词改用自动渲染。",
                )
        if re.search(r'["“”][^"“”]{2,}["“”]|说道|问道|回答|says\b|speaks\b', script_text):
            add(
                "prompt_dialogue_without_lines",
                "warning",
                "Prompt 似乎包含对白，但 ShotDialogLine 没有结构化台词；声音和口型可能由模型自由生成。",
                "把对白拆成结构化台词行并确认说话人。",
            )
        if re.search(r"female lead|male lead|女主角|男主角", script_text, re.IGNORECASE):
            add(
                "prompt_gender_claim_unverified",
                "warning",
                "Prompt 含性别化主角描述，但没有任何结构化声音描述可作为依据。",
                "避免根据姓名推断性别；补充结构化对白与用户确认的声音描述。",
            )

    # ---- 音色参考 -------------------------------------------------------- #
    if project is not None and project.use_dialog_audio_as_reference:
        from app.services.studio.voice_samples import resolve_p6_audio_references

        try:
            audio_refs = await resolve_p6_audio_references(db, shot_id=shot_id)
        except ValueError as exc:
            add(
                "voice_reference_unavailable",
                "warning",
                f"项目已开启音色参考，但当前镜头无法建立参考音频：{exc}",
                "补齐说话人/音色样本，或关闭项目音色参考并改用文字声音描述。",
            )
        else:
            if audio_refs:
                add(
                    "voice_reference_ready",
                    "info",
                    f"已配置 {len(audio_refs)} 个音色参考；文字声音描述仅作补充，不锁定音色身份。",
                )
    elif lines:
        add(
            "voice_reference_disabled",
            "info",
            "项目未开启音色参考；声音只由文字描述约束，不能保证稳定音色身份。",
            "如需固定音色，请在项目配置开启参考音频并上传角色音色样本。",
        )

    # ---- 场景与连续性 ---------------------------------------------------- #
    if scene_version is None:
        add(
            "scene_version_missing",
            "warning",
            "镜头没有绑定场景资产版本；无法保证背景布局和光线连续。",
            "在镜头详情选择场景，并绑定已采纳的场景图片版本。",
        )
    else:
        if detail.scene_id and scene_version.asset_id != detail.scene_id:
            add(
                "scene_version_mismatch",
                "warning",
                "镜头场景与 ShotAssetVersion(scene) 指向不同场景；参考图可能来自另一套环境。",
                "统一镜头 scene_id 与场景资产版本。",
            )
        if not has_scene_ref:
            add(
                "scene_reference_missing",
                "warning",
                "镜头已选择场景版本，但场景图片未进入实际参考图；背景可能漂移。",
                "自动推荐或手动添加该场景版本的已采纳图片。",
            )
        else:
            mismatched_refs = [
                row
                for row in scene_refs
                if row.asset_version_id
                and scene_version.asset_version_id
                and row.asset_version_id != scene_version.asset_version_id
            ]
            if mismatched_refs:
                add(
                    "scene_reference_version_mismatch",
                    "warning",
                    "场景参考图版本与 ShotAssetVersion(scene) 不一致；背景细节可能不是当前版本。",
                    "重新绑定当前场景版本的已采纳图片。",
                )
            else:
                add(
                    "scene_reference_ready",
                    "info",
                    "场景参考已进入实际参考图，并参与 input_hash。",
                )

    if _CUT_CUE_RE.search(script_text):
        duration = int(getattr(detail, "duration", 0) or 0)
        if 0 < duration <= 6:
            add(
                "short_shot_multi_camera",
                "warning",
                "短镜头描述包含多个独立机位/切镜线索，可能出现背景不连续；建议拆分为多个 Shot。",
                "缩短为单一连续镜头，或拆分镜头后分别生成。",
            )
        else:
            add(
                "shot_multi_camera",
                "warning",
                "镜头描述包含多机位/切镜线索，请确认场景锚点和空间连续性。",
                "补充场景锚点与人物位置，或拆分镜头。",
            )
    elif scene_version is not None and has_scene_ref:
        add(
            "single_continuity_default",
            "info",
            "未检测到明确切镜线索，默认按单一连续镜头生成。",
        )

    if _MULTI_LOCATION_RE.search(script_text):
        add(
            "multiple_location_cues",
            "warning",
            "镜头描述可能包含多个地点/环境；同一条短视频内切换地点会造成背景不连续。",
            "确认是否同一场景；如不是，请拆分 Shot 并分别绑定场景。",
        )

    return checks


__all__ = [
    "MAX_REFERENCE_IMAGES",
    "active_bindings",
    "auto_recommend",
    "build_generation_preview",
    "build_manifest",
    "collect_generation_quality_checks",
    "create_snapshot",
    "create_video_task",
    "stage_video_from_preview",
    "list_bindings",
    "list_snapshots",
    "remove_binding",
    "reorder_bindings",
    "resolve_prompt_references",
    "save_prompt",
    "snapshot_to_read",
    "update_binding",
    "upload_reference",
]


class _CreateOnlyTask:
    async def run(self, *args: object, **kwargs: object):
        return None

    async def status(self) -> dict[str, object]:
        return {}

    async def is_done(self) -> bool:
        return False

    async def get_result(self) -> object:
        return None


async def stage_video_from_preview(
    db: AsyncSession,
    *,
    shot_id: str,
    preview: GenerationPreviewRead,
    auto_adopt: bool = False,
    created_by: int | None = None,
    request_key: str | None = None,
) -> tuple[str, ShotGenerationSnapshot]:
    """基于已校验的同一份 preview 创建任务与快照；不提交、不入队。"""
    from app.core.task_manager import DeliveryMode, SqlAlchemyTaskStore, TaskManager
    from app.services.common.workspace import resolve_workspace_id
    from app.services.film.generated_video import (
        load_provider_config_by_model,
        resolve_default_video_model,
    )
    from app.models.task_links import GenerationTaskLink

    project_id = await _project_id_for_shot(db, shot_id)
    if project_id is None:
        raise ValueError("镜头缺少项目归属")
    model = await resolve_default_video_model(db, project_id=project_id)
    provider_cfg = await load_provider_config_by_model(db, model)
    workspace_id = await resolve_workspace_id(db, shot_id=shot_id)
    snapshot = await create_snapshot(
        db,
        shot_id=shot_id,
        preview=preview,
        task_id=None,
        created_by=created_by,
        request_key=request_key,
    )
    input_payload: dict[str, Any] = {
        "prompt": preview.prompt,
        "reference_file_ids": preview.images,
        "model": model.name,
        "ratio": preview.ratio,
        "seconds": preview.duration,
        "auto_adopt": bool(auto_adopt),
        "snapshot_id": snapshot.id,
    }
    if preview.resolution:
        input_payload["resolution"] = preview.resolution
    if preview.audio_file_ids:
        input_payload["reference_audio_file_ids"] = preview.audio_file_ids
    run_args = {
        "shot_id": shot_id,
        "provider": provider_cfg.provider,
        "provider_id": model.provider_id,
        "base_url": provider_cfg.base_url,
        "input": input_payload,
    }
    store = SqlAlchemyTaskStore(db)
    tm = TaskManager(store=store, strategies={})
    task = await tm.create(
        task=_CreateOnlyTask(),
        mode=DeliveryMode.async_polling,
        task_kind="video_generation",
        run_args=run_args,
        workspace_id=workspace_id,
    )
    snapshot.task_id = task.id
    snapshot.model_id = model.id
    db.add(
        GenerationTaskLink(
            task_id=task.id,
            resource_type="video",
            relation_type="video",
            relation_entity_id=shot_id,
        )
    )
    await db.flush()
    return task.id, snapshot


async def create_video_task(
    db: AsyncSession,
    *,
    shot_id: str,
    body: P6VideoGenerateRequest,
    created_by: int | None = None,
) -> tuple[str, ShotGenerationSnapshot, GenerationPreviewRead]:
    """创建 P6 单镜头视频任务；预览与提交使用同一份 manifest/prompt。"""
    preview = await build_generation_preview(
        db,
        shot_id=shot_id,
        natural_prompt=body.prompt,
        advanced_prompt=body.advanced_prompt,
        reference_mode=body.reference_mode,
        ratio=body.ratio,
        resolution=body.resolution,
        reference_audio_file_ids=body.reference_audio_file_ids,
    )
    if body.expected_input_hash and body.expected_input_hash != preview.input_hash:
        raise ValueError("生成输入已变化（参考图/提示词/参数与预览不一致），请刷新预览后重试")
    if preview.blocking_errors:
        raise ValueError("；".join(preview.blocking_errors))
    if not preview.images:
        raise ValueError("没有可提交的参考图片")
    if not preview.prompt.strip():
        raise ValueError("最终提示词为空")
    readiness = await get_p6_readiness(db, shot_id=shot_id)
    if not readiness.ready:
        failed = [item.message for item in readiness.checks if not item.ok]
        raise ValueError(
            "视频生成准备度未通过：" + "；".join(failed[:5])
        )
    async def _existing() -> ShotGenerationSnapshot | None:
        if not body.request_key:
            return None
        return (
            await db.execute(
                select(ShotGenerationSnapshot)
                .where(
                    ShotGenerationSnapshot.shot_id == shot_id,
                    ShotGenerationSnapshot.request_key == body.request_key,
                )
                .limit(1)
            )
        ).scalars().first()

    existing = await _existing()
    if existing is not None:
        if existing.input_hash != preview.input_hash:
            raise ValueError("相同 request_key 对应了不同生成输入，请使用新的请求键")
        if not existing.task_id:
            raise ValueError("该请求键对应的任务已丢失，请使用新的请求键重新生成")
        return existing.task_id, existing, preview
    try:
        task_id, snapshot = await stage_video_from_preview(
            db,
            shot_id=shot_id,
            preview=preview,
            auto_adopt=body.auto_adopt,
            created_by=created_by,
            request_key=body.request_key,
        )
        await db.commit()
    except IntegrityError:
        # 两个并发请求同时通过了上面的查询：唯一约束只允许一个任务，另一个读取赢家。
        await db.rollback()
        existing = await _existing()
        if existing is not None and existing.task_id and existing.input_hash == preview.input_hash:
            return existing.task_id, existing, preview
        raise ValueError("并发生成请求冲突，请使用新的请求键后重试")
    from app.tasks.execute_task import enqueue_task_execution

    enqueue_task_execution(task_id)
    return task_id, snapshot, preview


async def list_snapshots(
    db: AsyncSession, *, shot_id: str
) -> list[ShotGenerationSnapshot]:
    return list(
        (
            await db.execute(
                select(ShotGenerationSnapshot)
                .where(ShotGenerationSnapshot.shot_id == shot_id)
                .order_by(ShotGenerationSnapshot.created_at.desc())
            )
        ).scalars().all()
    )


async def get_p6_readiness(db: AsyncSession, *, shot_id: str) -> Any:
    """在既有 readiness 上追加 P6 参考绑定/版本/角色锁定检查。"""
    from app.schemas.studio.shots import ShotVideoReadinessCheck, ShotVideoReadinessRead
    from app.services.studio.shot_video_readiness import get_shot_video_readiness

    base = await get_shot_video_readiness(db, shot_id=shot_id, reference_mode=REFERENCE_MODE)
    detail = await db.get(ShotDetail, shot_id)
    bindings = await list_bindings(db, shot_id=shot_id, active_only=True)
    active = [item for item in bindings if item.is_active]
    files_ok = True
    for item in active:
        if not item.file_id or await db.get(FileItem, item.file_id) is None:
            files_ok = False
            break
    binding_check = {
        "key": "reference_bindings_ready",
        "ok": bool(active) and files_ok,
        "message": (
            f"已启用 {len(active)} 张参考图"
            if active and files_ok
            else ("没有启用中的参考图" if not active else "有参考图文件不存在")
        ),
    }
    limit_check = {
        "key": "reference_limit_ready",
        "ok": len(active) <= MAX_REFERENCE_IMAGES,
        "message": (
            f"参考图 {len(active)} 张，未超过 H3 上限 {MAX_REFERENCE_IMAGES}"
            if len(active) <= MAX_REFERENCE_IMAGES
            else f"参考图 {len(active)} 张，超过 H3 上限 {MAX_REFERENCE_IMAGES}"
        ),
    }
    version_rows = (
        await db.execute(select(ShotAssetVersion).where(ShotAssetVersion.shot_id == shot_id))
    ).scalars().all()
    version_ok = bool(version_rows)
    version_message = "镜头资产版本已选择" if version_ok else "镜头尚未保存资产版本选择"
    for row in version_rows:
        if not row.asset_version_id:
            version_ok = False
            version_message = f"{row.asset_type} 缺少资产版本"
            break
    version_check = {
        "key": "shot_asset_versions_ready",
        "ok": version_ok,
        "message": version_message,
    }
    locked_ok = True
    locked_message = "角色视觉身份已锁定"
    for row in version_rows:
        if row.asset_type != "character":
            continue
        character = await db.get(Character, row.asset_id)
        if character is None or character.identity_locked_at is None:
            locked_ok = False
            locked_message = "有角色的视觉身份尚未锁定"
            break
    lock_check = {
        "key": "character_identity_locked",
        "ok": locked_ok,
        "message": locked_message,
    }
    prompt_text = detail.video_prompt_draft if detail else ""
    prompt_refs = await resolve_prompt_references(
        db, shot_id=shot_id, prompt=prompt_text or ""
    )
    prompt_check = {
        "key": "prompt_references_ready",
        "ok": not prompt_refs.unresolved,
        "message": (
            "提示词引用均可解析"
            if not prompt_refs.unresolved
            else "无法解析的 @ 引用：" + "、".join(prompt_refs.unresolved)
        ),
    }
    # P6 正式路径的参考图来源是 active bindings，而不是旧 IR 的自动收集；
    # 旧 readiness 的 reference_images_ready 只按剧本语料推断，会把已显式绑定的镜头误判为阻塞。
    base_checks: list[ShotVideoReadinessCheck] = []
    for check in base.checks:
        if check.key == "reference_images_ready" and active and files_ok:
            base_checks.append(
                ShotVideoReadinessCheck(
                    key=check.key,
                    ok=True,
                    message=f"已启用 {len(active)} 张有序参考图",
                )
            )
        else:
            base_checks.append(check)
    checks = base_checks + [ShotVideoReadinessCheck(**item) for item in [binding_check, limit_check, version_check, lock_check, prompt_check]]
    quality_checks = await collect_generation_quality_checks(db, shot_id=shot_id)
    has_blocking = any(item.level == "blocking" for item in quality_checks)
    return ShotVideoReadinessRead(
        shot_id=shot_id,
        reference_mode=REFERENCE_MODE,
        ready=all(item.ok for item in checks) and not has_blocking,
        checks=checks,
        quality_checks=quality_checks,
    )
