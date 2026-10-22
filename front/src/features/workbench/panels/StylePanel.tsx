/**
 * 风格圣经面板（P2）。
 *
 * 未锁定：浏览目录模板 / 创建自定义风格 / 上传参考图 / AI 分析 / 人工修订 / 锁定。
 * 已锁定：只读展示项目快照；全局目录后续变更不会影响这里。
 *
 * 设计边界：
 * - 不引入 antd；
 * - AI 分析只生成可编辑草稿，不自动落库；
 * - 锁定的不可逆性由服务端保证，前端只做说明与二次确认；
 * - 风格参考图不会自动进入 H3 镜头参考图列表。
 */
import { useEffect, useMemo, useState } from 'react'
import {
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  ImagePlus,
  Lock,
  Palette,
  RefreshCw,
  Sparkles,
  Trash2,
} from 'lucide-react'
import { Badge } from '../../../components/ui/badge'
import { Button } from '../../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../../../components/ui/dialog'
import { Input } from '../../../components/ui/input'
import { Select } from '../../../components/ui/select'
import { Textarea } from '../../../components/ui/textarea'
import { cn } from '../../../lib/utils'
import type {
  ProjectStyleOptionRead,
  StyleStructuredProfile,
} from '../../../services/generated'
import { buildFileDownloadUrl } from '../../../pages/aiStudio/assets/utils'
import { LegacyLink, PanelHeader } from '../components/PanelHeader'
import { PanelError, PanelLoading, StageNote } from '../components/PanelStates'
import {
  useProjectStyleActions,
  useStyleAnalysisCapability,
  useWorkbenchProjectStyle,
} from '../useWorkbenchQueries'

const PROFILE_FIELDS: Array<{ key: keyof StyleStructuredProfile; label: string; hint: string }> = [
  { key: 'medium', label: '视觉媒介', hint: '实拍 / 2D 动画 / 3D 渲染 / 定格…' },
  { key: 'texture', label: '画面质感', hint: '皮肤、颗粒、笔触、渲染噪点…' },
  { key: 'color', label: '色彩与饱和度', hint: '主色调、饱和度、对比度' },
  { key: 'lighting', label: '光照方式', hint: '自然光、窗光、体积光、阴影' },
  { key: 'material', label: '材质特征', hint: '布料、金属、木材、玉石…' },
  { key: 'character_rendering', label: '人物渲染', hint: '骨相、五官比例、表情、发丝' },
  { key: 'scene_rendering', label: '场景渲染', hint: '空间层次、生活痕迹、景深' },
  { key: 'camera', label: '摄影与运镜', hint: '焦段、构图、运镜倾向' },
  { key: 'keep', label: '应当保持', hint: '必须稳定的视觉特征' },
  { key: 'avoid', label: '禁止出现', hint: '要明确排除的风格特征' },
]

function emptyProfile(): Required<StyleStructuredProfile> {
  return {
    medium: '',
    texture: '',
    color: '',
    lighting: '',
    material: '',
    character_rendering: '',
    scene_rendering: '',
    camera: '',
    keep: '',
    avoid: '',
  }
}

function profileFromStyle(style?: ProjectStyleOptionRead | null): Required<StyleStructuredProfile> {
  const profile = style?.structured_profile
  if (!profile) return emptyProfile()
  return {
    medium: profile.medium ?? '',
    texture: profile.texture ?? '',
    color: profile.color ?? '',
    lighting: profile.lighting ?? '',
    material: profile.material ?? '',
    character_rendering: profile.character_rendering ?? '',
    scene_rendering: profile.scene_rendering ?? '',
    camera: profile.camera ?? '',
    keep: profile.keep ?? '',
    avoid: profile.avoid ?? '',
  }
}

function FileGallery({
  fileIds,
  label,
  emptyText = '暂无图片',
}: {
  fileIds: string[]
  label: string
  emptyText?: string
}) {
  if (fileIds.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border p-3 text-[11px] text-muted-foreground">
        {label}：{emptyText}
      </div>
    )
  }
  return (
    <div>
      <p className="mb-1 text-[11px] text-muted-foreground">{label}</p>
      <div className="grid grid-cols-3 gap-2">
        {fileIds.map((fileId) => (
          <a
            key={fileId}
            href={buildFileDownloadUrl(fileId) ?? '#'}
            target="_blank"
            rel="noreferrer"
            className="block overflow-hidden rounded-md border border-border bg-muted"
            title={fileId}
          >
            <img
              src={buildFileDownloadUrl(fileId) ?? ''}
              alt={`${label} ${fileId}`}
              className="aspect-square w-full object-cover"
              loading="lazy"
            />
          </a>
        ))}
      </div>
    </div>
  )
}

function StyleCard({
  style,
  selected,
  onSelect,
  onEdit,
}: {
  style: ProjectStyleOptionRead
  selected: boolean
  onSelect: () => void
  onEdit: () => void
}) {
  return (
    <Card className={cn(selected && 'border-primary/60 bg-primary/5')}>
      <CardContent className="space-y-2 p-3">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">{style.name}</p>
            <p className="text-[10px] text-muted-foreground">{style.visual_style}</p>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-1">
            {style.is_builtin ? <Badge variant="secondary">内置</Badge> : null}
            <Badge variant="outline" className="font-normal">
              {style.analysis_status === 'analyzed' ? '已分析' : '草稿'}
            </Badge>
          </div>
        </div>
        <p className="line-clamp-2 min-h-[2rem] text-[11px] leading-4 text-muted-foreground">
          {style.description || '暂无说明'}
        </p>
        <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
          <ImagePlus className="h-3 w-3" />
          参考图 {style.reference_file_ids?.length ?? 0} · 样张 {style.sample_file_ids?.length ?? 0}
        </div>
        <div className="flex items-center gap-1.5">
          <Button
            size="sm"
            variant={selected ? 'secondary' : 'outline'}
            className="h-7 px-2 text-[11px]"
            onClick={onSelect}
            disabled={selected}
          >
            {selected ? '当前选择' : '选择'}
          </Button>
          <Button variant="ghost" size="sm" className="h-7 px-2 text-[11px]" onClick={onEdit}>
            查看/编辑
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export function StylePanel({ projectId }: { projectId: string }) {
  const stateQuery = useWorkbenchProjectStyle(projectId)
  const capabilityQuery = useStyleAnalysisCapability()
  const actions = useProjectStyleActions(projectId)

  const state = stateQuery.data
  const styles = useMemo(() => state?.styles ?? [], [state?.styles])
  const [activeStyleId, setActiveStyleId] = useState<string | null>(null)
  const [editorOpen, setEditorOpen] = useState(false)
  const [editingStyle, setEditingStyle] = useState<ProjectStyleOptionRead | null>(null)
  const [lockOpen, setLockOpen] = useState(false)
  const [notice, setNotice] = useState<{ tone: 'ok' | 'error'; text: string } | null>(null)

  useEffect(() => {
    setActiveStyleId(state?.style?.id ?? state?.snapshot?.source_style_id ?? null)
  }, [state?.style?.id, state?.snapshot?.source_style_id])

  const presets = useMemo(
    () => styles.filter((style) => style.is_builtin).sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0)),
    [styles],
  )
  const others = useMemo(
    () => styles.filter((style) => !style.is_builtin).sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0)),
    [styles],
  )
  const activeStyle = styles.find((style) => style.id === activeStyleId) ?? null

  if (stateQuery.isLoading) return <PanelLoading lines={8} label="加载风格圣经" />
  if (stateQuery.isError) {
    return (
      <PanelError
        message={stateQuery.error instanceof Error ? stateQuery.error.message : '风格状态加载失败'}
        onRetry={() => void stateQuery.refetch()}
      />
    )
  }
  if (!state) return <PanelError message="风格状态为空" onRetry={() => void stateQuery.refetch()} />

  const selectStyle = (styleId: string) => {
    setNotice(null)
    actions.select.mutate(styleId, {
      onSuccess: (next) => {
        setActiveStyleId(next.style?.id ?? null)
        setNotice({ tone: 'ok', text: `已选择「${next.style?.name ?? '风格'}」；锁定后不可直接切换` })
      },
      onError: (error) =>
        setNotice({ tone: 'error', text: error instanceof Error ? error.message : '选择失败' }),
    })
  }

  const lockStyle = () => {
    if (!activeStyle) return
    setNotice(null)
    actions.lock.mutate(
      { style_id: activeStyle.id },
      {
        onSuccess: (next) => {
          setLockOpen(false)
          setNotice({
            tone: 'ok',
            text: `已锁定「${next.snapshot?.style_name ?? activeStyle.name}」，后续生成将读取该快照`,
          })
        },
        onError: (error) =>
          setNotice({ tone: 'error', text: error instanceof Error ? error.message : '锁定失败' }),
      },
    )
  }

  if (state.locked && state.snapshot) {
    const snapshot = state.snapshot
    return (
      <div className="space-y-4">
        <PanelHeader
          title="风格圣经"
          description="项目视觉风格已锁定；以下为项目快照，不受全局风格目录后续修改影响。"
          badge={
            <span className="rounded-full border border-ready-complete/40 bg-ready-complete/10 px-2 py-0.5 text-[11px] font-medium text-ready-complete">
              已锁定
            </span>
          }
          actions={
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => void stateQuery.refetch()}
                disabled={stateQuery.isFetching}
              >
                <RefreshCw className={cn('h-3.5 w-3.5', stateQuery.isFetching && 'animate-spin')} />
                刷新
              </Button>
              <LegacyLink href="/styles">
                <ExternalLink className="h-3.5 w-3.5" />
                管理全局目录
              </LegacyLink>
            </>
          }
        />

        {notice ? <Notice tone={notice.tone} text={notice.text} /> : null}

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">锁定快照</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-lg font-semibold">{snapshot.style_name}</span>
              <Badge variant="outline">{snapshot.visual_style}</Badge>
              <span className="text-[11px] text-muted-foreground">
                锁定于 {new Date(snapshot.locked_at).toLocaleString()} · v{snapshot.snapshot_version}
              </span>
            </div>
            <p className="text-xs leading-5 text-muted-foreground">{snapshot.description || '暂无说明'}</p>
            {snapshot.source_style_id ? (
              <p className="text-[11px] text-muted-foreground">来源风格 ID：{snapshot.source_style_id}</p>
            ) : null}
            <div className="grid gap-3 md:grid-cols-2">
              <FileGallery fileIds={snapshot.reference_file_ids ?? []} label="风格参考图" />
              <FileGallery fileIds={snapshot.sample_file_ids ?? []} label="确认样张" />
            </div>
            <div>
              <h3 className="mb-1 text-xs font-medium">最终提示词质感描述</h3>
              <pre className="whitespace-pre-wrap rounded-md bg-muted/40 p-2 text-[11px] leading-5">
                {snapshot.prompt_pack}
              </pre>
            </div>
            {snapshot.structured_profile ? (
              <div className="grid gap-2 md:grid-cols-2">
                {PROFILE_FIELDS.map((field) => {
                  const value = snapshot.structured_profile?.[field.key]
                  if (!value) return null
                  return (
                    <div key={field.key} className="rounded-md border border-border p-2">
                      <p className="text-[10px] text-muted-foreground">{field.label}</p>
                      <p className="mt-0.5 text-xs leading-5">{value}</p>
                    </div>
                  )
                })}
              </div>
            ) : null}
          </CardContent>
        </Card>

        <StageNote stage="P2">
          已锁定项目不能直接切换风格。若需要采用其他风格，应在后续的项目复制流程中建立新项目；本阶段不提供跨风格转换。
        </StageNote>
      </div>
    )
  }

  const analysisAvailable = capabilityQuery.data?.available ?? false
  const analysisReason = capabilityQuery.data?.reason || '正在检查视觉分析模型'

  return (
    <div className="space-y-4">
      <PanelHeader
        title="风格圣经"
        description="先选择或创建视觉风格，确认后锁定为项目快照。锁定后本项目的资产生成将固定使用该风格。"
        badge={
          <span className="rounded-full border border-state-pending/40 bg-state-pending/10 px-2 py-0.5 text-[11px] font-medium text-state-pending">
            未锁定
          </span>
        }
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void stateQuery.refetch()}
              disabled={stateQuery.isFetching}
            >
              <RefreshCw className={cn('h-3.5 w-3.5', stateQuery.isFetching && 'animate-spin')} />
              刷新
            </Button>
            <LegacyLink href="/styles">
              <ExternalLink className="h-3.5 w-3.5" />
              管理全局目录
            </LegacyLink>
          </>
        }
      />

      {notice ? <Notice tone={notice.tone} text={notice.text} /> : null}

      <StageNote stage="P2">
        参考图只用于提炼风格提示词，不会自动加入 H3 镜头参考图列表。锁定后全局目录的修改不会影响本项目。
      </StageNote>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Palette className="h-4 w-4 text-muted-foreground" />
            当前选择
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-2">
          {activeStyle ? (
            <>
              <span className="text-base font-semibold">{activeStyle.name}</span>
              <Badge variant="outline">{activeStyle.visual_style}</Badge>
              {activeStyle.analysis_status !== 'analyzed' ? (
                <Badge variant="secondary">分析草稿</Badge>
              ) : null}
              <Button
                size="sm"
                className="ml-auto"
                onClick={() => setLockOpen(true)}
                disabled={actions.lock.isPending}
              >
                <Lock className="h-3.5 w-3.5" />
                锁定此风格
              </Button>
            </>
          ) : (
            <p className="text-xs text-muted-foreground">
              尚未选择风格。可以从下方模板/目录中选择，或创建自定义风格。
            </p>
          )}
        </CardContent>
      </Card>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-medium">内置模板</h3>
        <Button
          size="sm"
          variant="outline"
          onClick={() => {
            setEditingStyle(null)
            setEditorOpen(true)
          }}
        >
          <Sparkles className="h-3.5 w-3.5" />
          新建自定义风格
        </Button>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {presets.length === 0 ? (
          <p className="text-xs text-muted-foreground">
            内置模板尚未初始化；可先刷新，或直接在下方选择已有目录风格。
          </p>
        ) : (
          presets.map((style) => (
            <StyleCard
              key={style.id}
              style={style}
              selected={style.id === activeStyleId}
              onSelect={() => selectStyle(style.id)}
              onEdit={() => {
                setEditingStyle(style)
                setEditorOpen(true)
              }}
            />
          ))
        )}
      </div>

      {others.length > 0 ? (
        <>
          <h3 className="text-sm font-medium">其他目录风格</h3>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {others.map((style) => (
              <StyleCard
                key={style.id}
                style={style}
                selected={style.id === activeStyleId}
                onSelect={() => selectStyle(style.id)}
                onEdit={() => {
                  setEditingStyle(style)
                  setEditorOpen(true)
                }}
              />
            ))}
          </div>
        </>
      ) : null}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">AI 风格分析</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-xs">
          {analysisAvailable ? (
            <p className="flex items-center gap-1.5 text-ready-complete">
              <CheckCircle2 className="h-3.5 w-3.5" />
              可用模型：{capabilityQuery.data?.model_name}（{capabilityQuery.data?.provider_name}）
            </p>
          ) : (
            <p className="flex items-start gap-1.5 text-state-pending">
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              当前没有可用的视觉分析模型：{analysisReason}。你仍可以手动填写结构化描述并保存草稿。
            </p>
          )}
          <p className="text-[11px] text-muted-foreground">
            分析只生成可编辑草稿，不会自动保存或覆盖人工修改；本阶段不会调用图片生成模型。
          </p>
        </CardContent>
      </Card>

      <StyleEditorDialog
        open={editorOpen}
        onOpenChange={setEditorOpen}
        style={editingStyle}
        analysisAvailable={analysisAvailable}
        analysisReason={analysisReason}
        actions={actions}
        onSaved={(saved) => {
          setEditorOpen(false)
          setActiveStyleId(saved.id)
          selectStyle(saved.id)
        }}
      />

      <Dialog open={lockOpen} onOpenChange={setLockOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>锁定视觉风格</DialogTitle>
            <DialogDescription>
              将「{activeStyle?.name}」锁定为项目风格快照。锁定后：
            </DialogDescription>
          </DialogHeader>
          <ul className="list-disc space-y-1 pl-5 text-xs text-muted-foreground">
            <li>本项目不能直接切换到其他视觉风格；</li>
            <li>全局风格目录后续修改不会影响本项目；</li>
            <li>已生成的资产与历史结果保持不变；</li>
            <li>后续资产生成会优先读取该快照的提示词质感描述。</li>
          </ul>
          <DialogFooter>
            <Button variant="outline" onClick={() => setLockOpen(false)}>
              取消
            </Button>
            <Button onClick={lockStyle} disabled={actions.lock.isPending}>
              <Lock className="h-3.5 w-3.5" />
              {actions.lock.isPending ? '锁定中…' : '确认锁定'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function Notice({ tone, text }: { tone: 'ok' | 'error'; text: string }) {
  return (
    <div
      className={cn(
        'flex items-start gap-2 rounded-md border p-3 text-xs',
        tone === 'ok'
          ? 'border-ready-complete/40 bg-ready-complete/10 text-ready-complete'
          : 'border-ready-blocked/40 bg-ready-blocked/10 text-ready-blocked',
      )}
      role="status"
    >
      {tone === 'ok' ? (
        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
      ) : (
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
      )}
      <span className="whitespace-pre-wrap">{text}</span>
    </div>
  )
}

function StyleEditorDialog({
  open,
  onOpenChange,
  style,
  analysisAvailable,
  analysisReason,
  actions,
  onSaved,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  style: ProjectStyleOptionRead | null
  analysisAvailable: boolean
  analysisReason: string
  actions: ReturnType<typeof useProjectStyleActions>
  onSaved: (style: ProjectStyleOptionRead) => void
}) {
  const [name, setName] = useState('')
  const [visualStyle, setVisualStyle] = useState('现实')
  const [description, setDescription] = useState('')
  const [profile, setProfile] = useState<Required<StyleStructuredProfile>>(emptyProfile)
  const [promptPack, setPromptPack] = useState('')
  const [referenceFileIds, setReferenceFileIds] = useState<string[]>([])
  const [sampleFileIds, setSampleFileIds] = useState<string[]>([])
  const [analysisStatus, setAnalysisStatus] = useState('draft')
  const [analysisModel, setAnalysisModel] = useState('')
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState<'reference' | 'sample' | null>(null)

  useEffect(() => {
    if (!open) return
    setName(style?.name ?? '')
    setVisualStyle(style?.visual_style ?? '现实')
    setDescription(style?.description ?? '')
    setProfile(profileFromStyle(style))
    setPromptPack(style?.prompt_pack ?? '')
    setReferenceFileIds(style?.reference_file_ids ?? [])
    setSampleFileIds(style?.sample_file_ids ?? [])
    setAnalysisStatus(style?.analysis_status ?? 'draft')
    setAnalysisModel('')
    setError('')
  }, [open, style])

  const uploadFiles = async (kind: 'reference' | 'sample', files: FileList | null) => {
    if (!files?.length) return
    const current = kind === 'reference' ? referenceFileIds : sampleFileIds
    const incoming = Array.from(files)
    if (current.length + incoming.length > 3) {
      setError(`${kind === 'reference' ? '风格参考图' : '确认样张'}最多 3 张`)
      return
    }
    for (const file of incoming) {
      if (!file.type.startsWith('image/')) {
        setError('只能上传图片文件')
        return
      }
      if (file.size > 10 * 1024 * 1024) {
        setError('单张图片不能超过 10MB')
        return
      }
    }
    setError('')
    setUploading(kind)
    try {
      const ids: string[] = []
      for (const file of incoming) {
        ids.push(await actions.upload.mutateAsync(file))
      }
      if (kind === 'reference') setReferenceFileIds((prev) => [...prev, ...ids])
      else setSampleFileIds((prev) => [...prev, ...ids])
    } catch (err) {
      setError(err instanceof Error ? err.message : '上传失败')
    } finally {
      setUploading(null)
    }
  }

  const runAnalysis = () => {
    if (referenceFileIds.length < 1 || referenceFileIds.length > 3) {
      setError('请先上传 1–3 张风格参考图')
      return
    }
    setError('')
    actions.analyze.mutate(
      { file_ids: referenceFileIds },
      {
        onSuccess: (result) => {
          setProfile({
            medium: result.profile.medium ?? '',
            texture: result.profile.texture ?? '',
            color: result.profile.color ?? '',
            lighting: result.profile.lighting ?? '',
            material: result.profile.material ?? '',
            character_rendering: result.profile.character_rendering ?? '',
            scene_rendering: result.profile.scene_rendering ?? '',
            camera: result.profile.camera ?? '',
            keep: result.profile.keep ?? '',
            avoid: result.profile.avoid ?? '',
          })
          setPromptPack(result.prompt_pack)
          setAnalysisStatus('analyzed')
          setAnalysisModel(`${result.model_name}（${result.provider_name}）`)
        },
        onError: (err) =>
          setError(err instanceof Error ? err.message : 'AI 分析失败，可继续手动填写'),
      },
    )
  }

  const save = async () => {
    if (!name.trim()) {
      setError('请填写风格名称')
      return
    }
    setError('')
    const payload = {
      visual_style: visualStyle,
      name: name.trim(),
      description: description.trim(),
      prompt_pack: promptPack.trim(),
      structured_profile: profile,
      reference_file_ids: referenceFileIds,
      sample_file_ids: sampleFileIds,
      analysis_status: analysisStatus,
    }
    try {
      const saved = style
        ? await actions.updateStyle.mutateAsync({ styleId: style.id, body: payload })
        : await actions.createStyle.mutateAsync(payload)
      onSaved(saved)
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败')
    }
  }

  const busy = actions.createStyle.isPending || actions.updateStyle.isPending

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] w-[min(900px,95vw)] max-w-none overflow-auto">
        <DialogHeader>
          <DialogTitle>{style ? `编辑风格：${style.name}` : '新建自定义风格'}</DialogTitle>
          <DialogDescription>
            上传 1–3 张参考图 → AI 分析 → 人工修订 → 保存草稿 → 回到面板选择并锁定。
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {error ? (
            <div className="flex items-start gap-2 rounded-md border border-ready-blocked/40 bg-ready-blocked/10 p-2 text-xs text-ready-blocked">
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              {error}
            </div>
          ) : null}

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">风格名称</label>
              <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="例如：赛博国风" />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">画面表现形式</label>
              <Select value={visualStyle} onChange={(event) => setVisualStyle(event.target.value)}>
                <option value="现实">现实</option>
                <option value="动漫">动漫</option>
              </Select>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium">面向用户的说明</label>
            <Textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="说明这个风格适合什么题材、画面倾向是什么"
              rows={2}
            />
          </div>

          <div className="rounded-md border border-border p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-sm font-medium">风格参考图（1–3 张）</p>
                <p className="text-[11px] text-muted-foreground">
                  上传后点击 AI 分析；也可以直接手动填写下方字段。
                </p>
              </div>
              <div className="flex items-center gap-2">
                <label className="inline-flex h-8 cursor-pointer items-center gap-1.5 rounded-md border border-input bg-background px-3 text-xs hover:bg-accent">
                  <ImagePlus className="h-3.5 w-3.5" />
                  {uploading === 'reference' ? '上传中…' : '上传参考图'}
                  <input
                    type="file"
                    accept="image/*"
                    multiple
                    className="hidden"
                    onChange={(event) => void uploadFiles('reference', event.target.files)}
                    disabled={uploading !== null}
                  />
                </label>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={runAnalysis}
                  disabled={!analysisAvailable || actions.analyze.isPending || uploading !== null}
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  {actions.analyze.isPending ? '分析中…' : 'AI 分析'}
                </Button>
              </div>
            </div>
            {!analysisAvailable ? (
              <p className="mt-2 text-[11px] text-state-pending">
                无可用视觉模型：{analysisReason}。可手动填写字段并保存草稿。
              </p>
            ) : null}
            {analysisModel ? (
              <p className="mt-1 text-[11px] text-muted-foreground">上次分析模型：{analysisModel}</p>
            ) : null}
            <div className="mt-2">
              <EditableFileList
                fileIds={referenceFileIds}
                onRemove={(id) => setReferenceFileIds((prev) => prev.filter((item) => item !== id))}
              />
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            {PROFILE_FIELDS.map((field) => (
              <div key={field.key} className="space-y-1">
                <label className="text-xs font-medium">{field.label}</label>
                <Textarea
                  value={profile[field.key]}
                  onChange={(event) =>
                    setProfile((prev) => ({ ...prev, [field.key]: event.target.value }))
                  }
                  placeholder={field.hint}
                  rows={2}
                />
              </div>
            ))}
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium">最终提示词质感描述（可手动修订）</label>
            <Textarea
              value={promptPack}
              onChange={(event) => setPromptPack(event.target.value)}
              rows={3}
              placeholder="留空时会由结构化字段自动生成"
            />
          </div>

          <div className="rounded-md border border-border p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-sm font-medium">确认样张（最多 3 张）</p>
                <p className="text-[11px] text-muted-foreground">
                  人工确认该风格的代表画面；不调用图片生成模型。
                </p>
              </div>
              <label className="inline-flex h-8 cursor-pointer items-center gap-1.5 rounded-md border border-input bg-background px-3 text-xs hover:bg-accent">
                <ImagePlus className="h-3.5 w-3.5" />
                {uploading === 'sample' ? '上传中…' : '上传样张'}
                <input
                  type="file"
                  accept="image/*"
                  multiple
                  className="hidden"
                  onChange={(event) => void uploadFiles('sample', event.target.files)}
                  disabled={uploading !== null}
                />
              </label>
            </div>
            <div className="mt-2">
              <EditableFileList
                fileIds={sampleFileIds}
                onRemove={(id) => setSampleFileIds((prev) => prev.filter((item) => item !== id))}
              />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button onClick={() => void save()} disabled={busy || uploading !== null}>
            {busy ? '保存中…' : style ? '保存修改' : '保存草稿'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function EditableFileList({
  fileIds,
  onRemove,
}: {
  fileIds: string[]
  onRemove: (fileId: string) => void
}) {
  if (fileIds.length === 0) {
    return <p className="text-[11px] text-muted-foreground">尚未上传图片</p>
  }
  return (
    <div className="grid grid-cols-3 gap-2">
      {fileIds.map((fileId) => (
        <div key={fileId} className="group relative overflow-hidden rounded-md border border-border">
          <img
            src={buildFileDownloadUrl(fileId) ?? ''}
            alt={fileId}
            className="aspect-square w-full object-cover"
          />
          <Button
            variant="destructive"
            size="icon"
            className="absolute right-1 top-1 h-6 w-6 opacity-90"
            aria-label="移除图片"
            onClick={() => onRemove(fileId)}
          >
            <Trash2 className="h-3 w-3" />
          </Button>
        </div>
      ))}
    </div>
  )
}
