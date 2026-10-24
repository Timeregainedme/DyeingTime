import { ArrowRight, FolderTree, MoreHorizontal, Pencil, Trash2 } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Card } from '../../components/ui/card'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../../components/ui/dropdown-menu'
import { cn } from '../../lib/utils'
import { formatDateTime, getStagePresentation } from './format'
import type { ProjectSummary } from './useProjectDashboard'
import type { ProjectView } from './types'

interface ProjectCardProps {
  project: ProjectView
  summary?: ProjectSummary
  /** 摘要是否仍在加载，用于把「下一步」区域显示成占位而不是「待推进」。 */
  summaryLoading?: boolean
  /** 只读成员不显示编辑/删除（后端仍会拒绝，前端只做可见性收敛）。 */
  canEdit?: boolean
  onOpen: () => void
  onOpenWorkbench: () => void
  onEdit: () => void
  onDelete: () => void
}

/**
 * 项目卡片（工作台版）。
 *
 * 与旧版差异：
 * - 主操作只保留一个「下一步」，其余操作收进右侧更多菜单，避免一排同级按钮；
 * - 信息密度提高（阶段、镜头流量、更新时间同屏），减少空白；
 * - 待确认/已就绪/待审核三个数字直接来自 dashboard 聚合，不再单独发请求。
 */
export function ProjectCard({
  project,
  summary,
  summaryLoading = false,
  canEdit = true,
  onOpen,
  onOpenWorkbench,
  onEdit,
  onDelete,
}: ProjectCardProps) {
  const stage = getStagePresentation(summary?.stageKey)
  const actionLabel = summary?.actionLabel ?? '进入项目'
  const flow = summary?.flow
  const total = flow?.totalShots ?? project.stats.chapters
  const ready = flow?.readyShots ?? 0
  const pending = flow?.pendingConfirmShots ?? 0
  const ratio = total > 0 ? Math.round((ready / total) * 100) : 0

  return (
    <Card
      className="group flex h-full cursor-pointer flex-col p-4 transition-shadow hover:shadow-popover"
      onClick={onOpen}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-[11px] uppercase tracking-wide text-muted-foreground">
            {project.visualStyle} · {project.style || '未设定风格'}
          </p>
          <h3 className="mt-1 truncate text-sm font-semibold leading-tight">{project.name}</h3>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <span
            className={cn(
              'rounded-full px-2 py-0.5 text-[11px] font-medium',
              stage.tone === 'ready'
                ? 'bg-state-ready/15 text-state-ready'
                : 'bg-state-pending/15 text-state-pending',
            )}
          >
            {stage.label}
          </span>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-muted-foreground"
                aria-label="更多项目操作"
                onClick={(event) => event.stopPropagation()}
              >
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" onClick={(event) => event.stopPropagation()}>
              <DropdownMenuItem onSelect={onOpenWorkbench}>
                <FolderTree className="mr-2 h-3.5 w-3.5" />
                打开树状工作台
              </DropdownMenuItem>
              {canEdit ? (
                <>
                  <DropdownMenuItem onSelect={onEdit}>
                    <Pencil className="mr-2 h-3.5 w-3.5" />
                    编辑项目
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onSelect={onDelete}
                    className="text-destructive focus:text-destructive"
                  >
                    <Trash2 className="mr-2 h-3.5 w-3.5" />
                    删除项目
                  </DropdownMenuItem>
                </>
              ) : null}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <p className="mt-2 line-clamp-2 min-h-[2.25rem] text-xs leading-[1.125rem] text-muted-foreground">
        {project.description || '暂无简介'}
      </p>

      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
        <span className="inline-flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-state-pending" />
          待确认 {pending}
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-state-ready" />
          已就绪 {ready}
        </span>
        <span className="truncate">{summary?.chapterCount ?? project.stats.chapters} 章</span>
      </div>

      <div className="mt-2 space-y-1">
        <div className="flex items-center justify-between text-[11px] text-muted-foreground">
          <span>镜头就绪</span>
          <span className="tabular-nums">
            {ready}/{total}
          </span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-[width]"
            style={{ width: `${ratio}%` }}
          />
        </div>
      </div>

      <div className="mt-auto flex items-center justify-between gap-2 border-t border-border pt-3">
        <span className="truncate text-[11px] text-muted-foreground">
          {summaryLoading ? '正在分析…' : formatDateTime(project.updatedAt)}
        </span>
        <Button
          size="sm"
          className="h-7 px-2.5 text-xs"
          onClick={(event) => {
            event.stopPropagation()
            onOpen()
          }}
        >
          {actionLabel}
          <ArrowRight className="h-3.5 w-3.5" />
        </Button>
      </div>
    </Card>
  )
}
