---
title: "P9-B1 H3 真实供应商预检查"
description: "H3 官方参数核对、真实浏览器操作、四镜头预演、预算与首次调用条件。"
weight: 8
---

> 状态：**预检查完成，未发起任何真实付费调用。L3/L4 未通过。**

## 1. 官方参数核对

依据 MiniMax 官方文档（2026-10-23 查询）：

- `MiniMax-H3`：4–15 秒，768P / 2K
- 参考模式：最多 9 图、3 视频、3 音频，总参考 ≤12
- 提交：`POST /v2/video_generation`，`content[]` + role
- 查询：`GET /v2/query/video_generation/{task_id}`
- 成功结果：`task.content.url`

P9-B1 修复了本地适配器此前声明的错误能力：

| 项 | 修复前 | 修复后 |
| --- | --- | --- |
| 时长 | 4–30 秒 | 4–15 秒 |
| 分辨率 | 480P/768P/1080P/2K/4K | 768P/2K |

项目内部仍保持 4–15 秒。

## 2. 仍未经优云智算网关验证

官方文档不能证明当前 `compshare_model_api` 网关完全一致：

- `/minimax` 路径前缀与鉴权头
- `RetCode` / `task_id` 外层结构
- 参考图片使用 Data URL 是否被实际接受
- 参考音频公网 URL 要求
- 实际价格、并发、错误码
- 异步任务状态字段与失败状态

因此当前只能声明“官方协议与适配器代码已核对”，不能声明 L3。

## 3. 真实浏览器/CI 结果

GitHub Actions 实际执行：

- V2 Browser E2E：成功
  - https://github.com/Timeregainedme/dyeingtime/actions/runs/39957304607
- V2 Real Backend Browser E2E：成功
  - https://github.com/Timeregainedme/dyeingtime/actions/runs/39957304589
- 早期失败运行：
  - https://github.com/Timeregainedme/dyeingtime/actions/runs/39954735817
  - https://github.com/Timeregainedme/dyeingtime/actions/runs/39954735768
  - 已通过 `workers=1`、后端起停检查和失败摘要步骤修复。

真实后端 E2E 浏览器真实完成：

- 登录
- 创建项目（写入 MySQL）
- 打开工作台
- 保存项目配置草稿
- 浏览风格、剧本、角色、剧集、镜头
- 导出预检查
- 下载 ZIP，解压验证 4 个 MP4

仍以种子数据准备：

- P3 解析结果
- P4 资产版本/图片
- P5 场次/镜头
- P6 视频候选/Mock 视频

不是完整 UI 的“上传→解析→审核→生成”闭环。

## 4. 四个准备镜头

详细标题、参考文件、prompt、hash 与 snapshot：

`docs/p9-h3-real-test-plan.md`

四个镜头 `s-e2e-1` 至 `s-e2e-4` 均已：

- 建立有序参考绑定并锁定
- 生成输入快照
- `get_p6_readiness` 返回 ready
- 不提交 GenerationTask
- 不预留额度

## 5. 预算与安全

- image：0 / 20
- video：0 / 4
- audio：0 / 500
- 未启用真实付费测试
- 未使用真实 API Key
- 未调用真实媒体模型

第一次真实调用需要用户单独批准。建议只执行 `s-e2e-1` 的 5 秒单人近景，视频并发临时设为 1；失败/超时先查询供应商 task，不自动重试。

## 6. 首次调用阻塞

- 优云智算实际网关参数尚未验证。
- 参考图 Data URL 是否被接受尚未验证。
- 实际价格未确认。
- 用户未批准本轮付费调用。
- 额度门禁需在真实验收环境显式启用并验证。
