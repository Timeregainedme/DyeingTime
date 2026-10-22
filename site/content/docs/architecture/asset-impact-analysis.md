---
title: "资产变更影响分析"
description: "记录 P4 / C8 已生效的资产引用查询、确定/可能影响区分、版本切换影响快照与非破坏性提示。"
weight: 28
---

> 本文属于“当前架构”，描述 P4 / C8 已落地的实现。
> 资产版本与锁定规则见 [角色圣经与资产版本](/docs/architecture/character-bible-asset-versions/)。

## 1. 目标

当用户准备切换角色身份版本或修改场景/道具/服装版本时，系统回答：

- 哪些剧集、镜头使用了该资产；
- 哪些是数据库显式引用，哪些只是可能影响；
- 哪些镜头已有历史视频；
- 切换版本不会删除或自动重拍什么。

## 2. 精度模型

### 确定引用 `explicit`

| 资产 | 显式来源 |
| --- | --- |
| Character | `shot_character_links` |
| Scene | `project_scene_links.shot_id` |
| Prop | `project_prop_links.shot_id` |
| Costume | `project_costume_links.shot_id` |

这些是数据库外键/关联表，直接证明镜头使用了该资产。

### 可能影响 `possible`

- 资产只关联到章节（`project_*_links.chapter_id` 非空、`shot_id` 为空）时，该章节下镜头标为 possible；
- 资产只关联到项目（`chapter_id/shot_id` 均为空）时，项目下镜头标为 possible；
- 章节原文出现资产名称/角色别名时，该章节镜头标为 possible，`reference_kind=script_text_mention`；
- 多个来源命中同一镜头时，`explicit` 优先，`reference_kind` 保留补充说明。

### 版本精度

P4 没有镜头级版本引用，因此：

- `version_precision=asset_level`；
- `version_reference_established=false`；
- 版本切换的影响提示不能声称“镜头确定引用了旧/新版本”。

只有 P6 建立有序参考绑定与生成输入快照后，才能升级为精确版本依赖图。

## 3. 版本切换影响快照

迁移 `041-add-asset-impact-refs.sql` 新增 `asset_version_impact_refs`：

| 字段 | 说明 |
| --- | --- |
| `asset_type` / `asset_id` | 资产 |
| `from_version_id` / `to_version_id` | 切换前后版本 |
| `shot_id` / `chapter_id` | 当时关联镜头 |
| `certainty` | `explicit` / `possible` |
| `reference_kind` | 引用来源 |
| `had_video` | 当时是否已有视频 |
| `created_by` | 操作人 |

切换版本成功后记录快照；同一 `(from_version, to_version, shot)` 幂等。
记录只用于审计与后续提示，不改变镜头、分镜帧、资产图片或视频。

## 4. API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/studio/projects/{pid}/assets/{type}/{aid}/impact` | 当前引用与影响 |
| `GET` | `/api/v1/studio/projects/{pid}/assets/{type}/{aid}/impact-history` | 版本切换影响快照 |

`impact` 可选 `from_version_id` / `to_version_id`，仅作为报告元数据，不会伪造版本引用。

响应包含：

- `chapters[]`：章节、镜头数、确定/可能数、视频数；
- `shots[]`：镜头、确定/可能、引用来源、`has_video`、`video_file_id`；
- `summary`：总数与精度标记；
- `notes`：边界说明。

## 5. 前端

`front/src/features/workbench/panels/AssetImpactPanel.tsx` 嵌入资产详情底部：

- 显示章节/镜头/确定引用/可能影响/已有视频数量；
- 列出镜头及来源；
- 明确提示：已有视频不会删除、覆盖或自动重新生成；
- 切换版本后自动刷新影响分析（通过查询失效/刷新）。

## 6. 非破坏性保证

影响分析只读；版本切换只移动指针并写影响快照：

- 不删除历史版本；
- 不删除候选图与图片文件；
- 不删除/覆盖已有视频；
- 不自动重新生成镜头；
- 不把所有镜头自动切到最新版本。

## 7. 当前边界

- P4 不建立镜头级版本引用；
- `possible` 不是“确定失效”；
- 文本匹配只作提示，不写入正式关联；
- P6 才能精确追踪 H3 实际使用的参考图片/版本。
