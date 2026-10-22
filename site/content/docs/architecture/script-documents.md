---
title: "剧本文档与版本"
description: "记录 P3 已生效的剧本文档模型、DOCX/Markdown 解析、版本生效与章节正文同步规则。"
weight: 25
---

> 本文属于“当前架构”文档，描述 P3 / C5 已落地的剧本文档基础设施。
> AI 解析、统一审核与差异分析见 [剧本解析与统一审核](/docs/architecture/script-parse-review/)。

## 两类文档

| 类型 | `doc_type` | 关联 |
| --- | --- | --- |
| 世界观与人物设定 | `worldbuilding` | 项目级，`chapter_id = NULL` |
| 每集完整剧本 | `episode` | 必须绑定一个 `Chapter` |

一集对应一个 `ScriptDocument`；重复上传会创建新版本，不创建新文档。

## 数据模型

```text
script_documents
  id / project_id / chapter_id / doc_type / title
  current_version_id   ← 最近上传版本（候选或生效）
  active_version_id    ← 当前生效版本
script_document_versions
  id / document_id / version_no
  file_id              ← 原始上传文件（files.type = document）
  file_name / file_type / content_hash
  raw_text / text_length
  status               ← candidate / active / superseded
  parse_status         ← not_parsed / parsing / parsed / failed（C6 使用）
  metadata             ← 提取告警、表格/图片统计
```

`current_version_id` 与 `active_version_id` 分离的原因：

- 上传新文件只更新 current，旧 active 继续作为正式内容；
- 用户显式“启用版本”或 C6 审核确认后，才把 active 指向新版本；
- 历史版本永不删除，可回看与追溯。

`chapters.raw_text` 仍是正式章节正文。只有启用版本时才会同步，
上传和解析阶段不会覆盖它。

## 文件解析

支持：

- `.docx`：python-docx 按 body 顺序读取段落与表格；Word 标题样式转成 Markdown `#`；
- `.md` / `.markdown`：UTF-8 解码，统一换行为 `\n`。

服务端校验：

- 扩展名白名单；
- 单文件 ≤ 10MB；
- DOCX 必须是含 `word/document.xml` 的 ZIP；
- Markdown 不允许 NUL 字节，必须是 UTF-8；
- 空正文拒绝创建版本；
- 表格/图片提取不完整时写入 `metadata.warnings`，不静默丢弃正文。

DOCX 宏、外部引用不会执行；只读取文档 XML。

## 重复上传

同一文档下 `content_hash` 相同视为重复上传，返回已有版本，`created=false`，
不会新增版本行。

## API

| 方法 | 路径 |
| --- | --- |
| `GET` | `/api/v1/studio/projects/{id}/script-documents` |
| `POST` | `/api/v1/studio/projects/{id}/script-documents/worldbuilding` |
| `POST` | `/api/v1/studio/projects/{id}/chapters/{cid}/script-document` |
| `GET` | `/api/v1/studio/script-documents/{id}` |
| `GET` | `/api/v1/studio/script-documents/{id}/versions/{vid}` |
| `POST` | `/api/v1/studio/script-documents/{id}/versions/{vid}/activate` |

上传为 multipart，字段 `file`，可选 `title`。原始文件写入 `files`（`type=document`），
并通过 `file_usages(usage_kind=script_document)` 关联项目/章节。

## 当前边界

- 不自动解析文档内容（C6）；
- 不自动覆盖章节正文、分镜或资产；
- 不创建场次实体（P5）；
- 文件大小上限 10MB；更大的剧本需拆分或后续调整。
