/**
 * P5 AI 分镜规划工作区：参数 → 生成 → 审核 → 应用。
 *
 * 规划只写 shot_plan_candidates；确认后才追加正式 Shot/ShotDetail。
 */
import { useEffect, useMemo, useState } from 'react'
import {
  AlertCircle,
  ArrowDown,
  ArrowUp,
  CheckCircle2,
  GitMerge,
  Plus,
  RefreshCw,
  Sparkles,
  Trash2,
  XCircle,
} from 'lucide-react'
import { Badge } from '../../../components/ui/badge'
import { Button } from '../../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card'
import { Input } from '../../../components/ui/input'
import { Select } from '../../../components/ui/select'
import { Textarea } from '../../../components/ui/textarea'
import type {
  ChapterRead,
  SceneGroupRead,
  ShotPlanCandidateRead,
  ShotPlanDraftRead,
} from '../../../services/generated'
import {
  useAssetProfile,
  useChapterShotPlans,
  useShotPlan,
  useShotPlanActions,
  useShotPlanStats,
} from '../useWorkbenchQueries'
import { cn } from '../../../lib/utils'

type PlanPayload = Record<string, unknown>
type PlanCharacter = Record<string, unknown>
type PlanAsset = Record<string, unknown>

function candidateIssues(candidate: ShotPlanCandidateRead) {
  return (candidate.issues ?? []).filter((item) => item.severity === 'blocking')
}

function warningIssues(candidate: ShotPlanCandidateRead) {
  return (candidate.issues ?? []).filter((item) => item.severity !== 'blocking')
}

function AssetVersionSelect({
  projectId,
  assetType,
  assetId,
  versionId,
  valueKey,
  onChange,
}: {
  projectId: string
  assetType: 'scene' | 'prop' | 'costume'
  assetId: string
  versionId?: string | null
  valueKey: string
  onChange: (key: string, value: string | null) => void
}) {
  const query = useAssetProfile(projectId, assetType, assetId)
  const versions = query.data?.versions ?? []
  return (
    <Select
      className="h-7 text-[10px]"
      value={versionId ?? ''}
      onChange={(event) => onChange(valueKey, event.target.value || null)}
    >
      <option value="">当前版本</option>
      {versions.map((version) => (
        <option key={version.id} value={version.id}>
          v{version.version_no} · {version.name || version.variant_type} · {version.status}
        </option>
      ))}
    </Select>
  )
}

function CharacterVersionControl({
  projectId,
  character,
  onChange,
}: {
  projectId: string
  character: PlanCharacter
  onChange: (appearanceVersionId: string | null) => void
}) {
  const assetId = String(character.character_id ?? '')
  const query = useAssetProfile(projectId, 'character', assetId)
  const versions = (query.data?.versions ?? []).filter(
    (version) => version.version_kind === 'appearance' || version.version_kind === 'identity',
  )
  return (
    <div className="flex items-center gap-1 text-[10px]">
      <span className="text-muted-foreground">{String(character.name ?? assetId)}</span>
      <Select
        className="h-6 w-40 text-[10px]"
        value={String(character.appearance_version_id ?? '')}
        onChange={(event) => onChange(event.target.value || null)}
      >
        <option value="">当前造型</option>
        {versions.map((version) => (
          <option key={version.id} value={version.id}>
            v{version.version_no} · {version.name || version.variant_type}
          </option>
        ))}
      </Select>
    </div>
  )
}

function CandidateCard({
  projectId,
  draft,
  candidate,
  candidates,
  busy,
  onSave,
  onAccept,
  onIgnore,
  onDuplicate,
  onDelete,
  onMergePrevious,
  onVersionChange,
}: {
  projectId: string
  draft: ShotPlanDraftRead
  candidate: ShotPlanCandidateRead
  candidates: ShotPlanCandidateRead[]
  busy: boolean
  onSave: (payload: PlanPayload, sceneGroupId: string | null) => void
  onAccept: () => void
  onIgnore: () => void
  onDuplicate: () => void
  onDelete: () => void
  onMergePrevious: () => void
  onVersionChange: (payload: PlanPayload) => void
}) {
  const payload = (candidate.payload ?? {}) as PlanPayload
  const [form, setForm] = useState({
    title: String(payload.title ?? ''),
    duration: String(payload.duration ?? 5),
    script_excerpt: String(payload.script_excerpt ?? ''),
    description: String(payload.description ?? ''),
    action_beats: Array.isArray(payload.action_beats) ? payload.action_beats.join('\n') : '',
    video_prompt: String(payload.video_prompt ?? ''),
    scene_group_id: candidate.scene_group_id ?? '',
  })
  useEffect(() => {
    setForm({
      title: String(payload.title ?? ''),
      duration: String(payload.duration ?? 5),
      script_excerpt: String(payload.script_excerpt ?? ''),
      description: String(payload.description ?? ''),
      action_beats: Array.isArray(payload.action_beats) ? payload.action_beats.join('\n') : '',
      video_prompt: String(payload.video_prompt ?? ''),
      scene_group_id: candidate.scene_group_id ?? '',
    })
  }, [candidate.id, candidate.scene_group_id, payload.title, payload.duration, payload.script_excerpt, payload.description, payload.action_beats, payload.video_prompt])
  const blocking = candidateIssues(candidate)
  const warnings = warningIssues(candidate)
  const characters = Array.isArray(payload.characters) ? (payload.characters as PlanCharacter[]) : []
  const scene = (payload.scene ?? null) as PlanAsset | null
  const costume = (payload.costume ?? null) as PlanAsset | null
  const props = Array.isArray(payload.props) ? (payload.props as PlanAsset[]) : []
  const dialogues = Array.isArray(payload.dialogues) ? (payload.dialogues as PlanPayload[]) : []
  const resolved = ['accepted', 'ignored'].includes(candidate.review_status ?? 'pending')
  const index = candidates.findIndex((item) => item.id === candidate.id)

  const basePayload = () => ({
    ...payload,
    title: form.title,
    duration: Number(form.duration) || 0,
    script_excerpt: form.script_excerpt,
    description: form.description,
    action_beats: form.action_beats.split('\n').map((item) => item.trim()).filter(Boolean),
    video_prompt: form.video_prompt,
    scene_group_id: form.scene_group_id || null,
  })

  const updateRef = (key: 'scene' | 'costume', versionId: string | null) => {
    const current = (payload[key] ?? null) as PlanAsset | null
    if (!current) return
    onVersionChange({ ...payload, [key]: { ...current, asset_version_id: versionId } })
  }

  const updateCharacterVersion = (indexValue: number, versionId: string | null) => {
    const next = characters.map((item, itemIndex) =>
      itemIndex === indexValue ? { ...item, appearance_version_id: versionId } : item,
    )
    onVersionChange({ ...payload, characters: next })
  }

  return (
    <div className={cn('space-y-2 rounded-md border p-3', blocking.length ? 'border-ready-blocked/50' : 'border-border')}>
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="outline">#{candidate.order_index}</Badge>
        <span className="text-xs font-medium">{form.title || '未命名镜头'}</span>
        {resolved ? (
          <Badge variant="secondary">{candidate.review_status === 'accepted' ? '已接受' : '已忽略'}</Badge>
        ) : (
          <Badge variant="outline" className="border-state-pending/40 text-state-pending">待审核</Badge>
        )}
        {blocking.length ? <Badge variant="outline" className="border-ready-blocked/40 text-ready-blocked">{blocking.length} 个阻塞项</Badge> : null}
      </div>

      <div className="grid gap-2 md:grid-cols-[1fr_90px_180px]">
        <Input value={form.title} onChange={(event) => setForm((prev) => ({ ...prev, title: event.target.value }))} className="h-8 text-xs" />
        <Input
          type="number"
          min={1}
          value={form.duration}
          onChange={(event) => setForm((prev) => ({ ...prev, duration: event.target.value }))}
          className="h-8 text-xs"
        />
        <Select value={form.scene_group_id} onChange={(event) => setForm((prev) => ({ ...prev, scene_group_id: event.target.value }))} className="h-8 text-xs">
          <option value="">选择场次</option>
          {(draft.scene_group_snapshot ?? []).map((group) => (
            <option key={String(group.id ?? group.index)} value={String(group.id ?? '')}>
              场次 {String(group.index)} · {String(group.title ?? '')}
            </option>
          ))}
        </Select>
      </div>
      <Textarea
        value={form.script_excerpt}
        rows={2}
        onChange={(event) => setForm((prev) => ({ ...prev, script_excerpt: event.target.value }))}
        placeholder="剧本原文摘录"
        className="text-xs"
      />
      <Textarea
        value={form.description}
        rows={2}
        onChange={(event) => setForm((prev) => ({ ...prev, description: event.target.value }))}
        placeholder="视觉/动作描述"
        className="text-xs"
      />
      <Textarea
        value={form.action_beats}
        rows={2}
        onChange={(event) => setForm((prev) => ({ ...prev, action_beats: event.target.value }))}
        placeholder="动作拍点，每行一个"
        className="text-xs"
      />

      <div className="space-y-1 rounded bg-muted/20 p-2 text-[10px]">
        <p className="font-medium">资产与版本</p>
        {characters.map((character, characterIndex) => (
          <CharacterVersionControl
            key={String(character.character_id ?? characterIndex)}
            projectId={projectId}
            character={character}
            onChange={(versionId) => updateCharacterVersion(characterIndex, versionId)}
          />
        ))}
        {scene ? (
          <div className="flex items-center gap-1">
            <span className="text-muted-foreground">场景：{String(scene.name ?? scene.asset_id)}</span>
            <AssetVersionSelect
              projectId={projectId}
              assetType="scene"
              assetId={String(scene.asset_id)}
              versionId={String(scene.asset_version_id ?? '')}
              valueKey="scene"
              onChange={(_key, versionId) => updateRef('scene', versionId)}
            />
          </div>
        ) : null}
        {props.map((prop, indexValue) => (
          <div key={String(prop.asset_id ?? indexValue)} className="flex items-center gap-1">
            <span className="text-muted-foreground">道具：{String(prop.name ?? prop.asset_id)}</span>
            <AssetVersionSelect
              projectId={projectId}
              assetType="prop"
              assetId={String(prop.asset_id)}
              versionId={String(prop.asset_version_id ?? '')}
              valueKey="prop"
              onChange={(_key, versionId) => {
                const next = props.map((item, itemIndex) =>
                  itemIndex === indexValue ? { ...item, asset_version_id: versionId } : item,
                )
                onVersionChange({ ...payload, props: next })
              }}
            />
          </div>
        ))}
        {costume ? (
          <div className="flex items-center gap-1">
            <span className="text-muted-foreground">服装：{String(costume.name ?? costume.asset_id)}</span>
            <AssetVersionSelect
              projectId={projectId}
              assetType="costume"
              assetId={String(costume.asset_id)}
              versionId={String(costume.asset_version_id ?? '')}
              valueKey="costume"
              onChange={(_key, versionId) => updateRef('costume', versionId)}
            />
          </div>
        ) : null}
      </div>

      {dialogues.length ? (
        <div className="space-y-1 text-[11px]">
          <p className="font-medium">对白</p>
          {dialogues.map((dialogue, indexValue) => (
            <p key={`${candidate.id}-dialogue-${indexValue}`} className="text-muted-foreground">
              {dialogue.speaker_name ? `${String(dialogue.speaker_name)}：` : '（说话人待确认）：'}
              {String(dialogue.text ?? '')}
            </p>
          ))}
        </div>
      ) : null}

      {blocking.length ? (
        <div className="rounded border border-ready-blocked/40 bg-ready-blocked/10 p-2 text-[10px] text-ready-blocked">
          {blocking.map((issue, indexValue) => (
            <p key={`${candidate.id}-block-${indexValue}`}>{String(issue.message ?? issue.code)}</p>
          ))}
        </div>
      ) : null}
      {warnings.length ? (
        <div className="rounded border border-state-pending/40 bg-state-pending/10 p-2 text-[10px] text-state-pending">
          {warnings.slice(0, 3).map((issue, indexValue) => (
            <p key={`${candidate.id}-warn-${indexValue}`}>{String(issue.message ?? issue.code)}</p>
          ))}
        </div>
      ) : null}

      <div className="flex flex-wrap items-center gap-1">
        <Button size="sm" className="h-7 px-2 text-[10px]" onClick={() => onSave(basePayload(), form.scene_group_id || null)} disabled={busy}>
          保存
        </Button>
        <Button size="sm" variant="outline" className="h-7 px-2 text-[10px]" onClick={onAccept} disabled={busy}>
          <CheckCircle2 className="h-3 w-3" /> 接受
        </Button>
        <Button size="sm" variant="ghost" className="h-7 px-2 text-[10px]" onClick={onIgnore} disabled={busy}>
          <XCircle className="h-3 w-3" /> 忽略
        </Button>
        <Button size="sm" variant="ghost" className="h-7 px-2 text-[10px]" onClick={onDuplicate} disabled={busy}>
          <Plus className="h-3 w-3" /> 复制/拆分
        </Button>
        {index > 0 ? (
          <Button
            size="sm"
            variant="ghost"
            className="h-7 px-2 text-[10px]"
            onClick={onMergePrevious}
            disabled={busy}
          >
            <GitMerge className="h-3 w-3" /> 合并到上一镜
          </Button>
        ) : null}
        <Button size="sm" variant="ghost" className="h-7 px-2 text-[10px] text-ready-blocked" onClick={onDelete} disabled={busy}>
          <Trash2 className="h-3 w-3" /> 删除
        </Button>
      </div>
    </div>
  )
}

export function ShotPlanWorkspace({
  projectId,
  chapter,
  sceneGroups,
  existingShotCount,
  onApplied,
}: {
  projectId: string
  chapter: ChapterRead
  sceneGroups: SceneGroupRead[]
  existingShotCount: number
  onApplied: () => void
}) {
  const plansQuery = useChapterShotPlans(projectId, chapter.id)
  const latest = plansQuery.data?.[0]
  const planQuery = useShotPlan(projectId, latest?.id)
  const statsQuery = useShotPlanStats(projectId, chapter.id)
  const actions = useShotPlanActions(projectId, chapter.id)
  const [targetDuration, setTargetDuration] = useState(90)
  const [pace, setPace] = useState<'slow' | 'standard' | 'fast'>('standard')
  const [notice, setNotice] = useState('')
  const plan = planQuery.data ?? latest
  const candidates = useMemo(
    () => [...(plan?.candidates ?? [])].sort((a, b) => a.order_index - b.order_index),
    [plan?.candidates],
  )
  const pending = candidates.filter((item) => item.review_status === 'pending')
  const blocking = candidates.reduce((sum, item) => sum + candidateIssues(item).length, 0)
  const busy =
    actions.create.isPending ||
    actions.updateCandidate.isPending ||
    actions.addCandidate.isPending ||
    actions.duplicate.isPending ||
    actions.remove.isPending ||
    actions.reorder.isPending ||
    actions.merge.isPending ||
    actions.confirm.isPending

  const start = (force = false) => {
    setNotice('')
    if (!sceneGroups.length) {
      setNotice('请先创建/导入正式场次，再开始 AI 分镜规划')
      return
    }
    actions.create.mutate(
      { target_duration: targetDuration, pace, force },
      {
        onSuccess: () => setNotice('规划任务已提交；完成后在此审核'),
        onError: (error) => setNotice(error instanceof Error ? error.message : '规划任务创建失败'),
      },
    )
  }

  const updateCandidate = (candidateId: string, payload: PlanPayload, sceneGroupId: string | null) => {
    if (!plan) return
    actions.updateCandidate.mutate(
      {
        draftId: plan.id,
        candidateId,
        body: { payload, scene_group_id: sceneGroupId },
      },
      {
        onSuccess: () => setNotice('镜头候选已保存'),
        onError: (error) => setNotice(error instanceof Error ? error.message : '保存失败'),
      },
    )
  }

  const confirmPlan = () => {
    if (!plan) return
    if (existingShotCount > 0) {
      if (!window.confirm('当前剧集已有镜头。本阶段只允许追加，不会覆盖或删除旧镜头；是否继续？')) return
    }
    actions.confirm.mutate(
      { draftId: plan.id, appendToExisting: existingShotCount > 0 },
      {
        onSuccess: (result) => {
          setNotice(`已写入 ${(result.shot_ids ?? []).length} 个正式镜头`)
          onApplied()
        },
        onError: (error) => setNotice(error instanceof Error ? error.message : '应用失败'),
      },
    )
  }

  if (!plan) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm"><Sparkles className="h-4 w-4" />AI 分镜规划</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {notice ? <p className="text-[11px] text-state-pending">{notice}</p> : null}
          <div className="flex flex-wrap items-end gap-2">
            <div className="space-y-1">
              <label className="text-[11px] text-muted-foreground">目标总时长（秒）</label>
              <Input
                type="number"
                min={30}
                max={300}
                value={targetDuration}
                onChange={(event) => setTargetDuration(Number(event.target.value) || 90)}
                className="h-8 w-28 text-xs"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[11px] text-muted-foreground">节奏</label>
              <Select value={pace} onChange={(event) => setPace(event.target.value as typeof pace)} className="h-8 text-xs">
                <option value="slow">舒缓</option>
                <option value="standard">标准</option>
                <option value="fast">快速</option>
              </Select>
            </div>
            <Button size="sm" onClick={() => start(false)} disabled={busy || !sceneGroups.length}>
              <Sparkles className="h-3.5 w-3.5" />开始规划本集
            </Button>
          </div>
          <p className="text-[10px] text-muted-foreground">
            系统会综合剧本、P3 场次建议、已锁定角色、场次资产与项目时长范围生成候选；应用前必须人工审核。
          </p>
        </CardContent>
      </Card>
    )
  }

  const coverage = plan.coverage ?? {}
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Sparkles className="h-4 w-4" />AI 分镜规划
          </CardTitle>
          <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
            <Badge variant="outline">{plan.status}</Badge>
            <Badge variant="outline">目标 {plan.target_duration}s</Badge>
            <Badge variant="outline">{plan.pace}</Badge>
            <Badge variant="outline">镜头 {candidates.length}</Badge>
            <Badge variant="outline">总时长 {String(coverage.total_duration ?? statsQuery.data?.total_duration ?? 0)}s</Badge>
            <Badge variant="outline">覆盖 {Math.round(Number(coverage.coverage_ratio ?? 0) * 100)}%</Badge>
            {blocking ? <Badge variant="outline" className="border-ready-blocked/40 text-ready-blocked">阻塞 {blocking}</Badge> : null}
            <Button size="sm" variant="ghost" className="h-6 px-1.5 text-[10px]" onClick={() => void planQuery.refetch()}>
              <RefreshCw className="h-3 w-3" />刷新
            </Button>
            <Button size="sm" variant="outline" className="h-6 px-1.5 text-[10px]" onClick={() => start(true)} disabled={busy}>
              重新规划
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {notice ? <p className="rounded border border-state-pending/40 bg-state-pending/10 p-2 text-[11px]">{notice}</p> : null}
        {plan.error ? <p className="text-[11px] text-ready-blocked">{plan.error}</p> : null}
        {Array.isArray(coverage.warnings) && coverage.warnings.length ? (
          <div className="rounded border border-state-pending/40 bg-state-pending/10 p-2 text-[10px] text-state-pending">
            {(coverage.warnings as string[]).map((warning) => (
              <p key={warning}>{warning}</p>
            ))}
          </div>
        ) : null}
        {plan.status === 'draft' || plan.status === 'generating' ? (
          <p className="text-xs text-muted-foreground">AI 正在规划镜头，页面会自动刷新。</p>
        ) : null}
        {plan.status === 'failed' ? (
          <p className="text-[11px] text-ready-blocked">规划失败；已有候选仍可查看，修复问题后重新规划。</p>
        ) : null}

        <div className="flex flex-wrap items-center gap-1.5">
          <Button
            size="sm"
            variant="outline"
            className="h-7 px-2 text-[10px]"
            disabled={busy}
            onClick={() => {
              if (!plan) return
              const next = Array.from({ length: Math.max(0, pending.length) })
              void Promise.all(
                pending.map((candidate) =>
                  actions.updateCandidate.mutateAsync({
                    draftId: plan.id,
                    candidateId: candidate.id,
                    body: { review_status: 'accepted' },
                  }),
                ),
              ).then(() => setNotice('待处理候选已全部接受')).catch((error) =>
                setNotice(error instanceof Error ? error.message : '批量接受失败'),
              )
              void next
            }}
          >
            接受全部待处理
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="h-7 px-2 text-[10px]"
            disabled={busy}
            onClick={() => {
              if (!plan) return
              actions.addCandidate.mutate(
                { draftId: plan.id, body: { scene_group_id: sceneGroups[0]?.id ?? null } },
                { onSuccess: () => setNotice('已新增空白镜头候选') },
              )
            }}
          >
            <Plus className="h-3 w-3" />新增镜头
          </Button>
          <Button
            size="sm"
            className="h-7 px-2 text-[10px]"
            disabled={busy || !candidates.length || plan.status !== 'review_required'}
            onClick={confirmPlan}
          >
            <CheckCircle2 className="h-3 w-3" />确认并写入正式镜头
          </Button>
          {existingShotCount > 0 ? (
            <span className="text-[10px] text-state-pending">已有 {existingShotCount} 个镜头，确认时仅追加不覆盖</span>
          ) : null}
        </div>

        {!candidates.length ? (
          <p className="text-xs text-muted-foreground">暂无镜头候选。</p>
        ) : (
          <div className="space-y-2">
            {candidates.map((candidate, index) => (
              <div key={candidate.id} className="space-y-1">
                <div className="flex justify-end gap-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 w-6 p-0"
                    disabled={index === 0 || busy}
                    onClick={() => {
                      const ids = candidates.map((item) => item.id)
                      ;[ids[index - 1], ids[index]] = [ids[index], ids[index - 1]]
                      actions.reorder.mutate({ draftId: plan.id, candidateIds: ids })
                    }}
                  >
                    <ArrowUp className="h-3 w-3" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 w-6 p-0"
                    disabled={index === candidates.length - 1 || busy}
                    onClick={() => {
                      const ids = candidates.map((item) => item.id)
                      ;[ids[index + 1], ids[index]] = [ids[index], ids[index + 1]]
                      actions.reorder.mutate({ draftId: plan.id, candidateIds: ids })
                    }}
                  >
                    <ArrowDown className="h-3 w-3" />
                  </Button>
                </div>
                <CandidateCard
                  projectId={projectId}
                  draft={plan}
                  candidate={candidate}
                  candidates={candidates}
                  busy={busy}
                  onSave={(payload, sceneGroupId) => updateCandidate(candidate.id, payload, sceneGroupId)}
                  onAccept={() =>
                    actions.updateCandidate.mutate({
                      draftId: plan.id,
                      candidateId: candidate.id,
                      body: { review_status: 'accepted' },
                    })
                  }
                  onIgnore={() =>
                    actions.updateCandidate.mutate({
                      draftId: plan.id,
                      candidateId: candidate.id,
                      body: { review_status: 'ignored' },
                    })
                  }
                  onDuplicate={() =>
                    actions.duplicate.mutate(
                      { draftId: plan.id, candidateId: candidate.id },
                      { onSuccess: () => setNotice('已复制镜头候选，可继续拆分/修改') },
                    )
                  }
                  onDelete={() =>
                    actions.remove.mutate(
                      { draftId: plan.id, candidateId: candidate.id },
                      { onError: (error) => setNotice(error instanceof Error ? error.message : '删除失败') },
                    )
                  }
                  onMergePrevious={() => {
                    if (index === 0) return
                    actions.merge.mutate(
                      {
                        draftId: plan.id,
                        sourceId: candidate.id,
                        targetId: candidates[index - 1].id,
                      },
                      {
                        onSuccess: () => setNotice('已合并到上一镜；请检查时长与对白'),
                        onError: (error) => setNotice(error instanceof Error ? error.message : '合并失败'),
                      },
                    )
                  }}
                  onVersionChange={(payload) => {
                    const sceneGroupId = candidate.scene_group_id ?? null
                    updateCandidate(candidate.id, payload, sceneGroupId)
                  }}
                />
              </div>
            ))}
          </div>
        )}

        {pending.length > 0 ? (
          <p className="flex items-center gap-1 text-[11px] text-state-pending">
            <AlertCircle className="h-3 w-3" />仍有 {pending.length} 个候选未接受/忽略。
          </p>
        ) : null}
      </CardContent>
    </Card>
  )
}
