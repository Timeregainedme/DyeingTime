---
title: "生成测试额度与原子预留"
description: "记录 P6 / C12 的 V2 验收测试额度、原子预留、结算与共享执行层拦截。"
weight: 32
---

> 本文属于“当前架构”，描述 P6 / C12 已落地的测试预算控制。
> 它是开发/验收预算，不是生产用户终身额度。

## 1. 范围

V2 累计测试预算：

- 图片 20 张
- 视频 4 次供应商生成请求
- 音频 500 字

默认 scope：`v2-acceptance`。

运行时是否启用由设置控制：

- `generation_test_quota_enabled`（默认 false）
- `generation_test_quota_scope`（默认 `v2-acceptance`）

生产环境应保持关闭，或使用独立的生产预算配置；不得把验收 scope 当作生产用户配额。

## 2. 数据模型

`generation_quotas`：

- scope / media_type
- limit_amount
- consumed_amount
- reserved_amount
- unique(scope, media_type)

`generation_usage_reservations`：

- scope / media_type / amount
- status：reserved / committed / released
- task_id / provider / model
- note / settled_at

迁移：`044-add-generation-usage-quota.sql`；初始化默认 20/4/500。

## 3. 原子预留

`reserve()` 使用单条 SQL 原子更新：

```sql
UPDATE generation_quotas
SET reserved_amount = reserved_amount + amount
WHERE id = ?
  AND consumed_amount + reserved_amount + amount <= limit_amount
```

`rowcount=0` 即额度不足。两个并发请求只有一个能抢到最后一份额度。

## 4. 结算语义

- 成功：`reserved → committed`，consumed 增加，reserved 减少；
- 请求未发送/明确释放：`reserved → released`；
- 已发送但失败、超时、取消：保守按 committed；
- 任务重试/执行层重复调用通过 `(task_id, media_type)` 查已有 reservation，避免重复扣减。

## 5. 执行层覆盖

共享真实供应商执行层：

- `image_task_runner`：按 `input.n` 预留图片额度；
- `video_generation` runner：每任务预留 1 次；
- `audio_task_runner`：按文本字符数预留。

额度检查在 `task.run()` 之前；服务端内部执行，不依赖前端按钮。

Mock/本地测试不经过真实供应商 runner，不消耗额度。

## 6. API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/studio/generation-quota` | 查询 scope 额度 |
| `GET` | `/api/v1/studio/generation-quota/reservations` | 使用记录 |
| `POST` | `/api/v1/studio/generation-quota/reserve` | 显式原子预留 |
| `POST` | `/api/v1/studio/generation-quota/settle` | 结算预留 |

## 7. 当前边界

- 默认关闭，真实调用必须在启用的测试环境中进行；
- 不把本地 Mock 计入预算；
- 未执行真实供应商测试，因此当前剩余额度仍为 20/4/500；
- 生产预算与验收预算继续分离。
