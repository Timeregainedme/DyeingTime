import {
  ArrowRight,
  CheckCircle2,
  Clapperboard,
  Clock3,
  Film,
  FolderKanban,
  ListChecks,
  Loader2,
  ShieldAlert,
  Sparkles,
} from 'lucide-react'
import { Badge } from '../../../components/ui/badge'
import { Button } from '../../../components/ui/button'
import { Card } from '../../../components/ui/card'
import { cn } from '../../../lib/utils'
import { resolveTaskTitle } from '../../../pages/aiStudio/components/taskCopy'
import { formatDateTime, getStagePresentation } from '../format'
import type { ProjectSummary } from '../useProjectDashboard'
import type {
  DashboardProjectRead,
  DashboardReviewRead,
  DashboardStatsRead,
  DashboardTaskRead,
} from '../../../services/generated'

/** 任务状态 → 中文文案与色板。与任务中心使用同一套状态语义。 */
const TASK_STATUS_META: Record<
  string,
  { label: string; tone: string; icon: typeof Clock3 }
> = {
  pending: { label: '等待执行', tone: 'text-state-pending', icon: Clock3 },
  running: { label: '生成中', tone: 'text-run-running', icon: Loader2 },
  streaming: { label: '生成中', tone: 'text-run-running', icon: Loader2 },
  succeeded: { label: '已完成', tone: 'text-state-ready', icon: CheckCircle2 },
  failed: { label: '失败', tone: 'text-destructive', icon: ShieldAlert },
  cancelled: { label: '已取消', tone: 'text-muted-foreground', icon: Clock3 },
}

/** 统计卡片：四个数字全部来自 `/studio/dashboard`，不使用任何前端估算。 */
export function DashboardStats({ stats }: { stats: DashboardStatsRead }) {
  const items = [
    {
      key: 'projects',
      label: '项目总数',
      value: stats.project_count,
      hint: '当前工作区可访问的短剧项目',
      icon: FolderKanban,
      tone: 'bg-primary/10 text-primary',
    },
    {
      key: 'review',
      label: '待审核镜头',
      value: stats.pending_review_shots,
      hint: '已有成功视频、尚未人工确认的镜头',
      icon: ListChecks,
      tone: 'bg-state-pending/10 text-state-pending',
    },
    {
      key: 'running',
      label: '正在生成任务',
      value: stats.running_tasks,
      hint: '等待执行 + 运行中的后台任务',
      icon: Loader2,
      tone: 'bg-run-running/10 text-run-running',
    },
    {
      key: 'adopted',
      label: '已采纳视频',
      value: stats.adopted_videos,
      hint: '镜头已完成人工采纳的视频数',
      icon: Clapperboard,
      tone: 'bg-state-ready/10 text-state-ready',
    },
  ]

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {items.map((item) => (
        <Card key={item.key} className="p-4">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="text-xs text-muted-foreground">{item.label}</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums tracking-tight">{item.value}</p>
            </div>
            <span className={cn('flex h-9 w-9 shrink-0 items-center justify-center rounded-lg', item.tone)}>
              <item.icon className="h-4 w-4" />
            </span>
          </div>
          <p className="mt-2 line-clamp-2 text-[11px] leading-4 text-muted-foreground">{item.hint}</p>
        </Card>
      ))}
    </div>
  )
}

/** 「继续创作」卡片：只展示最近更新的项目，主按钮直接进入下一步业务页面。 */
export function ContinueCreating({
  projects,
  summaries,
  onOpen,
}: {
  projects: DashboardProjectRead[]
  summaries: Record<string, ProjectSummary>
  onOpen: (project: DashboardProjectRead) => void
}) {
  const recent = projects.slice(0, 3)
  if (!recent.length) return null

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-semibold">
            <Sparkles className="h-4 w-4 text-primary" />
            继续创作
          </h2>
          <p className="mt-0.5 text-xs text-muted-foreground">按最近编辑排序，直接回到下一步</p>
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {recent.map((project) => {
          const summary = summaries[project.id]
          const stage = getStagePresentation(summary?.stageKey)
          const total = summary?.flow?.totalShots ?? project.total_shots
          const ready = summary?.flow?.readyShots ?? project.ready_shots
          const ratio = total > 0 ? Math.round((ready / total) * 100) : 0
          return (
            <Card
              key={project.id}
              className="flex cursor-pointer flex-col gap-3 p-4 transition-shadow hover:shadow-popover"
              onClick={() => onOpen(project)}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-[11px] text-muted-foreground">
                    {project.visual_style} · {project.style || '未设定风格'}
                  </p>
                  <h3 className="mt-0.5 truncate text-sm font-semibold">{project.name}</h3>
                </div>
                <Badge
                  variant="outline"
                  className={cn(
                    'shrink-0',
                    stage.tone === 'ready'
                      ? 'border-state-ready/40 text-state-ready'
                      : 'border-state-pending/40 text-state-pending',
                  )}
                >
                  {stage.label}
                </Badge>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                  <span>镜头就绪</span>
                  <span className="tabular-nums">
                    {ready}/{total}
                  </span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                  <div className="h-full rounded-full bg-primary" style={{ width: `${ratio}%` }} />
                </div>
                <p className="truncate text-[11px] text-muted-foreground">
                  {summary?.hint ?? '进入项目工作台继续推进'}
                </p>
              </div>

              <div className="mt-auto flex items-center justify-between gap-2 border-t border-border pt-2.5">
                <span className="text-[11px] text-muted-foreground">
                  {project.updated_at ? formatDateTime(project.updated_at) : '—'}
                </span>
                <Button size="sm" variant="ghost" className="h-7 px-2 text-xs">
                  {summary?.actionLabel ?? '进入项目'}
                  <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </div>
            </Card>
          )
        })}
      </div>
    </section>
  )
}

const REVIEW_META: Record<DashboardReviewRead['kind'], { icon: typeof Film; tone: string }> = {
  video_candidate: { icon: Film, tone: 'text-run-running' },
  shot_plan: { icon: ListChecks, tone: 'text-state-pending' },
  shot_extraction: { icon: ShieldAlert, tone: 'text-state-pending' },
}

/** 待审核事项：每一条都必须能落到具体项目的真实页面。 */
export function PendingReviews({
  reviews,
  onOpen,
}: {
  reviews: DashboardReviewRead[]
  onOpen: (review: DashboardReviewRead) => void
}) {
  return (
    <Card className="flex flex-col p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">待审核事项</h2>
        <Badge variant="outline">{reviews.length}</Badge>
      </div>
      {reviews.length === 0 ? (
        <p className="mt-3 rounded-md bg-muted/50 px-3 py-4 text-center text-xs text-muted-foreground">
          当前没有需要人工确认的内容
        </p>
      ) : (
        <ul className="mt-2 list-none divide-y divide-border p-0">
          {reviews.map((review, index) => {
            const meta = REVIEW_META[review.kind]
            return (
              <li key={`${review.kind}-${review.project_id}-${index}`}>
                <button
                  type="button"
                  onClick={() => onOpen(review)}
                  className="flex w-full items-center gap-2.5 py-2.5 text-left transition-colors hover:text-primary"
                >
                  <meta.icon className={cn('h-4 w-4 shrink-0', meta.tone)} />
                  <span className="min-w-0 flex-1 truncate text-xs">{review.label}</span>
                  <span className="shrink-0 rounded-full bg-muted px-1.5 py-0.5 text-[10px] tabular-nums text-muted-foreground">
                    {review.count}
                  </span>
                  <ArrowRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </Card>
  )
}

/** 最近任务：复用任务中心的状态语义，点击打开真实任务中心浮层。 */
export function RecentTasks({
  tasks,
  onOpenTaskCenter,
}: {
  tasks: DashboardTaskRead[]
  onOpenTaskCenter: () => void
}) {
  return (
    <Card className="flex flex-col p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">最近任务</h2>
        <Button variant="ghost" size="sm" className="h-6 px-2 text-[11px]" onClick={onOpenTaskCenter}>
          任务中心
          <ArrowRight className="h-3 w-3" />
        </Button>
      </div>
      {tasks.length === 0 ? (
        <p className="mt-3 rounded-md bg-muted/50 px-3 py-4 text-center text-xs text-muted-foreground">
          还没有生成任务
        </p>
      ) : (
        <ul className="mt-2 list-none divide-y divide-border p-0">
          {tasks.slice(0, 6).map((task) => {
            const meta = TASK_STATUS_META[task.status] ?? TASK_STATUS_META.pending
            const Icon = meta.icon
            return (
              <li key={task.id}>
                <button
                  type="button"
                  onClick={onOpenTaskCenter}
                  className="flex w-full items-center gap-2.5 py-2.5 text-left transition-colors hover:text-primary"
                >
                  <Icon
                    className={cn(
                      'h-3.5 w-3.5 shrink-0',
                      meta.tone,
                      (task.status === 'running' || task.status === 'streaming') && 'animate-spin',
                    )}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-xs">{resolveTaskTitle(task.task_kind)}</span>
                    <span className="block truncate text-[10px] text-muted-foreground">
                      {task.project_name ?? '未关联项目'} · {meta.label}
                    </span>
                  </span>
                  <span className="shrink-0 text-[10px] tabular-nums text-muted-foreground">
                    {task.progress}%
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </Card>
  )
}
