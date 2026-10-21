-- 2026-04-03
-- 为分镜提取确认流程新增中间状态结构：
-- 1. shots.skip_extraction
-- 2. shots.last_extracted_at
-- 3. shot_extracted_candidates 表
-- 说明：
-- - 在 fresh init 场景下，init_db.py 可能已经创建过这些结构
-- - 这里必须允许重复执行，避免 compose 第二次启动失败

BEGIN;


SET @has_shots_skip_extraction = (
  SELECT COUNT(*)
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'shots'
    AND COLUMN_NAME = 'skip_extraction'
);

SET @add_shots_skip_extraction = IF(
  @has_shots_skip_extraction = 0,
  'ALTER TABLE shots ADD COLUMN skip_extraction BOOLEAN NOT NULL DEFAULT 0',
  'SELECT 1'
);
PREPARE stmt_add_shots_skip_extraction FROM @add_shots_skip_extraction;
EXECUTE stmt_add_shots_skip_extraction;
DEALLOCATE PREPARE stmt_add_shots_skip_extraction;

SET @has_shots_last_extracted_at = (
  SELECT COUNT(*)
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'shots'
    AND COLUMN_NAME = 'last_extracted_at'
);

SET @add_shots_last_extracted_at = IF(
  @has_shots_last_extracted_at = 0,
  'ALTER TABLE shots ADD COLUMN last_extracted_at DATETIME NULL',
  'SELECT 1'
);
PREPARE stmt_add_shots_last_extracted_at FROM @add_shots_last_extracted_at;
EXECUTE stmt_add_shots_last_extracted_at;
DEALLOCATE PREPARE stmt_add_shots_last_extracted_at;

CREATE TABLE IF NOT EXISTS shot_extracted_candidates (
  id INTEGER PRIMARY KEY AUTO_INCREMENT,
  shot_id VARCHAR(64) NOT NULL,
  candidate_type VARCHAR(32) NOT NULL,
  candidate_name VARCHAR(255) NOT NULL,
  candidate_status VARCHAR(32) NOT NULL DEFAULT 'pending',
  linked_entity_id VARCHAR(64) NULL,
  source VARCHAR(32) NOT NULL DEFAULT 'extraction',
  payload JSON NULL,
  confirmed_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_shot_extracted_candidates_shot
    FOREIGN KEY (shot_id) REFERENCES shots(id) ON DELETE CASCADE,
  CONSTRAINT uq_shot_extracted_candidates_shot_type_name
    UNIQUE (shot_id, candidate_type, candidate_name),
  CONSTRAINT ck_shot_extracted_candidates_type
    CHECK (candidate_type IN ('character', 'scene', 'prop', 'costume')),
  CONSTRAINT ck_shot_extracted_candidates_status
    CHECK (candidate_status IN ('pending', 'linked', 'ignored'))
);

SET @has_ix_shot_extracted_candidates_shot_id = (
  SELECT COUNT(*)
  FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'shot_extracted_candidates'
    AND INDEX_NAME = 'ix_shot_extracted_candidates_shot_id'
);

SET @create_ix_shot_extracted_candidates_shot_id = IF(
  @has_ix_shot_extracted_candidates_shot_id = 0,
  'CREATE INDEX ix_shot_extracted_candidates_shot_id ON shot_extracted_candidates (shot_id)',
  'SELECT 1'
);
PREPARE stmt_shot_idx FROM @create_ix_shot_extracted_candidates_shot_id;
EXECUTE stmt_shot_idx;
DEALLOCATE PREPARE stmt_shot_idx;

SET @has_ix_shot_extracted_candidates_status = (
  SELECT COUNT(*)
  FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'shot_extracted_candidates'
    AND INDEX_NAME = 'ix_shot_extracted_candidates_status'
);

SET @create_ix_shot_extracted_candidates_status = IF(
  @has_ix_shot_extracted_candidates_status = 0,
  'CREATE INDEX ix_shot_extracted_candidates_status ON shot_extracted_candidates (candidate_status)',
  'SELECT 1'
);
PREPARE stmt_status_idx FROM @create_ix_shot_extracted_candidates_status;
EXECUTE stmt_status_idx;
DEALLOCATE PREPARE stmt_status_idx;

SET @has_ix_shot_extracted_candidates_type = (
  SELECT COUNT(*)
  FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'shot_extracted_candidates'
    AND INDEX_NAME = 'ix_shot_extracted_candidates_type'
);

SET @create_ix_shot_extracted_candidates_type = IF(
  @has_ix_shot_extracted_candidates_type = 0,
  'CREATE INDEX ix_shot_extracted_candidates_type ON shot_extracted_candidates (candidate_type)',
  'SELECT 1'
);
PREPARE stmt_type_idx FROM @create_ix_shot_extracted_candidates_type;
EXECUTE stmt_type_idx;
DEALLOCATE PREPARE stmt_type_idx;

COMMIT;
