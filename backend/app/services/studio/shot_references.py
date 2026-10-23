"""P6 / C11：镜头参考绑定、@ 引用、H3 同源预览与生成快照。"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chains.prompts.ir import IRReference
from app.core import storage
from app.models.studio import (
    AssetImageCandidate,
    AssetVersion,
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
    ShotGenerationSnapshot,
    ShotPromptReference,
    ShotReferenceBinding,
)
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
    lookup: dict[str, tuple[str, str, str | None]] = {}
    for item in characters:
        key = _normalize(item.name)
        lookup[key] = ("character", item.id, item.identity_version_id)
        for alias in await list_aliases(db, character_id=item.id):
            lookup[_normalize(alias.alias)] = ("character", item.id, item.identity_version_id)
    for asset_type in ("scene", "prop", "costume"):
        model = _ASSET_MODELS[asset_type]
        rows = (
            await db.execute(select(model).where(model.name.is_not(None)))
        ).scalars().all()
        for item in rows:
            if await _project_asset(db, asset_type=asset_type, asset_id=item.id, project_id=project_id):
                lookup[_normalize(item.name)] = (
                    asset_type,
                    item.id,
                    getattr(item, "current_version_id", None),
                )
    resolved: list[PromptReferenceRead] = []
    unresolved: list[str] = []
    warnings: list[str] = []
    for match in _AT_REF_RE.finditer(prompt or ""):
        mention = match.group(1)
        target = lookup.get(_normalize(mention))
        if target is None:
            unresolved.append(mention)
            continue
        asset_type, asset_id, version_id = target
        name, _ = await _asset_name_version(db, asset_type=asset_type, asset_id=asset_id)
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
        if label == "Audio" and int(number) > MAX_REFERENCE_AUDIOS:
            errors.append(f"高级提示词引用了不存在的 <Audio {number}>")
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
    if len(manifest) > MAX_REFERENCE_IMAGES:
        errors.append(f"参考图超过 {MAX_REFERENCE_IMAGES} 张上限")
    if advanced_prompt:
        errors.extend(_validate_advanced_prompt(advanced_prompt, manifest))
    from app.services.film.generated_video import resolve_video_reference_audio_file_ids

    audio_ids = await resolve_video_reference_audio_file_ids(
        db,
        shot_id=shot_id,
        reference_mode=reference_mode,
        explicit_file_ids=reference_audio_file_ids,
    )
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
    prompt = advanced_prompt.strip() if advanced_prompt.strip() else ""
    warnings = list(manifest_warnings) + list(ref_result.warnings)
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
) -> ShotGenerationSnapshot:
    shot = await db.get(Shot, shot_id)
    if shot is None:
        raise ValueError("镜头不存在")
    from app.models.studio import Chapter

    chapter = await db.get(Chapter, shot.chapter_id)
    if chapter is None:
        raise ValueError("章节不存在")
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
        audio_refs=list(preview.audio_file_ids),
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
        style_snapshot={},
        duration=preview.duration,
        ratio=preview.ratio,
        resolution=preview.resolution,
        input_hash=preview.input_hash,
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


__all__ = [
    "MAX_REFERENCE_IMAGES",
    "active_bindings",
    "auto_recommend",
    "build_generation_preview",
    "build_manifest",
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
        db, shot_id=shot_id, preview=preview, task_id=None, created_by=created_by
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
    if preview.blocking_errors:
        raise ValueError("；".join(preview.blocking_errors))
    if not preview.images:
        raise ValueError("没有可提交的参考图片")
    if not preview.prompt.strip():
        raise ValueError("最终提示词为空")
    task_id, snapshot = await stage_video_from_preview(
        db,
        shot_id=shot_id,
        preview=preview,
        auto_adopt=body.auto_adopt,
        created_by=created_by,
    )
    await db.commit()
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
    checks = list(base.checks) + [ShotVideoReadinessCheck(**item) for item in [binding_check, limit_check, version_check, lock_check, prompt_check]]
    return ShotVideoReadinessRead(
        shot_id=shot_id,
        reference_mode=REFERENCE_MODE,
        ready=all(item.ok for item in checks),
        checks=checks,
    )
