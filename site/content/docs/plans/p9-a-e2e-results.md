---
title: "P9-A 浏览器与真实后端验收结果"
description: "记录 P9-A 的 Chromium E2E、真实 FastAPI/MySQL 验收、截图、限制与提交。"
weight: 9
---

> 状态：真实 Chromium 页面断言通过；真实后端纵向页面通过。L3 真实供应商与 L4 人工质量仍未执行。

## 1. 环境

- Node 22.23.4
- Playwright 1.64.1
- Chromium headless
- 前端 Vite 7801
- FastAPI 8010
- MySQL 8.0.46 独立库 `p8_e2e`
- 本地 S3 mock（moto）
- 外部 AI 供应商：未调用

本机 Chromium 缺失的 `libatk1.0-0t64`、`libatk-bridge2.0-0t64`、`libatspi2.0-0t64`、`libxcomposite1`、`libxdamage1` 从 Ubuntu noble deb 解包到临时 sysroot，通过 `LD_LIBRARY_PATH` 启动；未修改生产系统。

## 2. 通过结果

### 原有前端 E2E

```text
25 passed
```

覆盖项目列表、旧版工作室、设计系统、镜头看板、镜头编辑、风格管理、树状工作台。

### 真实后端 E2E

```text
2 passed
```

- 真实登录 FastAPI。
- 真实项目列表、工作台、配置、风格、剧本、角色、场次、镜头、导出页面。
- 真实 API 数据来自 MySQL。
- 导出选择 4 个已采纳视频，预检查、下载 ZIP，`unzip -l` 验证 4 个 MP4、无 MANIFEST。
- 8 个页面在 1280/1440/1920/2560 下截图，共 32 张：`docs/p9-screens/`。

## 3. 测试文件

- `front/playwright.real.config.ts`
- `front/e2e-real/vertical.spec.ts`
- `backend/scripts/seed_p9_staging.py`
- `.github/workflows/v2-browser-e2e.yml`
- `.github/workflows/v2-real-backend-e2e.yml`

## 4. 数据边界

真实后端用例使用固定 E2E 用户/工作区/项目：

- 用户：`e2e`（仅测试库）
- 项目：`p-e2e`
- 12 镜头、2 场次、4 个已采纳 MP4、角色/场景资产
- P3/P4/P5 的 AI 输出以确定性 Mock 业务对象预置，不是浏览器中重新执行 AI 上传/解析/规划
- P6 视频不是供应商生成，使用本地有效 MP4 fixture
- 外部 AI 供应商未参与

因此该结果证明：**真实 React + 真实 FastAPI + 真实 MySQL + 测试对象存储 + Mock 外部 AI 的主页面与导出链路可用**。
不证明：真实 AI 解析、真实视频生成、真实质量。

## 5. 发现与修复

- P8 导航迁移后，旧 Playwright 用例仍按旧分镜结构断言；已更新为剧集 + 未分配场次 + 树节点导航。
- 真实后端开发模式登录使用相对 `/api`，Vite 原先没有代理；已增加 `server.proxy`，允许 `VITE_DEV_PROXY_TARGET` 指向测试后端。
- 真实后端项目数据 `visual_style` 必须使用枚举值 `现实/动漫`，不是内部 key `live_action`；测试数据已修正。
- 本机截图初版因缺少 CJK 字体显示方框；安装用户级 Noto Sans CJK 后重新生成。

## 6. 未完成

- 浏览器中创建项目、配置保存、风格锁定、文件上传、AI 解析、分镜规划、视频生成提交的逐步 UI 操作。
- 真实后端 + MySQL 的 CI workflow 尚未实际运行。
- Chrome 系统依赖在 CI 由 `playwright install --with-deps` 负责；本地需要临时 sysroot 或安装系统包。
- L3/L4 未执行。
