---
title: "项目风格快照与锁定"
description: "记录 P2 已生效的风格目录扩展、参考图分析、项目级风格快照与锁定约束。"
weight: 24
---

> 本文属于“当前架构”文档，描述 P2 / C4 已落地的视觉风格机制。
> 生成配置与模型快照见 [项目生成配置与模型快照](/docs/architecture/project-generation-config/)。

## 数据模型

### 风格目录 `project_styles`

在原有 `id / visual_style / name / description / prompt_pack / sort_order` 基础上新增：

| 字段 | 说明 |
| --- | --- |
| `structured_profile` | 结构化风格字段（JSON） |
| `reference_file_ids` | 风格参考图文件 ID（最多 3 张） |
| `sample_file_ids` | 已确认样张文件 ID（最多 3 张） |
| `analysis_status` | `draft` / `analyzed` |
| `is_builtin` | 是否平台内置模板 |

首批内置模板（稳定 ID）：

- `preset-live-action-realism` — 真人电影写实
- `preset-2d-animation` — 2D 动画
- `preset-3d-chinese-anime` — 3D 国漫

迁移 `035-add-project-style-lock.sql` 只插入这三个模板；原有 7 个风格及其 ID 不变。

### 项目快照 `project_style_snapshots`

每个项目至多一行，主键 `project_id`：

```text
source_style_id / style_name / visual_style / description
structured_profile / prompt_pack
reference_file_ids / sample_file_ids
snapshot_version / locked_at
```

快照保存的是**副本**，不是目录项的引用。因此：

- 修改全局风格的名称、描述或 `prompt_pack` 不会改变已锁定项目；
- 删除全局目录项时 `source_style_id` 置空，快照内容仍然完整；
- 项目 `style` / `visual_style` 字段继续同步，兼容旧页面读取。

## 结构化字段

`StyleStructuredProfile`：

| 字段 | 含义 |
| --- | --- |
| `medium` | 视觉媒介 |
| `texture` | 画面质感 |
| `color` | 色彩与饱和度 |
| `lighting` | 光照方式 |
| `material` | 材质特征 |
| `character_rendering` | 人物渲染特征 |
| `scene_rendering` | 场景渲染特征 |
| `camera` | 摄影与运镜风格 |
| `keep` | 应当保持的视觉特征 |
| `avoid` | 禁止出现的风格特征 |

`prompt_pack` 为空时由结构化字段自动拼接；锁定快照始终保存**最终生效**的 `prompt_pack`。

## 参考图分析

```text
上传 1–3 张参考图（POST /studio/files/upload）
→ POST /studio/styles/analyze（不落库）
→ 人工修订结构化字段
→ POST/PATCH /studio/styles（保存草稿）
→ PUT /studio/projects/{id}/style（选择）
→ POST /studio/projects/{id}/style/lock（锁定）
```

约束：

- 分析复用现有文本供应商基础设施（`build_text_llm`），不新建模型调用框架；
- 没有可用模型时返回明确原因，前端仍允许手动填写并保存草稿；
- 分析结果永远不自动覆盖已保存草稿；
- 本阶段不调用图片生成模型来制作测试样张，样张由人工上传；
- 风格参考图**不会**自动进入 H3 镜头参考图列表。

## 锁定约束

服务端保证：

- 已存在快照时，`PUT /studio/projects/{id}/style` 返回 409；
- 已存在快照时，`POST /studio/projects/{id}/style/lock` 返回 409；
- 前端禁用按钮只是提示，不构成约束。

锁定后：

- 当前项目不能直接切换视觉风格；
- 已生成资产与历史视频不受影响；
- 后续角色 / 场景 / 道具 / 服装与分镜帧提示词优先读取项目快照的 `prompt_pack`
  （`resolve_style_motif` 的 `project_id` 分支）；
- 需要采用其他风格时应复制为新项目（后续阶段提供）。

## API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/studio/styles` | 风格目录（含结构化字段与参考图） |
| `GET` | `/api/v1/studio/styles/analysis-capability` | 视觉分析可用性 |
| `POST` | `/api/v1/studio/styles/analyze` | 分析 1–3 张参考图，不落库 |
| `POST` | `/api/v1/studio/styles` | 新建自定义风格草稿 |
| `PATCH` | `/api/v1/studio/styles/{id}` | 修改风格/草稿 |
| `GET` | `/api/v1/studio/projects/{id}/style` | 项目风格状态（选择或锁定快照） |
| `PUT` | `/api/v1/studio/projects/{id}/style` | 选择风格（未锁定） |
| `POST` | `/api/v1/studio/projects/{id}/style/lock` | 锁定并生成快照 |

## 当前边界

- 不做跨风格转换或项目复制（后续阶段）；
- 不自动生成风格测试样张；
- 不把风格参考图加入镜头多参考列表（P6 负责参考绑定）；
- 全局目录的编辑入口仍在 `/styles`，工作台负责项目级选择与锁定。
