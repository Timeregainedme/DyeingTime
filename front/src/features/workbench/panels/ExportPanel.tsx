/**
 * 导出面板。
 *
 * P7：在树状工作台中按剧集/场次/镜头选择已采纳视频，先做服务端预检查，
 * 再下载 MP4-only ZIP。导出只读取现有文件，不触发任何生成任务。
 */
import { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  ExternalLink,
  Film,
  RefreshCw,
  XCircle,
} from 'lucide-react'
import { Badge } from '../../../components/ui/badge'
import { Button } from '../../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card'
import { cn } from '../../../lib/utils'
import type { ClipsExportPrecheckRead, TimelineClipRead } from '../../../services/generated'
import {
  useClipsExportActions,
  useWorkbenchTimeline,
} from '../useWorkbenchQueries'
import { LegacyLink, PanelHeader } from '../components/PanelHeader'
import { PanelEmpty, PanelError, PanelLoading } from '../components/PanelStates'
import { legacyChapterListPath, legacyEditorPath } from './legacyPaths'

function clipLabel(clip: TimelineClipRead) {
  return `E${String(clip.chapter_index).padStart(2, '0')} · SC${String(
    clip.scene_index ?? 0,
  ).padStart(2, '0')} · SH${String(clip.index).padStart(3, '0')}`
}



function statusText(status?: string) {
  if (status === 'ok') return '文件可导出'
  if (status === 'no_accepted') return '尚未采纳视频'
  if (status === 'storage_unavailable') return '对象存储不可读'
  if (status === 'unsupported_format') return '不是有效 MP4'
  if (status === 'file_missing') return '文件缺失'
  return '待预检查'
}

export function ExportPanel({ projectId }: { projectId: string }) {
  const timelineQuery = useWorkbenchTimeline(projectId)
  const actions = useClipsExportActions(projectId)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [chapterFilter, setChapterFilter] = useState('')
  const [sceneFilter, setSceneFilter] = useState('')
  const [onlyAccepted, setOnlyAccepted] = useState(false)
  const [precheck, setPrecheck] = useState<ClipsExportPrecheckRead | null>(null)
  const [notice, setNotice] = useState('')

  const timeline = timelineQuery.data
  const clips = useMemo(
    () =>
      [...(timeline?.clips ?? [])].sort((a, b) =>
        a.chapter_index === b.chapter_index
          ? a.index - b.index
          : a.chapter_index - b.chapter_index,
      ),
    [timeline?.clips],
  )
  const acceptedClips = useMemo(
    () => clips.filter((clip) => Boolean(clip.video_file_id)),
    [clips],
  )
  const chapterOptions = useMemo(() => {
    const map = new Map<string, { id: string; index: number; title: string }>()
    for (const clip of clips) {
      if (!map.has(clip.chapter_id)) {
        map.set(clip.chapter_id, {
          id: clip.chapter_id,
          index: clip.chapter_index,
          title: clip.chapter_title,
        })
      }
    }
    return [...map.values()].sort((a, b) => a.index - b.index)
  }, [clips])
  const sceneOptions = useMemo(() => {
    const map = new Map<string, { id: string; index: number; title: string; chapterId: string }>()
    for (const clip of clips) {
      if (!clip.scene_group_id) continue
      if (chapterFilter && clip.chapter_id !== chapterFilter) continue
      if (!map.has(clip.scene_group_id)) {
        map.set(clip.scene_group_id, {
          id: clip.scene_group_id,
          index: clip.scene_index ?? 0,
          title: clip.scene_title ?? '',
          chapterId: clip.chapter_id,
        })
      }
    }
    return [...map.values()].sort((a, b) => a.index - b.index)
  }, [chapterFilter, clips])
  const filteredClips = useMemo(
    () =>
      clips.filter((clip) => {
        if (chapterFilter && clip.chapter_id !== chapterFilter) return false
        if (sceneFilter && clip.scene_group_id !== sceneFilter) return false
        if (onlyAccepted && !clip.video_file_id) return false
        return true
      }),
    [chapterFilter, clips, onlyAccepted, sceneFilter],
  )
  const selectedClips = useMemo(
    () => clips.filter((clip) => selected.has(clip.shot_id)),
    [clips, selected],
  )
  const selectedDuration = selectedClips.reduce(
    (total, clip) => total + Number(clip.duration ?? 0),
    0,
  )
  const selectedKey = useMemo(() => [...selected].sort().join(','), [selected])
  const precheckById = useMemo(
    () => new Map((precheck?.items ?? []).map((item) => [item.shot_id, item])),
    [precheck?.items],
  )
  const grouped = useMemo(() => {
    const chapters = new Map<
      string,
      {
        chapterId: string
        chapterIndex: number
        chapterTitle: string
        scenes: Map<
          string,
          { sceneIndex: number; sceneTitle: string; clips: TimelineClipRead[] }
        >
      }
    >()
    for (const clip of filteredClips) {
      const chapter = chapters.get(clip.chapter_id) ?? {
        chapterId: clip.chapter_id,
        chapterIndex: clip.chapter_index,
        chapterTitle: clip.chapter_title,
        scenes: new Map(),
      }
      const sceneKey = clip.scene_group_id ?? '__unassigned__'
      const scene = chapter.scenes.get(sceneKey) ?? {
        sceneIndex: clip.scene_index ?? 0,
        sceneTitle: clip.scene_title || '未分配场次',
        clips: [],
      }
      scene.clips.push(clip)
      chapter.scenes.set(sceneKey, scene)
      chapters.set(clip.chapter_id, chapter)
    }
    return [...chapters.values()].sort((a, b) => a.chapterIndex - b.chapterIndex)
  }, [filteredClips])

  useEffect(() => {
    if (sceneFilter && !sceneOptions.some((scene) => scene.id === sceneFilter)) {
      setSceneFilter('')
    }
  }, [sceneFilter, sceneOptions])

  useEffect(() => {
    setPrecheck(null)
  }, [selectedKey])

  const toggle = (shotId: string) => {
    setSelected((previous) => {
      const next = new Set(previous)
      if (next.has(shotId)) next.delete(shotId)
      else next.add(shotId)
      return next
    })
    setNotice('')
  }
  const selectVisible = () => {
    setSelected((previous) => {
      const next = new Set(previous)
      for (const clip of filteredClips) next.add(clip.shot_id)
      return next
    })
    setPrecheck(null)
  }
  const selectAccepted = () => {
    setSelected(new Set(acceptedClips.map((clip) => clip.shot_id)))
    setPrecheck(null)
  }
  const clearSelection = () => {
    setSelected(new Set())
    setPrecheck(null)
    setNotice('')
  }
  const runPrecheck = () => {
    setNotice('')
    if (!selected.size) {
      setNotice('请先选择至少一个镜头')
      return
    }
    actions.precheck.mutate(
      { shot_ids: [...selected] },
      {
        onSuccess: (data) => {
          setPrecheck(data)
          setNotice(
            data.can_download
              ? `预检查通过：${data.exportable_count} 个 MP4，总时长 ${Math.round(data.total_duration)}s`
              : `预检查发现 ${(data.blockers ?? []).length} 个阻塞项，请调整选择`,
          )
        },
        onError: (error) => {
          setPrecheck(null)
          setNotice(error instanceof Error ? error.message : '预检查失败')
        },
      },
    )
  }
  const download = () => {
    if (!precheck?.can_download) return
    setNotice('')
    actions.download.mutate(
      {
        shot_ids: [...selected],
        expected_plan_hash: precheck.plan_hash,
      },
      {
        onSuccess: ({ blob, filename }) => {
          const url = URL.createObjectURL(blob)
          const link = document.createElement('a')
          link.href = url
          link.download = filename
          document.body.appendChild(link)
          link.click()
          link.remove()
          URL.revokeObjectURL(url)
          setNotice(`已生成 ${filename}，包含 ${precheck.exportable_count} 个 MP4`)
        },
        onError: (error) =>
          setNotice(error instanceof Error ? error.message : 'ZIP 下载失败'),
      },
    )
  }

  if (timelineQuery.isLoading) return <PanelLoading lines={6} label="加载导出信息" />
  if (timelineQuery.isError) {
    return (
      <PanelError
        message={
          timelineQuery.error instanceof Error ? timelineQuery.error.message : '时间线加载失败'
        }
        onRetry={() => void timelineQuery.refetch()}
      />
    )
  }

  return (
    <div className="space-y-4">
      <PanelHeader
        title="导出"
        description="选择已采纳的视频镜头，检查文件后按正式编号打包 MP4 ZIP。"
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void timelineQuery.refetch()}
              disabled={timelineQuery.isFetching}
            >
              <RefreshCw
                className={cn('h-3.5 w-3.5', timelineQuery.isFetching && 'animate-spin')}
              />
              刷新
            </Button>
            <LegacyLink href={legacyEditorPath(projectId)}>
              <ExternalLink className="h-3.5 w-3.5" />
              旧版导出
            </LegacyLink>
          </>
        }
      />

      {!timeline || clips.length === 0 ? (
        <PanelEmpty
          title="还没有可导出的镜头"
          description="先在生成工作室产出并采纳视频，导出清单才会出现镜头。"
          action={
            <LegacyLink href={legacyChapterListPath(projectId)}>
              去剧集列表
            </LegacyLink>
          }
        />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 2xl:grid-cols-7">
            {[
              { label: '项目', value: timeline.project_name || projectId },
              { label: '剧集数', value: chapterOptions.length },
              { label: '镜头总数', value: clips.length },
              { label: '已采纳', value: acceptedClips.length },
              { label: '未采纳', value: clips.length - acceptedClips.length },
              { label: '已选镜头', value: selected.size },
              { label: '已选时长', value: `${Math.round(selectedDuration)}s` },
            ].map((item) => (
              <Card key={item.label}>
                <CardContent className="p-3">
                  <p className="text-[11px] text-muted-foreground">{item.label}</p>
                  <p className="truncate text-lg font-semibold leading-tight">{item.value}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex flex-wrap items-center gap-2 text-sm">
                <Film className="h-4 w-4 text-muted-foreground" />
                镜头选择
                <Badge variant="outline">已采纳 {acceptedClips.length}</Badge>
                <Badge variant="outline">当前筛选 {filteredClips.length}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-wrap items-center gap-2 text-[11px]">
                <select
                  value={chapterFilter}
                  onChange={(event) => setChapterFilter(event.target.value)}
                  className="h-8 rounded-md border border-input bg-background px-2 text-xs"
                >
                  <option value="">全部剧集</option>
                  {chapterOptions.map((chapter) => (
                    <option key={chapter.id} value={chapter.id}>
                      E{String(chapter.index).padStart(2, '0')} · {chapter.title}
                    </option>
                  ))}
                </select>
                <select
                  value={sceneFilter}
                  onChange={(event) => setSceneFilter(event.target.value)}
                  className="h-8 rounded-md border border-input bg-background px-2 text-xs"
                >
                  <option value="">全部场次</option>
                  {sceneOptions.map((scene) => (
                    <option key={scene.id} value={scene.id}>
                      SC{String(scene.index).padStart(2, '0')} · {scene.title}
                    </option>
                  ))}
                </select>
                <label className="flex items-center gap-1">
                  <input
                    type="checkbox"
                    checked={onlyAccepted}
                    onChange={(event) => setOnlyAccepted(event.target.checked)}
                  />
                  仅显示已采纳视频
                </label>
                <Button size="sm" variant="outline" className="h-8 px-2 text-[10px]" onClick={selectVisible}>
                  全选当前筛选
                </Button>
                <Button size="sm" variant="outline" className="h-8 px-2 text-[10px]" onClick={selectAccepted}>
                  选择全部已采纳
                </Button>
                <Button size="sm" variant="ghost" className="h-8 px-2 text-[10px]" onClick={clearSelection}>
                  取消全选
                </Button>
              </div>

              <div className="max-h-[52vh] overflow-auto rounded-md border border-border">
                {grouped.length === 0 ? (
                  <p className="p-4 text-xs text-muted-foreground">当前筛选没有镜头。</p>
                ) : (
                  grouped.map((chapter) => (
                    <section key={chapter.chapterId} className="border-b border-border last:border-b-0">
                      <div className="sticky top-0 z-10 bg-muted/80 px-3 py-1.5 text-[11px] font-medium backdrop-blur">
                        第 {chapter.chapterIndex} 集 · {chapter.chapterTitle}
                      </div>
                      {[...chapter.scenes.entries()]
                        .sort(([, a], [, b]) => a.sceneIndex - b.sceneIndex)
                        .map(([sceneKey, scene]) => (
                          <div key={sceneKey}>
                            <div className="px-3 py-1 text-[10px] text-muted-foreground">
                              SC{String(scene.sceneIndex).padStart(2, '0')} · {scene.sceneTitle}
                            </div>
                            {scene.clips.map((clip) => {
                              const item = precheckById.get(clip.shot_id)
                              const checked = selected.has(clip.shot_id)
                              return (
                                <label
                                  key={clip.shot_id}
                                  className={cn(
                                    'flex cursor-pointer items-center gap-2 border-t border-border/50 px-3 py-1.5 text-xs hover:bg-muted/40',
                                    checked && 'bg-primary/5',
                                  )}
                                >
                                  <input
                                    type="checkbox"
                                    checked={checked}
                                    onChange={() => toggle(clip.shot_id)}
                                  />
                                  <span className="w-40 shrink-0 tabular-nums text-muted-foreground">
                                    {clipLabel(clip)}
                                  </span>
                                  <span className="min-w-0 flex-1 truncate">{clip.title}</span>
                                  <span className="w-10 shrink-0 text-right tabular-nums text-muted-foreground">
                                    {clip.duration ?? 0}s
                                  </span>
                                  <span className="w-28 shrink-0 text-right">
                                    {clip.video_file_id ? (
                                      <Badge variant="secondary">已采纳</Badge>
                                    ) : (
                                      <Badge variant="outline" className="text-muted-foreground">未采纳</Badge>
                                    )}
                                  </span>
                                  <span
                                    className={cn(
                                      'w-24 shrink-0 text-right text-[10px]',
                                      item?.status === 'ok'
                                        ? 'text-run-success'
                                        : item && item.status !== 'ok'
                                          ? 'text-ready-blocked'
                                          : 'text-muted-foreground',
                                    )}
                                  >
                                    {statusText(item?.status)}
                                  </span>
                                </label>
                              )
                            })}
                          </div>
                        ))}
                    </section>
                  ))
                )}
              </div>
              <p className="text-[10px] text-muted-foreground">
                ZIP 命名固定为 E01_SC02_SH003.mp4；未分配场次使用 SC00。导出只读取
                `shots.generated_video_file_id` 指向的当前采纳版本，包含候选但不含未采纳结果。
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">预检查与下载</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-[11px]">
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  className="h-8 text-[11px]"
                  onClick={runPrecheck}
                  disabled={!selected.size || actions.precheck.isPending}
                >
                  <RefreshCw className={cn('h-3.5 w-3.5', actions.precheck.isPending && 'animate-spin')} />
                  预检查
                </Button>
                <Button
                  size="sm"
                  className="h-8 text-[11px]"
                  onClick={download}
                  disabled={!precheck?.can_download || actions.download.isPending}
                >
                  <Download className="h-3.5 w-3.5" />
                  下载 MP4 ZIP
                </Button>
                <span className="text-muted-foreground">
                  已选 {selected.size} 个 · {Math.round(selectedDuration)}s
                </span>
              </div>
              {notice ? (
                <p className="rounded border border-state-pending/40 bg-state-pending/10 p-2 text-state-pending">
                  {notice}
                </p>
              ) : null}
              {precheck ? (
                <div className="space-y-2">
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                    <div className="rounded border border-border p-2">可导出 <b>{precheck.exportable_count}</b></div>
                    <div className="rounded border border-border p-2">未采纳 <b>{precheck.no_accepted_count}</b></div>
                    <div className="rounded border border-border p-2">文件缺失 <b>{precheck.file_missing_count}</b></div>
                    <div className="rounded border border-border p-2">格式不支持 <b>{precheck.unsupported_count}</b></div>
                  </div>
                  <div className="space-y-1">
                    {(precheck.items ?? []).map((item) => (
                      <div key={item.shot_id} className="flex items-center gap-2">
                        {item.status === 'ok' ? (
                          <CheckCircle2 className="h-3 w-3 text-run-success" />
                        ) : (
                          <XCircle className="h-3 w-3 text-ready-blocked" />
                        )}
                        <span className="w-56 shrink-0 font-mono text-[10px]">{item.file_name}</span>
                        <span className="truncate text-muted-foreground">
                          {item.status === 'ok' ? `${item.duration}s` : item.error}
                        </span>
                      </div>
                    ))}
                  </div>
                  {(precheck.blockers ?? []).length ? (
                    <div className="rounded border border-ready-blocked/40 bg-ready-blocked/5 p-2 text-ready-blocked">
                      <p className="flex items-center gap-1 font-medium"><AlertTriangle className="h-3 w-3" />阻塞项</p>
                      {(precheck.blockers ?? []).slice(0, 8).map((blocker) => <p key={blocker}>· {blocker}</p>)}
                    </div>
                  ) : null}
                </div>
              ) : (
                <p className="text-muted-foreground">选择镜头后先预检查；预检查通常会确认已采纳文件、对象存储和 MP4 头。</p>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
