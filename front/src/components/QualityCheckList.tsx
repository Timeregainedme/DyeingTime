/**
 * 视频生成质量检查列表。
 *
 * 与硬性准备度检查分开展示：blocking 会阻止提交，warning 是高质量风险，
 * info 是已满足约束或可优化建议。抽成公共组件，避免工作台、分镜看板和
 * 分镜工作室各自维护一套颜色/文案。
 */
import type { ShotVideoQualityCheck } from '../services/generated'

const LEVEL_STYLE: Record<ShotVideoQualityCheck['level'], string> = {
  blocking: 'text-ready-blocked',
  warning: 'text-state-pending',
  info: 'text-muted-foreground',
}

const LEVEL_LABEL: Record<ShotVideoQualityCheck['level'], string> = {
  blocking: '阻塞',
  warning: '风险',
  info: '建议',
}

export function QualityCheckList({
  checks,
  title = '生成质量检查',
  compact = false,
}: {
  checks: ShotVideoQualityCheck[]
  title?: string
  compact?: boolean
}) {
  if (!checks.length) return null
  return (
    <div data-testid="quality-check-list" className={compact ? 'mt-2 space-y-1' : 'space-y-1.5'}>
      <p className={compact ? 'text-[10px] font-medium text-muted-foreground' : 'text-xs font-medium'}>
        {title}
      </p>
      {checks.map((check) => (
        <div key={`${check.code}-${check.message}`} className="text-[10px] leading-4">
          <p className={LEVEL_STYLE[check.level]}>
            <span className="mr-1 rounded border border-current px-1 py-0.5 text-[9px]">
              {LEVEL_LABEL[check.level]}
            </span>
            {check.message}
          </p>
          {check.fix_hint ? (
            <p className="mt-0.5 text-muted-foreground">修复：{check.fix_hint}</p>
          ) : null}
        </div>
      ))}
    </div>
  )
}
