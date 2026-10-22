/**
 * 剧本文档版本差异面板（P3 / C6）。
 *
 * 只展示与记录人工决策，不自动覆盖章节正文、镜头或历史视频。
 */
import { useState } from 'react'
import { AlertTriangle, CheckCircle2, GitCompare, XCircle } from 'lucide-react'
import { Badge } from '../../../components/ui/badge'
import { Button } from '../../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card'
import type { ScriptDiffReportRead, ScriptDocumentRead } from '../../../services/generated'
import { useScriptParseActions } from '../useWorkbenchQueries'

function DiffRow({ row }: { row: Record<string, unknown> }) {
  const type = String(row.type ?? '')
  const oldText = row.old_text ? String(row.old_text) : ''
  const newText = row.new_text ? String(row.new_text) : ''
  if (type === 'insert') {
    return (
      <div className="rounded bg-ready-complete/10 px-2 py-1 text-[11px] text-ready-complete">
        + 新行 {String(row.new_line_no ?? '')}：{newText}
      </div>
    )
  }
  if (type === 'delete') {
    return (
      <div className="rounded bg-ready-blocked/10 px-2 py-1 text-[11px] text-ready-blocked">
        − 旧行 {String(row.old_line_no ?? '')}：{oldText}
      </div>
    )
  }
  return (
    <div className="rounded bg-state-pending/10 px-2 py-1 text-[11px] text-state-pending">
      改 旧 {String(row.old_line_no ?? '')} / 新 {String(row.new_line_no ?? '')}：{oldText}
      {newText && oldText ? ` → ${newText}` : newText}
    </div>
  )
}

export function ScriptDiffPanel({
  projectId,
  document,
}: {
  projectId: string
  document: ScriptDocumentRead
}) {
  const actions = useScriptParseActions(projectId, document.id)
  const [report, setReport] = useState<ScriptDiffReportRead | null>(null)
  const [error, setError] = useState('')
  const comparable =
    Boolean(document.active_version_id) &&
    Boolean(document.current_version_id) &&
    document.active_version_id !== document.current_version_id

  if (!comparable && !report) return null

  const generate = () => {
    setError('')
    actions.diff.mutate(
      { documentId: document.id },
      {
        onSuccess: setReport,
        onError: (err) =>
          setError(err instanceof Error ? err.message : '差异报告生成失败'),
      },
    )
  }

  const decide = (status: 'accepted' | 'ignored') => {
    if (!report) return
    actions.decideDiff.mutate(
      { reportId: report.id, status },
      {
        onSuccess: setReport,
        onError: (err) =>
          setError(err instanceof Error ? err.message : '差异决策失败'),
      },
    )
  }

  const impact = report?.impact ?? {}
  const textDiff = report?.text_diff ?? []
  const structuredDiff = report?.structured_diff ?? {}
  const chapters = (impact.chapters as Array<Record<string, unknown>> | undefined) ?? []
  const shots = (impact.shots as Array<Record<string, unknown>> | undefined) ?? []
  const assets = (impact.assets as Record<string, string[]> | undefined) ?? {}

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <GitCompare className="h-4 w-4 text-muted-foreground" />
            版本差异与影响范围
          </CardTitle>
          <div className="flex items-center gap-1.5">
            {report ? <Badge variant="outline">{report.status}</Badge> : null}
            <Button
              size="sm"
              variant="outline"
              onClick={generate}
              disabled={actions.diff.isPending || !comparable}
            >
              {actions.diff.isPending ? '生成中…' : report ? '重新生成' : '生成差异报告'}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {error ? (
          <div className="rounded-md border border-ready-blocked/40 bg-ready-blocked/10 p-2 text-[11px] text-ready-blocked">
            {error}
          </div>
        ) : null}
        {!report ? (
          <p className="text-xs text-muted-foreground">
            当前有一个候选版本尚未生效。生成差异报告后，可查看文本变化、角色/场景/道具变化与可能受影响的章节、镜头。
          </p>
        ) : (
          <>
            <div className="flex flex-wrap gap-3 text-[11px] text-muted-foreground">
              <span>文本变化 {textDiff.length} 条</span>
              <span>影响章节 {chapters.length}</span>
              <span>可能影响镜头 {shots.length}</span>
              <span>
                其中有历史视频{' '}
                {shots.filter((item) => item.has_video).length} 个（不会被删除）
              </span>
            </div>

            <div className="grid gap-3 lg:grid-cols-2">
              <div className="space-y-1">
                <p className="text-xs font-medium">文本差异</p>
                <div className="max-h-48 space-y-1 overflow-auto">
                  {textDiff.slice(0, 30).map((row, index) => (
                    <DiffRow key={`diff-${index}`} row={row} />
                  ))}
                  {textDiff.length === 0 ? (
                    <p className="text-[11px] text-muted-foreground">文本无变化。</p>
                  ) : null}
                </div>
              </div>
              <div className="space-y-2">
                <p className="text-xs font-medium">结构化变化</p>
                {structuredDiff.requires_reparse ? (
                  <p className="flex items-start gap-1.5 text-[11px] text-state-pending">
                    <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
                    新版本尚未解析，结构化变化需要重新解析后再确认。
                  </p>
                ) : null}
                <div className="space-y-1 text-[11px] text-muted-foreground">
                  <p>角色新增：{JSON.stringify(structuredDiff.characters_added ?? [])}</p>
                  <p>角色移除：{JSON.stringify(structuredDiff.characters_removed ?? [])}</p>
                  <p>场景新增：{JSON.stringify(structuredDiff.scenes_added ?? [])}</p>
                  <p>道具新增：{JSON.stringify(structuredDiff.props_added ?? [])}</p>
                  <p>
                    服装变化：
                    {JSON.stringify(structuredDiff.costume_changes_added ?? [])}
                  </p>
                </div>
                <div className="rounded-md border border-border p-2 text-[11px]">
                  <p className="font-medium">可能受影响的资产</p>
                  <p className="mt-1 text-muted-foreground">
                    角色：{assets.characters?.join('、') || '—'}
                  </p>
                  <p className="text-muted-foreground">场景：{assets.scenes?.join('、') || '—'}</p>
                  <p className="text-muted-foreground">道具：{assets.props?.join('、') || '—'}</p>
                  <p className="text-muted-foreground">服装：{assets.costumes?.join('、') || '—'}</p>
                </div>
                {chapters.length ? (
                  <div className="text-[11px] text-muted-foreground">
                    章节：{chapters.map((item) => `第${item.index}集`).join('、')}
                  </div>
                ) : null}
              </div>
            </div>

            <div className="flex items-center gap-1.5 border-t border-border pt-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => decide('accepted')}
                disabled={actions.decideDiff.isPending || report.status === 'accepted'}
              >
                <CheckCircle2 className="h-3.5 w-3.5" />
                接受差异
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => decide('ignored')}
                disabled={actions.decideDiff.isPending || report.status === 'ignored'}
              >
                <XCircle className="h-3.5 w-3.5" />
                忽略差异
              </Button>
              <span className="text-[10px] text-muted-foreground">
                接受/忽略只记录决策，不会自动覆盖正式数据或删除历史视频。
              </span>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
