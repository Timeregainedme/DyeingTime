---
title: "P9-B2 真实 MiniMax H3 生成结果"
description: "真实 H3 调用、供应商任务、MP4 回存、候选历史、积分消耗与 L4 待评价状态。"
weight: 7
---

> 状态：**L3 已通过 2 条真实 5 秒视频；L4 待用户实际观看确认。**

## 1. 连接与协议

- 供应商：优云智算 `compshare_model_api`
- Base URL：`https://cp.compshare.cn`
- 模型：`MiniMax-H3`
- API Key：有效（`sk-ml-`，未记录到文件/日志）
- 账户积分：9993.02，两次成功后 9893.02
- 请求：`POST /minimax/v2/video_generation`
- 查询：`GET /minimax/v2/query/video_generation/{task_id}`
- 参考图：Data URL，真实网关接受
- 成功：`task.content.url` 下载 MP4
- 幂等：`Idempotency-Key` 使用 GenerationTask ID，Worker 重试保持稳定

P9-B1 曾错误套用 MiniMax 官方 4–15 秒/768P/2K；优云智算实际 API 支持 4–30 秒及 480P/768P/1080P/2K/4K，已恢复对齐。

## 2. 真实调用

### 第一次：协议探测（失败，未出片）

- Task：`f2d99a0cb2054d0f8b52d655fa12d94b`
- 供应商错误：`RetCode=220 Params [Width], should be in [256, 5760]`
- 原因：E2E seed 使用了无效占位 PNG，参考图实际宽度不可解析
- 供应商积分消耗：0
- 本地额度：按保守规则消费 1 次
- 处理：替换为真实有效图片后重新提交，未重复使用旧 request_key

### 第二次：`s-e2e-1` 单人近景（成功）

- 内部 Task：`3adb6fa28f2c47d4b1a174a797f7b026`
- 供应商 task：`01a168f7-6bb2-7ec4-b574-a92aa98d29f5`
- 参考图：2 张
- 时长/规格：5 秒 / 768P / 9:16
- FileItem：`03884933-f923-40ec-b235-4be2d27763e1`
- MP4：H.264/AAC，768×1344，5.175 秒，2.28MB
- 当前采纳指针仍为旧版本 `v-e2e-1`；新视频仅作为候选
- 供应商积分：50

### 第三次：`s-e2e-2` 双人互动（成功）

- 内部 Task：`92aa30e950b04a50a7803fb0fd4f0a2a`
- 供应商 task：`01a168fd-10d7-78bb-be26-dcd4fa51d6aa`
- 参考图：3 张
- 时长/规格：5 秒 / 768P / 9:16
- FileItem：`a56f5198-112b-4cfc-af85-461bc7e78bd5`
- MP4：H.264/AAC，768×1344，5.175 秒，2.27MB
- 当前采纳指针仍为旧版本 `v-e2e-2`
- 供应商积分：50

## 3. 额度与费用

| 类型 | 已消耗 | 剩余 |
|---|---:|---:|
| 图片 | 0 | 20 |
| 视频本地测试额度 | 3（含 1 次失败探测） | 1 |
| 音频 | 0 | 500 |
| 供应商积分 | 100 | 9893.02 |

- 供应商积分包：12000 points / `total_price=9900`（接口未声明币种/单位）。
- 按该包折算 50 points ≈ 0.41 元，但**法币实际账单未由供应商账单接口确认**。
- 未继续执行测试 3/4，保留 1 次视频额度给 L4 后的必要重抽。

## 4. 视频与工作台

- MP4 本地路径（未提交 Git）：`/tmp/opencode/s-e2e-1.mp4`、`/tmp/opencode/s-e2e-2.mp4`
- 候选截图：`docs/p9-real-h3/`
- 真实 Chromium 工作台已确认 `<video>`：
  - `duration=5.175`
  - `width=768`, `height=1344`
  - `readyState=4`
- 新视频没有自动采纳；旧视频文件和历史保留。

## 5. L3 / L4

- L3：通过 2 条真实 H3 视频；另 1 条协议失败（未出片）。
- L4：**待人工观看**。不得由 OpenCode 代替用户评价或采纳。

## 6. 当前阻塞

- 用户尚未进行 L4 人工质量评价。
- 真实视频仅保存在本地测试对象存储；外部访问需要授权导出/迁移。
- 法币费用未由供应商账单确认。
- 测试 3（场景/道具）和测试 4（Prompt 重抽）未执行，剩余 1 次本地视频额度。
