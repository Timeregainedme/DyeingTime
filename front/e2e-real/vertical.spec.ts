import { execFileSync } from 'node:child_process'
import { expect, test, type Page } from '@playwright/test'

/** 登录真实 FastAPI；不注入伪造 token。 */
async function login(page: Page) {
  await page.addInitScript(() => {
    const env = (window as unknown as { __ENV?: Record<string, string> }).__ENV ?? {}
    env.BACKEND_URL = 'http://127.0.0.1:8010'
    ;(window as unknown as { __ENV?: Record<string, string> }).__ENV = env
  })
  await page.goto('/login')
  await page.getByPlaceholder('账号').fill('e2e')
  await page.getByPlaceholder('密码').fill('e2e-pass')
  await page.getByRole('button', { name: /登\s*录/ }).click()
  await expect(page).toHaveURL(/\/projects$/)
}

const WORKBENCH = '/projects/p-e2e/workbench'

test('真实后端：工作台、配置、风格、剧本、资产、镜头与 ZIP 导出', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await login(page)

  await expect(page.getByText('E2E 都市短剧').first()).toBeVisible()

  // 真实创建项目：前端表单 → FastAPI → MySQL。
  const createdName = `P9 浏览器项目 ${Date.now()}`
  await page.getByRole('button', { name: '新建项目' }).click()
  await page.getByLabel('项目名称').fill(createdName)
  await page.getByLabel('简介').fill('P9-A 浏览器真实创建')
  await page.getByRole('button', { name: '创建项目' }).click()
  await expect(page).toHaveURL(/\/projects\/[^/]+\/workbench$/)
  await expect(page.getByRole('main', { name: '工作区' }).getByRole('heading', { name: createdName })).toBeVisible()

  await page.goto(WORKBENCH)
  await expect(page.getByRole('main', { name: '工作区' }).getByRole('heading', { name: 'E2E 都市短剧' })).toBeVisible()
  await expect(page.getByText('制作流程')).toBeVisible()
  await expect(page.getByRole('tree')).toBeVisible()

  await page.goto(`${WORKBENCH}/config`)
  await expect(page.getByRole('main', { name: '工作区' }).getByRole('heading', { name: '项目配置' })).toBeVisible()
  await expect(page.getByText('视频批量并发数').first()).toBeVisible()
  await page.getByRole('button', { name: '保存草稿' }).click()
  await expect(page.getByText(/草稿已保存/)).toBeVisible()

  await page.goto(`${WORKBENCH}/style`)
  await expect(page.getByText('风格圣经').first()).toBeVisible()
  await expect(page.getByText('已锁定').first()).toBeVisible()

  await page.goto(`${WORKBENCH}/script`)
  await expect(page.getByText('第1集：夜班').first()).toBeVisible()

  await page.goto(`${WORKBENCH}/assets/character/char-e2e-1`)
  await expect(page.getByText('林晚').first()).toBeVisible()
  await expect(page.getByText('音色').first()).toBeVisible()

  await page.goto(`${WORKBENCH}/episodes/c-e2e`)
  await expect(page.getByText('场次 01').first()).toBeVisible()
  await expect(page.getByText('场次 02').first()).toBeVisible()
  await expect(page.getByText('镜头 01').first()).toBeVisible()

  await page.goto(`${WORKBENCH}/episodes/c-e2e/shots/s-e2e-1`)
  await expect(page.getByText('H3 参考素材').first()).toBeVisible()
  await expect(page.getByText('视频候选与抽卡').first()).toBeVisible()
  await expect(page.getByText('信息确认状态').first()).toBeVisible()

  await page.goto(`${WORKBENCH}/export`)
  await expect(page.getByText('已采纳 4').first()).toBeVisible()
  await page.getByRole('button', { name: '选择全部已采纳' }).click()
  await page.getByRole('button', { name: '预检查' }).click()
  await expect(page.getByText(/预检查通过/)).toBeVisible()
  await expect(page.getByText('可导出').first()).toBeVisible()
  await expect(page.getByText(/E01_SC01_SH001\.mp4/).first()).toBeVisible()

  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: '下载 MP4 ZIP' }).click()
  const download = await downloadPromise
  const path = await download.path()
  expect(path).toBeTruthy()
  const listing = execFileSync('unzip', ['-l', path as string], { encoding: 'utf8' })
  const mp4s = listing.split('\n').filter((line) => line.trim().endsWith('.mp4'))
  expect(mp4s).toHaveLength(4)
  expect(mp4s.join('\n')).toContain('E01_SC01_SH001.mp4')
  expect(mp4s.join('\n')).toContain('E01_SC01_SH004.mp4')
  expect(listing).not.toContain('MANIFEST')
})

test('桌面分辨率截图', async ({ page }) => {
  test.setTimeout(180_000)
  await login(page)
  const pages = [
    ['overview', WORKBENCH],
    ['config', `${WORKBENCH}/config`],
    ['style', `${WORKBENCH}/style`],
    ['script', `${WORKBENCH}/script`],
    ['character', `${WORKBENCH}/assets/character/char-e2e-1`],
    ['episode', `${WORKBENCH}/episodes/c-e2e`],
    ['shot', `${WORKBENCH}/episodes/c-e2e/shots/s-e2e-1`],
    ['export', `${WORKBENCH}/export`],
  ] as const
  for (const [width, height] of [[1280, 720], [1440, 900], [1920, 1080], [2560, 1440]] as const) {
    await page.setViewportSize({ width, height })
    for (const [name, path] of pages) {
      await page.goto(path)
      await page.waitForTimeout(250)
      await page.screenshot({
        path: `test-results/p9-screens/${width}x${height}-${name}.png`,
        fullPage: true,
      })
    }
  }
})
