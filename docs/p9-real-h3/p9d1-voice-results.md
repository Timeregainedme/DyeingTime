# P9-D1 男性对白声音修复真实生成结果

> 状态：**真实 H3 调用成功，视频可播放；已标记为用户 L4 待评价。**
>
> 本阶段只新增 1 次真实 H3 视频提交。旧 01 视频、历史快照、当前采纳指针均未修改。

## 1. 原 01 视频的问题定性

原 01 视频**不是“有结构化对白但声音错配”**。

真实快照 `3adb6fa28f2c47d4b1a174a797f7b026` 的输入事实：

- `ShotDialogLine`：0 条
- `ShotCharacterLink`：0 条
- `audio_refs`：0 条
- `characters.voice_description`：空
- 高级 Prompt：`locked female lead / she`
- 参考图 `f-char` 实际为男性肖像，但资产名是“林晚”

因此原问题是：

1. **无结构化对白，H3 擅自生成说话/口型/声音**；
2. Prompt 的女性指代与男性参考图冲突，模型得到矛盾的性别线索；
3. 未开启参考音频，也没有用户声音描述，系统没有可执行的音色约束。

## 2. 原始矛盾核对

| 检查项 | 原始 01 |
| --- | --- |
| 原始剧本对白 | 无结构化 `ShotDialogLine` |
| 实际角色 | 参考图是男性肖像，资产名为“林晚” |
| Character 名称与图片 | 名称/图片不一致 |
| ShotCharacterLink | 无 |
| speaker_character_id | 无 |
| voice_description | 空 |
| H3 Prompt | 含 `female lead / she` |
| Subject 编号 | `<Picture 1>` 对应男性参考图，但文本称其 female |
| 音频参考 | 关闭 |

结论：原 01 的“男性角色 + 女性声音”是**无结构化对白、性别文本与参考图冲突、无声音描述**共同造成的；不能把它简单归因成后端说话人字段映射错误。

## 3. 本次修正内容

为了避免在正式剧情中新增台词，本次没有修改原 `s-e2e-1`，而是在隔离测试项目 `p-e2e` 中创建专项镜头 `s-p9d1-voice`：

- 角色：`char-p9d1-male` / 江屿
- 参考图：`f-p9d1-male`，复用原男性肖像 `e2e/images/char.jpg`
- 场景：`scene-p9d1-office` / 办公室，复用原办公室图 `e2e/images/scene.jpg`
- 台词：`ShotDialogLine` = “你先听我解释。”
- 说话人：`speaker_character_id=char-p9d1-male`
- 声音描述：`年轻成年男性声音，音色清晰，语速适中，情绪克制。`
- `ShotCharacterLink`：已建立
- `ShotAssetVersion`：角色身份 `av-p9d1-male` + 场景 `av-p9d1-office`
- Manifest：2 张参考图，顺序为角色身份 → 场景
- 项目音频参考：关闭
- `auto_adopt=false`

准备脚本：`backend/scripts/prepare_p9d1_voice_shot.py`。

## 4. 新旧 Prompt 与 input_hash

### 旧 01 快照

- input_hash：`5767d116ad3711155e2ac0312a9599adb4239d6dd24ef0b13b0555e17c9e2cc1`
- Prompt 关键句：

```text
<Subject 1> is the locked female lead. [Shot 1] ... she stands in the hospital duty room ...
```

### 新专项镜头

- input_hash：`b0f427df290805dd83cdf6e47c725d7bba080229ce9ac6ffe68204e8a823a5d2`
- 快照：`daeaedbc-4b7b-42ba-a144-fb17c9e5f866`
- Prompt 关键句：

```text
<Subject 1> is 江屿 in <Picture 1>.
<Subject 2> is 办公室 in <Picture 2>.
...
<Subject 1> (S1), using this voice profile: 年轻成年男性声音，音色清晰，语速适中，情绪克制, says, <d>[Chinese] 你先听我解释。</d>
Characters who are not speaking keep their mouths closed and only react physically.
Continuity: Keep the entire video in one continuous scene at 办公室; ... do not cut to another location.
```

核对结果：

- 不再出现 `female lead / she` / 女性代词；
- 出现结构化 `<d>` 台词、`(S1)`、voice profile；
- 场景名与实际参考图一致；
- 只有一名画面角色，没有第二角色开口；
- 最终 Prompt 与 `GenerationTask.payload.run_args.input.prompt` 完全一致；
- `reference_file_ids` 与快照 manifest 顺序完全一致。

## 5. 真实供应商调用

| 项 | 值 |
| --- | --- |
| 内部 Task | `1722a29e118e4cfd9eb3839ee3bd5f00` |
| 供应商 task | `01a169a6-b9a6-799a-8f50-3cfc66f79d90` |
| Snapshot | `daeaedbc-4b7b-42ba-a144-fb17c9e5f866` |
| request_key | `p9d1-voice-b0f427df2908` |
| FileItem | `1fefbc8f-065b-4fab-bf0d-b8a6e5eca302` |
| 模型/供应商 | MiniMax-H3 / compshare_model_api |
| 参数 | 5 秒 / 768P / 9:16 / 2 张参考图 / 音频参考关闭 |
| 结果 | succeeded |
| 候选状态 | 未采纳，`is_current=false` |

## 6. 真实视频

| 项 | 值 |
| --- | --- |
| 本地文件 | `/tmp/opencode/p9d1-voice.mp4` |
| 对象存储 key | `generated-videos/shots/s-p9d1-voice/e6bab3c80d6c45f58ba8a70204d63153.mp4` |
| 大小 | 1,285,861 bytes |
| 容器 | MP4 |
| 视频 | H.264，768×1344，5.1667s |
| 音频 | AAC，32kHz，双声道，5.175s |
| 工作台播放 | `duration=5.175`，`readyState=4`，无播放错误 |

抽帧与频谱：

- `docs/p9-real-h3/p9d1-voice-contact.jpg`
- `docs/p9-real-h3/p9d1-voice-spectrum.png`
- `docs/p9-real-h3/p9d1-voice-workbench.png`

画面观察：

- 男性人物与参考图一致；
- 办公室背景贯穿全片，未见明显切镜；
- 人物有说话口型；
- 没有第二个角色开口。

## 7. 声音分析

ASR（faster-whisper base，中文，VAD）结果：

```text
0.00–3.97  与 Prompt 中文画面描述高度对应的旁白文本
3.97–5.17  你先聽我解釋
```

结论：

- **指定台词已正确说出**，内容与 `ShotDialogLine` 一致；
- **但 H3 额外朗读了非 `<d>` 的画面描述/旁白**；这是本次新发现的 Prompt 范围问题，不是原来的女性声音问题；
- 旧 01 尾部语音基频中位数约 **225.35 Hz**，本次台词段约 **113.08 Hz**；基频只作辅助线索，不能单独据此判定性别；
- 是否需要保留旁白、音色是否符合“江屿”，必须由用户实际试听确认。

> 因为本阶段只允许 1 次真实提交，本次没有再次生成。代码已补充“只有对白行会被朗读”的约束，下一次受控重抽应使用包含该约束的预览快照。

## 8. 积分与额度

调用后读取数据库：

| 类型 | 上限 | 已消耗 | 已预留 | 剩余 |
| --- | ---: | ---: | ---: | ---: |
| 图片 | 40 | 0 | 0 | 40 |
| 视频 | 8 | 4 | 0 | 4 |
| 音频 | 1000 | 0 | 0 | 1000 |

供应商积分：

- P9-B2 记录：`9893.02`
- 本次调用后 `compshare minimax points`：**5663.02 available**
- 本单按同参数（5s / 2 图）估算约 **50 points**，供应商未提供逐任务积分字段，无法单独确认；
- 供应商任务列表显示同一账号在 16:37–16:42 存在多条**非本会话发起**的 H3 任务（4–6 秒、4–5 图），因此不能用余额差直接归因本次调用；
- 未发现本会话发起第二次 H3 任务。

## 9. 历史保护

- 原 `s-e2e-1` 快照 hash 仍为 `5767d116…e2cc1`；
- 原 `s-e2e-1` 采纳指针仍为 `v-e2e-1`；
- 原 01 视频 `/tmp/opencode/s-e2e-1.mp4` 保留；
- 新视频只新增候选，未自动采纳；
- 未修改生产数据库。

## 10. P9-D2 背景连续性预检查

对 `s-e2e-2` 使用当前代码做**不收费预览**：

- 场景版本：`scene-e2e / av-scene` 有效；
- 参考图：3 张，`f-char`、`f-char2`、`f-scene`，场景图实际进入 H3 输入；
- 当前预览 hash：`175de974a153b0cb0b1087a08aad5f864014586ec4821ab53583afbaec07fe21`；
- Prompt 已包含：`Keep the entire video in one continuous scene at 医院值班室` 和 `do not cut to another location`；
- 当前自然提示词没有明确多机位线索；`_CUT_CUE_RE` 只命中了 `do not cut to another location` 中的 "cut to"，这是否定约束，不应判为风险；
- 预览无 blocking；提示词仍有“中文正文可能被朗读”的 warning（文本模型不可用，回落到骨架）；
- 结论：P9-D2 可以直接用该镜头做一次“同一场景 + 连续运镜 + 结构化对白”的受控重抽，不需要先拆 Shot；如果模型仍切镜，再拆分为多个 Shot。

P9-D2 建议参数：

- 1 次视频额度，5 秒 / 768P / 9:16 / 3 张参考图；
- 保留两个角色身份和场景版本；
- 增加结构化轮流台词（或明确无对白），避免 `they talk` 这种无归属描述；
- 清空旧高级 Prompt，使用新预览；
- `auto_adopt=false`，生成后只新增候选。

## 11. 回归与提交

代码变更（no-narration 指令 + 测试 + 准备脚本）将在本次报告中单独提交。需要执行：

```bash
cd backend
uv run pytest tests -q
cd ../front
pnpm exec tsc --noEmit
pnpm run build
pnpm run openapi:check
```

## 12. 当前结论

- **技术链路成功**：真实 H3 任务成功、MP4 可播放、候选已回存、旧采纳不变。
- **台词成功**：指定台词被正确说出。
- **声音待确认**：听觉上需用户确认是否为符合“江屿”的男性声音；基频辅助线索倾向男性，但不能替代试听。
- **新发现**：模型额外朗读了非 `<d>` 的画面描述，说明“中文骨架正文”可能被当成旁白。代码已加 no-narration 约束，下一次真实重抽应验证该约束。
- **不再自动重抽**：本阶段 1 次额度已使用，停止并等待用户 L4。
