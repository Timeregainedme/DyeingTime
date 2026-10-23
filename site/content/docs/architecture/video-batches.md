---
title: "视频批量生成与并发协调"
description: "记录 P6 / C13 的视频批次、子任务、默认并发、取消、重试与恢复规则。"
weight: 33
---

> 本文属于“当前架构”，描述 P6 / C13 已落地的批量视频任务。

## 1. 数据模型

`video_generation_batches`：

- 项目/剧集/场次
- 状态 queued/running/succeeded/failed/cancelled/partial_success
- 每镜候选数、并发数
- 总/排队/运行/成功/失败/取消计数
- 分镜覆盖快照
- coordinator task id

`video_generation_batch_items`：

- batch、shot、candidate_index
- child `GenerationTask`
- 子状态、enqueue/completed 时间、错误

迁移：`045-add-video-batches.sql`。

## 2. 创建

- 校验镜头全部属于当前剧集/场次；
- 读取 P5 分镜覆盖率；低于 60% 默认拒绝，可显式 `allow_low_coverage=true`；
- 并发取项目 `video_concurrency`，并夹在 1–8；
- 每个镜头每候选先构建 P6 同一份 generation preview/snapshot；
- 子任务先 stage，不立即全部入队；
- 创建 `video_batch` coordinator 任务。

## 3. 并发协调

`run_video_batch_task`：

1. 读取 batch，标记 running；
2. 只启动 queued 子任务，直到 running 数达到并发；
3. 已 enqueue 的子任务不重复 enqueue；
4. 周期刷新子任务 GenerationTask 状态；
5. 全部终态后汇总：
   - 全成功 → succeeded；
   - 部分成功 → partial_success；
   - 全失败 → failed；
   - 取消 → cancelled。
6. 子任务结果不写回 `shot.status`；视频候选由 C14 审核采纳。

## 4. 取消与重试

- 取消 batch：queued 子任务直接 cancelled；running 子任务请求取消，但不宣称供应商远端已停止计费；
- 失败重试：为失败 item 创建新的 `GenerationTask`，复用原任务输入；不重复使用已失败 task；
- resume：重新唤起已存在的 coordinator task，适用于 API/Worker 重启后的恢复；
- 子任务 task id 持久化，页面刷新可恢复进度。

## 5. 覆盖与保护

- 批次显示 P5 覆盖率、阻塞/警告；
- 低覆盖不等于全部镜头不能生成，但必须显式确认；
- 批量结果默认不自动采纳（C11 `auto_adopt=false`）；
- 不删除已有视频与历史任务。

## 6. API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/v1/studio/chapters/{id}/video-batches` | 创建批次 |
| `GET` | `/api/v1/studio/chapters/{id}/video-batches` | 批次列表 |
| `GET` | `/api/v1/studio/video-batches/{id}` | 批次详情 |
| `POST` | `.../video-batches/{id}/cancel` | 取消 |
| `POST` | `.../video-batches/{id}/retry` | 重试失败 |
| `POST` | `.../video-batches/{id}/resume` | 恢复协调器 |

## 7. 当前边界

- 真实供应商并发能力未做在线探测，当前只使用项目配置与 1–8 安全上限；
- 取消请求不保证供应商停止计费；
- 不做原型级视频队列；沿用现有 Celery/GenerationTask 底层。
