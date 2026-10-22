/**
 * 只读信息网格。
 *
 * 工作台在 P1 只展示真实字段，不提供内嵌编辑；统一网格避免每个面板
 * 各写一套 label/value 间距，也保证窄屏自动回落成单列。
 */
import type { ReactNode } from 'react'

export interface InfoItem {
  label: string
  value: ReactNode
}

export function InfoGrid({ items }: { items: InfoItem[] }) {
  return (
    <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-2">
      {items.map((item) => (
        <div key={item.label} className="flex items-start justify-between gap-3 border-b border-border/60 py-1.5">
          <dt className="shrink-0 text-xs text-muted-foreground">{item.label}</dt>
          <dd className="min-w-0 break-words text-right text-xs">{item.value ?? '—'}</dd>
        </div>
      ))}
    </dl>
  )
}
