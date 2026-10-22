/**
 * P4 资产详情：角色圣经 / 资产版本 / 图片候选 / 音色 / 身份锁定。
 *
 * 复用现有设计系统；图片任务仍由后端资产图链路执行，本面板只负责发起与采纳。
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import {
  ArrowLeft,
  CheckCircle2,
  ExternalLink,
  ImagePlus,
  Lock,
  RefreshCw,
  Sparkles,
  Trash2,
  Upload,
} from 'lucide-react'
import { Badge } from '../../../components/ui/badge'
import { Button } from '../../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card'
import { Input } from '../../../components/ui/input'
import { ScrollArea } from '../../../components/ui/scroll-area'
import { Select } from '../../../components/ui/select'
import { Textarea } from '../../../components/ui/textarea'
import { cn } from '../../../lib/utils'
import type {
  AssetImageCandidateRead,
  AssetProfileRead,
  AssetVersionRead,
} from '../../../services/generated'
import {
  WORKBENCH_ASSET_LABELS,
  workbenchAssetGroupPath,
  type WorkbenchAssetType,
} from '../routes'
import {
  useAssetProfile,
  useAssetProfileActions,
  useAvailableVoices,
  useCharacterVoice,
  useWorkbenchGlobalAssets,
} from '../useWorkbenchQueries'
import { LegacyLink, PanelHeader } from '../components/PanelHeader'
import { PanelError, PanelLoading } from '../components/PanelStates'
import { legacyAssetEditPath } from './legacyPaths'

const ANGLE_OPTIONS = [
  { value: 'front', label: '正面' },
  { value: 'left', label: '左侧' },
  { value: 'right', label: '右侧' },
  { value: 'back', label: '背面' },
  { value: 'three_quarter', label: '四分之三侧面' },
]

const VARIANT_OPTIONS = [
  { value: 'costume', label: '服装造型' },
  { value: 'hairstyle', label: '发型' },
  { value: 'makeup', label: '妆容' },
  { value: 'age', label: '年龄状态' },
  { value: 'weather', label: '雨淋/破损等环境状态' },
  { value: 'lighting', label: '光照状态' },
  { value: 'other', label: '其他衍生' },
]

function angleLabel(value?: string) {
  return ANGLE_OPTIONS.find((item) => item.value === (value ?? '').toLowerCase())?.label ??
    value ??
    '—'
}

function statusBadge(status?: string) {
  if (status === 'adopted') return <Badge variant="secondary">已采纳</Badge>
  if (status === 'succeeded') return <Badge variant="outline">已生成</Badge>
  if (status === 'failed') return <Badge variant="outline" className="border-ready-blocked/40 text-ready-blocked">失败</Badge>
  if (status === 'pending') return <Badge variant="outline" className="border-state-pending/40 text-state-pending">生成中</Badge>
  return <Badge variant="outline">{status ?? '—'}</Badge>
}

function Field({
  label,
  value,
  onChange,
  disabled,
  multiline,
  placeholder,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  disabled?: boolean
  multiline?: boolean
  placeholder?: string
}) {
  return (
    <div className="space-y-1">
      <label className="text-[11px] text-muted-foreground">{label}</label>
      {multiline ? (
        <Textarea
          value={value}
          disabled={disabled}
          rows={2}
          placeholder={placeholder}
          onChange={(event) => onChange(event.target.value)}
        />
      ) : (
        <Input
          value={value}
          disabled={disabled}
          placeholder={placeholder}
          onChange={(event) => onChange(event.target.value)}
        />
      )}
    </div>
  )
}

function CandidateCard({
  candidate,
  busy,
  onAdopt,
  onDelete,
  onLocatePrompt,
}: {
  candidate: AssetImageCandidateRead
  busy: boolean
  onAdopt: () => void
  onDelete: () => void
  onLocatePrompt: () => void
}) {
  const [showPrompt, setShowPrompt] = useState(false)
  const pending = candidate.status === 'pending'
  return (
    <div className="overflow-hidden rounded-md border border-border">
      <div className="relative flex h-36 items-center justify-center bg-muted/40">
        {candidate.file_url ? (
          <img
            src={candidate.file_url}
            alt={`候选 ${candidate.id}`}
            className="h-full w-full object-contain"
          />
        ) : (
          <div className="text-center text-[11px] text-muted-foreground">
            {pending ? '图片生成中…' : candidate.status === 'failed' ? '生成失败' : '暂无图片'}
          </div>
        )}
        {candidate.is_adopted ? (
          <span className="absolute left-2 top-2 inline-flex items-center gap-1 rounded-full bg-primary px-2 py-0.5 text-[10px] text-primary-foreground">
            <CheckCircle2 className="h-3 w-3" />
            当前选用
          </span>
        ) : null}
      </div>
      <div className="space-y-1.5 p-2">
        <div className="flex items-center justify-between gap-2 text-[11px]">
          <span className="text-muted-foreground">
            #{candidate.id} · {angleLabel(candidate.view_angle)} · {candidate.source === 'uploaded' ? '上传' : '生成'}
          </span>
          {statusBadge(candidate.status)}
        </div>
        {candidate.generation_params?.model_name ? (
          <p className="truncate text-[10px] text-muted-foreground">
            模型：{String(candidate.generation_params.model_name)}
          </p>
        ) : null}
        <div className="flex flex-wrap gap-1">
          <Button
            size="sm"
            variant={candidate.is_adopted ? 'outline' : 'default'}
            className="h-6 px-2 text-[10px]"
            disabled={busy || pending || candidate.status === 'failed' || candidate.is_adopted || !candidate.file_url}
            onClick={onAdopt}
          >
            {candidate.is_adopted ? '已选用' : '选用为当前图'}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="h-6 px-2 text-[10px]"
            disabled={busy || candidate.is_adopted}
            onClick={onDelete}
          >
            <Trash2 className="h-3 w-3" />
            删除
          </Button>
          {candidate.prompt ? (
            <Button
              size="sm"
              variant="ghost"
              className="h-6 px-2 text-[10px]"
              onClick={() => {
                setShowPrompt((value) => !value)
                onLocatePrompt()
              }}
            >
              {showPrompt ? '收起提示词' : '查看提示词'}
            </Button>
          ) : null}
        </div>
        {showPrompt ? (
          <p className="max-h-24 overflow-auto rounded bg-muted/40 p-1.5 text-[10px] leading-4">
            {candidate.prompt}
          </p>
        ) : null}
      </div>
    </div>
  )
}

function VersionList({
  profile,
  busy,
  onSwitch,
  onCreate,
  isCharacter,
}: {
  profile: AssetProfileRead
  busy: boolean
  onSwitch: (version: AssetVersionRead) => void
  onCreate: () => void
  isCharacter: boolean
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-sm">版本历史</CardTitle>
          <Button size="sm" variant="outline" className="h-7 px-2 text-[11px]" onClick={onCreate} disabled={busy}>
            <ImagePlus className="h-3.5 w-3.5" />
            {isCharacter ? '新增造型/身份' : '新增衍生版本'}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-1.5">
        {(profile.versions ?? []).map((version) => {
          const current =
            version.id === profile.current_version_id ||
            version.id === profile.identity_version_id ||
            version.id === profile.current_appearance_version_id
          return (
            <div
              key={version.id}
              className={cn(
                'flex flex-wrap items-center gap-2 rounded-md border px-2 py-1.5 text-[11px]',
                current ? 'border-primary/50 bg-primary/5' : 'border-border',
              )}
            >
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">
                  v{version.version_no} · {version.name || '未命名'}
                  {version.version_kind === 'identity' ? ' · 身份' : version.version_kind === 'appearance' ? ' · 造型' : ''}
                </p>
                <p className="truncate text-[10px] text-muted-foreground">
                  {version.variant_type} · {version.status} · 采纳图 {version.adopted_image_count}
                </p>
              </div>
              {version.id === profile.identity_version_id ? <Badge variant="secondary">身份当前</Badge> : null}
              {version.id === profile.current_appearance_version_id ? <Badge variant="outline">造型当前</Badge> : null}
              {version.id === profile.current_version_id && !isCharacter ? <Badge variant="secondary">当前</Badge> : null}
              <Button
                size="sm"
                variant="ghost"
                className="h-6 px-1.5 text-[10px]"
                disabled={busy || current}
                onClick={() => onSwitch(version)}
              >
                设为当前
              </Button>
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}

function VoiceSection({
  projectId,
  profile,
}: {
  projectId: string
  profile: AssetProfileRead
}) {
  const voicesQuery = useAvailableVoices()
  const voiceQuery = useCharacterVoice(projectId, profile.asset_id)
  const actions = useAssetProfileActions(projectId, profile.asset_type as WorkbenchAssetType, profile.asset_id)
  const [voiceId, setVoiceId] = useState(profile.voice_id ?? '')
  const [source, setSource] = useState(profile.voice_source ?? 'preset')
  const [description, setDescription] = useState(profile.voice_description ?? '')
  const [notice, setNotice] = useState('')
  const voice = voiceQuery.data

  useEffect(() => {
    setVoiceId(profile.voice_id ?? '')
    setSource(profile.voice_source ?? 'preset')
    setDescription(profile.voice_description ?? '')
  }, [profile.voice_id, profile.voice_source, profile.voice_description, profile.asset_id])

  const previewUrl = useMemo(() => {
    const row = (voicesQuery.data ?? []).find((item) => item.voice_id === voiceId)
    const raw = row?.raw ?? {}
    const value =
      raw.audio_url ??
      raw.preview_url ??
      raw.sample_url ??
      raw.url ??
      raw.demo_url
    return typeof value === 'string' ? value : ''
  }, [voiceId, voicesQuery.data])

  const bind = () => {
    setNotice('')
    actions.updateVoice.mutate(
      {
        voice_id: voiceId.trim() || null,
        voice_source: voiceId.trim() ? source : null,
        voice_description: description,
      },
      {
        onSuccess: () => setNotice('音色绑定已保存；视觉身份锁定状态不受影响。'),
        onError: (error) => setNotice(error instanceof Error ? error.message : '音色绑定失败'),
      },
    )
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">音色</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex flex-wrap items-center gap-2 text-[11px]">
          <Badge variant={voice?.effective_voice_id ? 'secondary' : 'outline'}>
            {voice?.effective_voice_id
              ? `生效：${voice.effective_voice_id}（${voice.effective_from === 'actor' ? '演员回退' : '角色'}）`
              : '未绑定音色'}
          </Badge>
          {voice?.effective_voice_source ? (
            <Badge variant="outline" className="font-normal">
              来源 {voice.effective_voice_source}
            </Badge>
          ) : null}
        </div>
        <div className="grid gap-2 md:grid-cols-2">
          <div className="space-y-1">
            <label className="text-[11px] text-muted-foreground">绑定音色</label>
            <Select value={voiceId} onChange={(event) => setVoiceId(event.target.value)}>
              <option value="">不绑定（回退演员音色）</option>
              {(voicesQuery.data ?? []).map((item) => (
                <option key={item.voice_id} value={item.voice_id}>
                  {item.name || item.voice_id}
                  {item.language ? ` · ${item.language}` : ''}
                </option>
              ))}
            </Select>
          </div>
          <div className="space-y-1">
            <label className="text-[11px] text-muted-foreground">音色来源</label>
            <Select value={source} onChange={(event) => setSource(event.target.value)}>
              <option value="preset">preset 预设</option>
              <option value="custom">custom 自定义</option>
            </Select>
          </div>
        </div>
        <Field label="音色描述" value={description} onChange={setDescription} multiline />
        {previewUrl ? (
          <audio className="w-full" controls src={previewUrl}>
            当前浏览器不支持音频预览
          </audio>
        ) : (
          <p className="text-[10px] text-muted-foreground">
            当前音色列表未提供试听地址；仍可完成人工绑定。
          </p>
        )}
        {voicesQuery.isError ? (
          <p className="text-[10px] text-state-pending">
            音色列表读取失败：{voicesQuery.error instanceof Error ? voicesQuery.error.message : '供应商未配置'}
          </p>
        ) : null}
        {notice ? <p className="text-[11px] text-muted-foreground">{notice}</p> : null}
        <Button
          size="sm"
          className="h-7 px-2 text-[11px]"
          disabled={actions.updateVoice.isPending}
          onClick={bind}
        >
          保存音色绑定
        </Button>
      </CardContent>
    </Card>
  )
}

export function AssetDetailPanel({
  projectId,
  assetType,
  assetId,
  onNavigate,
}: {
  projectId: string
  assetType: WorkbenchAssetType
  assetId: string
  onNavigate: (path: string) => void
}) {
  const query = useAssetProfile(projectId, assetType, assetId)
  const actions = useAssetProfileActions(projectId, assetType, assetId)
  const costumesQuery = useWorkbenchGlobalAssets(projectId, 'costume')
  const [form, setForm] = useState({
    name: '',
    description: '',
    age_range: '',
    appearance: '',
    face_features: '',
    body_type: '',
    identity_features: '',
    tags: '',
  })
  const [notice, setNotice] = useState('')
  const [alias, setAlias] = useState('')
  const [angle, setAngle] = useState('front')
  const [targetVersionId, setTargetVersionId] = useState<string | null>(null)
  const [versionName, setVersionName] = useState('')
  const [versionDescription, setVersionDescription] = useState('')
  const [variantType, setVariantType] = useState('costume')
  const [costumeId, setCostumeId] = useState('')
  const [identityDraftMode, setIdentityDraftMode] = useState(false)
  const [uploading, setUploading] = useState(false)
  const uploadRef = useRef<HTMLInputElement | null>(null)
  const profile = query.data
  const isCharacter = assetType === 'character'
  const locked = Boolean(profile?.identity_locked)

  useEffect(() => {
    if (!profile) return
    setForm({
      name: profile.name ?? '',
      description: profile.description ?? '',
      age_range: profile.age_range ?? '',
      appearance: profile.appearance ?? '',
      face_features: profile.face_features ?? '',
      body_type: profile.body_type ?? '',
      identity_features: profile.identity_features ?? '',
      tags: (profile.tags ?? []).join('、'),
    })
    setTargetVersionId(profile.current_version_id ?? profile.identity_version_id ?? null)
  // profile 对象每秒轮询会产生新引用；只依赖实际表单字段，避免覆盖用户正在输入的草稿。
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile?.asset_id, profile?.name, profile?.description, profile?.tags])

  if (query.isLoading) return <PanelLoading lines={7} label={`加载${WORKBENCH_ASSET_LABELS[assetType]}档案`} />
  if (query.isError) {
    return (
      <PanelError
        message={query.error instanceof Error ? query.error.message : '资产档案加载失败'}
        onRetry={() => void query.refetch()}
      />
    )
  }
  if (!profile) {
    return <PanelError message="资产不存在或不属于当前项目" onRetry={() => void query.refetch()} />
  }

  const saveProfile = () => {
    setNotice('')
    actions.update.mutate(
      {
        name: form.name,
        description: form.description,
        age_range: form.age_range,
        appearance: form.appearance,
        face_features: form.face_features,
        body_type: form.body_type,
        identity_features: form.identity_features,
        tags: form.tags.split(/[，,]/).map((item) => item.trim()).filter(Boolean),
      },
      {
        onSuccess: () => setNotice('档案已保存'),
        onError: (error) => setNotice(error instanceof Error ? error.message : '保存失败'),
      },
    )
  }

  const generate = () => {
    setNotice('')
    actions.generate.mutate(
      { viewAngle: angle },
      {
        onSuccess: () => setNotice('已创建 2 个候选任务；完成后候选列表自动更新'),
        onError: (error) => setNotice(error instanceof Error ? error.message : '候选生成失败'),
      },
    )
  }

  const upload = async (file: File) => {
    setUploading(true)
    setNotice('')
    try {
      await actions.upload.mutateAsync({
        file,
        viewAngle: angle,
        versionId: targetVersionId,
      })
      setNotice('图片已上传为候选；请确认后再选用')
    } catch (error) {
      setNotice(error instanceof Error ? error.message : '上传失败')
    } finally {
      setUploading(false)
    }
  }

  const createVersion = () => {
    if (!versionName.trim()) {
      setNotice('请填写版本名称')
      return
    }
    setNotice('')
    const body = {
      name: versionName.trim(),
      description: versionDescription,
      variant_type: (isCharacter && identityDraftMode ? 'base' : variantType) as
        | 'base'
        | 'costume'
        | 'hairstyle'
        | 'makeup'
        | 'age'
        | 'weather'
        | 'lighting'
        | 'other',
      costume_id: costumeId || null,
      activate: !(isCharacter && identityDraftMode),
      attributes: {},
    }
    const mutation = isCharacter && identityDraftMode
      ? actions.createIdentityVersion
      : actions.createVersion
    mutation.mutate(body, {
      onSuccess: () => {
        setVersionName('')
        setVersionDescription('')
        setCostumeId('')
        setIdentityDraftMode(false)
        setNotice(isCharacter && identityDraftMode ? '身份草稿已创建；采纳正面图后切换' : '新版本已创建')
      },
      onError: (error) => setNotice(error instanceof Error ? error.message : '创建版本失败'),
    })
  }

  const busy =
    actions.update.isPending ||
    actions.addAlias.isPending ||
    actions.removeAlias.isPending ||
    actions.generate.isPending ||
    actions.upload.isPending ||
    actions.adopt.isPending ||
    actions.removeCandidate.isPending ||
    actions.createVersion.isPending ||
    actions.createIdentityVersion.isPending ||
    actions.switchVersion.isPending ||
    actions.lock.isPending ||
    actions.updateVoice.isPending

  return (
    <div className="space-y-4">
      <PanelHeader
        title={profile.name || '未命名资产'}
        description={`${WORKBENCH_ASSET_LABELS[assetType]} · 角色圣经与资产版本`}
        actions={
          <>
            <Button variant="ghost" size="sm" onClick={() => onNavigate(workbenchAssetGroupPath(projectId, assetType))}>
              <ArrowLeft className="h-3.5 w-3.5" />
              返回列表
            </Button>
            <Button variant="outline" size="sm" onClick={() => void query.refetch()} disabled={query.isFetching}>
              <RefreshCw className={query.isFetching ? 'h-3.5 w-3.5 animate-spin' : 'h-3.5 w-3.5'} />
              刷新
            </Button>
            <LegacyLink href={legacyAssetEditPath(projectId, assetType, assetId)}>
              <ExternalLink className="h-3.5 w-3.5" />
              旧版编辑
            </LegacyLink>
          </>
        }
      />

      <div className="flex flex-wrap items-center gap-2 text-[11px]">
        <Badge variant={locked ? 'secondary' : 'outline'}>{locked ? '视觉身份已锁定' : '视觉身份未锁定'}</Badge>
        {isCharacter ? (
          <Badge variant="outline" className="font-normal">
            {profile.effective_voice_id ? `音色 ${profile.effective_voice_id}` : '音色未绑定'}
          </Badge>
        ) : null}
        <span className="text-muted-foreground">当前版本：{profile.current_version_id?.slice(0, 12) ?? '—'}</span>
      </div>
      {notice ? (
        <div className="rounded-md border border-state-pending/40 bg-state-pending/10 p-2 text-[11px] text-state-pending">
          {notice}
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between gap-2">
                <CardTitle className="text-sm">基础身份</CardTitle>
                {locked ? (
                  <Badge variant="outline" className="font-normal">
                    <Lock className="mr-1 h-3 w-3" /> 核心字段只读
                  </Badge>
                ) : null}
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="grid gap-2 md:grid-cols-2">
                <Field label="角色名称" value={form.name} onChange={(value) => setForm((prev) => ({ ...prev, name: value }))} disabled={locked} />
                <Field label="年龄感" value={form.age_range} onChange={(value) => setForm((prev) => ({ ...prev, age_range: value }))} disabled={locked} />
                <Field label="基础体型" value={form.body_type} onChange={(value) => setForm((prev) => ({ ...prev, body_type: value }))} disabled={locked} />
                <Field label="标签（逗号分隔）" value={form.tags} onChange={(value) => setForm((prev) => ({ ...prev, tags: value }))} />
              </div>
              <Field label="角色描述" value={form.description} onChange={(value) => setForm((prev) => ({ ...prev, description: value }))} disabled={locked} multiline />
              {isCharacter ? (
                <>
                  <Field label="基础外貌" value={form.appearance} onChange={(value) => setForm((prev) => ({ ...prev, appearance: value }))} disabled={locked} multiline />
                  <Field label="脸型与五官" value={form.face_features} onChange={(value) => setForm((prev) => ({ ...prev, face_features: value }))} disabled={locked} multiline />
                  <Field label="固定身份特征" value={form.identity_features} onChange={(value) => setForm((prev) => ({ ...prev, identity_features: value }))} disabled={locked} multiline />
                </>
              ) : null}
              <div className="flex flex-wrap items-center gap-1.5">
                <Button size="sm" className="h-7 px-2 text-[11px]" onClick={saveProfile} disabled={busy}>
                  保存档案
                </Button>
                {isCharacter ? (
                  <Button
                    size="sm"
                    variant={locked ? 'outline' : 'secondary'}
                    className="h-7 px-2 text-[11px]"
                    disabled={busy || locked}
                    onClick={() => {
                      if (!window.confirm('锁定后基础身份字段与当前身份正面图不可直接覆盖，确定锁定？')) return
                      actions.lock.mutate(profile.identity_lock_version ?? 0, {
                        onSuccess: () => setNotice('视觉身份已锁定；音色、造型和辅助视角仍可继续维护'),
                        onError: (error) => setNotice(error instanceof Error ? error.message : '锁定失败'),
                      })
                    }}
                  >
                    <Lock className="h-3 w-3" />
                    锁定视觉身份
                  </Button>
                ) : null}
              </div>
            </CardContent>
          </Card>

          {isCharacter ? (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">别名与称谓</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex flex-wrap gap-1">
                  {(profile.aliases ?? []).map((item) => (
                    <span key={item.id} className="inline-flex items-center gap-1 rounded-full border border-border px-2 py-0.5 text-[11px]">
                      {item.alias}
                      <button
                        type="button"
                        className="text-muted-foreground hover:text-ready-blocked"
                        onClick={() => actions.removeAlias.mutate(item.id)}
                        aria-label={`删除别名 ${item.alias}`}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                  {(profile.aliases ?? []).length === 0 ? <span className="text-[11px] text-muted-foreground">暂未维护别名</span> : null}
                </div>
                <div className="flex gap-1.5">
                  <Input
                    value={alias}
                    onChange={(event) => setAlias(event.target.value)}
                    placeholder="如：沈总、总裁"
                    className="h-8 text-xs"
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-8 px-2 text-[11px]"
                    disabled={!alias.trim() || busy}
                    onClick={() =>
                      actions.addAlias.mutate(alias.trim(), {
                        onSuccess: () => {
                          setAlias('')
                          setNotice('别名已保存；后续剧本解析可参与匹配')
                        },
                        onError: (error) => setNotice(error instanceof Error ? error.message : '别名保存失败'),
                      })
                    }
                  >
                    添加
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : null}

          {isCharacter ? <VoiceSection projectId={projectId} profile={profile} /> : null}

          <VersionList
            profile={profile}
            busy={busy}
            isCharacter={isCharacter}
            onSwitch={(version) =>
              actions.switchVersion.mutate(
                {
                  versionId: version.id,
                  expectedLockVersion: isCharacter ? profile.identity_lock_version : undefined,
                },
                {
                  onSuccess: () => setNotice('当前版本已切换；历史版本与已生成视频保留'),
                  onError: (error) => setNotice(error instanceof Error ? error.message : '切换失败'),
                },
              )
            }
            onCreate={() => setVersionName('')}
          />
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Sparkles className="h-4 w-4 text-muted-foreground" />
                图片候选
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-wrap items-end gap-2">
                <div className="space-y-1">
                  <label className="text-[11px] text-muted-foreground">生成视角</label>
                  <Select value={angle} onChange={(event) => setAngle(event.target.value)} className="h-8 text-xs">
                    {ANGLE_OPTIONS.map((item) => (
                      <option key={item.value} value={item.value}>{item.label}</option>
                    ))}
                  </Select>
                </div>
                <Button size="sm" className="h-8 text-[11px]" onClick={generate} disabled={busy}>
                  <Sparkles className="h-3.5 w-3.5" />
                  生成 2 张候选
                </Button>
                <Button size="sm" variant="outline" className="h-8 text-[11px]" onClick={() => uploadRef.current?.click()} disabled={busy || uploading}>
                  <Upload className="h-3.5 w-3.5" />
                  {uploading ? '上传中…' : '上传图片'}
                </Button>
                <input
                  ref={uploadRef}
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/gif"
                  className="hidden"
                  onChange={(event) => {
                    const file = event.target.files?.[0]
                    event.target.value = ''
                    if (file) void upload(file)
                  }}
                />
              </div>
              <div className="space-y-1">
                <label className="text-[11px] text-muted-foreground">采纳/上传目标版本</label>
                <Select
                  value={targetVersionId ?? ''}
                  onChange={(event) => setTargetVersionId(event.target.value || null)}
                  className="h-8 text-xs"
                >
                  {(profile.versions ?? []).map((version) => (
                    <option key={version.id} value={version.id}>
                      v{version.version_no} · {version.name || version.id.slice(0, 8)} · {version.status}
                    </option>
                  ))}
                </Select>
              </div>
              {profile.thumbnail ? (
                <div className="flex h-52 items-center justify-center overflow-hidden rounded-md border border-border bg-muted/30">
                  <img src={profile.thumbnail} alt={profile.name} className="h-full w-full object-contain" />
                </div>
              ) : null}
              <ScrollArea className="max-h-[42vh] pr-1">
                <div className="grid gap-2 sm:grid-cols-2">
                  {(profile.candidates ?? []).map((candidate) => (
                    <CandidateCard
                      key={candidate.id}
                      candidate={candidate}
                      busy={busy}
                      onAdopt={() =>
                        actions.adopt.mutate(
                          { candidateId: candidate.id, versionId: targetVersionId },
                          {
                            onSuccess: () => setNotice('候选已采纳为当前图片'),
                            onError: (error) => setNotice(error instanceof Error ? error.message : '采纳失败'),
                          },
                        )
                      }
                      onDelete={() =>
                        actions.removeCandidate.mutate(candidate.id, {
                          onError: (error) => setNotice(error instanceof Error ? error.message : '删除失败'),
                        })
                      }
                      onLocatePrompt={() => undefined}
                    />
                  ))}
                </div>
              </ScrollArea>
              {(profile.candidates ?? []).length === 0 ? (
                <p className="text-[11px] text-muted-foreground">还没有候选图。生成默认两张，或上传已有图片；上传不会自动锁定。</p>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">新增版本 / 造型</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="grid gap-2 md:grid-cols-2">
                <Field label="版本名称" value={versionName} onChange={setVersionName} placeholder={isCharacter ? '晚宴造型 / 十年前' : '夜晚办公室'} />
                {isCharacter ? (
                  <div className="space-y-1">
                    <label className="text-[11px] text-muted-foreground">类型</label>
                    <Select value={variantType} onChange={(event) => setVariantType(event.target.value)} className="h-8 text-xs">
                      {VARIANT_OPTIONS.map((item) => (
                        <option key={item.value} value={item.value}>{item.label}</option>
                      ))}
                    </Select>
                  </div>
                ) : (
                  <div className="space-y-1">
                    <label className="text-[11px] text-muted-foreground">衍生类型</label>
                    <Select value={variantType} onChange={(event) => setVariantType(event.target.value)} className="h-8 text-xs">
                      {VARIANT_OPTIONS.map((item) => (
                        <option key={item.value} value={item.value}>{item.label}</option>
                      ))}
                    </Select>
                  </div>
                )}
              </div>
              {isCharacter ? (
                <>
                  <div className="space-y-1">
                    <label className="text-[11px] text-muted-foreground">关联服装（可选）</label>
                    <Select value={costumeId} onChange={(event) => setCostumeId(event.target.value)} className="h-8 text-xs">
                      <option value="">不关联</option>
                      {(costumesQuery.data ?? []).map((item) => (
                        <option key={item.id} value={item.id}>{item.name}</option>
                      ))}
                    </Select>
                  </div>
                  <label className="flex items-center gap-2 text-[11px]">
                    <input
                      type="checkbox"
                      checked={identityDraftMode}
                      onChange={(event) => setIdentityDraftMode(event.target.checked)}
                    />
                    创建新的身份草稿（不立即切换）
                  </label>
                </>
              ) : null}
              <Field label="版本描述" value={versionDescription} onChange={setVersionDescription} multiline />
              <Button size="sm" className="h-7 px-2 text-[11px]" onClick={createVersion} disabled={busy || !versionName.trim()}>
                创建版本
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
