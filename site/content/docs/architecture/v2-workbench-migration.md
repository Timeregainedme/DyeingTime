---
title: "V2 工作台迁移与旧页面保留清单"
description: "P8 当前已迁移、部分迁移、保留和待废弃的旧页面功能对照。"
weight: 36
---

> 本文是 P8 的当前事实清单；未完成真实供应商 L3/L4 前，不删除旧生成适配器、任务执行器和媒体路径。

## 1. 默认入口

- 生产默认：项目列表 → `/projects/:projectId/workbench`
- `/projects/:projectId`（无 query）自动跳到树状工作台。
- 带 `?tab=...` 的旧项目深链接仍保留，避免存量链接失效。
- 旧版页面入口改为同一标签页打开；浏览器返回可回到工作台。

## 2. 功能对照

| 旧功能/路由 | 新工作台位置 | 覆盖率 | 策略 |
| --- | --- | --- | --- |
| 项目列表 `/projects` | `/projects` 新卡片 | A | 已替换默认入口 |
| 项目 dashboard `/projects/:id?tab=dashboard` | `/workbench` 总览 | A/B | 保留旧 URL；新入口优先工作台 |
| 项目设置 `/projects/:id?tab=settings` | `/workbench/config` | A | 新面板覆盖生成配置；旧页保留 |
| 章节/剧本 `/projects/:id?tab=chapters` | `/workbench/script` | B | 上传/审核/版本已覆盖；旧版章节批量操作保留 |
| 角色管理 `/projects/:id?tab=roles` | `/workbench/assets/character` + 资产详情 | A/B | 资产版本、候选、锁定、音色已覆盖；旧页保留兼容 |
| 全局资产 `/assets` | `/workbench/assets/*` | A/B | 新工作台资产列表/详情；全局素材库旧页保留 |
| 分镜列表 `/chapters/:cid/shots` | `/workbench/episodes/:cid` | B | 场次/镜头/资产版本/参考/生成已覆盖；旧列表保留 |
| 分镜编辑 `/chapters/:cid/shots/:sid/edit` | `/workbench/.../shots/:sid` | B | 新 ShotPanel 覆盖核心；首尾帧/音频/旧高级编辑仍可走旧页 |
| 分镜工作室 `/chapters/:cid/studio` | `/workbench/episodes/:cid` + 批量/审核 | B/C | H3、批量、抽卡已覆盖；旧图片生成/首尾帧/音频路径保留 |
| 统一审核 `/chapters/:cid/review` | `/workbench/script` 审核 | A/B | 新审核面板可确认；旧审阅页保留 |
| 视频版本 `/editor` | `/workbench/.../shots/:sid` 视频候选 | A | 新抽卡采纳覆盖；旧 ffmpeg 成片编辑保留 |
| 旧片段打包 `/timeline/.../clips-archive` | `/workbench/export` 选择式 ZIP | A/B | 新 MP4-only；旧 clips-archive 保留语义 |
| ffmpeg 成片导出 | 旧 `/timeline/.../export` | C | 新阶段不替代整集成片，保留 |
| 任务中心 | 工作台底部任务中心 | A/B | 通用任务保留；业务详情留在业务面板 |
| 模型/供应商管理 `/models` | 项目配置选择模型 | C | 全局模型管理仍保留 |
| 音色/语音管理 `/voices` | 资产详情固定音色样本 | C | 旧语音生成/管理仍保留 |
| 文件库 `/files` | 无完整替代 | C | 保留 |
| 风格管理 `/styles` | `/workbench/style` | A/B | 新风格锁定覆盖；全局风格目录旧页保留 |

分类：A=新工作台完全替代；B=部分替代需补齐；C=保留独立价值；D=确认废弃（当前无新增 D 删除）。

## 3. 当前不删除的旧能力

- 首尾帧生成与关键帧流程。
- 旧音频任务与台词配音相关入口。
- 旧 ffmpeg 成片拼接与 clips-archive。
- 旧资产图片生成/候选的兼容链路。
- 存量项目旧 tab 编辑入口。
- 全局模型、供应商、音色、文件管理。

删除条件仍按 AGENTS.md：功能对等、无依赖、无深链接、无存量数据解析、测试迁移、回滚方案。

## 4. P8 新增导航约束

- 工作台内部不再默认打开新标签页；`LegacyLink` 改为同标签导航。
- 工作台顶部保留“旧版项目页”过渡入口。
- 默认项目打开直达工作台；旧 tab 参数仍可进入旧页。
- 制作流程入口集中在项目总览，不新增与业务状态冲突的主状态机。
