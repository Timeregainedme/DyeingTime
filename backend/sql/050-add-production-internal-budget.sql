-- 050-add-production-internal-budget.sql
--
-- P10-A：公司内部 Beta 生产预算与并发默认值。
--
-- 说明：
-- - 与 v2-acceptance 隔离；正式环境使用 scope=production-internal。
-- - 初始额度保守，不允许无限制付费生成；管理员可按供应商余额调整。
-- - 视频并发初始为 1，避免 2 vCPU / 3.7GB 主机同时跑多条真实视频任务。
--
-- 回滚：
--   DELETE FROM generation_quotas WHERE scope = 'production-internal';
--   UPDATE projects SET video_concurrency = 4 WHERE video_concurrency = 1;

INSERT INTO generation_quotas (scope, media_type, limit_amount, consumed_amount, reserved_amount)
VALUES
  ('production-internal', 'image', 100, 0, 0),
  ('production-internal', 'video', 20, 0, 0),
  ('production-internal', 'audio', 5000, 0, 0)
ON DUPLICATE KEY UPDATE
  limit_amount = GREATEST(limit_amount, VALUES(limit_amount));

UPDATE projects
SET video_concurrency = 1
WHERE video_concurrency > 1;
