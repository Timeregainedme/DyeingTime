-- 030-add-fallback-text-model.sql
-- 文本模型失败时的备用模型（默认指向 OpenCode Go 的 minimax-m3）。
--
-- 背景：分镜切分/资产提取是单次长调用，主模型超时或返回不可解析时，
-- 只重试同一模型往往仍然很慢。备用模型让任务可以快速降级完成。
SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'model_settings'
        AND COLUMN_NAME = 'fallback_text_model_id'
    ),
    'SELECT 1',
    'ALTER TABLE model_settings ADD COLUMN fallback_text_model_id VARCHAR(64) NULL COMMENT ''文本模型失败时的备用模型 ID'' AFTER default_text_model_id'
  )
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

UPDATE model_settings
SET fallback_text_model_id = (
  SELECT id FROM models WHERE LOWER(name) = 'minimax-m3' LIMIT 1
)
WHERE id = 1
  AND fallback_text_model_id IS NULL
  AND EXISTS (SELECT 1 FROM models WHERE LOWER(name) = 'minimax-m3');
