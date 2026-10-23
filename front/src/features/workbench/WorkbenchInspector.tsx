/**
 * 工作台右侧属性面板。
 *
 * 只做「当前对象的只读上下文」：基础字段、三类状态的真实取值、可用入口。
 * 所有状态都来自后端接口，不在前端推导新状态；属性面板也不承担编辑职责，
 * 编辑仍走既有页面（P1 的边界，编辑内嵌留给后续阶段）。
 */
import type { ReactNode } from 'react'
import { CheckCircle2, XCircle } from 'lucide-react'
import { Separator } from '../../components/ui/separator'
import type { ChapterRead, ProjectRead } from '../../services/generated'
import { cn } from '../../lib/utils'
import { WORKBENCH_ASSET_LABELS, type WorkbenchAssetType, type WorkbenchSelection } from './routes'
import {
  useWorkbenchAssetDetail,
  useWorkbenchRuntimeQueries,
  useWorkbenchSceneGroup,
  useWorkbenchShot,
  useWorkbenchShotDetail,
  useWorkbenchShotPreparation,
  useWorkbenchShotReadiness,
} from './useWorkbenchQueries'
import { PrepStatusBadge, ReadinessBadge, RunStatusBadge } from './components/StatusBadges'
import { PanelError, PanelLoading } from './components/PanelStates'

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? '是' : '否'
  if (Array.isArray(value)) return value.length ? value.join('、') : '—'
  if (typeof value === 'object') return '—'
  return String(value)
}

function Row({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="flex items-start justify-between gap-3 py-1 text-xs">
      <span className="shrink-0 text-muted-foreground">{label}</span>
      <span className="min-w-0 break-words text-right">{displayValue(value)}</span>
    </div>
  )
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-1">
      <h3 className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        {title}
      </h3>
      <div>{children}</div>
    </section>
  )
}

interface InspectorProps {
  projectId: string
  selection: WorkbenchSelection
  project?: ProjectRead
  chapters: ChapterRead[]
  assetCounts: Record<WorkbenchAssetType, number>
}

export function WorkbenchInspector({
  projectId,
  selection,
  project,
  chapters,
  assetCounts,
}: InspectorProps) {
  return (
    <aside className="flex h-full min-h-0 flex-col bg-card" aria-label="属性面板">
      <div className="flex h-9 shrink-0 items-center justify-between border-b border-border px-3">
        <span className="text-xs font-medium">属性</span>
        <span className="text-[10px] text-muted-foreground">只读</span>
      </div>
      <div className="min-h-0 flex-1 space-y-3 overflow-auto p-3">
        {selection.kind === 'shot' ? (
          <ShotInspector projectId={projectId} chapterId={selection.chapterId} shotId={selection.shotId} />
        ) : selection.kind === 'assets' ? (
          <AssetInspector
            projectId={projectId}
            assetType={selection.assetType}
            assetId={selection.assetId}
            assetCount={assetCounts[selection.assetType]}
          />
        ) : selection.kind === 'scene-group' ? (
          <SceneGroupInspector
            projectId={projectId}
            chapterId={selection.chapterId}
            sceneGroupId={selection.sceneGroupId}
          />
        ) : selection.kind === 'episode' ? (
          <EpisodeInspector chapter={chapters.find((item) => item.id === selection.chapterId)} />
        ) : (
          <ProjectInspector project={project} selection={selection} chapterCount={chapters.length} />
        )}
      </div>
    </aside>
  )
}

function ProjectInspector({
  project,
  selection,
  chapterCount,
}: {
  project?: ProjectRead
  selection: WorkbenchSelection
  chapterCount: number
}) {
  if (!project) return <PanelLoading lines={5} />
  return (
    <>
      <Section title="项目">
        <Row label="名称" value={project.name} />
        <Row label="题材" value={project.style} />
        <Row label="表现形式" value={project.visual_style} />
        <Row label="剧集数" value={chapterCount} />
        <Row label="进度" value={`${project.progress ?? 0}%`} />
      </Section>
      <Separator />
      <Section title="生成参数">
        <Row label="视频比例" value={project.default_video_ratio} />
        <Row label="图片比例" value={project.default_image_ratio} />
        <Row label="视频分辨率" value={project.default_video_resolution} />
        <Row label="图片档位" value={project.default_image_resolution_profile} />
        <Row label="台词音频参考" value={project.use_dialog_audio_as_reference} />
      </Section>
      <Separator />
      <Section title="当前节点">
        <Row label="类型" value={selection.kind === 'overview' ? '项目总览' : selection.kind} />
        <Row label="项目 ID" value={project.id} />
        <Row label="工作区" value={project.workspace_id} />
      </Section>
      <p className="text-[10px] leading-4 text-muted-foreground">
        项目配置在工作台「项目配置」面板编辑；属性栏保持只读，避免两处同时修改。
      </p>
    </>
  )
}

function EpisodeInspector({ chapter }: { chapter?: ChapterRead }) {
  if (!chapter) return <PanelLoading lines={4} />
  return (
    <>
      <Section title="剧集">
        <Row label="集数" value={`第 ${chapter.index} 集`} />
        <Row label="标题" value={chapter.title} />
        <Row label="状态" value={chapter.status} />
        <Row label="镜头数" value={chapter.shot_count ?? chapter.storyboard_count} />
        <Row label="章节 ID" value={chapter.id} />
      </Section>
      <Separator />
      <Section title="原文">
        <Row label="原文长度" value={`${(chapter.raw_text ?? '').length} 字`} />
        <Row label="摘要" value={chapter.summary} />
      </Section>
      <p className="text-[10px] leading-4 text-muted-foreground">
        场次（SceneGroup）是剧集内剧情分组，场景（Scene）是可复用资产；P5 已把两者分开。
      </p>
    </>
  )
}

function SceneGroupInspector({
  projectId,
  chapterId,
  sceneGroupId,
}: {
  projectId: string
  chapterId: string
  sceneGroupId: string
}) {
  const query = useWorkbenchSceneGroup(projectId, chapterId, sceneGroupId)
  if (query.isLoading) return <PanelLoading lines={4} />
  if (query.isError || !query.data) {
    return (
      <p className="text-xs text-destructive">
        场次读取失败：{query.error instanceof Error ? query.error.message : '不存在'}
      </p>
    )
  }
  const group = query.data
  return (
    <>
      <Section title="场次">
        <Row label="序号" value={`场次 ${String(group.index).padStart(2, '0')}`} />
        <Row label="标题" value={group.title} />
        <Row label="地点" value={group.location} />
        <Row label="时间" value={group.time_of_day} />
        <Row label="主场景" value={group.primary_scene_name ?? '未指定'} />
        <Row label="镜头数" value={group.shot_count ?? 0} />
        <Row label="预计时长" value={`${group.total_duration ?? 0}s`} />
      </Section>
      <Separator />
      <Section title="剧情">
        <Row label="关键事件" value={group.story_event} />
        <Row label="描述" value={group.description} />
      </Section>
    </>
  )
}

function ShotInspector({
  projectId,
  chapterId,
  shotId,
}: {
  projectId: string
  chapterId: string
  shotId: string
}) {
  const shotQuery = useWorkbenchShot(projectId, shotId)
  const detailQuery = useWorkbenchShotDetail(projectId, shotId)
  const preparationQuery = useWorkbenchShotPreparation(projectId, shotId)
  const readinessQuery = useWorkbenchShotReadiness(projectId, shotId)
  const runtimeQueries = useWorkbenchRuntimeQueries(projectId, [chapterId])
  const activeTasks =
    runtimeQueries[0]?.data?.find((item) => item.shot_id === shotId)?.active_task_count ?? 0

  if (shotQuery.isLoading) return <PanelLoading lines={6} />
  if (shotQuery.isError) {
    return (
      <PanelError
        message={shotQuery.error instanceof Error ? shotQuery.error.message : '镜头加载失败'}
        onRetry={() => void shotQuery.refetch()}
      />
    )
  }

  const shot = shotQuery.data
  const detail = detailQuery.data
  const preparation = preparationQuery.data
  const readiness = readinessQuery.data

  return (
    <>
      <Section title="镜头">
        <Row label="序号" value={shot ? `镜头 ${String(shot.index).padStart(2, '0')}` : '—'} />
        <Row label="标题" value={shot?.title} />
        <Row label="镜头 ID" value={shotId} />
      </Section>
      <Separator />
      <Section title="状态（三类独立）">
        <div className="flex flex-wrap items-center gap-1.5 py-1">
          <PrepStatusBadge status={shot?.status} />
          <RunStatusBadge activeTasks={activeTasks} />
          <ReadinessBadge ready={readiness?.ready} checks={readiness?.checks} />
        </div>
        <Row
          label="待确认项"
          value={preparation ? preparation.pending_confirm_count : '—'}
        />
        <Row
          label="可进入生成"
          value={preparation ? (preparation.ready_for_generation ? '是' : '否') : '—'}
        />
        <p className="pt-1 text-[10px] leading-4 text-muted-foreground">
          信息确认、任务运行、视频准备度是三套独立语义，不能互相替代。
        </p>
      </Section>
      <Separator />
      <Section title="视频准备度明细">
        {readinessQuery.isLoading ? (
          <PanelLoading lines={3} />
        ) : readinessQuery.isError ? (
          <p className="text-xs text-destructive">准备度读取失败，可在中央面板重试。</p>
        ) : readiness?.checks?.length ? (
          <ul className="space-y-1">
            {readiness.checks.map((check) => (
              <li key={check.key} className="flex items-start gap-1.5 text-[11px] leading-4">
                {check.ok ? (
                  <CheckCircle2 className="mt-0.5 h-3 w-3 shrink-0 text-ready-complete" />
                ) : (
                  <XCircle className="mt-0.5 h-3 w-3 shrink-0 text-ready-blocked" />
                )}
                <span className={cn(!check.ok && 'text-muted-foreground')}>{check.message}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-muted-foreground">暂无检查结果。</p>
        )}
      </Section>
      <Separator />
      <Section title="镜头语言">
        <Row label="时长" value={detail ? `${detail.duration ?? 0}s` : '—'} />
        <Row label="景别" value={detail?.camera_shot} />
        <Row label="机位" value={detail?.angle} />
        <Row label="运镜" value={detail?.movement} />
        <Row label="动作拍点" value={detail?.action_beats?.length ?? 0} />
      </Section>
    </>
  )
}

function AssetInspector({
  projectId,
  assetType,
  assetId,
  assetCount,
}: {
  projectId: string
  assetType: WorkbenchAssetType
  assetId?: string
  assetCount: number
}) {
  const query = useWorkbenchAssetDetail(projectId, assetType, assetId)

  if (!assetId) {
    return (
      <>
        <Section title={WORKBENCH_ASSET_LABELS[assetType]}>
          <Row label="类型" value={WORKBENCH_ASSET_LABELS[assetType]} />
          <Row label="数量" value={assetCount} />
        </Section>
        <p className="text-[10px] leading-4 text-muted-foreground">
          选择具体资产后显示基础字段。角色是项目内资产，场景 / 道具 / 服装是工作区级全局资产。
        </p>
      </>
    )
  }

  if (query.isLoading) return <PanelLoading lines={5} />
  if (query.isError) {
    return (
      <PanelError
        message={query.error instanceof Error ? query.error.message : '资产加载失败'}
        onRetry={() => void query.refetch()}
      />
    )
  }

  const data = query.data ?? {}
  return (
    <>
      <Section title={WORKBENCH_ASSET_LABELS[assetType]}>
        <Row label="名称" value={data.name} />
        <Row label="题材" value={data.style} />
        <Row label="表现形式" value={data.visual_style} />
        <Row label="描述" value={data.description} />
        <Row label="资产 ID" value={assetId} />
      </Section>
      <Separator />
      <p className="text-[10px] leading-4 text-muted-foreground">
        资产详情支持候选图、身份锁定、造型/衍生版本和影响分析；旧版编辑页仍保留。
      </p>
    </>
  )
}
