---
title: "P9-D1 男性对白声音验证结果"
description: "真实 H3 男性对白声音测试：输入修正、真实视频、台词/旁白分析、额度与 P9-D2 背景连续性准备。"
weight: 5
---

> 状态：**真实 H3 调用成功，视频可播放；音色由用户 L4 试听确认。**
>
> 本阶段只新增 1 次真实 H3 视频提交；旧视频、历史快照和采纳指针未修改。

## 1. 原 01 问题的定性

原 `s-e2e-1` **不是结构化对白声音错配**：

- `ShotDialogLine` = 0
- `ShotCharacterLink` = 0
- `voice_description` 为空
- 参考音频关闭
- 高级 Prompt 写 `female lead / she`
- 参考图实际是男性肖像，但资产名是“林晚”

因此原问题是“无结构化对白时模型擅自生成说话/声音”，叠加“女性文本指代 vs 男性参考图”的冲突。系统没有可执行的说话人和声音约束。

## 2. 专项输入

为避免修改正式剧情，在隔离测试项目 `p-e2e` 创建专项镜头：

- Shot：`s-p9d1-voice`
- Character：`char-p9d1-male` / 江屿
- 参考图：男性肖像 + 办公室场景，共 2 张
- 台词：`你先听我解释。`
- `speaker_character_id=char-p9d1-male`
- `voice_description=年轻成年男性声音，音色清晰，语速适中，情绪克制。`
- 音频参考关闭
- `auto_adopt=false`

准备脚本：`backend/scripts/prepare_p9d1_voice_shot.py`。

## 3. 真实调用

| 项 | 值 |
| --- | --- |
| 内部 Task | `1722a29e118e4cfd9eb3839ee3bd5f00` |
| 供应商 task | `01a169a6-b9a6-799a-8f50-3cfc66f79d90` |
| Snapshot | `daeaedbc-4b7b-42ba-a144-fb17c9e5f866` |
| input_hash | `b0f427df290805dd83cdf6e47c725d7bba080229ce9ac6ffe68204e8a823a5d2` |
| request_key | `p9d1-voice-b0f427df2908` |
| FileItem | `1fefbc8f-065b-4fab-bf0d-b8a6e5eca302` |
| 参数 | 5s / 768P / 9:16 / 2 参考图 |
| 结果 | succeeded，候选未采纳 |

## 4. 新旧 Prompt

旧 01 Prompt 关键句：

```text
<Subject 1> is the locked female lead. ... she stands in the hospital duty room ...
```

新专项 Prompt 关键句：

```text
<Subject 1> is 江屿 in <Picture 1>.
<Subject 1> (S1), using this voice profile: 年轻成年男性声音，音色清晰，语速适中，情绪克制, says, <d>[Chinese] 你先听我解释。</d>
Characters who are not speaking keep their mouths closed and only react physically.
Continuity: ... one continuous scene at 办公室 ... do not cut to another location.
```

新 Prompt 不再出现相反性别指代；`GenerationTask.payload` 中的 prompt 与快照完全一致，参考图顺序与 manifest 一致。

## 5. 真实视频

- 本地：`/tmp/opencode/p9d1-voice.mp4`
- 大小：1,285,861 bytes
- 容器：MP4
- 视频：H.264，768×1344，5.1667s
- 音频：AAC，32kHz，双声道，5.175s
- Chromium：`duration=5.175`，`readyState=4`，无错误
- 候选：`unrated`，`is_current=false`，未自动采纳

画面抽帧显示男性角色、同一办公室背景、无可见切镜。

## 6. 声音分析

ASR 结果：

```text
0.00–3.97  与中文画面描述对应的额外旁白
3.97–5.17  你先聽我解釋
```

- 指定台词正确说出；
- 但模型额外朗读了非 `<d>` 的画面描述，说明当前中文骨架正文可能被 H3 当作旁白；
- 旧 01 尾部语音基频中位数约 225.35 Hz，本次台词段约 113.08 Hz；基频只作辅助，最终音色由用户试听确认；
- 代码已补充“只有对白行会被朗读”的 no-narration 约束；本次真实调用发生在该约束之前，历史快照不修改。

## 7. 额度

| 类型 | 上限 | 已消耗 | 剩余 |
| --- | ---: | ---: | ---: |
| 图片 | 40 | 0 | 40 |
| 视频 | 8 | 4 | 4 |
| 音频 | 1000 | 0 | 1000 |

供应商余额读取为 `5663.02 available`。同账号在 16:37–16:42 存在多条非本会话发起的 H3 任务，因此不能用余额差单独结算本单；本单按同参数估算约 50 points，供应商未提供逐任务积分字段。

## 8. P9-D2 背景连续性准备

对 `s-e2e-2` 做不收费预览：

- 场景版本有效，3 张参考图，场景图实际进入 H3 输入；
- 新 Prompt 已包含同一场景、连续运镜、不切到另一地点；
- 当前无 blocking；
- 仍建议在 P9-D2 增加结构化轮流台词，清空旧高级 Prompt 后重新预览；
- 如果真实重抽仍切镜，再考虑拆分 Shot。

## 9. P9-D2 后续结果

P9-D2 已按官方 Ref2VA 规范化并完成 1 次真实生成，背景连续性明显改善；详见 [P9-D2 背景连续性真实生成结果](/docs/plans/p9-d2-continuity-results/)。

## 10. 结论

- 真实链路、视频回存、候选与播放均成功；
- 指定台词成功；
- 发现并修复了“非 `<d>` 文本被朗读”的下一项 Prompt 风险；
- P9-D1 额度已用 1 次；P9-D2 已另行执行 1 次并完成背景连续性验证。
