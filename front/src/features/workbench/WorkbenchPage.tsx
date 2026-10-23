/**
 * 树状工作台页面容器。
 *
 * 职责：
 *   1. 从 URL 解析当前节点（刷新 / 深链接 / 前进后退都由路由驱动）；
 *   2. 拉取项目、剧集、资产与「已展开剧集」的镜头 / 运行时摘要；
 *   3. 装配资源树与中央面板；
 *   4. 处理加载、错误、空态与未知节点。
 *
 * 业务仍在既有页面：本阶段不复制提取、生成、导出逻辑，
 * 需要旧能力时用新标签页跳转，避免把新外壳做成第二套业务实现。
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { useIsFetching, useQueryClient } from '@tanstack/react-query'
import type { UseQueryResult } from '@tanstack/react-query'
import { Button } from '../../components/ui/button'
import type { ChapterRead, ProjectRead } from '../../services/generated'
import type { WorkbenchAssetItem } from './types'
import {
  buildWorkbenchTree,
  getSelectionAncestorIds,
  getSelectionNodeId,
} from './buildTree'
import {
  parseWorkbenchSelection,
  workbenchPath,
  type WorkbenchAssetType,
  type WorkbenchSelection,
} from './routes'
import {
  collectChapterLoadState,
  collectRuntimeByChapter,
  collectSceneGroupsByChapter,
  collectShotsByChapter,
  useWorkbenchChapters,
  useWorkbenchCharacters,
  useWorkbenchGlobalAssets,
  useWorkbenchProject,
  useWorkbenchRuntimeQueries,
  useWorkbenchSceneGroupQueries,
  useWorkbenchShotQueries,
} from './useWorkbenchQueries'
import { WorkbenchLayout } from './WorkbenchLayout'
import { WorkbenchTree } from './WorkbenchTree'
import { WorkbenchInspector } from './WorkbenchInspector'
import { PanelEmpty, PanelError, PanelLoading } from './components/PanelStates'
import { OverviewPanel } from './panels/OverviewPanel'
import { ProjectConfigPanel } from './panels/ProjectConfigPanel'
import { ScriptPanel } from './panels/ScriptPanel'
import { StylePanel } from './panels/StylePanel'
import { AssetGroupPanel } from './panels/AssetGroupPanel'
import { AssetDetailPanel } from './panels/AssetDetailPanel'
import { EpisodePanel } from './panels/EpisodePanel'
import { SceneGroupPanel } from './panels/SceneGroupPanel'
import { ShotPanel } from './panels/ShotPanel'
import { ExportPanel } from './panels/ExportPanel'

const ASSET_TYPES: WorkbenchAssetType[] = ['character', 'scene', 'prop', 'costume']

/** 工作台骨架只读；任何生成动作都必须跳转到既有业务页面。 */
export default function WorkbenchPage() {
  const { projectId = '' } = useParams<{ projectId: string }>()
  const location = useLocation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const selection = useMemo(
    () => parseWorkbenchSelection(location.pathname, projectId),
    [location.pathname, projectId],
  )

  const projectQuery = useWorkbenchProject(projectId)
  const chaptersQuery = useWorkbenchChapters(projectId)
  const charactersQuery = useWorkbenchCharacters(projectId)
  const scenesQuery = useWorkbenchGlobalAssets(projectId, 'scene')
  const propsQuery = useWorkbenchGlobalAssets(projectId, 'prop')
  const costumesQuery = useWorkbenchGlobalAssets(projectId, 'costume')

  const chapters = useMemo(() => chaptersQuery.data ?? [], [chaptersQuery.data])
  const assetQueries = {
    character: charactersQuery,
    scene: scenesQuery,
    prop: propsQuery,
    costume: costumesQuery,
  }
  const assetCounts = {
    character: charactersQuery.data?.length ?? 0,
    scene: scenesQuery.data?.length ?? 0,
    prop: propsQuery.data?.length ?? 0,
    costume: costumesQuery.data?.length ?? 0,
  }
  const assetsLoading = ASSET_TYPES.some((type) => assetQueries[type].isPending)

  /**
   * 展开状态。
   *
   * 只存节点 ID，不存节点对象：数据刷新后节点会重建，
   * 存对象会让「展开状态」与最新数据脱节。
   */
  const ancestorKey = getSelectionAncestorIds(selection).join('|')
  const [expanded, setExpanded] = useState<Set<string>>(
    () => new Set(['root', 'assets', ...ancestorKey.split('|').filter(Boolean)]),
  )

  /** URL 变化（深链接 / 前进后退）时自动展开选中节点的祖先链。 */
  useEffect(() => {
    const ids = ancestorKey.split('|').filter(Boolean)
    setExpanded((prev) => {
      const next = new Set(prev)
      next.add('root')
      next.add('assets')
      ids.forEach((id) => next.add(id))
      return next
    })
  }, [ancestorKey])

  const expandedChapterIds = useMemo(
    () =>
      chapters
        .filter((chapter) => expanded.has(`episode:${chapter.id}`))
        .map((chapter) => chapter.id),
    [chapters, expanded],
  )

  const shotQueries = useWorkbenchShotQueries(projectId, expandedChapterIds)
  const runtimeQueries = useWorkbenchRuntimeQueries(projectId, expandedChapterIds)
  const sceneGroupQueries = useWorkbenchSceneGroupQueries(projectId, expandedChapterIds)
  const shotsByChapter = collectShotsByChapter(expandedChapterIds, shotQueries)
  const sceneGroupsByChapter = collectSceneGroupsByChapter(expandedChapterIds, sceneGroupQueries)
  const runtimeByChapter = collectRuntimeByChapter(expandedChapterIds, runtimeQueries)
  const chapterLoadState = collectChapterLoadState(expandedChapterIds, shotQueries)

  const tree = useMemo(
    () =>
      buildWorkbenchTree({
        projectId,
        projectName: projectQuery.data?.name ?? '加载项目…',
        chapters,
        shotsByChapter,
        sceneGroupsByChapter,
        runtimeByChapter,
        chapterLoadState,
        characters: charactersQuery.data ?? [],
        scenes: scenesQuery.data ?? [],
        props: propsQuery.data ?? [],
        costumes: costumesQuery.data ?? [],
      }),
    [
      projectId,
      projectQuery.data?.name,
      chapters,
      shotsByChapter,
      sceneGroupsByChapter,
      runtimeByChapter,
      chapterLoadState,
      charactersQuery.data,
      scenesQuery.data,
      propsQuery.data,
      costumesQuery.data,
    ],
  )

  const [keyword, setKeyword] = useState('')
  const selectedNodeId = getSelectionNodeId(selection)

  const toggleNode = useCallback((nodeId: string) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(nodeId)) next.delete(nodeId)
      else next.add(nodeId)
      return next
    })
  }, [])

  const setExpandedNodes = useCallback((nodeIds: string[]) => {
    setExpanded(new Set(['root', ...nodeIds]))
  }, [])

  const refreshAll = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ['workbench', projectId] })
  }, [projectId, queryClient])

  const refreshing = useIsFetching({ queryKey: ['workbench', projectId] }) > 0

  const onNavigate = useCallback(
    (path: string) => {
      navigate(path)
    },
    [navigate],
  )

  const center = renderCenter({
    projectId,
    selection,
    project: projectQuery.data,
    projectLoading: projectQuery.isLoading,
    projectError: projectQuery.error,
    onRetryProject: () => void projectQuery.refetch(),
    chapters,
    chaptersLoading: chaptersQuery.isLoading,
    assetQueries,
    assetCounts,
    assetsLoading,
    onNavigate,
  })

  return (
    <WorkbenchLayout
      projectId={projectId}
      projectName={projectQuery.data?.name ?? (projectQuery.isLoading ? '加载项目…' : '项目')}
      projectStyle={projectQuery.data?.style}
      progress={projectQuery.data?.progress ?? 0}
      tree={
        <WorkbenchTree
          tree={tree}
          selectedNodeId={selectedNodeId}
          expanded={expanded}
          keyword={keyword}
          onKeywordChange={setKeyword}
          onToggle={toggleNode}
          onSetExpanded={setExpandedNodes}
          onSelect={onNavigate}
          onRefresh={refreshAll}
          refreshing={refreshing}
        />
      }
      center={center}
      inspector={
        <WorkbenchInspector
          projectId={projectId}
          selection={selection}
          project={projectQuery.data}
          chapters={chapters}
          assetCounts={assetCounts}
        />
      }
    />
  )
}

interface RenderCenterContext {
  projectId: string
  selection: WorkbenchSelection
  project?: ProjectRead
  projectLoading: boolean
  projectError: unknown
  onRetryProject: () => void
  chapters: ChapterRead[]
  chaptersLoading: boolean
  assetQueries: Record<WorkbenchAssetType, UseQueryResult<WorkbenchAssetItem[]>>
  assetCounts: Record<WorkbenchAssetType, number>
  assetsLoading: boolean
  onNavigate: (path: string) => void
}

/**
 * 按选择渲染中央面板。
 *
 * 抽成普通函数而不是组件：它不持有状态、不调 hook，
 * 放在页面里可以保持一个清晰的「选择 → 面板」映射。
 */
function renderCenter(context: RenderCenterContext) {
  const {
    projectId,
    selection,
    project,
    projectLoading,
    projectError,
    onRetryProject,
    chapters,
    chaptersLoading,
    assetQueries,
    assetCounts,
    assetsLoading,
    onNavigate,
  } = context

  switch (selection.kind) {
    case 'overview':
      return (
        <OverviewPanel
          projectId={projectId}
          project={project}
          projectLoading={projectLoading}
          projectError={projectError}
          onRetryProject={onRetryProject}
          chapters={chapters}
          chaptersLoading={chaptersLoading}
          assetCounts={assetCounts}
          assetsLoading={assetsLoading}
          onNavigate={onNavigate}
        />
      )

    case 'config':
      return <ProjectConfigPanel projectId={projectId} />

    case 'script':
      return (
        <ScriptPanel
          projectId={projectId}
          project={project}
          chapters={chapters}
          loading={chaptersLoading}
          chapterId={selection.chapterId}
          onNavigate={onNavigate}
        />
      )

    case 'style':
      return <StylePanel projectId={projectId} />

    case 'assets': {
      const query = assetQueries[selection.assetType]
      if (selection.assetId) {
        return (
          <AssetDetailPanel
            projectId={projectId}
            assetType={selection.assetType}
            assetId={selection.assetId}
            onNavigate={onNavigate}
          />
        )
      }
      return (
        <AssetGroupPanel
          projectId={projectId}
          assetType={selection.assetType}
          assets={query.data ?? []}
          loading={query.isPending}
          error={query.error}
          onRetry={() => void query.refetch()}
          onNavigate={onNavigate}
        />
      )
    }

    case 'episode': {
      if (chaptersLoading) return <PanelLoading lines={6} label="加载剧集" />
      const chapter = chapters.find((item) => item.id === selection.chapterId)
      if (!chapter) {
        return (
          <PanelEmpty
            title="没有找到这一集"
            description={`章节 ${selection.chapterId} 不在当前项目中，或已被删除。`}
            action={
              <Button size="sm" onClick={() => onNavigate(workbenchPath(projectId))}>
                返回项目总览
              </Button>
            }
          />
        )
      }
      return <EpisodePanel projectId={projectId} chapter={chapter} onNavigate={onNavigate} />
    }

    case 'scene-group':
      return (
        <SceneGroupPanel
          projectId={projectId}
          chapterId={selection.chapterId}
          sceneGroupId={selection.sceneGroupId}
          onNavigate={onNavigate}
        />
      )

    case 'shot':
      return (
        <ShotPanel
          projectId={projectId}
          chapterId={selection.chapterId}
          shotId={selection.shotId}
          onNavigate={onNavigate}
        />
      )

    case 'export':
      return <ExportPanel projectId={projectId} />

    case 'unknown':
      return (
        <PanelEmpty
          title="节点不存在"
          description={`路径 ${selection.path} 没有对应的业务节点。可能是链接写错，或对象已被删除。`}
          action={
            <Button size="sm" onClick={() => onNavigate(workbenchPath(projectId))}>
              返回项目总览
            </Button>
          }
        />
      )

    default:
      return <PanelError message="无法识别的节点类型" />
  }
}
