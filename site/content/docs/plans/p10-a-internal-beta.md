---
title: "P10-A 公司内部 Beta 上线"
description: "Production Internal 部署拓扑、迁移、权限、费用、备份、回滚、验收证据与剩余安全阻塞项。"
weight: 3
---

> 状态：**Production Internal 已启动并可访问：`https://tim.run.place/`。**
>
> 内部 Beta 可用，但对象存储媒体私有访问尚未完成，不能宣称安全基线全部达标。

## 1. 部署结果

| 项 | 值 |
| --- | --- |
| 域名 | `https://tim.run.place/` |
| 发布目录 | `/srv/dyeingtime/releases/v2-internal-beta.1` |
| 当前链接 | `/srv/dyeingtime/current` |
| API | `127.0.0.1:8002` |
| Staging | `127.0.0.1:7802`（仅本机） |
| 数据库 | 本机 MySQL `dyeingtime` |
| 对象存储 | Cloudflare R2 |
| HTTPS | Let's Encrypt，有效期至 2027-01-18 |
| 资源 | 2 vCPU / 3.7 GiB / 19 GB，磁盘约 87% |

## 2. 发布方式

发布目录是不可变 checkout；`current` 是原子 symlink。旧 `/srv/dyeingtime` 保留为 `previous`。

```bash
sudo deploy/scripts/deploy_release.sh /srv/dyeingtime/releases/v2-internal-beta.1
sudo deploy/scripts/rollback_release.sh
```

P10 已实际测试回滚：旧 release 在 8002 启动后健康恢复。回滚脚本的健康等待已修正为 30 次轮询。

## 3. 数据库

- 已在 staging 重放 034–050。
- 生产执行 034–050 + `init_db`。
- 迁移前备份、迁移后备份均在 `/srv/dyeingtime-backups/`。
- 恢复演练导入独立库，用户/项目/镜头/文件计数一致。
- 原有 3 个项目、2 个用户、19 个镜头保留。

## 4. 权限

已验证：

- 未登录业务 API → 401。
- viewer 创建项目/供应商 → 403。
- owner 创建项目、章节、镜头 → 成功。
- 跨工作区项目 → 404。
- 文件下载匿名 → 401；同工作区 viewer → 302；其他工作区 → 404。
- LLM Provider/Model/全局设置写接口要求 workspace admin。
- QA 账号已停用并删除测试项目。

## 5. 费用

Production Internal 独立额度：

| 类型 | 上限 | 已消耗 | 剩余 |
| --- | ---: | ---: | ---: |
| 图片 | 100 | 0 | 100 |
| 视频 | 20 | 0 | 20 |
| 音频 | 5000 | 0 | 5000 |

生产项目视频并发已设为 1；生产部署未发起付费生成；部署复核供应商余额为 total `5559.02` / reserved `104` / available `5455.02`，其中包含同账号其他非本会话任务。

## 6. 备份与巡检

- `dyeingtime-backup.timer` 每日 19:00 UTC 备份，保留 14 天。
- `deploy/scripts/health-check.sh` 检查服务、探针、磁盘、内存、5xx、备份时效。
- Celery default/image/video 三个 worker 均 ping 成功。

## 7. 已知阻塞/风险

1. **R2 公共媒体直链**：API 下载已鉴权，但 `thumbnail` 的 `pub-*.r2.dev` 仍可被持有 URL 的人直接访问；需要 Cloudflare 账户级 API Token 关闭公共访问并切换签名 URL/应用代理。
2. 磁盘 87%，备份/日志/release 会继续增长。
3. 单机 MySQL/Redis/API/Worker，无高可用。
4. 历史 Go 切流已收回：所有业务 API 走 Python；Go 仅 health/ready。
5. 生产真实付费生成尚未验收，视频质量仍由用户 L4 判断。

## 8. 验收证据

截图与部署记录：`docs/p10-internal-beta/`。

生产验证：

- 登录页、管理员项目列表、管理员工作台、员工工作台均加载。
- 生产额度显示 `video 余额 20`，不再显示测试额度 8。
- `https://tim.run.place/health` → 200
- `https://tim.run.place/api/v1/ready` → `database:ok`
- `https://tim.run.place/api/v1/health` → 200
