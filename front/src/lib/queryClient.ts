import { QueryClient } from '@tanstack/react-query'

/**
 * 全局 QueryClient。
 *
 * 默认值按「长任务工作台」的场景调过，而不是照抄文档默认值：
 *   - retry: 1 —— 生成类接口失败通常是真的失败，重试两次只会拖慢错误反馈；
 *   - refetchOnWindowFocus: false —— 用户切窗口去剪片时不该触发大批请求；
 *   - staleTime: 30s —— 项目/章节列表这类数据在 30s 内重复进入不必重拉。
 * 需要更激进刷新的查询（如任务进度）在各自的 hook 里单独覆盖。
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
      gcTime: 5 * 60_000,
    },
    mutations: {
      retry: 0,
    },
  },
})

/**
 * 统一 query key 的构造出口。
 *
 * 把 key 收敛到一处，避免不同页面写成 ['shots'] 和 ['shot-list'] 各查一份缓存，
 * 也方便后续做「某个项目下所有查询一起失效」这类批量操作。
 */
export const queryKeys = {
  projects: ['projects'] as const,
  project: (projectId: string) => ['project', projectId] as const,
  chapters: (projectId: string) => ['chapters', projectId] as const,
  chapter: (projectId: string, chapterId: string) => ['chapter', projectId, chapterId] as const,
  shots: (chapterId: string) => ['shots', chapterId] as const,
  shot: (shotId: string) => ['shot', shotId] as const,
  tasks: ['tasks'] as const,

  /**
   * 树状工作台的查询键。
   *
   * 统一挂在 `['workbench', projectId, ...]` 下：
   * 切项目时旧数据自然隔离，也让「刷新整个工作台」可以按前缀失效。
   */
  workbenchProject: (projectId: string) => ['workbench', projectId, 'project'] as const,
  workbenchChapters: (projectId: string) => ['workbench', projectId, 'chapters'] as const,
  workbenchShots: (projectId: string, chapterId: string) =>
    ['workbench', projectId, 'shots', chapterId] as const,
  workbenchSceneGroups: (projectId: string, chapterId: string) =>
    ['workbench', projectId, 'scene-groups', chapterId] as const,
  workbenchSceneGroupSuggestions: (projectId: string, chapterId: string) =>
    ['workbench', projectId, 'scene-group-suggestions', chapterId] as const,
  workbenchSceneGroup: (projectId: string, groupId: string) =>
    ['workbench', projectId, 'scene-group', groupId] as const,
  workbenchSceneGroupShots: (projectId: string, groupId: string) =>
    ['workbench', projectId, 'scene-group-shots', groupId] as const,
  workbenchShotPlans: (projectId: string, chapterId: string) =>
    ['workbench', projectId, 'shot-plans', chapterId] as const,
  workbenchShotPlan: (projectId: string, draftId: string) =>
    ['workbench', projectId, 'shot-plan', draftId] as const,
  workbenchShotPlanStats: (projectId: string, chapterId: string) =>
    ['workbench', projectId, 'shot-plan-stats', chapterId] as const,
  workbenchShotAssetVersions: (projectId: string, shotId: string) =>
    ['workbench', projectId, 'shot-asset-versions', shotId] as const,
  workbenchReferenceBindings: (projectId: string, shotId: string) =>
    ['workbench', projectId, 'reference-bindings', shotId] as const,
  workbenchP6Readiness: (projectId: string, shotId: string) =>
    ['workbench', projectId, 'p6-readiness', shotId] as const,
  workbenchGenerationSnapshots: (projectId: string, shotId: string) =>
    ['workbench', projectId, 'generation-snapshots', shotId] as const,
  generationQuota: (scope: string) => ['generation-quota', scope] as const,
  workbenchRuntime: (projectId: string, chapterId: string) =>
    ['workbench', projectId, 'runtime', chapterId] as const,
  workbenchAssets: (projectId: string, assetType: string) =>
    ['workbench', projectId, 'assets', assetType] as const,
  workbenchAsset: (projectId: string, assetType: string, assetId: string) =>
    ['workbench', projectId, 'asset', assetType, assetId] as const,
  workbenchAssetProfile: (projectId: string, assetType: string, assetId: string) =>
    ['workbench', projectId, 'asset-profile', assetType, assetId] as const,
  workbenchVoices: (modelId: string) =>
    ['workbench', 'audio-voices', modelId] as const,
  workbenchAssetImpact: (projectId: string, assetType: string, assetId: string) =>
    ['workbench', projectId, 'asset-impact', assetType, assetId] as const,
  workbenchShot: (projectId: string, shotId: string) =>
    ['workbench', projectId, 'shot', shotId] as const,
  workbenchShotDetail: (projectId: string, shotId: string) =>
    ['workbench', projectId, 'shot-detail', shotId] as const,
  workbenchShotPreparation: (projectId: string, shotId: string) =>
    ['workbench', projectId, 'shot-preparation', shotId] as const,
  workbenchShotReadiness: (projectId: string, shotId: string) =>
    ['workbench', projectId, 'shot-readiness', shotId] as const,
  workbenchTimeline: (projectId: string) => ['workbench', projectId, 'timeline'] as const,
  workbenchStyleOptions: ['workbench', 'style-options'] as const,
  workbenchStyleCatalog: ['workbench', 'style-catalog'] as const,
  workbenchGenerationOptions: (projectId: string) =>
    ['workbench', projectId, 'generation-options'] as const,
  workbenchGenerationConfig: (projectId: string) =>
    ['workbench', projectId, 'generation-config'] as const,
  workbenchProjectStyle: (projectId: string) =>
    ['workbench', projectId, 'project-style'] as const,
  workbenchStyleAnalysisCapability: ['workbench', 'style-analysis-capability'] as const,
  workbenchScriptDocuments: (projectId: string) =>
    ['workbench', projectId, 'script-documents'] as const,
  workbenchScriptDocument: (documentId: string) =>
    ['workbench', 'script-document', documentId] as const,
  workbenchScriptVersion: (documentId: string, versionId: string) =>
    ['workbench', 'script-version', documentId, versionId] as const,
  workbenchScriptParseRun: (runId: string) =>
    ['workbench', 'script-parse-run', runId] as const,
  workbenchScriptParseRuns: (documentId: string) =>
    ['workbench', 'script-parse-runs', documentId] as const,
}
