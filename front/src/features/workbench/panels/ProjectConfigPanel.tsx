/**
 * 项目配置面板（P2）。
 *
 * 目标：用户在工作台内完成模型、输出规格、生成策略的配置与确认，
 * 不再跳到旧版 antd 设置页。
 *
 * 关键规则：
 * - 项目模型优先、全局默认兜底；保存时显式记录项目选择；
 * - 供应商能力（比例/分辨率/时长）来自后端，前端不写死枚举；
 * - 业务时长范围固定 4–15 秒，与供应商能力取交集；
 * - 保存草稿允许不完整；确认必须在服务端检查全部通过；
 * - 表单失败不清空用户输入，刷新后以服务端值为准。
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { AlertCircle, CheckCircle2, ExternalLink, RefreshCw, Save, ShieldCheck } from 'lucide-react'
import { Button } from '../../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card'
import { Checkbox } from '../../../components/ui/checkbox'
import { Input } from '../../../components/ui/input'
import { Select } from '../../../components/ui/select'
import { cn } from '../../../lib/utils'
import type {
  EffectiveGenerationModelRead,
  GenerationModelOptionRead,
  ProjectGenerationConfigRead,
  ProjectGenerationConfigUpdate,
} from '../../../services/generated'
import { LegacyLink, PanelHeader } from '../components/PanelHeader'
import { PanelError, PanelLoading, StageNote } from '../components/PanelStates'
import {
  useSaveGenerationConfig,
  useWorkbenchGenerationConfig,
  useWorkbenchGenerationOptions,
} from '../useWorkbenchQueries'

interface ConfigForm {
  imageModelId: string
  videoModelId: string
  audioModelId: string
  videoRatio: string
  videoResolution: string
  imageRatio: string
  imageResolutionProfile: string
  shotDuration: number
  concurrency: number
  referenceMode: string
  audioReference: boolean
}

function toForm(config: ProjectGenerationConfigRead): ConfigForm {
  const explicit = (model: EffectiveGenerationModelRead) =>
    model.source === 'project' ? model.model_id ?? '' : ''
  return {
    imageModelId: explicit(config.image_model),
    videoModelId: explicit(config.video_model),
    audioModelId: explicit(config.audio_model),
    videoRatio: config.output.video_ratio ?? '',
    videoResolution: config.output.video_resolution ?? '',
    imageRatio: config.output.image_ratio ?? '',
    imageResolutionProfile: config.output.image_resolution_profile ?? '',
    shotDuration: config.policy.default_shot_duration,
    concurrency: config.policy.video_concurrency,
    referenceMode: config.policy.reference_mode,
    audioReference: config.policy.use_dialog_audio_as_reference,
  }
}

function modelLabel(model: GenerationModelOptionRead): string {
  const status = model.available ? '' : `（${model.unavailable_reason || '不可用'}）`
  return `${model.name} · ${model.provider_name}${status}`
}

function effectiveLabel(model: EffectiveGenerationModelRead): string {
  if (!model.model_id) return '未配置'
  const source = model.source === 'project' ? '项目' : model.source === 'global' ? '全局默认' : '未知'
  return `${model.model_name || model.model_id}（${model.provider_name || '未知供应商'} · ${source}）`
}

/** 表单里的模型 ID 为空表示「跟随全局默认」；选项里需要显式给出这个语义。 */
function globalOptionLabel(
  categoryLabel: string,
  options: GenerationModelOptionRead[],
  globalId: string | null | undefined,
): string {
  const globalModel = options.find((item) => item.id === globalId)
  return globalModel
    ? `跟随全局默认（${globalModel.name}）`
    : `跟随全局默认（未配置${categoryLabel}模型）`
}

export function ProjectConfigPanel({
  projectId,
}: {
  projectId: string
}) {
  const configQuery = useWorkbenchGenerationConfig(projectId)
  const optionsQuery = useWorkbenchGenerationOptions(projectId)
  const saveMutation = useSaveGenerationConfig(projectId)

  const [form, setForm] = useState<ConfigForm | null>(null)
  const [baseline, setBaseline] = useState<string>('')
  const [notice, setNotice] = useState<{ tone: 'ok' | 'error'; text: string } | null>(null)
  const lastResetKey = useRef('')

  const config = configQuery.data
  const options = optionsQuery.data
  const imageModels = useMemo(() => options?.image_models ?? [], [options?.image_models])
  const videoModels = useMemo(() => options?.video_models ?? [], [options?.video_models])
  const audioModels = useMemo(() => options?.audio_models ?? [], [options?.audio_models])
  const globalDefaults = options?.global_defaults ?? {}

  /** 服务端值变化（首次加载 / 保存后）时重置表单；用户编辑期间不会被后台轮询覆盖。 */
  useEffect(() => {
    if (!config) return
    const key = `${config.version}:${config.updated_at ?? ''}`
    if (key === lastResetKey.current) return
    lastResetKey.current = key
    const next = toForm(config)
    setForm(next)
    setBaseline(JSON.stringify(next))
  }, [config])

  const dirty = form !== null && JSON.stringify(form) !== baseline

  const business = options?.business
  const selectedImage = useMemo(
    () =>
      form?.imageModelId
        ? imageModels.find((item) => item.id === form.imageModelId)
        : imageModels.find((item) => item.id === globalDefaults.image_model_id),
    [form?.imageModelId, imageModels, globalDefaults.image_model_id],
  )
  const selectedVideo = useMemo(
    () =>
      form?.videoModelId
        ? videoModels.find((item) => item.id === form.videoModelId)
        : videoModels.find((item) => item.id === globalDefaults.video_model_id),
    [form?.videoModelId, videoModels, globalDefaults.video_model_id],
  )
  const selectedAudio = useMemo(
    () =>
      form?.audioModelId
        ? audioModels.find((item) => item.id === form.audioModelId)
        : audioModels.find((item) => item.id === globalDefaults.audio_model_id),
    [form?.audioModelId, audioModels, globalDefaults.audio_model_id],
  )

  const videoRatios = useMemo(
    () =>
      selectedVideo?.allowed_ratios?.length
        ? selectedVideo.allowed_ratios
        : config?.output.video_ratios ?? [],
    [selectedVideo, config?.output.video_ratios],
  )
  const videoResolutions = useMemo(
    () =>
      selectedVideo?.allowed_resolutions?.length
        ? selectedVideo.allowed_resolutions
        : config?.output.video_resolutions ?? [],
    [selectedVideo, config?.output.video_resolutions],
  )
  const imageRatios = useMemo(
    () =>
      selectedImage?.allowed_ratios?.length
        ? selectedImage.allowed_ratios
        : config?.output.image_ratios ?? [],
    [selectedImage, config?.output.image_ratios],
  )
  const imageProfiles = useMemo(
    () =>
      selectedImage?.ratio_size_profiles &&
      Object.keys(selectedImage.ratio_size_profiles).length > 0
        ? Array.from(
            new Set(
              Object.values(selectedImage.ratio_size_profiles).flatMap((item) =>
                Object.keys(item),
              ),
            ),
          )
        : config?.output.image_resolution_profiles ?? [],
    [selectedImage, config?.output.image_resolution_profiles],
  )

  const durationMin = Math.max(
    business?.duration_min ?? 4,
    selectedVideo?.min_seconds ?? business?.duration_min ?? 4,
  )
  const durationMax = Math.min(
    business?.duration_max ?? 15,
    selectedVideo?.max_seconds ?? business?.duration_max ?? 15,
  )

  /** 前端只做「提交前就能发现」的校验；最终仍以服务端能力校验为准。 */
  const validationErrors = useMemo(() => {
    if (!form) return []
    const errors: string[] = []
    if (!selectedImage) errors.push('未选择图片模型，且全局默认图片模型未配置')
    else if (!selectedImage.available) errors.push(`图片模型不可用：${selectedImage.unavailable_reason}`)
    if (!selectedVideo) errors.push('未选择视频模型，且全局默认视频模型未配置')
    else if (!selectedVideo.available) errors.push(`视频模型不可用：${selectedVideo.unavailable_reason}`)
    if (!selectedAudio) errors.push('未选择音频模型，且全局默认音频模型未配置')
    else if (!selectedAudio.available) errors.push(`音频模型不可用：${selectedAudio.unavailable_reason}`)

    if (form.shotDuration < durationMin || form.shotDuration > durationMax) {
      errors.push(`默认时长需在 ${durationMin}–${durationMax} 秒内`)
    }
    if (form.concurrency < 1 || form.concurrency > (business?.max_concurrency ?? 16)) {
      errors.push(`并发数需在 1–${business?.max_concurrency ?? 16} 之间`)
    }
    if (videoRatios.length && !videoRatios.includes(form.videoRatio)) {
      errors.push('视频比例不在当前模型支持范围内')
    }
    if (videoResolutions.length && !videoResolutions.includes(form.videoResolution)) {
      errors.push('视频分辨率不在当前模型支持范围内')
    }
    if (imageRatios.length && !imageRatios.includes(form.imageRatio)) {
      errors.push('图片比例不在当前图片模型支持范围内')
    }
    if (imageProfiles.length && !imageProfiles.includes(form.imageResolutionProfile)) {
      errors.push('图片清晰度不在当前图片模型支持范围内')
    }
    return errors
  }, [
    form,
    selectedImage,
    selectedVideo,
    selectedAudio,
    durationMin,
    durationMax,
    business?.max_concurrency,
    videoRatios,
    videoResolutions,
    imageRatios,
    imageProfiles,
  ])

  if (configQuery.isLoading || optionsQuery.isLoading) {
    return <PanelLoading lines={8} label="加载项目配置" />
  }
  if (configQuery.isError || optionsQuery.isError) {
    return (
      <PanelError
        message={
          (configQuery.error ?? optionsQuery.error) instanceof Error
            ? ((configQuery.error ?? optionsQuery.error) as Error).message
            : '项目配置加载失败'
        }
        onRetry={() => {
          void configQuery.refetch()
          void optionsQuery.refetch()
        }}
      />
    )
  }
  if (!config || !options || !form || !business) {
    return <PanelError message="项目配置为空" onRetry={() => void configQuery.refetch()} />
  }

  const updateField = <K extends keyof ConfigForm>(key: K, value: ConfigForm[K]) => {
    setNotice(null)
    setForm((prev) => (prev ? { ...prev, [key]: value } : prev))
  }

  /** 切换模型时同步收敛比例/分辨率，避免保留上一个模型不支持的选项。 */
  const changeImageModel = (id: string) => {
    const next = id ? imageModels.find((item) => item.id === id) : undefined
    const ratios = next?.allowed_ratios?.length ? next.allowed_ratios : imageRatios
    const profiles = next?.ratio_size_profiles &&
      Object.keys(next.ratio_size_profiles).length > 0
      ? Array.from(new Set(Object.values(next.ratio_size_profiles).flatMap((item) => Object.keys(item))))
      : imageProfiles
    setForm((prev) =>
      prev
        ? {
            ...prev,
            imageModelId: id,
            imageRatio: ratios.includes(prev.imageRatio) ? prev.imageRatio : ratios[0] ?? '',
            imageResolutionProfile: profiles.includes(prev.imageResolutionProfile)
              ? prev.imageResolutionProfile
              : profiles[0] ?? '',
          }
        : prev,
    )
    setNotice(null)
  }

  const changeVideoModel = (id: string) => {
    const next = id ? videoModels.find((item) => item.id === id) : undefined
    const ratios = next?.allowed_ratios?.length ? next.allowed_ratios : videoRatios
    const resolutions = next?.allowed_resolutions?.length
      ? next.allowed_resolutions
      : videoResolutions
    const nextMin = Math.max(business.duration_min, next?.min_seconds ?? business.duration_min)
    const nextMax = Math.min(business.duration_max, next?.max_seconds ?? business.duration_max)
    setForm((prev) =>
      prev
        ? {
            ...prev,
            videoModelId: id,
            videoRatio: ratios.includes(prev.videoRatio) ? prev.videoRatio : ratios[0] ?? '',
            videoResolution: resolutions.includes(prev.videoResolution)
              ? prev.videoResolution
              : resolutions[0] ?? '',
            shotDuration: Math.min(nextMax, Math.max(nextMin, prev.shotDuration)),
          }
        : prev,
    )
    setNotice(null)
  }

  const buildPayload = (confirm: boolean): ProjectGenerationConfigUpdate => ({
    default_image_model_id: form.imageModelId || null,
    default_video_model_id: form.videoModelId || null,
    default_audio_model_id: form.audioModelId || null,
    default_video_ratio: form.videoRatio || null,
    default_video_resolution: form.videoResolution || null,
    default_image_ratio: form.imageRatio || null,
    default_image_resolution_profile: form.imageResolutionProfile || null,
    default_shot_duration: form.shotDuration,
    video_concurrency: form.concurrency,
    default_reference_mode: form.referenceMode,
    use_dialog_audio_as_reference: form.audioReference,
    confirm,
  })

  const submit = (confirm: boolean) => {
    setNotice(null)
    saveMutation.mutate(buildPayload(confirm), {
      onSuccess: (saved) => {
        const next = toForm(saved)
        lastResetKey.current = `${saved.version}:${saved.updated_at ?? ''}`
        setForm(next)
        setBaseline(JSON.stringify(next))
        setNotice({
          tone: 'ok',
          text: confirm
            ? `配置已保存并确认（v${saved.version}）`
            : '草稿已保存；确认后才会建立配置快照',
        })
      },
      onError: (error) => {
        setNotice({
          tone: 'error',
          text: error instanceof Error ? error.message : '保存失败，请检查配置',
        })
      },
    })
  }

  const failedChecks = config.checks?.filter((check) => !check.ok) ?? []
  const statusText = dirty
    ? '有未保存修改'
    : config.initialized
      ? '已初始化'
      : config.confirmed
        ? '已确认'
        : '未确认'
  const statusTone = dirty
    ? 'border-state-pending/40 bg-state-pending/10 text-state-pending'
    : config.initialized
      ? 'border-ready-complete/40 bg-ready-complete/10 text-ready-complete'
      : 'border-state-pending/40 bg-state-pending/10 text-state-pending'

  const missingModels =
    imageModels.length === 0 ||
    videoModels.length === 0 ||
    audioModels.length === 0

  /** 预览跟随表单：用户切换模型后不必先保存才能看到生效对象。 */
  const previewModelLabel = (
    selected: GenerationModelOptionRead | undefined,
    explicitId: string,
    fallback: EffectiveGenerationModelRead,
  ) => {
    if (!selected) return effectiveLabel(fallback)
    const source = explicitId ? '项目' : '全局默认'
    return `${selected.name}（${selected.provider_name} · ${source}）`
  }

  return (
    <div className="space-y-4">
      <PanelHeader
        title="项目配置"
        description="选择本项目实际使用的模型与输出规格。保存并确认后建立项目级快照，后续修改全局默认不会改变本项目。"
        badge={
          <span className={cn('rounded-full border px-2 py-0.5 text-[11px] font-medium', statusTone)}>
            {statusText}
          </span>
        }
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                void configQuery.refetch()
                void optionsQuery.refetch()
              }}
              disabled={configQuery.isFetching || optionsQuery.isFetching}
            >
              <RefreshCw
                className={cn(
                  'h-3.5 w-3.5',
                  (configQuery.isFetching || optionsQuery.isFetching) && 'animate-spin',
                )}
              />
              刷新
            </Button>
            <LegacyLink href={`/projects/${projectId}?tab=settings`}>
              <ExternalLink className="h-3.5 w-3.5" />
              旧版设置（只读对照）
            </LegacyLink>
          </>
        }
      />

      {missingModels ? (
        <div className="flex items-start gap-2 rounded-md border border-state-pending/40 bg-state-pending/10 p-3 text-xs">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-state-pending" />
          <div>
            <p className="font-medium">模型目录不完整</p>
            <p className="mt-0.5 text-muted-foreground">
              请先在模型管理中配置对应类别的供应商与模型；系统不会自动创建未经核实的模型。
            </p>
            <a
              href="/models"
              target="_blank"
              rel="noreferrer"
              className="mt-1 inline-flex items-center gap-1 text-primary hover:underline"
            >
              打开模型管理
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>
      ) : null}

      {notice ? (
        <div
          className={cn(
            'flex items-start gap-2 rounded-md border p-3 text-xs',
            notice.tone === 'ok'
              ? 'border-ready-complete/40 bg-ready-complete/10 text-ready-complete'
              : 'border-ready-blocked/40 bg-ready-blocked/10 text-ready-blocked',
          )}
          role="status"
        >
          {notice.tone === 'ok' ? (
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          ) : (
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          )}
          <span className="whitespace-pre-wrap">{notice.text}</span>
        </div>
      ) : null}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">模型配置</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-3">
          <Field label="图片模型" hint={selectedImage ? `当前能力：${(selectedImage.allowed_ratios ?? []).join(' / ') || '未声明'}` : '未配置'}>
            <Select
              value={form.imageModelId}
              onChange={(event) => changeImageModel(event.target.value)}
            >
              <option value="">
                {globalOptionLabel('图片', imageModels, globalDefaults.image_model_id)}
              </option>
              {imageModels.map((model) => (
                <option key={model.id} value={model.id} disabled={!model.available}>
                  {modelLabel(model)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="视频模型" hint={selectedVideo ? `供应商时长：${selectedVideo.min_seconds ?? '?'}–${selectedVideo.max_seconds ?? '?'} 秒` : '未配置'}>
            <Select
              value={form.videoModelId}
              onChange={(event) => changeVideoModel(event.target.value)}
            >
              <option value="">
                {globalOptionLabel('视频', videoModels, globalDefaults.video_model_id)}
              </option>
              {videoModels.map((model) => (
                <option key={model.id} value={model.id} disabled={!model.available}>
                  {modelLabel(model)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="音频模型" hint={selectedAudio?.provider_name ?? '未配置'}>
            <Select
              value={form.audioModelId}
              onChange={(event) => updateField('audioModelId', event.target.value)}
            >
              <option value="">
                {globalOptionLabel('音频', audioModels, globalDefaults.audio_model_id)}
              </option>
              {audioModels.map((model) => (
                <option key={model.id} value={model.id} disabled={!model.available}>
                  {modelLabel(model)}
                </option>
              ))}
            </Select>
          </Field>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">输出规格</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-2">
          <Field label="视频比例">
            <Select
              value={form.videoRatio}
              onChange={(event) => updateField('videoRatio', event.target.value)}
            >
              {videoRatios.length === 0 ? <option value="">暂无可选项</option> : null}
              {videoRatios.map((ratio) => (
                <option key={ratio} value={ratio}>
                  {ratio}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="视频分辨率">
            <Select
              value={form.videoResolution}
              onChange={(event) => updateField('videoResolution', event.target.value)}
            >
              {videoResolutions.length === 0 ? <option value="">供应商默认</option> : null}
              {videoResolutions.map((resolution) => (
                <option key={resolution} value={resolution}>
                  {resolution.toUpperCase()}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="图片比例">
            <Select
              value={form.imageRatio}
              onChange={(event) => updateField('imageRatio', event.target.value)}
            >
              {imageRatios.length === 0 ? <option value="">暂无可选项</option> : null}
              {imageRatios.map((ratio) => (
                <option key={ratio} value={ratio}>
                  {ratio}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="图片清晰度">
            <Select
              value={form.imageResolutionProfile}
              onChange={(event) => updateField('imageResolutionProfile', event.target.value)}
            >
              {imageProfiles.length === 0 ? <option value="">供应商默认</option> : null}
              {imageProfiles.map((profile) => (
                <option key={profile} value={profile}>
                  {profile === 'high' ? '高清（2K）' : profile === 'standard' ? '标准（1K）' : profile}
                </option>
              ))}
            </Select>
          </Field>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">生成策略</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-2">
          <Field
            label="默认镜头时长（秒）"
            hint={`业务范围 ${business.duration_min}–${business.duration_max} 秒；当前模型可用 ${durationMin}–${durationMax} 秒`}
          >
            <Input
              type="number"
              min={durationMin}
              max={durationMax}
              value={form.shotDuration}
              onChange={(event) =>
                updateField('shotDuration', Number(event.target.value) || 0)
              }
            />
          </Field>
          <Field
            label="视频批量并发数"
            hint={`默认 ${business.default_concurrency}；上限 ${business.max_concurrency}（真实并发仍受供应商配额约束）`}
          >
            <Input
              type="number"
              min={1}
              max={business.max_concurrency}
              value={form.concurrency}
              onChange={(event) =>
                updateField('concurrency', Number(event.target.value) || 0)
              }
            />
          </Field>
          <Field label="默认参考模式" hint="P2 固定多参考模式；首尾帧模式按镜头单独选择">
            <Select
              value={form.referenceMode}
              onChange={(event) => updateField('referenceMode', event.target.value)}
              disabled
            >
              {business.allowed_reference_modes.map((mode) => (
                <option key={mode} value={mode}>
                  {mode === 'reference' ? '多参考（reference）' : mode}
                </option>
              ))}
            </Select>
          </Field>
          <div className="space-y-1.5">
            <label className="flex items-start gap-2 text-sm">
              <Checkbox
                checked={form.audioReference}
                onCheckedChange={(checked) => updateField('audioReference', checked === true)}
                className="mt-0.5"
              />
              <span>
                使用角色音色作为参考音频
                <span className="mt-0.5 block text-[11px] font-normal leading-4 text-muted-foreground">
                  默认关闭。开启后，按镜头对白说话人读取角色固定音色样本作为 H3 音色参考；样本缺失会阻止 P6 生成，最终对白仍由 H3 生成。
                </span>
              </span>
            </label>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">生效值预览</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1.5 text-xs">
            <PreviewRow
              label="图片模型"
              value={previewModelLabel(selectedImage, form.imageModelId, config.image_model)}
            />
            <PreviewRow
              label="视频模型"
              value={previewModelLabel(selectedVideo, form.videoModelId, config.video_model)}
            />
            <PreviewRow
              label="音频模型"
              value={previewModelLabel(selectedAudio, form.audioModelId, config.audio_model)}
            />
            <PreviewRow label="视频规格" value={`${form.videoRatio || '—'} · ${form.videoResolution || '供应商默认'}`} />
            <PreviewRow label="图片规格" value={`${form.imageRatio || '—'} · ${form.imageResolutionProfile || '供应商默认'}`} />
            <PreviewRow label="默认时长" value={`${form.shotDuration}s（允许 ${durationMin}–${durationMax}s）`} />
            <PreviewRow label="并发 / 参考" value={`${form.concurrency} · ${form.referenceMode}`} />
            <PreviewRow
              label="音频参考"
              value={form.audioReference ? '开启' : '关闭'}
            />
            <PreviewRow
              label="配置版本"
              value={`v${config.version}${config.confirmed_at ? ` · 已确认` : ' · 未确认'}`}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <ShieldCheck className="h-4 w-4 text-muted-foreground" />
              初始化检查
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1.5">
            {validationErrors.length ? (
              <div className="rounded-md border border-ready-blocked/40 bg-ready-blocked/10 p-2 text-[11px] text-ready-blocked">
                <p className="font-medium">保存前需要修正：</p>
                <ul className="mt-1 list-disc space-y-0.5 pl-4">
                  {validationErrors.map((error) => (
                    <li key={error}>{error}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            {config.checks?.length ? (
              <ul className="space-y-1 text-[11px]">
                {config.checks.map((check) => (
                  <li key={check.key} className="flex items-start gap-1.5">
                    {check.ok ? (
                      <CheckCircle2 className="mt-0.5 h-3 w-3 shrink-0 text-ready-complete" />
                    ) : (
                      <AlertCircle className="mt-0.5 h-3 w-3 shrink-0 text-ready-blocked" />
                    )}
                    <span className={cn(!check.ok && 'text-muted-foreground')}>
                      {check.label}：{check.message}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-muted-foreground">保存后显示逐项检查结果。</p>
            )}
            <p className="pt-1 text-[10px] leading-4 text-muted-foreground">
              检查结果来自上次保存；修改表单后请重新保存。风格锁定状态在「风格圣经」面板查看。
            </p>
          </CardContent>
        </Card>
      </div>

      <StageNote stage="P2">
        确认后写入项目级快照；修改全局默认模型不会改变本项目。风格锁定与参考图分析在「风格圣经」面板完成。
      </StageNote>
      <div className="sticky bottom-0 z-10 flex flex-wrap items-center gap-2 border-t border-border bg-background/95 py-3 backdrop-blur">
        <Button
          variant="outline"
          size="sm"
          onClick={() => submit(false)}
          disabled={saveMutation.isPending || validationErrors.some((item) => item.includes('时长') || item.includes('并发数'))}
        >
          <Save className="h-3.5 w-3.5" />
          保存草稿
        </Button>
        <Button
          size="sm"
          onClick={() => submit(true)}
          disabled={saveMutation.isPending || validationErrors.length > 0}
        >
          <ShieldCheck className="h-3.5 w-3.5" />
          {saveMutation.isPending ? '保存中…' : '保存并确认'}
        </Button>
        {dirty ? (
          <span className="text-[11px] text-state-pending">有未保存修改</span>
        ) : (
          <span className="text-[11px] text-muted-foreground">当前表单与服务端一致</span>
        )}
        {failedChecks.length > 0 && !dirty ? (
          <span className="text-[11px] text-ready-blocked">
            {failedChecks.length} 项检查未通过
          </span>
        ) : null}
      </div>
    </div>
  )
}

function Field({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: ReactNode
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-sm font-medium">{label}</label>
      {children}
      {hint ? <p className="text-[11px] leading-4 text-muted-foreground">{hint}</p> : null}
    </div>
  )
}

function PreviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-border/60 py-1">
      <span className="shrink-0 text-muted-foreground">{label}</span>
      <span className="min-w-0 break-words text-right">{value}</span>
    </div>
  )
}
