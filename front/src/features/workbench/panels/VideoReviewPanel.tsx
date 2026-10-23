/**
 * P6 / C14：视频候选抽卡审核与显式采纳。
 */
import { useEffect, useState } from 'react'
import { CheckCircle2, Film, RefreshCw, XCircle } from 'lucide-react'
import { Badge } from '../../../components/ui/badge'
import { Button } from '../../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card'
import { Textarea } from '../../../components/ui/textarea'
import type { ShotVideoVersionRead } from '../../../services/generated'
import { useShotVideoVersions, useVideoReviewActions } from '../useWorkbenchQueries'

const ISSUE_TAGS = [
  '人物脸部漂移',
  '服装不一致',
  '场景错误',
  '动作错误',
  '运镜错误',
  '对白/口型错误',
  '音色错误',
  '肢体畸形',
  '画面闪烁',
  '其他',
]

function Candidate({
  item,
  busy,
  onReview,
  onAdopt,
}: {
  item: ShotVideoVersionRead
  busy: boolean
  onReview: (status: string, tags: string[], note: string) => void
  onAdopt: () => void
}) {
  const [tags, setTags] = useState<string[]>(item.issue_tags ?? [])
  const [note, setNote] = useState(item.note ?? '')
  useEffect(() => {
    setTags(item.issue_tags ?? [])
    setNote(item.note ?? '')
  }, [item.task_id, item.issue_tags, item.note])
  return (
    <div className={`space-y-2 rounded-md border p-2 ${item.is_current ? 'border-primary/60 bg-primary/5' : 'border-border'}`}>
      <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
        <Badge variant={item.is_current ? 'secondary' : 'outline'}>{item.is_current ? '当前采纳' : '候选'}</Badge>
        <Badge variant="outline">{item.status}</Badge>
        <span className="text-muted-foreground">{item.model_name || '模型'} · {item.seconds ?? '—'}s · 参考 {item.reference_count ?? 0} 张</span>
        {item.status === 'failed' ? <Badge variant="outline" className="border-ready-blocked/40 text-ready-blocked">失败</Badge> : null}
      </div>
      {item.file_url ? (
        <video className="max-h-64 w-full rounded bg-black" controls src={item.file_url} />
      ) : (
        <div className="flex h-32 items-center justify-center rounded bg-muted text-[11px] text-muted-foreground">
          {item.status === 'running' ? '生成中…' : '暂无视频文件'}
        </div>
      )}
      {item.error ? <p className="text-[10px] text-ready-blocked">{item.error}</p> : null}
      <div className="space-y-1">
        <p className="text-[10px] font-medium">问题标签</p>
        <div className="flex flex-wrap gap-1">
          {ISSUE_TAGS.map((tag) => (
            <button
              key={tag}
              type="button"
              onClick={() => setTags((prev) => prev.includes(tag) ? prev.filter((item) => item !== tag) : [...prev, tag])}
              className={`rounded-full border px-2 py-0.5 text-[10px] ${tags.includes(tag) ? 'border-state-pending/60 bg-state-pending/10 text-state-pending' : 'border-border text-muted-foreground'}`}
            >
              {tag}
            </button>
          ))}
        </div>
        <Textarea value={note} rows={2} onChange={(event) => setNote(event.target.value)} placeholder="审核备注" className="text-xs" />
      </div>
      <div className="flex flex-wrap gap-1">
        <Button size="sm" variant="outline" className="h-7 px-2 text-[10px]" disabled={busy || item.status !== 'succeeded'} onClick={() => onReview('satisfied', tags, note)}>
          <CheckCircle2 className="h-3 w-3" />满意
        </Button>
        <Button size="sm" variant="ghost" className="h-7 px-2 text-[10px] text-ready-blocked" disabled={busy || item.status !== 'succeeded'} onClick={() => onReview('unsatisfied', tags, note)}>
          <XCircle className="h-3 w-3" />不满意
        </Button>
        <Button size="sm" className="h-7 px-2 text-[10px]" disabled={busy || item.is_current || !item.file_id} onClick={onAdopt}>
          <CheckCircle2 className="h-3 w-3" />采纳此版本
        </Button>
        {item.review_status !== 'unrated' ? <Badge variant="outline" className="ml-auto">{item.review_status}</Badge> : null}
      </div>
      {item.manifest?.length ? (
        <p className="text-[10px] text-muted-foreground">参考图 {item.manifest.map((ref) => ref.asset_id ?? ref.file_id).slice(0, 5).join('、')}</p>
      ) : null}
    </div>
  )
}

export function VideoReviewPanel({
  projectId,
  shotId,
}: {
  projectId: string
  shotId: string
}) {
  const query = useShotVideoVersions(projectId, shotId)
  const actions = useVideoReviewActions(projectId, shotId)
  const [notice, setNotice] = useState('')
  const items = query.data ?? []

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex flex-wrap items-center gap-2">
          <CardTitle className="flex items-center gap-2 text-sm"><Film className="h-4 w-4" />视频候选与抽卡</CardTitle>
          <Badge variant="outline">共 {items.length} 个版本</Badge>
          <Button size="sm" variant="ghost" className="ml-auto h-6 px-1.5 text-[10px]" onClick={() => void query.refetch()}>
            <RefreshCw className={`h-3 w-3 ${query.isFetching ? 'animate-spin' : ''}`} />刷新
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        {notice ? <p className="rounded border border-state-pending/40 bg-state-pending/10 p-2 text-[11px]">{notice}</p> : null}
        {items.length === 0 ? (
          <p className="text-xs text-muted-foreground">还没有视频候选。上方“生成视频”只新增候选，不自动替换当前采纳版本。</p>
        ) : (
          <div className="grid gap-2 xl:grid-cols-2">
            {items.map((item) => (
              <Candidate
                key={item.task_id}
                item={item}
                busy={actions.review.isPending || actions.adopt.isPending}
                onReview={(status, tags, note) =>
                  actions.review.mutate(
                    { taskId: item.task_id, body: { review_status: status, issue_tags: tags, note } },
                    {
                      onSuccess: () => setNotice(status === 'satisfied' ? '已标记满意' : '已标记不满意'),
                      onError: (error) => setNotice(error instanceof Error ? error.message : '审核保存失败'),
                    },
                  )
                }
                onAdopt={() =>
                  actions.adopt.mutate(item.task_id, {
                    onSuccess: () => setNotice('已采纳该视频版本；旧版本文件保留'),
                    onError: (error) => setNotice(error instanceof Error ? error.message : '采纳失败'),
                  })
                }
              />
            ))}
          </div>
        )}
        <p className="text-[10px] text-muted-foreground">
          新任务完成不会自动覆盖已采纳视频；如需修改后重抽，请在上方提示词区修改并重新生成。
        </p>
      </CardContent>
    </Card>
  )
}
