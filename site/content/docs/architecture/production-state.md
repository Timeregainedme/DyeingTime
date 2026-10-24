---
title: "生产环境当前状态"
description: "Production Internal 的服务拓扑、发布目录、迁移、权限、额度、备份、回滚与已知风险。"
weight: 21
---

> 运维快照，随部署更新。架构原理见
> [Go 控制面](/docs/architecture/go-control-plane/) 与
> [多租户与工作区隔离](/docs/architecture/workspace-multitenancy/)。

## 服务拓扑

| 服务 | systemd unit | 端口 | 说明 |
|---|---|---|---|
| Nginx | `nginx` | 80 / 443 / 9443 | SPA + API 反向代理 + HTTPS |
| Production API | `dyeingtime-api` | 127.0.0.1:8002 | FastAPI |
| Staging API | `dyeingtime-staging-api` | 127.0.0.1:8021 | 独立测试库；仅本机 7802 UI |
| Celery default | `dyeingtime-celery` | — | 默认队列，并发 1 |
| Celery image | `dyeingtime-celery-image` | — | image 队列，并发 2 |
| Celery video | `dyeingtime-celery-video` | — | video 队列，并发 1 |
| Go control plane | `dyeingtime-go` | 127.0.0.1:8001 | 仅 `/health` 与 `/api/v1/ready`；读 `/etc/dyeingtime/backend.env` |
| MySQL backup | `dyeingtime-backup.timer` | — | 每日 19:00 UTC |

## 发布目录

```text
/srv/dyeingtime/releases/v2-internal-beta.3   # 当前 release（01b5564）
/srv/dyeingtime/current -> releases/v2-internal-beta.3
/srv/dyeingtime/previous -> releases/v2-internal-beta.2   # 上一个已验证 release
```

运行代码、venv、front dist 都从 `current` 读取。`/srv/dyeingtime` 不再直接对外服务，只用于回滚。

## 配置来源

| 文件 | 用途 | 权限 |
|---|---|---|
| `/etc/dyeingtime/backend.env` | Production API / Worker | `640 root:ubuntu` |
| `/etc/dyeingtime/staging.env` | Staging API | `640 root:ubuntu` |

关键变量：`DATABASE_URL`、`JWT_SECRET`、`SECRETS_KEY`、`S3_*`、`GENERATION_TEST_QUOTA_*`。

**`SECRETS_KEY` 轮换会导致既有 provider API Key 无法解密**；改动前必须重新录入供应商密钥。

## 数据库与迁移

- 根 EBS 已扩至 50 GiB（客户机可见 48G ext4，使用率约 32%）；AWS `DescribeVolumes` 仍无权限，云侧卷类型/快照需控制台复核。
- RustFS 已迁至根盘 `/data/rustfs0`（约 180K，仅 healthcheck），生产媒体实际走 R2。
- Production 数据库：本机 MySQL `dyeingtime`。
- Staging 数据库：`dyeingtime_staging`，独立 Redis DB `2`。
- 已执行迁移：034–050（项目生成配置、风格锁定、剧本、资产版本、场次/分镜、参考绑定、额度、批次、审核、音色样本、request_key、生产预算）。
- `schema_migrations` 记录已执行文件；发布脚本只对未记录的文件执行，重复发布不会重跑 `ALTER TABLE`。
- 迁移前备份：`/srv/dyeingtime-backups/`。
- 迁移后执行 `init_db` 补齐 ORM 表。
- 恢复演练：备份导入独立库后，用户/项目/镜头/文件计数一致。

迁移是加列/加表为主；**代码回滚不等于数据库回滚**。不可逆变更前必须备份并走恢复演练。

## Nginx 分流

P10 起所有业务 API 统一走 Python `8002`：

- `/api/v1/*` → Python
- `/health` → Go（进程存活）
- `/api/v1/ready` → Go（DB ready）
- `/api/v1/health` → Python
- `/static/*` → `/srv/dyeingtime/current/front/dist/static/`
- `/env.js` → Nginx 动态生成，注入 `BACKEND_URL=""`、`GENERATION_QUOTA_SCOPE="production-internal"`
- `/api/v1/studio/dashboard` → 首页创作工作台聚合（项目 / 章节 / 镜头 / 任务 / 待审核），只读、按工作区隔离

旧 Go 只读切流已收回。原因：精确/正则 location 会把 POST/PATCH/DELETE 也转给 Go，项目创建返回 503。Go 进程保留，仅用于探针。

## 权限与安全

- 公开注册关闭；Google 登录由 `GOOGLE_ALLOWED_EMAILS` 控制。
- 业务 API 全部要求登录；项目/章节/镜头/文件/任务走 workspace scoping。
- viewer 只读；editor 可写；模型供应商/模型/全局设置写接口要求 workspace admin。
- 文件下载 API 要求登录和工作区归属；匿名 401、跨工作区 404。
- QA 账号已停用，测试项目已删除。
- 首页只读聚合 `GET /studio/dashboard`；`can_edit` 仅用于前端隐藏按钮，后端写接口仍独立鉴权。
- `.env` 权限 600 / 640，未提交 Git；历史跟踪文件中未发现真实 API Key。

**剩余安全阻塞**：Cloudflare R2 媒体仍通过 `pub-*.r2.dev` 公共读 URL 提供；API 下载鉴权不能阻止持有直链的人访问对象。需 Cloudflare 账户级 Token 关闭公共访问并切换签名 URL/应用代理。

## 额度与并发

- Production scope：`production-internal`
  - 图片 100
  - 视频 20
  - 音频 5000 字
- 隔离验收 scope：`v2-acceptance`（图片 2/40、视频 5/8、音频 17/1000）。P10-B 图片与 TTS 真实调用只发生在这里。
- `v2-acceptance` 测试额度与生产独立，不继承 8 次测试额度。
- 生产项目 `video_concurrency = 1`。
- 生产部署本身未发起付费生成。

## 备份与恢复

```bash
# 手动备份
sudo python3 /usr/local/sbin/dyeingtime-backup-db.py

# 恢复（必须先停 API/Worker，并确认 --yes）
sudo systemctl stop dyeingtime-api dyeingtime-celery dyeingtime-celery-image dyeingtime-celery-video
sudo python3 /srv/dyeingtime/current/deploy/scripts/restore_db.py \
  /srv/dyeingtime-backups/dyeingtime-YYYYMMDDTHHMMSSZ.sql.gz --yes
sudo systemctl start dyeingtime-api dyeingtime-celery dyeingtime-celery-image dyeingtime-celery-video
```

备份目录 `/srv/dyeingtime-backups/`，保留 14 天；SHA256 一并保存。每次数据库备份会自动上传 R2 `backups/db/`，避免备份只存在同一台 EC2。

## 发布与回滚

```bash
# 发布
sudo /srv/dyeingtime/releases/v2-internal-beta.1/deploy/scripts/deploy_release.sh \
  /srv/dyeingtime/releases/v2-internal-beta.1

# 回滚
sudo /srv/dyeingtime/releases/v2-internal-beta.1/deploy/scripts/rollback_release.sh
```

发布脚本会先备份数据库，拒绝在有运行中视频任务时发布；切换 `current` 后重启 API/Worker，最后复制 Nginx 配置并校验外部探针。

## 巡检

```bash
sudo /usr/local/sbin/dyeingtime-health-check.sh
sudo /usr/local/sbin/dyeingtime-health-check.sh --quiet
```

检查服务/探针/磁盘/内存/5xx/备份时效，并输出 release / 备份 / 日志目录容量。磁盘阈值为 75% 预警、85% 高优先级、90% 失败。当前约 82%，属于已知容量告警。

## 已知风险

| 风险 | 说明 |
|---|---|
| R2 公共媒体 | 直链可被持有 URL 的人访问；需关闭 R2 公共访问并改签名 URL |
| 根盘 32% / 50 GiB | 扩容已完成；AWS API 仍无 DescribeVolumes 权限，云侧卷信息需控制台复核 |
| 单机 | MySQL/Redis/API/Worker 同机，无高可用 |
| Go 切流已收回 | 仅保留 health/ready；恢复切流前必须解决写方法 503 与审计 |
| 平台管理员 | 目前使用 workspace admin/owner，不是独立平台角色 |
| 生产真实生成 | 图片/TTS 已在隔离验收库真实验证，生产未付费调用；视频质量由用户 L4 判断 |
| 文本模型解析 | 隔离验收已用免费 `beam-free` 完成真实解析；生产 `script_parse_runs` 仍为 0 |
| 分镜规划质量 | 免费模型场次切分不合格，需更强模型或提示词改进 |
