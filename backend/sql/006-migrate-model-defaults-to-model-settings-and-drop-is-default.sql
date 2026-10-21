SET @has_model_settings_table = (
  SELECT COUNT(*)
  FROM information_schema.TABLES
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'model_settings'
);

SET @create_model_settings_table = IF(
  @has_model_settings_table = 0,
  "CREATE TABLE model_settings (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY COMMENT '设置行 ID（通常为 1）',
    default_text_model_id VARCHAR(64) NULL COMMENT '默认文本模型 ID',
    default_image_model_id VARCHAR(64) NULL COMMENT '默认图片模型 ID',
    default_video_model_id VARCHAR(64) NULL COMMENT '默认视频模型 ID',
    api_timeout INT NOT NULL DEFAULT 30 COMMENT 'API 超时（秒）',
    log_level VARCHAR(16) NOT NULL DEFAULT 'info' COMMENT '日志级别',
    CONSTRAINT fk_model_settings_default_text_model_id FOREIGN KEY (default_text_model_id) REFERENCES models(id) ON DELETE SET NULL,
    CONSTRAINT fk_model_settings_default_image_model_id FOREIGN KEY (default_image_model_id) REFERENCES models(id) ON DELETE SET NULL,
    CONSTRAINT fk_model_settings_default_video_model_id FOREIGN KEY (default_video_model_id) REFERENCES models(id) ON DELETE SET NULL
  )",
  'SELECT 1'
);
PREPARE stmt_create_model_settings_table FROM @create_model_settings_table;
EXECUTE stmt_create_model_settings_table;
DEALLOCATE PREPARE stmt_create_model_settings_table;

INSERT INTO model_settings (id, api_timeout, log_level)
SELECT 1, 30, 'info'
WHERE NOT EXISTS (SELECT 1 FROM model_settings WHERE id = 1);

SET @has_models_is_default = (
  SELECT COUNT(*)
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'models'
    AND COLUMN_NAME = 'is_default'
);

SET @sync_default_text_model = IF(
  @has_models_is_default = 1,
  "UPDATE model_settings ms
   SET ms.default_text_model_id = COALESCE(
     ms.default_text_model_id,
     (
       SELECT m.id
       FROM models m
       WHERE m.category = 'text'
       ORDER BY m.is_default DESC, m.updated_at DESC
       LIMIT 1
     )
   )
   WHERE ms.id = 1",
  'SELECT 1'
);
PREPARE stmt_sync_default_text_model FROM @sync_default_text_model;
EXECUTE stmt_sync_default_text_model;
DEALLOCATE PREPARE stmt_sync_default_text_model;

SET @sync_default_image_model = IF(
  @has_models_is_default = 1,
  "UPDATE model_settings ms
   SET ms.default_image_model_id = COALESCE(
     ms.default_image_model_id,
     (
       SELECT m.id
       FROM models m
       WHERE m.category = 'image'
       ORDER BY m.is_default DESC, m.updated_at DESC
       LIMIT 1
     )
   )
   WHERE ms.id = 1",
  'SELECT 1'
);
PREPARE stmt_sync_default_image_model FROM @sync_default_image_model;
EXECUTE stmt_sync_default_image_model;
DEALLOCATE PREPARE stmt_sync_default_image_model;

SET @sync_default_video_model = IF(
  @has_models_is_default = 1,
  "UPDATE model_settings ms
   SET ms.default_video_model_id = COALESCE(
     ms.default_video_model_id,
     (
       SELECT m.id
       FROM models m
       WHERE m.category = 'video'
       ORDER BY m.is_default DESC, m.updated_at DESC
       LIMIT 1
     )
   )
   WHERE ms.id = 1",
  'SELECT 1'
);
PREPARE stmt_sync_default_video_model FROM @sync_default_video_model;
EXECUTE stmt_sync_default_video_model;
DEALLOCATE PREPARE stmt_sync_default_video_model;

SET @drop_models_is_default = IF(
  @has_models_is_default = 1,
  'ALTER TABLE models DROP COLUMN is_default',
  'SELECT 1'
);
PREPARE stmt_drop_models_is_default FROM @drop_models_is_default;
EXECUTE stmt_drop_models_is_default;
DEALLOCATE PREPARE stmt_drop_models_is_default;
