SET @has_shot_details_action_beats = (
  SELECT COUNT(*)
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'shot_details'
    AND COLUMN_NAME = 'action_beats'
);

SET @add_shot_details_action_beats = IF(
  @has_shot_details_action_beats = 0,
  "ALTER TABLE shot_details ADD COLUMN action_beats JSON NULL COMMENT '镜头动作拍点（按时间顺序排列，用于关键帧与视频生成）'",
  'SELECT 1'
);
PREPARE stmt_add_shot_details_action_beats FROM @add_shot_details_action_beats;
EXECUTE stmt_add_shot_details_action_beats;
DEALLOCATE PREPARE stmt_add_shot_details_action_beats;

SET @backfill_shot_details_action_beats = IF(
  @has_shot_details_action_beats = 0,
  "UPDATE shot_details SET action_beats = JSON_ARRAY() WHERE action_beats IS NULL",
  'SELECT 1'
);
PREPARE stmt_backfill_shot_details_action_beats FROM @backfill_shot_details_action_beats;
EXECUTE stmt_backfill_shot_details_action_beats;
DEALLOCATE PREPARE stmt_backfill_shot_details_action_beats;

SET @normalize_shot_details_action_beats = (
  SELECT COUNT(*)
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'shot_details'
    AND COLUMN_NAME = 'action_beats'
    AND IS_NULLABLE = 'YES'
);

SET @alter_shot_details_action_beats = IF(
  @normalize_shot_details_action_beats > 0,
  "ALTER TABLE shot_details MODIFY COLUMN action_beats JSON NOT NULL COMMENT '镜头动作拍点（按时间顺序排列，用于关键帧与视频生成）'",
  'SELECT 1'
);
PREPARE stmt_alter_shot_details_action_beats FROM @alter_shot_details_action_beats;
EXECUTE stmt_alter_shot_details_action_beats;
DEALLOCATE PREPARE stmt_alter_shot_details_action_beats;
