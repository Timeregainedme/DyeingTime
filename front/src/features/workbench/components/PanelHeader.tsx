/**
 * 中央面板的统一标题区。
 *
 * 让所有节点面板保持同一套信息层级：标题 / 副标题 / 操作。
 * 操作区只放真实可用入口（跳旧版页面、刷新、返回），不放装饰性按钮。
 */
import type { ReactNode } from 'react'

export function PanelHeader({
  title,
  description,
  actions,
  badge,
}: {
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
  badge?: ReactNode
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border pb-3">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="truncate text-lg font-semibold leading-tight">{title}</h2>
          {badge}
        </div>
        {description ? (
          <p className="mt-1 text-xs leading-5 text-muted-foreground">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-1.5">{actions}</div> : null}
    </div>
  )
}

/** 外链按钮：统一在新标签页打开旧版页面，保留工作台当前 Tab 的节点状态。 */
export function LegacyLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="inline-flex h-8 items-center gap-1.5 rounded-md border border-input bg-background px-3 text-xs transition-colors hover:bg-accent"
      title="在新标签页打开旧版页面，工作台保持当前节点"
    >
      {children}
    </a>
  )
}
