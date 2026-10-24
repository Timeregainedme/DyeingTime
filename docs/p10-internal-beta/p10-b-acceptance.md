# P10-B 验收记录

> 版本：`v2-internal-beta.2`
>
> 生产：`https://tim.run.place/`
>
> 代码基线：`60c5a11`（`v2-internal-beta.2` 标签指向该 Commit）；验收文档提交在其后。

## 1. 总体状态

| 任务 | 结果 |
| --- | --- |
| P10-B1 AWS 根 EBS 扩容 | **阻塞**：实例角色无 EC2/SSM 权限；已给出最小授权策略与执行步骤 |
| P10-B2 首页创作工作台 | **完成**：生产已上线，真实聚合数据 |
| P10-B3 AI 图片真实验收 | **完成**：PIX `gpt-image-2.5-flare`，2 张真实图片 |
| P10-B4 TTS 真实验收 | **完成**：优云智算 `IndexTTS-2.5`，1 段真实语音；修复 1 个阻断性缺陷 |
| P10-B5 剧本解析核查 | **部分完成**：上传与不收费回放通过；真实文本模型调用未授权，未执行 |
| P10-B6 全功能盘点 | **完成**：见第 7 节 |
| P10-B7 可靠性 | **完成**：回滚目标修正、迁移追踪、异地 DB 备份、凭据轮换 |
| P10-B8 Staging 验收 | **完成** |
| P10-B9 回归 | **完成**：后端 689 passed、前端 53 passed、CI 双 E2E 通过 |
| P10-B10 Beta 2 发布 | **完成**：`v2-internal-beta.2` 已部署并验证 |

## 2. AWS 扩容（阻塞）

### 2.1 已核实的资源关系

| 项 | 值 | 证据 |
| --- | --- | --- |
| Account | `238224495259` | STS `get-caller-identity` |
| Region / AZ | `us-east-2` / `us-east-2a` | IMDSv2 |
| Instance | `i-08ef234188645963d` | IMDSv2 + STS 角色会话名 |
| 实例角色 | `atk-ec2-ssm-role` | STS ARN |
| 根设备（云侧） | `/dev/sda1` | IMDS `block-device-mapping/root` |
| 根卷（NVMe by-id） | `vol-0b1e3735220a28475` | `/dev/disk/by-id/nvme-Amazon_Elastic_Block_Store_vol0b1e3735220a28475` |
| 根盘 / 分区 | `nvme0n1` → `nvme0n1p1` ext4 `/` | `lsblk` / `findmnt` |
| 当前容量 | 20 GiB（可用 19G） | `df -hT` |
| 数据盘 | `nvme1n1` 20G xfs `/data/rustfs0`（**未触碰**） | `lsblk` |

### 2.2 阻塞原因

实例角色只允许 STS，以下动作全部 `UnauthorizedOperation` / `AccessDenied`：

```text
ec2:DescribeInstances
ec2:DescribeVolumes
ec2:DescribeVolumesModifications
ec2:CreateSnapshot
ec2:ModifyVolume
ssm:DescribeInstanceInformation
ssm:ListDocuments
```

因此**没有创建快照、没有提交 ModifyVolume、没有扩容文件系统**。不能把“已计划”说成“已扩容”。

### 2.3 最小授权策略

由 AWS 管理员附加到 `atk-ec2-ssm-role`（或提供具备同等权限的临时凭据）：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DescribeForRootVolume",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeVolumes",
        "ec2:DescribeVolumesModifications"
      ],
      "Resource": "*"
    },
    {
      "Sid": "SnapshotAndResizeRootVolume",
      "Effect": "Allow",
      "Action": [
        "ec2:CreateSnapshot",
        "ec2:CreateTags",
        "ec2:ModifyVolume"
      ],
      "Resource": "arn:aws:ec2:us-east-2:238224495259:volume/vol-0b1e3735220a28475"
    },
    {
      "Sid": "SnapshotResource",
      "Effect": "Allow",
      "Action": [
        "ec2:CreateSnapshot",
        "ec2:CreateTags"
      ],
      "Resource": "arn:aws:ec2:us-east-2::snapshot/*"
    }
  ]
}
```

### 2.4 授权后的执行顺序

```bash
# 1. 复核资源与卷类型/IOPS/吞吐
# 2. 创建快照并等待 completed
# 3. ModifyVolume Size=50（保持 VolumeType，不提高 IOPS/吞吐）
# 4. 等待 modification state = completed/optimizing
# 5. 在线扩展分区与文件系统（不要格式化）
growpart /dev/nvme0n1 1
resize2fs /dev/nvme0n1p1
# 6. df -hT / lsblk 复核；服务与数据健康检查
```

费用（us-east-2 gp3 公开价）：新增 30 GiB × $0.08/GiB-月 = **约 $2.40/月**；快照按实际增量计费。未改变 IOPS/吞吐档位。由于无法调用 `DescribeVolumes`，**卷类型未能由 API 确认**，执行前必须复核。

### 2.5 本次可独立完成的缓解

清理开发缓存（uv/pnpm/apt）后：

| 时间点 | 使用率 | 可用 |
| --- | ---: | ---: |
| 扩容前 | 87% | 2.6 GB |
| 清理后 | 81–82% | 3.6 GB |

这是临时缓解，不替代 50 GiB 扩容。

## 3. 首页创作工作台

### 3.1 结构

- 顶部：`创作工作台` + 副标题 + 刷新 + 新建项目（viewer 隐藏）。
- 四个真实统计卡片：项目总数、待审核镜头、正在生成任务、已采纳视频。
- `继续创作`：最近编辑的前 3 个项目，展示阶段、镜头就绪度、下一步。
- `待审核事项`：视频候选 / 分镜规划 / 镜头信息确认，全部带真实入口。
- `最近任务`：最近 8 条任务，点击打开真实任务中心浮层。
- `全部项目`：搜索、7 类筛选、3 种排序、项目卡片主操作 + 更多菜单。

### 3.2 数据来源与口径

新增只读接口 `GET /api/v1/studio/dashboard`（`require_viewer`，按 `ctx.workspace_id` 隔离），一次返回：

| 字段 | 口径 |
| --- | --- |
| `project_count` | 当前工作区项目数 |
| `pending_review_shots` | 有成功视频任务、该任务不是当前采纳版本、且无审核记录或 `unrated` 的镜头数 |
| `running_tasks` | `pending/running/streaming`，跨全部任务类型 |
| `adopted_videos` | `shots.generated_video_file_id` 非空的镜头数 |
| `pending_reviews` | 只返回有真实业务入口的三类事项 |
| `recent_tasks` | 最近 8 条任务，经 `generation_task_links` 解析项目 |

阶段状态机仍由前端 `getChapterPreparationState` 唯一计算，后端只提供章节字段，避免两套规则漂移。
章节分镜数直接取 `shots` 真实行数（`Chapter.storyboard_count` 历史值可能过期）。

### 3.3 截图

| 场景 | 文件 |
| --- | --- |
| 生产 1440 | `docs/p10-internal-beta/screens/p10b-prod-home.png` |
| 1366 | `docs/p10-internal-beta/screens/p10b-home-1366.png` |
| 1600 | `docs/p10-internal-beta/screens/p10b-home-1600.png` |
| 1920 | `docs/p10-internal-beta/screens/p10b-home-1920.png` |
| 深色模式 | `docs/p10-internal-beta/screens/p10b-home-dark.png` |
| 手机 390 | `docs/p10-internal-beta/screens/p10b-home-mobile.png` |
| viewer 只读 | `docs/p10-internal-beta/screens/p10b-home-viewer.png` |
| 生产任务中心 | `docs/p10-internal-beta/screens/p10b-prod-taskcenter.png` |

响应式验证：1366 / 1440 / 1600 / 1920 / 834 平板 / 390 手机均无横向溢出；小屏侧栏收敛为图标栏。

## 4. 图片真实验收

### 4.1 链路

| 项 | 值 |
| --- | --- |
| 环境 | 隔离验收库 `p8_e2e`，额度 scope `v2-acceptance` |
| 供应商 | PIX（`https://pix.token6688.com`） |
| 模型 | `gpt-image-2.5-flare`（`3b916316-9872-4e5d-933b-dd4108f636e1`） |
| 入口 | `POST /api/v1/studio/image-tasks/assets/{type}/{id}/image-tasks`、`.../characters/{id}/image-tasks` |
| Worker | Celery `image` 队列 |
| 参数 | 1024×1024，1K，1:1 |

### 4.2 任务与产物

| # | 任务 ID | 供应商任务 ID | FileItem | 对象 key | 大小/尺寸 |
| --- | --- | --- | --- | --- | --- |
| 1 场景 | `5def3ec0f4ec4e9e944fd6b7352057ce` | `task-1792826645493-21925` | `c1dfedd3-8ca4-45ed-8709-1e8fa493c433` | `generated-images/scene_image/1/b1dfbd0b48204931a20a0e4a269d2b53.jpg` | 302,050 B / 1024×1024 JPEG |
| 2 角色 | `19b0ade8a77c434fb55d73c52699e12c` | `task-1792826752746-22025` | `eb5dcc94-60eb-407c-bad7-90cb66d22d12` | `generated-images/character_image/1/0eee02a7f55c4ad3bfdb5619c55ba6f6.jpg` | 230,103 B / 1024×1024 JPEG |

证据文件：

- `docs/p10-internal-beta/media/p10b-image-scene.jpg`
- `docs/p10-internal-beta/media/p10b-image-character.jpg`

### 4.3 持久化与关联

- R2 公共直链返回 `200 image/jpeg`。
- 浏览器 `<img>` `naturalWidth/naturalHeight = 1024×1024`。
- `scene_images.file_id` / `character_images.file_id` 已回填。
- `file_usages`：`project=p-e2e`，`usage_kind=asset_image` / `character_image`。
- 刷新后仍可访问。
- 参考图准备度：镜头 `s-p9d2-continuity` 在 `reference` 模式下解析到 **2 张**参考图，证明生成图片可作为 H3 参考输入。

### 4.4 质量与费用

- 场景图：玻璃隔断、走廊、沙发、暖色台灯均符合 Prompt；无多余人物。
- 角色图：短发、白衬衫、深色西装、办公室背景符合；耳部饰品有轻微重影（可接受，记为质量观察）。
- 额度：`image` 0 → **2 / 40**。
- 供应商计费：第二张返回 `actual_cost_micro_usd=5258`（约 $0.0053）；第一张的 billing 日志被 worker 重启覆盖，未留证。

## 5. TTS 真实验收

### 5.1 链路

| 项 | 值 |
| --- | --- |
| 供应商 | 优云智算（`https://cp.compshare.cn`） |
| 模型 | `IndexTTS-2.5`（`2967f4f3-ef1c-4033-b2a5-aa3e5ecde7b8`） |
| 音色 | 晚晴（preset，`01a0a95a-52fa-7129-bbd0-8a622a37111b`） |
| 文本 | `你先听我解释，事情不是你想的那样。`（17 字） |
| 入口 | `POST /api/v1/studio/audio-tasks/speech` |

### 5.2 缺陷与修复

首次调用 `ff2706f056134049b88c4fcbf74f6c41` 失败：

```text
NameError: name 'reserve_for_task' is not defined
```

`audio_task_runner.py` 使用了 `reserve_for_task` / `settle_task` 却没有导入，导致**所有 TTS 任务在额度预留前就失败**，失败路径再次 `NameError`，任务状态与额度也无法正确落库。这是此前“TTS 已部署但从未真实验收”的直接后果。

修复：补充 `from app.services.studio.generation_quota import reserve_for_task, settle_task`，并新增回归测试 `test_audio_runner_binds_quota_helpers`。

修复后重试成功（该失败在调用供应商前终止，无供应商费用）。

### 5.3 产物

| 项 | 值 |
| --- | --- |
| 任务 ID | `e4d4cb5a40644d1ab1721c776c06127c` |
| 供应商任务 ID | `01a16cd1-f9a5-7030-82d9-1e0920c9c0d0` |
| FileItem | `6207bb83-54a8-4abf-b8d5-cc454e21b939` |
| 对象 key | `generated-audios/standalone/e4d4cb5a40644d1ab1721c776c06127c/55057d3c3fb546eca2e938b39f00ef9a.wav` |
| 格式 | WAV PCM 16-bit mono 22050 Hz |
| 时长/大小 | 3.390 s / 149,548 B |
| 证据 | `docs/p10-internal-beta/media/p10b-tts.wav` |

### 5.4 验证

- 供应商请求体确认文本、`language=ZH`、`voice.source=preset`、`voice_id` 正确传递。
- 供应商返回 `point_cost=0.15`、`point_status=consumed`。
- R2 直链 `200 audio/wav`；浏览器 `<audio>` `readyState=4`、`duration=3.390`、可播放。
- `file_usages`：`project=p-e2e`，`usage_kind=generated_audio`。
- 额度：`audio` 0 → **17 / 1000**（按字符数精确计费）。
- ASR 辅助（本地 faster-whisper，不产生费用）：
  - base：`你先替我解释事情不是你想的那样`
  - tiny：`你先挺我解释事情不是你想的那样`
  - 与原文差异集中在第二个字“听”；两个模型给出不同字，判断更可能是 ASR 对短音频的误识别，但**必须由人工试听确认**，不能据此判定 TTS 发音正确。
- 未验证项：角色固定音色库、角色 `voice_description` 传递、H3 音频参考开关的真实视频效果（未新增 H3 付费调用）。

## 6. 剧本 AI 解析

| 项 | 状态 |
| --- | --- |
| 文本模型配置 | 生产默认 `deepseek-v4.1-flash`（OpenCode Go），fallback `minimax-m3` |
| 剧本上传 | **真实验证**：验收项目上传 165 字 `.md`，生成 v1（candidate、not_parsed） |
| 文档解析（docx/md） | 自动化测试通过 |
| 分块 / 候选合并 / 人工审核 / 确认 | 不收费回放测试通过（`tests/test_script_parse.py`，mock LLM） |
| 真实文本模型解析 | **未执行**：没有获得新的文本模型付费预算授权 |
| 生产解析历史 | `script_parse_runs` 为 0，生产从未执行过真实解析 |
| 版本覆盖保护 | 确认后才写正式数据；未确认结果不会覆盖章节原文 |

结论：解析链路的“结构、分块、候选、确认、回放”已验证；**真实模型调用仍是待授权项**，不能标记为完整通过。

## 7. 完整功能清单

状态定义：A=真实验证；B=自动化/回放通过但未真实付费调用；C=已实现未验证；D=有缺陷；E=未开发。

| 模块 | 计划目标 | 当前实现 | 入口 | 真实模型 | 浏览器 | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| 登录 / 会话 | 内部账号 | 本地 + Google 白名单，JWT | `/login` | — | ✅ | A |
| 权限 / 工作区 | 服务端隔离 | viewer/editor/admin/owner | 全部 API | — | ✅ | A |
| 项目 CRUD | 项目管理 | 创建/编辑/删除/搜索/筛选 | `/projects` | — | ✅ | A |
| 项目生成配置 | 模型与时长 | 项目级模型、时长、并发 | 工作台配置 | — | ✅ | A（配置） |
| 树状工作台 | 层级浏览 | 项目/剧本/资产/剧集/镜头 | `/projects/:id/workbench` | — | ✅ | A |
| 剧本上传 | docx/md | 版本化、候选、启用 | 工作台剧本 | — | ✅ | A |
| AI 剧本解析 | 结构化候选 | 分块 + 候选 + 确认 | 工作台剧本 | ❌ 未调用 | 部分 | B |
| 风格圣经 | 风格锁定 | 项目风格快照 | 工作台风格 | — | ✅ | A |
| 角色 / 场景 / 道具 / 服装 | 资产管理 | CRUD + 关联 | `/assets`、工作台 | — | ✅ | A |
| 资产版本 / 身份锁定 | 版本与一致性 | AssetVersion、identity lock | 资产详情 | — | ✅ | B |
| 图片生成 | 资产候选图 | PIX gpt-image-2.5 | 资产/角色 | ✅ 2 张 | ✅ | A |
| 图片候选采纳 | 人工选择 | 候选/采纳接口 | 资产详情 | — | 部分 | B |
| SceneGroup | 正式场次 | 场次 CRUD、镜头归属 | 工作台剧集 | — | ✅ | A |
| AI 分镜规划 | 候选镜头 | ShotPlanDraft/Candidate | 工作台 | ❌ 未调用 | ✅ | B |
| 分镜编辑 | 镜头详情/对白 | 完整编辑 | 镜头页 | — | ✅ | A |
| 参考图绑定 / Prompt 预览 | H3 输入 | 自动推荐 + 手工绑定 | 镜头页 | ✅ 解析 2 张 | ✅ | A |
| H3 视频生成 | 真实视频 | 5s / 768P / 9:16 | 镜头/批次 | ✅ 历史 7 条 | ✅ | A（质量待人工） |
| 批量任务 / 并发 | 队列与限流 | image/video/default 队列，视频并发 1 | 任务中心 | — | ✅ | B |
| 视频候选 / 质量审核 | 抽卡与标签 | review/adopt | 镜头页 | — | ✅ | A |
| 人工采纳 | 显式采纳 | 按 task 采纳 | 镜头页 | — | ✅ | A |
| MP4 ZIP 导出 | 成片导出 | 生产 7 个 MP4 | 项目导出 | — | ✅ | A |
| 文件上传/下载 | 鉴权访问 | 100MB 上限，登录 + 工作区校验 | `/files` | — | ✅ | A |
| TTS | 独立配音 | IndexTTS-2.5 | 镜头/角色 | ✅ 1 段 | ✅ | A |
| 音色样本 / 角色音色 | 固定音色 | voice samples + preset | `/voices` | 部分 | ✅ | B |
| 任务中心 | 通用状态 | 全局浮层 + 取消 + 跳转 | 全局 | — | ✅ | A |
| 首页工作台 | 生产概览 | dashboard 聚合 | `/projects` | — | ✅ | A |
| 发布 / 回滚 | 可回滚发布 | 不可变 release + symlink | 运维脚本 | — | — | A |
| AWS 扩容 | 50 GiB | 仍 20 GiB | AWS API | — | — | **阻塞** |

## 8. 安全与可靠性

### 8.1 访问控制

- 无公开注册；匿名业务 API → 401。
- viewer 写操作 → 403；跨工作区 → 404。
- 文件下载：匿名 401、同工作区 302、跨工作区 404。
- LLM Provider/Model/全局设置写接口要求 workspace admin。
- 首页 `can_edit=false` 时隐藏新建/编辑/删除，但后端仍是最终门禁。

### 8.2 R2

按用户要求**未修改**公共直链、r2.dev、URL 或访问策略。风险继续记录，不标记为已修复。

### 8.3 密钥

- 数据库密码已在本次审计后轮换；`/etc/dyeingtime/*.env` 640 root:ubuntu，旧 release `.env` 600。
- 轮换后 API、Staging、三个 Worker 均重启并通过健康检查。
- Provider Key 加密存储，日志中 Authorization 为 `***redacted***`。
- Git 跟踪文件未发现真实 Key。

### 8.4 备份

- MySQL：每日 19:00 UTC，保留 14 天，SHA256。
- **新增异地备份**：每次 DB 备份自动上传 R2 `backups/db/`。
- 媒体：每周日 20:00 UTC 归档，保留 28 天。
- 恢复演练：备份导入独立库，计数一致。
- `schema_migrations` 表记录已执行迁移，重复发布自动跳过。

### 8.5 回滚

```text
current  -> /srv/dyeingtime/releases/v2-internal-beta.2
previous -> /srv/dyeingtime/releases/v2-internal-beta.1
```

beta.1 的 venv 与 front dist 均在，回滚不依赖开发工作区。发布脚本在切换前创建数据库备份，并拒绝在有运行中视频任务时发布。

## 9. 测试

| 项 | 结果 |
| --- | --- |
| 后端 | **689 passed, 2 deselected** |
| TypeScript | 通过 |
| Build | 通过 |
| Vitest | **53 passed** |
| OpenAPI | 契约一致 |
| Mock Browser E2E | CI `40075076565` success |
| Real Backend E2E | CI `40075076550` success |
| 首页（生产） | 登录、统计、项目、继续创作、任务中心、手机端均通过 |
| 首页（Staging） | 搜索、筛选、排序、深链接、viewer 只读均通过 |
| 图片 | 2 张真实生成、R2、FileItem、额度、浏览器均通过 |
| 语音 | 1 段真实生成、R2、FileItem、额度、浏览器播放均通过 |
| ESLint | **仍未通过**：86 个历史 `no-explicit-any` 错误（集中在 `pages/aiStudio/assets`）；本次改动文件 0 error |

## 10. 发布

| 项 | 值 |
| --- | --- |
| Release tag | `v2-internal-beta.2` |
| Commit | `60c5a11` |
| 生产 release | `/srv/dyeingtime/releases/v2-internal-beta.2` |
| 生产访问 | `https://tim.run.place/` |
| Staging | `http://127.0.0.1:7802/`（仅本机）+ `127.0.0.1:8021` API |
| 数据库 | `dyeingtime`（生产）/ `dyeingtime_staging`（Staging） |
| 回滚 | `sudo deploy/scripts/rollback_release.sh` |

发布后生产数据：3 个项目、19 镜头、33 文件、7 条已采纳视频；ZIP 导出 7 个 MP4；额度 `image 100 / video 20 / audio 5000` 未消耗。

## 11. 遗留问题

### 必须立即处理

1. **AWS 扩容授权**：根卷仍 20 GiB，磁盘 82%，需要 50 GiB。

### 内部使用中处理

2. 真实文本模型剧本解析未授权，生产解析历史为 0。
3. 图片候选采纳、音色样本、分镜规划仅到自动化/回放级。
4. ESLint 历史 86 error 未清理。
5. 单机无高可用；R2 公共直链按用户要求保留。
6. TTS “听/替/挺”需人工试听确认。

### 质量长期优化

7. H3 多机位空间连续性、口型同步、角色声音一致性。
8. 角色耳饰重影等图像细节。

### 后续版本功能

9. 完整后期配音与口型同步。
10. 平台级管理员角色（当前复用 workspace admin/owner）。

## 12. P10-C 试生产准备条件

1. 完成 EBS 50 GiB 扩容并通过服务/数据复核。
2. 授权一次短剧本真实解析（建议 1 集、≤3000 字、单模型），确认候选与确认落库。
3. 用真实项目跑通：剧本 → 角色/场景 → 分镜 → 参考图 → 1 条 H3 视频 → 审核 → 采纳 → ZIP。
4. 明确生产图片/视频/TTS 的月度预算与并发上限（视频并发保持 1）。
5. 建立人工质量门槛：声音、口型、场景连续性、多机位一致性必须人工签字。
6. 保留 R2 公共直链风险接受记录，安排后续私有化窗口。
