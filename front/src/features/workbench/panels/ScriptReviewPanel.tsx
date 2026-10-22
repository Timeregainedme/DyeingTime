/**
 * 统一审核面板（P3 / C6）。
 *
 * 左侧原文由 ScriptPanel 负责；本组件只处理右侧候选：
 * 编辑、接受、忽略、合并、关联已有资产、查看原文证据、确认落库。
 *
 * AI 候选默认 pending；确认前必须全部处理（issue 类型除外）。
 */
import { useEffect, useMemo, useState } from 'react'
import { AlertCircle, Check, GitMerge, MapPin, Plus, RefreshCw, Trash2, X } from 'lucide-react'
import { Badge } from '../../../components/ui/badge'
import { Button } from '../../../components/ui/button'
import { Input } from '../../../components/ui/input'
import { Select } from '../../../components/ui/select'
import { Textarea } from '../../../components/ui/textarea'
import { cn } from '../../../lib/utils'
import type {
  ScriptParseCandidateRead,
  ScriptParseRunRead,
} from '../../../services/generated'
import {
  useScriptParseActions,
  useWorkbenchCharacters,
  useWorkbenchGlobalAssets,
} from '../useWorkbenchQueries'

const TYPE_LABELS: Record<string, string> = {
  character: '角色',
  scene: '场景资产',
  prop: '道具',
  costume_change: '服装变化',
  scene_beat: '场次建议',
  dialogue: '对白',
  episode: '本集信息',
  issue: '待处理问题',
}

const TYPE_ORDER = [
  'character',
  'scene',
  'prop',
  'costume_change',
  'scene_beat',
  'dialogue',
  'episode',
  'issue',
]

/** 为人工新增候选提供各类型的最小合法 payload；用户随后可在卡片中补全。 */
function blankPayload(type: string): Record<string, unknown> {
  switch (type) {
    case 'character':
      return { name: '', aliases: [], role: '', age_range: '', appearance: '', hairstyle: '', body_type: '', base_costume: '', voice_description: '', episodes: [], evidence: [], issues: [] }
    case 'scene':
      return { name: '', location_type: '', interior_exterior: '', spatial_features: '', time_light: '', key_furnishings: '', is_existing: false, evidence: [], issues: [] }
    case 'prop':
      return { name: '', appearance: '', color_material: '', story_usage: '', holder_character: '', location: '', is_existing: false, evidence: [], issues: [] }
    case 'costume_change':
      return { character_name: '', base_costume: '', changed_costume: '', story_position: '', reason: '', applicable_episode: null, suggested_scene: '', evidence: [], issues: [] }
    case 'scene_beat':
      return { index: 0, title: '', location: '', time_of_day: '', characters: [], events: [], source_range: '', evidence: [], issues: [] }
    case 'dialogue':
      return { text: '', speaker_name: null, order: 0, emotion: '', line_mode: 'DIALOGUE', story_range: '', speaker_unresolved: true, evidence: [], issues: [] }
    case 'episode':
      return { title: '', summary: '', major_events: [], scene_beats: [] }
    case 'issue':
      return { type: 'other', message: '', related: '', evidence: [] }
    default:
      return {}
  }
}

function statusBadge(status: string) {
  if (status === 'accepted') return <Badge variant="secondary">已接受</Badge>
  if (status === 'edited') return <Badge variant="secondary">已修改</Badge>
  if (status === 'ignored') return <Badge variant="outline">已忽略</Badge>
  if (status === 'merged') return <Badge variant="outline">已合并</Badge>
  return <Badge variant="outline" className="border-state-pending/40 text-state-pending">待审核</Badge>
}

function Field({
  label,
  value,
  onChange,
  multiline = false,
  placeholder,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  multiline?: boolean
  placeholder?: string
}) {
  return (
    <div className="space-y-1">
      <label className="text-[11px] text-muted-foreground">{label}</label>
      {multiline ? (
        <Textarea
          value={value}
          rows={2}
          placeholder={placeholder}
          onChange={(event) => onChange(event.target.value)}
        />
      ) : (
        <Input value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
      )}
    </div>
  )
}

function candidateFields(candidate: ScriptParseCandidateRead) {
  switch (candidate.candidate_type) {
    case 'character':
      return [
        ['name', '角色名称'],
        ['role', '剧情身份'],
        ['age_range', '年龄感'],
        ['appearance', '外貌描述', true],
        ['hairstyle', '发型/发色'],
        ['body_type', '体型'],
        ['base_costume', '基础服装'],
        ['voice_description', '音色描述（仅依据原文）', true],
      ] as const
    case 'scene':
      return [
        ['name', '场景名称'],
        ['location_type', '地点类型'],
        ['interior_exterior', '室内/室外'],
        ['spatial_features', '空间特征', true],
        ['time_light', '时间与光照', true],
        ['key_furnishings', '重要陈设', true],
      ] as const
    case 'prop':
      return [
        ['name', '道具名称'],
        ['appearance', '外观', true],
        ['color_material', '颜色与材质'],
        ['story_usage', '剧情用途', true],
        ['holder_character', '持有角色'],
        ['location', '出现位置'],
      ] as const
    case 'costume_change':
      return [
        ['character_name', '角色'],
        ['base_costume', '基础服装'],
        ['changed_costume', '变化后服装/造型'],
        ['story_position', '剧情位置'],
        ['reason', '变化原因', true],
      ] as const
    case 'scene_beat':
      return [
        ['title', '场次标题'],
        ['location', '地点'],
        ['time_of_day', '时间'],
        ['source_range', '原文区间'],
      ] as const
    case 'dialogue':
      return [
        ['speaker_name', '说话人'],
        ['emotion', '情绪'],
        ['story_range', '剧情位置'],
        ['text', '台词', true],
      ] as const
    case 'episode':
      return [
        ['title', '本集标题'],
        ['summary', '剧情摘要', true],
      ] as const
    case 'issue':
      return [
        ['type', '问题类型'],
        ['related', '关联对象'],
        ['message', '问题说明', true],
      ] as const
    default:
      return []
  }
}

function updatePayloadField(
  payload: Record<string, unknown>,
  key: string,
  value: string,
): Record<string, unknown> {
  return { ...payload, [key]: value }
}

function ArrayField({
  label,
  value,
  onChange,
  multiline = false,
}: {
  label: string
  value: unknown
  onChange: (items: string[]) => void
  multiline?: boolean
}) {
  const text = Array.isArray(value) ? value.join(multiline ? '\n' : '，') : String(value ?? '')
  return (
    <Field
      label={label}
      value={text}
      multiline={multiline}
      onChange={(next) =>
        onChange(
          next
            .split(multiline ? '\n' : /[，,]/)
            .map((item) => item.trim())
            .filter(Boolean),
        )
      }
    />
  )
}

function CandidateCard({
  candidate,
  candidates,
  matchedOptions,
  busy,
  onSave,
  onAccept,
  onIgnore,
  onMatch,
  onMerge,
  onLocate,
  onDelete,
}: {
  candidate: ScriptParseCandidateRead
  candidates: ScriptParseCandidateRead[]
  matchedOptions: Array<{ id: string; name: string }>
  busy: boolean
  onSave: (payload: Record<string, unknown>) => void
  onAccept: () => void
  onIgnore: () => void
  onMatch: (entityId: string | null) => void
  onMerge: (targetId: string) => void
  onLocate: (quote: string) => void
  onDelete: () => void
}) {
  const [payload, setPayload] = useState<Record<string, unknown>>(candidate.payload ?? {})
  const [mergeTarget, setMergeTarget] = useState('')
  useEffect(() => {
    setPayload(candidate.payload ?? {})
    setMergeTarget('')
  }, [candidate.id, candidate.payload])

  const fields = candidateFields(candidate)
  const others = candidates.filter(
    (item) => item.candidate_type === candidate.candidate_type && item.id !== candidate.id,
  )
  const resolved = ['accepted', 'ignored', 'merged'].includes(candidate.review_status ?? 'pending')
  const issue = candidate.issue

  return (
    <div className="space-y-2 rounded-md border border-border p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium">
          {TYPE_LABELS[candidate.candidate_type] ?? candidate.candidate_type}
          {typeof payload.name === 'string' && payload.name ? `：${String(payload.name)}` : ''}
        </span>
        {statusBadge(candidate.review_status ?? 'pending')}
        {candidate.matched_entity_id ? (
          <Badge variant="outline" className="font-normal">
            已关联 {candidate.matched_entity_id.slice(0, 12)}
          </Badge>
        ) : null}
        {issue ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-state-pending/10 px-2 py-0.5 text-[10px] text-state-pending">
            <AlertCircle className="h-3 w-3" />
            {issue}
          </span>
        ) : null}
      </div>

      {!resolved ? (
        <>
          <div className="grid gap-2 md:grid-cols-2">
            {fields.map(([key, label, multiline]) => (
              <Field
                key={key}
                label={label}
                value={String(payload[key] ?? '')}
                multiline={Boolean(multiline)}
                onChange={(value) => setPayload((prev) => updatePayloadField(prev, key, value))}
              />
            ))}
            {candidate.candidate_type === 'character' ? (
              <ArrayField
                label="别名（逗号分隔）"
                value={payload.aliases}
                onChange={(items) => setPayload((prev) => ({ ...prev, aliases: items }))}
              />
            ) : null}
            {candidate.candidate_type === 'scene_beat' ? (
              <>
                <ArrayField
                  label="出场角色（逗号分隔）"
                  value={payload.characters}
                  onChange={(items) => setPayload((prev) => ({ ...prev, characters: items }))}
                />
                <ArrayField
                  label="重要事件（每行一条）"
                  value={payload.events}
                  multiline
                  onChange={(items) => setPayload((prev) => ({ ...prev, events: items }))}
                />
              </>
            ) : null}
            {candidate.candidate_type === 'episode' ? (
              <ArrayField
                label="主要事件（每行一条）"
                value={payload.major_events}
                multiline
                onChange={(items) => setPayload((prev) => ({ ...prev, major_events: items }))}
              />
            ) : null}
            {candidate.candidate_type === 'dialogue' ? (
              <>
                <div className="space-y-1">
                  <label className="text-[11px] text-muted-foreground">对白类型</label>
                  <Select
                    value={String(payload.line_mode ?? 'DIALOGUE')}
                    onChange={(event) =>
                      setPayload((prev) => ({ ...prev, line_mode: event.target.value }))
                    }
                  >
                    <option value="DIALOGUE">正常对白</option>
                    <option value="VOICE_OVER">旁白</option>
                    <option value="OFF_SCREEN">画外音</option>
                    <option value="PHONE">电话声</option>
                  </Select>
                </div>
                <label className="flex items-center gap-2 self-end pb-2 text-xs">
                  <input
                    type="checkbox"
                    checked={payload.speaker_unresolved === true}
                    onChange={(event) =>
                      setPayload((prev) => ({
                        ...prev,
                        speaker_unresolved: event.target.checked,
                      }))
                    }
                  />
                  说话人仍待确认
                </label>
              </>
            ) : null}
          </div>

          {matchedOptions.length > 0 ? (
            <div className="space-y-1">
              <label className="text-[11px] text-muted-foreground">关联已有资产</label>
              <Select
                value={candidate.matched_entity_id ?? ''}
                onChange={(event) => onMatch(event.target.value || null)}
              >
                <option value="">自动 / 不关联</option>
                {matchedOptions.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}（{item.id.slice(0, 8)}）
                  </option>
                ))}
              </Select>
            </div>
          ) : null}

          {candidate.evidence?.length ? (
            <div className="space-y-1">
              <p className="text-[10px] text-muted-foreground">原文证据</p>
              {candidate.evidence.slice(0, 3).map((item, index) => (
                <button
                  key={`${candidate.id}-evidence-${index}`}
                  type="button"
                  className="flex w-full items-start gap-1 rounded bg-muted/40 px-2 py-1 text-left text-[11px] leading-4 hover:bg-accent"
                  onClick={() => onLocate(String(item.quote ?? ''))}
                  title="在左侧原文定位"
                >
                  <MapPin className="mt-0.5 h-3 w-3 shrink-0 text-muted-foreground" />
                  「{String(item.quote ?? '')}」
                </button>
              ))}
            </div>
          ) : null}

          <div className="flex flex-wrap items-center gap-1.5">
            <Button
              size="sm"
              className="h-7 px-2 text-[11px]"
              onClick={() => onSave(payload)}
              disabled={busy}
            >
              保存修改
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-7 px-2 text-[11px]"
              onClick={onAccept}
              disabled={busy}
            >
              <Check className="h-3 w-3" />
              接受
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="h-7 px-2 text-[11px] text-muted-foreground"
              onClick={onIgnore}
              disabled={busy}
            >
              <X className="h-3 w-3" />
              忽略
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="h-7 px-2 text-[11px] text-ready-blocked"
              onClick={onDelete}
              disabled={busy}
            >
              <Trash2 className="h-3 w-3" />
              删除
            </Button>
            {others.length > 0 ? (
              <div className="ml-auto flex items-center gap-1">
                <Select
                  value={mergeTarget}
                  onChange={(event) => setMergeTarget(event.target.value)}
                  className="h-7 w-40 text-[11px]"
                >
                  <option value="">合并到…</option>
                  {others.map((item) => (
                    <option key={item.id} value={item.id}>
                      {String(item.payload?.name ?? item.candidate_key)}
                    </option>
                  ))}
                </Select>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 px-2 text-[11px]"
                  disabled={!mergeTarget || busy}
                  onClick={() => mergeTarget && onMerge(mergeTarget)}
                >
                  <GitMerge className="h-3 w-3" />
                  合并
                </Button>
              </div>
            ) : null}
          </div>
        </>
      ) : null}
    </div>
  )
}

export function ScriptReviewPanel({
  projectId,
  run,
  onRefresh,
  onConfirmed,
  onLocate,
}: {
  projectId: string
  run: ScriptParseRunRead
  onRefresh: () => void
  onConfirmed: () => void
  onLocate: (quote: string) => void
}) {
  const actions = useScriptParseActions(projectId, run.document_id)
  const charactersQuery = useWorkbenchCharacters(projectId)
  const scenesQuery = useWorkbenchGlobalAssets(projectId, 'scene')
  const propsQuery = useWorkbenchGlobalAssets(projectId, 'prop')
  const costumesQuery = useWorkbenchGlobalAssets(projectId, 'costume')
  const [activeType, setActiveType] = useState<string>('character')
  const [notice, setNotice] = useState<{ tone: 'ok' | 'error'; text: string } | null>(null)

  const grouped = useMemo(() => {
    const map: Record<string, ScriptParseCandidateRead[]> = {}
    for (const candidate of run.candidates ?? []) {
      map[candidate.candidate_type] = map[candidate.candidate_type] ?? []
      map[candidate.candidate_type].push(candidate)
    }
    return map
  }, [run.candidates])

  const availableTypes = TYPE_ORDER.filter((type) => (grouped[type]?.length ?? 0) > 0)
  useEffect(() => {
    if (!availableTypes.includes(activeType) && availableTypes.length) {
      setActiveType(availableTypes[0])
    }
  }, [activeType, availableTypes])

  const candidates = grouped[activeType] ?? []
  const pending = (run.candidates ?? []).filter(
    (item) => item.review_status === 'pending' && item.candidate_type !== 'issue',
  )
  const busy =
    actions.updateCandidate.isPending ||
    actions.addCandidate.isPending ||
    actions.deleteCandidate.isPending ||
    actions.merge.isPending ||
    actions.confirm.isPending

  const matchedOptions = (candidate: ScriptParseCandidateRead) => {
    const toOptions = (items?: Array<{ id: string; name: string }>) =>
      (items ?? []).map((item) => ({ id: item.id, name: item.name }))
    if (candidate.candidate_type === 'character') return toOptions(charactersQuery.data)
    if (candidate.candidate_type === 'scene') return toOptions(scenesQuery.data)
    if (candidate.candidate_type === 'prop') return toOptions(propsQuery.data)
    if (candidate.candidate_type === 'costume_change') return toOptions(costumesQuery.data)
    return []
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium">统一审核</span>
        <Badge variant="outline" className="font-normal">
          {run.model_name || '模型未记录'} · {run.provider_name || '—'}
        </Badge>
        <Badge variant="outline" className="font-normal">
          分块 {run.chunk_count}
        </Badge>
        {run.failed_chunks?.length ? (
          <Badge variant="outline" className="border-ready-blocked/40 text-ready-blocked">
            失败块 {run.failed_chunks.join(',')}
          </Badge>
        ) : null}
        <Button variant="ghost" size="sm" className="ml-auto h-7 px-2 text-[11px]" onClick={onRefresh}>
          <RefreshCw className="h-3 w-3" />
          刷新
        </Button>
        {pending.length > 0 ? (
          <Button
            size="sm"
            variant="outline"
            className="h-7 px-2 text-[11px]"
            disabled={busy}
            onClick={async () => {
              setNotice(null)
              try {
                for (const candidate of pending) {
                  await actions.updateCandidate.mutateAsync({
                    runId: run.id,
                    candidateId: candidate.id,
                    body: { review_status: 'accepted' },
                  })
                }
                setNotice({ tone: 'ok', text: `已接受 ${pending.length} 条候选，可继续确认` })
                onRefresh()
              } catch (error) {
                setNotice({
                  tone: 'error',
                  text: error instanceof Error ? error.message : '批量接受失败',
                })
              }
            }}
          >
            接受全部待处理
          </Button>
        ) : null}
        <Button
          size="sm"
          className="h-7 px-2 text-[11px]"
          disabled={pending.length > 0 || busy || run.status !== 'completed'}
          onClick={() =>
            actions.confirm.mutate(run.id, {
              onSuccess: (result) => {
                setNotice({
                  tone: 'ok',
                  text: `已确认并写入正式数据：${JSON.stringify(result.applied_summary)}`,
                })
                onConfirmed()
              },
              onError: (error) =>
                setNotice({
                  tone: 'error',
                  text: error instanceof Error ? error.message : '确认失败',
                }),
            })
          }
        >
          确认解析结果
        </Button>
      </div>

      {run.error ? (
        <div className="rounded-md border border-ready-blocked/40 bg-ready-blocked/10 p-2 text-[11px] text-ready-blocked">
          {run.error}
        </div>
      ) : null}
      {notice ? (
        <div
          className={cn(
            'rounded-md border p-2 text-[11px]',
            notice.tone === 'ok'
              ? 'border-ready-complete/40 bg-ready-complete/10 text-ready-complete'
              : 'border-ready-blocked/40 bg-ready-blocked/10 text-ready-blocked',
          )}
        >
          {notice.text}
        </div>
      ) : null}
      {pending.length > 0 ? (
        <p className="text-[11px] text-state-pending">
          还有 {pending.length} 条候选待处理；确认前必须接受、编辑或忽略。
        </p>
      ) : null}

      <div className="flex flex-wrap items-center gap-1">
        <Button
          size="sm"
          variant="outline"
          className="h-7 px-2 text-[11px]"
          disabled={busy || !activeType}
          onClick={() =>
            actions.addCandidate.mutate(
              {
                runId: run.id,
                candidateType: activeType,
                payload: blankPayload(activeType),
              },
              {
                onSuccess: () => {
                  setNotice({ tone: 'ok', text: '已新增候选，请补全字段后保存' })
                  onRefresh()
                },
                onError: (error) =>
                  setNotice({
                    tone: 'error',
                    text: error instanceof Error ? error.message : '新增候选失败',
                  }),
              },
            )
          }
        >
          <Plus className="h-3 w-3" />
          新增
        </Button>
        {availableTypes.map((type) => (
          <button
            key={type}
            type="button"
            onClick={() => setActiveType(type)}
            className={cn(
              'rounded-md border px-2 py-1 text-[11px] transition-colors',
              activeType === type
                ? 'border-primary/60 bg-primary/5 text-primary'
                : 'border-border text-muted-foreground hover:bg-accent',
            )}
          >
            {TYPE_LABELS[type] ?? type} {grouped[type]?.length ?? 0}
          </button>
        ))}
      </div>

      <div className="max-h-[55vh] space-y-2 overflow-auto pr-1">
        {candidates.length === 0 ? (
          <p className="text-xs text-muted-foreground">该分类没有候选。</p>
        ) : (
          candidates.map((candidate) => (
            <CandidateCard
              key={candidate.id}
              candidate={candidate}
              candidates={candidates}
              matchedOptions={matchedOptions(candidate)}
              busy={busy}
              onSave={(payload) =>
                actions.updateCandidate.mutate(
                  {
                    runId: run.id,
                    candidateId: candidate.id,
                    body: { payload },
                  },
                  {
                    onSuccess: () => {
                      setNotice({ tone: 'ok', text: '候选修改已保存' })
                      onRefresh()
                    },
                    onError: (error) =>
                      setNotice({
                        tone: 'error',
                        text: error instanceof Error ? error.message : '保存失败',
                      }),
                  },
                )
              }
              onAccept={() =>
                actions.updateCandidate.mutate(
                  {
                    runId: run.id,
                    candidateId: candidate.id,
                    body: { review_status: 'accepted' },
                  },
                  { onSuccess: onRefresh },
                )
              }
              onIgnore={() =>
                actions.updateCandidate.mutate(
                  {
                    runId: run.id,
                    candidateId: candidate.id,
                    body: { review_status: 'ignored' },
                  },
                  { onSuccess: onRefresh },
                )
              }
              onMatch={(entityId) =>
                actions.updateCandidate.mutate(
                  {
                    runId: run.id,
                    candidateId: candidate.id,
                    body: { matched_entity_id: entityId },
                  },
                  { onSuccess: onRefresh },
                )
              }
              onLocate={onLocate}
              onDelete={() =>
                actions.deleteCandidate.mutate(
                  { runId: run.id, candidateId: candidate.id },
                  {
                    onSuccess: () => {
                      setNotice({ tone: 'ok', text: '候选已删除' })
                      onRefresh()
                    },
                    onError: (error) =>
                      setNotice({
                        tone: 'error',
                        text: error instanceof Error ? error.message : '删除候选失败',
                      }),
                  },
                )
              }
              onMerge={(targetId) =>
                actions.merge.mutate(
                  { runId: run.id, sourceId: candidate.id, targetId },
                  {
                    onSuccess: () => {
                      setNotice({ tone: 'ok', text: '候选已合并' })
                      onRefresh()
                    },
                    onError: (error) =>
                      setNotice({
                        tone: 'error',
                        text: error instanceof Error ? error.message : '合并失败',
                      }),
                  },
                )
              }
            />
          ))
        )}
      </div>
    </div>
  )
}
