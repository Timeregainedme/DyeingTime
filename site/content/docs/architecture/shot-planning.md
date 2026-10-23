---
title: "AI 分镜规划与镜头资产版本"
description: "记录 P5 / C10 的分镜规划草稿、Mock/真实任务链路、审核、正式 Shot 写入与镜头资产版本选择。"
weight: 30
---

> 本文属于“当前架构”，描述 P5 / C10 已落地的实现。
> 场次结构与 P3 建议导入见 [正式场次（SceneGroup）](/docs/architecture/scene-groups/)。

## 1. 两层结构

```text
正式结构：
Chapter → SceneGroup → Shot → ShotDetail / ShotDialogLine / ShotAssetVersion
                ↑
审核草稿：
ShotPlanDraft → ShotPlanCandidate[]
```

AI 只写 `shot_plan_candidates`；只有用户确认后才创建正式 `Shot`。
`shot.status` 仍只表示信息确认状态；规划状态独立在 `shot_plan_drafts.status`。

## 2. 分镜规划草稿

`shot_plan_drafts`：

- 来源剧本版本、P3 解析运行；
- 目标时长（30–300 秒，通常 50–120）、节奏 `slow/standard/fast`；
- 状态 `draft/generating/review_required/confirmed/failed`；
- 模型、提示词版本/哈希、任务 ID；
- 场次快照、覆盖率/问题、应用审计。

`shot_plan_candidates`：

- 草稿、场次、顺序、稳定 key；
- `payload`：标题、原文摘录/区间、时长、景别/角度/运镜、动作/氛围、视频提示词草稿、角色/场景/道具/服装与版本、对白；
- `issues`：`blocking` / `warning`；
- 审核状态 `pending/edited/accepted/ignored`。

`shot_plan_applied_shots` 保证同一草稿重复确认不重复创建镜头。

## 3. AI 任务链路

复用：

- `AgentBase` + `build_text_llm`；
- `GenerationTask` + Celery + TaskManager；
- P3 的长文本分块工具；
- 项目文本模型与 P3/P4 资产上下文。

新增：

- `SceneShotPlannerAgent`（`episode_shot_plan@v1`）；
- `shot_plan` 任务类型与 worker executor。

输入包括：

- 剧集与剧本版本；
- P3 确认结果/世界观；
- 正式场次；
- 已锁定角色、别名、身份/造型版本；
- 场景/道具/服装资产；
- 目标总时长、节奏、项目时长范围。

输出为结构化 `ShotPlanResult`，不输出业务 ID。服务端负责：

- 场次序号 → `scene_group_id`；
- 角色名称/别名 → Character ID 与版本；
- 场景/道具/服装名称 → 资产 ID 与当前/所选版本；
- 原文摘录 → 全局字符区间；
- 时长/镜头语言校验；
- 未知角色、未锁定角色、未知场次、超范围时长、未识别说话人等阻塞问题。

长文本按 3000 字符块顺序规划并合并，重复摘录去重；有块失败时保留其它块候选，草稿标记 `failed`，确认被阻止。

## 4. 审核与应用

审核页支持：

- 修改标题、时长、原文/描述/动作、场次；
- 修改角色造型版本、场景/道具/服装版本；
- 接受/忽略、复制（拆分）、删除、合并到上一镜；
- 上下调整顺序；
- 接受全部待处理；
- 查看覆盖率、总时长、阻塞项与警告。

应用规则：

1. 草稿必须 `review_required`，除忽略外不能有 pending；
2. 重新校验 payload、场次、角色锁定、资产/版本、时长、说话人；
3. 有阻塞项拒绝应用；
4. 章节已有镜头时默认拒绝；显式 `append_to_existing=true` 时只追加，不更新/删除旧镜头；
5. 正式写入：
   - `Shot`（chapter/scene_group/index/title/script_excerpt）
   - `ShotDetail`（duration/camera/angle/movement/scene/description/action_beats/video_prompt_draft）
   - `ShotCharacterLink`
   - `ShotDialogLine`
   - 场景/道具/服装项目关联
   - `ShotAssetVersion`
6. 重复确认返回已应用镜头，不重复创建；
7. 旧镜头、历史视频、人工修改不被覆盖。

## 5. 镜头资产版本

`shot_asset_versions`：

| 字段 | 说明 |
| --- | --- |
| `shot_id` | 镜头 |
| `asset_type` / `asset_id` | character/scene/prop/costume |
| `asset_version_id` | P4 版本 ID |
| `role` | character_identity / character_appearance / scene / prop / costume |
| `slot` | 角色/道具排序 |
| `source` | plan/manual |

P5 只保存“镜头使用哪个资产版本”；P6 再保存“传给 H3 哪几张参考图”的有序绑定与生成输入快照。

## 6. 顺序与编号

- `scene_groups.index`：剧集内场次顺序；
- `shots.index`：章节内全局镜头顺序，`(chapter_id,index)` 唯一；
- 场次内镜头是按 `shots.index` 过滤后的顺序；
- 跨场次移动/重排使用事务，先写临时负 index，再写最终 index；
- 重新规划不修改已有正式镜头，只追加新镜头。

## 7. API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/v1/studio/chapters/{id}/shot-plans` | 创建规划任务 |
| `GET` | `/api/v1/studio/chapters/{id}/shot-plans` | 规划历史 |
| `GET` | `/api/v1/studio/chapters/{id}/shot-plan-stats` | 统计 |
| `GET` | `/api/v1/studio/shot-plans/{did}` | 草稿详情 |
| `PATCH` | `.../shot-plans/{did}/candidates/{cid}` | 修改/接受/忽略 |
| `POST` | `.../candidates` | 新增 |
| `POST` | `.../candidates/{cid}/duplicate` | 复制（拆分） |
| `DELETE` | `.../candidates/{cid}` | 删除 |
| `POST` | `.../shot-plans/{did}/reorder` | 候选排序 |
| `POST` | `.../shot-plans/{did}/merge` | 合并相邻镜头 |
| `POST` | `.../shot-plans/{did}/confirm` | 应用正式镜头 |
| `GET` | `/api/v1/studio/shots/{sid}/asset-versions` | 镜头资产版本 |

## 8. 当前边界

- 不建立 P6 有序参考图绑定；
- 不生成图片/视频/音频；
- 不自动覆盖已有镜头或历史视频；
- 不猜测未识别说话人；
- 场景资产生成/视频准备度仍由既有链路负责。
