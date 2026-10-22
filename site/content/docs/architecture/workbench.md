---
title: "树状工作台"
description: "记录当前已生效的工作台路由、三栏布局、树节点数据来源与状态展示规则。"
weight: 22
---

> 本文属于“当前架构”文档，描述 P1 已经落地的树状工作台骨架。
> 尚未实现的能力（场次、风格锁定、资产版本、多参考绑定、批量生成、选择式导出）
> 见 [V2 树状工作台重构计划](/docs/plans/v2-workbench-refactor/)。

## 定位

工作台把项目、剧集、镜头与全局资产收进同一套「左树 + 中编辑区 + 右属性栏 + 底部任务栏」布局，
替代在多个独立页面之间来回切换的主路径。

当前边界：

- 树与面板只读取真实接口，不提供静态演示数据；
- 资产生成、镜头提取、视频生成、成片导出仍由旧版页面承担；
- 工作台对旧能力的入口统一用「新标签页打开」，保留当前树的选中节点；
- 不引入无限画布，也不复制一套新的业务状态机。

## 路由契约

所有节点都挂在 `/projects/:projectId/workbench/*` 下，使用 **URL 表达选中对象**：

| 路由 | 选中节点 |
| --- | --- |
| `/workbench`、`/workbench/overview` | 项目总览 |
| `/workbench/config` | 项目配置（只读） |
| `/workbench/script` | 世界观与剧本（项目级） |
| `/workbench/script/:chapterId` | 某一集的剧本原文 |
| `/workbench/style` | 风格圣经 |
| `/workbench/assets/:type` | 角色 / 场景 / 道具 / 服装列表 |
| `/workbench/assets/:type/:assetId` | 单个资产 |
| `/workbench/episodes/:chapterId` | 某一集 |
| `/workbench/episodes/:chapterId/shots/:shotId` | 某个镜头 |
| `/workbench/export` | 导出 |

为什么用路径段而不是 `?node=shot:xxx`：

- 层级与业务结构一一对应，可读、可分享、可被日志直接识别；
- 刷新、深链接、浏览器前进后退都由路由天然承担，不需要额外同步内存状态；
- 查询参数更适合表达「同一节点的显示选项」，不适合表达资源定位。

路由使用 splat（`workbench/*`）+ `frontend/src/features/workbench/routes.ts` 解析，
因此新增节点类型只需扩展解析函数，不必为每一层再注册一次嵌套路由。

## 布局

`front/src/features/workbench/WorkbenchLayout.tsx`：

```text
顶部：返回项目列表 / 项目名称 / 制作进度 / 主题 / 语言 / 账号
左侧：项目资源树（220–420px，可拖拽，偏好存 localStorage）
中央：当前节点面板（唯一滚动区）
右侧：属性面板（240–420px，可收起）
底部：任务中心（120–360px，可收起）
```

响应式规则：

- `< 1024px`：左树改为抽屉；
- `< 1280px`：右栏改为抽屉；
- 抽屉与桌面面板互斥渲染，避免同一棵树挂两份 DOM。

工作台路径下 `AppShell` 直接返回 `Outlet`，不渲染旧侧边栏与全局浮窗，
避免双导航；任务轮询仍复用同一个 `TaskRuntimeProvider`，底部任务栏与浮窗同源。

## 树节点

`front/src/features/workbench/buildTree.ts` 是纯函数，输入真实业务数据，输出：

```text
项目
├── 项目配置
├── 世界观与剧本
├── 风格圣经
├── 全局资产
│   ├── 角色（项目内资产）
│   ├── 场景（工作区全局资产）
│   ├── 道具
│   └── 服装
├── 第 1 集
│   └── 镜头 01 / 02 / …
├── 第 2 集
└── 导出
```

规则：

- 节点 ID 只使用业务 ID 拼接（`episode:<id>`、`shot:<id>`、`asset:<type>:<id>`），不用数组下标；
- 剧集按 `index` 升序，镜头按 `index` 升序；
- 镜头**按剧集懒加载**：只有展开的剧集才会请求镜头与 runtime summary；
- 未加载完成时显示「正在加载镜头…」，失败显示「镜头加载失败」，不把未知状态写成 0；
- 搜索只过滤已加载节点；命中后代时保留祖先，但不会因为父节点命中就把整集镜头铺开；
- `scene-group` 是 P5 的保留类型，当前数据源不存在，因此树里不会出现虚构场次节点。

## 数据来源

全部走 `services/generated`（OpenAPI 客户端），没有新的手写接口封装：

| 数据 | 接口 | 说明 |
| --- | --- | --- |
| 项目 | `GET /studio/projects/{id}` | 名称、题材、进度、生成参数 |
| 剧集 | `GET /studio/chapters?project_id=` | 按 `index` 升序 |
| 镜头 | `GET /studio/shots?chapter_id=` | 按 `index` 升序，展开时加载 |
| 运行时摘要 | `GET /studio/shots/runtime-summary?chapter_id=` | 镜头节点上的运行中标记 |
| 镜头详情 | `GET /studio/shots/{id}` / `shot-details/{id}` | 基础信息与镜头语言 |
| 准备状态 | `GET /studio/shots/{id}/preparation-state` | 待确认项与生成准备 |
| 视频准备度 | `GET /studio/shots/{id}/video-readiness?reference_mode=reference` | 仅选中镜头时请求 |
| 角色 | `GET /studio/entities/character` | 工作区返回后按 `project_id` 收敛 |
| 场景 / 道具 / 服装 | `GET /studio/entities/{type}` | 工作区级全局资产 |
| 风格目录 | `GET /studio/styles` | 说明与提示词质感描述 |
| 时间线 | `GET /studio/timeline/projects/{id}` | 导出面板的片段统计 |

分页策略（`front/src/features/workbench/api.ts`）：

- 每页 100 条（与后端上限一致），按 `max_page` 翻到最后一页；
- 超过 200 页（20,000 条）时**抛错而不是静默截断**，避免用户误以为镜头丢了。

## 状态展示

树与面板严格区分三类状态，颜色取自 `state-* / run-* / ready-*` 三组 token：

| 语义 | 来源 | 展示位置 |
| --- | --- | --- |
| 信息提取确认 | `shot.status`、`preparation-state` | 树节点圆点、镜头面板「信息确认状态」 |
| 运行时任务 | `GenerationTask` / runtime summary | 树节点运行中圆点、底部任务栏 |
| 视频生成准备度 | `video-readiness` | 镜头面板与右侧属性栏 |

- 历史上的 `generating` 不再表示运行时状态，前端按「未确认」处理；
- 运行中不会写回 `shot.status`；
- video-readiness 只对当前选中的镜头请求，避免对几百个镜头做 N+1 查询。

## 旧版页面衔接

工作台不复制提取、生成、导出逻辑。需要旧能力时使用新标签页：

| 能力 | 入口 |
| --- | --- |
| 项目设置 / 章节管理 / 角色管理 | `/projects/{id}?tab=...` |
| 分镜列表与提取 | `/projects/{id}/chapters/{cid}/shots` |
| 单镜准备台 | `/projects/{id}/chapters/{cid}/shots/{sid}/edit` |
| 生成工作室 | `/projects/{id}/chapters/{cid}/studio` |
| 成片与导出 | `/projects/{id}/editor` |
| 资产编辑 | `/assets/{scenes|props|costumes}/{aid}/edit`、`/projects/{id}/roles/{rid}/edit` |

新标签页保留工作台当前 Tab 的 URL 与树展开状态，用户不需要重新定位节点。

## 当前未实现（按阶段）

| 能力 | 阶段 |
| --- | --- |
| 项目模型快照、风格锁定、并发配置、内嵌编辑 | P2 |
| `.docx` / `.md` 剧本导入、统一审核、增量差异 | P3 |
| 角色身份锁定、资产基础/衍生版本 | P4 |
| 场次（`SceneGroup`）与按场次分组镜头 | P5 |
| 显式参考绑定、批量生成、抽卡问题标记 | P6 |
| 选择镜头导出与 `E01_SC02_SH003.mp4` 命名 | P7 |

## 相关文件

```text
front/src/features/workbench/
├── WorkbenchPage.tsx          页面容器：路由解析、取数、面板分发
├── WorkbenchLayout.tsx        三栏布局、拖拽调宽、抽屉
├── WorkbenchTree.tsx          资源树、搜索、键盘导航
├── WorkbenchInspector.tsx     右侧只读属性
├── WorkbenchTaskDock.tsx      底部任务栏
├── routes.ts                  路由构造与解析
├── buildTree.ts               纯函数树装配与过滤
├── deriveStage.ts             章节阶段推导
├── useWorkbenchQueries.ts     TanStack Query 查询
├── api.ts                     翻页拉全与数据归一
├── usePanelResize.ts          面板尺寸与持久化
└── panels/                    各节点中央面板
```
