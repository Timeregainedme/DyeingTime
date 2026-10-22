/**
 * 镜头面板。
 *
 * 这是工作台里唯一同时展示三类状态的页面，必须严格分开：
 *   1. 信息确认状态：`shot.status` + 准备聚合（pending_confirm_count 等）；
 *   2. 运行时任务：runtime summary 的 active_task_count；
 *   3. 视频生成准备度：video-readiness 的逐项检查。
 *
 * P1 只读展示，不提供生成、参考绑定或重抽；这些入口仍在旧版准备台与工作室。
 */
import { ArrowLeft, ExternalLink, PlayCircle, RefreshCw } from 'lucide-react'
import { Button } from '../../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card'
import { cn } from '../../../lib/utils'
import { workbenchEpisodePath } from '../routes'
import {
  useWorkbenchRuntimeQueries,
  useWorkbenchShot,
  useWorkbenchShotDetail,
  useWorkbenchShotPreparation,
  useWorkbenchShotReadiness,
} from '../useWorkbenchQueries'
import { InfoGrid } from '../components/InfoGrid'
import { LegacyLink, PanelHeader } from '../components/PanelHeader'
import {
  PanelEmpty,
  PanelError,
  PanelLoading,
  StageNote,
} from '../components/PanelStates'
import { PrepStatusBadge, ReadinessBadge, RunStatusBadge } from '../components/StatusBadges'
import { legacyShotEditPath, legacyStudioPath } from './legacyPaths'

export function ShotPanel({
  projectId,
  chapterId,
  shotId,
  onNavigate,
}: {
  projectId: string
  chapterId: string
  shotId: string
  onNavigate: (path: string) => void
}) {
  const shotQuery = useWorkbenchShot(projectId, shotId)
  const detailQuery = useWorkbenchShotDetail(projectId, shotId)
  const preparationQuery = useWorkbenchShotPreparation(projectId, shotId)
  const readinessQuery = useWorkbenchShotReadiness(projectId, shotId)
  const runtimeQuery = useWorkbenchRuntimeQueries(projectId, [chapterId])

  const shot = shotQuery.data
  const detail = detailQuery.data
  const preparation = preparationQuery.data
  const readiness = readinessQuery.data
  const activeTasks =
    runtimeQuery[0]?.data?.find((item) => item.shot_id === shotId)?.active_task_count ?? 0

  if (shotQuery.isLoading) return <PanelLoading lines={7} label="加载镜头" />
  if (shotQuery.isError) {
    return (
      <PanelError
        message={shotQuery.error instanceof Error ? shotQuery.error.message : '镜头加载失败'}
        onRetry={() => void shotQuery.refetch()}
      />
    )
  }
  if (!shot) {
    return (
      <PanelEmpty
        title="没有找到该镜头"
        description="镜头可能已被删除，或不属于当前剧集。"
        action={
          <Button size="sm" onClick={() => onNavigate(workbenchEpisodePath(projectId, chapterId))}>
            返回剧集
          </Button>
        }
      />
    )
  }

  const refreshAll = () => {
    void shotQuery.refetch()
    void detailQuery.refetch()
    void preparationQuery.refetch()
    void readinessQuery.refetch()
    void runtimeQuery[0]?.refetch()
  }
  const refreshing =
    shotQuery.isFetching ||
    detailQuery.isFetching ||
    preparationQuery.isFetching ||
    readinessQuery.isFetching

  return (
    <div className="space-y-4">
      <PanelHeader
        title={`镜头 ${String(shot.index).padStart(2, '0')} · ${shot.title}`}
        description={shot.script_excerpt || '暂无剧本摘录'}
        badge={
          <span className="flex flex-wrap items-center gap-1.5">
            <PrepStatusBadge status={shot.status} />
            <RunStatusBadge activeTasks={activeTasks} />
            <ReadinessBadge ready={readiness?.ready} checks={readiness?.checks} />
          </span>
        }
        actions={
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onNavigate(workbenchEpisodePath(projectId, chapterId))}
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              返回剧集
            </Button>
            <Button variant="outline" size="sm" onClick={refreshAll} disabled={refreshing}>
              <RefreshCw className={cn('h-3.5 w-3.5', refreshing && 'animate-spin')} />
              刷新状态
            </Button>
            <LegacyLink href={legacyShotEditPath(projectId, chapterId, shotId)}>
              <ExternalLink className="h-3.5 w-3.5" />
              旧版镜头准备台
            </LegacyLink>
            <LegacyLink href={legacyStudioPath(projectId, chapterId)}>
              <PlayCircle className="h-3.5 w-3.5" />
              生成工作室
            </LegacyLink>
          </>
        }
      />

      <StageNote stage="P6">
        参考绑定、H3 提示词预览、批量生成与抽卡审核将在 P6 提供。当前生成仍走旧版工作室。
      </StageNote>

      <div className="grid gap-3 xl:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">信息确认状态</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <PrepStatusBadge status={shot.status} />
            <InfoGrid
              items={[
                { label: '待确认项', value: preparation?.pending_confirm_count ?? '—' },
                { label: '可进入生成', value: preparation?.ready_for_generation ? '是' : '否' },
                { label: '基础信息', value: preparation?.basic_info_ready ? '已齐' : '未齐' },
                { label: '镜头语言', value: preparation?.semantic_defaults_ready ? '已确认' : '未确认' },
                { label: '动作拍点', value: preparation?.action_beats_ready ? '已确认' : '未确认' },
              ]}
            />
            {preparationQuery.isError ? (
              <p className="text-[11px] text-destructive">准备状态读取失败，请刷新重试。</p>
            ) : null}
            <p className="text-[10px] leading-4 text-muted-foreground">
              `shot.status` 只表示信息提取确认状态，不代表任务是否在运行。
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">运行时任务</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <RunStatusBadge activeTasks={activeTasks} />
            <InfoGrid
              items={[
                { label: '活跃任务数', value: activeTasks },
                { label: '任务来源', value: 'GenerationTask / runtime summary' },
              ]}
            />
            <p className="text-[10px] leading-4 text-muted-foreground">
              运行中不会写回 `shot.status`；任务结束后由任务系统更新状态。
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">视频生成准备度</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <ReadinessBadge ready={readiness?.ready} checks={readiness?.checks} />
            {readinessQuery.isLoading ? (
              <p className="text-[11px] text-muted-foreground">正在读取准备度…</p>
            ) : readinessQuery.isError ? (
              <p className="text-[11px] text-destructive">准备度读取失败，请刷新重试。</p>
            ) : readiness?.checks?.length ? (
              <ul className="space-y-1 text-[11px] leading-4">
                {readiness.checks
                  .filter((check) => !check.ok)
                  .slice(0, 6)
                  .map((check) => (
                    <li key={check.key} className="text-muted-foreground">
                      <span className="mr-1 text-ready-blocked">×</span>
                      {check.message}
                    </li>
                  ))}
                {readiness.checks.every((check) => check.ok) ? (
                  <li className="text-ready-complete">全部检查通过。</li>
                ) : null}
              </ul>
            ) : (
              <p className="text-[11px] text-muted-foreground">暂无检查结果。</p>
            )}
            <p className="text-[10px] leading-4 text-muted-foreground">
              按 `reference` 参考模式检查；准备度与 `shot.status` 是两套语义。
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">镜头信息</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <InfoGrid
            items={[
              { label: '时长', value: detail ? `${detail.duration ?? 0}s` : '—' },
              { label: '景别', value: detail?.camera_shot ?? '—' },
              { label: '机位角度', value: detail?.angle ?? '—' },
              { label: '运镜', value: detail?.movement ?? '—' },
              { label: '氛围', value: detail?.atmosphere || '—' },
              { label: '视效', value: detail?.vfx_note || detail?.vfx_type || '—' },
            ]}
          />

          {detail?.action_beats?.length ? (
            <div>
              <h4 className="mb-1 text-xs font-medium">动作拍点</h4>
              <ol className="list-decimal space-y-0.5 pl-5 text-xs text-muted-foreground">
                {detail.action_beats.map((beat, index) => (
                  <li key={`${index}-${beat}`}>{beat}</li>
                ))}
              </ol>
            </div>
          ) : null}

          <div>
            <h4 className="mb-1 text-xs font-medium">剧本摘录</h4>
            <p className="whitespace-pre-wrap rounded-md bg-muted/40 p-2 text-xs leading-5">
              {shot.script_excerpt || '暂无摘录'}
            </p>
          </div>

          {preparation?.saved_dialogue_lines?.length ? (
            <div>
              <h4 className="mb-1 text-xs font-medium">已确认对白</h4>
              <ul className="space-y-1 text-xs">
                {preparation.saved_dialogue_lines.map((line) => (
                  <li key={line.id} className="flex gap-2">
                    <span className="shrink-0 text-muted-foreground">
                      {line.speaker_name || '角色'}：
                    </span>
                    <span>{line.text}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}
