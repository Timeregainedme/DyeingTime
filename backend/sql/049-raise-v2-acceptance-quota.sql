-- 049-raise-v2-acceptance-quota.sql
-- P9-C：用户批准将 V2 累计验收测试额度提升一倍；只提升 scope=v2-acceptance 的上限，
-- 不重置 consumed/reserved，不影响生产预算。
-- 回滚：将 limit_amount 恢复到 20/4/500（仅在确认当前验收 scope 无运行任务时执行）。

INSERT INTO generation_quotas (scope, media_type, limit_amount, consumed_amount, reserved_amount)
VALUES
  ('v2-acceptance', 'image', 40, 0, 0),
  ('v2-acceptance', 'video', 8, 0, 0),
  ('v2-acceptance', 'audio', 1000, 0, 0)
ON DUPLICATE KEY UPDATE
  limit_amount = GREATEST(limit_amount, VALUES(limit_amount));
