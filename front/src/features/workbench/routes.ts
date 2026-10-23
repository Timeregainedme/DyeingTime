/**
 * 树状工作台的路由契约与解析。
 *
 * 为什么把选中对象放在 URL 里，而不是 React 内存状态：
 *   - 刷新页面后必须回到同一个节点；
 *   - 深链接要能把某个剧集或镜头直接发给别人；
 *   - 浏览器前进/后退必须按「访问过的节点」回放。
 *
 * 路由形态（全部挂在 `/projects/:projectId/workbench/*` 下）：
 *
 *   /workbench                      项目总览（默认）
 *   /workbench/overview             项目总览
 *   /workbench/config               项目配置（本阶段只读）
 *   /workbench/script               世界观与剧本（项目级）
 *   /workbench/script/:chapterId    某一集的剧本原文
 *   /workbench/style                风格圣经
 *   /workbench/assets/:type         某类资产列表（character/scene/prop/costume）
 *   /workbench/assets/:type/:id     单个资产
 *   /workbench/episodes/:chapterId  某一集
 *   /workbench/episodes/:chapterId/scenes/:sceneGroupId  某个正式场次
 *   /workbench/episodes/:chapterId/shots/:shotId  某个镜头
 *   /workbench/export               导出
 *
 * 选择「显式路径段」而不是 `?node=shot:xxx`：
 *   路径段与业务层级一一对应，可读、可分享、可被面包屑/日志直接识别；
 *   查询参数更适合「同一节点的显示选项」（如 tab），不适合表达资源定位。
 */

/** 工作台里可被路由定位的资产类型。 */
export const WORKBENCH_ASSET_TYPES = ['character', 'scene', 'prop', 'costume'] as const

export type WorkbenchAssetType = (typeof WORKBENCH_ASSET_TYPES)[number]

/** 资产类型的中文名，树、页面标题、右侧面板共用一份。 */
export const WORKBENCH_ASSET_LABELS: Record<WorkbenchAssetType, string> = {
  character: '角色',
  scene: '场景',
  prop: '道具',
  costume: '服装',
}

/** 当前 URL 对应的业务选择。`unknown` 用于提示深链接写错，而不是静默跳走。 */
export type WorkbenchSelection =
  | { kind: 'overview' }
  | { kind: 'config' }
  | { kind: 'script'; chapterId?: string }
  | { kind: 'style' }
  | { kind: 'assets'; assetType: WorkbenchAssetType; assetId?: string }
  | { kind: 'episode'; chapterId: string }
  | { kind: 'scene-group'; chapterId: string; sceneGroupId: string }
  | { kind: 'shot'; chapterId: string; shotId: string }
  | { kind: 'export' }
  | { kind: 'unknown'; path: string }

/** 是否是工作台路径。外壳据此关闭旧侧边栏，避免两套导航同时出现。 */
export function isWorkbenchPath(pathname: string): boolean {
  return /^\/projects\/[^/]+\/workbench(?:\/|$)/.test(pathname)
}

/** 工作台根路径（选中项目总览）。 */
export function workbenchPath(projectId: string): string {
  return `/projects/${encodeURIComponent(projectId)}/workbench`
}

export function workbenchOverviewPath(projectId: string): string {
  return `${workbenchPath(projectId)}/overview`
}

export function workbenchConfigPath(projectId: string): string {
  return `${workbenchPath(projectId)}/config`
}

export function workbenchScriptPath(projectId: string, chapterId?: string): string {
  return chapterId
    ? `${workbenchPath(projectId)}/script/${encodeURIComponent(chapterId)}`
    : `${workbenchPath(projectId)}/script`
}

export function workbenchStylePath(projectId: string): string {
  return `${workbenchPath(projectId)}/style`
}

export function workbenchAssetGroupPath(
  projectId: string,
  assetType: WorkbenchAssetType,
): string {
  return `${workbenchPath(projectId)}/assets/${assetType}`
}

export function workbenchAssetDetailPath(
  projectId: string,
  assetType: WorkbenchAssetType,
  assetId: string,
): string {
  return `${workbenchAssetGroupPath(projectId, assetType)}/${encodeURIComponent(assetId)}`
}

export function workbenchEpisodePath(projectId: string, chapterId: string): string {
  return `${workbenchPath(projectId)}/episodes/${encodeURIComponent(chapterId)}`
}

export function workbenchSceneGroupPath(
  projectId: string,
  chapterId: string,
  sceneGroupId: string,
): string {
  return `${workbenchEpisodePath(projectId, chapterId)}/scenes/${encodeURIComponent(sceneGroupId)}`
}

export function workbenchShotPath(
  projectId: string,
  chapterId: string,
  shotId: string,
): string {
  return `${workbenchEpisodePath(projectId, chapterId)}/shots/${encodeURIComponent(shotId)}`
}

export function workbenchExportPath(projectId: string): string {
  return `${workbenchPath(projectId)}/export`
}

/** 安全解码：畸形百分号编码不应让整页崩溃，原样返回即可。 */
function safeDecode(value: string): string {
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

function isAssetType(value: string): value is WorkbenchAssetType {
  return (WORKBENCH_ASSET_TYPES as readonly string[]).includes(value)
}

/**
 * 从 pathname 解析当前选择。
 *
 * 传入 projectId 而不是从路径里猜：调用方已经有 `useParams()` 的项目 ID，
 * 两处各自解析容易出现「URL 里编码过、参数里没编码」的不一致。
 * 解析不消费查询参数——`?tab=` 这类显示选项不属于节点定位。
 */
export function parseWorkbenchSelection(
  pathname: string,
  projectId: string,
): WorkbenchSelection {
  const prefix = `/projects/${encodeURIComponent(projectId)}/workbench`
  // 同时兼容未编码的 projectId（浏览器地址栏常见手输形态）。
  const rawPrefix = `/projects/${projectId}/workbench`
  const matchedPrefix = pathname.startsWith(prefix)
    ? prefix
    : pathname.startsWith(rawPrefix)
      ? rawPrefix
      : null

  if (!matchedPrefix) {
    return { kind: 'unknown', path: pathname }
  }

  const rest = pathname
    .slice(matchedPrefix.length)
    .replace(/^\/+/, '')
    .replace(/\/+$/, '')

  if (rest === '' || rest === 'overview') return { kind: 'overview' }
  if (rest === 'config') return { kind: 'config' }
  if (rest === 'style') return { kind: 'style' }
  if (rest === 'export') return { kind: 'export' }

  if (rest === 'script') return { kind: 'script' }
  const scriptMatch = /^script\/([^/]+)$/.exec(rest)
  if (scriptMatch) {
    return { kind: 'script', chapterId: safeDecode(scriptMatch[1]) }
  }

  const assetMatch = /^assets\/([^/]+)(?:\/([^/]+))?$/.exec(rest)
  if (assetMatch && isAssetType(assetMatch[1])) {
    return {
      kind: 'assets',
      assetType: assetMatch[1],
      assetId: assetMatch[2] ? safeDecode(assetMatch[2]) : undefined,
    }
  }

  const sceneGroupMatch = /^episodes\/([^/]+)\/scenes\/([^/]+)$/.exec(rest)
  if (sceneGroupMatch) {
    return {
      kind: 'scene-group',
      chapterId: safeDecode(sceneGroupMatch[1]),
      sceneGroupId: safeDecode(sceneGroupMatch[2]),
    }
  }

  const shotMatch = /^episodes\/([^/]+)\/shots\/([^/]+)$/.exec(rest)
  if (shotMatch) {
    return {
      kind: 'shot',
      chapterId: safeDecode(shotMatch[1]),
      shotId: safeDecode(shotMatch[2]),
    }
  }

  const episodeMatch = /^episodes\/([^/]+)$/.exec(rest)
  if (episodeMatch) {
    return { kind: 'episode', chapterId: safeDecode(episodeMatch[1]) }
  }

  return { kind: 'unknown', path: pathname }
}
