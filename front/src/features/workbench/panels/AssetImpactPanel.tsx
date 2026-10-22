/**
 * P4 / C8：资产引用与受影响镜头提示。
 *
 * 只展示数据库/文本分析结果；不触发重拍、不删除视频、不改写镜头。
 */
import { AlertTriangle, Film, RefreshCw } from 'lucide-react'
import { Badge } from '../../../components/ui/badge'
import { Button } from '../../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card'
import { ScrollArea } from '../../../components/ui/scroll-area'
import type { AssetImpactShot } from '../../../services/generated'
import type { WorkbenchAssetType } from '../routes'
import { useAssetImpact } from '../useWorkbenchQueries'
import { PanelError, PanelLoading } from '../components/PanelStates'

function certaintyBadge(shot: AssetImpactShot) {
  if (shot.certainty === 'explicit') {
    return <Badge variant="secondary">确定资产引用</Badge>
  }
  return (
    <Badge variant="outline" className="border-state-pending/40 text-state-pending">
      可能影响
    </Badge>
  )
}

export function AssetImpactPanel({
  projectId,
  assetType,
  assetId,
}: {
  projectId: string
  assetType: WorkbenchAssetType
  assetId: string
}) {
  const query = useAssetImpact(projectId, assetType, assetId)
  if (query.isLoading) return <PanelLoading lines={3} label="分析资产引用" />
  if (query.isError) {
    return (
      <PanelError
        message={query.error instanceof Error ? query.error.message : '影响分析失败'}
        onRetry={() => void query.refetch()}
      />
    )
  }
  const data = query.data
  if (!data) return null
  const summary = data.summary ?? {}
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
            引用与受影响镜头
          </CardTitle>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 px-2 text-[11px]"
            onClick={() => void query.refetch()}
            disabled={query.isFetching}
          >
            <RefreshCw className={query.isFetching ? 'h-3 w-3 animate-spin' : 'h-3 w-3'} />
            刷新分析
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap gap-2 text-[11px]">
          <Badge variant="outline">章节 {String(summary.chapter_count ?? 0)}</Badge>
          <Badge variant="outline">镜头 {String(summary.shot_count ?? 0)}</Badge>
          <Badge variant="secondary">确定引用 {String(summary.explicit_count ?? 0)}</Badge>
          <Badge variant="outline" className="border-state-pending/40 text-state-pending">
            可能影响 {String(summary.possible_count ?? 0)}
          </Badge>
          <Badge variant="outline" className="font-normal">
            <Film className="mr-1 h-3 w-3" />
            已有视频 {String(summary.video_count ?? 0)}
          </Badge>
          <Badge variant="outline" className="font-normal">
            版本精度：{String(summary.version_precision ?? 'asset_level')}
          </Badge>
        </div>

        {data.chapters?.length ? (
          <div className="flex flex-wrap gap-1 text-[11px]">
            {(data.chapters as Array<Record<string, unknown>>).map((chapter) => (
              <span key={String(chapter.chapter_id)} className="rounded border border-border px-2 py-0.5">
                第{String(chapter.index ?? '—')}集 · {String(chapter.shot_count ?? 0)} 镜
                {Number(chapter.video_count ?? 0) > 0 ? ` · ${String(chapter.video_count)} 个视频` : ''}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-[11px] text-muted-foreground">当前没有查询到关联镜头。</p>
        )}

        {data.shots?.length ? (
          <ScrollArea className="max-h-64 pr-1">
            <div className="space-y-1">
              {data.shots.map((shot) => (
                <div
                  key={shot.shot_id}
                  className="flex flex-wrap items-center gap-2 rounded-md border border-border px-2 py-1.5 text-[11px]"
                >
                  <span className="min-w-0 flex-1 truncate">
                    第{shot.chapter_index ?? '—'}集 / 第{shot.shot_index ?? '—'}镜 ·{' '}
                    {shot.shot_title || shot.shot_id}
                  </span>
                  {certaintyBadge(shot)}
                  <span className="text-[10px] text-muted-foreground">{shot.reference_kind}</span>
                  {shot.has_video ? (
                    <Badge variant="outline" className="font-normal">
                      已有视频
                    </Badge>
                  ) : null}
                </div>
              ))}
            </div>
          </ScrollArea>
        ) : null}

        <div className="space-y-1 rounded-md border border-border bg-muted/20 p-2 text-[10px] text-muted-foreground">
          {(data.notes ?? []).map((note) => (
            <p key={note}>{note}</p>
          ))}
          <p>版本切换不会自动重拍或删除现有视频；如需更新请人工发起新的生成任务。</p>
        </div>
      </CardContent>
    </Card>
  )
}
