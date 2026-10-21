---
title: "安装说明"
weight: 1
description: "安装 DyeingTime 所需的基础环境与依赖。"
---

## 环境要求

| 用途 | 依赖 |
| --- | --- |
| 应用本体 | Python 3.12+、`uv`、Node.js 与 pnpm、MySQL 8、Redis 7、S3 兼容对象存储 |
| 一键部署（可选） | Docker 与 Docker Compose |
| Go 控制面（可选） | Go 1.27+ |
| 文档站（可选） | Hugo extended `>= 0.146.0`、Go `>= 1.22`（拉取 Hugo Modules） |

## 获取代码

```bash
git clone https://github.com/Timeregainedme/dyeingtime.git
cd dyeingtime
```

## 目录建议

如果你只是使用应用，优先关注：

- `front/`
- `backend/`
- `deploy/`

如果你还要维护官网与文档站，再关注：

- `site/`

## 最快路径：Docker 一键部署

```bash
cp deploy/compose/.env.example deploy/compose/.env
docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml up -d --build
```

编排包含 MySQL、Redis、对象存储、后端、Celery Worker 与前端共六个服务，
外加两个一次性初始化容器（数据库迁移、对象存储初始化）。

| 服务 | 地址 |
| --- | --- |
| 前端 | `http://localhost:7788` |
| 后端 API | `http://127.0.0.1:8000`（`/docs` 为 Swagger） |
| MySQL | `localhost:${MYSQL_PORT:-3306}` |
| Redis | `localhost:${REDIS_PORT:-6379}` |
| 对象存储 API | `http://localhost:${RUSTFS_PORT:-9000}` |
| 对象存储控制台 | `http://localhost:${RUSTFS_CONSOLE_PORT:-9001}` |

> 完整的部署要点（对象存储寻址方式、公共读策略、端口冲突处理）见
> [部署说明](https://github.com/Timeregainedme/dyeingtime/blob/main/docs/部署说明.md)。

## 本地开发

### 后端

```bash
cd backend
cp .env.example .env
uv sync --group dev
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动后：

- Swagger 文档：`http://127.0.0.1:8000/docs`
- OpenAPI 契约：`http://127.0.0.1:8000/openapi.json`

### 前端

```bash
cd front
pnpm install
pnpm dev
```

### Go 控制面（可选）

Go 控制面只接管只读接口，**不部署也能完整运行**（全部由 Python 处理面承接）。

```bash
cd backend/go
go build -o /tmp/dyeingtime-api ./cmd/api
```

类型由 `front/openapi.json` 经 `oapi-codegen` 生成：

```bash
cd backend/go && make generate
```

## 初始化数据库

迁移是 `backend/sql/` 下的纯 SQL 文件，由 compose 的 `mysql-init-sql` 服务按文件名顺序执行。
自行部署时按序号依次执行即可（脚本是幂等的，重复执行不会报错）。

## 安装站点主题模块

```bash
cd site
hugo mod tidy
hugo server
```

## 建议的安装顺序

1. 先安装后端依赖，确保 API 能跑起来。
2. 再安装前端依赖，用于本地联调。
3. 如果需要维护官网和文档，再初始化 `site/` 的 Hugo Modules。
4. 需要 Go 控制面时，最后再准备 Go 工具链。
