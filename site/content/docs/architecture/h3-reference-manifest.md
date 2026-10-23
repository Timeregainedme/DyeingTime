---
title: "H3 多参考 Manifest 与生成输入快照"
description: "记录 P6 / C11 的镜头参考绑定、@ 引用、H3 同源预览、准备度与不可变生成输入快照。"
weight: 31
---

> 本文属于“当前架构”，描述 P6 / C11 已落地的实现。

## 1. 核心原则

预览与真实提交必须使用同一份：

```text
ShotAssetVersion
  → ShotReferenceBinding（有序 manifest）
  → IR references / Subject-Picture 编号
  → 最终 H3 Prompt
  → Generation Input Snapshot
  → GenerationTask run_args
```

任何一步重新自动推荐或读取“最新版本”都会破坏一致性，因此 P6 正式路径使用显式 manifest，而不是旧 IR 的自动资产收集。

## 2. 数据模型

### `shot_reference_bindings`

- `shot_id`
- `file_id`（FileItem）
- `asset_type` / `asset_id` / `asset_version_id`
- `reference_role`：角色身份/造型、场景、道具、服装、镜头构图、上一镜
- `source`：auto / manual / uploaded
- `sort_order`
- `is_pinned`
- `is_active`

同一镜头同一文件唯一；删除参考图是 `is_active=false`，不是物理删除历史绑定。

### `shot_prompt_references`

保存自然语言提示词中的 `@` 引用：

- 资产类型/ID/版本
- 原始 mention
- 字符区间

### `shot_generation_snapshots`

不可变生成输入：

- 镜头/项目/章节/场次
- 模型/供应商
- manifest（文件、资产、版本、角色、顺序）
- 最终 prompt / 自然语言 prompt / 高级 prompt
- @ 引用
- 音频参考
- 镜头资产版本
- 比例、分辨率、时长、input_hash

## 3. 自动推荐

优先读取 P5 `shot_asset_versions`：

1. 角色身份版本；
2. 角色当前造型；
3. 场景；
4. 道具；
5. 服装。

图片来自 P4 已采纳候选（`asset_image_candidates.is_adopted`），旧资产在没有版本候选时，仅当版本就是当前版本才回退到旧图片槽位。

规则：

- 软推荐 3–7 张，硬上限 9 张；
- 不添加无关素材；
- 人工删除的自动项不会再次推荐；
- 人工锁定项不能被自动推荐删除；
- 超过硬上限阻止生成，不做静默截断。

## 4. `@` 引用

正则解析 `@名称`：

- 角色正式名 + `character_aliases` 别名；
- 场景、道具、服装名称；
- 同名/别名歧义返回未解析，要求人工处理；
- 解析结果保存稳定 asset_id/version_id，角色改名后引用仍指向同一 Character；
- 未解析 `@` 进入阻塞错误。

## 5. 预览与生成

`build_generation_preview`：

1. 读取 active bindings；
2. 生成 manifest 与 IRReference（`图N`）；
3. 构建 H3 IR，显式传入 references，不再自动收集；
4. 生成最终 H3 prompt；
5. 返回参考文件顺序、音频、prompt、warnings、blocking_errors、input_hash。

高级 prompt：

- 可覆盖最终 prompt；
- 必须校验 `<Picture N>` / `<Audio N>` 不超过 manifest/音频上限；
- 不再静默修补编号。

`create_video_task` 使用同一 preview 构建 run_args，并写 `shot_generation_snapshots`。
新路径默认 `auto_adopt=false`：生成完成只新增候选，不自动覆盖当前视频。

## 6. 准备度

在既有 readiness 上追加：

- 参考绑定存在、文件存在；
- 参考图不超 H3 上限；
- 镜头资产版本存在；
- 角色视觉身份已锁定；
- 提示词 @ 引用均可解析；
- 既有模型/供应商/时长/任务/参考帧检查继续生效。

## 7. API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/studio/shots/{id}/reference-bindings` | 参考列表 |
| `POST` | `.../reference-bindings/recommend` | 自动推荐 |
| `PATCH/DELETE` | `.../reference-bindings/{bid}` | 锁定/启停/删除 |
| `POST` | `.../reference-bindings/reorder` | 排序 |
| `POST` | `.../reference-bindings/upload` | 镜头专属上传 |
| `POST` | `.../prompt/resolve` | 解析 @ |
| `PUT` | `.../prompt` | 保存提示词 |
| `POST` | `.../generation-preview` | 同源预览 |
| `POST` | `.../generation` | 单镜头生成 |
| `GET` | `.../generation-snapshots` | 快照历史 |
| `GET` | `/api/v1/studio/generation-snapshots/{id}` | 快照详情 |

## 8. 当前边界

- 图片上传只做镜头参考，不自动生成图片；
- 音频参考仍复用现有台词配音文件；固定音色样本扩展由 P6 音频链路确认；
- 额度门禁、批量任务、视频审核在 C12/C13/C14 继续。
