---
title: "P9-C 真实视频质量缺陷修复"
description: "针对 01 声音错配与 02 背景不连续的真实输入诊断、Prompt / 声音 / 连续性约束修复、质量检查与受控重抽方案。"
weight: 6
---

> 状态：**P9-C 代码与不收费回归已完成；未发起新的真实视频生成。**
>
> 本文记录真实缺陷证据、已落地的约束、下一轮受控重抽方案与剩余模型能力边界。
> 历史生成快照、旧视频和当前采纳指针均未修改。

## 1. 缺陷与真实证据

两条视频来自 P9-B2 真实 MiniMax H3 调用：

| 项目 | 01 / `s-e2e-1` | 02 / `s-e2e-2` |
| --- | --- | --- |
| 内部 Task | `3adb6fa28f2c47d4b1a174a797f7b026` | `92aa30e950b04a50a7803fb0fd4f0a2a` |
| 供应商 task | `01a168f7-6bb2-7ec4-b574-a92aa98d29f5` | `01a168fd-10d7-78bb-be26-dcd4fa51d6aa` |
| 快照 input_hash | `5767d116…e2cc1` | `39cf2175…d30d03e` |
| 参考图 | 角色 `f-char` + 场景 `f-scene` | 角色 `f-char` / `f-char2` + 场景 `f-scene` |
| `ShotDialogLine` | 0 条 | 0 条 |
| `ShotCharacterLink` | 0 条 | 0 条 |
| 参考音频 | 0 条 | 0 条 |
| 高级 Prompt | `locked female lead / she` | `they talk … he explains, she looks suspicious` |
| 实际审核 | unsatisfied：角色声音不匹配、说话人归属错误 | unsatisfied：场景/背景不连续、镜头切换异常 |

### 1.1 01 声音错配

已确认的输入事实：

- `ShotDialogLine` 为空，`ShotCharacterLink` 为空，`characters.voice_description` 为空；
- 项目未开启 `use_dialog_audio_as_reference`，没有任何音色参考音频；
- 高级 Prompt 明确写 `female lead` 与 `she`；
- 镜头资产版本指向 `char-e2e-1`（资产名“林晚”），但其采纳参考图实际是**男性肖像**；
- 自然提示词没有要求说话，也没有任何 `<d>` 台词块或“无对白”指令。

结论与确认程度：

- **已确认（输入级）**：系统没有结构化说话人、没有声音描述、没有参考音频，并且 Prompt 的性别指代与参考图呈现不一致。
- **高概率（Prompt 级）**：H3 依据 `female lead / she` 分配了女性声音，同时自行生成了说话/口型；因为 Prompt 既没有 `<d>`，也没有 `No spoken dialogue`。
- **推测（模型内部）**：无法从供应商响应确认 H3 内部如何在“男性参考图”和“女性文本指代”之间做取舍；该部分不计为后端数据错误。

> 关键原则：系统不得根据角色名“林晚”或照片自动推断性别/音色。当前修复要求用户显式提供 `voice_description`，并检测 Prompt 指代与声音描述冲突。

### 1.2 02 背景不连续

已确认的输入事实：

- 场景 `scene-e2e` 已绑定 `ShotAssetVersion(scene)=av-scene`，`f-scene` 在 Reference Manifest 中；
- 高级 Prompt 只写 `they talk in the duty room`，没有明确“同一连续镜头 / 不切到另一地点”；
- 5 秒镜头内出现“人物特写 → 双人景 → 人物特写”的构图变化；
- 参考场景图是带玻璃隔断的办公室/值班区，而视频首尾特写背景是深色墙面，双人景才接近参考图。

结论与确认程度：

- **已确认（输入级）**：Prompt 没有单一连续场景约束，且描述包含多个构图层级；场景图虽在 manifest 中，但没有任何机制保证正文把它当作全片空间锚点。
- **高概率（模型行为）**：H3 在同一条 5 秒视频内部自动切镜，并在特写镜头重建了不同背景；这不是两个正式 Shot 之间的 Scene ID 不一致。
- **推测（模型内部）**：无法确认 H3 是否把特写理解为另一空间；当前通过“默认单一连续镜头 + 禁止切到另一地点 + 场景锚点”降低概率，不能保证 100% 消除。

## 2. 已落地的修复

### 2.1 说话人与声音（P9-C1）

- `ShotDialogLine.speaker_character_id` 是正式说话人来源；不再按角色名或照片猜测。
- `ShotVideoPromptPackRead.dialogues` 增加 `speaker_character_id` / `voice_description`。
- `IRDialogueInput` / `IRDialogueLine` 保留这两个字段，H3 Renderer 在台词句中输出：
  - `using this voice profile: <用户描述>, says, <d>[Chinese] …</d>`；
  - 非说话角色明确写 `Characters who are not speaking keep their mouths closed and only react physically.`。
- 没有结构化台词时，IR 写入：
  - `No spoken dialogue is requested; characters do not speak. Use only ambient room tone and natural physical sounds.`
- H3 正文 Agent 的系统提示增加：
  - 不按角色名、照片或性别刻板印象判断声音；
  - 必须保留 voice profile；
  - 无声镜头必须写无对白；
  - 默认单一连续镜头，只有明确要求多机位时才写切镜。
- Renderer 对 LLM 正文做**确定性补齐**：LLM 漏写台词、voice profile、无对白、连续性时，渲染阶段追加缺失约束。LLM 只负责文风，不能丢掉关键输入。

### 2.2 场景连续性（P9-C2）

- IR 默认追加连续性约束：
  - 场景已知：`Keep the entire video in one continuous scene at <场景>; keep the background layout, lighting direction and character positions consistent; use continuous camera movement and do not cut to another location.`
  - 场景未知：只要求同一连续空间与一致背景，不虚构地点。
- `build_shot_video_prompt_pack` 增加场景兜底：
  - 优先 `ShotDetail.scene_id`；
  - 其次 `ShotAssetVersion(scene)`；
  - 只补 Prompt 上下文，**不自动把场景图塞进参考图列表**。
- 高级 Prompt 不会被静默改写；如果缺少 `<d>` 或连续性约束，质量检查给出 warning，并提示清空高级 Prompt 或补齐约束。
- 场景参考被用户移除时保留用户选择，只提示 `scene_reference_missing`，不静默恢复。

### 2.3 质量检查（P9-C3）

`ShotVideoReadinessRead.quality_checks` 与硬性 `checks` 分离。级别：

- `blocking`：输入数据无法正确构建，阻止提交并进入 `blocking_errors`；
- `warning`：高概率质量风险，不阻止生成；
- `info`：已满足的约束或可优化建议。

规则清单：

| code | 级别 | 触发条件 |
| --- | --- | --- |
| `dialogue_speaker_unknown` | blocking | 台词引用的说话角色不存在 |
| `dialogue_speaker_project_mismatch` | blocking | 说话角色不属于当前项目 |
| `dialogue_speaker_missing` | warning | 有台词但未确认说话人 |
| `dialogue_speaker_not_linked` | warning | 对白说话人不在镜头角色资产版本中 |
| `dialogue_speaker_offscreen` | info | 画外音/旁白说话人不在画面角色中 |
| `character_voice_missing` | warning | 说话角色没有声音描述 |
| `dialogue_speaker_ambiguous` | warning | 多说话人场景中仍有台词未确认归属 |
| `advanced_prompt_missing_dialogue` | warning | 高级 Prompt 缺少 `<d>` 台词块 |
| `advanced_prompt_missing_continuity` | warning | 高级 Prompt 未明确同一场景/连续镜头 |
| `prompt_voice_gender_conflict` | warning | Prompt 性别指代与用户声音描述冲突 |
| `advanced_prompt_without_structured_dialogue` | warning | 高级 Prompt 存在但无结构化台词 |
| `advanced_prompt_may_invent_speech` | warning | 高级 Prompt 既无 `<d>` 也无“无对白” |
| `prompt_dialogue_without_lines` | warning | Prompt 疑似有对白但无结构化台词 |
| `prompt_gender_claim_unverified` | warning | Prompt 含性别化主角描述但无声音描述依据 |
| `voice_reference_unavailable` | warning | 项目开启音色参考但样本/说话人不可用 |
| `voice_reference_ready` | info | 已配置音色参考 |
| `voice_reference_disabled` | info | 未开启音色参考，文字描述不能锁定音色 |
| `scene_asset_unknown` | blocking | `ShotAssetVersion(scene)` 引用的场景不存在 |
| `scene_version_missing` | warning | 镜头未绑定场景资产版本 |
| `scene_version_mismatch` | warning | `ShotDetail.scene_id` 与场景资产版本不一致 |
| `scene_reference_missing` | warning | 场景版本存在但场景图未进入参考图 |
| `scene_reference_version_mismatch` | warning | 场景参考图版本与场景资产版本不一致 |
| `scene_reference_ready` | info | 场景参考已进入参考图并参与 input_hash |
| `short_shot_multi_camera` | warning | ≤6 秒镜头描述含多机位/切镜线索 |
| `shot_multi_camera` | warning | 更长镜头含多机位/切镜线索 |
| `single_continuity_default` | info | 未检测到切镜线索，按单一连续镜头生成 |
| `multiple_location_cues` | warning | 描述可能包含多个地点/环境 |

## 3. 新旧 Prompt 对照

对照使用**同一份真实快照 + 当前代码**生成；为避免调用文本模型，对比时关闭 LLM 正文，使用确定性 IR 骨架。真实提交前必须重新预览，以新预览返回的 `input_hash` 为准。

### 3.1 01 / `s-e2e-1`

旧 Prompt：

```text
<Subject 1> is the locked female lead. [Shot 1] At 00:00.000, she stands in the hospital duty room and slowly turns her head toward the camera, expression shifting from calm to doubt. <Picture 1> preserves her identity; <Picture 2> preserves the duty room.
```

新默认（无结构化台词）：

```text
Sound: No spoken dialogue is requested; characters do not speak. Use only ambient room tone and natural physical sounds.
Continuity: … Keep the entire video in one continuous scene at 医院值班室; keep the background layout, lighting direction and character positions consistent; use continuous camera movement and do not cut to another location.
```

方案 A（补结构化男声台词）：

```text
<Subject 1> (S1), using this voice profile: 年轻成年男性声音，音色清晰，语速适中，情绪克制, says, <d>[Chinese] 你先听我解释。</d>
Characters who are not speaking keep their mouths closed and only react physically.
```

| 对照项 | 旧快照 | 新默认 | 方案 A |
| --- | --- | --- | --- |
| input_hash | `5767d116…e2cc1` | `0c0bf968…857d4` | `054080d5…3966e` |
| 对白 | 无 | 明确无对白 | 1 条结构化台词 |
| 声音 | 无 | 禁止说话 | 男性 voice profile |
| 场景 | 仅文字 `duty room` | 明确医院值班室 + 连续镜头 | 同左 |

### 3.2 02 / `s-e2e-2`

旧 Prompt：

```text
<Subject 1> and <Subject 2> are the two locked leads. [Shot 1] At 00:00.000, they talk in the duty room; he explains, she looks suspicious. <Picture 1> and <Picture 2> keep the two identities separate; <Picture 3> preserves the room.
```

方案 B（双人轮流说话 + 场景连续）：

```text
<Subject 2> (S1), using this voice profile: 成年女性声音，冷静，语气有压迫感, says, <d>[Chinese] 你听我解释，事情不是你想的那样。</d>
<Subject 1> (S2), using this voice profile: 年轻成年男性声音，音色低沉，语速偏慢, says, <d>[Chinese] 那你告诉我，钥匙为什么在你口袋里？</d>
Characters who are not speaking keep their mouths closed and only react physically.
Continuity: … Keep the entire video in one continuous scene at 医院值班室; … do not cut to another location.
```

| 对照项 | 旧快照 | 新默认 | 方案 B |
| --- | --- | --- | --- |
| input_hash | `39cf2175…d30d03e` | `175de974…7fe21` | `0dc4c4d9…a7a8215` |
| 对白 | 无 `<d>`，仅 “they talk” | 明确无对白 | 2 条轮流台词 |
| 声音 | 无 | 禁止说话 | 女声 + 男声 voice profile |
| 场景 | 场景图存在但无连续性约束 | 明确同一场景、禁止切镜 | 同左 |

## 4. 测试结果

- 后端：`uv run pytest tests -q` → **677 passed, 2 deselected**。
- 前端 TypeScript：`pnpm exec tsc --noEmit` → 通过。
- 前端 ESLint（本次改动文件）：通过；仓库全量 ESLint 仍有既有历史错误，未在本阶段扩大修复范围。
- Vitest（Node 22）：**49 passed**。
- 前端构建：`pnpm run build` → 通过。
- OpenAPI：`pnpm run openapi:check` → 契约一致。
- Mock 浏览器 E2E：**26 passed**（新增质量风险与视频审核标签交互）。
- 真实后端浏览器 E2E：**2 passed**（真实 FastAPI + MySQL + 本地 S3；质量检查列表可见）。

## 5. 真实额度

已重新读取隔离环境 `generation_quotas`，未按文字报告覆盖数据库：

| 类型 | 累计上限 | 已消耗 | 已预留 | 剩余 |
| --- | ---: | ---: | ---: | ---: |
| 图片 | 40 | 0 | 0 | 40 |
| 视频 | 8 | 3 | 0 | 5 |
| 音频 | 1000 | 0 | 0 | 1000 |

- 上限由 `backend/sql/049-raise-v2-acceptance-quota.sql` 提升，**未重置已消耗**。
- 供应商积分：P9-B2 后 `9893.02`；P9-C 未发起真实图片/视频/音频调用，积分未变化。
- 视频已消耗 3 次包含 1 次失败协议探测；失败探测未消耗供应商积分。

## 6. 下一轮受控重抽方案

> 两个方案都必须由用户明确选择后执行；不要为了验证代码自动连续消耗额度。

### 方案 A：修复 01 声音

目标：验证“结构化说话人 + 用户声音描述 + 无对白/说话约束”是否能让男性角色使用男声。

执行步骤：

1. 在隔离测试库为 `s-e2e-1` 增加 `ShotDialogLine`：
   - `speaker_character_id=char-e2e-1`
   - `text=你先听我解释。`
   - `line_mode=DIALOGUE`
2. 设置 `characters.voice_description=年轻成年男性声音，音色清晰，语速适中，情绪克制。`
3. 清空该镜头高级 Prompt（避免旧 `female lead/she` 继续覆盖），用新预览生成最终 Prompt。
4. 确认预览包含 `<d>`、`using this voice profile`、单一连续场景；记录新 `input_hash`。
5. 提交 1 次真实 H3：5 秒 / 768P / 9:16 / 2 张参考图 / `auto_adopt=false`。

成本与风险：

- 预计 1 次视频额度、约 50 供应商积分；本地剩余 5 次。
- 风险：文字声音描述不是音色身份锁定；H3 仍可能自行选择音色。若失败，下一步才考虑固定音色参考或独立配音，不在本阶段扩展。
- 重点观察：说话人是否与画面男性一致、声音是否男性、口型是否只出现在说话人。

### 方案 B：修复 02 背景连续性

目标：验证“同一连续场景 + 禁止切镜 + 场景版本参考”是否能消除同片内背景跳变。

执行步骤：

1. 保留两个角色身份参考与 `scene-e2e` 场景参考；
2. 为 `s-e2e-2` 增加结构化轮流台词（示例见 3.2），或保持无对白并确认“无对白”约束；
3. 清空旧高级 Prompt，使用新预览；确认 `Continuity` 明确医院值班室与 `do not cut to another location`；
4. 记录新 `input_hash`，提交 1 次真实 H3：5 秒 / 768P / 9:16 / 3 张参考图 / `auto_adopt=false`。

成本与风险：

- 预计 1 次视频额度、约 50 供应商积分。
- 风险：H3 可能在 5 秒内仍做特写/双人景切换；Prompt 只能降低概率，不能保证模型不切镜。若仍失败，应拆分 Shot 或在后期剪辑，而不是继续堆 Prompt。

### 建议顺序

**先执行方案 A。** 理由：声音/说话人错配直接破坏角色身份，是短剧的硬缺陷；方案 A 同时验证结构化对白与 voice profile 的主链路。方案 B 可在 A 结果确认后单独执行，避免一次消耗两次额度。

## 7. 当前边界

- 已修复：说话人来源、声音描述传递、无对白指令、默认连续镜头、场景兜底、质量检查分级、审核标签。
- 需真实模型再次验证：男声是否稳定、H3 是否仍自行切镜、文字描述能否稳定控制音色。
- 无法由 Prompt 保证：音色身份锁定、模型内部镜头切换、参考图与资产名/描述冲突时的模型取舍。
- 历史快照、真实视频、当前采纳指针均保持不变；没有自动采纳新视频。
