"""P3 / C6：剧本解析任务、候选审核、确认与差异报告 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import WorkspaceContext, get_db, require_editor, require_viewer
from app.models.studio import (
    Project,
    ScriptDiffReport,
    ScriptDocument,
    ScriptDocumentVersion,
    ScriptParseRun,
)
from app.schemas.common import ApiResponse, created_response, success_response
from app.schemas.studio.script_parse import (
    ScriptDiffDecisionRequest,
    ScriptDiffReportRead,
    ScriptDiffRequest,
    ScriptParseCandidateCreate,
    ScriptParseCandidateRead,
    ScriptParseCandidateUpdate,
    ScriptParseConfirmRead,
    ScriptParseMergeRequest,
    ScriptParseRequest,
    ScriptParseRunRead,
    ScriptParseTaskRead,
)
from app.services.studio.script_diff import (
    create_diff_report,
    decide_diff_report,
    report_to_read,
)
from app.services.studio.script_parse import (
    add_candidate,
    confirm_parse_run,
    delete_candidate,
    create_parse_run,
    get_run,
    list_document_runs,
    merge_candidates,
    run_to_read,
    update_candidate,
)

router = APIRouter()


async def _version_in_workspace(
    db: AsyncSession, *, version_id: str, workspace_id: str
) -> tuple[ScriptDocumentVersion, ScriptDocument, Project]:
    row = (
        await db.execute(
            select(ScriptDocumentVersion, ScriptDocument, Project)
            .join(ScriptDocument, ScriptDocument.id == ScriptDocumentVersion.document_id)
            .join(Project, Project.id == ScriptDocument.project_id)
            .where(
                ScriptDocumentVersion.id == version_id,
                Project.workspace_id == workspace_id,
            )
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Script document version not found")
    return row[0], row[1], row[2]


async def _run_in_workspace(db: AsyncSession, *, run_id: str, workspace_id: str) -> ScriptParseRun:
    row = await db.scalar(
        select(ScriptParseRun)
        .join(ScriptDocument, ScriptDocument.id == ScriptParseRun.document_id)
        .join(Project, Project.id == ScriptDocument.project_id)
        .options(selectinload(ScriptParseRun.candidates))
        .where(ScriptParseRun.id == run_id, Project.workspace_id == workspace_id)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Script parse run not found")
    return row


async def _document_in_workspace(
    db: AsyncSession, *, document_id: str, workspace_id: str
) -> tuple[ScriptDocument, Project]:
    row = (
        await db.execute(
            select(ScriptDocument, Project)
            .join(Project, Project.id == ScriptDocument.project_id)
            .options(selectinload(ScriptDocument.versions))
            .where(
                ScriptDocument.id == document_id,
                Project.workspace_id == workspace_id,
            )
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Script document not found")
    return row[0], row[1]


@router.post(
    "/script-document-versions/{version_id}/parse",
    response_model=ApiResponse[ScriptParseTaskRead],
    status_code=status.HTTP_202_ACCEPTED,
    summary="开始解析某一集剧本",
)
async def start_script_parse_api(
    version_id: str,
    body: ScriptParseRequest,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[ScriptParseTaskRead]:
    version, document, project = await _version_in_workspace(
        db, version_id=version_id, workspace_id=ctx.workspace_id
    )
    try:
        run, reused = await create_parse_run(
            db,
            document=document,
            version=version,
            project=project,
            model_id=body.model_id,
            force=body.force,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return success_response(ScriptParseTaskRead(run=run_to_read(run), reused=reused))


@router.get(
    "/script-parse-runs/{run_id}",
    response_model=ApiResponse[ScriptParseRunRead],
    summary="解析运行详情与候选",
)
async def get_script_parse_run_api(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[ScriptParseRunRead]:
    await _run_in_workspace(db, run_id=run_id, workspace_id=ctx.workspace_id)
    data = await get_run(db, run_id=run_id)
    return success_response(data)


@router.get(
    "/script-documents/{document_id}/parse-runs",
    response_model=ApiResponse[list[ScriptParseRunRead]],
    summary="文档的解析运行历史",
)
async def list_script_parse_runs_api(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[list[ScriptParseRunRead]]:
    await _document_in_workspace(db, document_id=document_id, workspace_id=ctx.workspace_id)
    data = await list_document_runs(db, document_id=document_id)
    return success_response(data)


@router.patch(
    "/script-parse-runs/{run_id}/candidates/{candidate_id}",
    response_model=ApiResponse[ScriptParseCandidateRead],
    summary="编辑/接受/忽略解析候选",
)
async def update_script_parse_candidate_api(
    run_id: str,
    candidate_id: str,
    body: ScriptParseCandidateUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[ScriptParseCandidateRead]:
    await _run_in_workspace(db, run_id=run_id, workspace_id=ctx.workspace_id)
    try:
        data = await update_candidate(
            db, run_id=run_id, candidate_id=candidate_id, body=body
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(data)


@router.post(
    "/script-parse-runs/{run_id}/candidates",
    response_model=ApiResponse[ScriptParseCandidateRead],
    status_code=status.HTTP_201_CREATED,
    summary="人工新增解析候选",
)
async def create_script_parse_candidate_api(
    run_id: str,
    body: ScriptParseCandidateCreate,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[ScriptParseCandidateRead]:
    await _run_in_workspace(db, run_id=run_id, workspace_id=ctx.workspace_id)
    try:
        data = await add_candidate(db, run_id=run_id, body=body)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return created_response(data)


@router.delete(
    "/script-parse-runs/{run_id}/candidates/{candidate_id}",
    response_model=ApiResponse[ScriptParseRunRead],
    summary="删除解析候选",
)
async def delete_script_parse_candidate_api(
    run_id: str,
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[ScriptParseRunRead]:
    await _run_in_workspace(db, run_id=run_id, workspace_id=ctx.workspace_id)
    try:
        data = await delete_candidate(db, run_id=run_id, candidate_id=candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(data)


@router.post(
    "/script-parse-runs/{run_id}/merge",
    response_model=ApiResponse[ScriptParseRunRead],
    summary="合并重复候选",
)
async def merge_script_parse_candidates_api(
    run_id: str,
    body: ScriptParseMergeRequest,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[ScriptParseRunRead]:
    await _run_in_workspace(db, run_id=run_id, workspace_id=ctx.workspace_id)
    try:
        data = await merge_candidates(
            db,
            run_id=run_id,
            source_candidate_id=body.source_candidate_id,
            target_candidate_id=body.target_candidate_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(data)


@router.post(
    "/script-parse-runs/{run_id}/confirm",
    response_model=ApiResponse[ScriptParseConfirmRead],
    summary="确认解析结果并写入正式数据",
)
async def confirm_script_parse_run_api(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[ScriptParseConfirmRead]:
    run = await _run_in_workspace(db, run_id=run_id, workspace_id=ctx.workspace_id)
    try:
        run, summary, reused = await confirm_parse_run(
            db, run=run, confirmed_by=ctx.user_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(
        ScriptParseConfirmRead(run=run_to_read(run), applied_summary=summary, reused=reused)
    )


@router.post(
    "/script-documents/{document_id}/diff",
    response_model=ApiResponse[ScriptDiffReportRead],
    status_code=status.HTTP_201_CREATED,
    summary="生成版本差异报告",
)
async def create_script_diff_api(
    document_id: str,
    body: ScriptDiffRequest,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[ScriptDiffReportRead]:
    document, _project = await _document_in_workspace(
        db, document_id=document_id, workspace_id=ctx.workspace_id
    )
    if not document.current_version_id:
        raise HTTPException(status_code=400, detail="文档没有可比较的版本")
    new_version = await db.get(ScriptDocumentVersion, document.current_version_id)
    if new_version is None:
        raise HTTPException(status_code=404, detail="当前版本不存在")
    try:
        report = await create_diff_report(
            db,
            document=document,
            new_version=new_version,
            old_version_id=body.old_version_id,
            created_by=ctx.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return created_response(report_to_read(report))


@router.get(
    "/script-diff-reports/{report_id}",
    response_model=ApiResponse[ScriptDiffReportRead],
    summary="差异报告详情",
)
async def get_script_diff_report_api(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[ScriptDiffReportRead]:
    report = await db.scalar(
        select(ScriptDiffReport)
        .join(ScriptDocument, ScriptDocument.id == ScriptDiffReport.document_id)
        .join(Project, Project.id == ScriptDocument.project_id)
        .where(
            ScriptDiffReport.id == report_id,
            Project.workspace_id == ctx.workspace_id,
        )
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Script diff report not found")
    return success_response(report_to_read(report))


@router.post(
    "/script-diff-reports/{report_id}/status",
    response_model=ApiResponse[ScriptDiffReportRead],
    summary="接受/忽略差异报告",
)
async def decide_script_diff_report_api(
    report_id: str,
    body: ScriptDiffDecisionRequest,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[ScriptDiffReportRead]:
    report = await db.scalar(
        select(ScriptDiffReport)
        .join(ScriptDocument, ScriptDocument.id == ScriptDiffReport.document_id)
        .join(Project, Project.id == ScriptDocument.project_id)
        .where(
            ScriptDiffReport.id == report_id,
            Project.workspace_id == ctx.workspace_id,
        )
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Script diff report not found")
    try:
        report = await decide_diff_report(
            db,
            report=report,
            status_value=body.status,
            decisions=body.decisions,
            decided_by=ctx.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(report_to_read(report))
