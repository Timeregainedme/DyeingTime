/**
 * 剧集面板。
 *
 * 当前层级事实：剧集（Chapter）直接包含镜头，没有场次实体。
 * 因此这里展示的是「本集概览 + 镜头清单」，不会渲染虚构的场次分组；
 * P5 引入场次后，镜头清单会按场次分组。
 */
import { ArrowRight, Clapperboard, ExternalLink, PlayCircle, RefreshCw } from 'lucide-react'
import type { ChapterRead, ShotRead } from '../../../services/generated'
import { Button } from '../../../components/ui/button'
import { Card, CardContent } from '../../../components/ui/card'
import { cn } from '../../../lib/utils'
import { workbenchShotPath } from '../routes'
import { useWorkbenchRuntimeQueries, useWorkbenchShotQueries } from '../useWorkbenchQueries'
import { ChapterStatusBadge, PrepStatusBadge, RunStatusBadge } from '../components/StatusBadges'
import { LegacyLink, PanelHeader } from '../components/PanelHeader'
import { PanelEmpty, PanelError, PanelLoading, StageNote } from '../components/PanelStates'
import { legacyShotListPath, legacyStudioPath } from './legacyPaths'

function ShotRow({
  shot,
  activeTasks,
  onOpen,
}: {
  shot: ShotRead
  activeTasks: number
  onOpen: () => void
}) {
  return (
    <li>
      <button
        type="button"
        className="flex w-full items-center gap-3 px-3 py-2.5 text-left transition-colors hover:bg-accent"
        onClick={onOpen}
      >
        <span className="w-16 shrink-0 text-[11px] tabular-nums text-muted-foreground">
          镜头 {String(shot.index).padStart(2, '0')}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm">{shot.title}</span>
          <span className="block truncate text-[11px] text-muted-foreground">
            {shot.script_excerpt || '暂无剧本摘录'}
          </span>
        </span>
        <span className="flex shrink-0 items-center gap-1.5">
          <PrepStatusBadge status={shot.status} />
          <RunStatusBadge activeTasks={activeTasks} />
        </span>
        <ArrowRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
      </button>
    </li>
  )
}

export function EpisodePanel({
  projectId,
  chapter,
  onNavigate,
}: {
  projectId: string
  chapter: ChapterRead
  onNavigate: (path: string) => void
}) {
  const shotsQuery = useWorkbenchShotQueries(projectId, [chapter.id])
  const runtimeQuery = useWorkbenchRuntimeQueries(projectId, [chapter.id])
  const shots = shotsQuery[0]?.data
  const runtime = runtimeQuery[0]?.data

  const loading = shotsQuery[0]?.isPending
  const error = shotsQuery[0]?.isError
  const activeTasksFor = (shotId: string) =>
    runtime?.find((item) => item.shot_id === shotId)?.active_task_count ?? 0

  const readyCount = shots?.filter((shot) => shot.status === 'ready').length ?? 0
  const pendingCount = shots ? shots.length - readyCount : 0
  const runningCount = shots?.reduce((sum, shot) => sum + activeTasksFor(shot.id), 0) ?? 0

  return (
    <div className="space-y-4">
      <PanelHeader
        title={`第 ${chapter.index} 集 · ${chapter.title}`}
        description={chapter.summary || '本集暂无摘要'}
        badge={<ChapterStatusBadge status={chapter.status} />}
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void shotsQuery[0]?.refetch()}
              disabled={shotsQuery[0]?.isFetching}
            >
              <RefreshCw
                className={cn('h-3.5 w-3.5', shotsQuery[0]?.isFetching && 'animate-spin')}
              />
              刷新
            </Button>
            <LegacyLink href={legacyShotListPath(projectId, chapter.id)}>
              <ExternalLink className="h-3.5 w-3.5" />
              旧版分镜列表
            </LegacyLink>
            <LegacyLink href={legacyStudioPath(projectId, chapter.id)}>
              <PlayCircle className="h-3.5 w-3.5" />
              生成工作室
            </LegacyLink>
          </>
        }
      />

      <StageNote stage="P5">
        场次（剧集内的剧情分组）将在 P5 落地。当前剧集直接包含镜头；场次与场景资产是两个不同概念，后续也不会共用一个实体。
      </StageNote>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: '镜头总数', value: shots ? shots.length : '…' },
          { label: '待确认', value: shots ? pendingCount : '…' },
          { label: '已确认', value: shots ? readyCount : '…' },
          { label: '运行中任务', value: shots ? runningCount : '…' },
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
        <CardContent className="p-3">
          <div className="mb-2 flex items-center gap-2">
            <Clapperboard className="h-4 w-4 text-muted-foreground" />
            <h3 className="text-sm font-medium">镜头清单</h3>
            <span className="text-[11px] text-muted-foreground">
              信息确认状态来自 shot.status；运行中来自任务系统
            </span>
          </div>

          {loading ? (
            <PanelLoading lines={5} label="加载镜头" />
          ) : error ? (
            <PanelError
              message={
                shotsQuery[0]?.error instanceof Error
                  ? shotsQuery[0].error.message
                  : '镜头加载失败'
              }
              onRetry={() => void shotsQuery[0]?.refetch()}
            />
          ) : !shots || shots.length === 0 ? (
            <PanelEmpty
              title="这一集还没有镜头"
              description="分镜提取仍在旧版分镜列表页完成；提取后刷新本节点即可看到镜头。"
              action={
                <LegacyLink href={legacyShotListPath(projectId, chapter.id)}>
                  去旧版提取分镜
                </LegacyLink>
              }
            />
          ) : (
            <ul className="divide-y divide-border rounded-md border border-border">
              {[...shots]
                .sort((a, b) => a.index - b.index)
                .map((shot) => (
                  <ShotRow
                    key={shot.id}
                    shot={shot}
                    activeTasks={activeTasksFor(shot.id)}
                    onOpen={() =>
                      onNavigate(workbenchShotPath(projectId, chapter.id, shot.id))
                    }
                  />
                ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
