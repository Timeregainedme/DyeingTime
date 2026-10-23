-- 043-add-shot-reference-bindings.sql
--
-- P6 / C11：镜头级有序参考绑定、@ 引用与不可变生成输入快照。
--
-- 回滚：
--   DROP TABLE IF EXISTS shot_generation_snapshots;
--   DROP TABLE IF EXISTS shot_prompt_references;
--   DROP TABLE IF EXISTS shot_reference_bindings;

CREATE TABLE IF NOT EXISTS shot_reference_bindings (
  id               INT          NOT NULL AUTO_INCREMENT,
  shot_id          VARCHAR(64)  NOT NULL,
  file_id          VARCHAR(64)  NULL,
  asset_type       VARCHAR(32)  NOT NULL DEFAULT 'shot_reference',
  asset_id         VARCHAR(64)  NULL,
  asset_version_id VARCHAR(64)  NULL,
  reference_role   VARCHAR(32)  NOT NULL DEFAULT 'shot_composition',
  source           VARCHAR(16)  NOT NULL DEFAULT 'auto',
  sort_order       INT          NOT NULL DEFAULT 0,
  is_pinned        TINYINT(1)   NOT NULL DEFAULT 0,
  is_active        TINYINT(1)   NOT NULL DEFAULT 1,
  created_by       INT          NULL,
  created_at       DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at       DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_shot_reference_bindings_shot_file (shot_id, file_id),
  KEY ix_shot_reference_bindings_order (shot_id, sort_order),
  KEY ix_shot_reference_bindings_asset (asset_type, asset_id),
  CONSTRAINT fk_shot_reference_bindings_shot
    FOREIGN KEY (shot_id) REFERENCES shots(id) ON DELETE CASCADE,
  CONSTRAINT fk_shot_reference_bindings_file
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE SET NULL,
  CONSTRAINT fk_shot_reference_bindings_version
    FOREIGN KEY (asset_version_id) REFERENCES asset_versions(id) ON DELETE SET NULL,
  CONSTRAINT fk_shot_reference_bindings_created_by
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='镜头有序参考素材绑定';

CREATE TABLE IF NOT EXISTS shot_prompt_references (
  id               INT          NOT NULL AUTO_INCREMENT,
  shot_id          VARCHAR(64)  NOT NULL,
  asset_type       VARCHAR(32)  NOT NULL,
  asset_id         VARCHAR(64)  NOT NULL,
  asset_version_id VARCHAR(64)  NULL,
  mention          VARCHAR(255) NOT NULL DEFAULT '',
  start_index      INT          NULL,
  end_index        INT          NULL,
  created_at       DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  KEY ix_shot_prompt_references_shot (shot_id),
  CONSTRAINT fk_shot_prompt_references_shot
    FOREIGN KEY (shot_id) REFERENCES shots(id) ON DELETE CASCADE,
  CONSTRAINT fk_shot_prompt_references_version
    FOREIGN KEY (asset_version_id) REFERENCES asset_versions(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='镜头提示词 @ 资产引用';

CREATE TABLE IF NOT EXISTS shot_generation_snapshots (
  id              VARCHAR(64)  NOT NULL,
  shot_id         VARCHAR(64)  NOT NULL,
  project_id      VARCHAR(64)  NOT NULL,
  chapter_id      VARCHAR(64)  NOT NULL,
  scene_group_id  VARCHAR(64)  NULL,
  task_id         VARCHAR(64)  NULL,
  model_id        VARCHAR(64)  NULL,
  model_name      VARCHAR(255) NOT NULL DEFAULT '',
  provider_name   VARCHAR(255) NOT NULL DEFAULT '',
  reference_mode  VARCHAR(16)  NOT NULL DEFAULT 'reference',
  manifest        JSON         NOT NULL,
  prompt          TEXT         NOT NULL,
  natural_prompt  TEXT         NOT NULL,
  advanced_prompt TEXT         NOT NULL,
  prompt_refs     JSON         NOT NULL,
  audio_refs      JSON         NOT NULL,
  asset_versions  JSON         NOT NULL,
  generation_params JSON       NOT NULL,
  style_snapshot  JSON         NOT NULL,
  duration        INT          NOT NULL DEFAULT 0,
  ratio           VARCHAR(16)  NOT NULL DEFAULT '',
  resolution      VARCHAR(16)  NULL,
  input_hash      VARCHAR(64)  NOT NULL DEFAULT '',
  created_by      INT          NULL,
  created_at      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  KEY ix_shot_generation_snapshots_shot_created (shot_id, created_at),
  KEY ix_shot_generation_snapshots_task (task_id),
  KEY ix_shot_generation_snapshots_hash (input_hash),
  CONSTRAINT fk_shot_generation_snapshots_shot
    FOREIGN KEY (shot_id) REFERENCES shots(id) ON DELETE CASCADE,
  CONSTRAINT fk_shot_generation_snapshots_task
    FOREIGN KEY (task_id) REFERENCES generation_tasks(id) ON DELETE SET NULL,
  CONSTRAINT fk_shot_generation_snapshots_created_by
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='镜头视频生成不可变输入快照';
