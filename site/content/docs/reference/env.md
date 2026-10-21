---
title: "环境变量"
weight: 1
description: "后端、Go 控制面与 Compose 部署涉及的全部环境变量。"
---

后端配置由 `backend/app/config.py` 的 `Settings`（`pydantic-settings`）读取，
全部以环境变量或 `backend/.env` 文件注入；**Go 控制面只从环境变量读取**，
与 Python 共用同一份 `.env`。

## 应用与 API

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `APP_NAME` | `DyeingTime API` | 应用名 |
| `DEBUG` | `false` | 调试开关 |
| `API_V1_PREFIX` | `/api/v1` | 接口路径前缀 |
| `CORS_ORIGINS` | `http://localhost:7788,http://127.0.0.1:7788` | 允许的前端来源，逗号分隔 |

## 数据库

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite+aiosqlite:///./dyeingtime.db` | 异步数据库连接串 |

生产使用 MySQL：

```bash
DATABASE_URL=mysql+aiomysql://user:pass@127.0.0.1:3306/dyeingtime
```

## Redis / Celery

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `REDIS_HOST` | `localhost` | Redis 主机 |
| `REDIS_PORT` | `6379` | Redis 端口 |
| `REDIS_DB` | `0` | Redis 库号 |
| `REDIS_PASSWORD` | 空 | Redis 密码 |
| `CELERY_BROKER_URL` | 空 | 直接指定完整 broker 地址时使用，优先于上面四项 |

## 鉴权与密钥加密

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `JWT_SECRET` | 空 | **必填**。签发与校验访问令牌的 HMAC 密钥 |
| `JWT_EXPIRE_MINUTES` | `720` | 访问令牌有效期（分钟） |
| `SECRETS_KEY` | 空 | **推荐必填**。供应商密钥落库加密用的 Fernet 密钥 |

> ⚠️ `SECRETS_KEY` 未配置时，加密会回退为「从 `JWT_SECRET` 派生密钥」并打告警日志。
> 这意味着**轮换 `JWT_SECRET` 会导致已加密的供应商密钥无法解密**。生产环境请显式设置
> `SECRETS_KEY`，生成方式：
>
> ```bash
> python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
> ```

存量明文密钥可用幂等迁移脚本就地加密（`--dry-run` 可先预览）：

```bash
cd backend && uv run python scripts/encrypt_provider_keys.py --dry-run
```

## Google 登录（可选）

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `GOOGLE_CLIENT_ID` | 空 | Google OAuth 客户端 ID |
| `GOOGLE_ALLOWED_EMAILS` | 空 | 允许登录的邮箱，逗号分隔；**留空等于放行所有** |
| `GOOGLE_TOKENINFO_URL` | `https://oauth2.googleapis.com/tokeninfo` | 令牌校验地址 |

> 公网部署请务必配置 `GOOGLE_ALLOWED_EMAILS` 白名单。

## 对象存储（S3 兼容）

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `S3_ENDPOINT_URL` | 空 | S3 端点；自建服务（RustFS / MinIO）填服务地址 |
| `S3_REGION_NAME` | 空 | 区域 |
| `S3_ACCESS_KEY_ID` | 空 | Access Key |
| `S3_SECRET_ACCESS_KEY` | 空 | Secret Key |
| `S3_BUCKET_NAME` | 空 | 桶名 |
| `S3_BASE_PATH` | 空 | 统一前缀，便于按环境/项目隔离 |
| `S3_PUBLIC_BASE_URL` | 空 | **浏览器可达**的素材直链基址 |
| `S3_ADDRESSING_STYLE` | `path` | 自建服务必须用 `path`；容器 DNS 无法解析虚拟主机名 |

> 素材直链直出依赖桶的公共读策略或签名 URL，`S3_PUBLIC_BASE_URL` 未配置时
> 前端无法展示已上传的图片。

## 生成接口默认参数（可选）

用于「演员/角色/道具/场景/服装/镜头帧图片生成任务」与 `/film/generated_video`：

| 变量 | 说明 |
| --- | --- |
| `IMAGE_API_PROVIDER` / `IMAGE_API_BASE_URL` / `IMAGE_API_KEY` | 图片生成默认供应商与凭据 |
| `VIDEO_API_PROVIDER` / `VIDEO_API_BASE_URL` / `VIDEO_API_KEY` | 视频生成默认供应商与凭据 |

> 多数场景下**不需要**设置这些：供应商凭据在「模型管理」界面按 Provider 记录维护，
> 并以密文落库。

## Go 控制面

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `GO_API_ADDR` | `127.0.0.1:8001` | 监听地址 |
| `GO_API_ENV_FILE` | `backend/.env` | 环境文件路径（与 Python 共用同一份） |
| `PYTHON_UPSTREAM` | `http://127.0.0.1:8000` | 写方法回落与文件下载代理的 Python 上游 |
| `APP_ENV` | `dev` | 运行环境标识 |

## Compose 部署

`deploy/compose/.env` 额外用到：

| 变量 | 说明 |
| --- | --- |
| `MYSQL_ROOT_PASSWORD` / `MYSQL_PASSWORD` | 数据库密码 |
| `MYSQL_DATABASE` / `MYSQL_USER` | 库名与账号 |
| `MYSQL_PORT` | 宿主机端口（被占用时改这里） |
| `REDIS_PORT` / `REDIS_DB` | Redis 端口与库号 |
| `RUSTFS_ACCESS_KEY` / `RUSTFS_SECRET_KEY` | 本地对象存储凭据 |
| `RUSTFS_PORT` / `RUSTFS_CONSOLE_PORT` | 对象存储 API 与控制台端口 |
| `BACKEND_URL` | 注入前端 `/env.js`，浏览器访问后端用的地址 |

## 前端运行时配置

前端与后端分端口部署时，运行时地址通过 `front/public/env.js` 注入：

```js
window.__ENV = { BACKEND_URL: "http://localhost:8000" };
```

