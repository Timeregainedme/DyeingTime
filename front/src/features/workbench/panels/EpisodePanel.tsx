/**
 * 剧集面板（P5）：场次 → 镜头。
 *
 * 正式场次来自 `scene_groups`；历史镜头没有场次时进入「未分配场次」。
 * P3 场次建议只作为导入草稿，用户确认后才创建正式场次。
 */
import { useEffect, useMemo, useState } from 'react'
import {
  ArrowDown,
  ArrowRight,
  ArrowUp,
  Clapperboard,
  ExternalLink,
  FolderPlus,
  Import,
  PlayCircle,
  RefreshCw,
} from 'lucide-react'
import type { ChapterRead, SceneGroupRead, ShotRead } from '../../../services/generated'
import { Button } from '../../../components/ui/button'
import { Card, CardContent } from '../../../components/ui/card'
import { Input } from '../../../components/ui/input'
import { cn } from '../../../lib/utils'
import { workbenchSceneGroupPath, workbenchShotPath } from '../routes'
import {
  useSceneGroupActions,
  useSceneGroupSuggestions,
  useWorkbenchRuntimeQueries,
  useWorkbenchSceneGroups,
  useWorkbenchShotQueries,
} from '../useWorkbenchQueries'
import { ChapterStatusBadge, PrepStatusBadge, RunStatusBadge } from '../components/StatusBadges'
import { LegacyLink, PanelHeader } from '../components/PanelHeader'
import { PanelEmpty, PanelError, PanelLoading, StageNote } from '../components/PanelStates'
import { legacyShotListPath, legacyStudioPath } from './legacyPaths'
import { ShotPlanWorkspace } from './ShotPlanWorkspace'
import { VideoBatchPanel } from './VideoBatchPanel'

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
        className="flex w-full items-center gap-3 px-3 py-2 text-left transition-colors hover:bg-accent"
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
  const groupsQuery = useWorkbenchSceneGroups(projectId, chapter.id)
  const suggestionsQuery = useSceneGroupSuggestions(projectId, chapter.id)
  const runtimeQuery = useWorkbenchRuntimeQueries(projectId, [chapter.id])
  const actions = useSceneGroupActions(projectId, chapter.id)
  const shots = shotsQuery[0]?.data
  const groups = useMemo(() => groupsQuery.data ?? [], [groupsQuery.data])
  const runtime = runtimeQuery[0]?.data
  const [showImport, setShowImport] = useState(false)
  const [importDrafts, setImportDrafts] = useState<
    Array<{ beat_key: string; title: string; location: string; time_of_day: string }>
  >([])
  const [notice, setNotice] = useState('')

  useEffect(() => {
    if (!showImport || !suggestionsQuery.data) return
    setImportDrafts(
      (suggestionsQuery.data.items ?? [])
        .filter((item) => !item.already_imported)
        .map((item) => ({
          beat_key: item.beat_key ?? '',
          title: item.title ?? '',
          location: item.location ?? '',
          time_of_day: item.time_of_day ?? '',
        })),
    )
  }, [showImport, suggestionsQuery.data])

  const loading = shotsQuery[0]?.isPending || groupsQuery.isLoading
  const error = shotsQuery[0]?.isError || groupsQuery.isError
  const activeTasksFor = (shotId: string) =>
    runtime?.find((item) => item.shot_id === shotId)?.active_task_count ?? 0

  const groupedShots = useMemo(() => {
    const map = new Map<string, ShotRead[]>()
    const unassigned: ShotRead[] = []
    const groupIds = new Set(groups.map((group) => group.id))
    for (const shot of [...(shots ?? [])].sort((a, b) => a.index - b.index)) {
      const groupId = shot.scene_group_id ?? ''
      if (!groupId || !groupIds.has(groupId)) unassigned.push(shot)
      else {
        const rows = map.get(groupId) ?? []
        rows.push(shot)
        map.set(groupId, rows)
      }
    }
    return { map, unassigned }
  }, [groups, shots])

  const readyCount = shots?.filter((shot) => shot.status === 'ready').length ?? 0
  const pendingCount = shots ? shots.length - readyCount : 0
  const runningCount = shots?.reduce((sum, shot) => sum + activeTasksFor(shot.id), 0) ?? 0

  const createGroup = () => {
    const index = groups.length + 1
    actions.create.mutate(
      { title: `场次 ${String(index).padStart(2, '0')}`, index },
      {
        onSuccess: (group) => onNavigate(workbenchSceneGroupPath(projectId, chapter.id, group.id)),
        onError: (error) => setNotice(error instanceof Error ? error.message : '创建场次失败'),
      },
    )
  }

  const reorderGroup = (group: SceneGroupRead, direction: -1 | 1) => {
    const rows = [...groups].sort((a, b) => a.index - b.index)
    const index = rows.findIndex((item) => item.id === group.id)
    const target = index + direction
    if (index < 0 || target < 0 || target >= rows.length) return
    ;[rows[index], rows[target]] = [rows[target], rows[index]]
    actions.reorder.mutate(
      rows.map((item) => item.id),
      { onError: (error) => setNotice(error instanceof Error ? error.message : '场次排序失败') },
    )
  }

  const applyImport = () => {
    if (!suggestionsQuery.data) return
    setNotice('')
    actions.importSuggestions.mutate(
      {
        parse_run_id: suggestionsQuery.data.parse_run_id,
        items: importDrafts.map((item) => ({
          beat_key: item.beat_key,
          title: item.title,
          location: item.location,
          time_of_day: item.time_of_day,
        })),
      },
      {
        onSuccess: (result) => {
          setShowImport(false)
          setNotice(`已创建 ${(result.created ?? []).length} 个场次，跳过 ${result.skipped ?? 0} 个已导入项`)
        },
        onError: (error) => setNotice(error instanceof Error ? error.message : '导入失败'),
      },
    )
  }

  return (
    <div className="space-y-4">
      <PanelHeader
        title={`第 ${chapter.index} 集 · ${chapter.title}`}
        description={chapter.summary || '本集场次与镜头'}
        badge={<ChapterStatusBadge status={chapter.status} />}
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void shotsQuery[0]?.refetch()}
              disabled={shotsQuery[0]?.isFetching}
            >
              <RefreshCw className={cn('h-3.5 w-3.5', shotsQuery[0]?.isFetching && 'animate-spin')} />
              刷新
            </Button>
            <Button variant="outline" size="sm" onClick={() => setShowImport((value) => !value)}>
              <Import className="h-3.5 w-3.5" />
              从 P3 场次建议导入
            </Button>
            <Button size="sm" onClick={createGroup} disabled={actions.create.isPending}>
              <FolderPlus className="h-3.5 w-3.5" />
              新增场次
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

      {notice ? (
        <div className="rounded-md border border-state-pending/40 bg-state-pending/10 p-2 text-[11px]">
          {notice}
        </div>
      ) : null}

      <StageNote stage="P5">
        场次是剧集内剧情分组；场景（Scene）是可复用资产。历史镜头没有场次时显示在「未分配场次」，不会被自动塞进虚构场次。
      </StageNote>

      {showImport ? (
        <Card>
          <CardContent className="space-y-2 p-3">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-medium">P3 场次建议</h3>
              {suggestionsQuery.data?.script_version_changed ? (
                <span className="text-[11px] text-state-pending">剧本版本已变化，规划可能过期</span>
              ) : null}
              <span className="text-[11px] text-muted-foreground">
                解析运行 {suggestionsQuery.data?.parse_run_id?.slice(0, 8) ?? '—'}
              </span>
            </div>
            {suggestionsQuery.isLoading ? (
              <PanelLoading lines={3} label="加载场次建议" />
            ) : suggestionsQuery.isError ? (
              <PanelError
                message={suggestionsQuery.error instanceof Error ? suggestionsQuery.error.message : '建议加载失败'}
                onRetry={() => void suggestionsQuery.refetch()}
              />
            ) : importDrafts.length === 0 ? (
              <p className="text-xs text-muted-foreground">没有可导入的新场次建议。</p>
            ) : (
              <>
                <div className="space-y-1">
                  {importDrafts.map((item, index) => (
                    <div key={item.beat_key} className="grid gap-1 rounded border border-border p-2 md:grid-cols-[1fr_180px_120px_auto]">
                      <Input
                        value={item.title}
                        onChange={(event) =>
                          setImportDrafts((prev) =>
                            prev.map((row, rowIndex) =>
                              rowIndex === index ? { ...row, title: event.target.value } : row,
                            ),
                          )
                        }
                        placeholder="场次标题"
                        className="h-7 text-xs"
                      />
                      <Input
                        value={item.location}
                        onChange={(event) =>
                          setImportDrafts((prev) =>
                            prev.map((row, rowIndex) =>
                              rowIndex === index ? { ...row, location: event.target.value } : row,
                            ),
                          )
                        }
                        placeholder="地点"
                        className="h-7 text-xs"
                      />
                      <Input
                        value={item.time_of_day}
                        onChange={(event) =>
                          setImportDrafts((prev) =>
                            prev.map((row, rowIndex) =>
                              rowIndex === index ? { ...row, time_of_day: event.target.value } : row,
                            ),
                          )
                        }
                        placeholder="时间"
                        className="h-7 text-xs"
                      />
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 px-2 text-[10px]"
                        onClick={() =>
                          setImportDrafts((prev) => prev.filter((_, rowIndex) => rowIndex !== index))
                        }
                      >
                        移除
                      </Button>
                    </div>
                  ))}
                </div>
                <div className="flex items-center gap-2">
                  <Button size="sm" onClick={applyImport} disabled={actions.importSuggestions.isPending}>
                    确认创建正式场次
                  </Button>
                  <span className="text-[10px] text-muted-foreground">
                    仅新建场次，不覆盖已有人工修改；同一解析结果重复导入会跳过。
                  </span>
                </div>
              </>
            )}
            {suggestionsQuery.data?.warnings?.length ? (
              <ul className="text-[10px] text-state-pending">
                {suggestionsQuery.data.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      <ShotPlanWorkspace
        projectId={projectId}
        chapter={chapter}
        sceneGroups={groups}
        existingShotCount={shots?.length ?? 0}
        onApplied={() => {
          void shotsQuery[0]?.refetch()
          void groupsQuery.refetch()
          setNotice('分镜规划已写入正式镜头；旧镜头与历史视频未被覆盖。')
        }}
      />

      <VideoBatchPanel projectId={projectId} chapterId={chapter.id} shots={shots ?? []} />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: '场次总数', value: groups.length },
          { label: '镜头总数', value: shots ? shots.length : '…' },
          { label: '待确认', value: shots ? pendingCount : '…' },
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

      {loading ? (
        <PanelLoading lines={5} label="加载场次与镜头" />
      ) : error ? (
        <PanelError
          message={
            (shotsQuery[0]?.error ?? groupsQuery.error) instanceof Error
              ? ((shotsQuery[0]?.error ?? groupsQuery.error) as Error).message
              : '加载失败'
          }
          onRetry={() => {
            void shotsQuery[0]?.refetch()
            void groupsQuery.refetch()
          }}
        />
      ) : groups.length === 0 && (!shots || shots.length === 0) ? (
        <PanelEmpty
          title="这一集还没有场次与镜头"
          description="可先导入 P3 场次建议，或手工新增场次；镜头规划在 P5 分镜规划中完成。"
          action={
            <Button size="sm" onClick={createGroup}>
              新增第一个场次
            </Button>
          }
        />
      ) : (
        <div className="space-y-3">
          {[...groups]
            .sort((a, b) => a.index - b.index)
            .map((group, groupIndex) => {
              const rows = groupedShots.map.get(group.id) ?? []
              return (
                <Card key={group.id}>
                  <CardContent className="space-y-2 p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <Clapperboard className="h-4 w-4 text-muted-foreground" />
                      <button
                        type="button"
                        className="text-left text-sm font-medium hover:text-primary"
                        onClick={() =>
                          onNavigate(workbenchSceneGroupPath(projectId, chapter.id, group.id))
                        }
                      >
                        场次 {String(group.index).padStart(2, '0')} · {group.title}
                      </button>
                      <span className="text-[11px] text-muted-foreground">
                        {[group.location, group.time_of_day].filter(Boolean).join(' · ')}
                      </span>
                      <span className="text-[10px] text-muted-foreground">
                        {group.shot_count} 镜 · {group.total_duration}s
                      </span>
                      <Button size="sm" variant="ghost" className="ml-auto h-6 w-6 p-0" disabled={groupIndex === 0} onClick={() => reorderGroup(group, -1)}>
                        <ArrowUp className="h-3 w-3" />
                      </Button>
                      <Button size="sm" variant="ghost" className="h-6 w-6 p-0" disabled={groupIndex === groups.length - 1} onClick={() => reorderGroup(group, 1)}>
                        <ArrowDown className="h-3 w-3" />
                      </Button>
                    </div>
                    {rows.length === 0 ? (
                      <p className="rounded bg-muted/40 px-2 py-2 text-[11px] text-muted-foreground">
                        场次暂无镜头。
                      </p>
                    ) : (
                      <ul className="divide-y divide-border rounded-md border border-border">
                        {rows.map((shot) => (
                          <ShotRow
                            key={shot.id}
                            shot={shot}
                            activeTasks={activeTasksFor(shot.id)}
                            onOpen={() => onNavigate(workbenchShotPath(projectId, chapter.id, shot.id))}
                          />
                        ))}
                      </ul>
                    )}
                  </CardContent>
                </Card>
              )
            })}

          {groupedShots.unassigned.length > 0 ? (
            <Card>
              <CardContent className="space-y-2 p-3">
                <div className="flex items-center gap-2">
                  <Clapperboard className="h-4 w-4 text-muted-foreground" />
                  <h3 className="text-sm font-medium">未分配场次</h3>
                  <span className="text-[10px] text-muted-foreground">
                    {groupedShots.unassigned.length} 个历史/待分配镜头
                  </span>
                </div>
                <ul className="divide-y divide-border rounded-md border border-border">
                  {groupedShots.unassigned.map((shot) => (
                    <ShotRow
                      key={shot.id}
                      shot={shot}
                      activeTasks={activeTasksFor(shot.id)}
                      onOpen={() => onNavigate(workbenchShotPath(projectId, chapter.id, shot.id))}
                    />
                  ))}
                </ul>
              </CardContent>
            </Card>
          ) : null}
        </div>
      )}
    </div>
  )
}
