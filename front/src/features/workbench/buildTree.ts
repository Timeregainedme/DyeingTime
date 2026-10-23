/**
 * 把真实业务数据装配成树节点。
 *
 * 保持纯函数（无 React、无网络、无时间依赖）：
 *   - 便于单测覆盖「大量镜头、空剧集、加载中、加载失败」等边界；
 *   - 页面只负责取数与展开状态，装配规则集中在这里，避免树与面板各算一套。
 */
import type { ShotRead } from '../../services/generated'
import {
  WORKBENCH_ASSET_LABELS,
  workbenchAssetDetailPath,
  workbenchAssetGroupPath,
  workbenchConfigPath,
  workbenchEpisodePath,
  workbenchExportPath,
  workbenchScriptPath,
  workbenchSceneGroupPath,
  workbenchShotPath,
  workbenchStylePath,
  workbenchPath,
  type WorkbenchAssetType,
  type WorkbenchSelection,
} from './routes'
import type {
  BuildWorkbenchTreeInput,
  WorkbenchAssetItem,
  WorkbenchNodeStatus,
  WorkbenchTreeNode,
} from './types'

/** 镜头序号固定两位，和导出命名 `SH003` 的视觉习惯保持一致。 */
function shotLabel(index: number): string {
  return `镜头 ${String(index).padStart(2, '0')}`
}

function sortByIndex<T extends { index: number }>(items: T[]): T[] {
  return [...items].sort((a, b) => a.index - b.index)
}

function sortAssets(items: WorkbenchAssetItem[]): WorkbenchAssetItem[] {
  return [...items].sort((a, b) => a.name.localeCompare(b.name, 'zh-Hans-CN'))
}

/**
 * 单镜头状态摘要。
 *
 * `shot.status` 只有 pending / ready 两种业务含义；历史上的 `generating`
 * 不再表示运行时状态，这里按「未确认」处理，运行时只看 activeTasks。
 */
function shotStatus(shot: ShotRead, activeTasks: number): WorkbenchNodeStatus {
  return {
    prep: shot.status === 'ready' ? 'ready' : 'pending',
    activeTasks: activeTasks > 0 ? activeTasks : undefined,
  }
}

/** 剧集节点只聚合「已加载」的镜头，未加载时不编造 0/0。 */
function episodeStatus(
  shots: ShotRead[] | undefined,
  runtime: Record<string, number> | undefined,
): WorkbenchNodeStatus | undefined {
  if (!shots) return undefined
  const readyShots = shots.filter((shot) => shot.status === 'ready').length
  const activeTasks = shots.reduce((sum, shot) => sum + (runtime?.[shot.id] ?? 0), 0)
  return {
    pendingShots: shots.length - readyShots,
    readyShots,
    activeTasks: activeTasks > 0 ? activeTasks : undefined,
  }
}

function assetChildren(
  input: BuildWorkbenchTreeInput,
  assetType: WorkbenchAssetType,
  items: WorkbenchAssetItem[],
): WorkbenchTreeNode {
  return {
    id: `assets:${assetType}`,
    kind: 'asset-group',
    label: WORKBENCH_ASSET_LABELS[assetType],
    hint: `${items.length} 项`,
    selectable: true,
    expandable: true,
    to: workbenchAssetGroupPath(input.projectId, assetType),
    meta: { assetType },
    children: sortAssets(items).map((item) => ({
      id: `asset:${assetType}:${item.id}`,
      kind: assetType,
      label: item.name,
      hint: item.description || undefined,
      selectable: true,
      expandable: false,
      to: workbenchAssetDetailPath(input.projectId, assetType, item.id),
      meta: { assetType, assetId: item.id },
      children: [],
    })),
  }
}

/**
 * 单个镜头节点。
 *
 * 镜头在树中只出现一次；P5 后归属场次只影响父节点，不复制镜头数据。
 */
function shotNode(input: BuildWorkbenchTreeInput, chapterId: string, shot: ShotRead): WorkbenchTreeNode {
  const runtime = input.runtimeByChapter[chapterId] ?? {}
  return {
    id: `shot:${shot.id}`,
    kind: 'shot',
    label: shotLabel(shot.index),
    hint: shot.title,
    selectable: true,
    expandable: false,
    to: workbenchShotPath(input.projectId, chapterId, shot.id),
    meta: { chapterId, shotId: shot.id, sceneGroupId: shot.scene_group_id ?? undefined },
    status: shotStatus(shot, runtime[shot.id] ?? 0),
    children: [],
  }
}

/** 剧集子节点：正式场次 → 镜头；无场次历史镜头进入「未分配场次」。 */
function episodeChildren(
  input: BuildWorkbenchTreeInput,
  chapterId: string,
): WorkbenchTreeNode[] {
  const shots = input.shotsByChapter[chapterId]
  if (shots) {
    const groups = [...(input.sceneGroupsByChapter?.[chapterId] ?? [])].sort(
      (a, b) => a.index - b.index,
    )
    const knownGroupIds = new Set(groups.map((group) => group.id))
    const shotsByGroup = new Map<string, ShotRead[]>()
    const unassigned: ShotRead[] = []
    for (const shot of sortByIndex(shots)) {
      const groupId = shot.scene_group_id ?? ''
      if (!groupId || !knownGroupIds.has(groupId)) {
        unassigned.push(shot)
        continue
      }
      const rows = shotsByGroup.get(groupId) ?? []
      rows.push(shot)
      shotsByGroup.set(groupId, rows)
    }
    const groupNodes: WorkbenchTreeNode[] = groups.map((group) => ({
      id: `scene-group:${group.id}`,
      kind: 'scene-group',
      label: `场次 ${String(group.index).padStart(2, '0')} · ${group.title}`,
      hint: [group.location, group.time_of_day].filter(Boolean).join(' · ') || undefined,
      selectable: true,
      expandable: true,
      to: workbenchSceneGroupPath(input.projectId, chapterId, group.id),
      meta: { chapterId, sceneGroupId: group.id },
      children: (shotsByGroup.get(group.id) ?? []).map((shot) => shotNode(input, chapterId, shot)),
    }))
    if (unassigned.length > 0) {
      groupNodes.push({
        id: `scene-group:unassigned:${chapterId}`,
        kind: 'scene-group',
        label: '未分配场次',
        hint: `${unassigned.length} 个镜头`,
        selectable: false,
        expandable: true,
        meta: { chapterId, unassigned: true },
        children: unassigned.map((shot) => shotNode(input, chapterId, shot)),
      })
    }
    return groupNodes
  }

  const state = input.chapterLoadState[chapterId]
  if (state === 'error') {
    return [
      {
        id: `error:shots:${chapterId}`,
        kind: 'error',
        label: '场次/镜头加载失败',
        hint: '在中央面板点击重试',
        selectable: false,
        expandable: false,
        children: [],
      },
    ]
  }
  if (state === 'loading') {
    return [
      {
        id: `loading:shots:${chapterId}`,
        kind: 'loading',
        label: '正在加载场次与镜头…',
        selectable: false,
        expandable: false,
        children: [],
      },
    ]
  }
  return []
}

/**
 * 装配完整树。
 *
 * 层级与产品目标一致：项目 → 配置 / 剧本 / 风格 / 全局资产 / 每集 / 导出。
 * 每集下面当前直接挂镜头；P5 引入场次实体后，会在这一层插入 `scene-group`。
 */
export function buildWorkbenchTree(input: BuildWorkbenchTreeInput): WorkbenchTreeNode {
  const chapters = sortByIndex(input.chapters ?? [])

  const rootChildren: WorkbenchTreeNode[] = [
    {
      id: 'config',
      kind: 'config',
      label: '项目配置',
      selectable: true,
      expandable: false,
      to: workbenchConfigPath(input.projectId),
      children: [],
    },
    {
      id: 'script',
      kind: 'script',
      label: '世界观与剧本',
      hint: `${chapters.length} 集`,
      selectable: true,
      expandable: false,
      to: workbenchScriptPath(input.projectId),
      children: [],
    },
    {
      id: 'style',
      kind: 'style',
      label: '风格圣经',
      selectable: true,
      expandable: false,
      to: workbenchStylePath(input.projectId),
      children: [],
    },
    {
      id: 'assets',
      kind: 'assets-root',
      label: '全局资产',
      hint: `${input.characters.length + input.scenes.length + input.props.length + input.costumes.length} 项`,
      selectable: false,
      expandable: true,
      children: [
        assetChildren(input, 'character', input.characters),
        assetChildren(input, 'scene', input.scenes),
        assetChildren(input, 'prop', input.props),
        assetChildren(input, 'costume', input.costumes),
      ],
    },
  ]

  for (const chapter of chapters) {
    rootChildren.push({
      id: `episode:${chapter.id}`,
      kind: 'episode',
      label: `第 ${chapter.index} 集`,
      hint: chapter.title,
      selectable: true,
      expandable: true,
      to: workbenchEpisodePath(input.projectId, chapter.id),
      meta: { chapterId: chapter.id },
      status: episodeStatus(
        input.shotsByChapter[chapter.id],
        input.runtimeByChapter[chapter.id],
      ),
      children: episodeChildren(input, chapter.id),
    })
  }

  rootChildren.push({
    id: 'export',
    kind: 'export',
    label: '导出',
    selectable: true,
    expandable: false,
    to: workbenchExportPath(input.projectId),
    children: [],
  })

  return {
    id: 'root',
    kind: 'root',
    label: input.projectName || input.projectNameFallback || '未命名项目',
    hint: '项目总览',
    selectable: true,
    expandable: true,
    to: workbenchPath(input.projectId),
    children: rootChildren,
  }
}

/** 当前选择对应的节点 ID；用于高亮与滚动定位。 */
export function getSelectionNodeId(selection: WorkbenchSelection): string | null {
  switch (selection.kind) {
    case 'overview':
      return 'root'
    case 'config':
      return 'config'
    case 'script':
      return 'script'
    case 'style':
      return 'style'
    case 'assets':
      return selection.assetId
        ? `asset:${selection.assetType}:${selection.assetId}`
        : `assets:${selection.assetType}`
    case 'episode':
      return `episode:${selection.chapterId}`
    case 'scene-group':
      return `scene-group:${selection.sceneGroupId}`
    case 'shot':
      return `shot:${selection.shotId}`
    case 'export':
      return 'export'
    default:
      return null
  }
}

/**
 * 选中节点的祖先链。
 *
 * 刷新、深链接、浏览器前进后退时都靠它自动展开，
 * 否则用户会看到「URL 指向某镜头，但树里找不到」。
 */
export function getSelectionAncestorIds(selection: WorkbenchSelection): string[] {
  switch (selection.kind) {
    case 'overview':
    case 'config':
    case 'script':
    case 'style':
    case 'export':
      return ['root']
    case 'assets':
      return selection.assetId
        ? ['root', 'assets', `assets:${selection.assetType}`]
        : ['root', 'assets']
    case 'episode':
      // 选中剧集时同时展开它：用户点一集通常就是想看这一集的场次。
      return ['root', `episode:${selection.chapterId}`]
    case 'scene-group':
      return ['root', `episode:${selection.chapterId}`, `scene-group:${selection.sceneGroupId}`]
    case 'shot':
      return ['root', `episode:${selection.chapterId}`]
    default:
      return ['root']
  }
}

/**
 * 关键词过滤。
 *
 * 规则：节点自身命中或任一后代命中才保留；保留时只带上同样命中的后代。
 * 这样搜「第 2 集」会显示剧集本身而不是把它整集的几百个镜头全部铺开。
 * 加载/失败占位不参与匹配，避免搜出无意义的提示行。
 */
export function filterWorkbenchTree(
  node: WorkbenchTreeNode,
  keyword: string,
): WorkbenchTreeNode | null {
  const normalized = keyword.trim().toLowerCase()
  if (!normalized) return node
  if (node.kind === 'loading' || node.kind === 'error') return null

  const selfMatches =
    node.label.toLowerCase().includes(normalized) ||
    (node.hint ?? '').toLowerCase().includes(normalized)

  const filteredChildren = node.children
    .map((child) => filterWorkbenchTree(child, keyword))
    .filter((child): child is WorkbenchTreeNode => child !== null)

  if (!selfMatches && filteredChildren.length === 0) return null

  return {
    ...node,
    children: filteredChildren,
  }
}

/** 树里所有可展开节点的 ID，供「全部展开」使用。 */
export function collectExpandableIds(node: WorkbenchTreeNode, acc: string[] = []): string[] {
  if (node.expandable && node.children.length > 0) acc.push(node.id)
  node.children.forEach((child) => collectExpandableIds(child, acc))
  return acc
}
