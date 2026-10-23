/**
 * P6：镜头 H3 多参考、@ 提示词、准备度与生成入口。
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { ImagePlus, Pin, RefreshCw, Sparkles, Trash2, Unlock, Upload } from 'lucide-react'
import { Badge } from '../../../components/ui/badge'
import { Button } from '../../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card'
import { Input } from '../../../components/ui/input'
import { Textarea } from '../../../components/ui/textarea'
import type {
  GenerationPreviewRead,
  P6VideoGenerateRequest,
  ReferenceBindingRead,
} from '../../../services/generated'
import {
  useGenerationQuota,
  useGenerationSnapshots,
  useP6Readiness,
  useReferenceBindings,
  useShotReferenceActions,
  useWorkbenchShotDetail,
} from '../useWorkbenchQueries'

const ROLE_LABELS: Record<string, string> = {
  character_identity: '角色身份',
  character_appearance: '角色造型',
  scene: '场景',
  prop: '道具',
  costume: '服装',
  shot_composition: '镜头构图',
  previous_shot: '上一镜参考',
}

export function ShotReferencePanel({
  projectId,
  shotId,
}: {
  projectId: string
  shotId: string
}) {
  const bindingsQuery = useReferenceBindings(projectId, shotId)
  const readinessQuery = useP6Readiness(projectId, shotId)
  const snapshotsQuery = useGenerationSnapshots(projectId, shotId)
  const detailQuery = useWorkbenchShotDetail(projectId, shotId)
  const quotaQuery = useGenerationQuota()
  const actions = useShotReferenceActions(projectId, shotId)
  const [prompt, setPrompt] = useState('')
  const [advancedPrompt, setAdvancedPrompt] = useState('')
  const [preview, setPreview] = useState<GenerationPreviewRead | null>(null)
  const [notice, setNotice] = useState('')
  const [role, setRole] = useState('shot_composition')
  const uploadRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    setPrompt(detailQuery.data?.video_prompt_draft ?? '')
  }, [detailQuery.data?.video_prompt_draft, shotId])

  const active = useMemo(
    () => (bindingsQuery.data ?? []).filter((item) => item.is_active),
    [bindingsQuery.data],
  )
  const body = (): P6VideoGenerateRequest => ({
    prompt,
    advanced_prompt: advancedPrompt,
    reference_mode: 'reference',
    reference_audio_file_ids: [],
    auto_adopt: false,
  })
  const readiness = readinessQuery.data
  const busy =
    actions.recommend.isPending ||
    actions.update.isPending ||
    actions.remove.isPending ||
    actions.reorder.isPending ||
    actions.upload.isPending ||
    actions.preview.isPending ||
    actions.generate.isPending

  const move = (binding: ReferenceBindingRead, direction: -1 | 1) => {
    const index = active.findIndex((item) => item.id === binding.id)
    const target = index + direction
    if (index < 0 || target < 0 || target >= active.length) return
    const ids = active.map((item) => item.id)
    ;[ids[index], ids[target]] = [ids[target], ids[index]]
    actions.reorder.mutate(ids)
  }

  return (
    <div className="space-y-3">
      <Card>
        <CardHeader className="pb-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <ImagePlus className="h-4 w-4" />H3 参考素材
            </CardTitle>
            <div className="flex flex-wrap gap-1">
              <Badge variant={readiness?.ready ? 'secondary' : 'outline'}>
                {readiness?.ready ? '生成准备就绪' : '准备度未通过'}
              </Badge>
              <Badge variant="outline">已启用 {active.length} 张</Badge>
              {quotaQuery.data?.map((item) => (
                <Badge key={item.media_type} variant="outline" className="font-normal">
                  {item.media_type} 余额 {item.remaining}
                </Badge>
              ))}
              <Button size="sm" variant="outline" className="h-7 px-2 text-[10px]" onClick={() => actions.recommend.mutate()} disabled={busy}>
                <Sparkles className="h-3 w-3" />自动推荐
              </Button>
              <Button size="sm" variant="outline" className="h-7 px-2 text-[10px]" onClick={() => uploadRef.current?.click()} disabled={busy}>
                <Upload className="h-3 w-3" />上传参考
              </Button>
              <input
                ref={uploadRef}
                type="file"
                accept="image/png,image/jpeg,image/webp,image/gif"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0]
                  event.target.value = ''
                  if (file) actions.upload.mutate({ file, referenceRole: role })
                }}
              />
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-2">
          {notice ? <p className="text-[11px] text-state-pending">{notice}</p> : null}
          <div className="space-y-1">
            <label className="text-[10px] text-muted-foreground">上传用途</label>
            <Input value={role} onChange={(event) => setRole(event.target.value)} className="h-7 text-[11px]" />
          </div>
          {bindingsQuery.isLoading ? (
            <p className="text-xs text-muted-foreground">加载参考绑定…</p>
          ) : (bindingsQuery.data ?? []).length === 0 ? (
            <p className="text-xs text-muted-foreground">暂无参考图。自动推荐会读取 P5 镜头资产版本；手工删除的自动项不会再次恢复。</p>
          ) : (
            <div className="space-y-1">
              {(bindingsQuery.data ?? []).map((item) => (
                <div
                  key={item.id}
                  className={`flex items-center gap-2 rounded border p-1.5 ${item.is_active ? 'border-border' : 'border-border/50 opacity-50'}`}
                >
                  <span className="w-6 text-center text-[10px] text-muted-foreground">图{(item.sort_order ?? 0) + 1}</span>
                  {item.file_url ? (
                    <img src={item.file_url} alt={item.asset_name} className="h-12 w-12 rounded object-cover" />
                  ) : (
                    <div className="flex h-12 w-12 items-center justify-center rounded bg-muted text-[9px]">缺图</div>
                  )}
                  <div className="min-w-0 flex-1 text-[10px]">
                    <p className="truncate font-medium">{item.asset_name || item.reference_role}</p>
                    <p className="truncate text-muted-foreground">
                      {ROLE_LABELS[item.reference_role ?? ''] ?? item.reference_role} · {item.source}
                      {item.is_pinned ? ' · 已锁定' : ''}
                    </p>
                  </div>
                  <Button size="sm" variant="ghost" className="h-6 w-6 p-0" disabled={!item.is_active || busy} onClick={() => move(item, -1)}>↑</Button>
                  <Button size="sm" variant="ghost" className="h-6 w-6 p-0" disabled={!item.is_active || busy} onClick={() => move(item, 1)}>↓</Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 w-6 p-0"
                    disabled={busy}
                    onClick={() => actions.update.mutate({ bindingId: item.id, body: { is_pinned: !item.is_pinned } })}
                  >
                    {item.is_pinned ? <Unlock className="h-3 w-3" /> : <Pin className="h-3 w-3" />}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 w-6 p-0 text-ready-blocked"
                    disabled={busy || item.is_pinned || !item.is_active}
                    onClick={() =>
                      actions.remove.mutate(item.id, {
                        onError: (error) => setNotice(error instanceof Error ? error.message : '删除失败'),
                      })
                    }
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              ))}
            </div>
          )}
          {readiness?.checks?.length ? (
            <div className="rounded border border-border bg-muted/20 p-2 text-[10px]">
              {readiness.checks.filter((item) => !item.ok).slice(0, 6).map((item) => (
                <p key={item.key} className="text-ready-blocked">× {item.message}</p>
              ))}
              {readiness.checks.every((item) => item.ok) ? <p className="text-ready-complete">全部准备度检查通过。</p> : null}
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-sm">提示词与生成预览</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          <label className="text-[11px] text-muted-foreground">自然语言提示词（支持 @角色 / @场景 / @道具）</label>
          <Textarea value={prompt} rows={3} onChange={(event) => setPrompt(event.target.value)} className="text-xs" />
          <label className="text-[11px] text-muted-foreground">高级最终 H3 提示词（可选；非空时优先）</label>
          <Textarea value={advancedPrompt} rows={3} onChange={(event) => setAdvancedPrompt(event.target.value)} className="text-xs" />
          <div className="flex flex-wrap gap-1">
            <Button size="sm" variant="outline" className="h-7 px-2 text-[10px]" onClick={() => actions.savePrompt.mutate(prompt)} disabled={busy}>
              保存提示词
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-7 px-2 text-[10px]"
              onClick={() => actions.preview.mutate(body(), {
                onSuccess: (data) => {
                  setPreview(data)
                  setNotice((data.blocking_errors ?? []).length ? (data.blocking_errors ?? []).join('；') : '预览已按当前 manifest 生成')
                },
                onError: (error) => setNotice(error instanceof Error ? error.message : '预览失败'),
              })}
              disabled={busy}
            >
              <RefreshCw className="h-3 w-3" />预览最终 H3
            </Button>
            <Button
              size="sm"
              className="h-7 px-2 text-[10px]"
              disabled={busy || !readiness?.ready || Boolean((preview?.blocking_errors ?? []).length)}
              onClick={() => actions.generate.mutate(body(), {
                onSuccess: (data) => setNotice(`已创建视频任务 ${data.task_id}；生成完成后进入抽卡审核`),
                onError: (error) => setNotice(error instanceof Error ? error.message : '生成任务创建失败'),
              })}
            >
              <Sparkles className="h-3 w-3" />生成视频（不自动采纳）
            </Button>
          </div>
          {preview ? (
            <div className="space-y-1 rounded border border-border p-2 text-[10px]">
              <p className="font-medium">参考图 {(preview.images ?? []).length} 张 · 音频 {(preview.audio_file_ids ?? []).length} 个 · {preview.ratio} · {preview.duration}s</p>
              <pre className="max-h-40 overflow-auto whitespace-pre-wrap">{preview.prompt}</pre>
              {(preview.warnings ?? []).map((warning) => <p key={warning} className="text-state-pending">{warning}</p>)}
              {(preview.blocking_errors ?? []).map((error) => <p key={error} className="text-ready-blocked">{error}</p>)}
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-sm">生成输入快照</CardTitle></CardHeader>
        <CardContent className="space-y-1 text-[10px]">
          {(snapshotsQuery.data ?? []).slice(0, 5).map((snapshot) => (
            <div key={snapshot.id} className="rounded border border-border p-2">
              <p className="font-medium">{snapshot.model_name || '模型'} · {snapshot.ratio} · {snapshot.duration}s · {snapshot.created_at}</p>
              <p className="text-muted-foreground">参考 {(snapshot.manifest ?? []).length} 张 · 音频 {(snapshot.audio_refs ?? []).length} · hash {(snapshot.input_hash ?? '').slice(0, 12)}</p>
            </div>
          ))}
          {(snapshotsQuery.data ?? []).length === 0 ? <p className="text-muted-foreground">还没有生成快照。</p> : null}
        </CardContent>
      </Card>
    </div>
  )
}
