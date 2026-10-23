# P9-C 真实视频缺陷证据

本文件只记录 P9-B2 两条真实 H3 视频及对应不可变生成快照的核对结果。
P9-C 未修改任何历史 `shot_generation_snapshots`，也未自动采纳新视频。

## 1. 01 / `s-e2e-1`

- 内部 Task：`3adb6fa28f2c47d4b1a174a797f7b026`
- 供应商 task：`01a168f7-6bb2-7ec4-b574-a92aa98d29f5`
- Snapshot input_hash：`5767d116ad3711155e2ac0312a9599adb4239d6dd24ef0b13b0555e17c9e2cc1`
- FileItem：`03884933-f923-40ec-b235-4be2d27763e1`
- 规格：768×1344，5.175s，H.264/AAC，2.28MB
- 参考 Manifest：
  - `f-char` / `char-e2e-1` / `av-char1` / `character_identity`
  - `f-scene` / `scene-e2e` / `av-scene` / `scene`
- `ShotDialogLine`：0
- `ShotCharacterLink`：0
- `audio_refs`：0
- `characters.voice_description`：空
- 旧高级 Prompt：

```text
<Subject 1> is the locked female lead. [Shot 1] At 00:00.000, she stands in the hospital duty room and slowly turns her head toward the camera, expression shifting from calm to doubt. <Picture 1> preserves her identity; <Picture 2> preserves the duty room.
```

证据观察：

- 参考图 `f-char` 实际为男性肖像，但资产名为“林晚”；
- Prompt 使用 `female lead` / `she`；
- 无 `<d>`、无“无对白”指令；
- 实际视频中男性角色有说话表现，并出现女性声音（用户反馈）；
- 审核记录：`unsatisfied` + `角色声音不匹配` + `说话人归属错误`。

确认程度：

- 输入缺失：已确认；
- Prompt 性别指代冲突：已确认；
- H3 内部为何选择女性声音：推测，无法从供应商响应确认。

## 2. 02 / `s-e2e-2`

- 内部 Task：`92aa30e950b04a50a7803fb0fd4f0a2a`
- 供应商 task：`01a168fd-10d7-78bb-be26-dcd4fa51d6aa`
- Snapshot input_hash：`39cf21753926e0016c72d165230e13d0c3f455602af52baee0a5404d5d30d03e`
- FileItem：`a56f5198-112b-4cfc-af85-461bc7e78bd5`
- 规格：768×1344，5.175s，H.264/AAC，2.27MB
- 参考 Manifest：
  - `f-char` / `char-e2e-1` / `av-char1` / `character_identity`
  - `f-char2` / `char-e2e-2` / `av-char2` / `character_identity`
  - `f-scene` / `scene-e2e` / `av-scene` / `scene`
- `ShotDialogLine`：0
- `ShotCharacterLink`：0
- `audio_refs`：0
- 旧高级 Prompt：

```text
<Subject 1> and <Subject 2> are the two locked leads. [Shot 1] At 00:00.000, they talk in the duty room; he explains, she looks suspicious. <Picture 1> and <Picture 2> keep the two identities separate; <Picture 3> preserves the room.
```

证据观察：

- 场景图已进入 Manifest；
- Prompt 未要求同一连续镜头，也未禁止切到另一地点；
- 5 秒视频内部出现“人物特写 → 双人景 → 人物特写”，首尾特写背景与参考场景图不一致；
- 审核记录：`unsatisfied` + `场景/背景不连续` + `镜头切换异常`。

确认程度：

- 场景参考存在但缺少连续性约束：已确认；
- H3 在同一条视频内部自动切镜：高概率（视觉证据）；
- 切镜的具体模型内部决策：推测。

## 3. 新旧 Prompt 对照

对比条件：真实快照 + 当前代码；关闭 LLM 正文，使用确定性 IR 骨架；所有数据库改动均在事务内回滚。
真实提交前必须重新预览，以新预览返回的 `input_hash` 为准。

| 场景 | 旧 hash | 新默认 hash | 受控重抽 hash |
| --- | --- | --- | --- |
| 01 / s1 | `5767d116…e2cc1` | `0c0bf968…857d4` | 方案 A `054080d5…3966e` |
| 02 / s2 | `39cf2175…d30d03e` | `175de974…7fe21` | 方案 B `0dc4c4d9…a7a8215` |

新默认 01 关键片段：

```text
Sound: No spoken dialogue is requested; characters do not speak. Use only ambient room tone and natural physical sounds.
Continuity: … Keep the entire video in one continuous scene at 医院值班室; … do not cut to another location.
```

方案 A 01 关键片段：

```text
<Subject 1> (S1), using this voice profile: 年轻成年男性声音，音色清晰，语速适中，情绪克制, says, <d>[Chinese] 你先听我解释。</d>
Characters who are not speaking keep their mouths closed and only react physically.
```

方案 B 02 关键片段：

```text
<Subject 2> (S1), using this voice profile: 成年女性声音，冷静，语气有压迫感, says, <d>[Chinese] 你听我解释，事情不是你想的那样。</d>
<Subject 1> (S2), using this voice profile: 年轻成年男性声音，音色低沉，语速偏慢, says, <d>[Chinese] 那你告诉我，钥匙为什么在你口袋里？</d>
Characters who are not speaking keep their mouths closed and only react physically.
Continuity: … Keep the entire video in one continuous scene at 医院值班室; … do not cut to another location.
```

## 4. 保留项

- 旧视频：`/tmp/opencode/s-e2e-1.mp4`、`/tmp/opencode/s-e2e-2.mp4`（未提交 Git）。
- 旧采纳指针：`s-e2e-1 -> v-e2e-1`、`s-e2e-2 -> v-e2e-2`，未改变。
- 审核记录已写入既有 `shot_video_reviews`。
- 历史 Snapshot 的 `input_hash` 与 `prompt` 未改变。
