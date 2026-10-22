"""P4：资产档案、角色别名、版本、候选图、身份锁定与音色 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.scoping import get_project_in_workspace
from app.dependencies import WorkspaceContext, get_db, require_editor, require_viewer
from app.models.studio import AssetImageCandidate, AssetVersion
from app.schemas.common import ApiResponse, created_response, success_response
from app.schemas.studio.asset_versions import (
    AssetImageCandidateRead,
    AssetProfileRead,
    AssetProfileUpdate,
    AssetVersionRead,
    CandidateAdoptRequest,
    CharacterAliasCreate,
    CharacterAliasRead,
    CharacterAliasUpdate,
    CharacterLockRequest,
    CreateDerivedVersionRequest,
    GenerateCandidatesRequest,
    SwitchVersionRequest,
    VoiceBindingRead,
    VoiceBindingUpdate,
)
from app.services.studio.asset_image_candidates import (
    adopt_candidate,
    delete_candidate,
    enqueue_generated_candidates,
    generate_candidates,
    upload_candidate,
)
from app.services.studio.asset_profiles import (
    build_asset_profile,
    update_asset_profile,
)
from app.services.studio.asset_versions import (
    asset_belongs_to_project,
    create_derived_version,
    create_identity_version,
    delete_version,
    get_asset,
    list_versions,
    normalize_asset_type,
    switch_current_version,
    version_to_read,
)
from app.services.studio.character_aliases import (
    add_alias,
    delete_alias,
    update_alias,
)
from app.services.studio.asset_impact import record_version_impact
from app.services.studio.character_identity import (
    get_voice_binding,
    lock_identity,
    update_voice_binding,
)

router = APIRouter()


async def _project_asset(
    db: AsyncSession,
    *,
    project_id: str,
    asset_type: str,
    asset_id: str,
):
    normalized = normalize_asset_type(asset_type)
    if not await asset_belongs_to_project(
        db, asset_type=normalized, asset_id=asset_id, project_id=project_id
    ):
        raise HTTPException(status_code=404, detail="Asset not found in project")
    asset = await get_asset(db, asset_type=normalized, asset_id=asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return normalized, asset


async def _candidate_in_scope(
    db: AsyncSession,
    *,
    project_id: str,
    asset_type: str,
    asset_id: str,
    candidate_id: int,
) -> AssetImageCandidate:
    candidate = await db.get(AssetImageCandidate, candidate_id)
    if (
        candidate is None
        or candidate.project_id != project_id
        or candidate.asset_type != asset_type
        or candidate.asset_id != asset_id
    ):
        raise HTTPException(status_code=404, detail="Asset image candidate not found")
    return candidate


@router.get(
    "/projects/{project_id}/assets/{asset_type}/{asset_id}/profile",
    response_model=ApiResponse[AssetProfileRead],
    summary="资产档案（角色圣经/资产版本/候选图/音色）",
)
async def get_asset_profile_api(
    project_id: str,
    asset_type: str,
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[AssetProfileRead]:
    await get_project_in_workspace(db, project_id, ctx)
    await _project_asset(db, project_id=project_id, asset_type=asset_type, asset_id=asset_id)
    return success_response(
        await build_asset_profile(
            db, project_id=project_id, asset_type=asset_type, asset_id=asset_id
        )
    )


@router.patch(
    "/projects/{project_id}/assets/{asset_type}/{asset_id}/profile",
    response_model=ApiResponse[AssetProfileRead],
    summary="更新资产文字档案",
)
async def update_asset_profile_api(
    project_id: str,
    asset_type: str,
    asset_id: str,
    body: AssetProfileUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[AssetProfileRead]:
    await get_project_in_workspace(db, project_id, ctx)
    try:
        data = await update_asset_profile(
            db,
            project_id=project_id,
            asset_type=asset_type,
            asset_id=asset_id,
            body=body,
            updated_by=ctx.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(data)


@router.post(
    "/projects/{project_id}/assets/character/{asset_id}/aliases",
    response_model=ApiResponse[CharacterAliasRead],
    status_code=status.HTTP_201_CREATED,
    summary="新增角色别名",
)
async def add_character_alias_api(
    project_id: str,
    asset_id: str,
    body: CharacterAliasCreate,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[CharacterAliasRead]:
    await get_project_in_workspace(db, project_id, ctx)
    _normalized, character = await _project_asset(
        db, project_id=project_id, asset_type="character", asset_id=asset_id
    )
    try:
        alias = await add_alias(
            db, character=character, alias=body.alias, created_by=ctx.user_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if alias is None:
        raise HTTPException(status_code=409, detail="别名与角色正式名称相同或为空")
    return created_response(CharacterAliasRead.model_validate(alias))


@router.patch(
    "/projects/{project_id}/assets/character/{asset_id}/aliases/{alias_id}",
    response_model=ApiResponse[CharacterAliasRead],
    summary="修改角色别名",
)
async def update_character_alias_api(
    project_id: str,
    asset_id: str,
    alias_id: int,
    body: CharacterAliasUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[CharacterAliasRead]:
    await get_project_in_workspace(db, project_id, ctx)
    _normalized, character = await _project_asset(
        db, project_id=project_id, asset_type="character", asset_id=asset_id
    )
    try:
        alias = await update_alias(
            db, character=character, alias_id=alias_id, alias=body.alias
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(CharacterAliasRead.model_validate(alias))


@router.delete(
    "/projects/{project_id}/assets/character/{asset_id}/aliases/{alias_id}",
    response_model=ApiResponse[None],
    summary="删除角色别名",
)
async def delete_character_alias_api(
    project_id: str,
    asset_id: str,
    alias_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[None]:
    await get_project_in_workspace(db, project_id, ctx)
    _normalized, character = await _project_asset(
        db, project_id=project_id, asset_type="character", asset_id=asset_id
    )
    try:
        await delete_alias(db, character=character, alias_id=alias_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    from app.schemas.common import empty_response

    return empty_response()


@router.get(
    "/projects/{project_id}/assets/{asset_type}/{asset_id}/versions",
    response_model=ApiResponse[list[AssetVersionRead]],
    summary="资产版本历史",
)
async def list_asset_versions_api(
    project_id: str,
    asset_type: str,
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[list[AssetVersionRead]]:
    await get_project_in_workspace(db, project_id, ctx)
    normalized, _asset = await _project_asset(
        db, project_id=project_id, asset_type=asset_type, asset_id=asset_id
    )
    rows = await list_versions(db, asset_type=normalized, asset_id=asset_id)
    return success_response([await version_to_read(db, item) for item in rows])


@router.post(
    "/projects/{project_id}/assets/{asset_type}/{asset_id}/versions",
    response_model=ApiResponse[AssetProfileRead],
    status_code=status.HTTP_201_CREATED,
    summary="创建资产衍生版本",
)
async def create_asset_version_api(
    project_id: str,
    asset_type: str,
    asset_id: str,
    body: CreateDerivedVersionRequest,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[AssetProfileRead]:
    await get_project_in_workspace(db, project_id, ctx)
    normalized, _asset = await _project_asset(
        db, project_id=project_id, asset_type=asset_type, asset_id=asset_id
    )
    try:
        await create_derived_version(
            db,
            asset_type=normalized,
            asset_id=asset_id,
            body=body,
            created_by=ctx.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return created_response(
        await build_asset_profile(
            db, project_id=project_id, asset_type=normalized, asset_id=asset_id
        )
    )


@router.post(
    "/projects/{project_id}/assets/character/{asset_id}/identity-versions",
    response_model=ApiResponse[AssetProfileRead],
    status_code=status.HTTP_201_CREATED,
    summary="创建新的角色身份草稿版本",
)
async def create_character_identity_version_api(
    project_id: str,
    asset_id: str,
    body: CreateDerivedVersionRequest,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[AssetProfileRead]:
    await get_project_in_workspace(db, project_id, ctx)
    await _project_asset(
        db, project_id=project_id, asset_type="character", asset_id=asset_id
    )
    try:
        await create_identity_version(
            db,
            asset_id=asset_id,
            name=body.name,
            description=body.description,
            attributes=body.attributes,
            created_by=ctx.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return created_response(
        await build_asset_profile(
            db, project_id=project_id, asset_type="character", asset_id=asset_id
        )
    )


@router.post(
    "/projects/{project_id}/assets/{asset_type}/{asset_id}/versions/{version_id}/switch",
    response_model=ApiResponse[AssetProfileRead],
    summary="切换当前资产/身份版本",
)
async def switch_asset_version_api(
    project_id: str,
    asset_type: str,
    asset_id: str,
    version_id: str,
    body: SwitchVersionRequest,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[AssetProfileRead]:
    await get_project_in_workspace(db, project_id, ctx)
    normalized, _asset = await _project_asset(
        db, project_id=project_id, asset_type=asset_type, asset_id=asset_id
    )
    if body.version_id != version_id:
        raise HTTPException(status_code=400, detail="version_id 不一致")
    asset = await get_asset(db, asset_type=normalized, asset_id=asset_id)
    target_version = await db.get(AssetVersion, version_id)
    from_version_id = None
    if asset is not None and target_version is not None:
        if normalized == "character" and target_version.version_kind == "identity":
            from_version_id = asset.identity_version_id
        elif normalized == "character":
            from_version_id = asset.current_appearance_version_id
        else:
            from_version_id = asset.current_version_id
    try:
        await switch_current_version(
            db,
            asset_type=normalized,
            asset_id=asset_id,
            body=body,
            switched_by=ctx.user_id,
        )
        if from_version_id and from_version_id != version_id:
            await record_version_impact(
                db,
                project_id=project_id,
                asset_type=normalized,
                asset_id=asset_id,
                from_version_id=from_version_id,
                to_version_id=version_id,
                created_by=ctx.user_id,
            )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(
        await build_asset_profile(
            db, project_id=project_id, asset_type=normalized, asset_id=asset_id
        )
    )


@router.delete(
    "/projects/{project_id}/assets/{asset_type}/{asset_id}/versions/{version_id}",
    response_model=ApiResponse[None],
    summary="删除未引用的草稿版本",
)
async def delete_asset_version_api(
    project_id: str,
    asset_type: str,
    asset_id: str,
    version_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[None]:
    await get_project_in_workspace(db, project_id, ctx)
    normalized, _asset = await _project_asset(
        db, project_id=project_id, asset_type=asset_type, asset_id=asset_id
    )
    try:
        await delete_version(
            db, asset_type=normalized, asset_id=asset_id, version_id=version_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    from app.schemas.common import empty_response

    return empty_response()


@router.get(
    "/projects/{project_id}/assets/{asset_type}/{asset_id}/candidates",
    response_model=ApiResponse[list[AssetImageCandidateRead]],
    summary="资产图片候选列表",
)
async def list_asset_candidates_api(
    project_id: str,
    asset_type: str,
    asset_id: str,
    view_angle: str | None = None,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[list[AssetImageCandidateRead]]:
    await get_project_in_workspace(db, project_id, ctx)
    normalized, _asset = await _project_asset(
        db, project_id=project_id, asset_type=asset_type, asset_id=asset_id
    )
    profile = await build_asset_profile(
        db, project_id=project_id, asset_type=normalized, asset_id=asset_id
    )
    rows = profile.candidates
    if view_angle:
        rows = [item for item in rows if item.view_angle == view_angle]
    return success_response(rows)


@router.post(
    "/projects/{project_id}/assets/{asset_type}/{asset_id}/candidates/generate",
    response_model=ApiResponse[list[AssetImageCandidateRead]],
    status_code=status.HTTP_201_CREATED,
    summary="生成资产候选图（默认两张）",
)
async def generate_asset_candidates_api(
    project_id: str,
    asset_type: str,
    asset_id: str,
    body: GenerateCandidatesRequest,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[list[AssetImageCandidateRead]]:
    project = await get_project_in_workspace(db, project_id, ctx)
    normalized, _asset = await _project_asset(
        db, project_id=project_id, asset_type=asset_type, asset_id=asset_id
    )
    try:
        candidates = await generate_candidates(
            db,
            project=project,
            asset_type=normalized,
            asset_id=asset_id,
            view_angle=body.view_angle,
            candidate_count=body.candidate_count,
            prompt_override=body.prompt,
            created_by=ctx.user_id,
        )
        await enqueue_generated_candidates(db, candidates)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    profile = await build_asset_profile(
        db, project_id=project_id, asset_type=normalized, asset_id=asset_id
    )
    return created_response(profile.candidates[: body.candidate_count])


@router.post(
    "/projects/{project_id}/assets/{asset_type}/{asset_id}/candidates/upload",
    response_model=ApiResponse[AssetProfileRead],
    status_code=status.HTTP_201_CREATED,
    summary="上传资产图片候选",
)
async def upload_asset_candidate_api(
    project_id: str,
    asset_type: str,
    asset_id: str,
    view_angle: str = "front",
    version_id: str | None = None,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[AssetProfileRead]:
    project = await get_project_in_workspace(db, project_id, ctx)
    normalized, _asset = await _project_asset(
        db, project_id=project_id, asset_type=asset_type, asset_id=asset_id
    )
    try:
        await upload_candidate(
            db,
            project=project,
            asset_type=normalized,
            asset_id=asset_id,
            view_angle=view_angle,
            file=file,
            version_id=version_id,
            created_by=ctx.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return created_response(
        await build_asset_profile(
            db, project_id=project_id, asset_type=normalized, asset_id=asset_id
        )
    )


@router.post(
    "/projects/{project_id}/assets/{asset_type}/{asset_id}/candidates/{candidate_id}/adopt",
    response_model=ApiResponse[AssetProfileRead],
    summary="采纳资产图片候选",
)
async def adopt_asset_candidate_api(
    project_id: str,
    asset_type: str,
    asset_id: str,
    candidate_id: int,
    body: CandidateAdoptRequest,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[AssetProfileRead]:
    project = await get_project_in_workspace(db, project_id, ctx)
    normalized, _asset = await _project_asset(
        db, project_id=project_id, asset_type=asset_type, asset_id=asset_id
    )
    candidate = await _candidate_in_scope(
        db,
        project_id=project_id,
        asset_type=normalized,
        asset_id=asset_id,
        candidate_id=candidate_id,
    )
    if body.version_id:
        candidate.asset_version_id = body.version_id
    try:
        await adopt_candidate(
            db,
            candidate=candidate,
            project=project,
            make_primary=body.make_primary,
            adopted_by=ctx.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(
        await build_asset_profile(
            db, project_id=project_id, asset_type=normalized, asset_id=asset_id
        )
    )


@router.delete(
    "/projects/{project_id}/assets/{asset_type}/{asset_id}/candidates/{candidate_id}",
    response_model=ApiResponse[AssetProfileRead],
    summary="删除未采纳候选图",
)
async def delete_asset_candidate_api(
    project_id: str,
    asset_type: str,
    asset_id: str,
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[AssetProfileRead]:
    await get_project_in_workspace(db, project_id, ctx)
    normalized, _asset = await _project_asset(
        db, project_id=project_id, asset_type=asset_type, asset_id=asset_id
    )
    candidate = await _candidate_in_scope(
        db,
        project_id=project_id,
        asset_type=normalized,
        asset_id=asset_id,
        candidate_id=candidate_id,
    )
    try:
        await delete_candidate(db, candidate=candidate)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(
        await build_asset_profile(
            db, project_id=project_id, asset_type=normalized, asset_id=asset_id
        )
    )


@router.post(
    "/projects/{project_id}/assets/character/{asset_id}/lock",
    response_model=ApiResponse[AssetProfileRead],
    summary="锁定角色视觉身份",
)
async def lock_character_identity_api(
    project_id: str,
    asset_id: str,
    body: CharacterLockRequest,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[AssetProfileRead]:
    await get_project_in_workspace(db, project_id, ctx)
    _normalized, character = await _project_asset(
        db, project_id=project_id, asset_type="character", asset_id=asset_id
    )
    try:
        await lock_identity(
            db,
            character=character,
            expected_lock_version=body.expected_lock_version,
            locked_by=ctx.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(
        await build_asset_profile(
            db, project_id=project_id, asset_type="character", asset_id=asset_id
        )
    )


@router.get(
    "/projects/{project_id}/assets/character/{asset_id}/voice",
    response_model=ApiResponse[VoiceBindingRead],
    summary="角色音色绑定与最终生效来源",
)
async def get_character_voice_api(
    project_id: str,
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[VoiceBindingRead]:
    await get_project_in_workspace(db, project_id, ctx)
    _normalized, character = await _project_asset(
        db, project_id=project_id, asset_type="character", asset_id=asset_id
    )
    return success_response(await get_voice_binding(db, character=character))


@router.patch(
    "/projects/{project_id}/assets/character/{asset_id}/voice",
    response_model=ApiResponse[VoiceBindingRead],
    summary="绑定/修改/解除角色音色",
)
async def update_character_voice_api(
    project_id: str,
    asset_id: str,
    body: VoiceBindingUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[VoiceBindingRead]:
    await get_project_in_workspace(db, project_id, ctx)
    _normalized, character = await _project_asset(
        db, project_id=project_id, asset_type="character", asset_id=asset_id
    )
    try:
        await update_voice_binding(
            db, character=character, body=body, bound_by=ctx.user_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(await get_voice_binding(db, character=character))
