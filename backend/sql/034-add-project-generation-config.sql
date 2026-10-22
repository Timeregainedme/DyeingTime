-- 034-add-project-generation-config.sql
--
-- P2 / C3：项目级生成配置与模型快照。
--
-- 设计要点：
-- 1. 项目显式持有图片/视频/音频模型 ID；为空时回退到全局 ModelSettings。
--    这样修改全局默认模型不会静默改变已初始化项目。
-- 2. 模型 ID 只存引用，不存 API Key、Base URL 等凭据；凭据始终由服务端
--    按 provider_id 在运行时解析。
-- 3. 业务时长范围（4–15 秒）落在项目上，供应商能力（H3 为 4–30 秒）由
--    适配器声明，生成前取两者交集。
-- 4. `use_dialog_audio_as_reference` 只修改“新行默认值”，不批量回填存量项目。
--
-- 回滚：
--   ALTER TABLE projects DROP FOREIGN KEY fk_projects_default_image_model;
--   ALTER TABLE projects DROP FOREIGN KEY fk_projects_default_video_model;
--   ALTER TABLE projects DROP FOREIGN KEY fk_projects_default_audio_model;
--   ALTER TABLE projects
--     DROP COLUMN default_image_model_id,
--     DROP COLUMN default_video_model_id,
--     DROP COLUMN default_audio_model_id,
--     DROP COLUMN default_reference_mode,
--     DROP COLUMN default_shot_duration,
--     DROP COLUMN video_duration_min,
--     DROP COLUMN video_duration_max,
--     DROP COLUMN video_concurrency,
--     DROP COLUMN generation_config_version,
--     DROP COLUMN generation_config_confirmed_at,
--     DROP COLUMN generation_config_updated_at,
--     DROP COLUMN generation_config_snapshot;
--   ALTER TABLE projects ALTER COLUMN use_dialog_audio_as_reference SET DEFAULT 1;

-- 图片模型
SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'projects'
        AND COLUMN_NAME = 'default_image_model_id'
    ),
    'SELECT 1',
    'ALTER TABLE projects ADD COLUMN default_image_model_id VARCHAR(64) NULL COMMENT ''项目默认图片模型 ID；为空回退全局默认'' AFTER default_video_resolution, ADD KEY ix_projects_default_image_model_id (default_image_model_id), ADD CONSTRAINT fk_projects_default_image_model FOREIGN KEY (default_image_model_id) REFERENCES models(id) ON DELETE SET NULL'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 视频模型
SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'projects'
        AND COLUMN_NAME = 'default_video_model_id'
    ),
    'SELECT 1',
    'ALTER TABLE projects ADD COLUMN default_video_model_id VARCHAR(64) NULL COMMENT ''项目默认视频模型 ID；为空回退全局默认'' AFTER default_image_model_id, ADD KEY ix_projects_default_video_model_id (default_video_model_id), ADD CONSTRAINT fk_projects_default_video_model FOREIGN KEY (default_video_model_id) REFERENCES models(id) ON DELETE SET NULL'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 音频模型
SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'projects'
        AND COLUMN_NAME = 'default_audio_model_id'
    ),
    'SELECT 1',
    'ALTER TABLE projects ADD COLUMN default_audio_model_id VARCHAR(64) NULL COMMENT ''项目默认音频模型 ID；为空回退全局默认'' AFTER default_video_model_id, ADD KEY ix_projects_default_audio_model_id (default_audio_model_id), ADD CONSTRAINT fk_projects_default_audio_model FOREIGN KEY (default_audio_model_id) REFERENCES models(id) ON DELETE SET NULL'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 默认参考模式（P2 固定多参考；保留字段以便后续扩展）
SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'projects'
        AND COLUMN_NAME = 'default_reference_mode'
    ),
    'SELECT 1',
    'ALTER TABLE projects ADD COLUMN default_reference_mode VARCHAR(32) NOT NULL DEFAULT ''reference'' COMMENT ''H3 默认参考模式（reference=多参考）'' AFTER default_audio_model_id'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 默认镜头时长（业务值）
SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'projects'
        AND COLUMN_NAME = 'default_shot_duration'
    ),
    'SELECT 1',
    'ALTER TABLE projects ADD COLUMN default_shot_duration INT NOT NULL DEFAULT 5 COMMENT ''项目默认镜头时长（秒）'' AFTER default_reference_mode'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 业务时长下限（与供应商能力取交集）
SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'projects'
        AND COLUMN_NAME = 'video_duration_min'
    ),
    'SELECT 1',
    'ALTER TABLE projects ADD COLUMN video_duration_min INT NOT NULL DEFAULT 4 COMMENT ''项目业务时长下限（秒）'' AFTER default_shot_duration'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 业务时长上限（P2 固定 15，不因 H3 支持 30 秒而扩大）
SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'projects'
        AND COLUMN_NAME = 'video_duration_max'
    ),
    'SELECT 1',
    'ALTER TABLE projects ADD COLUMN video_duration_max INT NOT NULL DEFAULT 15 COMMENT ''项目业务时长上限（秒）'' AFTER video_duration_min'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 批量并发
SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'projects'
        AND COLUMN_NAME = 'video_concurrency'
    ),
    'SELECT 1',
    'ALTER TABLE projects ADD COLUMN video_concurrency INT NOT NULL DEFAULT 4 COMMENT ''视频批量并发数（默认 4）'' AFTER video_duration_max'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 配置版本
SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'projects'
        AND COLUMN_NAME = 'generation_config_version'
    ),
    'SELECT 1',
    'ALTER TABLE projects ADD COLUMN generation_config_version INT NOT NULL DEFAULT 1 COMMENT ''生成配置版本；确认时递增'' AFTER video_concurrency'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 配置确认时间（为空 = 仍是草稿/未初始化）
SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'projects'
        AND COLUMN_NAME = 'generation_config_confirmed_at'
    ),
    'SELECT 1',
    'ALTER TABLE projects ADD COLUMN generation_config_confirmed_at DATETIME(6) NULL COMMENT ''生成配置确认时间；为空表示未确认'' AFTER generation_config_version'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 配置最近保存时间
SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'projects'
        AND COLUMN_NAME = 'generation_config_updated_at'
    ),
    'SELECT 1',
    'ALTER TABLE projects ADD COLUMN generation_config_updated_at DATETIME(6) NULL COMMENT ''生成配置最近保存时间'' AFTER generation_config_confirmed_at'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 配置快照（确认时写入；只含模型 ID/名称/供应商/能力，不含密钥）
SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'projects'
        AND COLUMN_NAME = 'generation_config_snapshot'
    ),
    'SELECT 1',
    'ALTER TABLE projects ADD COLUMN generation_config_snapshot JSON NULL COMMENT ''已确认的生成配置快照（不含凭据）'' AFTER generation_config_updated_at'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 仅修改新行默认值：存量项目保持原有 True/False 设置，不做批量回填。
ALTER TABLE projects ALTER COLUMN use_dialog_audio_as_reference SET DEFAULT 0;
