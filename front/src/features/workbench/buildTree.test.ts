import { describe, expect, it } from 'vitest'
import type { ChapterRead, ShotRead, ShotStatus } from '../../services/generated'
import {
  buildWorkbenchTree,
  filterWorkbenchTree,
  getSelectionAncestorIds,
  getSelectionNodeId,
} from './buildTree'
import type { BuildWorkbenchTreeInput, WorkbenchTreeNode } from './types'

function chapter(id: string, index: number, overrides: Partial<ChapterRead> = {}): ChapterRead {
  return {
    id,
    project_id: 'p1',
    index,
    title: `第 ${index} 集标题`,
    summary: '',
    raw_text: '原文',
    condensed_text: '',
    storyboard_count: 0,
    shot_count: 0,
    status: 'draft',
    ...overrides,
  }
}

function shot(id: string, index: number, status: ShotStatus = 'pending'): ShotRead {
  return {
    id,
    chapter_id: 'c1',
    index,
    title: `镜头标题 ${index}`,
    thumbnail: '',
    status,
    skip_extraction: false,
    script_excerpt: '',
    generated_video_file_id: null,
    generated_audio_file_id: null,
    last_extracted_at: null,
    extraction: {
      state: status === 'ready' ? 'extracted_resolved' : 'extracted_pending',
      has_extracted: true,
    },
  }
}

function baseInput(overrides: Partial<BuildWorkbenchTreeInput> = {}): BuildWorkbenchTreeInput {
  return {
    projectId: 'p1',
    projectName: '测试项目',
    chapters: [],
    shotsByChapter: {},
    runtimeByChapter: {},
    chapterLoadState: {},
    characters: [{ id: 'ch1', name: '林晚' }],
    scenes: [
      { id: 'sc2', name: '天台' },
      { id: 'sc1', name: '出租屋' },
    ],
    props: [],
    costumes: [],
    ...overrides,
  }
}

/** 按 ID 深度查找节点，避免测试依赖数组下标。 */
function findNode(node: WorkbenchTreeNode, id: string): WorkbenchTreeNode | undefined {
  if (node.id === id) return node
  for (const child of node.children) {
    const found = findNode(child, id)
    if (found) return found
  }
  return undefined
}

describe('buildWorkbenchTree', () => {
  it('无剧集时也只生成真实节点，不伪造场次', () => {
    const tree = buildWorkbenchTree(baseInput())
    expect(tree.id).toBe('root')
    expect(tree.label).toBe('测试项目')
    expect(tree.children.map((child) => child.kind)).toEqual([
      'config',
      'script',
      'style',
      'assets-root',
      'export',
    ])
    expect(findNode(tree, 'scene-group')).toBeUndefined()
  })

  it('剧集按集数排序，镜头按序号排序，节点 ID 使用业务 ID', () => {
    const tree = buildWorkbenchTree(
      baseInput({
        chapters: [chapter('c2', 2), chapter('c1', 1)],
        shotsByChapter: {
          c2: [shot('s-b', 2), shot('s-a', 1)],
        },
      }),
    )

    const episodes = tree.children.filter((child) => child.kind === 'episode')
    expect(episodes.map((node) => node.id)).toEqual(['episode:c1', 'episode:c2'])
    expect(episodes.map((node) => node.label)).toEqual(['第 1 集', '第 2 集'])

    const episode2 = findNode(tree, 'episode:c2')
    expect(episode2?.children.map((node) => node.id)).toEqual(['shot:s-a', 'shot:s-b'])
    expect(episode2?.children.map((node) => node.label)).toEqual(['镜头 01', '镜头 02'])
  })

  it('超过 100 个镜头不会截断', () => {
    const shots = Array.from({ length: 150 }, (_, index) =>
      shot(`shot-${index}`, index + 1),
    )
    const tree = buildWorkbenchTree(
      baseInput({
        chapters: [chapter('c1', 1)],
        shotsByChapter: { c1: shots },
      }),
    )
    expect(findNode(tree, 'episode:c1')?.children).toHaveLength(150)
    expect(findNode(tree, 'shot:shot-149')).toBeDefined()
  })

  it('未加载的章节给出加载占位，加载失败给出错误占位', () => {
    const tree = buildWorkbenchTree(
      baseInput({
        chapters: [chapter('c1', 1), chapter('c2', 2)],
        chapterLoadState: { c1: 'loading', c2: 'error' },
      }),
    )
    expect(findNode(tree, 'episode:c1')?.children[0]?.kind).toBe('loading')
    expect(findNode(tree, 'episode:c2')?.children[0]?.kind).toBe('error')
  })

  it('状态摘要严格区分 shot.status 与运行中任务', () => {
    const tree = buildWorkbenchTree(
      baseInput({
        chapters: [chapter('c1', 1)],
        shotsByChapter: {
          c1: [shot('s1', 1, 'ready'), shot('s2', 2, 'pending')],
        },
        runtimeByChapter: { c1: { s2: 3 } },
      }),
    )

    expect(findNode(tree, 'shot:s1')?.status).toEqual({ prep: 'ready', activeTasks: undefined })
    expect(findNode(tree, 'shot:s2')?.status).toEqual({ prep: 'pending', activeTasks: 3 })

    const episode = findNode(tree, 'episode:c1')
    expect(episode?.status?.pendingShots).toBe(1)
    expect(episode?.status?.readyShots).toBe(1)
    expect(episode?.status?.activeTasks).toBe(3)
  })

  it('未加载镜头时不编造剧集状态', () => {
    const tree = buildWorkbenchTree(baseInput({ chapters: [chapter('c1', 1)] }))
    expect(findNode(tree, 'episode:c1')?.status).toBeUndefined()
  })

  it('全局资产按名称排序，并带上稳定业务 ID', () => {
    const tree = buildWorkbenchTree(baseInput())
    expect(findNode(tree, 'assets:scene')?.children.map((node) => node.id)).toEqual([
      'asset:scene:sc1',
      'asset:scene:sc2',
    ])
    expect(findNode(tree, 'assets:character')?.children[0]?.to).toContain('/assets/character/ch1')
  })
})

describe('filterWorkbenchTree', () => {
  const tree = buildWorkbenchTree(
    baseInput({
      chapters: [chapter('c1', 1), chapter('c2', 2, { title: '雨夜追踪' })],
      shotsByChapter: {
        c1: [shot('s1', 1), shot('s2', 2)],
        c2: [shot('s3', 1), shot('s4', 2)],
      },
    }),
  )

  it('命中后代时保留祖先，但只带命中的后代', () => {
    const filtered = filterWorkbenchTree(tree, '镜头标题 2')
    expect(filtered).not.toBeNull()
    const episode1 = findNode(filtered as WorkbenchTreeNode, 'episode:c1')
    expect(episode1?.children.map((node) => node.id)).toEqual(['shot:s2'])
    // 搜索不会因为父节点命中就把整集铺开
    const episode2 = findNode(filtered as WorkbenchTreeNode, 'episode:c2')
    expect(episode2?.children.map((node) => node.id)).toEqual(['shot:s4'])
  })

  it('剧集标题命中时保留剧集节点', () => {
    const filtered = filterWorkbenchTree(tree, '雨夜')
    expect(findNode(filtered as WorkbenchTreeNode, 'episode:c2')).toBeDefined()
    expect(findNode(filtered as WorkbenchTreeNode, 'episode:c1')).toBeUndefined()
  })

  it('占位节点不参与搜索', () => {
    const withPlaceholder = buildWorkbenchTree(
      baseInput({ chapters: [chapter('c1', 1)], chapterLoadState: { c1: 'loading' } }),
    )
    expect(filterWorkbenchTree(withPlaceholder, '加载')).toBeNull()
  })

  it('空关键词返回完整树', () => {
    expect(filterWorkbenchTree(tree, '   ')).toBe(tree)
  })
})

describe('选择的节点与祖先', () => {
  it('选中剧集会展开该集', () => {
    expect(getSelectionAncestorIds({ kind: 'episode', chapterId: 'c1' })).toEqual([
      'root',
      'episode:c1',
    ])
  })

  it('镜头选择会展开剧集与根节点', () => {
    expect(getSelectionNodeId({ kind: 'shot', chapterId: 'c1', shotId: 's2' })).toBe('shot:s2')
    expect(getSelectionAncestorIds({ kind: 'shot', chapterId: 'c1', shotId: 's2' })).toEqual([
      'root',
      'episode:c1',
    ])
  })

  it('资产详情会展开资产分组', () => {    expect(
      getSelectionNodeId({ kind: 'assets', assetType: 'scene', assetId: 'sc1' }),
    ).toBe('asset:scene:sc1')
    expect(
      getSelectionAncestorIds({ kind: 'assets', assetType: 'scene', assetId: 'sc1' }),
    ).toEqual(['root', 'assets', 'assets:scene'])
  })

  it('未知选择没有节点 ID', () => {
    expect(getSelectionNodeId({ kind: 'unknown', path: '/x' })).toBeNull()
  })
})
