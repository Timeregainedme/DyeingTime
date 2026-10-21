from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.studio import (
    Actor,
    ActorImage,
    Character,
    CharacterImage,
    Costume,
    CostumeImage,
    Prop,
    PropImage,
    Scene,
    SceneImage,
)
from app.services.common import entity_not_found, invalid_choice, not_belong_to, required_field


async def validate_actor_image(
    db: AsyncSession,
    *,
    actor_id: str,
    image_id: int | None,
) -> ActorImage:
    actor = await db.get(Actor, actor_id)
    if actor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=entity_not_found("Actor"))
    if image_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=required_field("image_id", when="actor generation"),
        )
    image_row = await db.get(ActorImage, image_id)
    if image_row is None or image_row.actor_id != actor_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=not_belong_to("image_id", "actor_id"),
        )
    return image_row


async def validate_asset_image_and_relation_type(
    db: AsyncSession,
    *,
    asset_type: str,
    asset_id: str,
    image_id: int | None,
) -> tuple[int, str]:
    if image_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=required_field("image_id", when="asset image generation"),
        )
    asset_type_norm = asset_type.strip().lower()
    if asset_type_norm == "prop":
        asset = await db.get(Prop, asset_id)
        if asset is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=entity_not_found("Prop"))
        image_row = await db.get(PropImage, image_id)
        if image_row is None or image_row.prop_id != asset_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=not_belong_to("image_id", "prop_id"),
            )
        return image_id, "prop_image"
    if asset_type_norm == "scene":
        asset = await db.get(Scene, asset_id)
        if asset is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=entity_not_found("Scene"))
        image_row = await db.get(SceneImage, image_id)
        if image_row is None or image_row.scene_id != asset_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=not_belong_to("image_id", "scene_id"),
            )
        return image_id, "scene_image"
    if asset_type_norm == "costume":
        asset = await db.get(Costume, asset_id)
        if asset is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=entity_not_found("Costume"))
        image_row = await db.get(CostumeImage, image_id)
        if image_row is None or image_row.costume_id != asset_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=not_belong_to("image_id", "costume_id"),
            )
        return image_id, "costume_image"
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=invalid_choice("asset_type", ["prop", "scene", "costume"]),
    )


async def validate_character_image(
    db: AsyncSession,
    *,
    character_id: str,
    image_id: int | None,
) -> CharacterImage:
    character = await db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=entity_not_found("Character"))
    if image_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=required_field("image_id", when="character image generation"),
        )
    image_row = await db.get(CharacterImage, image_id)
    if image_row is None or image_row.character_id != character_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=not_belong_to("image_id", "character_id"),
        )
    return image_row
