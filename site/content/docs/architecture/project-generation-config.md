---
title: "项目生成配置与模型快照"
description: "记录 P2 已生效的两层模型配置、项目快照、确认流程与 4–15 秒业务时长约束。"
weight: 23
---

> 本文属于“当前架构”文档，描述 P2 / C3 已落地的项目生成配置。
> 风格锁定见 [项目风格快照与锁定](/docs/architecture/project-style-lock/)。

## 两层配置

```text
全局层（ModelSettings / Provider / Model）
  供应商凭据、Base URL、模型目录、全局默认模型
        ↓ 仅作为兜底
项目层（projects.default_*_model_id + 生成参数）
  本项目确认使用的图片 / 视频 / 音频模型与输出规格
```

解析顺序：

1. 项目显式配置的模型 ID；
2. 项目未配置时，回退 `ModelSettings.default_{image,video,audio}_model_id`；
3. 两边都为空 → 配置检查失败，生成准备度返回未就绪。

项目显式配置指向不存在的模型或类别不匹配时**不回退**，直接返回 503。
这样不会出现「预览一个模型、实际跑另一个」的静默切换。

## 项目字段

| 字段 | 说明 |
| --- | --- |
| `default_image_model_id` | 项目图片模型；为空回退全局 |
| `default_video_model_id` | 项目视频模型；为空回退全局 |
| `default_audio_model_id` | 项目音频模型；为空回退全局 |
| `default_reference_mode` | 默认参考模式；P2 固定 `reference` |
| `default_shot_duration` | 默认镜头时长（秒） |
| `video_duration_min` / `video_duration_max` | 项目业务时长范围；默认 4–15 |
| `video_concurrency` | 批量并发数；默认 4 |
| `use_dialog_audio_as_reference` | 音频参考开关；新项目默认关闭 |
| `generation_config_version` | 配置版本；再次确认时递增 |
| `generation_config_confirmed_at` | 确认时间；为空表示未确认 |
| `generation_config_updated_at` | 最近保存时间 |
| `generation_config_snapshot` | 确认时的只读快照（JSON） |

快照只保存模型 ID、名称、供应商 ID / 名称、能力参数与输出策略，
**不保存 API Key、Base URL 或任何凭据**。

## 业务时长与供应商能力

- 供应商能力：优云智算 H3 适配器声明 4–30 秒；
- 内部业务约束：P2 固定 4–15 秒；
- 保存时校验 `4 <= min <= default <= max <= 15`；
- 配置面板显示两者交集，例如 H3 下为 4–15 秒；
- P6 的生成准备度与提交逻辑继续执行同一交集，不在页面里散落硬编码。

## API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/studio/projects/{id}/generation-options` | 模型清单、能力、全局默认与业务约束 |
| `GET` | `/api/v1/studio/projects/{id}/generation-config` | 当前生效值、检查项与快照 |
| `PUT` | `/api/v1/studio/projects/{id}/generation-config` | 保存草稿或保存并确认 |

`PUT` 的 `confirm=false` 只保存草稿；`confirm=true` 会在服务端重新跑完整检查，
失败返回 400 且不写入任何字段。

## 生成链路接入

- 视频：`build_run_args` 通过镜头反查项目，优先取项目视频模型；
- 图片：显式 `model_id` → 项目模型 → 全局默认；角色图与分镜帧可从关联实体唯一反查项目，
  全局资产（演员/场景/道具/服装）可能跨项目复用，继续回退全局默认；
- 音频：显式 `model_id` → 项目模型 → 全局默认；可从 `project_id` / 镜头反查项目；
- 视频准备度与项目开工预检同样优先读项目配置。

## 默认值修正

`use_dialog_audio_as_reference` 的 ORM、Pydantic 与数据库新行默认值统一为 `False`。
迁移只执行 `ALTER COLUMN ... SET DEFAULT 0`，**不回填存量项目**，已有项目保持自己的设置。

## 当前边界

- 项目配置面板不负责编辑全局供应商与 API Key；这些仍在模型管理页；
- 不自动创建未经核实的供应商/模型；
- 并发数只是项目配置，P2 不实现真实批量队列（P6）；
- 配置面板的检查项与 `shot.status`、任务状态、视频准备度是四套独立语义。
