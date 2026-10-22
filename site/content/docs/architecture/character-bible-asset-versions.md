---
title: "角色圣经与资产版本"
description: "记录 P4 已生效的角色身份、别名、图片候选、视觉锁定、造型/资产衍生版本与音色绑定实现。"
weight: 27
---

> 本文属于“当前架构”，描述 P4 / C7 已落地的实现。
> 受影响镜头分析见 [资产变更影响分析](/docs/architecture/asset-impact-analysis/)。
> P3 剧本确认产生的资产见 [剧本结构化解析与统一审核](/docs/architecture/script-parse-review/)。

## 1. 概念边界

| 概念 | 数据 | 说明 |
| --- | --- | --- |
| 角色身份 | `characters` + `asset_versions(version_kind=identity)` | 剧情中的同一个人；正式名称、别名、基础外貌、身份版本、锁定状态 |
| 演员 | `actors` | 工作区级共享资源；可被多个项目角色绑定，不能因项目角色锁定而冻结 |
| 角色造型 | `asset_versions(version_kind=appearance)` | 同一角色的服装/发型/妆容/年龄/环境状态变体；不改变身份 |
| 资产基础版本 | `asset_versions(version_kind=base)` | Scene/Prop/Costume 的当前基础快照 |
| 资产衍生版本 | `asset_versions(version_kind=derived)` | 夜景、雨淋、破损、灯光变化等 |
| 图片候选 | `asset_image_candidates` | 一次生成或上传得到的图片；不等于已采纳 |
| 已采纳图片 | `asset_image_candidates.is_adopted=true` | 用户明确选中的图片；同一版本同一视角只保留一个 |
| 角色音色 | `characters.voice_id` / `voice_source` | 与视觉身份独立；未绑定视觉锁定不受影响 |

`Character` / `Scene` / `Prop` / `Costume` 仍是唯一业务主实体。版本通过
`asset_type + asset_id` 多态引用，不复制主实体，也不新增平行资产系统。

## 2. 数据模型

### 2.1 `character_aliases`

| 字段 | 说明 |
| --- | --- |
| `character_id` | 指向稳定角色 ID |
| `alias` | 原始称谓 |
| `normalized_alias` | 去空白/小写后的匹配键 |
| `source` | `manual` / `p3_parse` |

- 同一角色内别名唯一。
- 同项目不同角色使用相同别名时，服务端返回冲突，由人工确认是否合并角色；不做自动合并。
- P3 解析会读取项目正式别名做预匹配，并把候选别名补入角色。

### 2.2 `asset_versions`

| 字段 | 说明 |
| --- | --- |
| `asset_type` / `asset_id` | character / scene / prop / costume |
| `version_no` | 资产内递增版本号 |
| `parent_version_id` | 衍生来源版本 |
| `version_kind` | `identity` / `appearance` / `base` / `derived` |
| `variant_type` | `base` / `costume` / `hairstyle` / `makeup` / `age` / `weather` / `lighting` / `other` |
| `name` / `description` | 版本快照 |
| `attributes` | 服装 ID、身份字段快照等 |
| `source` | `manual` / `generated` / `uploaded` / `p3_confirm` |
| `status` | `draft` / `active` / `superseded` |

当前指针：

- `characters.identity_version_id`：当前视觉身份版本；
- `characters.current_appearance_version_id`：当前造型版本（可空）；
- `scenes.current_version_id` / `props.current_version_id` / `costumes.current_version_id`：当前基础/衍生版本。

正式采纳版本不原地修改。切换版本只移动指针，旧版本保留为 `superseded`。
删除版本只允许未采纳、非当前/身份版本的草稿；已引用版本拒绝删除。

### 2.3 `asset_image_candidates`

| 字段 | 说明 |
| --- | --- |
| `asset_type` / `asset_id` | 所属资产 |
| `asset_version_id` | 归入哪个版本；采纳时仍可指定目标版本 |
| `candidate_batch_id` | 一次「生成 2 张」共享批次 |
| `view_angle` | `FRONT` / `LEFT` / `RIGHT` / `BACK` / `THREE_QUARTER` |
| `file_id` | FileItem 图片文件 |
| `source` | `generated` / `uploaded` |
| `generation_task_id` | 现有 `GenerationTask` |
| `prompt` / `generation_params` | 生成提示词、模型、比例、分辨率 |
| `status` | `pending` / `succeeded` / `failed` / `adopted` / `discarded` |
| `is_adopted` | 是否被采纳 |

图片文件仍保存为 `FileItem(type=image)`；采用统一鉴权与对象存储，不保存临时 URL。

## 3. 图片生成与候选

- 复用现有资产图提示词渲染、项目图片模型、风格快照、比例/分辨率配置；
- 每次默认创建 **2 个独立** `GenerationTask`，不假设供应商支持 `n=2`；
- 任务关联类型为 `asset_image_candidate`，`relation_entity_id` 是候选行 ID；
- `image_task_runner` 成功后回写候选 `file_id/status=succeeded`，失败/取消写 `failed`；
- 用户重新抽卡只新增候选，不自动改变已采纳图片；
- 用户可上传图片作为同等级候选，`source=uploaded`；
- 采纳是显式动作：
  - 同版本同视角其它候选取消 `is_adopted`；
  - 同步对应 `CharacterImage` / `SceneImage` / `PropImage` / `CostumeImage` 槽位；
  - 不删除其它候选文件；
- 已采纳候选不可删除。

## 4. 视觉身份锁定

前置条件：

1. 角色名称非空；
2. 基础外貌设定非空（`appearance` 或 `description`）；
3. 当前 identity 版本存在至少一张已采纳的 `FRONT` 候选图。

音色不是锁定前置条件。

锁定后：

- 服务端拒绝直接修改 `name`、`description`、`age_range`、`appearance`、`face_features`、`body_type`、`identity_features`、`identity_version_id`；
- 拒绝替换当前身份版本的正面已采纳图；
- 允许修改别名、音色、标签、造型版本、辅助视角、备注；
- 如需修改身份：创建新的 identity 草稿版本 → 采纳新的正面图 → 切换当前身份版本；旧版本保留；
- `identity_lock_version` 用于并发检查；切换身份版本时递增。

旧实体 PATCH 接口同样经过锁定校验，不能绕过前端禁用。

## 5. 音色

继续沿用既有解析顺序：

```text
显式 voice
  → characters.voice_id
    → 角色所绑 actors.voice_id
      → 未解析，配音 422
```

P4 只增加人工绑定入口与最终生效来源展示；不新增音色克隆引擎、不复制音频任务。
角色音色变更不改变 `identity_locked_at`，也不自动开启项目级音频参考开关。

## 6. P3 衔接

- P3 确认创建的角色直接出现在工作台资产列表；
- 角色 aliases 从 P3 候选导入；冲突别名跳过并保留人工处理；
- P3 已填写的 `appearance` / `age_range` / `body_type` 预填到角色圣经；
- P3 重解析只关联已有角色，不覆盖人工维护的外貌、锁定字段或别名；
- 没有图片的角色可以存在，但不能锁定视觉身份。

## 7. API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET/PATCH` | `/api/v1/studio/projects/{pid}/assets/{type}/{aid}/profile` | 资产档案 |
| `POST/PATCH/DELETE` | `.../assets/character/{aid}/aliases[/{alias_id}]` | 别名维护 |
| `GET` | `.../assets/{type}/{aid}/versions` | 版本历史 |
| `POST` | `.../assets/{type}/{aid}/versions` | 创建衍生/造型版本 |
| `POST` | `.../assets/character/{aid}/identity-versions` | 创建身份草稿 |
| `POST` | `.../assets/{type}/{aid}/versions/{vid}/switch` | 切换当前版本 |
| `DELETE` | `.../assets/{type}/{aid}/versions/{vid}` | 删除未引用草稿 |
| `GET` | `.../assets/{type}/{aid}/candidates` | 候选列表 |
| `POST` | `.../assets/{type}/{aid}/candidates/generate` | 生成 2 张候选 |
| `POST` | `.../assets/{type}/{aid}/candidates/upload` | 上传候选 |
| `POST` | `.../assets/{type}/{aid}/candidates/{cid}/adopt` | 采纳候选 |
| `DELETE` | `.../assets/{type}/{aid}/candidates/{cid}` | 删除未采纳候选 |
| `POST` | `.../assets/character/{aid}/lock` | 锁定视觉身份 |
| `GET/PATCH` | `.../assets/character/{aid}/voice` | 音色绑定与生效来源 |

所有接口按项目与工作区校验；编辑需要 editor。

## 8. 当前边界

- 不创建 P5 场次与镜头；
- 不建立 P6 镜头级有序参考绑定；
- 版本切换不自动改写历史镜头、分镜帧或视频；
- 多视角依赖现有资产图提示词与参考图能力；供应商不支持可靠参考图时应提示限制并允许手工上传；
- 真实图片生成仍受 P6 持久化额度门禁约束；P4 自动化测试使用 Mock。
