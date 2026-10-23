---
title: "P9-B1 MiniMax H3 真实调用准备"
description: "四个真实测试镜头的参考绑定、输入快照、预算与首次调用检查表。"
weight: 8
---

> 状态：**准备完成，未发起真实付费调用**。本文件不是 L3 通过证明。

## 1. 官方参数核对

依据 MiniMax 官方 Video Generation 文档（2026-10-23 查询）：

| 项 | 官方值 | 当前代码 |
| --- | --- | --- |
| 模型 | `MiniMax-H3` | `MiniMax-H3` |
| 时长 | 4–15 秒整数 | 4–15 秒 |
| 分辨率 | 768P / 2K | 768P / 2K（P9-B1 已修正） |
| 比例 | 文档支持 ratio | 业务限制交集 |
| 参考图 | 最多 9 张 | 最多 9 张 |
| 参考音频 | 最多 3 个，不能单独 | 最多 3 个，不能单独 |
| 总参考 | 12 | 12 |
| 提交 | `POST /v2/video_generation` | 优云智算封装 `/minimax/v2/video_generation` |
| 查询 | `GET /v2/query/video_generation/{task_id}` | 同上封装 |
| 成功结果 | `task.content.url` | `video_url_from_task` |

**仍未经真实网关验证：** 优云智算的 `/minimax` 前缀、鉴权、`RetCode`/`task_id` 外层、价格、并发、Data URL 图片实际接受度。

## 2. 四个准备镜头

测试库：`p8_e2e`；项目：`p-e2e`；外部供应商未调用。

| # | Shot ID | 用途 | 参考图 | 时长 | 规格 | input_hash | snapshot |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `s-e2e-1` | 单人角色近景 | 2 | 5s | 9:16 / 768p | `5767d116ad371115…` | `657be006-ca0d-443a-ba9e-be62d1ad4c2d` |
| 2 | `s-e2e-2` | 双人互动 | 3 | 5s | 9:16 / 768p | `39cf21753926e001…` | `e4e6e221-bd06-4e3b-8e8a-ba7a0a63ea05` |
| 3 | `s-e2e-3` | 场景与道具 | 2 | 5s | 9:16 / 768p | `ba333abb26d992cc…` | `f9195c9f-3632-4c66-933d-c10fa7339c8f` |
| 4 | `s-e2e-4` | Prompt 修改重抽 | 3 | 5s | 9:16 / 768p | `04e935c0ff3b7621…` | `d0caa286-03a8-4485-8427-84d5c6e98d42` |

- 参考图已按 `<Picture N>` 顺序绑定并锁定。
- 角色身份已锁定；场景/道具版本已选择。
- 音频参考关闭。
- 四个镜头 `get_p6_readiness` 均为 `ready=True`。
- 快照 `task_id` 为空，未提交、未预留额度。

## 3. 首次真实调用检查表

- [ ] 用户明确批准测试 1 的单次付费调用
- [ ] 确认优云智算账户/渠道和 `MiniMax-H3` 模型可用
- [ ] 确认单次价格（当前未核实）
- [ ] 启用 `generation_test_quota_enabled=true`，scope=`v2-acceptance`
- [ ] 查询 video 额度仍为 4，并验证并发抢占
- [ ] 视频并发临时设为 1
- [ ] 使用 `s-e2e-1` 的 preview input_hash
- [ ] 新 request_key 且不复用其他请求
- [ ] 超时不自动重试，先查询供应商 task
- [ ] 成功视频不自动采纳，进入 L4 人工评价

## 4. 首次调用建议

建议先执行 **测试 1：单人角色近景（5 秒）**，只允许 1 次视频调用。成功拿到真实 MP4 后再决定是否继续测试 2–4。
