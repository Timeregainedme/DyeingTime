-- 041-add-asset-impact-refs.sql
--
-- P4 / C8：资产版本切换时的受影响镜头快照。
--
-- 重要边界：
-- - P4 只有「资产级」引用，没有镜头级版本引用；
-- - 本表记录切换当时可查询到的关联镜头，不声称镜头已引用新版本；
-- - P6 建立镜头级有序参考绑定后，才可升级为精确版本依赖图。
--
-- 回滚：
--   DROP TABLE IF EXISTS asset_version_impact_refs;

CREATE TABLE IF NOT EXISTS asset_version_impact_refs (
  id              INT          NOT NULL AUTO_INCREMENT,
  project_id      VARCHAR(64)  NOT NULL,
  asset_type      VARCHAR(32)  NOT NULL,
  asset_id        VARCHAR(64)  NOT NULL,
  from_version_id VARCHAR(64)  NULL,
  to_version_id   VARCHAR(64)  NULL,
  shot_id         VARCHAR(64)  NOT NULL,
  chapter_id      VARCHAR(64)  NOT NULL,
  certainty       VARCHAR(24)  NOT NULL DEFAULT 'possible' COMMENT 'explicit/possible',
  reference_kind  VARCHAR(32)  NOT NULL DEFAULT 'possible',
  had_video       TINYINT(1)   NOT NULL DEFAULT 0,
  created_by      INT          NULL,
  created_at      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_asset_version_impact_pair_shot (from_version_id, to_version_id, shot_id),
  KEY ix_asset_version_impact_scope (project_id, asset_type, asset_id),
  KEY ix_asset_version_impact_shot (shot_id),
  KEY ix_asset_version_impact_chapter (chapter_id),
  CONSTRAINT fk_asset_version_impact_project
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  CONSTRAINT fk_asset_version_impact_from
    FOREIGN KEY (from_version_id) REFERENCES asset_versions(id) ON DELETE SET NULL,
  CONSTRAINT fk_asset_version_impact_to
    FOREIGN KEY (to_version_id) REFERENCES asset_versions(id) ON DELETE SET NULL,
  CONSTRAINT fk_asset_version_impact_shot
    FOREIGN KEY (shot_id) REFERENCES shots(id) ON DELETE CASCADE,
  CONSTRAINT fk_asset_version_impact_chapter
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE,
  CONSTRAINT fk_asset_version_impact_created_by
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='资产版本切换影响镜头快照';
