---
title: "章节制作四阶段"
description: "说明分镜、资产、提示词、出图四个独立阶段，以及多参考图模式下的分镜帧取舍。"
weight: 13
---

> 本文属于“当前架构”文档，描述当前已经生效的章节制作流程。

## 为什么拆成四个阶段

此前的“一键提取资产”是一条长链：

```text
切分镜 → 提取资产候选 → 建资产 →（可选）出图
```

任何一步失败都会中止后续，且用户在长链中只能等待。现在改为四个独立按钮：

| 阶段 | 入口 | 产物 | 不做什么 |
| --- | --- | --- | --- |
| 提取分镜 | `divide-async` | `shots` | 不提取资产、不写提示词 |
| 提取资产 | `extract-async` + `batch-create-assets` | 候选、资产、镜头关联 | 不写提示词、不出图 |
| 生成提示词 | 资产批量渲染 + 分镜帧提示词任务 | `asset_prompt_snapshots`、`shot_details.*_frame_prompt` | 不调用图片模型 |
| 生成图片 | 批量图片任务 | 资产图、分镜帧图 | 不改提示词 |

每个阶段有独立状态、独立重试，不自动串联。上游未完成时下游按钮禁用并提示原因。

## 多参考图模式不需要分镜帧

`REQUIRED_FRAMES_BY_MODE["reference"] = ()`。多参考图视频只使用资产参考图：

- 角色卡；
- 场景图；
- 道具图；
- 服装图。

分镜帧只在 `first / last / key / first_last` 模式下是硬前置。多参模式下：

- “生成提示词”默认只渲染资产图提示词；
- 分镜帧提示词是可选动作；
- “生成图片”默认只生成资产图，分镜帧图默认不勾选。

## 分镜快速切分与兜底

`ScriptDivisionResult` 只强依赖：

```text
index
script_excerpt
shot_name
```

`start_line / end_line / time_of_day` 是可选历史字段，不再参与强校验。分镜 Agent 的系统提示词也只要求这三个字段。

分镜任务执行顺序：

1. 按时间轴标记或行数把章节切成块（约 1800 字 / 120 行一块）；
2. 每块并行调用主模型，单次 90 秒超时；
3. 单块失败立即切备用文本模型（`model_settings.fallback_text_model_id`，默认 `minimax-m3`）；
4. 全部块成功后合并、去边界重复、重排 `index`，一次性写库；
5. 仍有块失败则任务失败，不写半成品；错误信息包含失败块编号。

## 资产提示词审核稿

`asset_prompt_snapshots` 保存资产图提示词的当前审核稿：

| 列 | 说明 |
| --- | --- |
| `project_id` | 项目 ID |
| `asset_type` | costume / scene / prop / character |
| `asset_id` | 资产 ID |
| `image_id` | 渲染时使用的图片行 ID |
| `prompt` | 审核后的完整提示词 |

流程：

```text
POST /studio/image-tasks/assets/{asset_type}/batch-render-prompts
→ 模板渲染 → 写入审核稿（不扣图费）
→ 用户编辑 → PATCH 审核稿
→ POST /studio/image-tasks/assets/batch-image-tasks
（use_prompt_snapshots=true，优先使用审核稿）
```

资产顺序固定：

```text
服装 → 场景 → 道具 → 角色
```

角色图会引用演员图与服装图；角色缺演员绑定时，状态接口返回 `character_actor_missing`，前端显示 warning，但不阻断其他资产。

## 重新关联

`POST /studio/shots/extracted-candidates/batch-create-assets` 支持：

```json
{"chapter_id": "...", "link_only": true}
```

`link_only=true` 时不创建新资产，只按名称查找已有资产并建立镜头关联；找不到的候选进入 `skipped`，原因 `asset_not_found`。用于修改资产名称/候选后重新绑定。

## 状态接口

`GET /api/v1/studio/chapters/{chapter_id}/production-status` 返回：

- 分镜数；
- 候选 pending/linked/ignored；
- 四类资产数；
- 角色缺演员列表；
- 资产提示词审核稿数；
- 分镜帧提示词数；
- 分镜帧图片数。

四个按钮和状态标签都读这一份数据，避免前端各自计算不一致。
