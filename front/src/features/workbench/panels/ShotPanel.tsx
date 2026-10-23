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
import { useEffect, useState } from 'react'
import { ArrowLeft, ExternalLink, PlayCircle, RefreshCw } from 'lucide-react'
import { Button } from '../../../components/ui/button'
import { Input } from '../../../components/ui/input'
import { Select } from '../../../components/ui/select'
import { Textarea } from '../../../components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card'
import { cn } from '../../../lib/utils'
import { workbenchEpisodePath } from '../routes'
import {
  useShotAssetVersions,
  useShotEditActions,
  useWorkbenchRuntimeQueries,
  useWorkbenchSceneGroups,
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
import { ShotReferencePanel } from './ShotReferencePanel'

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
  const groupsQuery = useWorkbenchSceneGroups(projectId, chapterId)
  const assetVersionsQuery = useShotAssetVersions(projectId, shotId)
  const editActions = useShotEditActions(projectId, chapterId, shotId)
  const [notice, setNotice] = useState('')
  const [form, setForm] = useState({
    title: '',
    script_excerpt: '',
    scene_group_id: '',
    duration: '4',
    camera_shot: 'MS',
    angle: 'EYE_LEVEL',
    movement: 'STATIC',
    description: '',
    action_beats: '',
    video_prompt_draft: '',
  })

  const shot = shotQuery.data
  const detail = detailQuery.data
  const preparation = preparationQuery.data
  const readiness = readinessQuery.data
  const activeTasks =
    runtimeQuery[0]?.data?.find((item) => item.shot_id === shotId)?.active_task_count ?? 0

  useEffect(() => {
    if (!shot) return
    setForm({
      title: shot.title ?? '',
      script_excerpt: shot.script_excerpt ?? '',
      scene_group_id: shot.scene_group_id ?? '',
      duration: String(detail?.duration ?? 4),
      camera_shot: detail?.camera_shot ?? 'MS',
      angle: detail?.angle ?? 'EYE_LEVEL',
      movement: detail?.movement ?? 'STATIC',
      description: detail?.description ?? '',
      action_beats: (detail?.action_beats ?? []).join('\n'),
      video_prompt_draft: detail?.video_prompt_draft ?? '',
    })
    // 只在镜头/详情数据变化时回填，避免覆盖用户正在编辑的草稿。
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shot?.id, shot?.title, shot?.script_excerpt, shot?.scene_group_id, detail?.duration, detail?.camera_shot, detail?.angle, detail?.movement, detail?.description, detail?.action_beats, detail?.video_prompt_draft])

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

  const saveShot = async () => {
    setNotice('')
    try {
      await editActions.updateShot.mutateAsync({
        title: form.title,
        script_excerpt: form.script_excerpt,
        scene_group_id: form.scene_group_id || null,
      })
      await editActions.updateDetail.mutateAsync({
        duration: Number(form.duration) || 0,
        camera_shot: form.camera_shot as never,
        angle: form.angle as never,
        movement: form.movement as never,
        description: form.description,
        action_beats: form.action_beats.split('\n').map((item) => item.trim()).filter(Boolean),
        video_prompt_draft: form.video_prompt_draft,
      })
      setNotice('镜头已保存；资产版本与历史视频未被覆盖。')
    } catch (error) {
      setNotice(error instanceof Error ? error.message : '保存失败')
    }
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
        参考绑定、H3 提示词预览、批量生成与抽卡审核将在 P6 提供。P5 已支持镜头文字、时长、场次与资产版本选择。
      </StageNote>

      {notice ? <p className="rounded border border-state-pending/40 bg-state-pending/10 p-2 text-[11px]">{notice}</p> : null}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">镜头编辑</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="grid gap-2 md:grid-cols-2">
            <div className="space-y-1">
              <label className="text-[11px] text-muted-foreground">标题</label>
              <Input value={form.title} onChange={(event) => setForm((prev) => ({ ...prev, title: event.target.value }))} className="h-8 text-xs" />
            </div>
            <div className="space-y-1">
              <label className="text-[11px] text-muted-foreground">所属场次</label>
              <Select value={form.scene_group_id} onChange={(event) => setForm((prev) => ({ ...prev, scene_group_id: event.target.value }))} className="h-8 text-xs">
                <option value="">未分配场次</option>
                {(groupsQuery.data ?? []).map((group) => (
                  <option key={group.id} value={group.id}>场次 {group.index} · {group.title}</option>
                ))}
              </Select>
            </div>
            <div className="space-y-1">
              <label className="text-[11px] text-muted-foreground">时长（秒）</label>
              <Input type="number" min={1} value={form.duration} onChange={(event) => setForm((prev) => ({ ...prev, duration: event.target.value }))} className="h-8 text-xs" />
            </div>
            <div className="grid grid-cols-3 gap-1">
              <div className="space-y-1">
                <label className="text-[10px] text-muted-foreground">景别</label>
                <Input value={form.camera_shot} onChange={(event) => setForm((prev) => ({ ...prev, camera_shot: event.target.value }))} className="h-8 text-xs" />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] text-muted-foreground">角度</label>
                <Input value={form.angle} onChange={(event) => setForm((prev) => ({ ...prev, angle: event.target.value }))} className="h-8 text-xs" />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] text-muted-foreground">运镜</label>
                <Input value={form.movement} onChange={(event) => setForm((prev) => ({ ...prev, movement: event.target.value }))} className="h-8 text-xs" />
              </div>
            </div>
          </div>
          <Textarea value={form.script_excerpt} rows={2} onChange={(event) => setForm((prev) => ({ ...prev, script_excerpt: event.target.value }))} placeholder="剧本摘录" className="text-xs" />
          <Textarea value={form.description} rows={2} onChange={(event) => setForm((prev) => ({ ...prev, description: event.target.value }))} placeholder="视觉/动作描述" className="text-xs" />
          <Textarea value={form.action_beats} rows={2} onChange={(event) => setForm((prev) => ({ ...prev, action_beats: event.target.value }))} placeholder="动作拍点，每行一个" className="text-xs" />
          <Textarea value={form.video_prompt_draft} rows={2} onChange={(event) => setForm((prev) => ({ ...prev, video_prompt_draft: event.target.value }))} placeholder="自然语言视频提示词草稿" className="text-xs" />
          <div className="flex flex-wrap items-center gap-2">
            <Button size="sm" className="h-7 px-2 text-[11px]" onClick={() => void saveShot()} disabled={editActions.updateShot.isPending || editActions.updateDetail.isPending}>
              保存镜头
            </Button>
            <span className="text-[10px] text-muted-foreground">时长需落在项目有效业务范围；保存不会改写历史视频。</span>
          </div>
          <div className="rounded border border-border bg-muted/20 p-2 text-[10px]">
            <p className="mb-1 font-medium">镜头资产版本选择（P5）</p>
            {assetVersionsQuery.data?.length ? (
              <ul className="space-y-0.5">
                {assetVersionsQuery.data.map((item) => (
                  <li key={`${item.asset_type}-${item.asset_id}-${item.role}`} className="text-muted-foreground">
                    {item.role} · {item.asset_id.slice(0, 12)} · 版本 {item.asset_version_id?.slice(0, 12) ?? '当前/未指定'}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-muted-foreground">暂无镜头级资产版本；可在分镜规划中确认，或由旧版资产链路回退读取当前版本。</p>
            )}
          </div>
        </CardContent>
      </Card>

      <ShotReferencePanel projectId={projectId} shotId={shotId} />

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
