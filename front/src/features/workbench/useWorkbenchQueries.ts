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
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import type { ShotRead } from '../../services/generated'
import { queryKeys } from '../../lib/queryClient'
import type { WorkbenchAssetType } from './routes'
import {
  loadAllChapters,
  loadAllShots,
  loadAssetDetail,
  loadGenerationConfig,
  loadGenerationOptions,
  loadGlobalAssets,
  loadProject,
  loadProjectCharacters,
  loadProjectStyleState,
  loadProjectTimeline,
  loadRuntimeSummary,
  loadScriptDocument,
  loadScriptDocuments,
  loadScriptDocumentVersion,
  loadShot,
  loadShotDetail,
  loadShotPreparation,
  loadShotReadiness,
  loadStyleAnalysisCapability,
  loadStyleCatalog,
  loadStyleOptions,
  saveGenerationConfig,
  selectProjectStyle,
  lockProjectStyle,
  analyzeStyleReferences,
  createStyleOption,
  updateStyleOption,
  uploadStyleImage,
  uploadEpisodeDocument,
  uploadWorldbuildingDocument,
  activateScriptDocumentVersion,
  addScriptParseCandidate,
  confirmScriptParseRun,
  createScriptDiffReport,
  deleteScriptParseCandidate,
  decideScriptDiffReport,
  listDocumentParseRuns,
  loadScriptParseRun,
  mergeScriptParseCandidates,
  startScriptParse,
  updateScriptParseCandidate,
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

export function useWorkbenchGenerationOptions(projectId: string) {
  return useQuery({
    queryKey: queryKeys.workbenchGenerationOptions(projectId),
    queryFn: () => loadGenerationOptions(projectId),
    enabled: Boolean(projectId),
    staleTime: STALE_MS,
  })
}

export function useWorkbenchGenerationConfig(projectId: string) {
  return useQuery({
    queryKey: queryKeys.workbenchGenerationConfig(projectId),
    queryFn: () => loadGenerationConfig(projectId),
    enabled: Boolean(projectId),
    staleTime: STALE_MS,
  })
}

/**
 * 保存项目生成配置。
 *
 * 成功后失效配置、项目详情与开工预检：这三处都读取同一批模型/参数，
 * 只刷新表单会让树与预检面板继续显示旧值。
 */
export function useSaveGenerationConfig(projectId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: Parameters<typeof saveGenerationConfig>[1]) =>
      saveGenerationConfig(projectId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.workbenchGenerationConfig(projectId),
      })
      void queryClient.invalidateQueries({ queryKey: queryKeys.project(projectId) })
      void queryClient.invalidateQueries({ queryKey: queryKeys.workbenchProject(projectId) })
    },
  })
}

export function useWorkbenchProjectStyle(projectId: string) {
  return useQuery({
    queryKey: queryKeys.workbenchProjectStyle(projectId),
    queryFn: () => loadProjectStyleState(projectId),
    enabled: Boolean(projectId),
    staleTime: STALE_MS,
  })
}

/** 选择风格、锁定风格、分析参考图都只需要失效「项目风格 + 目录」两类查询。 */
export function useProjectStyleActions(projectId: string) {
  const queryClient = useQueryClient()

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.workbenchProjectStyle(projectId) })
    void queryClient.invalidateQueries({ queryKey: queryKeys.workbenchStyleCatalog })
    void queryClient.invalidateQueries({ queryKey: queryKeys.workbenchGenerationConfig(projectId) })
    void queryClient.invalidateQueries({ queryKey: queryKeys.workbenchProject(projectId) })
  }

  const select = useMutation({
    mutationFn: (styleId: string) => selectProjectStyle(projectId, styleId),
    onSuccess: invalidate,
  })
  const lock = useMutation({
    mutationFn: (payload: { style_id?: string | null; sample_file_ids?: string[] }) =>
      lockProjectStyle(projectId, payload),
    onSuccess: invalidate,
  })
  const analyze = useMutation({
    mutationFn: (payload: { file_ids: string[]; model_id?: string | null }) =>
      analyzeStyleReferences(payload),
  })
  const createStyle = useMutation({
    mutationFn: createStyleOption,
    onSuccess: invalidate,
  })
  const updateStyle = useMutation({
    mutationFn: (payload: { styleId: string; body: Parameters<typeof updateStyleOption>[1] }) =>
      updateStyleOption(payload.styleId, payload.body),
    onSuccess: invalidate,
  })
  const upload = useMutation({ mutationFn: uploadStyleImage })

  return { select, lock, analyze, createStyle, updateStyle, upload }
}

export function useStyleAnalysisCapability() {
  return useQuery({
    queryKey: queryKeys.workbenchStyleAnalysisCapability,
    queryFn: loadStyleAnalysisCapability,
    staleTime: 60_000,
  })
}

export function useWorkbenchScriptDocuments(projectId: string) {
  return useQuery({
    queryKey: queryKeys.workbenchScriptDocuments(projectId),
    queryFn: () => loadScriptDocuments(projectId),
    enabled: Boolean(projectId),
    staleTime: STALE_MS,
  })
}

export function useWorkbenchScriptDocument(documentId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.workbenchScriptDocument(documentId ?? ''),
    queryFn: () => loadScriptDocument(documentId as string),
    enabled: Boolean(documentId),
    staleTime: STALE_MS,
  })
}

export function useWorkbenchScriptVersion(
  documentId: string | undefined,
  versionId: string | undefined,
) {
  return useQuery({
    queryKey: queryKeys.workbenchScriptVersion(documentId ?? '', versionId ?? ''),
    queryFn: () => loadScriptDocumentVersion(documentId as string, versionId as string),
    enabled: Boolean(documentId) && Boolean(versionId),
    staleTime: 60_000,
  })
}

/** 上传/启用文档后统一失效文档列表、文档详情、项目与章节缓存。 */
export function useScriptDocumentActions(projectId: string) {
  const queryClient = useQueryClient()
  const invalidate = (documentId?: string) => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.workbenchScriptDocuments(projectId) })
    if (documentId) {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.workbenchScriptDocument(documentId),
      })
    }
    void queryClient.invalidateQueries({ queryKey: queryKeys.workbenchChapters(projectId) })
    void queryClient.invalidateQueries({ queryKey: queryKeys.workbenchProject(projectId) })
  }

  const uploadWorld = useMutation({
    mutationFn: (payload: { file: File; title?: string }) =>
      uploadWorldbuildingDocument(projectId, payload.file, payload.title),
    onSuccess: (data) => invalidate(data.document.id),
  })
  const uploadEpisode = useMutation({
    mutationFn: (payload: { chapterId: string; file: File; title?: string }) =>
      uploadEpisodeDocument(projectId, payload.chapterId, payload.file, payload.title),
    onSuccess: (data) => invalidate(data.document.id),
  })
  const activate = useMutation({
    mutationFn: (payload: { documentId: string; versionId: string }) =>
      activateScriptDocumentVersion(payload.documentId, payload.versionId),
    onSuccess: (data) => invalidate(data.id),
  })

  return { uploadWorld, uploadEpisode, activate }
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


export function useScriptParseRun(runId: string | null | undefined) {
  return useQuery({
    queryKey: queryKeys.workbenchScriptParseRun(runId ?? ''),
    queryFn: () => loadScriptParseRun(runId as string),
    enabled: Boolean(runId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'pending' || status === 'running' ? 2000 : false
    },
  })
}

export function useDocumentParseRuns(documentId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.workbenchScriptParseRuns(documentId ?? ''),
    queryFn: () => listDocumentParseRuns(documentId as string),
    enabled: Boolean(documentId),
    staleTime: 10_000,
  })
}

/** 解析/审核/确认/差异动作统一失效脚本相关缓存。 */
export function useScriptParseActions(
  projectId: string,
  documentId?: string,
) {
  const queryClient = useQueryClient()
  const invalidate = (runId?: string) => {
    if (runId) {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.workbenchScriptParseRun(runId),
      })
    }
    if (documentId) {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.workbenchScriptParseRuns(documentId),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.workbenchScriptDocument(documentId),
      })
    }
    void queryClient.invalidateQueries({ queryKey: queryKeys.workbenchScriptDocuments(projectId) })
    void queryClient.invalidateQueries({ queryKey: queryKeys.workbenchChapters(projectId) })
    void queryClient.invalidateQueries({ queryKey: queryKeys.workbenchProject(projectId) })
  }

  const start = useMutation({
    mutationFn: (payload: { versionId: string; force?: boolean; modelId?: string | null }) =>
      startScriptParse(payload.versionId, {
        force: payload.force ?? false,
        model_id: payload.modelId ?? null,
      }),
    onSuccess: (data) => invalidate(data.run.id),
  })
  const updateCandidate = useMutation({
    mutationFn: (payload: {
      runId: string
      candidateId: string
      body: Parameters<typeof updateScriptParseCandidate>[2]
    }) => updateScriptParseCandidate(payload.runId, payload.candidateId, payload.body),
    onSuccess: (_data, variables) => invalidate(variables.runId),
  })
  const addCandidate = useMutation({
    mutationFn: (payload: {
      runId: string
      candidateType: string
      payload: Record<string, unknown>
    }) =>
      addScriptParseCandidate(payload.runId, {
        candidate_type: payload.candidateType,
        payload: payload.payload,
        evidence: [],
      }),
    onSuccess: (_data, variables) => invalidate(variables.runId),
  })
  const deleteCandidate = useMutation({
    mutationFn: (payload: { runId: string; candidateId: string }) =>
      deleteScriptParseCandidate(payload.runId, payload.candidateId),
    onSuccess: (_data, variables) => invalidate(variables.runId),
  })
  const merge = useMutation({
    mutationFn: (payload: { runId: string; sourceId: string; targetId: string }) =>
      mergeScriptParseCandidates(payload.runId, payload.sourceId, payload.targetId),
    onSuccess: (_data, variables) => invalidate(variables.runId),
  })
  const confirm = useMutation({
    mutationFn: (runId: string) => confirmScriptParseRun(runId),
    onSuccess: (_data, runId) => invalidate(runId),
  })
  const diff = useMutation({
    mutationFn: (payload: { documentId: string; oldVersionId?: string | null }) =>
      createScriptDiffReport(payload.documentId, payload.oldVersionId),
  })
  const decideDiff = useMutation({
    mutationFn: (payload: { reportId: string; status: 'accepted' | 'ignored' }) =>
      decideScriptDiffReport(payload.reportId, payload.status),
  })

  return {
    start,
    updateCandidate,
    addCandidate,
    deleteCandidate,
    merge,
    confirm,
    diff,
    decideDiff,
  }
}
