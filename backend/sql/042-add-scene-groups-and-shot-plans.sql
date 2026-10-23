-- 042-add-scene-groups-and-shot-plans.sql
--
-- P5 / C9 + C10：正式场次、镜头规划草稿、镜头资产版本选择与确认映射。
--
-- 命名边界：
-- - scene_groups = 剧集内剧情场次；
-- - scenes = 可复用场景资产；
-- - shots.scene_group_id 明确指向剧情场次，避免 scene_id 歧义。
--
-- 回滚（先确认无业务引用）：
--   DROP TABLE IF EXISTS shot_plan_applied_shots;
--   DROP TABLE IF EXISTS shot_asset_versions;
--   DROP TABLE IF EXISTS shot_plan_candidates;
--   DROP TABLE IF EXISTS shot_plan_drafts;
--   ALTER TABLE shots DROP FOREIGN KEY fk_shots_scene_group;
--   ALTER TABLE shots DROP COLUMN scene_group_id;
--   DROP TABLE IF EXISTS scene_groups;

CREATE TABLE IF NOT EXISTS scene_groups (
  id                  VARCHAR(64)  NOT NULL,
  project_id          VARCHAR(64)  NOT NULL,
  chapter_id          VARCHAR(64)  NOT NULL,
  `index`             INT          NOT NULL,
  title               VARCHAR(255) NOT NULL DEFAULT '',
  description         TEXT         NOT NULL,
  location            VARCHAR(255) NOT NULL DEFAULT '',
  time_of_day         VARCHAR(64)  NOT NULL DEFAULT '',
  story_event         TEXT         NOT NULL,
  primary_scene_id    VARCHAR(64)  NULL,
  source_parse_run_id VARCHAR(64)  NULL,
  source_beat_key     VARCHAR(64)  NULL,
  source_start_char   INT          NULL,
  source_end_char     INT          NULL,
  created_by          INT          NULL,
  created_at          DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at          DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_scene_groups_chapter_index (chapter_id, `index`),
  UNIQUE KEY uq_scene_groups_source_beat (chapter_id, source_parse_run_id, source_beat_key),
  KEY ix_scene_groups_project_chapter (project_id, chapter_id),
  KEY ix_scene_groups_primary_scene (primary_scene_id),
  CONSTRAINT fk_scene_groups_project
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  CONSTRAINT fk_scene_groups_chapter
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE,
  CONSTRAINT fk_scene_groups_primary_scene
    FOREIGN KEY (primary_scene_id) REFERENCES scenes(id) ON DELETE SET NULL,
  CONSTRAINT fk_scene_groups_source_run
    FOREIGN KEY (source_parse_run_id) REFERENCES script_parse_runs(id) ON DELETE SET NULL,
  CONSTRAINT fk_scene_groups_created_by
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='剧集内正式剧情场次（SceneGroup）';

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'shots'
        AND COLUMN_NAME = 'scene_group_id'
    ),
    'SELECT 1',
    'ALTER TABLE shots ADD COLUMN scene_group_id VARCHAR(64) NULL COMMENT ''所属正式场次 ID；为空表示未分配'' AFTER chapter_id, ADD KEY ix_shots_scene_group_id (scene_group_id)'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'shot_details'
        AND COLUMN_NAME = 'video_prompt_draft'
    ),
    'SELECT 1',
    'ALTER TABLE shot_details ADD COLUMN video_prompt_draft TEXT NOT NULL COMMENT ''P5 分镜规划自然语言视频提示词草稿'''
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'shots'
        AND CONSTRAINT_NAME = 'fk_shots_scene_group' AND CONSTRAINT_TYPE = 'FOREIGN KEY'
    ),
    'SELECT 1',
    'ALTER TABLE shots ADD CONSTRAINT fk_shots_scene_group FOREIGN KEY (scene_group_id) REFERENCES scene_groups(id) ON DELETE SET NULL'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

CREATE TABLE IF NOT EXISTS shot_plan_drafts (
  id                       VARCHAR(64)  NOT NULL,
  project_id               VARCHAR(64)  NOT NULL,
  chapter_id               VARCHAR(64)  NOT NULL,
  source_parse_run_id      VARCHAR(64)  NULL,
  source_script_version_id VARCHAR(64)  NULL,
  target_duration          INT          NOT NULL DEFAULT 90,
  pace                     VARCHAR(16)  NOT NULL DEFAULT 'standard',
  status                   VARCHAR(24)  NOT NULL DEFAULT 'draft',
  model_id                 VARCHAR(64)  NULL,
  model_name               VARCHAR(255) NOT NULL DEFAULT '',
  provider_name            VARCHAR(255) NOT NULL DEFAULT '',
  prompt_version           VARCHAR(64)  NOT NULL DEFAULT '',
  prompt_hash              VARCHAR(64)  NOT NULL DEFAULT '',
  task_id                  VARCHAR(64)  NULL,
  error                    TEXT         NOT NULL,
  scene_group_snapshot     JSON         NOT NULL,
  coverage                 JSON         NOT NULL,
  applied_at               DATETIME(6)  NULL,
  applied_by               INT          NULL,
  created_by               INT          NULL,
  created_at               DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at               DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  KEY ix_shot_plan_drafts_chapter_status (chapter_id, status),
  KEY ix_shot_plan_drafts_task (task_id),
  CONSTRAINT fk_shot_plan_drafts_project
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  CONSTRAINT fk_shot_plan_drafts_chapter
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE,
  CONSTRAINT fk_shot_plan_drafts_parse_run
    FOREIGN KEY (source_parse_run_id) REFERENCES script_parse_runs(id) ON DELETE SET NULL,
  CONSTRAINT fk_shot_plan_drafts_script_version
    FOREIGN KEY (source_script_version_id) REFERENCES script_document_versions(id) ON DELETE SET NULL,
  CONSTRAINT fk_shot_plan_drafts_task
    FOREIGN KEY (task_id) REFERENCES generation_tasks(id) ON DELETE SET NULL,
  CONSTRAINT fk_shot_plan_drafts_applied_by
    FOREIGN KEY (applied_by) REFERENCES users(id) ON DELETE SET NULL,
  CONSTRAINT fk_shot_plan_drafts_created_by
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='AI 分镜规划草稿';

CREATE TABLE IF NOT EXISTS shot_plan_candidates (
  id              VARCHAR(64)  NOT NULL,
  draft_id        VARCHAR(64)  NOT NULL,
  order_index     INT          NOT NULL DEFAULT 1,
  scene_group_id  VARCHAR(64)  NULL,
  candidate_key   VARCHAR(128) NOT NULL DEFAULT '',
  payload         JSON         NOT NULL,
  issues          JSON         NOT NULL,
  review_status   VARCHAR(16)  NOT NULL DEFAULT 'pending',
  source_key      VARCHAR(128) NULL,
  created_at      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_shot_plan_candidates_key (draft_id, candidate_key),
  KEY ix_shot_plan_candidates_draft_order (draft_id, order_index),
  KEY ix_shot_plan_candidates_group (scene_group_id),
  CONSTRAINT fk_shot_plan_candidates_draft
    FOREIGN KEY (draft_id) REFERENCES shot_plan_drafts(id) ON DELETE CASCADE,
  CONSTRAINT fk_shot_plan_candidates_group
    FOREIGN KEY (scene_group_id) REFERENCES scene_groups(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='AI 分镜规划候选镜头';

CREATE TABLE IF NOT EXISTS shot_asset_versions (
  id               INT          NOT NULL AUTO_INCREMENT,
  shot_id          VARCHAR(64)  NOT NULL,
  asset_type       VARCHAR(32)  NOT NULL,
  asset_id         VARCHAR(64)  NOT NULL,
  asset_version_id VARCHAR(64)  NULL,
  role             VARCHAR(32)  NOT NULL DEFAULT 'base',
  slot             INT          NOT NULL DEFAULT 0,
  source           VARCHAR(16)  NOT NULL DEFAULT 'plan',
  created_at       DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_shot_asset_versions_shot_asset_role (shot_id, asset_type, asset_id, role),
  KEY ix_shot_asset_versions_shot_type (shot_id, asset_type),
  CONSTRAINT fk_shot_asset_versions_shot
    FOREIGN KEY (shot_id) REFERENCES shots(id) ON DELETE CASCADE,
  CONSTRAINT fk_shot_asset_versions_version
    FOREIGN KEY (asset_version_id) REFERENCES asset_versions(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='镜头资产版本选择（P5；不等同 P6 参考图绑定）';

CREATE TABLE IF NOT EXISTS shot_plan_applied_shots (
  id           INT          NOT NULL AUTO_INCREMENT,
  draft_id     VARCHAR(64)  NOT NULL,
  candidate_id VARCHAR(64)  NULL,
  shot_id      VARCHAR(64)  NOT NULL,
  created_at   DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_shot_plan_applied_candidate (draft_id, candidate_id),
  UNIQUE KEY uq_shot_plan_applied_shot (draft_id, shot_id),
  KEY ix_shot_plan_applied_shot (shot_id),
  CONSTRAINT fk_shot_plan_applied_draft
    FOREIGN KEY (draft_id) REFERENCES shot_plan_drafts(id) ON DELETE CASCADE,
  CONSTRAINT fk_shot_plan_applied_candidate
    FOREIGN KEY (candidate_id) REFERENCES shot_plan_candidates(id) ON DELETE SET NULL,
  CONSTRAINT fk_shot_plan_applied_shot
    FOREIGN KEY (shot_id) REFERENCES shots(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='规划候选到正式镜头的幂等映射';
