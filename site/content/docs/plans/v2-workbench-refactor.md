---
title: "V2 树状工作台重构计划"
description: "把 DyeingTime 从「章节+分镜两段式」重构为「项目→剧集→场次→镜头」树状工作台的分阶段实施计划、依赖关系与风险清单。P0 审计、P1 骨架与 P2 项目配置/风格锁定已完成。"
weight: 2
---

> 本文是**仍在推进中的计划**，不是已生效架构。
> 当前真实生效的工作台实现见 [树状工作台](/docs/architecture/workbench/)，
> [视频提示词链路与参考图](/docs/architecture/video-prompt-pipeline/)、
> [视频抽卡与版本切换](/docs/architecture/video-version-redraw/)、
> [分镜状态流转说明](/docs/architecture/shot-status-flow/)。
>
> 阶段边界与验收口径来自产品侧重构需求（单人主导的内部 AI 短剧生产系统）。
> 落地过程中若与既有架构文档冲突，以本文的阶段结论为准，并同步回写对应架构文档。

## 目标形态

```text
项目
├── 项目配置（模型快照 / 风格锁定 / 比例 / 分辨率 / 并发 / 音频参考开关）
├── 世界观与剧本（项目级设定文件 + 每集独立剧本文件）
├── 风格圣经（风格目录 + 锁定快照）
├── 全局资产（角色 / 场景资产 / 道具 / 服装）
├── 第 1 集
│   ├── 场次 1（剧集内剧情分组）
│   │   ├── 镜头 1
│   │   └── 镜头 2
│   └── 场次 2
├── 第 2 集
└── 导出
```

**不做无限画布。** 默认交互是树状层级管理，不是节点图。

## 硬约束（贯穿所有阶段）

1. 保留三种状态语义，不得合并：
   - `shot.status`：信息提取确认状态（`pending` / `ready`）。
   - video-readiness：是否具备视频生成条件。
   - task status：任务运行状态（`GenerationTask.status`）。
2. 数据库变更只做可审查、可回滚的迁移，**不删除旧业务数据**。
3. API 变更后必须执行 `pnpm run openapi:update` 同步前端 generated client。
4. 新增/改动的函数与类必须补注释，说明「做什么」与「为什么」。
5. 当前阶段实行为改动同步 `architecture/`，计划变更同步本文。
6. 真实供应商调用受额度门禁约束（见「额度与安全」）。

---

## P0 审计结论（已完成）

### 复用基线：已具备、无需重建

| 能力 | 现状位置 | 结论 |
|---|---|---|
| 项目 / 章节 / 分镜主链路 | `projects` → `chapters` → `shots` → `shot_details` | 直接复用 |
| 分镜状态机 | `backend/app/services/studio/shot_status.py` | 复用，语义不变 |
| 视频生成准备度 | `services/studio/shot_video_readiness.py`（8 项检查） | 复用并扩展 |
| 视频提示词 IR | `chains/prompts/ir.py` | 复用，修与显式绑定的不一致 |
| H3 渲染器 | `chains/prompts/renderers/h3.py`（7000 字符上限） | 复用 |
| 参考图有序解析 | `services/studio/generation/frame/build_context.py`（character→scene→prop→costume） | 复用为「自动推荐」 |
| H3 供应商能力 | `core/integrations/compshare/video_capabilities.py` | 复用 |
| 任务系统 | `GenerationTask` + `GenerationTaskLink` + Celery | 复用 |
| 视频抽卡与采纳 | `services/studio/shot_video_versions.py`（零新增表） | 复用 |
| 生成准备四层架构 | `services/studio/generation/{frame,video,asset_image}` | 复用 |
| 风格目录 | `project_styles` + `chains/prompts/style_pack.py` | 扩展，不另建体系 |
| 角色音色两级 | `characters.voice_*` → `actors.voice_*` 回退 | 复用 |
| 章节四阶段 | 提取分镜 / 提取资产 / 生成提示词 / 生成图片 | 复用 |
| 片段 ZIP 导出 | `services/studio/timeline.py::build_clips_archive` | 扩展 |
| 多租户隔离 | `projects.workspace_id` + `api/scoping.py` | 复用 |
| 提示词模板发布机制 | `prompt_templates` + `published_at` | 复用 |

### 缺口清单（重构必须补齐）

| # | 缺口 | 证据 | 影响阶段 |
|---|---|---|---|
| G1 | **无「场次」实体**，剧集直接挂镜头 | `shots.chapter_id` 直连，无 scene_group 表 | P5 |
| G2 | **参考绑定无持久化**：无显式绑定表、无目的、无人工锁定、无自定义排序 | `resolve_reference_mode_file_ids` 服务端按 IR 排序现算 | P6 |
| G3 | **无视频批量生成端点** | `film/` 下只有单镜 `/tasks/video`；`batch` 仅存在于资产图片 | P6 |
| G4 | **无并发控制**：无项目级并发配置，Celery 无 worker 并发/信号量约束 | 全仓无 `concurrency` 语义代码 | P2 / P6 |
| G5 | **无项目模型配置快照**：视频模型硬取 `ModelSettings.default_video_model_id` | `build_run_args` → `resolve_default_video_model` | P2 |
| G6 | **无剧本文件导入**：章节原文只是 `chapters.raw_text` 文本字段，无 `.docx` / `.md` 解析 | `schemas/studio/projects.py:91` | P3 |
| G7 | **无世界观/设定文件**与项目级解析版本 | 无对应表与端点 | P3 |
| G8 | **无增量差异分析**（改剧本后提示受影响场次/镜头/资产） | 无对应服务 | P3 |
| G9 | **无风格锁定与快照**；风格无参考图、无测试样张确认流程 | `project_styles` 仅目录 + `prompt_pack` 文本 | P2 |
| G10 | **无角色身份版本/视觉锁定**；无资产基础版本 + 衍生版本模型 | 资产图挂在 `*_images` 平铺表，无版本概念 | P4 |
| G11 | **导出不支持选择筛选与规范命名**：整项目打包，命名为 `{集}-{镜}-{标题}.mp4` | `timeline.py:445-465` | P7 |
| G12 | **无测试额度门禁**：无 quota/usage 持久化与拦截 | 全仓无 quota 语义 | P6（前置于真实调用验收） |
| G13 | **无树状工作台**：前端为扁平侧边栏导航 | `front/src/App.tsx` + `app/shell/navConfig.ts` | P1 |
| G14 | **无受影响镜头提示**：改被引用资产不提示、不阻断 | 无对应服务 | P4 |
| G15 | **配音无前端入口** | 后端 API 齐备，前端未接入 | 记录项 |

### 已核实的事实（与需求假设的偏差）

| 需求假设 | 代码事实 | 处理 |
|---|---|---|
| H3 单镜头 4–15 秒 | 优云智算 H3 声明 `min_seconds=4, max_seconds=30`（`compshare/video_capabilities.py`） | P6 按供应商实际能力校验，不写死 15 |
| 推荐每镜 3–7 张参考图 | H3 硬上限参考图 9、参考视频 3、参考音频 3、总数 ≤12；参考音频不可单独使用 | P6 采用「软推荐 + 硬上限」 |
| 风格参考图不默认进镜头参考 | 现状参考图仅来自 character/scene/prop/costume 资产图，风格图本就不入列 | 与目标一致，无需改 |
| 每集独立剧本文件 | 现状是每集一个 `chapter` + `raw_text` | P3 在 chapter 上挂文件与解析版本 |

---

## 实施阶段与文件级清单

### P1 — 树状工作台骨架（已完成）

状态：已完成并提交；当前真实实现见 [树状工作台](/docs/architecture/workbench/)。

目标：新增路由与布局，展示真实项目 / 剧集 / 镜头 / 资产数据；保留旧路径与兼容跳转。

实际新增（相对初版规划的路径调整）：
- `front/src/features/workbench/WorkbenchPage.tsx` — 容器页：路由解析、取数、面板分发
- `front/src/features/workbench/WorkbenchLayout.tsx` — 顶栏 + 左树 + 中央 + 右栏 + 底部任务栏
- `front/src/features/workbench/WorkbenchTree.tsx` — 资源树、搜索、键盘导航
- `front/src/features/workbench/WorkbenchInspector.tsx` — 右侧只读属性
- `front/src/features/workbench/WorkbenchTaskDock.tsx` — 底部任务栏
- `front/src/features/workbench/routes.ts` — 工作台路由构造与解析
- `front/src/features/workbench/buildTree.ts` — 纯函数树装配与过滤
- `front/src/features/workbench/deriveStage.ts` — 章节阶段推导
- `front/src/features/workbench/useWorkbenchQueries.ts` / `api.ts` — TanStack Query 与翻页拉全
- `front/src/features/workbench/panels/*` — 总览 / 配置 / 剧本 / 风格 / 资产 / 剧集 / 镜头 / 导出
- `front/e2e/workbench.spec.ts` — 工作台交互回归用例

修改：
- `front/src/App.tsx` — 注册 `/projects/:projectId/workbench/*`
- `front/src/app/shell/AppShell.tsx` — 工作台路径关闭旧侧边栏，避免双导航
- `front/src/features/projects/ProjectCard.tsx` / `ProjectListPage.tsx` — 项目列表工作台入口
- `front/src/pages/aiStudio/project/ProjectWorkbench/index.tsx` — 旧项目页工作台入口
- `front/src/mocks/handlers.ts` — 工作台实体 / 单镜头 / 时间线 mock

已交付：
- 真实数据树：项目 → 配置 / 剧本 / 风格 / 全局资产（角色、场景、道具、服装）/ 每集 → 镜头 / 导出；
- 镜头按剧集懒加载，分页拉全（>100 条不遗漏，20,000 条上限显式报错）；
- 中央面板按节点切换；右栏只读属性；底部任务栏与全局任务中心同源；
- 刷新、深链接、浏览器前进后退均按 URL 恢复；
- 旧项目页与旧业务页面保持可用；
- 三类状态分组展示，未合并状态语义；
- 未虚构场次，`scene-group` 仅保留类型。

本阶段未做（按计划留给后续）：
- 项目配置内嵌编辑、风格锁定与模型快照 → P2；
- `.docx` / `.md` 导入与统一审核 → P3；
- 角色身份锁定与资产版本 → P4；
- 场次实体与按场次分组 → P5；
- 显式参考绑定、批量生成、抽卡问题标记 → P6；
- 选择镜头导出 → P7。

验收：刷新 / 切换节点 / 深链接 / 返回正常；不丢已有项目；旧页面路径继续可用。

### P2 — 项目初始化与风格（已完成）

状态：C3 / C4 已完成并提交；当前实现见
[项目生成配置与模型快照](/docs/architecture/project-generation-config/) 与
[项目风格快照与锁定](/docs/architecture/project-style-lock/)。

目标：模型选择、风格锁定、比例分辨率、默认并发 4、音频参考默认关闭。

迁移（实际编号）：
- `backend/sql/034-add-project-generation-config.sql` — 项目模型 ID、时长范围、并发、配置版本/确认时间/快照
- `backend/sql/035-add-project-style-lock.sql` — 风格结构化字段/参考图/样张、项目风格快照、三个内置模板

新增/修改（实际）：
- `backend/app/models/studio_projects.py` — Project 生成配置字段、ProjectStyleOption 扩展、ProjectStyleSnapshot
- `backend/app/schemas/studio/projects.py` / `project_generation.py` / `project_style.py`
- `backend/app/api/v1/routes/studio/projects.py` — 生成配置读写、项目风格选择/锁定
- `backend/app/api/v1/routes/studio/styles.py` — 风格分析、结构化字段 CRUD
- `backend/app/services/studio/project_generation_config.py` — 两层模型解析、能力校验、快照
- `backend/app/services/studio/project_style.py` — 项目风格选择/锁定
- `backend/app/services/studio/style_analysis.py` — 复用文本供应商的参考图分析
- `backend/app/services/studio/style_catalog.py` — 结构化字段与快照优先读取
- 生成链路：视频/图片/音频任务改为项目模型优先、全局兜底
- `front/src/features/workbench/panels/ProjectConfigPanel.tsx` — 可编辑项目配置
- `front/src/features/workbench/panels/StylePanel.tsx` — 模板/自定义/分析/锁定
- `backend/tests/test_project_generation_config.py` / `test_project_style.py` / `test_style_analysis.py`

关键决策：
- 项目显式模型失效时**不回退**全局，直接报 503，避免静默换模型；
- 配置草稿可保存；确认时服务端校验模型/比例/分辨率/时长/并发；
- 业务时长固定 4–15 秒，与供应商能力取交集；
- `use_dialog_audio_as_reference` 只改新行默认值，存量项目不回填；
- 风格锁定快照与全局目录解耦，删除目录项不破坏已锁定项目。

验收：项目参数正确传递到生成预览；风格锁定后不可直接改；无 API Key 泄露。

### P3 — 剧本导入与统一审核（已完成）

状态：C5 / C6 已完成并提交；当前实现见
[剧本文档与版本](/docs/architecture/script-documents/) 与
[剧本结构化解析与统一审核](/docs/architecture/script-parse-review/)。

目标：世界观文件与每集剧本文件导入、异步解析、统一审核、增量差异提示。

迁移：
- `backend/sql/036-add-script-documents.sql` — 剧本文档与版本（原始文件、提取原文、哈希、生效指针）
- `backend/sql/037-add-script-parse-runs.sql` — 解析运行与可审核候选
- `backend/sql/038-add-script-diff-reports.sql` — 版本差异报告与人工决策

已实现（以实际代码路径为准）：
- `backend/app/services/studio/script_document_parser.py` — DOCX / Markdown 提取、大小/格式/内容校验
- `backend/app/services/studio/script_documents.py` — 上传、版本、重复检测、显式启用
- `backend/app/services/studio/script_parse.py` — 解析运行创建、候选编辑/合并、确认落库
- `backend/app/services/studio/script_parse_runner.py` — 复用 Celery/任务体系的分块解析执行与跨块合并
- `backend/app/services/studio/script_parse_chunking.py` — 长文按行分块与上下文重叠
- `backend/app/services/studio/script_diff.py` — 行级文本差异、结构化差异、影响范围
- `backend/app/chains/agents/episode_script_parser_agent.py` — 单集结构化解析 Agent
- `backend/app/schemas/skills/script_parse.py` — `ScriptParseResult` 严格 Schema
- `backend/app/api/v1/routes/studio/script_documents.py`、`script_parse.py` — 上传/解析/审核/差异端点
- `front/src/features/workbench/panels/ScriptPanel.tsx` — 原文、版本与解析入口
- `front/src/features/workbench/panels/ScriptReviewPanel.tsx` — 统一审核、合并、忽略、关联与确认
- `front/src/features/workbench/panels/ScriptDiffPanel.tsx` — 差异与影响范围查看

修改：
- `backend/app/models/types.py` — `FileType.document`、`FileUsageKind.script_document`
- `backend/app/services/studio/files.py` — DOCX/Markdown 文件类型识别与下载 media type
- `backend/app/services/worker/task_registry.py` — 注册 `script_parse` 任务执行器
- `backend/app/models/studio.py`、`backend/app/models/studio_script_documents.py`、`studio_script_parse.py`
- `front/src/features/workbench/api.ts`、`useWorkbenchQueries.ts` — 生成客户端调用与解析/审核 hooks

验收结果：
- DOCX/Markdown、中文文件名、表格、空文档、非法格式、重复上传、Unicode、长文分块均有测试；
- Mock LLM 端到端跑通上传→解析→修改/合并/忽略→确认→差异→增量确认；
- 确认幂等、重复确认不重复创建资产；
- 未修改的角色人工描述在再次解析确认后保留；
- 历史镜头与视频标记在差异/增量确认后保留；
- 未调用真实图片/视频/音频模型。

后续边界：
- 正式场次与镜头拆分仍属 P5；
- 资产身份版本、音色绑定仍属 P4；
- 差异第一版不做语义向量 Diff，也不自动覆盖正式数据。

### P4 — 角色与资产版本（已完成）

状态：C7 / C8 已完成并提交；当前实现见
[角色圣经与资产版本](/docs/architecture/character-bible-asset-versions/) 与
[资产变更影响分析](/docs/architecture/asset-impact-analysis/)。

目标：双候选图、身份锁定、多视角、音色绑定、资产衍生版本、受影响镜头提示。

迁移（实际）：
- `backend/sql/039-add-asset-versions.sql` — 角色别名、资产版本、图片候选
- `backend/sql/040-add-character-identity-lock.sql` — 角色圣经字段、视觉身份锁定、资产当前版本指针
- `backend/sql/041-add-asset-impact-refs.sql` — C8 资产版本影响审计

C7 已实现：
- `backend/app/models/studio_asset_versions.py` — CharacterAlias / AssetVersion / AssetImageCandidate
- `backend/app/services/studio/character_aliases.py` — 别名持久化与冲突检测
- `backend/app/services/studio/asset_versions.py` — 基础/衍生/身份版本与当前指针
- `backend/app/services/studio/asset_image_candidates.py` — 双候选生成、上传、采纳、删除
- `backend/app/services/studio/asset_profiles.py` — 资产档案聚合与文字字段更新
- `backend/app/services/studio/character_identity.py` — 视觉锁定、音色绑定与回退读取
- `backend/app/api/v1/routes/studio/asset_profiles.py` — 档案/版本/候选/锁定/音色 API
- 图片任务：新增 `asset_image_candidate` 关联，复用 `GenerationTask` 与 image_task_runner
- P3：别名参与实体预匹配；确认时导入别名与外貌字段
- `front/src/features/workbench/panels/AssetDetailPanel.tsx` — 角色圣经、候选图、版本、锁定、音色
- 项目级资产查询：`GET /api/v1/studio/entities/{type}?project_id=...`

C7 约束：
- 一次生成默认两张独立任务，不假设供应商 `n=2`；
- 采纳/锁定后重新抽卡不自动替换；
- 视觉锁定由服务端校验，音色不是锁定前置条件；
- Actor 共享语义不变；
- 真正图片生成测试使用 Mock，不消耗真实额度。

C8 已实现：
- `backend/app/services/studio/asset_impact.py` — 确定引用/可能影响分析与版本切换快照
- `backend/app/api/v1/routes/studio/asset_impact.py` — impact 与 impact-history API
- `backend/sql/041-add-asset-impact-refs.sql` — 版本切换影响审计
- `front/src/features/workbench/panels/AssetImpactPanel.tsx` — 受影响镜头提示
- 区分显式关联与章节/项目/文本推断；历史视频不删除、不自动重拍

后续边界：
- 正式场次与镜头拆分仍属 P5；
- 镜头级显式参考绑定与生成输入快照仍属 P6。

### P5 — 场次与分镜（已完成）

状态：C9 / C10 已完成并提交；当前实现见
[正式场次（SceneGroup）](/docs/architecture/scene-groups/)。

目标：AI 划分场次、合理镜头拆解、树状管理、排序、剧本定位。

迁移：
- `backend/sql/042-add-scene-groups-and-shot-plans.sql` — 场次、镜头规划草稿、镜头资产版本、应用映射

C9 已实现：
- `backend/app/models/studio_scene_groups.py` — SceneGroup
- `backend/app/services/studio/scene_groups.py` — CRUD、排序、镜头移动、P3 建议导入
- `backend/app/api/v1/routes/studio/scene_groups.py` — 场次 API
- `shots.scene_group_id` 可空外键；历史镜头保留为「未分配场次」
- `front/src/features/workbench/panels/EpisodePanel.tsx` — 场次分组与导入
- `front/src/features/workbench/panels/SceneGroupPanel.tsx` — 场次编辑与镜头移动
- 工作台树：剧集 → 场次 → 镜头 / 未分配场次

C10 已实现：
- `backend/app/models/studio_shot_plans.py` — 规划草稿、候选、镜头资产版本、应用映射
- `backend/app/chains/agents/scene_shot_planner_agent.py` — 结构化分镜 Agent
- `backend/app/services/studio/shot_plan_runner.py` — 分块规划、资产解析、问题检查
- `backend/app/services/studio/shot_plans.py` — 草稿/审核/确认与正式 Shot 写入
- `backend/app/api/v1/routes/studio/shot_plans.py` — 规划 API
- `front/src/features/workbench/panels/ShotPlanWorkspace.tsx` — 规划参数/审核/应用
- `ShotPanel` — 镜头文字、时长、场次与资产版本编辑

约束：
- 正式场次与场景资产严格分开；
- 存量镜头不自动塞入虚构场次；
- 含镜头场次删除保护；
- 镜头 index 保持章节内全局唯一。

后续边界：
- P6 才建立镜头级有序参考绑定与生成输入快照。

### P6 — 多参考与视频生产（进行中）

状态：C11/C12/C13 已完成并提交；C14 继续。当前实现见
[H3 多参考 Manifest 与生成输入快照](/docs/architecture/h3-reference-manifest/)。

C11 已实现：
- `shot_reference_bindings`、`shot_prompt_references`、`shot_generation_snapshots`
- 按 P5 `shot_asset_versions` 自动推荐、人工锁定/排序/删除/上传
- `@` 角色/场景/道具/服装引用解析
- H3 显式 manifest → IR → prompt 同源预览
- 单镜头 P6 生成任务与不可变快照
- 扩展 readiness；新路径默认不自动采纳

C12 已实现：
- `generation_quotas` / `generation_usage_reservations`
- 原子预留、结算、并发防超额
- 图片/视频/音频共享执行层拦截
- 额度查询与记录 API
- 默认关闭，验收环境显式启用

C13 已实现：
- `video_generation_batches` / `video_generation_batch_items`
- 批次创建、coverage 风险确认、默认并发 4/上限 8
- coordinator 子任务队列、取消、失败重试、resume
- 子任务默认不自动采纳

C14 待完成：
- 视频候选审核、问题标记与显式采纳

### P7 — 导出与端到端验收

目标：选择镜头、轻量 ZIP 导出、规范命名，跑通真实链路。

修改：
- `backend/app/services/studio/timeline.py` — 支持选择筛选、`E01_SC02_SH003.mp4` 命名
- `backend/app/api/v1/routes/studio/timeline.py` — 导出参数化
- `front/src/pages/aiStudio/workbench/panels/ExportPanel.tsx` — 筛选与下载

新增：
- `scripts/e2e_single_episode.py` — 单集端到端验收脚本（结构全量真实、真实视频不超过 4 镜）
- `docs/test-scripts/` — 三类空白剧本模板（`.docx` + `.md`）

验收：单集约 12 镜结构可完整生产；真实视频调用数严格不超过 4；导出命名与顺序正确。

### P8 — 全站迁移

第一里程碑稳定后执行：迁移剩余老页面、统一设计语言与组件库、删除确认废弃的兼容代码、完善响应式布局。

---

## 阶段依赖关系

```text
P1 树状骨架（前端，可与后端并行起步）
 ├─> P2 项目配置与风格锁定
 │     ├─> P4 角色与资产版本
 │     │     └─> P6 多参考与视频生产
 │     └─> P5 场次与分镜
 │           └─> P6（依赖场次归属）
 └─> P3 剧本导入与统一审核
       └─> P5（场次划分依赖解析结果）
P6 ──> P7 导出与端到端验收 ──> P8 全站迁移
```

关键串行点：
- P6 依赖 P2（模型快照）、P4（资产版本）、P5（场次）。
- P7 必须在 P6 之后，因为额度门禁与批量任务是验收前提。
- P8 必须最后，且第一里程碑验收通过前不开始大面积删旧页面。

---

## 风险清单

| 风险 | 说明 | 缓解 |
|---|---|---|
| R1 场次与场景资产概念混淆 | 现有 `scenes` 表是场景资产；新增场次极易重名误用 | 新模型命名 `SceneGroup`，表名 `scene_groups`，代码与文档强制区分 |
| R2 参考绑定与 IR 双源不一致 | 显式绑定与自动推荐并存时可能编号错位 | 单一快照生成：绑定列表 → IR → payload 一次成型 |
| R3 改全局默认模型影响进行中项目 | 现模型硬取全局默认 | 项目快照优先，缺失时才回落全局 |
| R4 批量任务重复计费 | 超时重试可能重复提交 | 提交状态不确定时先查询供应商任务；额度门禁累计 |
| R5 现有 3 状态语义被合并 | 树状 UI 容易把「生成中」写回 `shot.status` | 保持三状态分离，树节点只做聚合展示 |
| R6 时区依赖 | Python `datetime.timestamp()` 按本地时区解释，非 UTC 与 Go 不等价 | 迁移与任务时间戳统一 UTC |
| R7 Go 控制面已切流部分只读路径 | 若新增树状读接口需同步 Go 或绕过 | 新接口先只落 Python，Go 侧按需跟进 |
| R8 无独立测试环境 | 生产库直接迁移风险高 | 迁移全部幂等 + 备份表 + 先在测试库验证 |
| R9 存量数据字符集 | 存量表为 `utf8mb4_unicode_ci`，MySQL 8/9 默认不同会导致外键失败 | 所有新迁移显式指定字符集 |

---

## 建议提交拆分

| 提交 | 类型 | 内容 |
|---|---|---|
| C1 | `[docs]` | P0 审计结论与本计划文档 |
| C2 | `[feat]` | P1：树状工作台骨架与路由（✅ 已完成） |
| C3 | `[feat]` | P2：项目生成配置快照与并发配置（✅ 已完成） |
| C4 | `[feat]` | P2：风格锁定与快照（✅ 已完成） |
| C5 | `[feat]` | P3：剧本文档导入与版本管理（✅ 已完成 `6e3cf7d`） |
| C6 | `[feat]` | P3：AI 解析、统一审核与增量差异（✅ 已完成） |
| C7 | `[feat]` | P4：角色圣经与资产版本（✅ 已完成 `e5f14d6`） |
| C8 | `[feat]` | P4：资产变更影响分析（✅ 已完成） |
| C9 | `[feat]` | P5：正式场次实体与树状管理（✅ 已完成 `008526c`） |
| C10 | `[feat]` | P5：AI 分镜规划与镜头管理（✅ 已完成） |
| C11 | `[feat]` | P6：H3 多参考绑定与生成输入快照（✅ 已完成 `2428814`） |
| C12 | `[feat]` | P6：额度门禁 |
| C13 | `[feat]` | P6：批量视频生成任务与并发控制 |
| C14 | `[feat]` | P6：抽卡审核与问题标记 |
| C15 | `[feat]` | P7：选择导出与规范命名 |
| C16 | `[test]` | P7：端到端验收脚本与测试剧本模板 |
| C17 | `[refactor]` | P8：老页面迁移与兼容代码清理 |

每个提交必须自带迁移文件与回滚说明，不跨阶段混提。

---

## 额度与安全约束

一次重构验收的累计额度上限：

| 类型 | 上限 |
|---|---|
| 图片 | 20 张 |
| 视频 | 4 次 |
| 音频 | 500 字 |

- 额度必须持久化，耗尽即阻止新的真实生成（P6 的 C12 交付）。
- 自动重试同样计入可能产生费用的调用。
- 对未确定是否计费的超时提交，采取保守计数，先查询任务再考虑重试。
- 单集 12 镜验收：结构、引用与状态用真实业务数据全量验证；最多 4 镜真实生成；其余用 Mock 或历史结果。
- 凭据只存服务端，禁止出现在源码、日志、测试快照与 Git 提交中。
- 无独立测试环境时，不得直接在生产库执行破坏性迁移。

---

## 阶段通用执行纪律

1. 明确影响文件、数据模型与 API。
2. 列出复用能力与新增功能。
3. 实现最小可运行闭环。
4. 执行测试并修复（后端 pytest、前端 `pnpm exec tsc --noEmit`、相关契约与交互测试）。
5. 更新架构与计划文档。
6. 提交独立、可回滚的变更。
7. 输出本阶段验收报告（必须有证据，不允许只写「已完成」）。