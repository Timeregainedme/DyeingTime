---
title: "H3 官方 Prompt Skill 接入"
description: "记录 MiniMax H3 官方 h3-prompt-writing Skill 的固定版本、Ref2VA 规范、DyeingTime 业务约束与 Renderer 校验。"
weight: 12
---

> 本文属于“当前架构”，描述 DyeingTime 当前使用的 H3 Prompt 规范与版本。

## 1. 固定版本

- Skill：`h3-prompt-writing`
- 来源：`MiniMax-AI/MiniMax-H3`
- 上游 commit：`d21241f0a4b3acbb34c97dae47fa417b7065e438`
- 安装路径：`.agents/skills/h3-prompt-writing`
- 版本锁定：`skills-lock.json`
- 安装方式：项目级 copy，仅安装 `h3-prompt-writing`

安装/更新后必须：

1. 将 Skill 文件与上游同 commit 做逐文件 diff；
2. 更新 `skills-lock.json`；
3. 更新本节 commit 与文件校验；
4. 运行 H3 Prompt 回归测试。

## 2. 官方规则

### 模式

- T2VA：纯文本
- I2VA：首帧
- FL2VA：首尾帧
- L2VA：尾帧
- Ref2VA：多参考素材

DyeingTime 正式多参考工作流使用 Ref2VA，不因存在任意图片而切到 I2VA。

### Ref2VA 六段

```text
subject_definitions
summary
retention_analysis
detailed_description
overall_soundscape
non_diegetic_music
```

- `<Subject N>` 是可复用视觉主体；同一主体可引用多张 `<Picture N>`。
- `<Picture N>` 是实际参考图片；只作来源时写在 Subject 定义行内。
- `(S1)`/`(S2)` 只分配给实际发声的说话人；沉默角色不分配。
- 正文英文；台词/歌词/可见文字保留原语言并放入 `<d>`。
- `[Shot 1]` 不带时间戳；后续切镜使用 `[Shot N] At MM:SS.mmm`。
- `overall_soundscape` 与 `non_diegetic_music` 不重复对白。

## 3. DyeingTime 业务约束

- 优云智算 H3 Prompt 上限 7000 字符。
- 当前正式生成 5 秒 / 768P / 9:16。
- 5 秒短剧使用 200–300 词自适应区间，不机械套用官方 350–500 词长示例。
- 默认一个业务 Shot 对应一个 H3 `[Shot 1]`；只有用户明确要求复合镜头时才生成多个 `[Shot N]`。
- 默认同一场景、连续运镜、不切到另一地点。
- 对白只来自已确认的 `ShotDialogLine`，不允许模型自行增加剧情。
- 没有结构化对白时显式 `No spoken dialogue`。
- 只有对白行会被朗读：`Only the dialogue lines are spoken ... No narration or voiceover.`
- `voice_description` 只使用用户配置，不按姓名/照片推断。
- 参考音频默认关闭；固定音色样本属于项目配置。
- 历史 Snapshot 不可变；Prompt 变化必须反映到 `input_hash`。

## 4. Renderer 行为

- LLM 正文可用时以其为文风主体，但 Renderer 会补齐缺失的台词、voice profile、无对白、no-narration、连续性约束。
- 文本模型不可用时输出英文结构骨架；中文画面/动作/构图自由描述不进入正文，避免被 H3 朗读成旁白。
- 同一资产多张参考图按 `(kind, ref_id)` 合并为一个 Subject。
- 校验六段顺序、`[Shot 1]`、`<d>` 成对、Subject/Audio 定义、retention marker、单镜头 `[Shot 2+]`、summary 任务前缀、时间戳与长度。
- 质量检查与结构校验分离；blocking / warning / info 分级展示。

## 5. 边界

- Skill 是提示词编写规范，不是运行时视频生成引擎。
- 结构合规不等于真实视频质量提升；最终质量由真实 H3 生成与用户 L4 判断。
- 文字 Prompt 不能保证音色身份锁定、不能保证模型绝不切镜。
- 中文专有名词/用户声音描述仍可能保留在英文正文中；no-narration 只能降低被朗读概率。

## 6. 相关文档

- [视频提示词链路与参考图](/docs/architecture/video-prompt-pipeline/)
- [H3 多参考 Manifest 与生成输入快照](/docs/architecture/h3-reference-manifest/)
- [角色与演员音色链路](/docs/architecture/character-voice/)
