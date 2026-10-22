"""P3 / C5：剧本文档存储、版本管理与原文提取。

上传只创建候选版本；`activate_version` 是显式生效动作（C6 审核确认也会调用它）。
任何解析/上传都不会自动覆盖分镜或资产。
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import storage
from app.models.studio import (
    Chapter,
    FileItem,
    FileType,
    FileUsageKind,
    Project,
    ScriptDocument,
    ScriptDocumentVersion,
)
from app.schemas.studio.script_documents import (
    ScriptDocumentListRead,
    ScriptDocumentRead,
    ScriptDocumentUploadRead,
    ScriptDocumentVersionDetailRead,
    ScriptDocumentVersionRead,
)
from app.services.studio.file_usages import upsert_file_usage
from app.services.studio.script_document_parser import (
    MAX_DOCUMENT_BYTES,
    normalize_suffix,
    parse_script_document,
)

DOC_TYPE_WORLD = "worldbuilding"
DOC_TYPE_EPISODE = "episode"
ALLOWED_DOC_TYPES = {DOC_TYPE_WORLD, DOC_TYPE_EPISODE}

_CONTENT_TYPES = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".md": "text/markdown; charset=utf-8",
}


def _version_read(version: ScriptDocumentVersion | None) -> ScriptDocumentVersionRead | None:
    if version is None:
        return None
    return ScriptDocumentVersionRead.model_validate(version)


def document_to_read(document: ScriptDocument) -> ScriptDocumentRead:
    """把 ORM 文档转为带版本摘要的响应；避免调用方各自拼字段。"""
    versions = list(document.versions or [])
    by_id = {version.id: version for version in versions}
    return ScriptDocumentRead(
        id=document.id,
        project_id=document.project_id,
        chapter_id=document.chapter_id,
        doc_type=document.doc_type,
        title=document.title,
        current_version_id=document.current_version_id,
        active_version_id=document.active_version_id,
        created_at=document.created_at,
        updated_at=document.updated_at,
        versions=[ScriptDocumentVersionRead.model_validate(item) for item in versions],
        current_version=_version_read(by_id.get(document.current_version_id or "")),
        active_version=_version_read(by_id.get(document.active_version_id or "")),
    )


async def _load_document(db: AsyncSession, *, document_id: str) -> ScriptDocument:
    row = await db.scalar(
        select(ScriptDocument)
        .options(selectinload(ScriptDocument.versions))
        .where(ScriptDocument.id == document_id)
    )
    if row is None:
        raise ValueError(f"剧本文档不存在：{document_id}")
    return row


async def list_project_documents(
    db: AsyncSession, *, project_id: str
) -> ScriptDocumentListRead:
    rows = (
        await db.execute(
            select(ScriptDocument)
            .options(selectinload(ScriptDocument.versions))
            .where(ScriptDocument.project_id == project_id)
            .order_by(ScriptDocument.doc_type.asc(), ScriptDocument.created_at.asc())
        )
    ).scalars().all()
    # 世界观置顶，其余按创建时间；不依赖 doc_type 字母序。
    ordered = sorted(rows, key=lambda item: (0 if item.doc_type == DOC_TYPE_WORLD else 1, item.created_at))
    return ScriptDocumentListRead(items=[document_to_read(item) for item in ordered])


async def _find_document(
    db: AsyncSession,
    *,
    project_id: str,
    chapter_id: str | None,
    doc_type: str,
) -> ScriptDocument | None:
    stmt = select(ScriptDocument).options(selectinload(ScriptDocument.versions)).where(
        ScriptDocument.project_id == project_id,
        ScriptDocument.doc_type == doc_type,
    )
    if chapter_id is None:
        stmt = stmt.where(ScriptDocument.chapter_id.is_(None))
    else:
        stmt = stmt.where(ScriptDocument.chapter_id == chapter_id)
    return (await db.execute(stmt)).scalars().first()


async def upload_script_document(
    db: AsyncSession,
    *,
    project: Project,
    doc_type: str,
    file: UploadFile,
    chapter: Chapter | None = None,
    title: str | None = None,
    created_by: int | None = None,
) -> ScriptDocumentUploadRead:
    """保存原始文件 + 提取原文，并创建候选版本。

    去重规则：同一文档下内容哈希相同视为重复上传，直接返回已有版本。
    """
    normalized_type = (doc_type or "").strip()
    if normalized_type not in ALLOWED_DOC_TYPES:
        raise ValueError("doc_type 只支持 worldbuilding / episode")
    if normalized_type == DOC_TYPE_EPISODE and chapter is None:
        raise ValueError("每集剧本必须指定 chapter_id")
    if normalized_type == DOC_TYPE_WORLD and chapter is not None:
        raise ValueError("世界观文档不能绑定 chapter_id")

    if not file.filename:
        raise ValueError("上传文件缺少文件名")
    content = await file.read()
    if len(content) > MAX_DOCUMENT_BYTES:
        raise ValueError(f"文件超过大小限制（{MAX_DOCUMENT_BYTES // 1024 // 1024}MB）")

    parsed = parse_script_document(filename=file.filename, content=content)
    if not parsed.text.strip():
        raise ValueError("文档内容为空，无法创建版本")

    content_hash = hashlib.sha256(content).hexdigest()
    document = await _find_document(
        db,
        project_id=project.id,
        chapter_id=chapter.id if chapter else None,
        doc_type=normalized_type,
    )
    existing_versions = list(document.versions or []) if document is not None else []

    if document is not None:
        duplicated = next(
            (item for item in existing_versions if item.content_hash == content_hash),
            None,
        )
        if duplicated is not None:
            return ScriptDocumentUploadRead(
                document=document_to_read(document),
                version=ScriptDocumentVersionRead.model_validate(duplicated),
                created=False,
                warnings=list((duplicated.extract_meta or {}).get("warnings") or []),
            )

    if document is None:
        document = ScriptDocument(
            id=str(uuid.uuid4()),
            project_id=project.id,
            chapter_id=chapter.id if chapter else None,
            doc_type=normalized_type,
            title=(title or "").strip()
            or (chapter.title if chapter else f"{project.name} 世界观与人物设定"),
            created_by=created_by,
        )
        db.add(document)
        await db.flush()
    elif title:
        document.title = title.strip()

    version_no = max((item.version_no for item in existing_versions), default=0) + 1
    version_id = str(uuid.uuid4())
    suffix = normalize_suffix(file.filename)
    storage_key = f"script-documents/{project.id}/{document.id}/v{version_no}-{uuid.uuid4().hex}{suffix}"
    info = await storage.upload_file(
        key=storage_key,
        data=content,
        content_type=_CONTENT_TYPES.get(suffix, "application/octet-stream"),
        # 剧本可能含未公开内容，不主动设置 public-read；下载统一走鉴权接口。
    )
    file_item = FileItem(
        id=str(uuid.uuid4()),
        type=FileType.document,
        name=Path(file.filename).name,
        thumbnail=info.url,
        tags=[],
        storage_key=storage_key,
    )
    db.add(file_item)
    await db.flush()
    await upsert_file_usage(
        db,
        file_id=file_item.id,
        project_id=project.id,
        chapter_id=chapter.id if chapter else None,
        shot_id=None,
        usage_kind=FileUsageKind.script_document,
        source_ref=version_id,
    )

    is_first = document.active_version_id is None
    version = ScriptDocumentVersion(
        id=version_id,
        document_id=document.id,
        version_no=version_no,
        file_id=file_item.id,
        file_name=Path(file.filename).name,
        file_type=parsed.file_type,
        content_hash=content_hash,
        raw_text=parsed.text,
        text_length=parsed.char_count,
        status="active" if is_first else "candidate",
        parse_status="not_parsed",
        extract_meta={
            "warnings": parsed.warnings,
            "table_count": parsed.table_count,
            "image_count": parsed.image_count,
        },
        created_by=created_by,
    )
    db.add(version)
    await db.flush()
    document.current_version_id = version.id
    if is_first:
        document.active_version_id = version.id
    await db.flush()
    # selectinload 不会自动包含刚 add 的版本；重新读取一次保证响应完整。
    document = await _load_document(db, document_id=document.id)
    return ScriptDocumentUploadRead(
        document=document_to_read(document),
        version=ScriptDocumentVersionRead.model_validate(version),
        created=True,
        warnings=parsed.warnings,
    )


async def get_document_detail(db: AsyncSession, *, document_id: str) -> ScriptDocumentRead:
    document = await _load_document(db, document_id=document_id)
    return document_to_read(document)


async def get_version_detail(
    db: AsyncSession, *, document_id: str, version_id: str
) -> ScriptDocumentVersionDetailRead:
    document = await _load_document(db, document_id=document_id)
    version = next((item for item in (document.versions or []) if item.id == version_id), None)
    if version is None:
        raise ValueError(f"文档版本不存在：{version_id}")
    return ScriptDocumentVersionDetailRead(
        **ScriptDocumentVersionRead.model_validate(version).model_dump(),
        raw_text=version.raw_text,
    )


async def activate_version(
    db: AsyncSession, *, document_id: str, version_id: str
) -> ScriptDocumentRead:
    """显式启用版本：更新章节原文，并把旧生效版本标记为 superseded。

    只在这里（或 C6 审核确认）同步 `chapters.raw_text`；上传/解析阶段不会覆盖。
    """
    document = await _load_document(db, document_id=document_id)
    target = next((item for item in (document.versions or []) if item.id == version_id), None)
    if target is None:
        raise ValueError(f"文档版本不存在：{version_id}")

    for item in document.versions or []:
        if item.status == "active" and item.id != target.id:
            item.status = "superseded"
    target.status = "active"
    document.active_version_id = target.id
    document.current_version_id = target.id

    if document.doc_type == DOC_TYPE_EPISODE and document.chapter_id:
        chapter = await db.get(Chapter, document.chapter_id)
        if chapter is not None:
            chapter.raw_text = target.raw_text
            # 旧精简文本基于旧原文，继续保留会造成误用；交给后续提取重新生成。
            chapter.condensed_text = ""

    await db.flush()
    document = await _load_document(db, document_id=document.id)
    return document_to_read(document)


async def get_script_document_for_workspace(
    db: AsyncSession, *, document_id: str, workspace_id: str
) -> ScriptDocument:
    """按工作区读取文档（join projects），供路由与 C6 复用。"""
    row = await db.scalar(
        select(ScriptDocument)
        .join(Project, Project.id == ScriptDocument.project_id)
        .options(selectinload(ScriptDocument.versions))
        .where(
            ScriptDocument.id == document_id,
            Project.workspace_id == workspace_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="ScriptDocument not found")
    return row
