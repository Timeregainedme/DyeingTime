-- 036-add-script-documents.sql
--
-- P3 / C5：剧本文档与版本。
--
-- 设计要点：
-- - 原始文件保存在 files（type=document），提取原文保存在版本表；
-- - current_version_id = 最近上传版本，active_version_id = 当前生效版本；
--   上传候选不会立刻覆盖 chapters.raw_text；
-- - 一集一个 episode 文档，项目一个 worldbuilding 文档（应用层保证 worldbuilding 唯一）。
--
-- 回滚：
--   DROP TABLE IF EXISTS script_document_versions;
--   DROP TABLE IF EXISTS script_documents;

CREATE TABLE IF NOT EXISTS script_documents (
  id                 VARCHAR(64)  NOT NULL COMMENT '文档 ID',
  project_id         VARCHAR(64)  NOT NULL COMMENT '所属项目 ID',
  chapter_id         VARCHAR(64)  NULL COMMENT '所属章节 ID；世界观文档为空',
  doc_type           VARCHAR(32)  NOT NULL COMMENT 'worldbuilding / episode',
  title              VARCHAR(255) NOT NULL DEFAULT '' COMMENT '展示标题',
  current_version_id VARCHAR(64)  NULL COMMENT '最近上传版本 ID',
  active_version_id  VARCHAR(64)  NULL COMMENT '当前生效版本 ID',
  created_by         INT          NULL COMMENT '上传者账号 ID',
  created_at         DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at         DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_script_documents_scope (project_id, chapter_id, doc_type),
  KEY ix_script_documents_project_type (project_id, doc_type),
  KEY ix_script_documents_current_version (current_version_id),
  KEY ix_script_documents_active_version (active_version_id),
  CONSTRAINT fk_script_documents_project
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  CONSTRAINT fk_script_documents_chapter
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE,
  CONSTRAINT fk_script_documents_created_by
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='剧本文档（世界观 / 每集剧本）';

CREATE TABLE IF NOT EXISTS script_document_versions (
  id            VARCHAR(64)  NOT NULL COMMENT '版本 ID',
  document_id   VARCHAR(64)  NOT NULL COMMENT '所属文档 ID',
  version_no    INT          NOT NULL COMMENT '版本号，从 1 开始',
  file_id       VARCHAR(64)  NULL COMMENT '原始上传文件 ID',
  file_name     VARCHAR(255) NOT NULL DEFAULT '' COMMENT '原始文件名',
  file_type     VARCHAR(16)  NOT NULL DEFAULT '' COMMENT 'docx / md',
  content_hash  VARCHAR(64)  NOT NULL DEFAULT '' COMMENT '原始文件 SHA-256',
  raw_text      LONGTEXT     NOT NULL COMMENT '提取后的完整原文',
  text_length   INT          NOT NULL DEFAULT 0 COMMENT '原文长度（字符）',
  status        VARCHAR(16)  NOT NULL DEFAULT 'candidate' COMMENT 'candidate / active / superseded',
  parse_status  VARCHAR(16)  NOT NULL DEFAULT 'not_parsed' COMMENT 'not_parsed / parsing / parsed / failed',
  metadata      JSON         NULL COMMENT '提取告警、表格/图片统计等',
  created_by    INT          NULL COMMENT '上传者账号 ID',
  created_at    DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at    DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_script_document_versions_no (document_id, version_no),
  KEY ix_script_document_versions_hash (content_hash),
  KEY ix_script_document_versions_file (file_id),
  CONSTRAINT fk_script_document_versions_document
    FOREIGN KEY (document_id) REFERENCES script_documents(id) ON DELETE CASCADE,
  CONSTRAINT fk_script_document_versions_file
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE SET NULL,
  CONSTRAINT fk_script_document_versions_created_by
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='剧本文档版本（原始文件 + 提取原文）';
