---
title: "P10-B 内部 Beta 2 与真实验收"
description: "首页创作工作台、图片与 TTS 真实验收、AWS 扩容阻塞、可靠性整改与 v2-internal-beta.2 发布记录。"
weight: 4
---

> 状态：**已发布 `v2-internal-beta.2`（Commit `60c5a11`）。**
>
> AWS 根 EBS 扩容仍阻塞；其余 P10-B 任务已完成或已明确标注未验证范围。

## 1. 交付

| 项 | 结果 |
| --- | --- |
| 首页 | `/projects` 改为创作工作台，真实聚合数据 |
| 图片 | PIX `gpt-image-2.5-flare`，2 张真实生成 |
| TTS | 优云智算 `IndexTTS-2.5`，1 段真实生成 |
| 阻断缺陷 | 修复 TTS 执行器缺少额度函数导入导致的 NameError |
| 可靠性 | 回滚目标修正、迁移追踪、异地 DB 备份、DB 密码轮换 |
| 发布 | `v2-internal-beta.2`，生产与 Staging 均已切换 |

## 2. AWS 阻塞

- Account `238224495259`，Region `us-east-2`，Instance `i-08ef234188645963d`，根卷 `vol-0b1e3735220a28475`。
- 实例角色 `atk-ec2-ssm-role` 无 `DescribeVolumes / CreateSnapshot / ModifyVolume / SSM` 权限。
- 因此未创建快照、未修改容量、未扩容文件系统；根分区仍 20 GiB。
- 最小授权策略与执行步骤见 `docs/p10-internal-beta/p10-b-acceptance.md` 第 2 节。
- 通过清理缓存把磁盘从 87% 降到 82%，属于临时缓解。

## 3. 首页实现

- 新增 `GET /api/v1/studio/dashboard`：一次返回项目、章节、镜头计数、最近任务、待审核事项。
- 统计口径集中在服务层；阶段状态机仍由前端唯一计算。
- 待审核 = 有成功视频任务、不是当前采纳版本、且未审核的镜头。
- 小屏侧栏收敛为图标栏；深色模式、1366–1920、平板、手机均验证。

## 4. 真实验收边界

- 图片与 TTS 在隔离验收库 `p8_e2e` 执行，额度 `v2-acceptance`；生产未发起付费生成。
- 生产图片/TTS 只能标为“隔离环境真实验证通过，生产待验证”。
- 剧本解析只完成上传与不收费回放；真实文本模型调用未授权。
- 未新增 H3 视频付费调用。

## 5. 后续

1. 取得 AWS 授权后执行 50 GiB 扩容。
2. 授权一次短剧本真实解析。
3. 以真实项目跑 P10-C 全流程试生产。
4. 继续清理 ESLint 历史错误与单机高可用风险。
