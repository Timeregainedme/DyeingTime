/**
 * 工作台状态徽标。
 *
 * 三类状态必须使用三组颜色 token，禁止互相借用：
 *   - state-*  → `shot.status`（信息提取确认）
 *   - run-*    → GenerationTask / runtime summary（任务运行）
 *   - ready-*  → video-readiness（视频生成准备度）
 *
 * 组件只接收已经归一化好的数据，不自己推导业务状态；
 * 状态语义变化必须回到后端与服务层处理，前端不造新状态机。
 */
import { Badge } from '../../../components/ui/badge'
import { cn } from '../../../lib/utils'
import type { ShotStatus } from '../../../services/generated'

/** 信息确认状态：只有 pending / ready 两种业务含义。 */
export function PrepStatusBadge({ status }: { status?: ShotStatus }) {
  const ready = status === 'ready'
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium',
        ready ? 'bg-state-ready/15 text-state-ready' : 'bg-state-pending/15 text-state-pending',
      )}
      title={
        ready
          ? '信息提取确认完成（shot.status = ready）'
          : '仍有提取确认工作未完成（shot.status = pending）'
      }
    >
      <span
        className={cn('h-1.5 w-1.5 rounded-full', ready ? 'bg-state-ready' : 'bg-state-pending')}
      />
      {ready ? '已确认' : '待确认'}
    </span>
  )
}

/** 运行时任务：只表达「有任务在跑」，不写回 shot.status。 */
export function RunStatusBadge({ activeTasks }: { activeTasks?: number }) {
  if (!activeTasks) return null
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full bg-run-running/15 px-2 py-0.5 text-[11px] font-medium text-run-running"
      title="该镜头当前有进行中的生成任务（来自任务系统，不代表 shot.status）"
    >
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-run-running" />
      运行中 {activeTasks}
    </span>
  )
}

/**
 * 视频生成准备度。
 *
 * 依据视频准备度接口的逐项检查结果分三档：
 * 全部通过 → complete；全部不通过 → blocked；部分通过 → partial。
 * 不把 readiness 折算成 `shot.status`。
 */
export function ReadinessBadge({
  ready,
  checks,
}: {
  ready?: boolean
  checks?: Array<{ ok: boolean }>
}) {
  const total = checks?.length ?? 0
  const failed = checks?.filter((check) => !check.ok).length ?? 0
  const complete = ready === true
  const blocked = ready === false && total > 0 && failed === total
  const label = complete ? '可生成' : blocked ? '未就绪' : '部分就绪'
  const tone = complete
    ? 'bg-ready-complete/15 text-ready-complete'
    : blocked
      ? 'bg-ready-blocked/15 text-ready-blocked'
      : 'bg-ready-partial/15 text-ready-partial'
  const dot = complete ? 'bg-ready-complete' : blocked ? 'bg-ready-blocked' : 'bg-ready-partial'

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium',
        tone,
      )}
      title={
        complete
          ? '按当前参考模式，已具备视频生成条件'
          : `视频生成准备度：${failed}/${total} 项未通过`
      }
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', dot)} />
      {label}
    </span>
  )
}

/** 章节状态（draft / shooting / done）。它是章节流程状态，不是 shot.status。 */
export function ChapterStatusBadge({ status }: { status?: string }) {
  const label = status === 'done' ? '已完成' : status === 'shooting' ? '拍摄中' : '草稿'
  return (
    <Badge variant="outline" className="font-normal">
      {label}
    </Badge>
  )
}

/** 树节点上的小圆点：按组取色，绝不跨组。 */
export function StatusDot({
  group,
  active = false,
  title,
}: {
  group: 'state' | 'run' | 'ready'
  active?: boolean
  title?: string
}) {
  if (!active) return null
  const className =
    group === 'state'
      ? 'bg-state-pending'
      : group === 'run'
        ? 'bg-run-running'
        : 'bg-ready-partial'
  return (
    <span
      title={title}
      className={cn('h-1.5 w-1.5 shrink-0 rounded-full', className)}
      aria-hidden="true"
    />
  )
}
