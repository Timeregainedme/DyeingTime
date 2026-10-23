---
title: "生成请求幂等与并发边界"
description: "记录 P8 的单镜头/批次 request_key、唯一约束、冲突检测与供应商 exactly-once 边界。"
weight: 37
---

> 本文描述当前已落地的幂等保障；不等于跨供应商 exactly-once。

## 1. 单镜头视频

- `P6VideoGenerateRequest.request_key`（可选，任意客户端生成的稳定 UUID/字符串）。
- `shot_generation_snapshots.request_key` 持久化。
- 唯一约束：`(shot_id, request_key)`。
- 重复提交：
  - 相同 key + 相同 `input_hash` → 返回已有 task/snapshot，不再创建任务、不再预留额度。
  - 相同 key + 不同 `input_hash` → 冲突，要求新 key。
- 并发：两个请求同时通过查询时，唯一约束只允许一个提交；失败方 rollback 后读取赢家。
- 前端：
  - 预览成功生成新 key；
  - 生成成功后再生成新 key；
  - 网络重试保持旧 key；
  - 用户主动重抽使用新 key。

## 2. 视频批次

- `VideoBatchCreate.request_key`（同一剧集内唯一）。
- `video_generation_batches.request_key` + `request_hash`。
- 唯一约束：`(chapter_id, request_key)`。
- `request_hash` 覆盖：shot IDs（排序）、候选数、并发、场次、低覆盖确认。
- 相同 key + 相同 hash → 返回已有 batch。
- 相同 key + 不同 hash → 冲突。
- 批次子任务仍通过 `GenerationTask`、`item.enqueued_at` 和 coordinator 恢复，避免重复入队。

## 3. 供应商边界

- 幂等只覆盖“本系统创建任务”这一层。
- 如果请求已发送供应商但响应丢失，系统不能假设供应商支持 exactly-once。
- 真实调用应先查询供应商任务；无法确认时保留不确定状态，不自动二次提交。
- 额度按保守规则结算；人工恢复入口保留。
- 真实 L3/L4 尚未执行。

## 4. 迁移

`048-add-generation-request-keys.sql`：

- 幂等添加 `shot_generation_snapshots.request_key` 与唯一索引；
- 幂等添加 `video_generation_batches.request_key/request_hash` 与唯一索引；
- 旧行为无需回填；旧任务 request_key 为空。
