---
title: "剧本结构化解析与统一审核"
description: "记录 P3 已生效的 AI 解析任务、候选审核、确认落库、原文证据与增量差异机制。"
weight: 26
---

> 本文属于“当前架构”，描述 P3 / C6 已落地的实现。
> 文档上传、版本与原文提取见 [剧本文档与版本](/docs/architecture/script-documents/)。

## 1. 链路

```text
世界观 active 版本 ─┐
本集剧本版本 ───────┼─> EpisodeScriptParserAgent ─> ScriptParseCandidate
已有角色/场景/资产 ─┘                                  │
                                                     ├─ 人工编辑/接受/忽略/合并/关联
                                                     └─ 确认 ─> 正式 Character/Scene/Prop/Costume
                                                               + chapters.raw_text
                                                               + confirmed_result（场次建议/对白快照）
```

原则：

- AI 输出只写候选，不直接写正式资产。
- 上传、解析、差异分析都不覆盖 `chapters.raw_text`、分镜、资产图或历史视频。
- 只有「启用版本」或「确认解析结果」才同步章节正文。

## 2. 数据模型

### `script_parse_runs`

一次「开始解析本集」对应一行：

| 字段 | 说明 |
| --- | --- |
| `document_id` / `version_id` | 输入剧本文档与版本 |
| `worldbuilding_version_id` | 本次使用的世界观 active 版本 |
| `task_id` | `GenerationTask` 异步任务 |
| `status` | `pending` / `running` / `completed` / `failed` / `confirmed` |
| `model_id` / `model_name` / `provider_name` | 实际使用的文本模型快照 |
| `prompt_version` / `prompt_hash` | 当前为 `episode_script_parse@v1` + 系统提示词 SHA-256 |
| `input_hash` | 剧本哈希 + 世界观哈希 + 模型 + 提示词版本，用于幂等 |
| `chunk_count` / `failed_chunks` | 分块数与失败块 |
| `error` | 可读错误；失败块会保留成功块的候选 |
| `confirmed_at` / `confirmed_by` / `applied_summary` | 确认审计 |
| `confirmed_result` | 确认后的场次建议、对白等 P5 前快照 |

### `script_parse_candidates`

候选按 `(run_id, candidate_type, candidate_key)` 唯一：

- `candidate_type`：`character` / `scene` / `prop` / `costume_change` / `scene_beat` / `dialogue` / `episode` / `issue`
- `payload`：该类型的 Pydantic 结构（JSON）
- `evidence`：原文证据数组
- `review_status`：`pending` / `edited` / `accepted` / `ignored` / `merged`
- `matched_entity_id`：人工或服务端匹配到的已有资产
- `merged_into_id`：合并目标候选
- `issue`：需人工注意的问题

候选行本身就是审核草稿：刷新页面后从数据库恢复，不依赖浏览器本地状态。

### `script_diff_reports`

| 字段 | 说明 |
| --- | --- |
| `document_id` / `old_version_id` / `new_version_id` | 比较对象 |
| `status` | `draft` / `accepted` / `ignored` |
| `text_diff` | 可解释的行级差异 |
| `structured_diff` | 角色/场景/道具/服装变化与待重新解析标记 |
| `impact` | 可能受影响的章节、镜头、资产 |
| `decisions` / `decided_by` / `decided_at` | 人工决策 |

## 3. AI 解析

### 组件

- Agent：`EpisodeScriptParserAgent`，复用 `AgentBase` 与 `build_text_llm`。
- Schema：`app/schemas/skills/script_parse.py` 中的 `ScriptParseResult`。
- Prompt：代码内置 system prompt；当前未在提示词模板表发布，`prompt_version` 与 `prompt_hash` 记录在 run 上。
- 模型：默认全局 `text` 类模型；请求可显式传 `model_id`。

### 输入

1. 项目世界观 active 版本全文；
2. 本集剧本版本全文（分块后逐块输入）；
3. 项目已有角色名称/描述；
4. 项目关联场景、道具、服装名称/描述；
5. 前序块已识别角色/场景名，保证跨块一致。

### 提取内容

- 角色：名称、别名、剧情身份、年龄感、外貌、发型、体型、基础服装、原文有依据的音色描述、证据、问题；
- 场景资产：名称、地点类型、室内外、空间特征、时间光照、陈设、证据；
- 道具：名称、外观、颜色材质、剧情用途、持有角色、位置、证据；
- 服装变化：角色、基础服装、变化后造型、剧情位置、原因、场次建议、证据；
- 场次建议：地点、时间、出场角色、事件、原文区间；
- 对白：文本、说话人、顺序、情绪、类型（对白/旁白/画外音/电话）、证据；
- 待处理问题：无法确认的说话人、信息不足、同名风险等。

硬约束：

- 不生成任何业务 ID；
- 场景资产与剧情场次分开；
- 换装/换发型写入 `costume_change`，不新建角色；
- 对白说话人无法确认时 `speaker_unresolved=true`，不随机分配；
- 不虚构音色 ID；
- 场次建议只是候选，P5 前不创建 `scene_groups`。

### 长文本

`script_parse_chunking.py`：

- 按行顺序切块，默认每块 ≤ 6000 字符；
- 相邻块保留 4 行上下文重叠；
- 单行超长时按字符窗口切分；
- 每块记录 `start_char` / `end_char`，对应完整原文；
- 跨块按精确名称/别名保守合并，不做模糊自动合并；
- 任一块失败时保留成功块候选，run 标记 `failed`，`failed_chunks` 与错误信息可读；重试会创建新 run。

### 失败恢复

- 结构化输出不符合 Schema：该块记失败，不写正式数据；
- 全部失败：run `failed`，候选为空；
- 部分失败：run `failed` 但保留成功块候选，用户可重试或人工补全；
- 重复点击解析：活动任务复用；同输入已完成 run 默认复用，`force=true` 才创建新 run；
- 原始文件、版本与 run 记录始终保留。

## 4. 统一审核

前端同一页：

- 左侧：原文预览；点击候选证据可在原文中高亮定位；
- 右侧：按类型切换的候选列表。

支持：

- 修改字段并保存（`review_status=edited`）；
- 新增候选（manual key，默认 `edited`）；
- 删除候选（仅未确认 run；与“忽略”不同，会移除候选行）；
- 接受 / 忽略；
- 合并同类型重复候选（source 标记 `merged`，名称/别名/证据并入 target）；
- 从项目已有角色、场景、道具、服装中重新关联或取消关联；
- 查看原文证据；
- 批量接受待处理候选；
- 「确认解析结果」。

确认前检查：

- run 必须 `completed`；
- 除 `issue` 外不允许存在 `pending` 候选；
- 已确认 run 再次确认直接返回原结果，不重复创建资产。

## 5. 确认落库

`confirm_parse_run` 在调用方数据库事务内执行：

1. 先处理场景、道具、服装变化；
2. 再处理角色（基础服装需要先存在）；
3. 角色/场景/道具/服装按以下顺序匹配：
   - `matched_entity_id` 指向的实体（若存在且工作区/项目合法）；
   - 同项目精确名称；
   - 都不存在才创建。
4. 已有实体只关联，不覆盖描述、服装、音色等人工数据；同一 run 被任务重试时，已编辑/已接受/已忽略/已合并候选不会被重新持久化覆盖；
5. 场次建议、对白、本集摘要写入 `confirmed_result`；
6. 章节摘要为空时才写入解析摘要；
7. 当前版本标记 `active`，旧 active 标记 `superseded`；
8. `chapters.raw_text` 同步为新版本原文，`condensed_text` 清空；
9. 候选状态、确认人、确认时间、创建/关联统计写入 run。

事务失败时整单回滚，不出现「一半角色成功、一半场景失败」。

P3 不创建：

- `scene_groups`（P5）；
- 镜头拆分（P5）；
- 资产图版本/身份版本（P4）；
- 音色绑定（P4）。

## 6. 增量差异

### 算法

1. `difflib.SequenceMatcher` 对旧/新原文按行比较，输出新增、删除、替换行；
2. 比较两个版本各自最近一次成功解析 run 的候选名称集合（若新版本尚未解析，`requires_reparse=true`）；
3. 在变化文本中匹配项目已有角色/场景/道具/服装名称；
4. 检测服装/造型关键词，输出 `possible` 级造型影响提示；
5. 计算可能受影响的章节与镜头；镜头标记 `has_video`，但绝不删除历史视频。

影响范围当前全部标记为 `possible`，不声称“确定失效”。

### 世界观变化

- 差异报告覆盖项目全部章节与镜头；
- 只提示可能受影响范围，不做全项目自动重解析；
- 用户仍需逐集重新解析/审核。

### 人工决策

`accepted` / `ignored` 只记录报告状态与决策：

- 不自动覆盖章节正文；
- 不自动删除分镜、资产或视频；
- 不自动重新创建实体；
- 后续是否重新解析由用户显式发起。

## 7. API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/v1/studio/script-document-versions/{vid}/parse` | 创建/复用解析任务 |
| `GET` | `/api/v1/studio/script-parse-runs/{rid}` | run 状态、候选、确认结果 |
| `GET` | `/api/v1/studio/script-documents/{did}/parse-runs` | 解析历史 |
| `POST` | `/api/v1/studio/script-parse-runs/{rid}/candidates` | 人工新增候选 |
| `PATCH` | `/api/v1/studio/script-parse-runs/{rid}/candidates/{cid}` | 编辑/接受/忽略/关联 |
| `DELETE` | `/api/v1/studio/script-parse-runs/{rid}/candidates/{cid}` | 删除候选 |
| `POST` | `/api/v1/studio/script-parse-runs/{rid}/merge` | 合并候选 |
| `POST` | `/api/v1/studio/script-parse-runs/{rid}/confirm` | 确认落库 |
| `POST` | `/api/v1/studio/script-documents/{did}/diff` | 生成/复用差异报告 |
| `GET` | `/api/v1/studio/script-diff-reports/{id}` | 差异详情 |
| `POST` | `/api/v1/studio/script-diff-reports/{id}/status` | 接受/忽略决策 |

所有读写按 `Project.workspace_id` 校验工作区；解析/审核/确认需要 editor 权限，查看需要 viewer 权限。

## 8. 当前边界与已知限制

- 解析提示词暂未接入提示词模板发布页；版本通过 `prompt_version` + hash 固化；
- 跨块合并只做精确名称/别名合并，不做模糊匹配；同名风险保留给人工；
- 差异第一版是行级文本 + 名称/候选对比，不做语义向量 Diff；
- `scene_beat`、`dialogue` 在 P5 前只保存在 `confirmed_result`，不创建正式场次/镜头对白；
- 差异报告目前由前端在候选版本出现时手动生成；刷新后可从同一对版本重新生成（后端按版本对唯一）；
- 大文件上限 10MB；文档图片内容不纳入原文，只给出 warning。
