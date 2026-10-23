# P9-D2 背景连续性真实生成结果

> 状态：**真实 H3 调用成功；新候选可播放、未自动采纳；L4 待用户观看。**
>
> 本阶段只新增 1 次真实 H3 视频提交。旧 02 视频、历史快照和当前采纳指针未修改。

## 1. 官方 Skill 规范化对照

使用已安装的 `h3-prompt-writing`（上游 commit `d21241f0a4b3acbb34c97dae47fa417b7065e438`）做不付费对照。

| 场景 | 旧快照 hash | 官方规范化后 hash | 核心变化 |
| --- | --- | --- | --- |
| 01 无对白意外语音 | `5767d116…e2cc1` | `7b592b5d…0b51c` | 英文六段；无中文画面描述；显式无对白；连续镜头 |
| 02 背景不连续 | `39cf2175…d30d03e` | `f6da9453…b9e4a` | 英文六段；3 个 Subject 对应 3 张 Picture；显式无对白；同一场景/不切镜 |
| P9-D1 男性对白 | `b0f427df…3a5d2` | `f7682ee4…bdbc9` | 英文六段；S1 台词；no-narration；单一连续镜头 |

说明：

- 旧快照 Prompt 未被修改。
- 官方规范化 hash 使用当前 Renderer fallback；真实提交前仍以新预览返回的 `input_hash` 为准。
- 文本模型在当前本地环境不可用，fallback 为通用英文骨架并给出 warning；P9-D2 真实提交使用了按官方 Skill 编写的英文高级 Prompt（已通过 manifest / `<Picture N>` / `<d>` / 单镜头校验）。

### 1.1 01 对照

旧 Prompt 含 `female lead / she`，且没有 `<d>` 或无对白指令。规范化后：

```text
subject_definitions:
<Subject 1> is the character 林晚 in <Picture 1>.
<Subject 2> is the environment 医院值班室 in <Picture 2>.
...
Sound: No spoken dialogue is requested; characters do not speak...
Continuity: ... one continuous scene at 医院值班室 ... do not cut to another location.
```

风险：中文角色名仍在 Subject 定义中；无对白约束降低模型擅自发声概率，但不能保证。

### 1.2 02 对照

旧 Prompt 只有 `they talk`，没有结构化对白和连续性约束。规范化后：

- `<Subject 1>` / `<Picture 1>` → 林晚参考图
- `<Subject 2>` / `<Picture 2>` → 周沉参考图
- `<Subject 3>` / `<Picture 3>` → 场景参考图
- 无 `<d>`，显式 `No spoken dialogue`
- 同一场景、连续运镜、不切到另一地点

### 1.3 P9-D1 对照

旧 Prompt 已有 S1 台词和 voice profile，但中文画面描述可能被朗读。规范化后：

- 正文英文骨架，不包含中文动作/构图自由描述；
- `<d>` 只保留中文台词；
- no-narration 约束保留；
- 单镜头 `[Shot 1]`，无 `[Shot 2]`。

## 2. P9-D2 测试输入

为避免旧 02 的角色名/图片/场景名冲突，使用隔离测试镜头 `s-p9d2-continuity`：

| 项 | 值 |
| --- | --- |
| 项目 | `p-e2e` |
| 镜头 | `s-p9d2-continuity` |
| 男性角色 / 说话人 | `char-p9d2-male` / 顾言 |
| 女性角色 / 沉默 | `char-p9d2-female` / 沈知微 |
| 场景 | `scene-p9d2-office` / 办公室 D2 |
| 台词 | 顾言：`你听我解释。` |
| 参考图 | `f-p9d2-male`、`f-p9d2-female`、`f-p9d2-office`（共 3 张） |
| 声音描述 | `Young adult male voice, clear timbre, moderate pace, restrained emotion.` |
| 音频参考 | 关闭 |
| 参数 | 5s / 768P / 9:16 / `auto_adopt=false` |

准备脚本：

- `backend/scripts/prepare_p9d2_continuity_shot.py`
- `backend/scripts/p9d2_official_prompt.py`

## 3. 官方 Prompt 与参考映射

官方英文 Prompt 文件：`docs/p9-real-h3/p9d2-official-prompt.txt`

参考映射：

| H3 标签 | 资产 | 版本 | 文件 |
| --- | --- | --- | --- |
| `<Picture 1>` | 顾言 | `av-p9d2-male` | `f-p9d2-male` |
| `<Picture 2>` | 沈知微 | `av-p9d2-female` | `f-p9d2-female` |
| `<Picture 3>` | 办公室 D2 | `av-p9d2-office` | `f-p9d2-office` |

说话人映射：

- `<Subject 1> (S1)` → 顾言，唯一说话人
- `<Subject 2>` → 沈知微，保持沉默，不分配 speaker ID

镜头结构：

- 单个 `[Shot 1]`
- 5 秒连续镜头
- 同一办公室空间、连续推近、不切到另一房间

声音：

- `overall_soundscape`：办公室环境声、通风声、远处脚步、衣料摩擦
- `non_diegetic_music`：`N/A`
- 台词只在 `<d>` 内

## 4. 真实调用

| 项 | 值 |
| --- | --- |
| 内部 Task | `d2f398cee22d45e88dcb939def720e9e` |
| 供应商 task | `01a16a35-d9c9-7259-aa73-3f2de7beb0b7` |
| Snapshot | `ff201572-0840-4ed6-babf-f38e764fd09d` |
| input_hash | `214962cad3fa4e10fae03a48480edb432e70bc3af19fd05e86eb6c7131e95a6e` |
| request_key | `p9d2-continuity-214962cad3fa` |
| FileItem | `bc9a1b44-303b-4cf2-ab04-3858e58cc686` |
| 模型/供应商 | MiniMax-H3 / compshare_model_api |
| 结果 | succeeded |

供应商先返回 `moderating`，随后 `running`，最终 `succeeded`；没有重试 POST。

Prompt / Payload 一致性：

- `GenerationTask.payload.run_args.input.prompt` 与 Snapshot `prompt` 完全一致；
- `reference_file_ids` 与 Manifest 顺序完全一致；
- Snapshot `advanced_prompt` 与最终 Prompt 一致；
- 参数：ratio `9:16`、resolution `768p`、duration `5`。

## 5. 真实视频

| 项 | 值 |
| --- | --- |
| 本地文件 | `/tmp/opencode/p9d2-continuity.mp4` |
| 对象存储 key | `generated-videos/shots/s-p9d2-continuity/b3181bfa18fc44128706c00eba6bc640.mp4` |
| 大小 | 2,051,254 bytes |
| 容器 | MP4 |
| 视频 | H.264，768×1344，5.1667s |
| 音频 | AAC，32kHz，双声道，5.175s |
| Chromium | `duration=5.175`、`readyState=4`、无错误 |
| 候选 | `unrated`、`is_current=false`、未采纳 |

截图/抽帧：

- `docs/p9-real-h3/p9d2-continuity-contact.jpg`
- `docs/p9-real-h3/p9d2-continuity-workbench.png`

## 6. 背景连续性分析

- 抽帧显示同一办公室背景贯穿全片：黑色玻璃隔断、长走廊、米色沙发、暖色灯具保持一致。
- 旧 02 场景切换检测（`scene > 0.25`）命中：
  - `1.375s`
  - `4.583s`
- 新 P9-D2 在同样阈值下**未检测到场景切换**。
- 人物位置保持：男性在左、女性在右；镜头连续推近，没有切到另一房间。
- 参考图与 Subject / Picture 编号一一对应。

## 7. 声音分析

ASR（faster-whisper base，中文，VAD）：

```text
1.04–2.04  你听我解释
```

- 只检测到指定台词，没有额外画面描述旁白；
- 女性角色没有发声；
- 台词内容与 `ShotDialogLine` 一致；
- 台词段基频中位数约 `109.2 Hz`（辅助线索，不单独用于性别判断）；
- 实际音色、口型和表演需用户 L4 试听确认。

## 8. 积分与额度

调用前：

- 本地视频：4/8，剩余 4
- 供应商可用积分：`5663.02`

调用后：

- 本地视频：**5/8，剩余 3**
- 供应商可用积分：**5623.02**
- 本单实际消耗：**40 points**（余额差与任务时间段一致）

| 类型 | 上限 | 已消耗 | 已预留 | 剩余 |
| --- | ---: | ---: | ---: | ---: |
| 图片 | 40 | 0 | 0 | 40 |
| 视频 | 8 | 5 | 0 | 3 |
| 音频 | 1000 | 0 | 0 | 1000 |

## 9. 历史保护

- 旧 02 Snapshot `39cf2175…d30d03e` 未修改；
- 旧 02 采纳指针仍为 `v-e2e-2`；
- 旧 02 视频 `/tmp/opencode/s-e2e-2.mp4` 保留；
- 新 P9-D2 视频只新增候选，未自动采纳；
- 未修改生产数据库，未合并 main。

## 10. 结论与待确认

- 官方 Skill 已安装并固定到上游 commit；Ref2VA 六段结构、标签、英文正文、单镜头和声音分层已纳入 Renderer/校验。
- P9-D2 真实视频技术上成功，背景连续性视觉上明显改善，场景切换检测为零。
- 指定台词出现，没有额外旁白；女性角色保持沉默。
- 仍需用户 L4 判断：表演、口型、音色、人物一致性、背景是否达到正式短剧标准。
- 不自动重抽，不再消耗剩余 3 次视频额度。
