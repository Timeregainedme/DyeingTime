# P10-C2 AI 分镜质量修复与 DeepSeek 真实验收

> 版本：`v2-internal-beta.5`
>
> 代码基线：`98f56b3`
>
> 生产：`https://tim.run.place/`

## 1. 结论

**P10-C2 通过。** 首次真实 DeepSeek 分镜规划即覆盖全部 3 个场次，6 个镜头均具备有效标题、画面描述、视频 Prompt、角色与对白；短信被正确标记为 `SCREEN_TEXT`，不再作为人声。

未使用人工修改镜头归属来“补救”AI 结果；人工只做了两件事：

1. 解析阶段把 2 条短信从 `PHONE` 改为 `SCREEN_TEXT`（模型已在其 `issues` 中主动提示）。
2. 为角色上传既有图片并锁定身份（这是生成前置资产，不属于分镜内容修正）。

## 2. beam-free 原始失败基线（P10-C 保留）

| 问题 | 实际表现 |
| --- | --- |
| 场次 | 6 镜头全部第 1 场，车库/公寓无镜头 |
| scene_group_index | 缺失，Pydantic 默认成 1 |
| 标题 | 全部“镜头 1” |
| 描述 / Prompt | 为空 |
| 对白 | 第 6 镜把短信当顾言口语 |

原始草稿：`2ee8a4b8-7fb0-4745-ad25-aafb748aabb7`（保留于验收库）。

## 3. 根因（代码/数据依据）

| 编号 | 根因 | 依据 |
| --- | --- | --- |
| A | 输入缺 SceneBeat、已确认对白索引/类型 | 旧 Prompt 只传 scene_groups/characters/assets/script |
| B | Prompt 只写“每个场次必须覆盖”，没有逐场次硬校验 | 旧 system prompt 第 5 条 |
| C | 解析器没有丢字段，但字段缺失被默认值掩盖 | `PlannedShot.scene_group_index=1`、`title=""` |
| D | Schema 未要求 scene_group_index/title/description/video_prompt/action_beats | `app/schemas/skills/shot_planning.py` |
| E | 模型可输出空描述/空 Prompt 且通过校验 | 同上 |
| F | 缺场次静默落到第 1 场；缺标题落“镜头 N” | `planned.title or f"镜头 {order}"` |
| G | `DialogueMode` 无 SCREEN_TEXT；H3 renderer 对未知 mode 默认“says” | `app/models/types.py`、`h3.py` |
| H | 30s/7 对白没有时长风险提示，只统计原文覆盖率 | `_coverage` |

## 4. 修复内容

### 4.1 Schema

- `scene_group_index`、`order`、`title`、`action_beats`、`visual_description`、`video_prompt_draft` 改为必填；描述/Prompt 至少 10 字符。
- 新增 `source_dialogue_index`（1-based）。
- `line_mode` 扩展为 `DIALOGUE / VOICE_OVER / OFF_SCREEN / PHONE / NARRATION / SCREEN_TEXT / ACTION`。
- 解析 Schema 对 `SMS/MESSAGE/TEXT/SUBTITLE/NARRATOR` 做归一化，避免整份解析因一个词失败。

### 4.2 Prompt

输入新增：

- `scene_beats_json`
- `dialogues_json`（index/text/speaker/line_mode/emotion）
- `shot_budget`
- `repair_feedback`

硬约束新增：

- 每个场次至少 1 镜，场次顺序不得打乱；
- 标题必须描述画面，禁止“镜头 N”，不得重复；
- 描述/Prompt 必须包含主体、动作、环境；
- 对白必须带 `source_dialogue_index`，说话人必须与原文一致；
- 短信/屏幕文字必须 `SCREEN_TEXT`，旁白 `NARRATION`，不得当人物口语；
- 无法容纳的对白写入 coverage_notes，不得静默删除；
- 修复时必须逐条处理 blocking 问题并输出完整 JSON。

### 4.3 质量检查

- 场次无镜头：coverage warning + `missing_scene_groups`。
- 确认时若仍有场次无镜头：直接拒绝（409）。
- 缺 `scene_group_index`：blocking。
- 重复标题：blocking。
- 标题只有序号：blocking。
- 描述/Prompt 过短：blocking。
- 对白 source index 缺失/越界、类型非 DIALOGUE、说话人不一致、文本不一致：blocking。
- 资产不存在/跨项目/版本不匹配：blocking（既有）。
- 角色未锁定身份：blocking（既有，属于生成前置条件）。

### 4.4 受控修复

- `SHOT_PLAN_MAX_REPAIRS` 控制最大修复次数；默认 0，验收环境设为 1。
- 修复只针对 Schema 失败、场次缺失、重复标题；不覆盖已确认镜头。
- 原始失败信息写入 `draft.coverage.repair_log`。
- 不会无限重试；预算耗尽保留候选与错误。

### 4.5 H3 渲染

- `SCREEN_TEXT` 渲染为“屏幕显示 …，无人朗读、无人声”，不再走 `says`。
- `ACTION` 不进入正文；`NARRATION` 走 VOICE_OVER。
- H3 prompt 明确区分“可见文字”和“需要人声的台词”。

## 5. 真实 DeepSeek 调用

供应商：OpenCode Go；模型：`deepseek-v4.1-flash`；价格 $0.15 / $0.60 per 1M input/output tokens。

| 调用 | 用途 | Input | Output | 费用 |
| --- | --- | ---: | ---: | ---: |
| 1 | 解析首次（结构化调用 + 回退，共 2 次 HTTP） | 3,656 + 7,932 | 6,000 + 411 | $0.005585 |
| 2 | 解析重试（Schema 失败） | 1,269 | 8,965 | $0.005569 |
| 3 | 解析成功 | 3,669 | 5,467 | $0.003831 |
| 4 | 分镜规划首次 | 4,256 | 6,005 | $0.004241 |
| **合计** | | **20,782** | **26,848** | **$0.019226** |

**低于 $0.05 授权上限**。未新增图片/TTS/H3 调用；未充值。

说明：解析前两次失败分别暴露了 `max_tokens` 不足和 `DialogueMode` 枚举过严；第 3 次成功，分镜首次即成功，未使用规划修复额度。

## 6. 解析结果

运行 `19abb6c3-c2df-4f32-88a3-b60128568624`，1 chunk，26 条候选：

- 角色 2：沈知微（别名“沈总”）、顾言
- 场景 3：办公室、地下车库、公寓客厅
- 对白 9：7 条口语 + 2 条短信
- SceneBeat 3、道具 2、服装变化 1、问题 5

人工修正：短信 2 条 `PHONE → SCREEN_TEXT`，不带说话人。

确认结果：2 角色、3 场景（复用已有全局场景）、1 新建道具 + 1 关联、1 新建服装 + 1 关联、9 对白、3 场次节拍。

## 7. 分镜结果

草稿 `7e10228b-7e57-4c25-bc3f-e49629179234`，目标 30s，6 镜头：

| # | 场次 | 标题 | 景别/运镜 | 时长 |
| --- | --- | --- | --- | ---: |
| 1 | 办公室 | 暴雨窗前，顾言抱着湿报告推门而入 | LS / STATIC | 5 |
| 2 | 办公室 | 沈知微转身下令“念”，顾言报出两点十七分 | MS / STATIC | 6 |
| 3 | 办公室 | 指尖停在报告右下角签名，报告被放回桌面 | CU / DOLLY_IN | 5 |
| 4 | 地下车库 | 车库电梯开门，她快步走向黑车后停下说“那就查” | MLS / TRACK | 6 |
| 5 | 公寓客厅 | 清晨灰色家居服坐在沙发上，手机亮起“等你决定” | MS / DOLLY_IN | 4 |
| 6 | 公寓客厅 | 盯着屏幕许久后打出“先不要告诉任何人” | CU / DOLLY_IN | 4 |

- 三场覆盖：3 / 1 / 2 镜。
- 标题、描述（121–152 字）、视频 Prompt（128–149 字）全部非空且可区分。
- 对白：7 条 DIALOGUE 说话人正确；2 条 `SCREEN_TEXT`，无说话人，不进入人声。
- 总时长 30s，与目标一致。
- 首次规划无 blocking；仅原文覆盖率 27% 的 warning（对白完整，属于 action 文本未计入来源区间）。
- 人工确认后写入 6 个 Shot，`confirm` 二次调用不新增镜头。

## 8. 人工确认与下游

- 6 个 Shot、ShotDetail、ShotCharacterLink、ShotDialogLine、ShotAssetVersion 全部写入。
- 角色身份锁定后无 blocking；参考推荐得到 2 角色 + 1 场景。
- H3 preview：无 blocking，`<Picture 1..3>` 与 manifest 一致；对白在 `<d>` 内；短信不出现在人声正文。
- 未调用 H3 视频。

## 9. 测试与发布

| 项 | 结果 |
| --- | --- |
| 后端 | **695 passed, 2 deselected** |
| TypeScript | 通过 |
| Vitest | 53 passed |
| Build | 通过 |
| OpenAPI | 契约一致 |
| ESLint | 86 个历史 error，本轮无新增 |
| Mock E2E | `40087020874` success |
| Real Backend E2E | `40087020824` success |
| Staging | 新 `SCREEN_TEXT` 枚举创建/查询通过，测试项目已删除 |

发布：

- `v2-internal-beta.4`（中间版本，含 Schema/质量修复）
- **`v2-internal-beta.5`（最终）**，Commit `98f56b3`
- `current → beta.5`，`previous → beta.4`
- 生产数据保持：3 项目 / 19 镜头 / 33 文件 / 7 已采纳视频
- 健康检查正常；磁盘 32%

## 10. P10-C 最终判定

| 门槛 | 结果 |
| --- | --- |
| 真实剧本解析 | ✅ DeepSeek 隔离验收通过 |
| 真实 AI 分镜规划 | ✅ 首次输出即覆盖 3 场、6 镜、对白/短信正确 |
| 图片候选/身份锁定 | ✅ |
| TTS/音色/音频参考 | ✅ 链路通过；H3 真实音色效果仍未验证 |
| 跨模块一致性 | ✅ |
| 视频审核/采纳/ZIP | ✅ |
| 权限/幂等/额度 | ✅ |
| AWS/生产健康 | ✅（云侧 DescribeVolumes 仍受限） |
| 验收矩阵 | ✅ |

**P10-C 可以标记完成。** 剩余非阻塞项：H3 固定音色真实视频效果、R2 公共直链、ESLint 历史错误、生产环境尚未实际触发一次付费文本解析（隔离验收已通过）。

## 11. ToonFlow

`Next Phase: ToonFlow Usage & Case Study`

`READY_FOR_TOONFLOW_RESEARCH`

本阶段未读取、扫描、比较或修改任何 ToonFlow 资料。
