-- 040-add-character-identity-lock.sql
--
-- P4 / C7：角色视觉身份锁定、P4 角色圣经字段与资产当前版本指针。
--
-- 兼容性：
-- - 全部使用 information_schema 判重，可重复执行；
-- - 新增 TEXT 列沿用仓库既有迁移口径（ADD COLUMN ... TEXT NOT NULL）；
-- - 存量角色默认未锁定，所有旧接口继续可读。
--
-- 回滚（仅在确认无业务依赖后执行）：
--   ALTER TABLE characters DROP FOREIGN KEY fk_characters_identity_version;
--   ALTER TABLE characters DROP FOREIGN KEY fk_characters_current_appearance_version;
--   ALTER TABLE characters DROP FOREIGN KEY fk_characters_identity_locked_by;
--   ALTER TABLE characters DROP FOREIGN KEY fk_characters_voice_bound_by;
--   ALTER TABLE scenes DROP FOREIGN KEY fk_scenes_current_version;
--   ALTER TABLE props DROP FOREIGN KEY fk_props_current_version;
--   ALTER TABLE costumes DROP FOREIGN KEY fk_costumes_current_version;
--   ALTER TABLE characters DROP COLUMN identity_version_id, DROP COLUMN current_appearance_version_id,
--     DROP COLUMN identity_locked_at, DROP COLUMN identity_locked_by, DROP COLUMN identity_lock_version,
--     DROP COLUMN age_range, DROP COLUMN appearance, DROP COLUMN face_features,
--     DROP COLUMN body_type, DROP COLUMN identity_features, DROP COLUMN voice_bound_at, DROP COLUMN voice_bound_by;
--   ALTER TABLE scenes DROP COLUMN current_version_id;
--   ALTER TABLE props DROP COLUMN current_version_id;
--   ALTER TABLE costumes DROP COLUMN current_version_id;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'characters'
        AND COLUMN_NAME = 'age_range'
    ),
    'SELECT 1',
    'ALTER TABLE characters ADD COLUMN age_range VARCHAR(64) NOT NULL DEFAULT '''' COMMENT ''年龄感/年龄段'' AFTER voice_description'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'characters'
        AND COLUMN_NAME = 'appearance'
    ),
    'SELECT 1',
    'ALTER TABLE characters ADD COLUMN appearance TEXT NOT NULL COMMENT ''基础外貌描述'' AFTER age_range'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'characters'
        AND COLUMN_NAME = 'face_features'
    ),
    'SELECT 1',
    'ALTER TABLE characters ADD COLUMN face_features TEXT NOT NULL COMMENT ''脸型与五官等身份辨识特征'' AFTER appearance'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'characters'
        AND COLUMN_NAME = 'body_type'
    ),
    'SELECT 1',
    'ALTER TABLE characters ADD COLUMN body_type VARCHAR(64) NOT NULL DEFAULT '''' COMMENT ''基础体型'' AFTER face_features'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'characters'
        AND COLUMN_NAME = 'identity_features'
    ),
    'SELECT 1',
    'ALTER TABLE characters ADD COLUMN identity_features TEXT NOT NULL COMMENT ''不可随造型改变的身份特征'' AFTER body_type'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'characters'
        AND COLUMN_NAME = 'identity_version_id'
    ),
    'SELECT 1',
    'ALTER TABLE characters ADD COLUMN identity_version_id VARCHAR(64) NULL COMMENT ''当前视觉身份版本 ID'' AFTER identity_features'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'characters'
        AND COLUMN_NAME = 'current_appearance_version_id'
    ),
    'SELECT 1',
    'ALTER TABLE characters ADD COLUMN current_appearance_version_id VARCHAR(64) NULL COMMENT ''当前造型版本 ID'' AFTER identity_version_id'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'characters'
        AND COLUMN_NAME = 'identity_locked_at'
    ),
    'SELECT 1',
    'ALTER TABLE characters ADD COLUMN identity_locked_at DATETIME(6) NULL COMMENT ''视觉身份锁定时间'' AFTER current_appearance_version_id'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'characters'
        AND COLUMN_NAME = 'identity_locked_by'
    ),
    'SELECT 1',
    'ALTER TABLE characters ADD COLUMN identity_locked_by INT NULL COMMENT ''视觉身份锁定人'' AFTER identity_locked_at'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'characters'
        AND COLUMN_NAME = 'identity_lock_version'
    ),
    'SELECT 1',
    'ALTER TABLE characters ADD COLUMN identity_lock_version INT NOT NULL DEFAULT 0 COMMENT ''身份乐观锁版本'' AFTER identity_locked_by'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'characters'
        AND COLUMN_NAME = 'voice_bound_at'
    ),
    'SELECT 1',
    'ALTER TABLE characters ADD COLUMN voice_bound_at DATETIME(6) NULL COMMENT ''最近绑定音色时间'' AFTER identity_lock_version'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'characters'
        AND COLUMN_NAME = 'voice_bound_by'
    ),
    'SELECT 1',
    'ALTER TABLE characters ADD COLUMN voice_bound_by INT NULL COMMENT ''最近绑定音色操作人'' AFTER voice_bound_at'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'scenes'
        AND COLUMN_NAME = 'current_version_id'
    ),
    'SELECT 1',
    'ALTER TABLE scenes ADD COLUMN current_version_id VARCHAR(64) NULL COMMENT ''当前基础/衍生版本 ID'' AFTER visual_style'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'props'
        AND COLUMN_NAME = 'current_version_id'
    ),
    'SELECT 1',
    'ALTER TABLE props ADD COLUMN current_version_id VARCHAR(64) NULL COMMENT ''当前基础/衍生版本 ID'' AFTER visual_style'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'costumes'
        AND COLUMN_NAME = 'current_version_id'
    ),
    'SELECT 1',
    'ALTER TABLE costumes ADD COLUMN current_version_id VARCHAR(64) NULL COMMENT ''当前基础/衍生版本 ID'' AFTER visual_style'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.STATISTICS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'characters' AND INDEX_NAME = 'ix_characters_identity_version_id'
    ),
    'SELECT 1',
    'ALTER TABLE characters ADD INDEX ix_characters_identity_version_id (identity_version_id)'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.STATISTICS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'characters' AND INDEX_NAME = 'ix_characters_current_appearance_version_id'
    ),
    'SELECT 1',
    'ALTER TABLE characters ADD INDEX ix_characters_current_appearance_version_id (current_appearance_version_id)'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.STATISTICS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'scenes' AND INDEX_NAME = 'ix_scenes_current_version_id'
    ),
    'SELECT 1',
    'ALTER TABLE scenes ADD INDEX ix_scenes_current_version_id (current_version_id)'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.STATISTICS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'props' AND INDEX_NAME = 'ix_props_current_version_id'
    ),
    'SELECT 1',
    'ALTER TABLE props ADD INDEX ix_props_current_version_id (current_version_id)'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.STATISTICS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'costumes' AND INDEX_NAME = 'ix_costumes_current_version_id'
    ),
    'SELECT 1',
    'ALTER TABLE costumes ADD INDEX ix_costumes_current_version_id (current_version_id)'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'characters'
        AND CONSTRAINT_NAME = 'fk_characters_identity_version' AND CONSTRAINT_TYPE = 'FOREIGN KEY'
    ),
    'SELECT 1',
    'ALTER TABLE characters ADD CONSTRAINT fk_characters_identity_version FOREIGN KEY (identity_version_id) REFERENCES asset_versions(id) ON DELETE SET NULL'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'characters'
        AND CONSTRAINT_NAME = 'fk_characters_current_appearance_version' AND CONSTRAINT_TYPE = 'FOREIGN KEY'
    ),
    'SELECT 1',
    'ALTER TABLE characters ADD CONSTRAINT fk_characters_current_appearance_version FOREIGN KEY (current_appearance_version_id) REFERENCES asset_versions(id) ON DELETE SET NULL'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'scenes'
        AND CONSTRAINT_NAME = 'fk_scenes_current_version' AND CONSTRAINT_TYPE = 'FOREIGN KEY'
    ),
    'SELECT 1',
    'ALTER TABLE scenes ADD CONSTRAINT fk_scenes_current_version FOREIGN KEY (current_version_id) REFERENCES asset_versions(id) ON DELETE SET NULL'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'props'
        AND CONSTRAINT_NAME = 'fk_props_current_version' AND CONSTRAINT_TYPE = 'FOREIGN KEY'
    ),
    'SELECT 1',
    'ALTER TABLE props ADD CONSTRAINT fk_props_current_version FOREIGN KEY (current_version_id) REFERENCES asset_versions(id) ON DELETE SET NULL'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'costumes'
        AND CONSTRAINT_NAME = 'fk_costumes_current_version' AND CONSTRAINT_TYPE = 'FOREIGN KEY'
    ),
    'SELECT 1',
    'ALTER TABLE costumes ADD CONSTRAINT fk_costumes_current_version FOREIGN KEY (current_version_id) REFERENCES asset_versions(id) ON DELETE SET NULL'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'characters'
        AND CONSTRAINT_NAME = 'fk_characters_identity_locked_by' AND CONSTRAINT_TYPE = 'FOREIGN KEY'
    ),
    'SELECT 1',
    'ALTER TABLE characters ADD CONSTRAINT fk_characters_identity_locked_by FOREIGN KEY (identity_locked_by) REFERENCES users(id) ON DELETE SET NULL'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'characters'
        AND CONSTRAINT_NAME = 'fk_characters_voice_bound_by' AND CONSTRAINT_TYPE = 'FOREIGN KEY'
    ),
    'SELECT 1',
    'ALTER TABLE characters ADD CONSTRAINT fk_characters_voice_bound_by FOREIGN KEY (voice_bound_by) REFERENCES users(id) ON DELETE SET NULL'
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;
