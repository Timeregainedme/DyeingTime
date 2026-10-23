/**
 * P5 场次编辑面板。
 *
 * 场次是剧集内剧情分组；主场景只是被引用的 Scene 资产，两者不合并。
 */
import { useEffect, useMemo, useState } from 'react'
import { ArrowDown, ArrowLeft, ArrowUp, ExternalLink, RefreshCw, Trash2 } from 'lucide-react'
import { Badge } from '../../../components/ui/badge'
import { Button } from '../../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card'
import { Input } from '../../../components/ui/input'
import { Select } from '../../../components/ui/select'
import { Textarea } from '../../../components/ui/textarea'
import type { ShotRead } from '../../../services/generated'
import {
  workbenchEpisodePath,
  workbenchShotPath,
} from '../routes'
import {
  useWorkbenchGlobalAssets,
  useWorkbenchSceneGroup,
  useWorkbenchSceneGroups,
  useWorkbenchShotQueries,
  useSceneGroupActions,
} from '../useWorkbenchQueries'
import { LegacyLink, PanelHeader } from '../components/PanelHeader'
import { PanelEmpty, PanelError, PanelLoading } from '../components/PanelStates'
import { PrepStatusBadge } from '../components/StatusBadges'
import { legacyShotEditPath } from './legacyPaths'

function Field({
  label,
  value,
  onChange,
  multiline,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  multiline?: boolean
}) {
  return (
    <div className="space-y-1">
      <label className="text-[11px] text-muted-foreground">{label}</label>
      {multiline ? (
        <Textarea value={value} rows={2} onChange={(event) => onChange(event.target.value)} />
      ) : (
        <Input value={value} onChange={(event) => onChange(event.target.value)} />
      )}
    </div>
  )
}

export function SceneGroupPanel({
  projectId,
  chapterId,
  sceneGroupId,
  onNavigate,
}: {
  projectId: string
  chapterId: string
  sceneGroupId: string
  onNavigate: (path: string) => void
}) {
  const groupQuery = useWorkbenchSceneGroup(projectId, chapterId, sceneGroupId)
  const groupsQuery = useWorkbenchSceneGroups(projectId, chapterId)
  const shotsQuery = useWorkbenchShotQueries(projectId, [chapterId])
  const scenesQuery = useWorkbenchGlobalAssets(projectId, 'scene')
  const actions = useSceneGroupActions(projectId, chapterId)
  const [form, setForm] = useState({
    title: '',
    description: '',
    location: '',
    time_of_day: '',
    story_event: '',
    primary_scene_id: '',
  })
  const [notice, setNotice] = useState('')
  const group = groupQuery.data
  const allShots = useMemo(() => shotsQuery[0]?.data ?? [], [shotsQuery])
  const groupShots = useMemo(
    () =>
      [...allShots]
        .filter((shot) => shot.scene_group_id === sceneGroupId)
        .sort((a, b) => a.index - b.index),
    [allShots, sceneGroupId],
  )

  useEffect(() => {
    if (!group) return
    setForm({
      title: group.title ?? '',
      description: group.description ?? '',
      location: group.location ?? '',
      time_of_day: group.time_of_day ?? '',
      story_event: group.story_event ?? '',
      primary_scene_id: group.primary_scene_id ?? '',
    })
  // 只依赖实际字段，避免轮询对象引用变化覆盖正在编辑的草稿。
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [group?.id, group?.title, group?.description, group?.location, group?.time_of_day, group?.story_event, group?.primary_scene_id])

  if (groupQuery.isLoading || shotsQuery[0]?.isLoading) {
    return <PanelLoading lines={7} label="加载场次" />
  }
  if (groupQuery.isError || !group) {
    return (
      <PanelError
        message={groupQuery.error instanceof Error ? groupQuery.error.message : '场次不存在'}
        onRetry={() => void groupQuery.refetch()}
      />
    )
  }

  const save = () => {
    setNotice('')
    actions.update.mutate(
      {
        groupId: sceneGroupId,
        body: {
          ...form,
          primary_scene_id: form.primary_scene_id || null,
        },
      },
      {
        onSuccess: () => setNotice('场次已保存'),
        onError: (error) => setNotice(error instanceof Error ? error.message : '保存失败'),
      },
    )
  }

  const reorderFromGroup = (next: ShotRead[]) => {
    const byShotId = new Map(next.map((shot) => [shot.id, shot]))
    const ordered = allShots.map((shot) => {
      const current = byShotId.get(shot.id) ?? shot
      return {
        shot_id: current.id,
        scene_group_id: current.scene_group_id ?? null,
      }
    })
    actions.reorderShots.mutate(ordered, {
      onError: (error) => setNotice(error instanceof Error ? error.message : '镜头排序失败'),
    })
  }

  const moveShot = (shot: ShotRead, direction: -1 | 1) => {
    const rows = [...groupShots]
    const index = rows.findIndex((item) => item.id === shot.id)
    const target = index + direction
    if (index < 0 || target < 0 || target >= rows.length) return
    ;[rows[index], rows[target]] = [rows[target], rows[index]]
    // 把本场次镜头按新顺序放回章节全局顺序中的原位置。
    const positions = allShots
      .map((item, position) => (item.scene_group_id === sceneGroupId ? position : -1))
      .filter((position) => position >= 0)
    const ordered = [...allShots]
    positions.forEach((position, rowIndex) => {
      ordered[position] = rows[rowIndex]
    })
    reorderFromGroup(ordered)
  }

  const moveToGroup = (shot: ShotRead, targetGroupId: string) => {
    const next = allShots.map((item) => ({
      shot_id: item.id,
      scene_group_id:
        item.id === shot.id ? (targetGroupId || null) : item.scene_group_id ?? null,
    }))
    const ordered = [
      ...next.filter((item) => item.shot_id !== shot.id),
      ...next.filter((item) => item.shot_id === shot.id),
    ]
    actions.reorderShots.mutate(ordered, {
      onError: (error) => setNotice(error instanceof Error ? error.message : '移动镜头失败'),
    })
  }

  return (
    <div className="space-y-4">
      <PanelHeader
        title={`场次 ${String(group.index).padStart(2, '0')} · ${group.title}`}
        description={[group.location, group.time_of_day].filter(Boolean).join(' · ') || '场次编辑'}
        badge={<Badge variant="outline">{group.shot_count} 镜 · {group.total_duration}s</Badge>}
        actions={
          <>
            <Button variant="ghost" size="sm" onClick={() => onNavigate(workbenchEpisodePath(projectId, chapterId))}>
              <ArrowLeft className="h-3.5 w-3.5" />
              返回剧集
            </Button>
            <Button variant="outline" size="sm" onClick={() => void groupQuery.refetch()}>
              <RefreshCw className="h-3.5 w-3.5" />
              刷新
            </Button>
          </>
        }
      />
      {notice ? <p className="rounded border border-state-pending/40 bg-state-pending/10 p-2 text-[11px]">{notice}</p> : null}

      <div className="grid gap-3 xl:grid-cols-[360px_1fr]">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">场次信息</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            <Field label="标题" value={form.title} onChange={(value) => setForm((prev) => ({ ...prev, title: value }))} />
            <div className="grid grid-cols-2 gap-2">
              <Field label="地点" value={form.location} onChange={(value) => setForm((prev) => ({ ...prev, location: value }))} />
              <Field label="时间" value={form.time_of_day} onChange={(value) => setForm((prev) => ({ ...prev, time_of_day: value }))} />
            </div>
            <div className="space-y-1">
              <label className="text-[11px] text-muted-foreground">主场景资产</label>
              <Select
                value={form.primary_scene_id}
                onChange={(event) => setForm((prev) => ({ ...prev, primary_scene_id: event.target.value }))}
              >
                <option value="">未指定</option>
                {(scenesQuery.data ?? []).map((item) => (
                  <option key={item.id} value={item.id}>{item.name}</option>
                ))}
              </Select>
            </div>
            <Field label="剧情摘要" value={form.story_event} onChange={(value) => setForm((prev) => ({ ...prev, story_event: value }))} multiline />
            <Field label="描述" value={form.description} onChange={(value) => setForm((prev) => ({ ...prev, description: value }))} multiline />
            <div className="flex gap-1.5">
              <Button size="sm" className="h-7 px-2 text-[11px]" onClick={save} disabled={actions.update.isPending}>
                保存
              </Button>
              <Button
                size="sm"
                variant="ghost"
                className="h-7 px-2 text-[11px] text-ready-blocked"
                onClick={() => {
                  if (!window.confirm('仅空场次可删除，确定删除？')) return
                  actions.remove.mutate(sceneGroupId, {
                    onSuccess: () => onNavigate(workbenchEpisodePath(projectId, chapterId)),
                    onError: (error) => setNotice(error instanceof Error ? error.message : '删除失败'),
                  })
                }}
                disabled={(group.shot_count ?? 0) > 0}
              >
                <Trash2 className="h-3 w-3" />
                删除空场次
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">场次镜头（{groupShots.length}）</CardTitle>
          </CardHeader>
          <CardContent>
            {groupShots.length === 0 ? (
              <PanelEmpty title="场次还没有镜头" description="可先在剧集页运行 AI 分镜规划，或把已有镜头移动到此场次。" />
            ) : (
              <ul className="divide-y divide-border rounded-md border border-border">
                {groupShots.map((shot, index) => (
                  <li key={shot.id} className="flex flex-wrap items-center gap-2 px-3 py-2 text-[11px]">
                    <span className="w-14 shrink-0 text-muted-foreground">镜 {String(shot.index).padStart(2, '0')}</span>
                    <button
                      type="button"
                      className="min-w-0 flex-1 text-left hover:text-primary"
                      onClick={() => onNavigate(workbenchShotPath(projectId, chapterId, shot.id))}
                    >
                      <span className="block truncate text-sm">{shot.title}</span>
                      <span className="block truncate text-[10px] text-muted-foreground">{shot.script_excerpt || '—'}</span>
                    </button>
                    <PrepStatusBadge status={shot.status} />
                    <Button size="sm" variant="ghost" className="h-6 w-6 p-0" disabled={index === 0} onClick={() => moveShot(shot, -1)}>
                      <ArrowUp className="h-3 w-3" />
                    </Button>
                    <Button size="sm" variant="ghost" className="h-6 w-6 p-0" disabled={index === groupShots.length - 1} onClick={() => moveShot(shot, 1)}>
                      <ArrowDown className="h-3 w-3" />
                    </Button>
                    <Select
                      className="h-6 w-32 text-[10px]"
                      value={shot.scene_group_id ?? ''}
                      onChange={(event) => moveToGroup(shot, event.target.value)}
                    >
                      <option value="">未分配</option>
                      {(groupsQuery.data ?? []).map((item) => (
                        <option key={item.id} value={item.id}>场次 {item.index} · {item.title}</option>
                      ))}
                    </Select>
                    <LegacyLink href={legacyShotEditPath(projectId, chapterId, shot.id)}>
                      <ExternalLink className="h-3 w-3" />
                      旧版
                    </LegacyLink>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
