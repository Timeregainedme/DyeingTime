---
title: "FAQ"
weight: 3
description: "常见开发与站点维护问题。"
---

## 后端没启动时，前端为什么无法更新 OpenAPI？

因为 `pnpm run openapi:update` 会先请求本地后端的 `/openapi.json`。

## 开发时一定要用 Docker 吗？

不一定。前后端都支持本地直接启动，Docker 更适合完整联调与依赖服务管理。

## 官网为什么需要 Go？

因为 Hextra 通过 Hugo Modules 拉取，模块解析依赖 Go 工具链。

## 为什么本地 Hugo 版本也要注意？

因为 Hextra 对 Hugo 最低版本有要求。版本过低时，主题模板可能无法正常加载。
