---
title: "本地开发"
weight: 2
description: "启动前后端并完成本地联调。"
---

## 启动后端

```bash
cd backend
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 启动前端

```bash
cd front
pnpm install
pnpm dev
```

## 默认端口

- 前端：`http://localhost:7788`
- 后端：`http://localhost:8000`
- Swagger：`http://localhost:8000/docs`

## OpenAPI 更新

```bash
cd front
pnpm run openapi:update
```

## 官网与文档站本地预览

```bash
cd site
hugo mod tidy
hugo server --buildDrafts --disableFastRender
```

## 推荐的联调顺序

1. 启动后端，确认 `/docs` 和 `/health` 正常。
2. 启动前端，确认页面能访问并能请求后端。
3. 如果修改了接口定义，再执行 `openapi:update`。
4. 如果同时在维护官网，再单独启动 `site/` 预览。
