# P9-B2 真实 H3 视频结果

真实 MP4 文件保存在测试运行目录（未提交 Git，避免大体积媒体入库）：

- `/tmp/opencode/s-e2e-1.mp4`
- `/tmp/opencode/s-e2e-2.mp4`

工作台候选截图：

- `s-e2e-1-workbench.png`
- `s-e2e-2-workbench.png`

客观媒体信息：

| 镜头 | 供应商 task | 时长 | 分辨率 | 编码 | 大小 |
|---|---|---|---|---|---|
| s-e2e-1 | 01a168f7-6bb2-7ec4-b574-a92aa98d29f5 | 5.175s | 768×1344 | H.264/AAC | 2.28 MB |
| s-e2e-2 | 01a168fd-10d7-78bb-be26-dcd4fa51d6aa | 5.175s | 768×1344 | H.264/AAC | 2.27 MB |

截图来自真实 FastAPI + MySQL + moto S3 + 真实 H3 结果；不是 Mock 视频。

L4 用户已观看并反馈两项缺陷：

- s-e2e-1：角色声音不匹配、说话人归属错误；
- s-e2e-2：场景/背景不连续、镜头切换异常。

两条真实视频均标记为 `unsatisfied`，未自动采纳。完整证据与新旧 Prompt 对照见 `p9c-evidence.md`。
