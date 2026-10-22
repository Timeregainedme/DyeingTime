/**
 * 导出面板。
 *
 * P1 复用现有导出入口：旧版编辑器负责成片拼装与片段打包。
 * 按镜头选择导出、`E01_SC02_SH003.mp4` 命名属于 P7；
 * 这里只展示真实的时间线统计，不提供「看起来能导出」的占位按钮。
 */
import { Download, ExternalLink, Film, RefreshCw } from 'lucide-react'
import { Button } from '../../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card'
import { cn } from '../../../lib/utils'
import { useWorkbenchTimeline } from '../useWorkbenchQueries'
import { LegacyLink, PanelHeader } from '../components/PanelHeader'
import { PanelEmpty, PanelError, PanelLoading, StageNote } from '../components/PanelStates'
import { legacyChapterListPath, legacyEditorPath } from './legacyPaths'

export function ExportPanel({ projectId }: { projectId: string }) {
  const timelineQuery = useWorkbenchTimeline(projectId)

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

  const timeline = timelineQuery.data
  const stats = timeline?.stats
  const clips = timeline?.clips ?? []

  return (
    <div className="space-y-4">
      <PanelHeader
        title="导出"
        description="按镜头顺序拼装成片，或把已生成片段原样打包。"
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
              旧版导出与成片
            </LegacyLink>
          </>
        }
      />

      <StageNote stage="P7">
        选择镜头、按剧集/场次筛选与 `E01_SC02_SH003.mp4` 规范命名将在 P7 提供。当前导出在旧版编辑器完成。
      </StageNote>

      {!timeline || clips.length === 0 ? (
        <PanelEmpty
          title="还没有可导出的镜头"
          description="先在生成工作室产出并采纳视频，时间线才会出现片段。"
          action={
            <LegacyLink href={legacyChapterListPath(projectId)}>
              去旧版选择剧集
            </LegacyLink>
          }
        />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 2xl:grid-cols-6">
            {[
              { label: '片段总数', value: stats?.clip_count ?? clips.length },
              { label: '已有视频', value: stats?.clips_with_video ?? '—' },
              { label: '缺少视频', value: stats?.clips_missing_video ?? '—' },
              { label: '带配音', value: stats?.clips_with_audio ?? '—' },
              { label: '总时长', value: `${Math.round(stats?.total_duration ?? 0)}s` },
              { label: '可导出成片', value: stats?.exportable ? '是' : '否' },
            ].map((item) => (
              <Card key={item.label}>
                <CardContent className="p-3">
                  <p className="text-[11px] text-muted-foreground">{item.label}</p>
                  <p className="text-lg font-semibold leading-tight">{item.value}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Film className="h-4 w-4 text-muted-foreground" />
                片段顺序（按剧集 / 镜头）
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ol className="max-h-[50vh] divide-y divide-border overflow-auto rounded-md border border-border">
                {[...clips]
                  .sort((a, b) =>
                    a.chapter_index === b.chapter_index
                      ? a.index - b.index
                      : a.chapter_index - b.chapter_index,
                  )
                  .map((clip) => (
                    <li
                      key={`${clip.chapter_id}-${clip.shot_id}`}
                      className="flex items-center gap-3 px-3 py-2 text-xs"
                    >
                      <span className="w-24 shrink-0 tabular-nums text-muted-foreground">
                        E{String(clip.chapter_index).padStart(2, '0')} · SH
                        {String(clip.index).padStart(3, '0')}
                      </span>
                      <span className="min-w-0 flex-1 truncate">{clip.title}</span>
                      <span className="w-12 shrink-0 text-right tabular-nums text-muted-foreground">
                        {clip.duration ?? 0}s
                      </span>
                      <span
                        className={cn(
                          'w-16 shrink-0 text-right',
                          clip.video_file_id
                            ? 'text-run-success'
                            : 'text-muted-foreground',
                        )}
                      >
                        {clip.video_file_id ? '有视频' : '缺视频'}
                      </span>
                    </li>
                  ))}
              </ol>
              <p className="mt-2 flex items-center gap-1.5 text-[10px] leading-4 text-muted-foreground">
                <Download className="h-3 w-3" />
                导出下载入口在旧版编辑器；P7 会迁移为工作台内的选择式导出。
              </p>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
