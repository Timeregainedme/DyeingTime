---
title: "P9-D2 背景连续性真实生成结果"
description: "MiniMax H3 官方 Skill 接入、Ref2VA 规范化、P9-D2 同一场景连续镜头真实生成、积分与额度记录。"
weight: 4
---

> 状态：**真实 H3 调用成功；新候选可播放、未自动采纳；L4 待用户观看。**

## 1. 官方 Skill

已安装 `h3-prompt-writing`：

- 来源：`MiniMax-AI/MiniMax-H3`
- 上游 commit：`d21241f0a4b3acbb34c97dae47fa417b7065e438`
- 安装路径：`.agents/skills/h3-prompt-writing`
- 版本锁定：`skills-lock.json`
- 与上游同 commit 文件逐文件一致

详细审计见 `docs/p9-real-h3/h3-official-skill-audit.md`。

## 2. Renderer 适配

已按官方 Ref2VA 规范修复：

- `summary` 改为英文并使用 `<Subject N>` / `<Audio N>`；
- fallback `detailed_description` 不再把中文画面/动作/构图写入英文正文；
- 内部枚举码映射为自然英文镜头语言；
- 同一角色多张参考图合并为一个 `<Subject N>`，可引用多个 `<Picture N>`；
- 中文 `continuity_guidance` 不再进入 H3 英文正文；
- 单业务 Shot 出现 `[Shot 2+]` 时给出 warning；
- `summary` 缺少任务类型前缀时给出 warning；
- 保留 no-narration、单一连续镜头、显式无对白；
- 质量检查忽略 “do not cut” 等否定约束，并按说话人附近片段判断性别指代。

官方规则与 DyeingTime 业务规则的边界见审计文档。

## 3. P9-D2 输入

隔离测试镜头 `s-p9d2-continuity`：

- 男性说话人：顾言 / `char-p9d2-male`
- 女性沉默角色：沈知微 / `char-p9d2-female`
- 场景：办公室 D2 / `scene-p9d2-office`
- 参考图：3 张
- 台词：`你听我解释。`
- 声音描述：`Young adult male voice, clear timbre, moderate pace, restrained emotion.`
- 5s / 768P / 9:16 / 音频参考关闭 / `auto_adopt=false`

官方英文 Ref2VA Prompt：`docs/p9-real-h3/p9d2-official-prompt.txt`

## 4. 真实调用

| 项 | 值 |
| --- | --- |
| 内部 Task | `d2f398cee22d45e88dcb939def720e9e` |
| 供应商 task | `01a16a35-d9c9-7259-aa73-3f2de7beb0b7` |
| Snapshot | `ff201572-0840-4ed6-babf-f38e764fd09d` |
| input_hash | `214962cad3fa4e10fae03a48480edb432e70bc3af19fd05e86eb6c7131e95a6e` |
| FileItem | `bc9a1b44-303b-4cf2-ab04-3858e58cc686` |
| 结果 | succeeded |

Prompt 与 Provider Payload 完全一致；3 张参考图顺序与 Manifest 一致。

## 5. 视频

- 本地：`/tmp/opencode/p9d2-continuity.mp4`
- 大小：2,051,254 bytes
- 视频：H.264，768×1344，5.1667s
- 音频：AAC，32kHz，双声道，5.175s
- Chromium：`duration=5.175`、`readyState=4`
- 候选未采纳、`unrated`

## 6. 连续性分析

- 抽帧显示同一办公室背景贯穿全片。
- 旧 02 场景切换检测：`1.375s`、`4.583s`。
- 新 P9-D2 同阈值未检测到场景切换。
- 男性在左、女性在右，位置保持；连续推近，无切到另一房间。

## 7. 声音分析

ASR：

```text
1.04–2.04  你听我解释
```

- 只出现指定台词；
- 没有额外画面描述旁白；
- 女性角色保持沉默；
- 台词段基频中位数约 109.2 Hz，仅作辅助线索；
- 音色与表演由用户 L4 确认。

## 8. 额度

| 类型 | 上限 | 已消耗 | 剩余 |
| --- | ---: | ---: | ---: |
| 图片 | 40 | 0 | 40 |
| 视频 | 8 | 5 | 3 |
| 音频 | 1000 | 0 | 1000 |

- 供应商积分：`5663.02 → 5623.02`
- 本单实际消耗：**40 points**
- 本阶段只新增 1 次真实 H3 提交。

## 9. 历史保护

- 旧 02 Snapshot `39cf2175…d30d03e` 未修改；
- 旧 02 采纳指针仍为 `v-e2e-2`；
- 旧 02 视频保留；
- 新视频未自动采纳。

## 10. 场景语义核查

旧 `scene-e2e` 名称为“医院值班室”，但实际图片是现代办公室；P9-B2 快照因此出现名称/图片冲突。P9-D2 使用新的 `scene-p9d2-office`（办公室 D2），名称、Prompt、Manifest 和视频一致。已修正测试 seed 名称，历史快照不修改。该问题未消耗新的真实视频额度。

## 11. 待确认

- 背景连续性是否达到正式短剧标准；
- 两人表演、口型、音色与人物一致性；
- 是否需要 L4 后重抽或直接进入下一阶段。
