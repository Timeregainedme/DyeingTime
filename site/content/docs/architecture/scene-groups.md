---
title: "正式场次（SceneGroup）"
description: "记录 P5 / C9 已生效的剧集内剧情场次模型、排序、P3 场次建议导入与树状工作台规则。"
weight: 29
---

> 本文属于“当前架构”，描述 P5 / C9 已落地的正式场次。
> AI 分镜规划与正式镜头写入见 [AI 分镜规划](/docs/architecture/shot-planning/)。

## 1. 概念边界

| 概念 | 表 | 说明 |
| --- | --- | --- |
| 剧情场次 | `scene_groups` | 剧集内一段连续时间/地点/事件，例如「场次 01 · 总裁办公室 · 白天」 |
| 场景资产 | `scenes` | 可被多个场次/剧集复用的空间素材，例如「总裁办公室」 |

一个场次可以有主场景资产，但一个场次也可能涉及多个场景；多个场次可以引用同一个 Scene。
**禁止把两者合并为一个实体。**

镜头同时保留：

- `shots.chapter_id`：始终属于剧集；
- `shots.scene_group_id`：可选，为空表示「未分配场次」。

使用 `scene_group_id` 而非 `scene_id`，避免与既有 Scene 资产语义冲突。

## 2. 数据模型

`scene_groups` 关键字段：

| 字段 | 说明 |
| --- | --- |
| `project_id` / `chapter_id` | 项目与剧集归属 |
| `index` | 剧集内场次顺序；`(chapter_id,index)` 唯一 |
| `title` / `description` | 场次标题与描述 |
| `location` / `time_of_day` | 地点与时间 |
| `story_event` | 场次关键剧情事件 |
| `primary_scene_id` | 主场景资产（可空） |
| `source_parse_run_id` | P3 解析运行来源 |
| `source_beat_key` | P3 scene_beat 稳定键；与解析运行一起唯一 |
| `source_start_char` / `source_end_char` | 原文区间 |

排序：

- 场次顺序由 `index` 表示；
- 镜头顺序仍由 `shots.index` 表示，且 `(chapter_id,index)` 全局唯一；
- 跨场次移动镜头时，服务端在事务内重写章节内 index，不会让不同场次出现重复 index；
- 场次内展示顺序使用全局 index 的升序过滤结果。

## 3. P3 场次建议导入

来源：

- 当前剧集对应 `ScriptDocument(doc_type=episode)`；
- 最近一次 `completed/confirmed` 的 P3 解析运行；
- `confirmed_result.episode.scene_beats`，兼容 `confirmed_result.scene_beats`。

流程：

1. 读取 suggestions，返回可编辑场次草稿；
2. 用户可修改标题、地点、时间，移除建议项；
3. `POST /chapters/{id}/scene-groups/import` 创建正式场次；
4. 每条场次用 `(chapter_id, source_parse_run_id, source_beat_key)` 幂等；
5. 重复导入同一解析结果只跳过，不覆盖已有人工修改；
6. 新剧本版本只提示 `script_version_changed`，不自动覆盖场次。

主场景匹配只按地点/场景名称精确或包含匹配；匹配不到时保留空主场景并返回 warning。

## 4. API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET/POST` | `/api/v1/studio/chapters/{id}/scene-groups` | 列表/创建 |
| `GET/PATCH/DELETE` | `/api/v1/studio/scene-groups/{gid}` | 详情/修改/删除空场次 |
| `POST` | `/api/v1/studio/chapters/{id}/scene-groups/reorder` | 场次排序 |
| `GET` | `/api/v1/studio/scene-groups/{gid}/shots` | 场次镜头 |
| `POST` | `/api/v1/studio/chapters/{id}/shots/reorder` | 跨场次镜头移动/排序 |
| `GET` | `/api/v1/studio/chapters/{id}/scene-group-suggestions` | P3 场次建议 |
| `POST` | `/api/v1/studio/chapters/{id}/scene-groups/import` | 幂等导入 |

删除含镜头场次返回 409，要求先移动/删除镜头；不会级联删除视频或任务。

## 5. 历史数据与工作台

- 存量镜头 `scene_group_id` 为空，继续可读、可编辑；
- 树状工作台显示「未分配场次」，不会把历史镜头自动放进虚构场次；
- 剧集节点 → 场次节点 → 镜头节点，镜头仍懒加载；
- 场次/镜头排序变更后失效相关 Query 缓存；
- 旧版分镜列表、旧版镜头准备台继续可用。

## 6. 当前边界

- 场次树不创建 P6 参考绑定；
- 场次编辑不自动重排或删除镜头；
- 镜头资产版本选择与 AI 分镜规划属于 C10，见 [AI 分镜规划](/docs/architecture/shot-planning/)。
