---
title: "OpenAPI"
weight: 4
description: "理解前后端接口生成与同步流程。"
---

前端请求函数和类型由后端 OpenAPI 文档生成。

## 生成目录

- `front/openapi.json`
- `front/src/services/generated/`

## 更新命令

```bash
cd front
pnpm run openapi:update
```

## 生成流程

1. 先从后端拉取 `/openapi.json`
2. 写入 `front/openapi.json`
3. 再生成 `front/src/services/generated/`

## 什么时候需要更新

- 后端新增路由
- 后端修改请求或响应模型
- 前端需要消费新的接口字段
