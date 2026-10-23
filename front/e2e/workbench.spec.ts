import { expect, test, type Page } from '@playwright/test'

/**
 * 树状工作台回归用例。
 *
 * 用 MSW mock + 伪造登录态，锁定 P1 的骨架行为：
 *   - 项目列表能进入工作台；
 *   - 树展示真实项目 / 剧集 / 镜头 / 全局资产节点；
 *   - 切换节点、刷新、前进后退、深链接都按 URL 工作；
 *   - 旧页面仍然可用，且工作台不出现旧侧边栏。
 */
async function signIn(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem('dyeingtime_token', 'e2e-token')
    localStorage.setItem(
      'dyeingtime_user',
      JSON.stringify({ id: '1', username: 'e2e', display_name: 'E2E' }),
    )
    localStorage.setItem('dyeingtime_language', 'zh-CN')
  })
}

const WORKBENCH = '/projects/p1/workbench'

test('从项目列表进入工作台，展示真实树节点且不出现旧侧边栏', async ({ page }) => {
  await signIn(page)
  await page.goto('/projects')

  await page.getByRole('button', { name: '打开树状工作台' }).first().click()

  await expect(page).toHaveURL(new RegExp(`${WORKBENCH}$`))
  await expect(
    page.getByRole('main', { name: '工作区' }).getByRole('heading', { name: '现实都市爱情短剧' }),
  ).toBeVisible()
  await expect(page.getByRole('tree')).toBeVisible()

  const tree = page.getByRole('tree')
  await expect(tree.getByText('第 1 集')).toBeVisible()
  await expect(tree.getByText('第 2 集')).toBeVisible()
  await expect(tree.getByText('全局资产')).toBeVisible()

  // 旧侧边栏的一级入口不应与工作台同时出现
  await expect(page.getByText('模型管理')).toHaveCount(0)
  await expect(page.getByText('提示词模板')).toHaveCount(0)
})

test('切换剧集与镜头，刷新和前进后退保持当前节点', async ({ page }) => {
  await signIn(page)
  await page.goto(WORKBENCH)

  const tree = page.getByRole('tree')
  await tree.getByText('第 1 集').click()

  await expect(page).toHaveURL(new RegExp(`${WORKBENCH}/episodes/c1$`))
  const main = page.getByRole('main', { name: '工作区' })
  await expect(main.getByRole('heading', { name: /第 1 集/ })).toBeVisible()

  // 剧集节点自动展开；历史镜头在未分配场次分组内。
  await tree.getByRole('button', { name: /展开 未分配场次/ }).click()
  await expect(tree.getByText('镜头 01')).toBeVisible()

  // 从资源树进入镜头节点
  await tree.getByText('镜头 01').click()
  await expect(page).toHaveURL(new RegExp(`${WORKBENCH}/episodes/c1/shots/s1$`))
  await expect(main.getByText('信息确认状态')).toBeVisible()
  await expect(main.getByText('视频生成准备度')).toBeVisible()

  // 刷新仍停留在同一镜头
  await page.reload()
  await expect(page).toHaveURL(new RegExp(`${WORKBENCH}/episodes/c1/shots/s1$`))
  await expect(page.getByRole('main', { name: '工作区' }).getByText('信息确认状态')).toBeVisible()

  // 浏览器后退回到剧集节点，前进回到镜头
  await page.goBack()
  await expect(page).toHaveURL(new RegExp(`${WORKBENCH}/episodes/c1$`))
  await page.goForward()
  await expect(page).toHaveURL(new RegExp(`${WORKBENCH}/episodes/c1/shots/s1$`))
})

test('深链接直接打开镜头，并自动展开所属剧集', async ({ page }) => {
  await signIn(page)
  await page.goto(`${WORKBENCH}/episodes/c1/shots/s2`)

  const main = page.getByRole('main', { name: '工作区' })
  await expect(main.getByRole('heading', { name: /镜头 02/ })).toBeVisible()
  await expect(main.getByText('信息确认状态')).toBeVisible()

  // 剧集被自动展开；历史镜头需要展开「未分配场次」才显示。
  const tree = page.getByRole('tree')
  await tree.getByRole('button', { name: /展开 未分配场次/ }).click()
  await expect(tree.getByText('镜头 02')).toBeVisible()
  await expect(tree.getByText('镜头 01')).toBeVisible()
})

test('树搜索只过滤节点，不改变当前 URL', async ({ page }) => {
  await signIn(page)
  await page.goto(WORKBENCH)

  const search = page.getByPlaceholder('搜索节点')
  await search.fill('第 2 集')

  const tree = page.getByRole('tree')
  await expect(tree.getByText('第 2 集')).toBeVisible()
  await expect(tree.getByText('第 1 集')).toHaveCount(0)
  await expect(page).toHaveURL(new RegExp(`${WORKBENCH}$`))

  await page.getByRole('button', { name: '清空搜索' }).click()
  await expect(tree.getByText('第 1 集')).toBeVisible()
})

test('未知节点给出明确错误与返回入口，不静默跳转', async ({ page }) => {
  await signIn(page)
  await page.goto(`${WORKBENCH}/episodes/not-exist`)

  await expect(page.getByText('没有找到这一集')).toBeVisible()
  await page.getByRole('button', { name: '返回项目总览' }).click()
  await expect(page).toHaveURL(new RegExp(`${WORKBENCH}$`))
})

test('旧版章节分镜页仍然可用', async ({ page }) => {
  await signIn(page)
  await page.goto('/projects/p1/chapters/c1/shots')

  await expect(page).toHaveURL(/\/projects\/p1\/chapters\/c1\/shots$/)
  await expect(page.getByText('分镜列表')).toBeVisible()
})
