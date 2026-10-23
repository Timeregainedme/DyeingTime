---
title: "选择式 MP4 ZIP 导出"
description: "记录 P7 的镜头选择、已采纳视频、预检查、规范命名、MP4-only ZIP 与安全边界。"
weight: 35
---

> 本文属于“当前架构”，描述 P7 / C15 已落地的选择式片段导出。P7 不包含成片拼接或视频转码。

## 1. 导出数据源

```text
Shot.generated_video_file_id
  → FileItem（type=video）
  → FileUsage（项目归属）
  → 对象存储实际对象
  → ZIP 内 E01_SC02_SH003.mp4
```

- `shots.generated_video_file_id` 是唯一正式采纳指针。
- 不使用最新生成任务、最新成功候选、`shot_video_reviews` 或文件名猜测定稿。
- 候选列表只用于人工审核；未采纳候选不会进入 ZIP。
- 导出不修改镜头状态、不删除旧视频、不触发媒体生成。

## 2. 选择范围

支持：

1. 整个项目（`include_all=true`）
2. 指定剧集（`chapter_ids`）
3. 指定场次（`scene_group_ids`）
4. 自定义镜头（`shot_ids`）

同一请求只能指定一种范围。`shot_ids` 会校验重复、跨项目和不存在的 ID。镜头顺序不由前端勾选顺序决定。

## 3. 排序与命名

排序使用 P5 正式业务顺序：

- `Chapter.index`
- `Shot.index`（剧集内全局故事顺序）
- `SceneGroup.index` 只用于文件名中的 SCxx，不把 SC00 历史镜头提前

命名：

```text
E{chapter.index:02d}_SC{scene.index:02d}_SH{shot.index:03d}.mp4
```

- 未分配场次：`SC00`
- 示例：`E01_SC01_SH001.mp4`、`E01_SC02_SH004.mp4`
- 不按选中数量重新编号；只选部分镜头仍保留正式编号。
- 生成前检查 ZIP 内重名；重名直接阻塞，不覆盖。

## 4. 预检查

`POST /api/v1/studio/timeline/projects/{project_id}/clips-precheck`

返回：

- 选中、可导出、未采纳、文件缺失、格式不支持数量
- 总时长、预计大小
- 导出顺序、目标文件名
- 每个镜头的状态与错误
- `plan_hash`

检查项：

- 镜头属于当前项目/剧集/场次
- `generated_video_file_id` 存在
- FileItem 存在且 type=video
- FileUsage 属于当前项目
- 对象存储 `head_object` 可读
- 存储扩展名是 `.mp4`
- MP4 文件头包含 `ftyp`（不把其他容器改扩展名伪装成 MP4）
- ZIP 内无重名

预检查不通过时允许继续调整选择，但正式下载必须全部通过；不会静默跳过缺失镜头。

## 5. 下载与一致性

`POST /api/v1/studio/timeline/projects/{project_id}/clips-export`

- 下载请求携带预检查的 `plan_hash`。
- 服务端重新预检查并比较 hash；采纳版本或文件变化返回 `409`，要求重新预检查。
- 任一所选镜头缺失/格式不支持/存储不可读时整体失败并返回具体镜头。
- 下载成功只包含 MP4，不包含 MANIFEST、剧本、图片、Prompt、JSON 或音频。

## 6. ZIP 性能与安全

- `ZIP_STORED`：MP4 已压缩，避免重复 DEFLATE 的 CPU 放大。
- `allowZip64=True`，支持大文件/大数量。
- 每个对象先流式下载到受控临时文件，再写入 ZIP；不把所有视频读入内存。
- 临时 ZIP 在响应完成后清理；异常路径清理临时目录。
- 单次最多 500 个镜头、预计 20GB；超限阻止。
- 内部 storage key 不返回前端；ZIP 内只使用规范命名的固定路径。
- 文件名由数字编号构成，不依赖用户标题，避免路径穿越和中文路径异常。
- 项目/工作区权限沿用现有路由依赖；FileUsage 再校验文件项目归属。

## 7. 与旧导出兼容

- 旧 `GET /api/v1/studio/timeline/projects/{project_id}/clips-archive` 保留，继续允许部分片段并写 MANIFEST。
- 旧成片 ffmpeg 拼接接口保留。
- 新选择式导出独立使用严格 MP4-only 规则，不改变旧接口行为。
- 旧镜头没有 `scene_group_id` 时使用 SC00，不创建虚构 SceneGroup。

## 8. API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/studio/timeline/projects/{id}` | 时间线清单（含场次字段） |
| `POST` | `.../clips-precheck` | 选择式预检查与 plan hash |
| `POST` | `.../clips-export` | 严格 MP4 ZIP 下载 |
| `GET` | `.../clips-archive` | 旧版全部片段打包（保留） |
| `POST` | `.../export` | 旧版 ffmpeg 成片拼接（保留） |
