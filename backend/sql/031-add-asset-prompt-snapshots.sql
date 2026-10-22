-- 031-add-asset-prompt-snapshots.sql
-- 资产图片提示词快照：把“生成提示词”与“生成图片”拆成两个可审核、可重试的阶段。
CREATE TABLE IF NOT EXISTS `asset_prompt_snapshots` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '快照 ID',
  `project_id` VARCHAR(64) NOT NULL COMMENT '项目 ID',
  `asset_type` VARCHAR(32) NOT NULL COMMENT '资产类型：costume/scene/prop/character',
  `asset_id` VARCHAR(64) NOT NULL COMMENT '资产 ID',
  `image_id` INT NULL COMMENT '渲染时使用的图片行 ID',
  `prompt` TEXT NOT NULL COMMENT '审核后的完整提示词',
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_asset_prompt_snapshot_asset` (`asset_type`, `asset_id`),
  KEY `ix_asset_prompt_snapshots_project_id` (`project_id`),
  KEY `ix_asset_prompt_snapshots_asset_type` (`asset_type`),
  KEY `ix_asset_prompt_snapshots_asset_id` (`asset_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='资产图片提示词审核稿';
