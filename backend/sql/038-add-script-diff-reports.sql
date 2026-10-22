-- 038-add-script-diff-reports.sql
--
-- P3 / C6：剧本版本差异报告。
--
-- 文本差异、结构化差异与影响范围分开保存；
-- 人工决策（accepted / ignored）独立记录，不自动覆盖正式业务数据。
--
-- 回滚：
--   DROP TABLE IF EXISTS script_diff_reports;

CREATE TABLE IF NOT EXISTS script_diff_reports (
  id             VARCHAR(64) NOT NULL COMMENT '差异报告 ID',
  document_id    VARCHAR(64) NOT NULL COMMENT '剧本文档 ID',
  old_version_id VARCHAR(64) NOT NULL COMMENT '旧版本 ID',
  new_version_id VARCHAR(64) NOT NULL COMMENT '新版本 ID',
  status         VARCHAR(16) NOT NULL DEFAULT 'draft' COMMENT 'draft / accepted / ignored',
  text_diff      JSON        NOT NULL,
  structured_diff JSON       NOT NULL,
  impact         JSON        NOT NULL,
  decisions      JSON        NOT NULL,
  decided_by     INT         NULL,
  decided_at     DATETIME(6) NULL,
  created_at     DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at     DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_script_diff_version_pair (old_version_id, new_version_id),
  KEY ix_script_diff_reports_document (document_id),
  KEY ix_script_diff_reports_new_version (new_version_id),
  CONSTRAINT fk_script_diff_reports_document
    FOREIGN KEY (document_id) REFERENCES script_documents(id) ON DELETE CASCADE,
  CONSTRAINT fk_script_diff_reports_old
    FOREIGN KEY (old_version_id) REFERENCES script_document_versions(id) ON DELETE CASCADE,
  CONSTRAINT fk_script_diff_reports_new
    FOREIGN KEY (new_version_id) REFERENCES script_document_versions(id) ON DELETE CASCADE,
  CONSTRAINT fk_script_diff_reports_decided_by
    FOREIGN KEY (decided_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='剧本版本差异报告';
