"""P3 / C5：剧本文档上传、版本读取与生效。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.scoping import get_chapter_in_workspace, get_project_in_workspace
from app.dependencies import WorkspaceContext, get_db, require_editor, require_viewer
from app.schemas.common import ApiResponse, created_response, success_response
from app.schemas.studio.script_documents import (
    ScriptDocumentListRead,
    ScriptDocumentRead,
    ScriptDocumentUploadRead,
    ScriptDocumentVersionDetailRead,
)
from app.services.studio.script_documents import (
    DOC_TYPE_EPISODE,
    DOC_TYPE_WORLD,
    activate_version,
    get_document_detail,
    get_script_document_for_workspace,
    get_version_detail,
    list_project_documents,
    upload_script_document,
)

router = APIRouter()


@router.get(
    "/projects/{project_id}/script-documents",
    response_model=ApiResponse[ScriptDocumentListRead],
    summary="项目剧本文档列表",
)
async def list_script_documents_api(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[ScriptDocumentListRead]:
    await get_project_in_workspace(db, project_id, ctx)
    data = await list_project_documents(db, project_id=project_id)
    return success_response(data)


@router.post(
    "/projects/{project_id}/script-documents/worldbuilding",
    response_model=ApiResponse[ScriptDocumentUploadRead],
    status_code=status.HTTP_201_CREATED,
    summary="上传世界观与人物设定文档",
)
async def upload_worldbuilding_document_api(
    project_id: str,
    file: UploadFile = File(..., description=".docx 或 .md"),
    title: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[ScriptDocumentUploadRead]:
    project = await get_project_in_workspace(db, project_id, ctx)
    try:
        data = await upload_script_document(
            db,
            project=project,
            doc_type=DOC_TYPE_WORLD,
            file=file,
            title=title,
            created_by=ctx.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if data.created:
        return created_response(data)
    return success_response(data)


@router.post(
    "/projects/{project_id}/chapters/{chapter_id}/script-document",
    response_model=ApiResponse[ScriptDocumentUploadRead],
    status_code=status.HTTP_201_CREATED,
    summary="上传某一集剧本文件",
)
async def upload_episode_document_api(
    project_id: str,
    chapter_id: str,
    file: UploadFile = File(..., description=".docx 或 .md"),
    title: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[ScriptDocumentUploadRead]:
    project = await get_project_in_workspace(db, project_id, ctx)
    chapter = await get_chapter_in_workspace(db, chapter_id, ctx)
    if chapter.project_id != project.id:
        raise HTTPException(status_code=404, detail="Chapter not found in project")
    try:
        data = await upload_script_document(
            db,
            project=project,
            chapter=chapter,
            doc_type=DOC_TYPE_EPISODE,
            file=file,
            title=title,
            created_by=ctx.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if data.created:
        return created_response(data)
    return success_response(data)


@router.get(
    "/script-documents/{document_id}",
    response_model=ApiResponse[ScriptDocumentRead],
    summary="剧本文档详情与版本列表",
)
async def get_script_document_api(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[ScriptDocumentRead]:
    await get_script_document_for_workspace(
        db, document_id=document_id, workspace_id=ctx.workspace_id
    )
    try:
        data = await get_document_detail(db, document_id=document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return success_response(data)


@router.get(
    "/script-documents/{document_id}/versions/{version_id}",
    response_model=ApiResponse[ScriptDocumentVersionDetailRead],
    summary="读取文档版本原文",
)
async def get_script_document_version_api(
    document_id: str,
    version_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[ScriptDocumentVersionDetailRead]:
    await get_script_document_for_workspace(
        db, document_id=document_id, workspace_id=ctx.workspace_id
    )
    try:
        data = await get_version_detail(
            db, document_id=document_id, version_id=version_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return success_response(data)


@router.post(
    "/script-documents/{document_id}/versions/{version_id}/activate",
    response_model=ApiResponse[ScriptDocumentRead],
    summary="启用某个文档版本并同步章节原文",
)
async def activate_script_document_version_api(
    document_id: str,
    version_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[ScriptDocumentRead]:
    await get_script_document_for_workspace(
        db, document_id=document_id, workspace_id=ctx.workspace_id
    )
    try:
        data = await activate_version(db, document_id=document_id, version_id=version_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(data)
