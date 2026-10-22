-- 039-add-asset-versions.sql
--
-- P4 / C7：角色别名、资产版本与图片候选。
--
-- 设计边界：
-- - Character/Scene/Prop/Costume 仍是唯一主实体；
-- - 版本通过 asset_type + asset_id 多态关联，不复制主实体；
-- - 候选图与已采纳图片分离，重新抽卡不会覆盖当前形象；
-- - 主实体上的 current_version_id / identity_version_id 指向当前生效版本。
--
-- 回滚：
--   DROP TABLE IF EXISTS asset_image_candidates;
--   DROP TABLE IF EXISTS asset_versions;
--   DROP TABLE IF EXISTS character_aliases;

CREATE TABLE IF NOT EXISTS character_aliases (
  id               INT          NOT NULL AUTO_INCREMENT,
  character_id     VARCHAR(64)  NOT NULL COMMENT '角色 ID',
  alias            VARCHAR(255) NOT NULL COMMENT '原始别名/称谓',
  normalized_alias VARCHAR(255) NOT NULL COMMENT '归一化别名',
  source           VARCHAR(16)  NOT NULL DEFAULT 'manual' COMMENT 'manual / p3_parse',
  created_by       INT          NULL,
  created_at       DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at       DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_character_aliases_character_alias (character_id, normalized_alias),
  KEY ix_character_aliases_normalized (normalized_alias),
  CONSTRAINT fk_character_aliases_character
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
  CONSTRAINT fk_character_aliases_created_by
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='角色别名/称谓';

CREATE TABLE IF NOT EXISTS asset_versions (
  id                VARCHAR(64)  NOT NULL COMMENT '版本 ID',
  project_id        VARCHAR(64)  NOT NULL COMMENT '项目 ID',
  asset_type        VARCHAR(32)  NOT NULL COMMENT 'character/scene/prop/costume',
  asset_id          VARCHAR(64)  NOT NULL COMMENT '主实体 ID',
  version_no        INT          NOT NULL COMMENT '资产内版本号',
  parent_version_id VARCHAR(64)  NULL COMMENT '父版本 ID',
  version_kind      VARCHAR(24)  NOT NULL DEFAULT 'base' COMMENT 'identity/appearance/base/derived',
  variant_type      VARCHAR(32)  NOT NULL DEFAULT 'base' COMMENT 'base/costume/hairstyle/makeup/age/weather/lighting/other',
  name              VARCHAR(255) NOT NULL DEFAULT '',
  description       TEXT         NOT NULL,
  attributes        JSON         NULL,
  source            VARCHAR(16)  NOT NULL DEFAULT 'manual' COMMENT 'manual/generated/uploaded/p3_confirm',
  status            VARCHAR(16)  NOT NULL DEFAULT 'draft' COMMENT 'draft/active/superseded',
  created_by        INT          NULL,
  created_at        DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at        DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_asset_versions_asset_no (asset_type, asset_id, version_no),
  KEY ix_asset_versions_scope (project_id, asset_type, asset_id),
  KEY ix_asset_versions_parent (parent_version_id),
  KEY ix_asset_versions_status (status),
  CONSTRAINT fk_asset_versions_project
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  CONSTRAINT fk_asset_versions_parent
    FOREIGN KEY (parent_version_id) REFERENCES asset_versions(id) ON DELETE SET NULL,
  CONSTRAINT fk_asset_versions_created_by
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='资产身份/造型/基础/衍生版本';

CREATE TABLE IF NOT EXISTS asset_image_candidates (
  id                  INT          NOT NULL AUTO_INCREMENT,
  project_id          VARCHAR(64)  NOT NULL,
  asset_type          VARCHAR(32)  NOT NULL,
  asset_id            VARCHAR(64)  NOT NULL,
  asset_version_id    VARCHAR(64)  NULL,
  candidate_batch_id  VARCHAR(64)  NOT NULL DEFAULT '',
  view_angle          VARCHAR(32)  NOT NULL DEFAULT 'FRONT',
  quality_level       VARCHAR(16)  NOT NULL DEFAULT 'low',
  file_id             VARCHAR(64)  NULL,
  source              VARCHAR(16)  NOT NULL DEFAULT 'generated',
  generation_task_id  VARCHAR(64)  NULL,
  prompt              TEXT         NOT NULL,
  generation_params   JSON         NULL,
  status              VARCHAR(16)  NOT NULL DEFAULT 'pending',
  width               INT          NULL,
  height              INT          NULL,
  format              VARCHAR(32)  NOT NULL DEFAULT 'png',
  is_adopted          TINYINT(1)   NOT NULL DEFAULT 0,
  adopted_at          DATETIME(6)  NULL,
  adopted_by          INT          NULL,
  created_at          DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at          DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  KEY ix_asset_image_candidates_scope (project_id, asset_type, asset_id),
  KEY ix_asset_image_candidates_batch (candidate_batch_id),
  KEY ix_asset_image_candidates_task (generation_task_id),
  KEY ix_asset_image_candidates_version (asset_version_id),
  KEY ix_asset_image_candidates_file (file_id),
  CONSTRAINT fk_asset_image_candidates_project
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  CONSTRAINT fk_asset_image_candidates_version
    FOREIGN KEY (asset_version_id) REFERENCES asset_versions(id) ON DELETE SET NULL,
  CONSTRAINT fk_asset_image_candidates_file
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE SET NULL,
  CONSTRAINT fk_asset_image_candidates_task
    FOREIGN KEY (generation_task_id) REFERENCES generation_tasks(id) ON DELETE SET NULL,
  CONSTRAINT fk_asset_image_candidates_adopted_by
    FOREIGN KEY (adopted_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='资产图片候选（生成/上传）';
