# P10-A 公司内部 Beta 部署记录

> 状态：**Production Internal 已启动并可访问；内部 Beta 可用。**
>
> 访问地址：`https://tim.run.place/`
>
> 注意：对象存储当前仍通过 Cloudflare R2 公共开发域名提供媒体直链，属于已知安全遗留项；不能宣称“媒体私有访问”已完全达标。

## 1. 主机与资源

| 项 | 值 |
| --- | --- |
| 主机 | AWS EC2 `ip-172-31-2-3`，公网 EIP `18.225.232.63` |
| CPU | 2 vCPU |
| 内存 | 3.7 GiB + 2 GiB swap |
| 磁盘 | 19 GB，部署后约 2.6 GB 可用（87% 使用） |
| OS | Ubuntu 24.04 |
| 数据库 | 本机 MySQL，`dyeingtime` 约 222 MB |
| Redis | 本机 Redis 6379 |
| 对象存储 | Cloudflare R2 `ai-jellyfish`（当前公共读 URL） |
| HTTPS | Let's Encrypt `tim.run.place`，有效期至 2027-01-18 |

视频生成主要成本在供应商侧，不在本机 GPU；本机只负责 API、Celery 轮询、下载与回存。

## 2. 部署拓扑

```text
Browser
  → Nginx :443 (Let's Encrypt)
      → /                 /srv/dyeingtime/current/front/dist
      → /api/v1/*         FastAPI 127.0.0.1:8002
      → /health           Go 127.0.0.1:8001
      → /api/v1/ready     Go 127.0.0.1:8001 (DB ready)
  → FastAPI 8002
      → MySQL 127.0.0.1:3306/dyeingtime
      → Redis 127.0.0.1:6379/0
      → Cloudflare R2
  → Celery: default/image/video queues
```

发布目录：

```text
/srv/dyeingtime/releases/v2-internal-beta.1   # 当前 release
/srv/dyeingtime/current -> releases/v2-internal-beta.1
/srv/dyeingtime/previous -> /srv/dyeingtime    # 旧 main 版本，用于回滚
```

运行代码只从 `current` 读取；`/srv/dyeingtime` 旧目录保留作回滚，不再直接对外提供服务。

## 3. 服务与端口

| 服务 | 单元 | 端口/队列 |
| --- | --- | --- |
| Nginx | `nginx` | 80/443/9443 |
| FastAPI Production | `dyeingtime-api` | 127.0.0.1:8002 |
| FastAPI Staging | `dyeingtime-staging-api` | 127.0.0.1:8021 + 7802 本地 UI |
| Celery default | `dyeingtime-celery` | 默认队列，并发 1 |
| Celery image | `dyeingtime-celery-image` | image，并发 2 |
| Celery video | `dyeingtime-celery-video` | video，并发 1 |
| Go control plane | `dyeingtime-go` | 127.0.0.1:8001，仅 health/ready |
| MySQL backup timer | `dyeingtime-backup.timer` | 每日 19:00 UTC |

Go 旧控制面不再承接业务写接口。P10 发现旧的精确/正则 location 会把 POST 项目创建转给 Go，导致 503；现在所有业务 API 统一回 Python，Go 只保留 `/health` 与 `/api/v1/ready`。

## 4. 环境隔离

| 环境 | 数据库 | Redis | 前端 | 付费生成 |
| --- | --- | --- | --- | --- |
| Development | 本地 `p8_e2e` | 本地 6380 | Vite 7801 | 仅授权测试 |
| Staging | `dyeingtime_staging` | Redis DB 2 | `127.0.0.1:7802` | 额度 0，默认禁止 |
| Production Internal | `dyeingtime` | Redis DB 0 | `https://tim.run.place` | `production-internal` 预算 |

Staging 配置：`/etc/dyeingtime/staging.env`；生产配置：`/etc/dyeingtime/backend.env`（640，root:ubuntu）。

## 5. 数据库迁移

- 迁移前备份：`/srv/dyeingtime-backups/dyeingtime-20261024T053139Z-pre-migration.sql`
- 在 `dyeingtime_staging` 重放 034–050 成功。
- 生产执行 034–050，随后 `init_db` 创建缺失 ORM 表。
- 迁移后备份：`/srv/dyeingtime-backups/dyeingtime-20261024T054612Z.sql.gz`
- 恢复演练：将备份导入 `dyeingtime_restore_test`，用户/项目/镜头/文件计数与生产一致，演练后删除测试库。

生产数据保留：

- 迁移前：2 用户、3 项目、19 镜头、33 文件、57 任务。
- 迁移后原有 3 个项目仍存在，数据未清空。

## 6. 权限与安全

已验证：

- 无公开注册接口。
- 未登录访问业务 API → 401。
- `viewer` 创建项目/供应商 → 403。
- `admin/owner` 创建项目、Chapter、Shot → 成功。
- 跨工作区访问项目 → 404。
- 文件下载匿名 → 401；工作区 viewer → 302；其他工作区 → 404。
- 模型供应商/模型/全局设置的写接口已加 `require_admin`。
- QA 测试账号 `qa-p10-admin` / `qa-p10-employee` 已停用。
- `.env` 权限 600；`/etc/dyeingtime/*.env` 640 root:ubuntu。
- Git 跟踪文件中未发现真实 API Key；历史中的 `sk-ml-` 仅为占位/说明文本。

仍然存在的安全遗留：

- **R2 媒体直链是公共读**。API 下载入口已要求登录，但数据库 `thumbnail` 指向的 `pub-*.r2.dev` 仍可被持有 URL 的人直接访问。要彻底满足“私有对象存储”，需要 Cloudflare R2 账户级权限/API Token，关闭公共访问并切换到签名 URL 或应用代理。
- `.env` 中的数据库密码在本次排查中曾出现在本地终端输出；建议后续轮换数据库密码并同步更新 `/etc/dyeingtime/backend.env`。
- 平台级管理员仍是工作区 admin/owner，不是独立平台角色；单工作区内部 Beta 可接受，多工作区前需补独立权限。

## 7. 额度与费用

Production Internal 独立额度：

| 类型 | 上限 | 已消耗 | 已预留 | 剩余 |
| --- | ---: | ---: | ---: | ---: |
| 图片 | 100 | 0 | 0 | 100 |
| 视频 | 20 | 0 | 0 | 20 |
| 音频 | 5000 | 0 | 0 | 5000 |

- `v2-acceptance` 测试额度与生产独立；生产未继承 8 次测试额度。
- 生产项目 `video_concurrency` 已设为 1。
- 生产本次部署未发起新的真实图片/视频/音频生成调用。
- 供应商积分仍为 `5623.02`（P9-D2 后）；生产生成前应在管理员面板重新确认余额。

## 8. 备份与恢复

- 每日备份：`dyeingtime-backup.timer` → `dyeingtime-backup.service`。
- 备份目录：`/srv/dyeingtime-backups/`，保留 14 天。
- 最新备份带 SHA256；环境文件另行备份为 600。
- 恢复命令见 `deploy/scripts/restore_db.py`，必须显式 `--yes`。
- 备份恢复演练已通过（计数一致）。

## 9. 发布与回滚

发布：

```bash
cd /srv/dyeingtime/releases/v2-internal-beta.1
sudo deploy/scripts/deploy_release.sh /srv/dyeingtime/releases/v2-internal-beta.1
```

回滚：

```bash
sudo /srv/dyeingtime/releases/v2-internal-beta.1/deploy/scripts/rollback_release.sh
```

P10 已实际测试回滚到旧 `/srv/dyeingtime`：旧 API 在 8002 启动后健康恢复。回滚脚本最初健康等待过短，已修复为 30 次轮询。

数据库迁移是加列/加表为主；代码回滚不等于数据库回滚。若回滚后出现新字段不兼容，必须使用备份恢复，而不是清空生产库。

## 10. 验收证据

- 生产登录页：`/tmp/opencode/p10-prod-login.png`
- 管理员项目列表：`/tmp/opencode/p10-prod-admin-projects.png`
- 管理员工作台：`/tmp/opencode/p10-prod-admin-workbench.png`
- 员工工作台：`/tmp/opencode/p10-prod-employee-workbench.png`
- QA 新项目/镜头页：`/tmp/opencode/p10-prod-qa-shot.png`
- 生产额度显示：`/tmp/opencode/p10-prod-quota.png`
- 健康检查：

```text
nginx active
dyeingtime-api active
dyeingtime-celery active
dyeingtime-celery-image active
dyeingtime-celery-video active
dyeingtime-go active
/health 200
/api/v1/ready database=ok
Python /health 200
```

- Celery ping：`default@dyeingtime / image@dyeingtime / video@dyeingtime` 均 pong。
- QA 项目已删除；QA 账号已停用。

## 11. 已知问题

1. R2 媒体公共直链（安全阻塞项）。
2. 磁盘 87%（2.6G 可用）；媒体不在本机，但备份、release、日志会持续增长。
3. 单机 MySQL/Redis/API/Worker；无高可用。
4. Go 控制面仅用于探针，业务 API 全部 Python；未来若恢复 Go 切流，必须先解决写方法 503 与审计。
5. 生产真实生成尚未做付费验收；L4 视频质量仍由用户判断。
6. 旧 `/srv/dyeingtime` 回滚版本的依赖已移除 `front/node_modules`，但前端 dist 保留；后端 venv 保留。

## 12. 发布标识

- Release tag：`v2-internal-beta.1`
- Tag commit：`8585d99`
- 分支：`refactor/v2-worktree-foundation`
- CI：
  - V2 Browser E2E `40068052012` success
  - V2 Real Backend Browser E2E `40068051925` success
- 工作区：clean

## 13. 最终上线状态

**Production Internal 已上线（内部 Beta），业务页面和 API 可访问；媒体对象存储私有化未完成，是剩余安全阻塞项。**
