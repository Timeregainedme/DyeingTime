import { defineConfig, devices } from '@playwright/test'

/**
 * 真实后端验收：React + Vite → Vite 同源代理 → FastAPI → MySQL → 本地 S3。
 * 外部 AI 供应商不参与；测试数据由 backend/scripts/seed_p9_staging.py 准备。
 */
const PORT = 7801
export default defineConfig({
  testDir: './e2e-real',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report-real' }]],
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium-real', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: `pnpm exec vite --port ${PORT} --strictPort`,
    url: `http://127.0.0.1:${PORT}`,
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      CI: '1',
      VITE_USE_MOCK: 'false',
      VITE_BACKEND_URL: 'http://127.0.0.1:8010',
      VITE_DEV_PROXY_TARGET: 'http://127.0.0.1:8010',
    },
  },
})
