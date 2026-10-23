# P9-A 真实后端浏览器截图

生成环境：

- Chromium（Playwright 1.64.1，Node 22.23.4）
- React/Vite 7801
- 真实 FastAPI 8010
- 独立 MySQL `p8_e2e`
- 本地 S3 mock（moto）与真实 MP4 fixtures
- 外部 AI 供应商未调用

页面覆盖：

`overview` / `config` / `style` / `script` / `character` / `episode` / `shot` / `export`

分辨率：

- 1280×720
- 1440×900
- 1920×1080
- 2560×1440

截图来自 `front/e2e-real/vertical.spec.ts` 的“桌面分辨率截图”用例。测试数据由 `backend/scripts/seed_p9_staging.py` 生成；P3/P4/P5 的 AI 结果以确定性 Mock 业务对象准备，不是真实 LLM 解析。
