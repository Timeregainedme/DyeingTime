/**
 * 工作台面板的加载 / 错误 / 空态。
 *
 * 统一抽出来，避免每个面板各写一套「转圈 + 文案 + 重试」：
 *   - 加载用骨架而不是整页 Spin，减少布局跳动；
 *   - 错误必须带重试入口，用户不需要刷新整页；
 *   - 空态区分「真的没有数据」和「功能尚未开放」。
 */
import type { ReactNode } from 'react'
import { AlertCircle, Inbox, RefreshCw } from 'lucide-react'
import { Button } from '../../../components/ui/button'
import { Skeleton } from '../../../components/ui/skeleton'

/** 面板加载态。lines 控制骨架行数，贴合不同面板的密度。 */
export function PanelLoading({ lines = 4, label = '加载中…' }: { lines?: number; label?: string }) {
  return (
    <div className="space-y-3" role="status" aria-label={label}>
      <Skeleton className="h-5 w-40" />
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton key={index} className={index % 2 === 0 ? 'h-4 w-full' : 'h-4 w-4/5'} />
      ))}
    </div>
  )
}

/** 面板错误态：保留原始错误文案，并提供局部重试。 */
export function PanelError({
  message,
  onRetry,
}: {
  message: string
  onRetry?: () => void
}) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-4">
      <div className="flex items-center gap-2 text-sm font-medium text-destructive">
        <AlertCircle className="h-4 w-4" />
        加载失败
      </div>
      <p className="text-sm text-muted-foreground">{message}</p>
      {onRetry ? (
        <Button size="sm" variant="outline" onClick={onRetry}>
          <RefreshCw className="h-3.5 w-3.5" />
          重试
        </Button>
      ) : null}
    </div>
  )
}

/** 空态：不假装有数据，也不给出无效按钮。 */
export function PanelEmpty({
  title,
  description,
  action,
}: {
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border py-12 text-center">
      <Inbox className="h-6 w-6 text-muted-foreground" />
      <p className="text-sm font-medium">{title}</p>
      {description ? <p className="max-w-md text-xs text-muted-foreground">{description}</p> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  )
}

/**
 * 阶段说明条。
 *
 * 用于「这一块能力要到 P2/P3/P5/P7 才提供」的诚实标注。
 * 用静态说明而不是禁用按钮：禁用的按钮仍会让人尝试点击。
 */
export function StageNote({ stage, children }: { stage: string; children: ReactNode }) {
  return (
    <p className="rounded-md border border-border bg-muted/40 px-3 py-2 text-xs leading-5 text-muted-foreground">
      <span className="mr-1.5 rounded bg-background px-1.5 py-0.5 font-medium text-foreground">
        {stage}
      </span>
      {children}
    </p>
  )
}
