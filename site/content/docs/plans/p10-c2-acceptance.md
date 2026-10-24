---
title: "P10-C2 AI 分镜修复与 DeepSeek 验收"
description: "分镜场次覆盖、内容质量、SCREEN_TEXT 与真实 DeepSeek 调用记录；v2-internal-beta.5。"
weight: 6
---

> 状态：**通过**。首次 DeepSeek 分镜规划覆盖 3 场 6 镜，标题/描述/Prompt/对白均合格。

## 1. 修复

- Schema 必填：`scene_group_index`、标题、动作、描述、视频 Prompt、`source_dialogue_index`。
- Prompt 新增 SceneBeat、已确认对白索引、镜头预算、修复反馈与逐场覆盖硬约束。
- 质量检查：场次无镜头、重复/弱标题、空描述、非法对白索引/说话人、短信误当口语。
- 受控修复：`SHOT_PLAN_MAX_REPAIRS`（默认 0，验收为 1），不无限重试。
- H3 渲染：`SCREEN_TEXT` 只显示、不朗读；`ACTION` 不进入正文。

## 2. DeepSeek 真实调用

- 模型：`deepseek-v4.1-flash`（OpenCode Go）。
- 4 次模型任务（5 次成功 HTTP 请求）：3 次解析（前两次失败重试）+ 1 次分镜。
- 总 tokens：input 20,782 / output 26,848。
- 费用：**$0.019226**，低于 $0.05 授权上限。
- 分镜首次即通过，未使用修复额度。

## 3. 结果

- 3 场覆盖：办公室 3 镜、车库 1 镜、公寓 2 镜。
- 6 镜头，标题/描述/Prompt 全部非空；总时长 30s。
- 7 条口语对白说话人正确；2 条短信 `SCREEN_TEXT`，不进入人声。
- 确认写入 6 Shot；二次确认不重复写入。
- H3 preview 无 blocking，Picture 编号与 manifest 一致。

## 4. 发布

- `v2-internal-beta.5` / `98f56b3`
- 后端 695 passed；Vitest 53 passed；CI Mock `40087020874`、Real Backend `40087020824`
- `current → beta.5`，`previous → beta.4`

## 5. 剩余非阻塞

H3 固定音色真实视频效果、R2 公共直链、ESLint 历史错误、生产尚未实际触发付费文本解析。
