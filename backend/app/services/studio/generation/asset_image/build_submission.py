from __future__ import annotations

from pydantic import Field

from app.services.studio.generation.asset_image.build_base import AssetImageBaseDraft
from app.services.studio.generation.asset_image.build_context import build_asset_image_context
from app.services.studio.generation.asset_image.derive_preview import derive_asset_image_preview
from app.services.studio.generation.shared.types import GenerationSubmissionPayload
from app.services.studio.image_task_validation import (
    validate_actor_image,
    validate_asset_image_and_relation_type,
    validate_character_image,
)


class AssetImageSubmissionPayload(GenerationSubmissionPayload):
    """资产图片生成最终提交载荷。"""

    kind: str = "asset_image"
    relation_type: str = Field(...)
    relation_entity_id: str = Field(...)


def _payload_from_base_and_images(
    *,
    base: AssetImageBaseDraft,
    images: list[str] | None,
) -> AssetImageSubmissionPayload:
    context = build_asset_image_context(base=base, images=images)
    preview = derive_asset_image_preview(base=base, context=context)
    return AssetImageSubmissionPayload(
        prompt=preview.prompt,
        images=preview.images,
        relation_type=preview.relation_type,
        relation_entity_id=preview.relation_entity_id,
        extra={"context_source": context.source},
    )


async def build_actor_image_submission_payload(
    db,
    *,
    actor_id: str,
    image_id: int | None,
    prompt: str,
    images: list[str] | None,
) -> AssetImageSubmissionPayload:
    image_row = await validate_actor_image(db, actor_id=actor_id, image_id=image_id)
    base = AssetImageBaseDraft(
        entity_type="actor",
        entity_id=actor_id,
        image_id=image_row.id,
        relation_type="actor_image",
        relation_entity_id=str(image_row.id),
        prompt=(prompt or "").strip(),
        default_images=[],
    )
    return _payload_from_base_and_images(base=base, images=images)


async def build_asset_image_submission_payload(
    db,
    *,
    asset_type: str,
    asset_id: str,
    image_id: int | None,
    prompt: str,
    images: list[str] | None,
) -> AssetImageSubmissionPayload:
    relation_entity_id, relation_type = await validate_asset_image_and_relation_type(
        db,
        asset_type=asset_type,
        asset_id=asset_id,
        image_id=image_id,
    )
    base = AssetImageBaseDraft(
        entity_type=asset_type.strip().lower(),
        entity_id=asset_id,
        image_id=relation_entity_id,
        relation_type=relation_type,
        relation_entity_id=str(relation_entity_id),
        prompt=(prompt or "").strip(),
        default_images=[],
    )
    return _payload_from_base_and_images(base=base, images=images)


async def build_character_image_submission_payload(
    db,
    *,
    character_id: str,
    image_id: int | None,
    prompt: str,
    images: list[str] | None,
) -> AssetImageSubmissionPayload:
    image_row = await validate_character_image(db, character_id=character_id, image_id=image_id)
    base = AssetImageBaseDraft(
        entity_type="character",
        entity_id=character_id,
        image_id=image_row.id,
        relation_type="character_image",
        relation_entity_id=str(image_row.id),
        prompt=(prompt or "").strip(),
        default_images=[],
    )
    return _payload_from_base_and_images(base=base, images=images)
