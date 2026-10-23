/**
 * 项目总览面板（工作台默认节点）。
 *
 * 回答三个问题：项目现在到哪一步、还有多少工作量、下一步该点哪里。
 * 所有计数都来自真实接口：章节/镜头用后端聚合，资产用实体列表，
 * 拿不到时显示「—」而不是编造 0。
 */
import type { ReactNode } from 'react'
import {
  ArrowRight,
  BookOpen,
  Boxes,
  Clapperboard,
  ExternalLink,
  FolderCog,
  Images,
  Users,
} from 'lucide-react'
import type { ChapterRead, ProjectRead } from '../../../services/generated'
import { Button } from '../../../components/ui/button'
import { Card, CardContent } from '../../../components/ui/card'
import {
  WORKBENCH_ASSET_LABELS,
  workbenchAssetGroupPath,
  workbenchConfigPath,
  workbenchEpisodePath,
  workbenchExportPath,
  workbenchScriptPath,
  type WorkbenchAssetType,
} from '../routes'
import { deriveChapterStage, pickRecommendedChapter } from '../deriveStage'
import { LegacyLink, PanelHeader } from '../components/PanelHeader'
import { PanelError, PanelLoading } from '../components/PanelStates'

interface OverviewPanelProps {
  projectId: string
  project?: ProjectRead
  projectLoading: boolean
  projectError: unknown
  onRetryProject: () => void
  chapters: ChapterRead[]
  chaptersLoading: boolean
  assetCounts: Record<WorkbenchAssetType, number>
  assetsLoading: boolean
  onNavigate: (path: string) => void
}

function StatCard({
  label,
  value,
  icon,
  onClick,
}: {
  label: string
  value: number | string
  icon: ReactNode
  onClick?: () => void
}) {
  const content = (
    <Card className={onClick ? 'cursor-pointer transition-shadow hover:shadow-popover' : ''}>
      <CardContent className="flex items-center gap-3 p-4">
        <span className="flex h-9 w-9 items-center justify-center rounded-md bg-muted text-muted-foreground">
          {icon}
        </span>
        <div className="min-w-0">
          <p className="text-[11px] text-muted-foreground">{label}</p>
          <p className="text-lg font-semibold leading-tight">{value}</p>
        </div>
      </CardContent>
    </Card>
  )
  return onClick ? (
    <button type="button" className="text-left" onClick={onClick}>
      {content}
    </button>
  ) : (
    content
  )
}

/** 面向制作流程的入口条；状态只使用已有数据，不创建新的主状态机。 */
function WorkflowGuide({
  projectId,
  project,
  chapters,
  assetCounts,
  shotTotal,
  recommendedChapterId,
  onNavigate,
}: {
  projectId: string
  project: ProjectRead
  chapters: ChapterRead[]
  assetCounts: Record<WorkbenchAssetType, number>
  shotTotal: number
  recommendedChapterId?: string
  onNavigate: (path: string) => void
}) {
  const assetTotal = Object.values(assetCounts).reduce((sum, value) => sum + value, 0)
  const steps = [
    {
      key: 'config',
      label: '项目准备',
      status: project.default_video_model_id ? '已配置模型' : '待配置模型',
      hint: '模型、比例、分辨率与生成参数',
      to: workbenchConfigPath(projectId),
    },
    {
      key: 'script',
      label: '剧本确认',
      status: chapters.length ? '已建立剧集' : '未开始',
      hint: '上传、解析、人工审核',
      to: workbenchScriptPath(projectId),
    },
    {
      key: 'assets',
      label: '资产确认',
      status: assetTotal ? `${assetTotal} 项资产` : '未开始',
      hint: '角色身份、场景、道具、服装',
      to: workbenchAssetGroupPath(projectId, 'character'),
    },
    {
      key: 'shots',
      label: '分镜确认',
      status: shotTotal ? `${shotTotal} 个镜头` : '未开始',
      hint: '场次、镜头资产版本与准备度',
      to: recommendedChapterId
        ? workbenchEpisodePath(projectId, recommendedChapterId)
        : workbenchEpisodePath(projectId, chapters[0]?.id ?? ''),
    },
    {
      key: 'video',
      label: '视频生产',
      status: shotTotal ? '按镜头检查' : '未开始',
      hint: '参考图、H3、批量任务、抽卡采纳',
      to: recommendedChapterId
        ? workbenchEpisodePath(projectId, recommendedChapterId)
        : workbenchEpisodePath(projectId, chapters[0]?.id ?? ''),
    },
    {
      key: 'export',
      label: '导出',
      status: '随时可用',
      hint: '选择已采纳镜头，检查后下载 MP4 ZIP',
      to: workbenchExportPath(projectId),
    },
  ]
  return (
    <Card>
      <CardContent className="p-4">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-medium">制作流程</h3>
          <span className="text-[10px] text-muted-foreground">
            状态来自项目、剧集、资产与镜头数据；不会替代 shot.status / video-readiness
          </span>
        </div>
        <div className="grid gap-2 md:grid-cols-3 xl:grid-cols-6">
          {steps.map((step) => (
            <button
              key={step.key}
              type="button"
              onClick={() => step.to && onNavigate(step.to)}
              className="rounded-md border border-border bg-background p-2 text-left transition-colors hover:bg-accent"
            >
              <p className="text-[11px] font-medium">{step.label}</p>
              <p className="mt-1 text-[10px] text-muted-foreground">{step.status}</p>
              <p className="mt-0.5 line-clamp-2 text-[10px] text-muted-foreground/80">{step.hint}</p>
            </button>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

export function OverviewPanel({
  projectId,
  project,
  projectLoading,
  projectError,
  onRetryProject,
  chapters,
  chaptersLoading,
  assetCounts,
  assetsLoading,
  onNavigate,
}: OverviewPanelProps) {
  if (projectLoading) return <PanelLoading lines={6} label="加载项目总览" />
  if (projectError || !project) {
    return (
      <PanelError
        message={
          projectError instanceof Error ? projectError.message : '项目不存在或没有访问权限'
        }
        onRetry={onRetryProject}
      />
    )
  }

  const shotTotal = chapters.reduce(
    (sum, chapter) => sum + (chapter.shot_count ?? chapter.storyboard_count ?? 0),
    0,
  )
  const recommended = pickRecommendedChapter(chapters)
  const stage = recommended ? deriveChapterStage(recommended) : null

  return (
    <div className="space-y-5">
      <PanelHeader
        title={project.name}
        description={project.description || '暂无项目简介'}
        actions={
          <LegacyLink href={`/projects/${projectId}?tab=dashboard`}>
            <ExternalLink className="h-3.5 w-3.5" />
            旧版项目页
          </LegacyLink>
        }
        badge={
          <span className="rounded-full bg-secondary px-2 py-0.5 text-[11px] text-secondary-foreground">
            {project.style} · {project.visual_style}
          </span>
        }
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 2xl:grid-cols-6">
        <StatCard
          label="剧集"
          value={chaptersLoading ? '…' : chapters.length}
          icon={<Clapperboard className="h-4 w-4" />}
          onClick={() => {
            if (recommended) onNavigate(workbenchEpisodePath(projectId, recommended.id))
          }}
        />
        <StatCard
          label="镜头"
          value={chaptersLoading ? '…' : shotTotal}
          icon={<Images className="h-4 w-4" />}
        />
        <StatCard
          label="角色"
          value={assetsLoading ? '…' : assetCounts.character}
          icon={<Users className="h-4 w-4" />}
          onClick={() => onNavigate(workbenchAssetGroupPath(projectId, 'character'))}
        />
        <StatCard
          label="场景"
          value={assetsLoading ? '…' : assetCounts.scene}
          icon={<Boxes className="h-4 w-4" />}
          onClick={() => onNavigate(workbenchAssetGroupPath(projectId, 'scene'))}
        />
        <StatCard
          label="道具"
          value={assetsLoading ? '…' : assetCounts.prop}
          icon={<Boxes className="h-4 w-4" />}
          onClick={() => onNavigate(workbenchAssetGroupPath(projectId, 'prop'))}
        />
        <StatCard
          label="服装"
          value={assetsLoading ? '…' : assetCounts.costume}
          icon={<Boxes className="h-4 w-4" />}
          onClick={() => onNavigate(workbenchAssetGroupPath(projectId, 'costume'))}
        />
      </div>

      <WorkflowGuide
        projectId={projectId}
        project={project}
        chapters={chapters}
        assetCounts={assetCounts}
        shotTotal={shotTotal}
        recommendedChapterId={recommended?.id}
        onNavigate={onNavigate}
      />

      <div className="grid gap-3 lg:grid-cols-2">
        <Card>
          <CardContent className="space-y-3 p-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium">制作进度</h3>
              <span className="text-xs text-muted-foreground">{project.progress ?? 0}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-[width]"
                style={{ width: `${Math.min(100, Math.max(0, project.progress ?? 0))}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              进度来自项目记录；具体阻塞项以每集与每个镜头的状态为准。
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-2 p-4">
            <h3 className="text-sm font-medium">下一步建议</h3>
            {chaptersLoading ? (
              <p className="text-xs text-muted-foreground">正在读取剧集…</p>
            ) : recommended && stage ? (
              <>
                <p className="text-xs text-muted-foreground">
                  第 {recommended.index} 集 · {stage.label}
                </p>
                <p className="text-xs">{stage.hint}</p>
                <Button
                  size="sm"
                  onClick={() => onNavigate(workbenchEpisodePath(projectId, recommended.id))}
                >
                  打开第 {recommended.index} 集
                  <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </>
            ) : (
              <>
                <p className="text-xs text-muted-foreground">
                  项目还没有剧集。创建与录入原文仍在旧版项目页完成。
                </p>
                <LegacyLink href={`/projects/${projectId}?tab=chapters&create=1`}>
                  <ExternalLink className="h-3.5 w-3.5" />
                  去旧版创建剧集
                </LegacyLink>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="p-4">
          <h3 className="mb-2 text-sm font-medium">工作台入口</h3>
          <div className="flex flex-wrap gap-1.5">
            <Button variant="outline" size="sm" onClick={() => onNavigate(workbenchConfigPath(projectId))}>
              <FolderCog className="h-3.5 w-3.5" />
              项目配置
            </Button>
            <Button variant="outline" size="sm" onClick={() => onNavigate(workbenchScriptPath(projectId))}>
              <BookOpen className="h-3.5 w-3.5" />
              世界观与剧本
            </Button>
            {(Object.keys(WORKBENCH_ASSET_LABELS) as WorkbenchAssetType[]).map((type) => (
              <Button
                key={type}
                variant="outline"
                size="sm"
                onClick={() => onNavigate(workbenchAssetGroupPath(projectId, type))}
              >
                <Boxes className="h-3.5 w-3.5" />
                全局资产 · {WORKBENCH_ASSET_LABELS[type]}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
