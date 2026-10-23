# MiniMax H3 官方 Skill 接入与 Renderer 差异审计

## 1. 安装结果

安装命令：

```bash
npx skills add https://github.com/MiniMax-AI/MiniMax-H3 --skill h3-prompt-writing
```

实际安装（项目级，OpenCode）：

- 路径：`.agents/skills/h3-prompt-writing/`
- 安装方式：copy
- 安装清单：`skills-lock.json`
- `skills-lock.json` `computedHash`：`77d059b596e34c1139b859bac30fe5049735bdf49acb70cd63ad8f4e7e329f3c`

上游版本：

- 仓库：https://github.com/MiniMax-AI/MiniMax-H3
- Commit：`d21241f0a4b3acbb34c97dae47fa417b7065e438`
- Commit 时间：2026-08-15 16:31:16 +0800
- Commit 标题：`Merge pull request #44 from GyArmyBrat/improve-skills`

文件校验（与上游该 commit 逐文件 `diff -r` 一致）：

| 文件 | SHA256 |
| --- | --- |
| `SKILL.md` | `a7000443588ca3f145e3b3fd8900f14e0325dc460bd811268fac89a9dc8e56d0` |
| `references/base-en.txt` | `2cfebc096a6e08370f288d468d90b60f7f9bcb938f94bf090816e910e48e75fc` |
| `references/ref-en.txt` | `1e574f356716ad55612247ffb7bbccbcdb484ad96599d63c7dca1af186b1fab7` |

已阅读 `SKILL.md`、`references/base-en.txt`、`references/ref-en.txt`。OpenCode 已能发现 `h3-prompt-writing` Skill。

## 2. 官方规则

### 模式识别

- T2VA：纯文本
- I2VA：首帧
- FL2VA：首尾帧
- L2VA：尾帧
- Ref2VA：多参考素材

DyeingTime 正式多参考工作流固定使用 Ref2VA；不能因为存在一张图就切到 I2VA。

### Ref2VA 六部分

顺序固定：

1. `subject_definitions`
2. `summary`
3. `retention_analysis`
4. `detailed_description`
5. `overall_soundscape`
6. `non_diegetic_music`

### 标签与内容

- `<Subject N>`：可复用视觉主体；一个主体可以由多张 `<Picture N>` 定义。
- `<Picture N>`：具体参考图片；只作为来源时写在 Subject 定义行内，不单独成行。
- `(S1)`/`(S2)`：实际发声的稳定说话人；从不发声的角色不分配 speaker ID。
- 正文英文；仅 `<d>` 内台词/歌词和画面可见文字保留原语言。
- `summary` 以 `[reference generation]` 等任务类型前缀开头。
- `retention_analysis` 使用固定 marker；音频 marker 与可见内容 marker 分开。
- `[Shot 1]` 不带时间戳；后续切镜才使用 `[Shot N] At MM:SS.mmm`。
- 运镜写成自然英文：类型 + 幅度 + 速度。
- `overall_soundscape` 只写环境声/物理声，不重复台词。
- `non_diegetic_music` 只写观众可听的配乐；没有则 `N/A`。

## 3. DyeingTime 自身业务约束

以下规则不属于官方 Skill，但必须继续保留：

- 优云智算网关 Prompt 上限 7000 字符。
- 当前正式生成 5 秒、768P、9:16；默认一个业务 Shot 对应一个 H3 `[Shot 1]`。
- 5 秒短剧使用 200–300 词自适应区间，而不是机械套用官方 350–500 词长示例。
- 结构化对白只来自已确认的 `ShotDialogLine`；禁止模型自行增加剧情对白。
- 默认单一连续场景、连续运镜、不切到另一地点。
- `voice_description` 来自用户配置，不按姓名/照片推断。
- 无对白时显式 `No spoken dialogue`。
- no-narration：只有对白行会被朗读。
- 参考音频默认关闭；固定音色样本属于项目级配置。
- Manifest、Prompt、Snapshot、Provider Payload 必须同源，历史快照不可变，`input_hash` 必须覆盖 Prompt 变化。

## 4. 审计发现与最小修复

### 4.1 已修复

| 差异 | 修复 |
| --- | --- |
| fallback `summary` 使用中文画面描述和 `@角色` | 改为英文，只使用 `<Subject N>` / `<Audio N>` |
| fallback `detailed_description` 含中文画面、动作、氛围、构图 | 英文正文只保留英文自由描述；中文自由描述不进入正文，改为通用英文骨架 |
| fallback 使用 `MS / EYE_LEVEL / STATIC` 内部枚举码 | 映射为 `medium shot / eye-level angle / static camera` 等自然英文 |
| 同一角色多张参考图被拆成多个 Subject | 按 `(kind, ref_id)` 合并，一个 Subject 可带多个 `<Picture N>` |
| `IRShot.subjects` 保存资产名而非标签 | 改为保存 `Subject N` 标签 |
| 中文 `continuity_guidance` 进入英文正文 | 中文连续性建议不写入 H3 正文，保留英文默认连续镜头约束并给 warning |
| 一个业务 Shot 的正文可能自动出现 `[Shot 2+]` | 新增单镜头校验 warning |
| `summary` 可能缺少任务类型前缀 | 新增校验 warning |
| voice profile 比较受句末标点影响，可能重复追加 | 统一去除句末标点后再比较/输出 |
| 质量检查把“do not cut”误判为多机位 | 新增正向切镜判断，忽略否定约束 |
| 男性说话人被其他角色女性代词误报 | 性别冲突检查只看说话人附近片段 |
| 中文骨架可能被朗读成旁白 | 保留并强化 no-narration；fallback 改英文 |

### 4.2 仍存在的差异/风险

- 中文角色名、中文 `voice_description` 仍可能出现在英文正文中（专有名词/用户配置）。no-narration 可降低被朗读概率，但不能保证模型完全忽略。
- 当前本地测试环境没有可用文本模型，fallback 只能输出通用英文骨架；细节丰富的正文需要配置文本模型，或使用经过校验的英文高级 Prompt。
- 官方建议 350–500 词；DyeingTime 5 秒短剧采用更短的自适应区间，这是业务约束，不是官方缺失。
- 高级 Prompt 的校验主要覆盖标签/编号/引用/结构；语义一致性仍需要人工/质量检查辅助。
- 文字 Prompt 不能保证音色身份锁定、不能保证模型绝不切镜。

## 5. 官方 Skill 与运行时引擎的边界

Skill 只是提示词编写规范，不是视频生成引擎。安装成功、Renderer 结构合规，不等于真实视频质量已经提高。真实质量仍需通过 H3 调用与 L4 人工观看确认。

## 6. 复现

```bash
npx skills add https://github.com/MiniMax-AI/MiniMax-H3 --skill h3-prompt-writing --agent opencode --yes --copy
```

版本由 `skills-lock.json` 与上述上游 commit 固定。
