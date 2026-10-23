/**
 * P6 / C13：剧集级视频批量生成面板。
 */
import { useEffect, useMemo, useState } from 'react'
import { Clapperboard, Play, RefreshCw, RotateCcw, Square } from 'lucide-react'
import { Badge } from '../../../components/ui/badge'
import { Button } from '../../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card'
import { Input } from '../../../components/ui/input'
import type { ShotRead, VideoBatchRead } from '../../../services/generated'
import {
  useVideoBatchActions,
  useVideoBatches,
} from '../useWorkbenchQueries'

function BatchRow({ batch, onCancel, onRetry }: {
  batch: VideoBatchRead
  onCancel: () => void
  onRetry: () => void
}) {
  const total = batch.total_count || 0
  const done = (batch.succeeded_count ?? 0) + (batch.failed_count ?? 0) + (batch.cancelled_count ?? 0)
  const percent = total ? Math.round((done / total) * 100) : 0
  return (
    <div className="space-y-1 rounded border border-border p-2 text-[11px]">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={batch.status === 'failed' ? 'outline' : batch.status === 'succeeded' ? 'secondary' : 'outline'}>
          {batch.status}
        </Badge>
        <span className="text-muted-foreground">
          {done}/{total} · 成功 {batch.succeeded_count ?? 0} · 失败 {batch.failed_count ?? 0} · 运行 {batch.running_count ?? 0}
        </span>
        <span className="ml-auto text-[10px] text-muted-foreground">并发 {batch.concurrency} · 每镜 {batch.candidate_count}</span>
        {['queued', 'running'].includes(batch.status) ? (
          <Button size="sm" variant="ghost" className="h-6 px-1.5 text-[10px]" onClick={onCancel}>
            <Square className="h-3 w-3" />取消
          </Button>
        ) : null}
        {(batch.failed_count ?? 0) > 0 ? (
          <Button size="sm" variant="outline" className="h-6 px-1.5 text-[10px]" onClick={onRetry}>
            <RotateCcw className="h-3 w-3" />重试失败
          </Button>
        ) : null}
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
        <div className="h-full bg-primary" style={{ width: `${percent}%` }} />
      </div>
      {batch.error ? <p className="text-ready-blocked">{batch.error}</p> : null}
    </div>
  )
}

export function VideoBatchPanel({
  projectId,
  chapterId,
  shots,
}: {
  projectId: string
  chapterId: string
  shots: ShotRead[]
}) {
  const batchesQuery = useVideoBatches(projectId, chapterId)
  const actions = useVideoBatchActions(projectId, chapterId)
  const [selected, setSelected] = useState<string[]>([])
  const [candidateCount, setCandidateCount] = useState(1)
  const [concurrency, setConcurrency] = useState(4)
  const [allowLowCoverage, setAllowLowCoverage] = useState(false)
  const [notice, setNotice] = useState('')
  const readyShots = useMemo(() => shots.filter((shot) => shot.status === 'ready'), [shots])

  useEffect(() => {
    if (selected.length === 0) setSelected(readyShots.map((shot) => shot.id))
  }, [readyShots, selected.length])

  const create = () => {
    setNotice('')
    if (!selected.length) {
      setNotice('请选择至少一个镜头')
      return
    }
    actions.create.mutate(
      {
        shot_ids: selected,
        candidate_count: candidateCount,
        concurrency,
        allow_low_coverage: allowLowCoverage,
      },
      {
        onSuccess: (batch) => setNotice(`批次 ${batch.id.slice(0, 8)} 已创建，按并发 ${batch.concurrency} 执行`),
        onError: (error) => setNotice(error instanceof Error ? error.message : '创建批量任务失败'),
      },
    )
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex flex-wrap items-center gap-2">
          <CardTitle className="flex items-center gap-2 text-sm"><Clapperboard className="h-4 w-4" />批量视频生成</CardTitle>
          <Button size="sm" variant="ghost" className="ml-auto h-6 px-1.5 text-[10px]" onClick={() => void batchesQuery.refetch()}>
            <RefreshCw className={`h-3 w-3 ${batchesQuery.isFetching ? 'animate-spin' : ''}`} />刷新
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {notice ? <p className="rounded border border-state-pending/40 bg-state-pending/10 p-2 text-[11px]">{notice}</p> : null}
        <div className="max-h-48 overflow-auto rounded border border-border p-2">
          {shots.length === 0 ? <p className="text-[11px] text-muted-foreground">本集还没有镜头。</p> : (
            <div className="grid gap-1 sm:grid-cols-2">
              {shots.map((shot) => (
                <label key={shot.id} className="flex items-center gap-2 text-[11px]">
                  <input
                    type="checkbox"
                    checked={selected.includes(shot.id)}
                    onChange={(event) =>
                      setSelected((prev) =>
                        event.target.checked ? [...prev, shot.id] : prev.filter((id) => id !== shot.id),
                      )
                    }
                  />
                  <span className="truncate">{String(shot.index).padStart(2, '0')} · {shot.title}</span>
                  <Badge variant="outline" className="ml-auto font-normal">{shot.status}</Badge>
                </label>
              ))}
            </div>
          )}
        </div>
        <div className="flex flex-wrap items-end gap-2 text-[11px]">
          <div className="space-y-1">
            <label className="text-muted-foreground">每镜候选数</label>
            <Input type="number" min={1} max={2} value={candidateCount} onChange={(event) => setCandidateCount(Number(event.target.value) || 1)} className="h-8 w-20 text-xs" />
          </div>
          <div className="space-y-1">
            <label className="text-muted-foreground">并发</label>
            <Input type="number" min={1} max={8} value={concurrency} onChange={(event) => setConcurrency(Number(event.target.value) || 4)} className="h-8 w-20 text-xs" />
          </div>
          <label className="flex items-center gap-1 pb-2">
            <input type="checkbox" checked={allowLowCoverage} onChange={(event) => setAllowLowCoverage(event.target.checked)} />
            分镜覆盖率低时仍继续
          </label>
          <Button size="sm" className="h-8 text-[11px]" onClick={create} disabled={actions.create.isPending}>
            <Play className="h-3.5 w-3.5" />生成选中镜头
          </Button>
          <span className="pb-2 text-[10px] text-muted-foreground">默认不自动采纳；生成完成后进入抽卡审核。</span>
        </div>
        <div className="space-y-1">
          {(batchesQuery.data ?? []).map((batch) => (
            <BatchRow
              key={batch.id}
              batch={batch}
              onCancel={() => actions.cancel.mutate(batch.id, { onError: (error) => setNotice(error instanceof Error ? error.message : '取消失败') })}
              onRetry={() => actions.retry.mutate({ batchId: batch.id }, { onError: (error) => setNotice(error instanceof Error ? error.message : '重试失败') })}
            />
          ))}
          {(batchesQuery.data ?? []).length === 0 ? <p className="text-[10px] text-muted-foreground">暂无批量任务。</p> : null}
        </div>
      </CardContent>
    </Card>
  )
}
