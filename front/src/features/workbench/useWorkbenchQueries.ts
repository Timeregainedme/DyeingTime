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
import type { SceneGroupRead, ShotRead } from '../../services/generated'
import { queryKeys } from '../../lib/queryClient'
import type { WorkbenchAssetType } from './routes'
import {
  addCharacterAlias,
  adoptAssetCandidate,
  createAssetVersion,
  createCharacterIdentityVersion,
  deleteAssetCandidate,
  deleteCharacterAlias,
  generateAssetCandidates,
  loadAllChapters,
  loadAllShots,
  loadAssetDetail,
  loadAssetImpact,
  loadAssetProfile,
  loadAvailableVoices,
  loadCharacterVoice,
  loadGenerationConfig,
  loadGenerationOptions,
  loadGlobalAssets,
  loadProject,
  loadProjectCharacters,
  loadProjectStyleState,
  loadProjectTimeline,
  loadRuntimeSummary,
  loadSceneGroup,
  loadSceneGroups,
  loadSceneGroupShots,
  loadSceneGroupSuggestions,
  loadShotAssetVersions,
  loadShotPlan,
  loadShotPlans,
  loadShotPlanStats,
  loadScriptDocument,
  addShotPlanCandidate,
  confirmShotPlan,
  createShotPlan,
  deleteShotPlanCandidate,
  duplicateShotPlanCandidate,
  mergeShotPlanCandidates,
  reorderShotPlanCandidates,
  updateShotPlanCandidate,
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
  createSceneGroup,
  deleteSceneGroup,
  importSceneGroupSuggestions,
  reorderChapterShots,
  reorderSceneGroups,
  updateSceneGroup,
  updateScriptParseCandidate,
  updateShot,
  updateShotDetail,
  updateAssetProfile,
  updateCharacterVoice,
  uploadAssetCandidate,
  lockCharacterIdentity,
  switchAssetVersion,
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
    queryFn: () => loadGlobalAssets(projectId, assetType),
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

/** 按已展开剧集加载正式场次；未展开剧集不发请求。 */
export function useWorkbenchSceneGroupQueries(projectId: string, chapterIds: string[]) {
  return useQueries({
    queries: chapterIds.map((chapterId) => ({
      queryKey: queryKeys.workbenchSceneGroups(projectId, chapterId),
      queryFn: () => loadSceneGroups(chapterId),
      staleTime: STALE_MS,
    })),
  })
}

export function useWorkbenchSceneGroups(projectId: string, chapterId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.workbenchSceneGroups(projectId, chapterId ?? ''),
    queryFn: () => loadSceneGroups(chapterId as string),
    enabled: Boolean(projectId) && Boolean(chapterId),
    staleTime: STALE_MS,
  })
}

export function useWorkbenchSceneGroup(
  projectId: string,
  chapterId: string | undefined,
  groupId: string | undefined,
) {
  return useQuery({
    queryKey: queryKeys.workbenchSceneGroup(projectId, groupId ?? ''),
    queryFn: () => loadSceneGroup(groupId as string),
    enabled: Boolean(projectId) && Boolean(chapterId) && Boolean(groupId),
    staleTime: STALE_MS,
  })
}

export function useWorkbenchSceneGroupShots(projectId: string, groupId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.workbenchSceneGroupShots(projectId, groupId ?? ''),
    queryFn: () => loadSceneGroupShots(groupId as string),
    enabled: Boolean(projectId) && Boolean(groupId),
    staleTime: STALE_MS,
  })
}

export function useSceneGroupSuggestions(projectId: string, chapterId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.workbenchSceneGroupSuggestions(projectId, chapterId ?? ''),
    queryFn: () => loadSceneGroupSuggestions(chapterId as string),
    enabled: Boolean(projectId) && Boolean(chapterId),
    staleTime: 10_000,
  })
}

/** 场次/镜头顺序变更后统一失效章节镜头、场次与工作台树缓存。 */
export function useChapterShotPlans(projectId: string, chapterId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.workbenchShotPlans(projectId, chapterId ?? ''),
    queryFn: () => loadShotPlans(chapterId as string),
    enabled: Boolean(projectId) && Boolean(chapterId),
    staleTime: 5_000,
  })
}

export function useShotPlan(projectId: string, draftId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.workbenchShotPlan(projectId, draftId ?? ''),
    queryFn: () => loadShotPlan(draftId as string),
    enabled: Boolean(projectId) && Boolean(draftId),
    staleTime: 2_000,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'draft' || status === 'generating' ? 2000 : false
    },
  })
}

export function useShotPlanStats(projectId: string, chapterId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.workbenchShotPlanStats(projectId, chapterId ?? ''),
    queryFn: () => loadShotPlanStats(chapterId as string),
    enabled: Boolean(projectId) && Boolean(chapterId),
    staleTime: 5_000,
  })
}

export function useShotAssetVersions(projectId: string, shotId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.workbenchShotAssetVersions(projectId, shotId ?? ''),
    queryFn: () => loadShotAssetVersions(shotId as string),
    enabled: Boolean(projectId) && Boolean(shotId),
    staleTime: STALE_MS,
  })
}

/** 分镜规划动作；确认后刷新镜头、场次、规划与统计缓存。 */
export function useShotPlanActions(projectId: string, chapterId: string) {
  const queryClient = useQueryClient()
  const invalidate = (draftId?: string) => {
    if (draftId) {
      void queryClient.invalidateQueries({ queryKey: queryKeys.workbenchShotPlan(projectId, draftId) })
    }
    void queryClient.invalidateQueries({ queryKey: queryKeys.workbenchShotPlans(projectId, chapterId) })
    void queryClient.invalidateQueries({ queryKey: queryKeys.workbenchShotPlanStats(projectId, chapterId) })
    void queryClient.invalidateQueries({ queryKey: queryKeys.workbenchShots(projectId, chapterId) })
    void queryClient.invalidateQueries({ queryKey: queryKeys.workbenchSceneGroups(projectId, chapterId) })
    void queryClient.invalidateQueries({ queryKey: ['workbench', projectId, 'scene-group'] })
  }
  const create = useMutation({
    mutationFn: (body: Parameters<typeof createShotPlan>[1]) => createShotPlan(chapterId, body),
    onSuccess: (data) => invalidate(data.id),
  })
  const updateCandidate = useMutation({
    mutationFn: (payload: {
      draftId: string
      candidateId: string
      body: Parameters<typeof updateShotPlanCandidate>[2]
    }) => updateShotPlanCandidate(payload.draftId, payload.candidateId, payload.body),
    onSuccess: (_data, variables) => invalidate(variables.draftId),
  })
  const addCandidate = useMutation({
    mutationFn: (payload: { draftId: string; body: Parameters<typeof addShotPlanCandidate>[1] }) =>
      addShotPlanCandidate(payload.draftId, payload.body),
    onSuccess: (_data, variables) => invalidate(variables.draftId),
  })
  const duplicate = useMutation({
    mutationFn: (payload: { draftId: string; candidateId: string }) =>
      duplicateShotPlanCandidate(payload.draftId, payload.candidateId),
    onSuccess: (_data, variables) => invalidate(variables.draftId),
  })
  const remove = useMutation({
    mutationFn: (payload: { draftId: string; candidateId: string }) =>
      deleteShotPlanCandidate(payload.draftId, payload.candidateId),
    onSuccess: (_data, variables) => invalidate(variables.draftId),
  })
  const reorder = useMutation({
    mutationFn: (payload: { draftId: string; candidateIds: string[] }) =>
      reorderShotPlanCandidates(payload.draftId, payload.candidateIds),
    onSuccess: (_data, variables) => invalidate(variables.draftId),
  })
  const merge = useMutation({
    mutationFn: (payload: { draftId: string; sourceId: string; targetId: string }) =>
      mergeShotPlanCandidates(payload.draftId, payload.sourceId, payload.targetId),
    onSuccess: (_data, variables) => invalidate(variables.draftId),
  })
  const confirm = useMutation({
    mutationFn: (payload: { draftId: string; appendToExisting: boolean }) =>
      confirmShotPlan(payload.draftId, payload.appendToExisting),
    onSuccess: (_data, variables) => invalidate(variables.draftId),
  })
  return { create, updateCandidate, addCandidate, duplicate, remove, reorder, merge, confirm }
}

export function useSceneGroupActions(projectId: string, chapterId: string) {
  const queryClient = useQueryClient()
  const invalidate = () => {
    void queryClient.invalidateQueries({
      queryKey: queryKeys.workbenchSceneGroups(projectId, chapterId),
    })
    void queryClient.invalidateQueries({
      queryKey: queryKeys.workbenchSceneGroupSuggestions(projectId, chapterId),
    })
    void queryClient.invalidateQueries({ queryKey: queryKeys.workbenchShots(projectId, chapterId) })
    void queryClient.invalidateQueries({ queryKey: queryKeys.workbenchSceneGroup(projectId, '') })
    void queryClient.invalidateQueries({ queryKey: ['workbench', projectId, 'scene-group'] })
    void queryClient.invalidateQueries({ queryKey: ['workbench', projectId, 'scene-group-shots'] })
    void queryClient.invalidateQueries({ queryKey: queryKeys.workbenchProject(projectId) })
    void queryClient.invalidateQueries({ queryKey: ['workbench', projectId, 'scene-groups'] })
  }
  const create = useMutation({
    mutationFn: (body: Parameters<typeof createSceneGroup>[1]) =>
      createSceneGroup(chapterId, body),
    onSuccess: invalidate,
  })
  const update = useMutation({
    mutationFn: (payload: { groupId: string; body: Parameters<typeof updateSceneGroup>[1] }) =>
      updateSceneGroup(payload.groupId, payload.body),
    onSuccess: invalidate,
  })
  const remove = useMutation({
    mutationFn: (groupId: string) => deleteSceneGroup(groupId),
    onSuccess: invalidate,
  })
  const reorder = useMutation({
    mutationFn: (groupIds: string[]) => reorderSceneGroups(chapterId, groupIds),
    onSuccess: invalidate,
  })
  const reorderShots = useMutation({
    mutationFn: (items: Array<{ shot_id: string; scene_group_id: string | null }>) =>
      reorderChapterShots(chapterId, items),
    onSuccess: invalidate,
  })
  const importSuggestions = useMutation({
    mutationFn: (body: Parameters<typeof importSceneGroupSuggestions>[1]) =>
      importSceneGroupSuggestions(chapterId, body),
    onSuccess: invalidate,
  })
  return { create, update, remove, reorder, reorderShots, importSuggestions }
}

/** P4 资产档案；有 pending 候选时自动轮询任务结果。 */
export function useAssetProfile(
  projectId: string,
  assetType: WorkbenchAssetType,
  assetId: string | undefined,
) {
  return useQuery({
    queryKey: queryKeys.workbenchAssetProfile(projectId, assetType, assetId ?? ''),
    queryFn: () => loadAssetProfile(projectId, assetType, assetId as string),
    enabled: Boolean(projectId) && Boolean(assetType) && Boolean(assetId),
    staleTime: 5_000,
    refetchInterval: (query) =>
      query.state.data?.candidates?.some((item) => item.status === 'pending') ? 2500 : false,
  })
}

export function useAssetImpact(
  projectId: string,
  assetType: WorkbenchAssetType,
  assetId: string | undefined,
) {
  return useQuery({
    queryKey: queryKeys.workbenchAssetImpact(projectId, assetType, assetId ?? ''),
    queryFn: () => loadAssetImpact(projectId, assetType, assetId as string),
    enabled: Boolean(projectId) && Boolean(assetType) && Boolean(assetId),
    staleTime: 15_000,
  })
}

export function useCharacterVoice(projectId: string, characterId: string | undefined) {
  return useQuery({
    queryKey: ['workbench', projectId, 'character-voice', characterId ?? ''],
    queryFn: () => loadCharacterVoice(projectId, characterId as string),
    enabled: Boolean(projectId) && Boolean(characterId),
    staleTime: 15_000,
  })
}

export function useAvailableVoices(modelId?: string | null) {
  return useQuery({
    queryKey: queryKeys.workbenchVoices(modelId ?? 'default'),
    queryFn: () => loadAvailableVoices(modelId),
    staleTime: 120_000,
  })
}

/** P4 资产编辑动作；成功后统一刷新档案、列表和项目树缩略图。 */
export function useAssetProfileActions(
  projectId: string,
  assetType: WorkbenchAssetType,
  assetId: string,
) {
  const queryClient = useQueryClient()
  const invalidate = () => {
    void queryClient.invalidateQueries({
      queryKey: queryKeys.workbenchAssetProfile(projectId, assetType, assetId),
    })
    void queryClient.invalidateQueries({
      queryKey: queryKeys.workbenchAssetImpact(projectId, assetType, assetId),
    })
    void queryClient.invalidateQueries({
      queryKey: queryKeys.workbenchAssets(projectId, assetType),
    })
    void queryClient.invalidateQueries({ queryKey: queryKeys.workbenchProject(projectId) })
  }
  const update = useMutation({
    mutationFn: (body: Parameters<typeof updateAssetProfile>[3]) =>
      updateAssetProfile(projectId, assetType, assetId, body),
    onSuccess: invalidate,
  })
  const addAlias = useMutation({
    mutationFn: (alias: string) => addCharacterAlias(projectId, assetId, alias),
    onSuccess: invalidate,
  })
  const removeAlias = useMutation({
    mutationFn: (aliasId: number) => deleteCharacterAlias(projectId, assetId, aliasId),
    onSuccess: invalidate,
  })
  const createVersion = useMutation({
    mutationFn: (body: Parameters<typeof createAssetVersion>[3]) =>
      assetType === 'character'
        ? createAssetVersion(projectId, assetType, assetId, body)
        : createAssetVersion(projectId, assetType, assetId, body),
    onSuccess: invalidate,
  })
  const createIdentityVersion = useMutation({
    mutationFn: (body: Parameters<typeof createCharacterIdentityVersion>[2]) =>
      createCharacterIdentityVersion(projectId, assetId, body),
    onSuccess: invalidate,
  })
  const switchVersion = useMutation({
    mutationFn: (payload: { versionId: string; expectedLockVersion?: number }) =>
      switchAssetVersion(
        projectId,
        assetType,
        assetId,
        payload.versionId,
        payload.expectedLockVersion,
      ),
    onSuccess: invalidate,
  })
  const generate = useMutation({
    mutationFn: (payload: { viewAngle: string; prompt?: string | null }) =>
      generateAssetCandidates(projectId, assetType, assetId, {
        view_angle: payload.viewAngle as 'front' | 'left' | 'right' | 'back' | 'three_quarter',
        candidate_count: 2,
        prompt: payload.prompt || null,
      }),
    onSuccess: invalidate,
  })
  const upload = useMutation({
    mutationFn: (payload: { file: File; viewAngle: string; versionId?: string | null }) =>
      uploadAssetCandidate(
        projectId,
        assetType,
        assetId,
        payload.file,
        payload.viewAngle,
        payload.versionId,
      ),
    onSuccess: invalidate,
  })
  const adopt = useMutation({
    mutationFn: (payload: { candidateId: number; versionId?: string | null }) =>
      adoptAssetCandidate(projectId, assetType, assetId, payload.candidateId, payload.versionId),
    onSuccess: invalidate,
  })
  const removeCandidate = useMutation({
    mutationFn: (candidateId: number) =>
      deleteAssetCandidate(projectId, assetType, assetId, candidateId),
    onSuccess: invalidate,
  })
  const lock = useMutation({
    mutationFn: (expectedLockVersion?: number) =>
      lockCharacterIdentity(projectId, assetId, expectedLockVersion),
    onSuccess: invalidate,
  })
  const updateVoice = useMutation({
    mutationFn: (body: Parameters<typeof updateCharacterVoice>[2]) =>
      updateCharacterVoice(projectId, assetId, body),
    onSuccess: () => {
      invalidate()
      void queryClient.invalidateQueries({
        queryKey: ['workbench', projectId, 'character-voice', assetId],
      })
    },
  })
  return {
    update,
    addAlias,
    removeAlias,
    createVersion,
    createIdentityVersion,
    switchVersion,
    generate,
    upload,
    adopt,
    removeCandidate,
    lock,
    updateVoice,
  }
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
export function collectSceneGroupsByChapter(
  chapterIds: string[],
  results: Array<{ data?: SceneGroupRead[] }>,
): Record<string, SceneGroupRead[]> {
  const map: Record<string, SceneGroupRead[]> = {}
  results.forEach((result, index) => {
    const chapterId = chapterIds[index]
    if (chapterId && result.data) map[chapterId] = result.data
  })
  return map
}

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


export function useShotEditActions(projectId: string, chapterId: string, shotId: string) {
  const queryClient = useQueryClient()
  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.workbenchShot(projectId, shotId) })
    void queryClient.invalidateQueries({ queryKey: queryKeys.workbenchShotDetail(projectId, shotId) })
    void queryClient.invalidateQueries({ queryKey: queryKeys.workbenchShots(projectId, chapterId) })
    void queryClient.invalidateQueries({ queryKey: queryKeys.workbenchSceneGroups(projectId, chapterId) })
    void queryClient.invalidateQueries({ queryKey: ['workbench', projectId, 'scene-group'] })
  }
  const updateShotMutation = useMutation({
    mutationFn: (body: Parameters<typeof updateShot>[1]) => updateShot(shotId, body),
    onSuccess: invalidate,
  })
  const updateDetail = useMutation({
    mutationFn: (body: Parameters<typeof updateShotDetail>[1]) => updateShotDetail(shotId, body),
    onSuccess: invalidate,
  })
  return { updateShot: updateShotMutation, updateDetail }
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
