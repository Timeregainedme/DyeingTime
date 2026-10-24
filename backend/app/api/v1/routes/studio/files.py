"""文件素材相关路由：上传 / 下载 / 列表 / 详情。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.scoping import get_file_in_workspace, require_scoped_resource
from app.dependencies import WorkspaceContext, get_db, get_workspace_context
from app.schemas.common import ApiResponse, PaginatedData, created_response, empty_response, paginated_response, success_response
from app.schemas.studio import FileDetailRead, FileRead, FileUpdate
from app.services.studio.file_usages import list_files_by_scope_paginated
from app.services.studio.files import (
    build_download_response,
    delete_file,
    get_file_detail as get_file_detail_service,
    get_storage_info,
    list_files_paginated,
    update_file_meta as update_file_meta_service,
    upload_file,
)
# 受保护路由：列表 / 上传 / 详情 / 更新 / 删除
router = APIRouter(
    # 文件归属经 file_usages → projects 反查（files 表自身无归属列）。
    dependencies=[Depends(require_scoped_resource("file_id", get_file_in_workspace))],
)

# 下载路由：仍然单独拆出，但必须经过登录与工作区文件归属校验。
#
# 说明：
# - 前端图片/视频大多直接使用对象存储 URL（见 FileItem.thumbnail），因此不会
#   因为本路由要求 Authorization 而裂图；
# - API 下载入口统一加 `require_scoped_resource`，禁止通过猜 file_id 读取
#   其他工作区文件；
# - 对象存储本身的公开读仍是独立的安全边界，生产环境应改为私有桶 + 签名 URL。
public_router = APIRouter()


@router.get(
    "",
    response_model=ApiResponse[PaginatedData[FileRead]],
    summary="文件列表（分页）",
)
async def list_files_api(
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    q: str | None = Query(None, description="关键字，过滤 name"),
    order: str | None = Query(None),
    is_desc: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    project_id: str | None = Query(None, description="按 file_usages 限定项目；提供后仅返回该项目下有关联记录的文件"),
    chapter_title: str | None = Query(None, description="章节标题（精确匹配，与 project_id 联用）"),
    shot_title: str | None = Query(None, description="镜头标题（精确匹配，与 project_id 联用）"),
) -> ApiResponse[PaginatedData[FileRead]]:
    if chapter_title is not None or shot_title is not None:
        if not project_id:
            raise HTTPException(
                status_code=400,
                detail="project_id is required when chapter_title or shot_title is set",
            )

    if project_id is not None:
        items, total = await list_files_by_scope_paginated(
            db,
            project_id=project_id,
            chapter_title=chapter_title,
            shot_title=shot_title,
            q=q,
            order=order,
            is_desc=is_desc,
            page=page,
            page_size=page_size,
            workspace_id=ctx.workspace_id,
        )
        return paginated_response(
            [FileRead.model_validate(x) for x in items],
            page=page,
            page_size=page_size,
            total=total,
        )
    return await list_files_paginated(
        db,
        q=q,
        order=order,
        is_desc=is_desc,
        page=page,
        page_size=page_size,
        workspace_id=ctx.workspace_id,
    )


@router.post(
    "/upload",
    response_model=ApiResponse[FileRead],
    status_code=status.HTTP_201_CREATED,
    summary="上传文件并创建 FileItem 记录",
)
async def upload_file_api(
    file: UploadFile = File(..., description="要上传的二进制文件"),
    name: str | None = None,
    db: AsyncSession = Depends(get_db),
    project_id: str | None = Form(None, description="可选：写入 file_usages 的项目 ID"),
    chapter_id: str | None = Form(None),
    shot_id: str | None = Form(None),
    usage_kind: str | None = Form(None, description="与 project_id 同时提供时写入 file_usages"),
    source_ref: str | None = Form(None),
) -> ApiResponse[FileRead]:
    obj = await upload_file(
        db,
        file=file,
        name=name,
        project_id=project_id,
        chapter_id=chapter_id,
        shot_id=shot_id,
        usage_kind=usage_kind,
        source_ref=source_ref,
    )
    return created_response(FileRead.model_validate(obj))


async def _serve_download(file_id: str, request: Request, db: AsyncSession):
    """GET/HEAD 共用的下载响应构建。

    单独拆出的原因：GET 与 HEAD 必须各自声明，才能给它们不同的
    `operation_id`。此前用 `api_route(methods=["GET", "HEAD"])` 让一个函数
    同时注册两个方法，FastAPI 生成 operationId 时取 `route.methods` 的第一个
    元素，而 `methods` 是 set —— 顺序随 `PYTHONHASHSEED` 变化，导致
    `/openapi.json` 在每台机器上产出不同的 operationId，契约基线无法稳定比对，
    前端 generated client 也生成了 `...DownloadHead` 与 `...DownloadHead1`
    这类无意义重名。
    """
    return await build_download_response(
        db,
        file_id=file_id,
        range_header=request.headers.get("range"),
    )


@public_router.get(
    "/{file_id}/download",
    operation_id="download_file",
    summary="下载文件二进制内容（需登录且校验工作区归属）",
    dependencies=[Depends(require_scoped_resource("file_id", get_file_in_workspace))],
)
async def download_file_api(
    file_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """下载/内联展示素材二进制。

    必须登录并通过文件工作区归属校验；对象存储公开 URL 的存在不等于 API
    可以匿名放行。若对象存储已给出公开 URL（files.thumbnail），直接 302 重定向：
      - 不占用 EC2 出网带宽（视频可达数百 MB）
      - Range 请求由对象存储处理，播放器可正常 seek
      - 可被 CDN 缓存
    仅在无公开 URL 时回退到后端流式代理。
    """
    return await _serve_download(file_id, request, db)


@public_router.head(
    "/{file_id}/download",
    operation_id="download_file_head",
    summary="探测文件可下载性（HEAD，需登录且校验工作区归属）",
    dependencies=[Depends(require_scoped_resource("file_id", get_file_in_workspace))],
)
async def download_file_head_api(
    file_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """HEAD 探测，与 GET 共用同一套响应头。

    为什么必须有：浏览器 <video>/<audio> 与部分下载器会先发 HEAD 探测
    Content-Length / Accept-Ranges，只注册 GET 会返回 405 Method Not Allowed。
    """
    return await _serve_download(file_id, request, db)


@router.get(
    "/{file_id}/storage-info",
    response_model=ApiResponse[dict],
    summary="获取对象存储详情（head_object）",
)
async def get_file_storage_info_api(
    file_id: str,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    return success_response(await get_storage_info(db, file_id=file_id))


@router.get(
    "/{file_id}",
    response_model=ApiResponse[FileDetailRead],
    summary="获取文件详情（元信息 + file_usages）",
)
async def get_file_detail(
    file_id: str,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[FileDetailRead]:
    return success_response(await get_file_detail_service(db, file_id=file_id))


@router.patch(
    "/{file_id}",
    response_model=ApiResponse[FileRead],
    summary="更新文件元信息",
)
async def update_file_meta(
    file_id: str,
    body: FileUpdate,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[FileRead]:
    obj = await update_file_meta_service(db, file_id=file_id, body=body)
    return success_response(FileRead.model_validate(obj))


@router.delete(
    "/{file_id}",
    response_model=ApiResponse[None],
    summary="删除文件（记录 + 存储对象）",
)
async def delete_file_api(
    file_id: str,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    await delete_file(db, file_id=file_id)
    return empty_response()
