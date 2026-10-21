SET @has_generation_tasks_cancel_requested = (
  SELECT COUNT(*)
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'generation_tasks'
    AND COLUMN_NAME = 'cancel_requested'
);

SET @add_generation_tasks_cancel_requested = IF(
  @has_generation_tasks_cancel_requested = 0,
  "ALTER TABLE generation_tasks ADD COLUMN cancel_requested TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已请求取消'",
  'SELECT 1'
);
PREPARE stmt_add_generation_tasks_cancel_requested FROM @add_generation_tasks_cancel_requested;
EXECUTE stmt_add_generation_tasks_cancel_requested;
DEALLOCATE PREPARE stmt_add_generation_tasks_cancel_requested;

SET @has_generation_tasks_cancel_requested_at = (
  SELECT COUNT(*)
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'generation_tasks'
    AND COLUMN_NAME = 'cancel_requested_at'
);

SET @add_generation_tasks_cancel_requested_at = IF(
  @has_generation_tasks_cancel_requested_at = 0,
  "ALTER TABLE generation_tasks ADD COLUMN cancel_requested_at DATETIME NULL COMMENT '请求取消时间'",
  'SELECT 1'
);
PREPARE stmt_add_generation_tasks_cancel_requested_at FROM @add_generation_tasks_cancel_requested_at;
EXECUTE stmt_add_generation_tasks_cancel_requested_at;
DEALLOCATE PREPARE stmt_add_generation_tasks_cancel_requested_at;

SET @has_generation_tasks_cancel_reason = (
  SELECT COUNT(*)
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'generation_tasks'
    AND COLUMN_NAME = 'cancel_reason'
);

SET @add_generation_tasks_cancel_reason = IF(
  @has_generation_tasks_cancel_reason = 0,
  "ALTER TABLE generation_tasks ADD COLUMN cancel_reason VARCHAR(255) NULL COMMENT '取消原因'",
  'SELECT 1'
);
PREPARE stmt_add_generation_tasks_cancel_reason FROM @add_generation_tasks_cancel_reason;
EXECUTE stmt_add_generation_tasks_cancel_reason;
DEALLOCATE PREPARE stmt_add_generation_tasks_cancel_reason;

SET @has_generation_tasks_cancelled_at = (
  SELECT COUNT(*)
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'generation_tasks'
    AND COLUMN_NAME = 'cancelled_at'
);

SET @add_generation_tasks_cancelled_at = IF(
  @has_generation_tasks_cancelled_at = 0,
  "ALTER TABLE generation_tasks ADD COLUMN cancelled_at DATETIME NULL COMMENT '实际取消完成时间'",
  'SELECT 1'
);
PREPARE stmt_add_generation_tasks_cancelled_at FROM @add_generation_tasks_cancelled_at;
EXECUTE stmt_add_generation_tasks_cancelled_at;
DEALLOCATE PREPARE stmt_add_generation_tasks_cancelled_at;

SET @has_ix_generation_tasks_status_cancel_requested = (
  SELECT COUNT(*)
  FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'generation_tasks'
    AND INDEX_NAME = 'ix_generation_tasks_status_cancel_requested'
);

SET @create_ix_generation_tasks_status_cancel_requested = IF(
  @has_ix_generation_tasks_status_cancel_requested = 0,
  'CREATE INDEX ix_generation_tasks_status_cancel_requested ON generation_tasks (status, cancel_requested)',
  'SELECT 1'
);
PREPARE stmt_ix_generation_tasks_status_cancel_requested FROM @create_ix_generation_tasks_status_cancel_requested;
EXECUTE stmt_ix_generation_tasks_status_cancel_requested;
DEALLOCATE PREPARE stmt_ix_generation_tasks_status_cancel_requested;

SET @has_generation_tasks_task_kind = (
  SELECT COUNT(*)
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'generation_tasks'
    AND COLUMN_NAME = 'task_kind'
);

SET @add_generation_tasks_task_kind = IF(
  @has_generation_tasks_task_kind = 0,
  "ALTER TABLE generation_tasks ADD COLUMN task_kind VARCHAR(64) NOT NULL DEFAULT 'generic' COMMENT '业务任务类型：用于执行器路由'",
  'SELECT 1'
);
PREPARE stmt_add_generation_tasks_task_kind FROM @add_generation_tasks_task_kind;
EXECUTE stmt_add_generation_tasks_task_kind;
DEALLOCATE PREPARE stmt_add_generation_tasks_task_kind;

SET @has_generation_tasks_executor_type = (
  SELECT COUNT(*)
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'generation_tasks'
    AND COLUMN_NAME = 'executor_type'
);

SET @add_generation_tasks_executor_type = IF(
  @has_generation_tasks_executor_type = 0,
  "ALTER TABLE generation_tasks ADD COLUMN executor_type VARCHAR(32) NULL COMMENT '执行器类型，如 celery'",
  'SELECT 1'
);
PREPARE stmt_add_generation_tasks_executor_type FROM @add_generation_tasks_executor_type;
EXECUTE stmt_add_generation_tasks_executor_type;
DEALLOCATE PREPARE stmt_add_generation_tasks_executor_type;

SET @has_generation_tasks_executor_task_id = (
  SELECT COUNT(*)
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'generation_tasks'
    AND COLUMN_NAME = 'executor_task_id'
);

SET @add_generation_tasks_executor_task_id = IF(
  @has_generation_tasks_executor_task_id = 0,
  "ALTER TABLE generation_tasks ADD COLUMN executor_task_id VARCHAR(128) NULL COMMENT '执行器侧任务 ID，如 celery task id'",
  'SELECT 1'
);
PREPARE stmt_add_generation_tasks_executor_task_id FROM @add_generation_tasks_executor_task_id;
EXECUTE stmt_add_generation_tasks_executor_task_id;
DEALLOCATE PREPARE stmt_add_generation_tasks_executor_task_id;

SET @has_generation_tasks_started_at = (
  SELECT COUNT(*)
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'generation_tasks'
    AND COLUMN_NAME = 'started_at'
);

SET @add_generation_tasks_started_at = IF(
  @has_generation_tasks_started_at = 0,
  "ALTER TABLE generation_tasks ADD COLUMN started_at DATETIME NULL COMMENT '任务开始执行时间'",
  'SELECT 1'
);
PREPARE stmt_add_generation_tasks_started_at FROM @add_generation_tasks_started_at;
EXECUTE stmt_add_generation_tasks_started_at;
DEALLOCATE PREPARE stmt_add_generation_tasks_started_at;

SET @has_generation_tasks_finished_at = (
  SELECT COUNT(*)
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'generation_tasks'
    AND COLUMN_NAME = 'finished_at'
);

SET @add_generation_tasks_finished_at = IF(
  @has_generation_tasks_finished_at = 0,
  "ALTER TABLE generation_tasks ADD COLUMN finished_at DATETIME NULL COMMENT '任务结束时间（成功 / 失败 / 取消）'",
  'SELECT 1'
);
PREPARE stmt_add_generation_tasks_finished_at FROM @add_generation_tasks_finished_at;
EXECUTE stmt_add_generation_tasks_finished_at;
DEALLOCATE PREPARE stmt_add_generation_tasks_finished_at;

SET @has_ix_generation_tasks_task_kind = (
  SELECT COUNT(*)
  FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'generation_tasks'
    AND INDEX_NAME = 'ix_generation_tasks_task_kind'
);

SET @create_ix_generation_tasks_task_kind = IF(
  @has_ix_generation_tasks_task_kind = 0,
  'CREATE INDEX ix_generation_tasks_task_kind ON generation_tasks (task_kind)',
  'SELECT 1'
);
PREPARE stmt_ix_generation_tasks_task_kind FROM @create_ix_generation_tasks_task_kind;
EXECUTE stmt_ix_generation_tasks_task_kind;
DEALLOCATE PREPARE stmt_ix_generation_tasks_task_kind;

SET @has_ix_generation_tasks_status_updated_at = (
  SELECT COUNT(*)
  FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'generation_tasks'
    AND INDEX_NAME = 'ix_generation_tasks_status_updated_at'
);

SET @create_ix_generation_tasks_status_updated_at = IF(
  @has_ix_generation_tasks_status_updated_at = 0,
  'CREATE INDEX ix_generation_tasks_status_updated_at ON generation_tasks (status, updated_at)',
  'SELECT 1'
);
PREPARE stmt_ix_generation_tasks_status_updated_at FROM @create_ix_generation_tasks_status_updated_at;
EXECUTE stmt_ix_generation_tasks_status_updated_at;
DEALLOCATE PREPARE stmt_ix_generation_tasks_status_updated_at;

SET @has_ix_generation_tasks_mode_updated_at = (
  SELECT COUNT(*)
  FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'generation_tasks'
    AND INDEX_NAME = 'ix_generation_tasks_mode_updated_at'
);

SET @create_ix_generation_tasks_mode_updated_at = IF(
  @has_ix_generation_tasks_mode_updated_at = 0,
  'CREATE INDEX ix_generation_tasks_mode_updated_at ON generation_tasks (mode, updated_at)',
  'SELECT 1'
);
PREPARE stmt_ix_generation_tasks_mode_updated_at FROM @create_ix_generation_tasks_mode_updated_at;
EXECUTE stmt_ix_generation_tasks_mode_updated_at;
DEALLOCATE PREPARE stmt_ix_generation_tasks_mode_updated_at;
