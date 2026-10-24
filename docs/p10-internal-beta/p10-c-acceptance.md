# P10-C 全功能验收记录

> 版本：`v2-internal-beta.3`
>
> 生产：`https://tim.run.place/`
>
> 代码基线：`01b5564`

## 1. 总体验收结论

**P10-C 未满足全部验收门槛，标记为「部分完成」。**

已实际完成：AWS 50 GiB 扩容核查、真实剧本解析、真实 AI 分镜规划、图片候选采纳与身份锁定、TTS 音色关联、跨模块一致性、生产发布。

未达到 A 级的两项：

1. **真实 AI 分镜规划的场景切分不合格**：使用免费 `beam-free` 模型时，3 个场次中有 2 个没有任何镜头，全部镜头被归到办公室场次；人工修正后才完成 6 个镜头的正式写入。
2. **生产环境未调用真实付费文本模型**：真实解析/规划在隔离验收库用 `beam-free` 完成，生产 `script_parse_runs` 仍为 0。

因此不能宣称“全功能真实验收全部通过”。

## 2. AWS 50 GiB 核查

| 项 | 实际值 |
| --- | --- |
| 实例 | `i-08ef234188645963d` |
| Region / AZ | `us-east-2` / `us-east-2a` |
| 根卷 ID | `vol-0b1e3735220a28475` |
| 云侧容量 | **无法通过 API 复核**：实例角色仍无 `ec2:DescribeVolumes` |
| 客户机可见容量 | `nvme0n1` 50G，`nvme0n1p1` 49G |
| 文件系统 | ext4 `/`，48G，已用 15G，**32%**，可用 33G |
| 第二块 EBS | 已不存在；仅 `nvme0n1` 一块盘 |
| 停机 | 无（本次核查未重启主机） |
| Snapshot ID | 无法从 AWS API 获取；本次未新建快照 |

RustFS：

- `rustfs.service` 运行中，参数仍为 `/data/rustfs0`，但该路径已不再单独挂载，实际落在根盘。
- `/data/rustfs0` 仅 180K，只有 `jellyfish-assets/healthcheck`；生产媒体实际存 Cloudflare R2。
- 结论：RustFS 数据盘迁移已完成，当前无独立数据盘；后续增长风险转移到根盘。

## 3. 真实剧本解析（A 级，隔离验收）

### 3.1 输入与配置

| 项 | 值 |
| --- | --- |
| 项目 | `p10c-parse-1792834234` |
| 章节 | `c10c-parse-1792834234` |
| 文档 / 版本 | `f4ad77ba-411d-468f-9622-3af5d0cf913c` / `9a8ff26a-ad14-4a0c-a09a-2c7382b4012d` |
| 输入 | 474 字，3 场，2 角色，含别名“沈总” |
| 模型 | `beam-free`（OpenCode Go，**cost=0**，billing_source=go） |
| 运行 / 任务 | `16500d86-729e-4532-828d-d348234e8ba6` / `d3442caec95047ada6449e492a07fc19` |
| 耗时 | 20 秒，1 chunk，0 失败 |

费用证据：供应商响应 `"cost": 0`、`"billing_source": "go"`、`"list_cost": 0`，不属于新增付费调用。

### 3.2 真实输出

23 条候选：

- 角色 2：沈知微（别名“沈总”）、顾言
- 场景 3：沈氏集团办公室、地下车库、沈知微公寓客厅
- 对白 7：说话人全部正确，含“念。”“那就查。”
- SceneBeat 3：办公室收报告 / 车库决定追查 / 公寓收到备份
- 道具 2：检测报告、手机
- 服装变化 1：沈知微换灰色家居服
- 问题 4：夫人身份未明、顾言外貌未明、沈知微年龄未明、短信不算口语对白

### 3.3 人工审核与确认

- 手工修改 `dialogue:1` 情绪为“急切汇报”，确认后 `confirmed_result.dialogues[0].emotion` 持久化为该值。
- 确认结果：创建 2 角色、3 场景、2 道具、2 服装；存 7 对白、3 场次节拍；章节原文 474 字，摘要写入。
- 别名表写入“沈总”（source=`p3_parse`）。
- 版本状态：`active / parsed`，原版本保留。
- 重复确认：角色/场景数量不变，幂等。
- 相同输入再次 parse：`reused=true`，返回同一 run，无重复调用。
- 未确认的 AI 结果不会覆盖已确认内容。

## 4. 真实 AI 分镜规划（B 级，质量不合格）

| 项 | 值 |
| --- | --- |
| 草稿 / 任务 | `2ee8a4b8-7fb0-4745-ad25-aafb748aabb7` / `8097346d6f534c7aa4a6a11ac60abf7e` |
| 模型 | `beam-free`（cost=0） |
| 目标 / 实际 | 30s / 6 镜头 × 5s = 30s |
| 角色 / 对白 | 角色关联正确；对白 7 条，说话人正确 |

**质量问题**：

1. **场次切分失败**：6 个镜头全部落到第 1 场“办公室”，第 2 场车库和第 3 场公寓没有任何镜头。
2. 模型未输出 `scene_group_index`，Pydantic 默认值把它静默当成第 1 场。
3. 镜头标题全部为“镜头 1”，`video_prompt`、`description` 为空。
4. 第 6 镜把短信内容当成顾言口语对白。

**人工修正**：

- 第 5 镜改为地下车库，第 6 镜改为公寓客厅。
- 第 6 镜移除短信对白，改为纯视觉镜头。
- 基础设施修复后确认成功，写入 6 个 Shot（index 1–6），并生成 ShotDetail、ShotCharacterLink、ShotDialogLine、ShotAssetVersion。
- 角色身份锁定后，阻塞问题清零。

**结论**：真实模型调用成功，但**场景覆盖不合格**，不能判为 A。需要更强文本模型或更严格的场次提示/校验。

## 5. 图片候选与身份锁定（A 级，隔离验收）

复用 P10-B 图片，未新增图片生成调用。

| 项 | 值 |
| --- | --- |
| 场景候选 | `17`（基础版）、`18`（夜间版） |
| 角色候选 | `19`（新身份草稿） |
| 场景版本 | `av-p9d2-office`（superseded）、`ac3dd34c-…`（active） |
| 角色身份 | `av-p9d2-female`（superseded）、`958314c2-…`（active） |

验证结果：

- 候选可展示、可审核、可显式采纳；采纳后旧候选保留为 `succeeded`。
- 采纳后 `SceneImage.file_id` / `CharacterImage.file_id` 回填，`file_usages` 正确。
- 发现并修复：资产档案缩略图用小写 `"front"` 比较大写 `"FRONT"`，导致采纳后仍显示旧图。
- 角色身份锁定后，向同一身份版本采纳新正面图返回 409；新建身份草稿版本后可采纳，切换后 `identity_lock_version` 递增。
- 版本切换后，旧 Shot 的 `ShotAssetVersion` 仍指向旧版本；`generation-preview` 仍读取旧文件，证明历史引用不被静默改写。
- 新镜头 `s-p10c-ref` 自动推荐到 2 张参考图；`<Picture 1>`/`<Picture 2>` 与 manifest 顺序一致。

## 6. 角色固定音色与 TTS（A 级关联，H3 效果待验证）

复用 P10-B 音频 `e4d4cb5a…`（17 字，3.390s WAV，22050Hz mono，149,548B）。

音频检查：

- 峰值 -4.5dB，RMS -18.9dB，无削波；首尾短静音，句中 0.4s 停顿（逗号）。
- ASR（本地 faster-whisper）：base “你先替我解释…”，tiny “你先挺我解释…”。差异集中在“听”，两个模型给出不同字，判断更可能是 ASR 误识别，但**仍需人工试听确认**。

角色关联：

- 沈知微绑定 preset 晚晴，顾言绑定 preset 承泽，`voice_description` 已保存。
- 上传固定音色样本：`a0ecd999-…`（沈知微）、`e7bb4dfb-…`（顾言）。
- 对白行 13/14 的 `speaker_character_id` 正确；`_resolve_audio_target` 自动带出文本、镜头、说话人、情绪“克制”。
- `_resolve_audio_voice` 返回角色 voice_id + preset。
- 项目 `use_dialog_audio_as_reference` 默认 false 时，P6 音频参考为空。
- 开启后，H3 输入包含 `<Audio 1>`/`<Audio 2>`、对应说话人和 voice profile；显式 file_id 覆盖也生效。
- 已恢复开关为 false。

**未验证**：H3 用固定音色真实生成视频后的听感与口型；按要求未新增付费 H3 调用。

## 7. 跨模块一致性

| 链路 | 结果 |
| --- | --- |
| ScriptDocument → Version → Chapter | 真实上传/解析/确认，原文与历史保留 |
| Chapter → SceneGroup | P3 场次建议导入 3 个正式场次 |
| SceneGroup → ShotPlan → Shot | 真实规划 + 人工修正 + 确认写入 6 镜头 |
| Shot → ShotDetail | 景别/角度/运镜/时长/场景写入 |
| Shot → ShotCharacterLink | 6 镜头角色数 2/1/1/2/2/1 |
| Shot → ShotDialogLine | 对白 7 条，说话人正确 |
| Shot → ShotAssetVersion | 每镜头 4–6 条 |
| ShotAssetVersion → Manifest → H3 Prompt | 2 角色 + 1 场景，`<Picture N>` 顺序一致 |
| 跨项目引用 | `ShotCharacterLink` 拒绝：400 “Character does not belong to the same project” |
| 旧版本 / 快照 | 场景/身份切换后旧 Shot 绑定不变；历史 Snapshot manifest 仍指向旧版本 |
| 视频候选 | 3 个版本保留（含失败版本），只有一个 `is_current`，不自动采纳 |
| ZIP 导出 | 生产 7 个 MP4，与 7 个已采纳视频一一对应 |
| 幂等 | parse 重复请求 `reused=true`；confirm 重复调用不新增数据；request_key 有单测 |

## 8. 已修复缺陷

| 缺陷 | 影响 | 修复 |
| --- | --- | --- |
| TTS 执行器缺少 `reserve_for_task/settle_task` 导入 | 所有 TTS 必然失败且额度不结算 | P10-B 已修；P10-C 回归覆盖 |
| Go `/api/v1/ready` 永久 503 | DB 密码轮换后 Go 连接池用旧密码，健康检查红灯 | Go 改用 `/etc/dyeingtime/backend.env`，`Requires=mysql`，重启恢复 |
| 资产档案缩略图 FRONT 大小写 | 采纳新图后仍显示旧图 | 统一大写比较 + 回归测试 |
| ShotCharacterLink 同 index 替换 | MySQL 唯一键 500 | delete 后显式 flush |
| 分镜规划入队早于事务提交 | Worker 查不到任务，Celery 假成功、任务永久 pending | commit → enqueue；Worker 增加 3 秒重试兜底 |
| 分镜确认先插 ShotAssetVersion | MySQL FK 1452，确认 500 | 先 flush Shot/Detail 再写关联 |
| 场景/道具/服装版本为空 | 参考图无法进入 Manifest | 确认时回退到资产当前版本 |
| 规划缺少场次/场次无镜头 | 静默丢场景 | 缺 `scene_group_index` 记 blocking；coverage 增加“场次无镜头”警告 |

## 9. 测试与发布

| 项 | 结果 |
| --- | --- |
| 后端 | **691 passed, 2 deselected** |
| TypeScript | 通过 |
| Vitest | **53 passed** |
| Build | 通过 |
| OpenAPI | 契约一致 |
| Mock E2E | CI `40083809731` success |
| Real Backend E2E | CI `40083809684` success |
| 生产浏览器 | 登录、首页、真实项目数据通过 |
| 生产 API | dashboard 200、ZIP 200/7 files、quota 100/20/5000 |
| 健康检查 | OK，磁盘 32% |

发布：

- Tag `v2-internal-beta.3`
- Commit `01b5564`
- `current → beta.3`，`previous → beta.2`
- 生产数据：3 项目 / 19 镜头 / 33 文件 / 7 已采纳视频
- 回滚脚本可用，beta.2 保留完整 venv + dist

## 10. 剩余问题

### 阻塞 P10-C 完成

1. AI 分镜场景切分不合格；需要更强文本模型（付费）或改进提示词/校验。
2. 生产未进行真实付费文本模型解析与规划。

### 内部使用中处理

3. 规划生成的镜头标题、描述、video_prompt 为空，需补充或加强 schema 校验。
4. 图片候选上传仍主动设置 `public-read` ACL（与其他上传路径不一致）。
5. ESLint 仍有 86 个历史 `no-explicit-any` 错误。
6. AWS `DescribeVolumes` 仍无权限，无法从云侧复核卷类型/Snapshot ID。
7. H3 固定音色真实视频效果未验证。
8. R2 公共直链按用户要求保留，风险未修复。

## 11. ToonFlow

`Next Phase: ToonFlow Usage & Case Study`

`NOT_STARTED`

本阶段未读取、扫描、比较或修改任何 ToonFlow 资料。
