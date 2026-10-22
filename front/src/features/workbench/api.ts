/**
 * 工作台数据访问层。
 *
 * 约束（AGENTS.md）：前端不得新增手写 service 封装，所有请求一律走
 * `services/generated`。这里只做三件事，不复制接口协议：
 *   1. 把分页接口翻页拉全，避免「固定 page_size 造成数据遗漏」；
 *   2. 把后端 dict / 分页信封收敛成工作台需要的稳定形状；
 *   3. 提供统一的错误文案。
 */
import {
  StudioAssetProfilesService,
  StudioAudioTasksService,
  StudioChaptersService,
  StudioEntitiesService,
  StudioFilesService,
  StudioProjectsService,
  StudioScriptDocumentsService,
  StudioScriptParseService,
  StudioShotDetailsService,
  StudioShotsService,
  StudioStylesService,
  StudioTimelineService,
} from '../../services/generated'
import type {
  AssetImageCandidateRead,
  AssetProfileRead,
  AssetProfileUpdate,
  ChapterRead,
  CharacterAliasRead,
  CreateDerivedVersionRequest,
  GenerateCandidatesRequest,
  ProjectGenerationConfigRead,
  ProjectGenerationConfigUpdate,
  ProjectGenerationOptionsRead,
  ProjectRead,
  ProjectStyleOptionRead,
  ProjectStyleOptionCreate,
  ProjectStyleOptionUpdate,
  ProjectStyleOptionsRead,
  ProjectStyleStateRead,
  ProjectTimelineRead,
  ScriptDiffReportRead,
  ScriptDocumentRead,
  ScriptDocumentUploadRead,
  ScriptDocumentVersionDetailRead,
  ScriptParseCandidateCreate,
  ScriptParseCandidateRead,
  ScriptParseCandidateUpdate,
  ScriptParseRunRead,
  ScriptParseTaskRead,
  ShotDetailRead,
  ShotPreparationStateRead,
  ShotRead,
  ShotRuntimeSummaryRead,
  ShotVideoReadinessRead,
  StyleAnalysisCapabilityRead,
  StyleAnalysisRead,
  VoiceBindingRead,
  VoiceBindingUpdate,
  VoiceItem,
} from '../../services/generated'
import type { WorkbenchAssetItem } from './types'
import type { WorkbenchAssetType } from './routes'

/** 与后端 `page_size` 上限一致；超过这个值请求会被 422 拒绝。 */
const PAGE_SIZE = 100

/**
 * 翻页硬保护。
 *
 * 200 页 × 100 条 = 20,000 条。超过时**抛错而不是静默截断**：
 * 工作台允许一次加载整章镜头，静默少几条会让用户以为镜头丢了。
 */
const MAX_PAGES = 200

interface PaginatedEnvelope<T> {
  data?: {
    items?: T[]
    pagination?: {
      total?: number
      max_page?: number
    }
  } | null
}

/**
 * 把一个分页接口拉全。
 *
 * 递归条件以 `max_page` 为准，而不是「本页是否满 100 条」：
 * 后者在服务端改变 page_size 语义时会提前停。
 */
export async function fetchAllPages<T>(
  loadPage: (page: number, pageSize: number) => Promise<PaginatedEnvelope<T>>,
): Promise<T[]> {
  const items: T[] = []
  for (let page = 1; page <= MAX_PAGES; page += 1) {
    const response = await loadPage(page, PAGE_SIZE)
    const pageItems = response.data?.items ?? []
    items.push(...pageItems)

    const maxPage = response.data?.pagination?.max_page ?? 1
    if (pageItems.length === 0 || page >= maxPage) return items
  }

  throw new Error(`列表超过 ${MAX_PAGES * PAGE_SIZE} 条，已停止加载以避免数据遗漏`)
}

/** 把任意异常收敛成可展示文案；401 由全局请求层处理，这里不重复判断。 */
export function toErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) return `${fallback}：${error.message}`
  return fallback
}

/** 项目详情。 */
export async function loadProject(projectId: string): Promise<ProjectRead> {
  const response = await StudioProjectsService.getProjectApiV1StudioProjectsProjectIdGet({ projectId })
  if (!response.data) throw new Error('服务端没有返回项目数据')
  return response.data
}

/** 项目风格目录（只读预览；P2 才会做风格锁定与样张确认）。 */
export async function loadStyleOptions(): Promise<ProjectStyleOptionsRead> {
  const response = await StudioProjectsService.getProjectStyleOptionsApiV1StudioProjectsStyleOptionsGet()
  if (!response.data) throw new Error('服务端没有返回风格目录')
  return response.data
}

/** 项目可配置的图片 / 视频 / 音频模型与业务约束。 */
export async function loadGenerationOptions(
  projectId: string,
): Promise<ProjectGenerationOptionsRead> {
  const response =
    await StudioProjectsService.getProjectGenerationOptionsApiApiV1StudioProjectsProjectIdGenerationOptionsGet(
      { projectId },
    )
  if (!response.data) throw new Error('服务端没有返回模型选项')
  return response.data
}

/** 项目生成配置（含生效值、检查项与快照）。 */
export async function loadGenerationConfig(
  projectId: string,
): Promise<ProjectGenerationConfigRead> {
  const response =
    await StudioProjectsService.getProjectGenerationConfigApiApiV1StudioProjectsProjectIdGenerationConfigGet(
      { projectId },
    )
  if (!response.data) throw new Error('服务端没有返回生成配置')
  return response.data
}

/** 保存项目生成配置；confirm=true 时服务端会重新校验并写入快照。 */
export async function saveGenerationConfig(
  projectId: string,
  body: ProjectGenerationConfigUpdate,
): Promise<ProjectGenerationConfigRead> {
  const response =
    await StudioProjectsService.saveProjectGenerationConfigApiApiV1StudioProjectsProjectIdGenerationConfigPut(
      { projectId, requestBody: body },
    )
  if (!response.data) throw new Error('服务端没有返回保存结果')
  return response.data
}

/** 风格目录明细（含说明与提示词质感描述），用于风格圣经面板。 */
export async function loadStyleCatalog(): Promise<ProjectStyleOptionRead[]> {
  const response = await StudioStylesService.listStylesApiV1StudioStylesGet()
  return response.data ?? []
}

/** 项目风格状态：当前选择或锁定快照。 */
export async function loadProjectStyleState(projectId: string): Promise<ProjectStyleStateRead> {
  const response =
    await StudioProjectsService.getProjectStyleStateApiApiV1StudioProjectsProjectIdStyleGet({
      projectId,
    })
  if (!response.data) throw new Error('服务端没有返回项目风格状态')
  return response.data
}

export async function selectProjectStyle(
  projectId: string,
  styleId: string,
): Promise<ProjectStyleStateRead> {
  const response =
    await StudioProjectsService.selectProjectStyleApiApiV1StudioProjectsProjectIdStylePut({
      projectId,
      requestBody: { style_id: styleId },
    })
  if (!response.data) throw new Error('服务端没有返回选择结果')
  return response.data
}

export async function lockProjectStyle(
  projectId: string,
  payload: { style_id?: string | null; sample_file_ids?: string[] },
): Promise<ProjectStyleStateRead> {
  const response =
    await StudioProjectsService.lockProjectStyleApiApiV1StudioProjectsProjectIdStyleLockPost({
      projectId,
      requestBody: payload,
    })
  if (!response.data) throw new Error('服务端没有返回锁定结果')
  return response.data
}

export async function loadStyleAnalysisCapability(): Promise<StyleAnalysisCapabilityRead> {
  const response =
    await StudioStylesService.getStyleAnalysisCapabilityApiApiV1StudioStylesAnalysisCapabilityGet()
  if (!response.data) throw new Error('服务端没有返回分析能力')
  return response.data
}

export async function analyzeStyleReferences(payload: {
  file_ids: string[]
  model_id?: string | null
}): Promise<StyleAnalysisRead> {
  const response = await StudioStylesService.analyzeStyleApiApiV1StudioStylesAnalyzePost({
    requestBody: payload,
  })
  if (!response.data) throw new Error('服务端没有返回分析结果')
  return response.data
}

export async function createStyleOption(
  payload: ProjectStyleOptionCreate,
): Promise<ProjectStyleOptionRead> {
  const response = await StudioStylesService.createStyleApiV1StudioStylesPost({
    requestBody: payload,
  })
  if (!response.data) throw new Error('服务端没有返回新建风格')
  return response.data
}

export async function updateStyleOption(
  styleId: string,
  payload: ProjectStyleOptionUpdate,
): Promise<ProjectStyleOptionRead> {
  const response = await StudioStylesService.updateStyleApiV1StudioStylesStyleIdPatch({
    styleId,
    requestBody: payload,
  })
  if (!response.data) throw new Error('服务端没有返回更新结果')
  return response.data
}

/** 上传风格参考图 / 样张；返回文件 ID。 */
export async function uploadStyleImage(file: File): Promise<string> {
  const response = await StudioFilesService.uploadFileApiApiV1StudioFilesUploadPost({
    // 生成客户端的类型把二进制字段写成了 string；运行时是 Blob，request 层会正确放入 FormData。
    formData: { file: file as unknown as string },
    name: file.name,
  })
  if (!response.data) throw new Error('上传失败：服务端没有返回文件')
  return response.data.id
}

/** 项目下的世界观与每集剧本文档。 */
export async function loadScriptDocuments(projectId: string): Promise<ScriptDocumentRead[]> {
  const response =
    await StudioScriptDocumentsService.listScriptDocumentsApiApiV1StudioProjectsProjectIdScriptDocumentsGet(
      { projectId },
    )
  return response.data?.items ?? []
}

export async function uploadWorldbuildingDocument(
  projectId: string,
  file: File,
  title?: string,
): Promise<ScriptDocumentUploadRead> {
  const response =
    await StudioScriptDocumentsService.uploadWorldbuildingDocumentApiApiV1StudioProjectsProjectIdScriptDocumentsWorldbuildingPost(
      {
        projectId,
        formData: { file: file as unknown as string, title: title || null },
      },
    )
  if (!response.data) throw new Error('上传失败：服务端没有返回文档')
  return response.data
}

export async function uploadEpisodeDocument(
  projectId: string,
  chapterId: string,
  file: File,
  title?: string,
): Promise<ScriptDocumentUploadRead> {
  const response =
    await StudioScriptDocumentsService.uploadEpisodeDocumentApiApiV1StudioProjectsProjectIdChaptersChapterIdScriptDocumentPost(
      {
        projectId,
        chapterId,
        formData: { file: file as unknown as string, title: title || null },
      },
    )
  if (!response.data) throw new Error('上传失败：服务端没有返回文档')
  return response.data
}

export async function loadScriptDocument(documentId: string): Promise<ScriptDocumentRead> {
  const response =
    await StudioScriptDocumentsService.getScriptDocumentApiApiV1StudioScriptDocumentsDocumentIdGet(
      { documentId },
    )
  if (!response.data) throw new Error('服务端没有返回文档详情')
  return response.data
}

export async function loadScriptDocumentVersion(
  documentId: string,
  versionId: string,
): Promise<ScriptDocumentVersionDetailRead> {
  const response =
    await StudioScriptDocumentsService.getScriptDocumentVersionApiApiV1StudioScriptDocumentsDocumentIdVersionsVersionIdGet(
      { documentId, versionId },
    )
  if (!response.data) throw new Error('服务端没有返回版本原文')
  return response.data
}

export async function activateScriptDocumentVersion(
  documentId: string,
  versionId: string,
): Promise<ScriptDocumentRead> {
  const response =
    await StudioScriptDocumentsService.activateScriptDocumentVersionApiApiV1StudioScriptDocumentsDocumentIdVersionsVersionIdActivatePost(
      { documentId, versionId },
    )
  if (!response.data) throw new Error('服务端没有返回启用结果')
  return response.data
}

export async function startScriptParse(
  versionId: string,
  payload: { model_id?: string | null; force?: boolean } = {},
): Promise<ScriptParseTaskRead> {
  const response =
    await StudioScriptParseService.startScriptParseApiApiV1StudioScriptDocumentVersionsVersionIdParsePost(
      { versionId, requestBody: payload },
    )
  if (!response.data) throw new Error('服务端没有返回解析任务')
  return response.data
}

export async function loadScriptParseRun(runId: string): Promise<ScriptParseRunRead> {
  const response =
    await StudioScriptParseService.getScriptParseRunApiApiV1StudioScriptParseRunsRunIdGet({
      runId,
    })
  if (!response.data) throw new Error('服务端没有返回解析运行')
  return response.data
}

export async function listDocumentParseRuns(
  documentId: string,
): Promise<ScriptParseRunRead[]> {
  const response =
    await StudioScriptParseService.listScriptParseRunsApiApiV1StudioScriptDocumentsDocumentIdParseRunsGet(
      { documentId },
    )
  return response.data ?? []
}

export async function updateScriptParseCandidate(
  runId: string,
  candidateId: string,
  body: ScriptParseCandidateUpdate,
): Promise<ScriptParseCandidateRead> {
  const response =
    await StudioScriptParseService.updateScriptParseCandidateApiApiV1StudioScriptParseRunsRunIdCandidatesCandidateIdPatch(
      { runId, candidateId, requestBody: body },
    )
  if (!response.data) throw new Error('服务端没有返回候选')
  return response.data
}

export async function addScriptParseCandidate(
  runId: string,
  body: ScriptParseCandidateCreate,
): Promise<ScriptParseCandidateRead> {
  const response =
    await StudioScriptParseService.createScriptParseCandidateApiApiV1StudioScriptParseRunsRunIdCandidatesPost(
      { runId, requestBody: body },
    )
  if (!response.data) throw new Error('服务端没有返回新增候选')
  return response.data
}

export async function deleteScriptParseCandidate(
  runId: string,
  candidateId: string,
): Promise<ScriptParseRunRead> {
  const response =
    await StudioScriptParseService.deleteScriptParseCandidateApiApiV1StudioScriptParseRunsRunIdCandidatesCandidateIdDelete(
      { runId, candidateId },
    )
  if (!response.data) throw new Error('服务端没有返回删除后的解析运行')
  return response.data
}

export async function mergeScriptParseCandidates(
  runId: string,
  sourceCandidateId: string,
  targetCandidateId: string,
): Promise<ScriptParseRunRead> {
  const response =
    await StudioScriptParseService.mergeScriptParseCandidatesApiApiV1StudioScriptParseRunsRunIdMergePost(
      {
        runId,
        requestBody: {
          source_candidate_id: sourceCandidateId,
          target_candidate_id: targetCandidateId,
        },
      },
    )
  if (!response.data) throw new Error('服务端没有返回合并结果')
  return response.data
}

export async function confirmScriptParseRun(
  runId: string,
): Promise<{ run: ScriptParseRunRead; applied_summary: Record<string, unknown> }> {
  const response =
    await StudioScriptParseService.confirmScriptParseRunApiApiV1StudioScriptParseRunsRunIdConfirmPost(
      { runId },
    )
  if (!response.data) throw new Error('服务端没有返回确认结果')
  return {
    run: response.data.run,
    applied_summary: (response.data.applied_summary ?? {}) as Record<string, unknown>,
  }
}

export async function createScriptDiffReport(
  documentId: string,
  oldVersionId?: string | null,
): Promise<ScriptDiffReportRead> {
  const response =
    await StudioScriptParseService.createScriptDiffApiApiV1StudioScriptDocumentsDocumentIdDiffPost(
      {
        documentId,
        requestBody: { old_version_id: oldVersionId || null },
      },
    )
  if (!response.data) throw new Error('服务端没有返回差异报告')
  return response.data
}

export async function decideScriptDiffReport(
  reportId: string,
  statusValue: 'accepted' | 'ignored',
): Promise<ScriptDiffReportRead> {
  const response =
    await StudioScriptParseService.decideScriptDiffReportApiApiV1StudioScriptDiffReportsReportIdStatusPost(
      { reportId, requestBody: { status: statusValue, decisions: {} } },
    )
  if (!response.data) throw new Error('服务端没有返回差异决策')
  return response.data
}

/** 项目下全部章节，按集数升序。 */
export async function loadAllChapters(projectId: string): Promise<ChapterRead[]> {
  return fetchAllPages<ChapterRead>(async (page, pageSize) =>
    StudioChaptersService.listChaptersApiV1StudioChaptersGet({
      projectId,
      order: 'index',
      isDesc: false,
      page,
      pageSize,
    }),
  )
}

/** 指定章节的全部镜头，按镜头序号升序。 */
export async function loadAllShots(chapterId: string): Promise<ShotRead[]> {
  return fetchAllPages<ShotRead>(async (page, pageSize) =>
    StudioShotsService.listShotsApiV1StudioShotsGet({
      chapterId,
      order: 'index',
      isDesc: false,
      page,
      pageSize,
    }),
  )
}

/** 章节级运行中任务摘要（一次请求返回该章所有镜头）。 */
export async function loadRuntimeSummary(
  chapterId: string,
): Promise<ShotRuntimeSummaryRead[]> {
  const response =
    await StudioShotsService.listShotRuntimeSummaryApiV1StudioShotsRuntimeSummaryGet({ chapterId })
  return response.data ?? []
}

/**
 * 把实体列表接口的 dict 收敛成树节点需要的形状。
 *
 * 字段名差异（`visual_style` / `visualStyle`）在边界处一次处理，
 * 业务组件不再各自做兼容判断。
 */
function normalizeAsset(raw: Record<string, unknown>): WorkbenchAssetItem | null {
  const id = typeof raw.id === 'string' ? raw.id : ''
  if (!id) return null
  return {
    id,
    name: typeof raw.name === 'string' && raw.name ? raw.name : id,
    description: typeof raw.description === 'string' ? raw.description : undefined,
    style: typeof raw.style === 'string' ? raw.style : undefined,
    visualStyle:
      typeof raw.visual_style === 'string'
        ? raw.visual_style
        : typeof raw.visualStyle === 'string'
          ? raw.visualStyle
          : undefined,
    thumbnail: typeof raw.thumbnail === 'string' && raw.thumbnail ? raw.thumbnail : undefined,
  }
}

async function loadAssetsByType(projectId: string, entityType: WorkbenchAssetType): Promise<WorkbenchAssetItem[]> {
  const rows = await fetchAllPages<Record<string, unknown>>(async (page, pageSize) =>
    StudioEntitiesService.listEntitiesApiV1StudioEntitiesEntityTypeGet({
      entityType,
      projectId,
      order: 'name',
      isDesc: false,
      page,
      pageSize,
    }),
  )
  return rows
    .map((row) => normalizeAsset(row))
    .filter((item): item is WorkbenchAssetItem => item !== null)
}

/** 角色按项目查询；后端同时校验工作区。 */
export async function loadProjectCharacters(projectId: string): Promise<WorkbenchAssetItem[]> {
  const rows = await fetchAllPages<Record<string, unknown>>(async (page, pageSize) =>
    StudioEntitiesService.listEntitiesApiV1StudioEntitiesEntityTypeGet({
      entityType: 'character',
      projectId,
      order: 'name',
      isDesc: false,
      page,
      pageSize,
    }),
  )
  return rows
    .map((row) => normalizeAsset(row))
    .filter((item): item is WorkbenchAssetItem => item !== null)
}

/** 场景 / 道具 / 服装是工作区全局资产，但按项目关联表过滤。 */
export function loadGlobalAssets(projectId: string, assetType: WorkbenchAssetType): Promise<WorkbenchAssetItem[]> {
  return loadAssetsByType(projectId, assetType)
}

/** 单个资产详情；返回原始 dict，由面板按类型展示。 */
export async function loadAssetDetail(
  assetType: WorkbenchAssetType,
  assetId: string,
): Promise<Record<string, unknown>> {
  const response = await StudioEntitiesService.getEntityApiV1StudioEntitiesEntityTypeEntityIdGet({
    entityType: assetType,
    entityId: assetId,
  })
  if (!response.data) throw new Error('服务端没有返回资产详情')
  return response.data as Record<string, unknown>
}

/** P4：资产档案（角色圣经 / 当前版本 / 候选图 / 音色来源）。 */
export async function loadAssetProfile(
  projectId: string,
  assetType: WorkbenchAssetType,
  assetId: string,
): Promise<AssetProfileRead> {
  const response =
    await StudioAssetProfilesService.getAssetProfileApiApiV1StudioProjectsProjectIdAssetsAssetTypeAssetIdProfileGet(
      { projectId, assetType, assetId },
    )
  if (!response.data) throw new Error('服务端没有返回资产档案')
  return response.data
}

export async function updateAssetProfile(
  projectId: string,
  assetType: WorkbenchAssetType,
  assetId: string,
  body: AssetProfileUpdate,
): Promise<AssetProfileRead> {
  const response =
    await StudioAssetProfilesService.updateAssetProfileApiApiV1StudioProjectsProjectIdAssetsAssetTypeAssetIdProfilePatch(
      { projectId, assetType, assetId, requestBody: body },
    )
  if (!response.data) throw new Error('服务端没有返回更新后的资产档案')
  return response.data
}

export async function addCharacterAlias(
  projectId: string,
  characterId: string,
  alias: string,
): Promise<CharacterAliasRead> {
  const response =
    await StudioAssetProfilesService.addCharacterAliasApiApiV1StudioProjectsProjectIdAssetsCharacterAssetIdAliasesPost(
      { projectId, assetId: characterId, requestBody: { alias } },
    )
  if (!response.data) throw new Error('服务端没有返回别名')
  return response.data
}

export async function deleteCharacterAlias(
  projectId: string,
  characterId: string,
  aliasId: number,
): Promise<void> {
  await StudioAssetProfilesService.deleteCharacterAliasApiApiV1StudioProjectsProjectIdAssetsCharacterAssetIdAliasesAliasIdDelete(
    { projectId, assetId: characterId, aliasId },
  )
}

export async function createAssetVersion(
  projectId: string,
  assetType: WorkbenchAssetType,
  assetId: string,
  body: CreateDerivedVersionRequest,
): Promise<AssetProfileRead> {
  const response =
    await StudioAssetProfilesService.createAssetVersionApiApiV1StudioProjectsProjectIdAssetsAssetTypeAssetIdVersionsPost(
      { projectId, assetType, assetId, requestBody: body },
    )
  if (!response.data) throw new Error('服务端没有返回版本结果')
  return response.data
}

export async function createCharacterIdentityVersion(
  projectId: string,
  characterId: string,
  body: CreateDerivedVersionRequest,
): Promise<AssetProfileRead> {
  const response =
    await StudioAssetProfilesService.createCharacterIdentityVersionApiApiV1StudioProjectsProjectIdAssetsCharacterAssetIdIdentityVersionsPost(
      { projectId, assetId: characterId, requestBody: body },
    )
  if (!response.data) throw new Error('服务端没有返回身份版本')
  return response.data
}

export async function switchAssetVersion(
  projectId: string,
  assetType: WorkbenchAssetType,
  assetId: string,
  versionId: string,
  expectedLockVersion?: number,
): Promise<AssetProfileRead> {
  const response =
    await StudioAssetProfilesService.switchAssetVersionApiApiV1StudioProjectsProjectIdAssetsAssetTypeAssetIdVersionsVersionIdSwitchPost(
      {
        projectId,
        assetType,
        assetId,
        versionId,
        requestBody: {
          version_id: versionId,
          expected_lock_version: expectedLockVersion ?? null,
        },
      },
    )
  if (!response.data) throw new Error('服务端没有返回版本切换结果')
  return response.data
}

export async function generateAssetCandidates(
  projectId: string,
  assetType: WorkbenchAssetType,
  assetId: string,
  body: GenerateCandidatesRequest,
): Promise<AssetImageCandidateRead[]> {
  const response =
    await StudioAssetProfilesService.generateAssetCandidatesApiApiV1StudioProjectsProjectIdAssetsAssetTypeAssetIdCandidatesGeneratePost(
      { projectId, assetType, assetId, requestBody: body },
    )
  return response.data ?? []
}

export async function uploadAssetCandidate(
  projectId: string,
  assetType: WorkbenchAssetType,
  assetId: string,
  file: File,
  viewAngle = 'front',
  versionId?: string | null,
): Promise<AssetProfileRead> {
  const response =
    await StudioAssetProfilesService.uploadAssetCandidateApiApiV1StudioProjectsProjectIdAssetsAssetTypeAssetIdCandidatesUploadPost(
      {
        projectId,
        assetType,
        assetId,
        viewAngle,
        versionId: versionId || undefined,
        formData: { file: file as unknown as string },
      },
    )
  if (!response.data) throw new Error('服务端没有返回上传结果')
  return response.data
}

export async function adoptAssetCandidate(
  projectId: string,
  assetType: WorkbenchAssetType,
  assetId: string,
  candidateId: number,
  versionId?: string | null,
): Promise<AssetProfileRead> {
  const response =
    await StudioAssetProfilesService.adoptAssetCandidateApiApiV1StudioProjectsProjectIdAssetsAssetTypeAssetIdCandidatesCandidateIdAdoptPost(
      {
        projectId,
        assetType,
        assetId,
        candidateId,
        requestBody: { version_id: versionId || null, make_primary: true },
      },
    )
  if (!response.data) throw new Error('服务端没有返回采纳结果')
  return response.data
}

export async function deleteAssetCandidate(
  projectId: string,
  assetType: WorkbenchAssetType,
  assetId: string,
  candidateId: number,
): Promise<AssetProfileRead> {
  const response =
    await StudioAssetProfilesService.deleteAssetCandidateApiApiV1StudioProjectsProjectIdAssetsAssetTypeAssetIdCandidatesCandidateIdDelete(
      { projectId, assetType, assetId, candidateId },
    )
  if (!response.data) throw new Error('服务端没有返回删除结果')
  return response.data
}

export async function lockCharacterIdentity(
  projectId: string,
  characterId: string,
  expectedLockVersion?: number,
): Promise<AssetProfileRead> {
  const response =
    await StudioAssetProfilesService.lockCharacterIdentityApiApiV1StudioProjectsProjectIdAssetsCharacterAssetIdLockPost(
      {
        projectId,
        assetId: characterId,
        requestBody: { expected_lock_version: expectedLockVersion ?? null },
      },
    )
  if (!response.data) throw new Error('服务端没有返回锁定结果')
  return response.data
}

export async function loadCharacterVoice(
  projectId: string,
  characterId: string,
): Promise<VoiceBindingRead> {
  const response =
    await StudioAssetProfilesService.getCharacterVoiceApiApiV1StudioProjectsProjectIdAssetsCharacterAssetIdVoiceGet(
      { projectId, assetId: characterId },
    )
  if (!response.data) throw new Error('服务端没有返回音色信息')
  return response.data
}

export async function updateCharacterVoice(
  projectId: string,
  characterId: string,
  body: VoiceBindingUpdate,
): Promise<VoiceBindingRead> {
  const response =
    await StudioAssetProfilesService.updateCharacterVoiceApiApiV1StudioProjectsProjectIdAssetsCharacterAssetIdVoicePatch(
      { projectId, assetId: characterId, requestBody: body },
    )
  if (!response.data) throw new Error('服务端没有返回音色更新结果')
  return response.data
}

export async function loadAvailableVoices(modelId?: string | null): Promise<VoiceItem[]> {
  const response = await StudioAudioTasksService.listAudioVoicesApiV1StudioAudioTasksVoicesGet({
    modelId: modelId || undefined,
    kind: 'preset',
  })
  return response.data ?? []
}

export async function loadShot(shotId: string): Promise<ShotRead> {
  const response = await StudioShotsService.getShotApiV1StudioShotsShotIdGet({ shotId })
  if (!response.data) throw new Error('服务端没有返回镜头数据')
  return response.data
}

export async function loadShotDetail(shotId: string): Promise<ShotDetailRead> {
  const response = await StudioShotDetailsService.getShotDetailApiV1StudioShotDetailsShotIdGet({
    shotId,
  })
  if (!response.data) throw new Error('服务端没有返回镜头细节')
  return response.data
}

export async function loadShotPreparation(shotId: string): Promise<ShotPreparationStateRead> {
  const response =
    await StudioShotsService.getShotPreparationStateApiApiV1StudioShotsShotIdPreparationStateGet({
      shotId,
    })
  if (!response.data) throw new Error('服务端没有返回镜头准备状态')
  return response.data
}

/**
 * 视频生成准备度。
 *
 * 固定查询 `reference` 模式：这是 H3 多参考的默认生产方式；
 * 准备度只读，切换参考模式属于生成工作室的职责，不在骨架阶段做。
 */
export async function loadShotReadiness(shotId: string): Promise<ShotVideoReadinessRead> {
  const response =
    await StudioShotsService.getShotVideoReadinessApiApiV1StudioShotsShotIdVideoReadinessGet({
      shotId,
      referenceMode: 'reference',
    })
  if (!response.data) throw new Error('服务端没有返回视频准备度')
  return response.data
}

export async function loadProjectTimeline(projectId: string): Promise<ProjectTimelineRead> {
  const response =
    await StudioTimelineService.getProjectTimelineApiApiV1StudioTimelineProjectsProjectIdGet({
      projectId,
    })
  if (!response.data) throw new Error('服务端没有返回时间线数据')
  return response.data
}
