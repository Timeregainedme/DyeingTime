---
title: "V2 交付就绪检查"
description: "P8 交付前状态：功能、Mock、迁移、浏览器、安全、真实供应商与生产阻塞项。"
weight: 10
---

> 状态：**受控内部试运行候选，不是生产就绪**。L3 真实供应商与 L4 人工质量尚未执行。

## 1. P0–P8 完成情况

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| P0 架构审计 | 完成 | 计划与边界已落文档 |
| P1 树状工作台 | 完成 | 默认入口已切到工作台 |
| P2 项目配置/风格 | 完成 | 配置、模型快照、风格锁定 |
| P3 剧本解析审核 | 完成 | 上传、解析、审核、差异 |
| P4 角色/资产版本 | 完成 | 身份锁定、版本、音色样本 |
| P5 场次/分镜 | 完成 | SceneGroup、ShotPlan、镜头资产版本 |
| P6 多参考/批量/审核 | 完成（Mock） | H3 manifest、额度、批次、抽卡 |
| P7 选择式导出 | 完成（Mock） | MP4 ZIP、预检查、plan hash |
| P8 整合/收口 | 代码完成 | 导航、幂等、迁移修复、文档 |

## 2. 功能与旧页面

当前默认：项目列表 → `/projects/:id/workbench`。

- 无 query 的 `/projects/:id` 自动跳工作台。
- 带 `?tab=...` 的旧 URL 保留。
- 旧版页面同标签打开，浏览器返回可恢复工作台。
- 旧页面迁移分类见 [V2 工作台迁移与旧页面保留清单](/docs/architecture/v2-workbench-migration/)。

未删除：旧 ChapterStudio、旧镜头编辑、首尾帧/音频、ffmpeg 成片、clips-archive、模型/供应商/音色/文件管理。

## 3. 可靠性

- 单镜头：`request_key` 持久化 + `(shot_id, request_key)` 唯一约束。
- 批次：`request_key` + `request_hash` + `(chapter_id, request_key)` 唯一约束。
- 同 key + 同输入返回已有任务；同 key + 不同输入冲突。
- 并发唯一约束兜底；重复提交不重复预留额度。
- 批次仍使用 persisted batch/item/coordinator、`enqueued_at` 与 resume。
- 详细边界见 [生成请求幂等与并发边界](/docs/architecture/generation-idempotency/)。

## 4. 迁移验证

在独立本地 MySQL 8.0.46 实例验证，不连接生产：

### 全新库

- 当前 ORM 元数据建表成功。
- 034–048 顺序执行成功。
- 034–048 第二次重复执行成功。

### 旧库升级

- 使用 pre-034 commit `12bb162` 的 ORM 建旧库。
- 插入旧项目、章节、镜头、角色、视频文件；镜头状态为历史 `generating`。
- 在旧库执行 034–048。
- 结果：
  - 旧项目/章节/镜头/视频文件均保留。
  - 旧镜头读取状态归一为 `pending`，数据库原值 `generating` 未被改写。
  - 新字段 `scene_group_id`、`video_prompt_draft`、角色身份字段、request_key 等补齐。
  - 未创建虚构 SceneGroup。
- 修复：`040-add-character-identity-lock.sql` 动态 SQL 的 COMMENT 引号在 MySQL 8.0.46 会报语法错误；P8 已修正为可执行形式，并验证重复执行。

### 迁移边界

- 001–033 属于既有基线；本次验证的是 034–048。
- 生产执行前仍应备份、在 staging 重放、核对字符集/外键。
- P8 无新增业务表；048 只增加 request_key/hash 与唯一索引。

## 5. Mock 全流程

```bash
cd backend
uv run python scripts/v2_full_acceptance.py
```

结果：

- 12 镜头、2 场次、角色身份锁定、Mock 剧本版本。
- H3 参考顺序/锁定、@ 引用、快照不变。
- 12 个 Mock 批次任务，并发配置 4，全部成功。
- 8 个镜头采纳。
- 选择 4 个已采纳镜头导出 ZIP，文件名 E01_SC01_SH001/2、E01_SC02_SH007/8。
- ZIP 仅 MP4；真实 MP4 fixture 内容一致。
- 切换采纳版本后 plan hash 变化，新 ZIP 使用新文件，旧文件保留。
- 额度仍为 image 20 / video 4 / audio 500。

## 6. 浏览器 E2E

P9-A 已实际启动 Chromium 并执行页面断言。

- Node 22.23.4（`pnpm dlx node@22`）。
- Playwright 1.64.1。
- 本机缺少的 `libatk/libatspi/libXcomposite/libXdamage` 通过 Ubuntu noble deb 解包到本地临时 sysroot，`LD_LIBRARY_PATH` 指向后 Chromium 正常启动；生产环境未修改。
- 原有 25 个前端 Mock E2E 全部通过（25 passed）。
- 新增真实后端 E2E：
  - React/Vite 7801
  - FastAPI 8010
  - 独立 MySQL `p8_e2e`
  - 本地 S3 mock（moto）
  - 仅外部 AI 供应商未调用
  - 2 个用例通过：真实页面纵向检查 + ZIP 下载；4 个桌面分辨率截图。
- 截图：`docs/p9-screens/`（32 张，8 页面 × 4 分辨率）。
- 截图显示中文、导航、三栏工作台、制作流程、导出页；1280 宽度核心操作可滚动访问。

限制：

- 真实后端用例的 P3/P4/P5 数据是确定性 Mock 业务对象，不是浏览器中重新执行 AI 上传/解析/规划。
- 真实后端用例覆盖项目列表、工作台总览、配置、风格、剧本、角色、剧集、镜头、导出与 ZIP 下载。
- 真实后端的创建项目、上传文件、AI 解析、视频生成任务仍需继续补浏览器级操作。
- CI 工作流已在 P9-B1 实际运行并成功：
  - `V2 Browser E2E`：https://github.com/Timeregainedme/dyeingtime/actions/runs/39957304607
  - `V2 Real Backend Browser E2E`：https://github.com/Timeregainedme/dyeingtime/actions/runs/39957304589
  - 早期失败运行已通过并发=1、FastAPI 存活检查和失败摘要修复。

## 7. 安全检查

- 跨工作区/跨项目读取继续走 scoped helpers。
- 导出按 FileUsage 校验项目归属。
- 新快照/任务 payload 不写 API Key。
- 新增只读扫描脚本：

```bash
cd backend
uv run python scripts/scan_generation_task_secrets.py
```

只输出任务 ID 和敏感字段路径，不打印值；不自动修改历史任务。本次在独立测试库确认可识别 `run_args.api_key` 路径。

历史任务如含密钥，需要单独脱敏方案和生产审批，不能直接批量改写。

## 8. 真实供应商

计划见 [P7 真实供应商验证计划（待批准）](/docs/plans/p7-real-provider-validation/)。

- 未执行真实付费调用。
- 额度消耗 0。
- L3 未验证，L4 未验证。
- 不得将 Mock 成功描述为真实媒体生产验收。

## 9. 生产部署前检查

- [ ] 在 staging 备份并重放 034–048。
- [ ] 校验所有新表/索引/外键和 utf8mb4_unicode_ci。
- [ ] 运行旧数据回归：项目、镜头、资产、视频读取。
- [ ] 启用验收额度 scope 前确认隔离，避免生产继承 20/4/500。
- [ ] 配置 S3/对象存储、Redis、Celery、供应商凭据。
- [ ] 在 CI/staging 跑真实浏览器 E2E 与截图。
- [ ] 完成 L3 四次真实视频测试并记录额度。
- [ ] 完成 L4 人工质量验收。
- [ ] 制定历史 api_key 扫描/脱敏方案。
- [ ] 制定回滚：应用回滚 + 048 索引/列回滚 + 任务/额度保留策略。

## 10. 剩余阻塞项

### P0 阻止生产

- L4 人工视频质量未验收。
- 生产迁移/部署未执行。
- 法币账单未由供应商确认；真实视频仅在本地测试存储。

### P1 上线前应修复

- 真实后端浏览器 E2E 目前只真实创建项目/保存配置，其余业务数据仍由 seed 准备；尚未覆盖 UI 上传、AI 解析、视频生成全操作。
- CI real-backend workflow 已实际成功运行。
- 历史任务 api_key 只读扫描已有，脱敏方案未执行。
- 单任务幂等边界不覆盖供应商侧 exactly-once；需人工查询/恢复流程。

### P2 可延期

- 旧页面完整迁移/删除。
- 参考视频素材能力。
- 非 MP4 转码。
- 旧 clips-archive 与 ffmpeg 成品的统一导出体验。
- 大列表虚拟化/性能压测。
