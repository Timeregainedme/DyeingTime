/**
 * 工作台底部任务栏。
 *
 * 与全局浮窗 `TaskCenter` 同源（都读 `useTaskUiStore` 的服务器任务），
 * 但在工作台里改成「常驻底部、可收起」的形态，避免浮窗遮住树与画布。
 *
 * 职责边界（AGENTS.md）：
 *   - 只展示通用任务信息：状态、进度、耗时、取消；
 *   - 不展示提示词、素材映射、业务上下文等重信息——这些留在对应业务面板。
 */
import { useMemo } from 'react'
import type { KeyboardEvent as ReactKeyboardEvent, PointerEvent as ReactPointerEvent } from 'react'
import { ChevronDown, ChevronUp, Loader2, XCircle } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { cn } from '../../lib/utils'
import {
  mergeTaskUiItems,
  useTaskUiStore,
  type TaskUiItem,
} from '../../pages/aiStudio/components/taskUiStore'

const MAX_VISIBLE_ROWS = 20

const STATUS_META: Record<
  string,
  { label: string; text: string; dot: string; active: boolean }
> = {
  pending: { label: '排队中', text: 'text-run-running', dot: 'bg-run-running', active: true },
  running: { label: '运行中', text: 'text-run-running', dot: 'bg-run-running', active: true },
  streaming: { label: '生成中', text: 'text-run-running', dot: 'bg-run-running', active: true },
  succeeded: { label: '成功', text: 'text-run-success', dot: 'bg-run-success', active: false },
  failed: { label: '失败', text: 'text-run-failed', dot: 'bg-run-failed', active: false },
  cancelled: { label: '已取消', text: 'text-muted-foreground', dot: 'bg-run-idle', active: false },
}

function statusMeta(status: string) {
  return STATUS_META[status] ?? STATUS_META.pending
}

function formatElapsed(task: TaskUiItem): string {
  if (task.elapsedMs && task.elapsedMs > 0) return `${Math.round(task.elapsedMs / 1000)}s`
  if (task.startedAtTs) return `${Math.max(0, Math.round(Date.now() / 1000 - task.startedAtTs))}s`
  return '—'
}

function TaskRow({ task }: { task: TaskUiItem }) {
  const meta = statusMeta(task.status)
  const cancelTask = useTaskUiStore((state) => state.cancelTask)
  const canCancel = meta.active && !task.cancelRequested

  return (
    <div className="flex items-center gap-2 border-b border-border/60 px-3 py-1.5 text-xs last:border-b-0">
      <span className={cn('h-1.5 w-1.5 shrink-0 rounded-full', meta.dot)} aria-hidden="true" />
      <span className="min-w-0 flex-1 truncate" title={task.title ?? undefined}>
        {task.title || '后台任务'}
      </span>
      <span className={cn('w-14 shrink-0 text-right', meta.text)}>
        {task.cancelRequested ? '取消中' : meta.label}
      </span>
      <span className="w-10 shrink-0 text-right tabular-nums text-muted-foreground">
        {Math.max(0, Math.min(100, Math.round(task.progress)))}%
      </span>
      <span className="w-12 shrink-0 text-right tabular-nums text-muted-foreground">
        {formatElapsed(task)}
      </span>
      <Button
        variant="ghost"
        size="icon"
        className="h-6 w-6 shrink-0 text-muted-foreground"
        aria-label={canCancel ? '取消任务' : '任务不可取消'}
        disabled={!canCancel}
        onClick={() => {
          if (!canCancel) return
          void cancelTask(task.taskId)
        }}
      >
        <XCircle className="h-3.5 w-3.5" />
      </Button>
    </div>
  )
}

export function WorkbenchTaskDock({
  open,
  height,
  onToggle,
  onResizePointerDown,
  onResizeKeyDown,
  resizing,
}: {
  open: boolean
  height: number
  onToggle: () => void
  onResizePointerDown: (event: ReactPointerEvent<HTMLElement>) => void
  onResizeKeyDown: (event: ReactKeyboardEvent<HTMLElement>) => void
  resizing: boolean
}) {
  const serverItems = useTaskUiStore((state) => state.serverItems)
  const optimisticItems = useTaskUiStore((state) => state.optimisticItems)

  const tasks = useMemo(
    () => mergeTaskUiItems(serverItems, optimisticItems),
    [serverItems, optimisticItems],
  )

  const { activeCount, ordered } = useMemo(() => {
    const sorted = [...tasks].sort((a, b) => {
      const aActive = statusMeta(a.status).active ? 0 : 1
      const bActive = statusMeta(b.status).active ? 0 : 1
      if (aActive !== bActive) return aActive - bActive
      return (b.startedAtTs ?? 0) - (a.startedAtTs ?? 0)
    })
    return {
      activeCount: tasks.filter((task) => statusMeta(task.status).active).length,
      ordered: sorted.slice(0, MAX_VISIBLE_ROWS),
    }
  }, [tasks])

  return (
    <section
      aria-label="任务中心"
      className={cn(
        'relative flex shrink-0 flex-col border-t border-border bg-card',
        resizing && 'select-none',
      )}
    >
      {/* 拖拽条独立于标题栏：标题栏还要承担点击收起，混在一起会误触。 */}
      {open ? (
        <div
          role="separator"
          aria-orientation="horizontal"
          aria-label="调整任务栏高度"
          tabIndex={0}
          onPointerDown={onResizePointerDown}
          onKeyDown={onResizeKeyDown}
          className={cn(
            'absolute inset-x-0 -top-1 z-10 h-2 cursor-row-resize',
            'hover:bg-primary/20 focus-visible:bg-primary/30 focus-visible:outline-none',
          )}
        />
      ) : null}

      <div className="flex h-9 items-center gap-2 px-3">
        <Button
          variant="ghost"
          size="sm"
          className="h-7 gap-1.5 px-2 text-xs"
          onClick={onToggle}
          aria-expanded={open}
        >
          {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronUp className="h-3.5 w-3.5" />}
          任务中心
          {activeCount > 0 ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-run-running/15 px-1.5 py-0.5 text-[10px] font-medium text-run-running">
              <Loader2 className="h-2.5 w-2.5 animate-spin" />
              {activeCount}
            </span>
          ) : (
            <span className="text-[10px] text-muted-foreground">{tasks.length} 条</span>
          )}
        </Button>
        <span className="ml-auto truncate text-[11px] text-muted-foreground">
          任务状态来自任务系统，与镜头信息确认状态、视频准备度相互独立
        </span>
      </div>

      {open ? (
        <div className="min-h-0 overflow-auto" style={{ height }}>
          {ordered.length === 0 ? (
            <p className="px-3 py-4 text-xs text-muted-foreground">
              当前没有活跃或近期任务。生成、提取等操作会在这里出现。
            </p>
          ) : (
            ordered.map((task) => <TaskRow key={task.taskId} task={task} />)
          )}
        </div>
      ) : null}
    </section>
  )
}
