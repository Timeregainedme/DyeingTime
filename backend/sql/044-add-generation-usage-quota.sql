-- 044-add-generation-usage-quota.sql
--
-- P6 / C12：开发验收测试额度（scope=v2-acceptance）与调用预留/结算记录。
-- 这是测试预算，不是生产用户的终身额度；生产环境默认不启用该 scope。
--
-- 回滚：
--   DROP TABLE IF EXISTS generation_usage_reservations;
--   DROP TABLE IF EXISTS generation_quotas;

CREATE TABLE IF NOT EXISTS generation_quotas (
  id              INT          NOT NULL AUTO_INCREMENT,
  scope           VARCHAR(64)  NOT NULL,
  media_type      VARCHAR(16)  NOT NULL,
  limit_amount    INT          NOT NULL DEFAULT 0,
  consumed_amount INT          NOT NULL DEFAULT 0,
  reserved_amount INT          NOT NULL DEFAULT 0,
  created_at      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_generation_quotas_scope_media (scope, media_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='生成测试预算额度（按 scope/media 聚合）';

CREATE TABLE IF NOT EXISTS generation_usage_reservations (
  id          INT          NOT NULL AUTO_INCREMENT,
  scope       VARCHAR(64)  NOT NULL,
  media_type  VARCHAR(16)  NOT NULL,
  amount      INT          NOT NULL,
  status      VARCHAR(16)  NOT NULL DEFAULT 'reserved',
  task_id     VARCHAR(64)  NULL,
  provider    VARCHAR(64)  NOT NULL DEFAULT '',
  model       VARCHAR(255) NOT NULL DEFAULT '',
  note        TEXT         NOT NULL,
  settled_at  DATETIME(6)  NULL,
  created_at  DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at  DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  KEY ix_generation_usage_reservations_scope_media (scope, media_type),
  KEY ix_generation_usage_reservations_task_media (task_id, media_type),
  CONSTRAINT fk_generation_usage_reservations_task
    FOREIGN KEY (task_id) REFERENCES generation_tasks(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='供应商调用额度预留与结算';

INSERT IGNORE INTO generation_quotas (scope, media_type, limit_amount, consumed_amount, reserved_amount)
VALUES
  ('v2-acceptance', 'image', 20, 0, 0),
  ('v2-acceptance', 'video', 4, 0, 0),
  ('v2-acceptance', 'audio', 500, 0, 0);
