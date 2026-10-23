---
title: "视频抽卡审核与显式采纳"
description: "记录 P6 / C14 的视频候选、问题标签、审核备注、历史版本与人工采纳规则。"
weight: 34
---

> 本文属于“当前架构”，描述 P6 / C14 已落地的视频候选审核。

## 1. 候选与采纳分离

- 每次视频任务生成一个版本/候选；
- 候选完成不会自动替换已采纳视频（P6 新任务 `auto_adopt=false`）；
- `shots.generated_video_file_id` 仍表示当前采纳视频；
- 旧版本文件与任务保留，可随时切回。

## 2. 候选列表

`GET /api/v1/studio/shots/{id}/video-versions` 返回每个候选：

- task_id / file_id / file_url
- status / error
- is_current
- model_name
- ratio / seconds / prompt
- reference_count / manifest
- review_status
- issue_tags / note
- created_at

## 3. 审核

`shot_video_reviews`：

- task_id 唯一
- shot_id / file_id
- review_status：unrated / satisfied / unsatisfied
- issue_tags JSON
- note
- reviewed_by / reviewed_at

问题标签（P9-C 扩展，仍保存到既有 `shot_video_reviews.issue_tags`，不新建质量库）：

- 角色声音不匹配
- 说话人归属错误
- 对白与口型不同步
- 人脸不一致
- 人物脸部漂移
- 服装不一致
- 场景/背景不连续
- 场景布局错误
- 场景错误
- 动作不准确
- 动作错误
- 镜头切换异常
- 运镜错误
- 画面闪烁
- 肢体异常
- 肢体畸形
- 其他

标签只描述人工观察结果，不自动判定视频合格；审核完成也不会自动采纳视频。

接口：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/v1/studio/shots/{sid}/video-versions/{tid}/review` | 保存满意/不满意、标签、备注 |
| `POST` | `/api/v1/studio/shots/{sid}/video-versions/{tid}/adopt` | 按任务显式采纳 |
| `POST` | `/api/v1/studio/shots/{sid}/video-versions/adopt` | 兼容旧 file_id 采纳 |

## 4. 历史保护

- 新候选完成不会覆盖当前采纳；
- 任务完成顺序不同也不会改变用户采纳决定；
- 采纳只移动 `shots.generated_video_file_id`，不删除旧文件；
- 可重新采纳旧版本；
- 审核标签与备注不修改视频文件。

## 5. 前端

`ShotPanel` 内嵌 `VideoReviewPanel`：

- 播放候选；
- 并排卡片对比；
- 问题标签与备注；
- 满意/不满意；
- 显式采纳；
- 当前采纳标识；
- 参考图快照摘要。

## 6. 当前边界

- 不做自动质量评分；
- 不在 P6 自动删除不满意候选；
- 修改提示词重抽仍通过上方 P6 生成入口；原样重跑使用当前 manifest/prompt 重新创建任务；
- 固定音色样本与预览 hash 校验属于 P6 正式生成路径，旧任务继续兼容。
