"""P6：角色固定音色样本上传/列表 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.scoping import get_entity_in_workspace
from app.dependencies import WorkspaceContext, get_db, require_editor, require_viewer
from app.models.studio import Character, CharacterVoiceSample, FileItem
from app.schemas.common import ApiResponse, created_response, empty_response, success_response
from app.schemas.studio.voice_samples import VoiceSampleRead
from app.services.studio.voice_samples import (
    deactivate_voice_sample,
    list_voice_samples,
    upload_voice_sample,
)

router = APIRouter()


async def _to_read(db: AsyncSession, row: CharacterVoiceSample) -> VoiceSampleRead:
    file_url = ""
    if row.file_id:
        file_item = await db.get(FileItem, row.file_id)
        file_url = (file_item.thumbnail or "") if file_item else ""
    return VoiceSampleRead(
        id=row.id,
        character_id=row.character_id,
        file_id=row.file_id,
        file_url=file_url,
        label=row.label,
        is_active=row.is_active,
    )


@router.get(
    "/characters/{character_id}/voice-samples",
    response_model=ApiResponse[list[VoiceSampleRead]],
    summary="角色固定音色样本列表",
)
async def list_voice_samples_api(
    character_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[list[VoiceSampleRead]]:
    entity = await get_entity_in_workspace(db, character_id, ctx, entity_type="character")
    if not isinstance(entity, Character):
        raise HTTPException(status_code=404, detail="Character not found")
    rows = await list_voice_samples(db, character_id=character_id)
    return success_response([await _to_read(db, item) for item in rows])


@router.post(
    "/characters/{character_id}/voice-samples",
    response_model=ApiResponse[VoiceSampleRead],
    status_code=status.HTTP_201_CREATED,
    summary="上传角色固定音色样本",
)
async def upload_voice_sample_api(
    character_id: str,
    file: UploadFile = File(...),
    label: str = Form(""),
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[VoiceSampleRead]:
    entity = await get_entity_in_workspace(db, character_id, ctx, entity_type="character")
    if not isinstance(entity, Character):
        raise HTTPException(status_code=404, detail="Character not found")
    try:
        row = await upload_voice_sample(db, character=entity, file=file, label=label)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return created_response(await _to_read(db, row))


@router.delete(
    "/characters/{character_id}/voice-samples/{sample_id}",
    response_model=ApiResponse[None],
    summary="停用角色固定音色样本",
)
async def delete_voice_sample_api(
    character_id: str,
    sample_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[None]:
    await get_entity_in_workspace(db, character_id, ctx, entity_type="character")
    try:
        await deactivate_voice_sample(
            db, character_id=character_id, sample_id=sample_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return empty_response()
