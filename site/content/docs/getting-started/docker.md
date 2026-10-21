---
title: "Docker 部署"
weight: 3
description: "通过 Docker Compose 拉起完整依赖与服务。"
---

## 服务组成

- Front
- Backend
- MySQL
- RustFS

## 启动方式

```bash
cp deploy/compose/.env.example deploy/compose/.env
docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml up --build
```

## 默认访问地址

- 前端：`http://localhost:7788`
- 后端：`http://localhost:8000`
- RustFS Console：`http://localhost:9001`

## 说明

首次启动会自动初始化数据库，并导入提示词模板数据。
