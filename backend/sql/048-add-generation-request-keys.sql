-- 048-add-generation-request-keys.sql
-- P8 / C17-B：生成请求持久化幂等键。
-- 单镜头：shot_generation_snapshots(shot_id, request_key) 唯一；
-- 批次：video_generation_batches(chapter_id, request_key) 唯一，并保存请求 hash 检测同 key 不同 payload。
-- 回滚（先确认无业务依赖）：
--   ALTER TABLE shot_generation_snapshots DROP INDEX uq_shot_generation_snapshots_request;
--   ALTER TABLE shot_generation_snapshots DROP COLUMN request_key;
--   ALTER TABLE video_generation_batches DROP INDEX uq_video_batches_request;
--   ALTER TABLE video_generation_batches DROP COLUMN request_key, DROP COLUMN request_hash;

SET @ddl = (
  SELECT IF(
    EXISTS(SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='shot_generation_snapshots' AND COLUMN_NAME='request_key'),
    'SELECT 1',
    'ALTER TABLE shot_generation_snapshots ADD COLUMN request_key VARCHAR(128) NULL COMMENT ''客户端幂等键'' AFTER input_hash, ADD KEY ix_shot_generation_snapshots_request_key (request_key)'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(SELECT 1 FROM information_schema.STATISTICS
      WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='shot_generation_snapshots' AND INDEX_NAME='uq_shot_generation_snapshots_request'),
    'SELECT 1',
    'ALTER TABLE shot_generation_snapshots ADD UNIQUE KEY uq_shot_generation_snapshots_request (shot_id, request_key)'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='video_generation_batches' AND COLUMN_NAME='request_key'),
    'SELECT 1',
    'ALTER TABLE video_generation_batches ADD COLUMN request_key VARCHAR(128) NULL COMMENT ''客户端幂等键'' AFTER coordinator_task_id, ADD COLUMN request_hash VARCHAR(64) NOT NULL DEFAULT '''' COMMENT ''请求 hash'' AFTER request_key, ADD KEY ix_video_batches_request_key (request_key)'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(SELECT 1 FROM information_schema.STATISTICS
      WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='video_generation_batches' AND INDEX_NAME='uq_video_batches_request'),
    'SELECT 1',
    'ALTER TABLE video_generation_batches ADD UNIQUE KEY uq_video_batches_request (chapter_id, request_key)'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;
