"""镜头资产总览服务：聚合已关联资产与提取候选。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.studio import Shot, ShotCandidateStatus
from app.schemas.studio.shots import (
    ShotAssetOverviewItem,
    ShotAssetsOverviewRead,
    ShotAssetsOverviewSummary,
)
from app.services.common import entity_not_found, require_entity
from app.services.studio.shot_assets import list_shot_linked_assets
from app.services.studio.shot_extracted_candidates import list_by_shot


def _normalize_name(name: str) -> str:
    return str(name).strip()


def _payload_value(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value)


def _enum_or_str_value(value: Any) -> str | None:
    if value is None:
        return None
    raw = getattr(value, "value", value)
    if raw is None:
        return None
    return str(raw)


async def get_shot_assets_overview(
    db: AsyncSession,
    *,
    shot_id: str,
) -> ShotAssetsOverviewRead:
    shot = await require_entity(db, Shot, shot_id, detail=entity_not_found("Shot"), status_code=400)
    linked_assets = await list_shot_linked_assets(db, shot_id=shot_id)
    candidates = await list_by_shot(db, shot_id=shot_id)

    item_by_key: dict[str, ShotAssetOverviewItem] = {}

    for linked in linked_assets:
        key = f"{linked.type}:{_normalize_name(linked.name)}"
        item_by_key[key] = ShotAssetOverviewItem(
            key=key,
            type=linked.type,
            name=linked.name,
            description=None,
            thumbnail=(linked.thumbnail or None),
            file_id=linked.file_id,
            source="linked",
            candidate_id=None,
            candidate_status=None,
            linked_entity_id=linked.id,
            linked_image_id=linked.image_id,
            is_linked=True,
        )

    for candidate in candidates:
        candidate_type = _enum_or_str_value(candidate.candidate_type)
        candidate_status = _enum_or_str_value(candidate.candidate_status)
        if not candidate_type:
            continue
        key = f"{candidate_type}:{_normalize_name(candidate.candidate_name)}"
        payload = dict(candidate.payload or {})
        existing = item_by_key.get(key)
        description = _payload_value(payload, "description")
        thumbnail = _payload_value(payload, "thumbnail")
        file_id = _payload_value(payload, "file_id")

        if existing is None:
            item_by_key[key] = ShotAssetOverviewItem(
                key=key,
                type=candidate_type,  # type: ignore[arg-type]
                name=candidate.candidate_name,
                description=description,
                thumbnail=thumbnail,
                file_id=file_id,
                source="candidate",
                candidate_id=candidate.id,
                candidate_status=candidate_status,  # type: ignore[arg-type]
                linked_entity_id=candidate.linked_entity_id,
                linked_image_id=None,
                is_linked=candidate_status == ShotCandidateStatus.linked.value,
            )
            continue

        item_by_key[key] = existing.model_copy(
            update={
                "description": description or existing.description,
                "thumbnail": thumbnail or existing.thumbnail,
                "file_id": file_id or existing.file_id,
                "source": "both",
                "candidate_id": candidate.id,
                "candidate_status": candidate_status,
                "linked_entity_id": existing.linked_entity_id or candidate.linked_entity_id,
                "is_linked": True,
            }
        )

    items = sorted(
        item_by_key.values(),
        key=lambda item: (
            0
            if item.candidate_status == ShotCandidateStatus.pending.value
            else 1
            if item.is_linked
            else 2,
            item.type,
            item.name,
        ),
    )

    linked_count = sum(1 for item in items if item.is_linked)
    pending_count = sum(1 for item in items if item.candidate_status == ShotCandidateStatus.pending.value)
    ignored_count = sum(1 for item in items if item.candidate_status == ShotCandidateStatus.ignored.value)

    return ShotAssetsOverviewRead(
        shot_id=shot.id,
        skip_extraction=bool(shot.skip_extraction),
        status=shot.status,
        summary=ShotAssetsOverviewSummary(
            linked_count=linked_count,
            pending_count=pending_count,
            ignored_count=ignored_count,
            total_count=len(items),
        ),
        items=items,
    )
