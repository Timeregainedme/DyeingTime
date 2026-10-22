"""P4：资产图片候选的生成、上传、采纳与删除。

复用现有资产图提示词渲染与图片任务系统：
- 每次默认 stage 两个独立 GenerationTask，不假设供应商支持 n=2；
- 任务成功/失败由 image_task_runner 按候选 ID 回写；
- 采纳只移动候选状态并同步资产图片槽位，不删除其他候选与历史文件。
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.models.studio import (
    AssetImageCandidate,
    AssetQualityLevel,
    AssetVersion,
    AssetViewAngle,
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
)
from app.services.studio.asset_versions import (
    ensure_base_version,
    get_asset,
    normalize_asset_type,
)
from app.services.studio.file_usages import upsert_file_usage
from app.services.studio.generation.asset_image import (
    build_asset_image_base_draft,
    build_asset_image_context,
    build_character_image_base_draft,
    derive_asset_image_preview,
)
from app.services.studio.image_task_runner import stage_image_task_and_link
from app.services.studio.image_tasks import resolve_image_model

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}
_VIEW_ANGLES = {item.name: item.value for item in AssetViewAngle}


def normalize_view_angle(value: str) -> str:
    """把 API 的小写视角归一为数据库既有大写枚举值。"""
    key = (value or "").strip().lower()
    if key not in _VIEW_ANGLES:
        raise ValueError("不支持的图片视角")
    return _VIEW_ANGLES[key]


_MODELS = {
    "character": (Character, CharacterImage, "character_id"),
    "scene": (Scene, SceneImage, "scene_id"),
    "prop": (Prop, PropImage, "prop_id"),
    "costume": (Costume, CostumeImage, "costume_id"),
}


def _check_image_bytes(filename: str, content: bytes) -> str:
    """校验图片扩展名与魔数；返回规范扩展名。"""
    suffix = Path(filename or "").suffix.lower()
    if suffix not in _IMAGE_EXTENSIONS:
        raise ValueError("只支持 jpg/jpeg/png/webp/gif 图片")
    if not content:
        raise ValueError("图片文件为空")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("图片超过 15MB 限制")
    head = content[:16]
    valid = (
        (suffix in {".jpg", ".jpeg"} and head.startswith(b"\xff\xd8\xff"))
        or (suffix == ".png" and head.startswith(b"\x89PNG\r\n\x1a\n"))
        or (suffix == ".gif" and head[:6] in {b"GIF87a", b"GIF89a"})
        or (suffix == ".webp" and head[:4] == b"RIFF" and head[8:12] == b"WEBP")
    )
    if not valid:
        raise ValueError("图片内容与扩展名不匹配或文件已损坏")
    return ".jpg" if suffix == ".jpeg" else suffix


async def _ensure_image_slot(
    db: AsyncSession,
    *,
    asset_type: str,
    asset_id: str,
    view_angle: str,
) -> Any:
    """确保存在请求视角的空图片槽位；返回图片行。"""
    _model, image_model, parent_field = _MODELS[asset_type]
    row = (
        await db.execute(
            select(image_model)
            .where(
                getattr(image_model, parent_field) == asset_id,
                image_model.quality_level == AssetQualityLevel.low,
                image_model.view_angle == view_angle,
            )
            .limit(1)
        )
    ).scalars().first()
    if row is not None:
        return row
    kwargs: dict[str, Any] = {
        parent_field: asset_id,
        "quality_level": AssetQualityLevel.low,
        "view_angle": view_angle,
        "format": "png",
    }
    if asset_type == "character":
        kwargs["is_primary"] = view_angle == "FRONT"
    row = image_model(**kwargs)
    db.add(row)
    await db.flush()
    return row


async def _build_prompt(
    db: AsyncSession,
    *,
    asset_type: str,
    asset_id: str,
    image_id: int,
):
    if asset_type == "character":
        base = await build_character_image_base_draft(
            db, character_id=asset_id, image_id=image_id
        )
    else:
        base = await build_asset_image_base_draft(
            db, asset_type=asset_type, asset_id=asset_id, image_id=image_id
        )
    context = build_asset_image_context(base=base)
    return derive_asset_image_preview(base=base, context=context)


async def list_candidates(
    db: AsyncSession,
    *,
    asset_type: str,
    asset_id: str,
    view_angle: str | None = None,
) -> list[AssetImageCandidate]:
    stmt = select(AssetImageCandidate).where(
        AssetImageCandidate.asset_type == normalize_asset_type(asset_type),
        AssetImageCandidate.asset_id == asset_id,
    )
    if view_angle:
        stmt = stmt.where(AssetImageCandidate.view_angle == view_angle)
    return list(
        (
            await db.execute(
                stmt.order_by(AssetImageCandidate.created_at.desc(), AssetImageCandidate.id.desc())
            )
        ).scalars().all()
    )


async def generate_candidates(
    db: AsyncSession,
    *,
    project: Project,
    asset_type: str,
    asset_id: str,
    view_angle: str = "front",
    candidate_count: int = 2,
    prompt_override: str | None = None,
    created_by: int | None = None,
) -> list[AssetImageCandidate]:
    """创建默认两张候选图任务；返回已 stage 的候选（任务尚未入队）。"""
    normalized = normalize_asset_type(asset_type)
    if await get_asset(db, asset_type=normalized, asset_id=asset_id) is None:
        raise ValueError("资产不存在")
    view_angle = normalize_view_angle(view_angle)
    if candidate_count < 1 or candidate_count > 2:
        raise ValueError("单次最多生成 2 张候选")

    version = await ensure_base_version(
        db, asset_type=normalized, asset_id=asset_id, source="generated"
    )
    slot = await _ensure_image_slot(
        db, asset_type=normalized, asset_id=asset_id, view_angle=view_angle
    )
    derived = await _build_prompt(
        db, asset_type=normalized, asset_id=asset_id, image_id=slot.id
    )
    model = await resolve_image_model(db, None, project_id=project.id)
    ratio = project.default_image_ratio or project.default_video_ratio
    resolution = project.default_image_resolution_profile
    prompt = (prompt_override or "").strip() or derived.prompt
    batch_id = str(uuid.uuid4())
    generated: list[AssetImageCandidate] = []
    for _ in range(candidate_count):
        candidate = AssetImageCandidate(
            project_id=project.id,
            asset_type=normalized,
            asset_id=asset_id,
            asset_version_id=version.id,
            candidate_batch_id=batch_id,
            view_angle=view_angle,
            quality_level=AssetQualityLevel.low.value,
            source="generated",
            prompt=prompt,
            generation_params={
                "model_id": model.id,
                "model_name": model.name,
                "provider_id": model.provider_id,
                "target_ratio": ratio,
                "resolution_profile": resolution,
                "view_angle": view_angle,
                # 现有资产图链路的参考图缺失/视角不一致提示必须随候选保存，
                # 前端据此提示用户，不能把「没有可靠参考图」伪装成身份一致。
                "reference_warnings": list(getattr(derived, "reference_warnings", []) or []),
            },
            status="pending",
            format="png",
        )
        db.add(candidate)
        await db.flush()
        task_id = await stage_image_task_and_link(
            db=db,
            model_id=model.id,
            relation_type="asset_image_candidate",
            relation_entity_id=str(candidate.id),
            prompt=prompt,
            images=derived.images,
            target_ratio=ratio,
            resolution_profile=resolution,
            purpose="asset_identity_candidate",
            project_id=project.id,
        )
        candidate.generation_task_id = task_id
        generated.append(candidate)
    await db.flush()
    return generated


def _generate_storage_key(project_id: str, asset_type: str, asset_id: str, suffix: str) -> str:
    digest = hashlib.sha256(f"{asset_type}:{asset_id}:{uuid.uuid4().hex}".encode()).hexdigest()[:24]
    return f"asset-candidates/{project_id}/{asset_type}/{asset_id}/{digest}{suffix}"


async def upload_candidate(
    db: AsyncSession,
    *,
    project: Project,
    asset_type: str,
    asset_id: str,
    view_angle: str,
    file: UploadFile,
    version_id: str | None = None,
    created_by: int | None = None,
) -> AssetImageCandidate:
    """上传图片作为候选；上传本身不等于采纳或锁定。"""
    normalized = normalize_asset_type(asset_type)
    if await get_asset(db, asset_type=normalized, asset_id=asset_id) is None:
        raise ValueError("资产不存在")
    view_angle = normalize_view_angle(view_angle)
    content = await file.read()
    suffix = _check_image_bytes(file.filename or "", content)
    version = await ensure_base_version(db, asset_type=normalized, asset_id=asset_id)
    if version_id:
        version = await db.get(AssetVersion, version_id)
        if version is None or version.asset_type != normalized or version.asset_id != asset_id:
            raise ValueError("指定版本不属于当前资产")

    candidate = AssetImageCandidate(
        project_id=project.id,
        asset_type=normalized,
        asset_id=asset_id,
        asset_version_id=version.id,
        candidate_batch_id=f"upload-{uuid.uuid4().hex}",
        view_angle=view_angle,
        quality_level=AssetQualityLevel.low.value,
        source="uploaded",
        prompt="",
        generation_params={"source": "upload", "filename": file.filename or ""},
        status="pending",
        format=suffix.lstrip("."),
    )
    db.add(candidate)
    await db.flush()

    key = _generate_storage_key(project.id, normalized, asset_id, suffix)
    info = await storage.upload_file(
        key=key,
        data=content,
        content_type=_CONTENT_TYPES.get(suffix, "application/octet-stream"),
        extra_args={"ACL": "public-read"},
    )
    file_item = FileItem(
        id=str(uuid.uuid4()),
        type=FileType.image,
        name=Path(file.filename or f"upload{suffix}").name,
        thumbnail=info.url,
        tags=[],
        storage_key=key,
    )
    db.add(file_item)
    await db.flush()
    candidate.file_id = file_item.id
    candidate.status = "succeeded"
    await upsert_file_usage(
        db,
        file_id=file_item.id,
        project_id=project.id,
        chapter_id=None,
        shot_id=None,
        usage_kind=FileUsageKind.asset_image,
        source_ref=f"asset_image_candidate:{candidate.id}",
    )
    await db.flush()
    return candidate


async def adopt_candidate(
    db: AsyncSession,
    *,
    candidate: AssetImageCandidate,
    project: Project,
    make_primary: bool = True,
    adopted_by: int | None = None,
) -> AssetImageCandidate:
    """采纳候选并把文件同步到资产图片槽位；不删除其他候选。"""
    if candidate.status not in {"succeeded", "adopted"} or not candidate.file_id:
        raise ValueError("候选还没有可用图片")
    normalized = normalize_asset_type(candidate.asset_type)
    asset = await get_asset(db, asset_type=normalized, asset_id=candidate.asset_id)
    if asset is None:
        raise ValueError("资产不存在")

    if candidate.is_adopted:
        return candidate
    if normalized == "character" and asset.identity_locked_at:
        if candidate.asset_version_id == asset.identity_version_id:
            raise ValueError("视觉身份已锁定，不能替换当前身份正面图；请创建新的身份版本")

    version = None
    if candidate.asset_version_id:
        version = await db.get(AssetVersion, candidate.asset_version_id)
        if (
            version is not None
            and (version.asset_type != normalized or version.asset_id != candidate.asset_id)
        ):
            raise ValueError("候选关联的版本不属于当前资产")
    if version is None:
        version = await ensure_base_version(
            db, asset_type=normalized, asset_id=candidate.asset_id
        )
        candidate.asset_version_id = version.id
    if normalized == "character" and asset.identity_locked_at:
        if version.id == asset.identity_version_id:
            raise ValueError("视觉身份已锁定，不能替换当前身份正面图；请创建新的身份版本")

    # 同一版本同一视角只保留一个已采纳候选；历史候选仍保留为 succeeded。
    siblings = (
        await db.execute(
            select(AssetImageCandidate).where(
                AssetImageCandidate.asset_version_id == version.id,
                AssetImageCandidate.view_angle == candidate.view_angle,
                AssetImageCandidate.id != candidate.id,
                AssetImageCandidate.is_adopted.is_(True),
            )
        )
    ).scalars().all()
    for row in siblings:
        row.is_adopted = False
        row.status = "succeeded"
    candidate.is_adopted = True
    candidate.status = "adopted"
    candidate.adopted_at = datetime.now(UTC)
    candidate.adopted_by = adopted_by

    if make_primary:
        _model, image_model, parent_field = _MODELS[normalized]
        image_row = (
            await db.execute(
                select(image_model)
                .where(
                    getattr(image_model, parent_field) == candidate.asset_id,
                    image_model.quality_level == AssetQualityLevel.low,
                    image_model.view_angle == candidate.view_angle,
                )
                .limit(1)
            )
        ).scalars().first()
        if image_row is None:
            image_row = image_model(
                **{
                    parent_field: candidate.asset_id,
                    "quality_level": AssetQualityLevel.low,
                    "view_angle": candidate.view_angle,
                    "format": candidate.format,
                }
            )
            db.add(image_row)
            await db.flush()
        image_row.file_id = candidate.file_id
        image_row.format = candidate.format or image_row.format
        if normalized == "character":
            image_row.is_primary = candidate.view_angle == "FRONT"
            if image_row.is_primary:
                rows = (
                    await db.execute(
                        select(CharacterImage).where(
                            CharacterImage.character_id == candidate.asset_id,
                            CharacterImage.id != image_row.id,
                        )
                    )
                ).scalars().all()
                for row in rows:
                    row.is_primary = False
    await db.flush()
    return candidate


async def delete_candidate(
    db: AsyncSession, *, candidate: AssetImageCandidate
) -> None:
    if candidate.is_adopted:
        raise ValueError("已采纳候选不能删除；请先采纳其他候选或保留历史")
    await db.delete(candidate)
    await db.flush()


async def mark_candidate_failed(
    db: AsyncSession, *, candidate_id: int, error: str = ""
) -> None:
    candidate = await db.get(AssetImageCandidate, candidate_id)
    if candidate is None:
        return
    candidate.status = "failed"
    candidate.generation_params = {
        **(candidate.generation_params or {}),
        "error": error[:1000],
    }
    await db.flush()


async def enqueue_generated_candidates(
    db: AsyncSession, candidates: list[AssetImageCandidate]
) -> None:
    """提交候选与任务行后统一入队；入队失败显式标记任务与候选失败。"""
    await db.commit()
    from app.tasks.execute_task import enqueue_task_execution

    for candidate in candidates:
        if not candidate.generation_task_id:
            continue
        try:
            enqueue_task_execution(candidate.generation_task_id)
        except Exception as exc:  # noqa: BLE001 - 入队失败必须留痕
            from app.core.task_manager import SqlAlchemyTaskStore
            from app.core.task_manager.types import TaskStatus

            store = SqlAlchemyTaskStore(db)
            await store.set_error(candidate.generation_task_id, f"enqueue failed: {exc}")
            await store.set_status(candidate.generation_task_id, TaskStatus.failed)
            await mark_candidate_failed(db, candidate_id=candidate.id, error=str(exc))
            await db.commit()


__all__ = [
    "adopt_candidate",
    "enqueue_generated_candidates",
    "delete_candidate",
    "generate_candidates",
    "list_candidates",
    "mark_candidate_failed",
    "upload_candidate",
]
