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

## P9-D1 男性对白声音验证

- 新视频：`/tmp/opencode/p9d1-voice.mp4`
- 供应商 task：`01a169a6-b9a6-799a-8f50-3cfc66f79d90`
- 内部 Task：`1722a29e118e4cfd9eb3839ee3bd5f00`
- 规格：5.175s / 768×1344 / H.264 + AAC / 1.3MB
- 结果：台词内容正确；额外出现画面描述旁白；待用户 L4 试听确认音色。
- 证据：`p9d1-voice-results.md`、`p9d1-call-record.json`、`p9d1-voice-contact.jpg`、`p9d1-voice-spectrum.png`

## H3 官方 Skill

- 安装与差异审计：`h3-official-skill-audit.md`
- 固定上游：`MiniMax-AI/MiniMax-H3@d21241f0a4b3acbb34c97dae47fa417b7065e438`

## P9-D2 背景连续性验证

- 新视频：`/tmp/opencode/p9d2-continuity.mp4`
- 供应商 task：`01a16a35-d9c9-7259-aa73-3f2de7beb0b7`
- 内部 Task：`d2f398cee22d45e88dcb939def720e9e`
- 规格：5.175s / 768×1344 / H.264 + AAC / 2.0MB
- 结果：同一办公室背景贯穿全片，场景切换检测为零；指定台词出现，无额外旁白；待用户 L4。
- 证据：`p9d2-continuity-results.md`、`p9d2-call-record.json`、`p9d2-continuity-contact.jpg`、`p9d2-official-prompt.txt`
