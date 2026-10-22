/**
 * 工作台查询 hooks。
 *
 * 统一用 TanStack Query 而不是组件内 useEffect：
 *   - 节点切换、浏览器前进后退时命中缓存，不重复请求整棵树；
 *   - 卸载后不会把过期响应写回已切换的页面（竞态由 Query 处理）；
 *   - 每个面板可以独立重试，不牵连整页。
 *
 * 分页拉全的策略在 `api.ts`；这里的职责只是声明查询键与生命周期。
 */
import { useQueries, useQuery } from '@tanstack/react-query'
import type { ShotRead } from '../../services/generated'
import { queryKeys } from '../../lib/queryClient'
import type { WorkbenchAssetType } from './routes'
import {
  loadAllChapters,
  loadAllShots,
  loadAssetDetail,
  loadGlobalAssets,
  loadProject,
  loadProjectCharacters,
  loadProjectTimeline,
  loadRuntimeSummary,
  loadShot,
  loadShotDetail,
  loadShotPreparation,
  loadShotReadiness,
  loadStyleCatalog,
  loadStyleOptions,
} from './api'

/** 工作台默认缓存时间：与全局 QueryClient 的 30s 对齐，避免切节点就重拉。 */
const STALE_MS = 30_000

export function useWorkbenchProject(projectId: string) {
  return useQuery({
    queryKey: queryKeys.workbenchProject(projectId),
    queryFn: () => loadProject(projectId),
    enabled: Boolean(projectId),
    staleTime: STALE_MS,
  })
}

export function useWorkbenchChapters(projectId: string) {
  return useQuery({
    queryKey: queryKeys.workbenchChapters(projectId),
    queryFn: () => loadAllChapters(projectId),
    enabled: Boolean(projectId),
    staleTime: STALE_MS,
  })
}

export function useWorkbenchStyleOptions() {
  return useQuery({
    queryKey: queryKeys.workbenchStyleOptions,
    queryFn: loadStyleOptions,
    staleTime: 5 * 60_000,
  })
}

/** 风格目录明细：与下拉选项分开缓存，二者字段用途不同。 */
export function useWorkbenchStyleCatalog() {
  return useQuery({
    queryKey: queryKeys.workbenchStyleCatalog,
    queryFn: loadStyleCatalog,
    staleTime: 5 * 60_000,
  })
}

export function useWorkbenchCharacters(projectId: string) {
  return useQuery({
    queryKey: queryKeys.workbenchAssets(projectId, 'character'),
    queryFn: () => loadProjectCharacters(projectId),
    enabled: Boolean(projectId),
    staleTime: STALE_MS,
  })
}

/** 场景 / 道具 / 服装共用一条查询，按类型取缓存。 */
export function useWorkbenchGlobalAssets(projectId: string, assetType: WorkbenchAssetType) {
  return useQuery({
    queryKey: queryKeys.workbenchAssets(projectId, assetType),
    queryFn: () => loadGlobalAssets(assetType),
    enabled: Boolean(projectId) && assetType !== 'character',
    staleTime: STALE_MS,
  })
}

export function useWorkbenchAssetDetail(
  projectId: string,
  assetType: WorkbenchAssetType,
  assetId: string | undefined,
) {
  return useQuery({
    queryKey: queryKeys.workbenchAsset(projectId, assetType, assetId ?? ''),
    queryFn: () => loadAssetDetail(assetType, assetId as string),
    enabled: Boolean(projectId) && Boolean(assetType) && Boolean(assetId),
    staleTime: STALE_MS,
  })
}

/**
 * 批量加载「已展开剧集」的镜头。
 *
 * 用 `useQueries` 而不是在页面里循环调 hook：章节数量是动态的，
 * 只有展开的章节才会真正发请求，收起后数据仍留在缓存里。
 */
export function useWorkbenchShotQueries(projectId: string, chapterIds: string[]) {
  return useQueries({
    queries: chapterIds.map((chapterId) => ({
      queryKey: queryKeys.workbenchShots(projectId, chapterId),
      queryFn: () => loadAllShots(chapterId),
      staleTime: STALE_MS,
    })),
  })
}

/** 批量加载「已展开剧集」的运行时任务摘要（镜头节点上的运行中标记）。 */
export function useWorkbenchRuntimeQueries(projectId: string, chapterIds: string[]) {
  return useQueries({
    queries: chapterIds.map((chapterId) => ({
      queryKey: queryKeys.workbenchRuntime(projectId, chapterId),
      queryFn: () => loadRuntimeSummary(chapterId),
      staleTime: 10_000,
    })),
  })
}

/**
 * 把 useQueries 的结果收敛成「按章节索引」的 map。
 *
 * 只保留成功结果；加载中/失败交给 tree 的占位节点表达，
 * 避免把「还没拿到」误写成「0 个镜头」。
 */
export function collectShotsByChapter(
  chapterIds: string[],
  results: Array<{ data?: ShotRead[] }>,
): Record<string, ShotRead[]> {
  const map: Record<string, ShotRead[]> = {}
  results.forEach((result, index) => {
    const chapterId = chapterIds[index]
    if (chapterId && result.data) map[chapterId] = result.data
  })
  return map
}

/** 把 runtime summary 收敛成 shotId → 活跃任务数。 */
export function collectRuntimeByChapter(
  chapterIds: string[],
  results: Array<{ data?: Array<{ shot_id: string; active_task_count: number }> }>,
): Record<string, Record<string, number>> {
  const map: Record<string, Record<string, number>> = {}
  results.forEach((result, index) => {
    const chapterId = chapterIds[index]
    if (!chapterId || !result.data) return
    const perShot: Record<string, number> = {}
    result.data.forEach((item) => {
      if (item.active_task_count > 0) perShot[item.shot_id] = item.active_task_count
    })
    map[chapterId] = perShot
  })
  return map
}

/** 章节加载状态：只对已展开但尚未成功的章节返回状态。 */
export function collectChapterLoadState(
  chapterIds: string[],
  results: Array<{ isPending: boolean; isError: boolean }>,
): Record<string, 'loading' | 'error'> {
  const map: Record<string, 'loading' | 'error'> = {}
  results.forEach((result, index) => {
    const chapterId = chapterIds[index]
    if (!chapterId) return
    if (result.isError) map[chapterId] = 'error'
    else if (result.isPending) map[chapterId] = 'loading'
  })
  return map
}

export function useWorkbenchShot(projectId: string, shotId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.workbenchShot(projectId, shotId ?? ''),
    queryFn: () => loadShot(shotId as string),
    enabled: Boolean(projectId) && Boolean(shotId),
    staleTime: STALE_MS,
  })
}

export function useWorkbenchShotDetail(projectId: string, shotId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.workbenchShotDetail(projectId, shotId ?? ''),
    queryFn: () => loadShotDetail(shotId as string),
    enabled: Boolean(projectId) && Boolean(shotId),
    staleTime: STALE_MS,
  })
}

export function useWorkbenchShotPreparation(projectId: string, shotId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.workbenchShotPreparation(projectId, shotId ?? ''),
    queryFn: () => loadShotPreparation(shotId as string),
    enabled: Boolean(projectId) && Boolean(shotId),
    staleTime: STALE_MS,
  })
}

export function useWorkbenchShotReadiness(projectId: string, shotId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.workbenchShotReadiness(projectId, shotId ?? ''),
    queryFn: () => loadShotReadiness(shotId as string),
    enabled: Boolean(projectId) && Boolean(shotId),
    staleTime: 10_000,
  })
}

export function useWorkbenchTimeline(projectId: string) {
  return useQuery({
    queryKey: queryKeys.workbenchTimeline(projectId),
    queryFn: () => loadProjectTimeline(projectId),
    enabled: Boolean(projectId),
    staleTime: STALE_MS,
  })
}
