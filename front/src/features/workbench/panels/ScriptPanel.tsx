/**
 * 世界观与剧本面板（P3 / C5）。
 *
 * C5 负责：上传 .docx/.md、保存原始文件与版本、提取原文、预览、显式启用版本。
 * C6 会在同一面板上增加 AI 解析、审核与差异；这里不伪造解析按钮。
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  ExternalLink,
  FileText,
  Upload,
} from 'lucide-react'
import { Badge } from '../../../components/ui/badge'
import { Button } from '../../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card'
import { ScrollArea } from '../../../components/ui/scroll-area'
import { cn } from '../../../lib/utils'
import type {
  ChapterRead,
  ProjectRead,
  ScriptDocumentRead,
  ScriptDocumentVersionRead,
} from '../../../services/generated'
import { LegacyLink, PanelHeader } from '../components/PanelHeader'
import { PanelEmpty, PanelError, PanelLoading, StageNote } from '../components/PanelStates'
import {
  useDocumentParseRuns,
  useScriptDocumentActions,
  useScriptParseActions,
  useScriptParseRun,
  useWorkbenchScriptDocuments,
  useWorkbenchScriptVersion,
} from '../useWorkbenchQueries'
import { workbenchScriptPath } from '../routes'
import { ScriptReviewPanel } from './ScriptReviewPanel'
import { ScriptDiffPanel } from './ScriptDiffPanel'

function formatTime(value?: string | null): string {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}

function VersionBadge({ version }: { version: ScriptDocumentVersionRead }) {
  if (version.status === 'active') return <Badge variant="secondary">生效中</Badge>
  if (version.status === 'superseded') {
    return (
      <Badge variant="outline" className="font-normal">
        历史
      </Badge>
    )
  }
  return (
    <Badge variant="outline" className="border-state-pending/40 font-normal text-state-pending">
      候选
    </Badge>
  )
}

function Warnings({ warnings }: { warnings?: string[] }) {
  if (!warnings?.length) return null
  return (
    <div className="space-y-1 rounded-md border border-state-pending/40 bg-state-pending/10 p-2 text-[11px] text-state-pending">
      {warnings.map((warning) => (
        <p key={warning} className="flex items-start gap-1.5">
          <AlertCircle className="mt-0.5 h-3 w-3 shrink-0" />
          {warning}
        </p>
      ))}
    </div>
  )
}

function UploadButton({
  label,
  onUpload,
  busy,
}: {
  label: string
  onUpload: (file: File) => Promise<void>
  busy: boolean
}) {
  const inputRef = useRef<HTMLInputElement | null>(null)
  return (
    <>
      <Button
        size="sm"
        variant="outline"
        onClick={() => inputRef.current?.click()}
        disabled={busy}
      >
        <Upload className="h-3.5 w-3.5" />
        {busy ? '上传中…' : label}
      </Button>
      <input
        ref={inputRef}
        type="file"
        accept=".docx,.md,.markdown"
        className="hidden"
        onChange={(event) => {
          const file = event.target.files?.[0]
          event.target.value = ''
          if (file) void onUpload(file)
        }}
      />
    </>
  )
}

function VersionList({
  document,
  selectedVersionId,
  onSelect,
  onActivate,
  activating,
}: {
  document: ScriptDocumentRead
  selectedVersionId: string | null
  onSelect: (versionId: string) => void
  onActivate: (versionId: string) => void
  activating: boolean
}) {
  return (
    <div className="space-y-1">
      {(document.versions ?? []).map((version) => (
        <button
          key={version.id}
          type="button"
          onClick={() => onSelect(version.id)}
          className={cn(
            'flex w-full items-center gap-2 rounded-md border px-2 py-1.5 text-left text-[11px] transition-colors',
            selectedVersionId === version.id
              ? 'border-primary/60 bg-primary/5'
              : 'border-border hover:bg-accent',
          )}
        >
          <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          <span className="min-w-0 flex-1">
            <span className="block truncate">
              v{version.version_no} · {version.file_name}
            </span>
            <span className="block text-[10px] text-muted-foreground">
              {(version.file_type ?? '').toUpperCase()} · {version.text_length} 字 · {formatTime(version.created_at)}
            </span>
          </span>
          <VersionBadge version={version} />
          {version.status === 'candidate' ? (
            <Button
              size="sm"
              variant="ghost"
              className="h-6 px-1.5 text-[10px]"
              disabled={activating}
              onClick={(event) => {
                event.stopPropagation()
                onActivate(version.id)
              }}
            >
              启用
            </Button>
          ) : null}
        </button>
      ))}
    </div>
  )
}

function VersionPreview({
  documentId,
  versionId,
  highlightQuote,
}: {
  documentId: string
  versionId: string | null
  highlightQuote?: string
}) {
  const query = useWorkbenchScriptVersion(documentId, versionId ?? undefined)
  if (!versionId) return <p className="text-xs text-muted-foreground">请选择一个版本查看原文。</p>
  if (query.isLoading) return <PanelLoading lines={6} label="加载原文" />
  if (query.isError) {
    return (
      <PanelError
        message={query.error instanceof Error ? query.error.message : '原文加载失败'}
        onRetry={() => void query.refetch()}
      />
    )
  }
  const rawText = query.data?.raw_text || ''
  const quote = (highlightQuote ?? '').trim()
  const parts = quote && rawText.includes(quote) ? rawText.split(quote) : [rawText]
  return (
    <ScrollArea className="h-[48vh] rounded-md border border-border bg-muted/20">
      <pre className="whitespace-pre-wrap break-words p-3 text-xs leading-6">
        {parts.map((part, index) => (
          <span key={`preview-${index}`}>
            {part}
            {quote && rawText.includes(quote) && index < parts.length - 1 ? (
              <mark className="rounded bg-state-pending/30 px-0.5 text-foreground">{quote}</mark>
            ) : null}
          </span>
        ))}
        {rawText ? null : '（空文档）'}
      </pre>
    </ScrollArea>
  )
}

function DocumentSection({
  document,
  title,
  description,
  onUpload,
  uploading,
  legacyHref,
  aside,
}: {
  document?: ScriptDocumentRead
  title: string
  description: string
  onUpload: (file: File) => Promise<void>
  uploading: boolean
  legacyHref?: string
  aside?: (locate: (quote: string) => void) => ReactNode
}) {
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null)
  const [highlightQuote, setHighlightQuote] = useState('')
  const actions = useScriptDocumentActions(document?.project_id ?? '')

  useEffect(() => {
    setSelectedVersionId(document?.current_version_id ?? document?.active_version_id ?? null)
    setHighlightQuote('')
  }, [document?.id, document?.current_version_id, document?.active_version_id])

  const selected = (document?.versions ?? []).find((item) => item.id === selectedVersionId)
  const warnings = (selected?.extract_meta?.warnings as string[] | undefined) ?? []

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <CardTitle className="flex items-center gap-2 text-sm">
              <BookOpen className="h-4 w-4 text-muted-foreground" />
              {title}
            </CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">{description}</p>
          </div>
          <div className="flex items-center gap-1.5">
            {legacyHref ? (
              <LegacyLink href={legacyHref}>
                <ExternalLink className="h-3.5 w-3.5" />
                旧版查看
              </LegacyLink>
            ) : null}
            <UploadButton label="上传 .docx / .md" onUpload={onUpload} busy={uploading} />
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {!document ? (
          <PanelEmpty
            title="尚未上传文档"
            description="支持 .docx 与 .md；上传后会保存原始文件并提取原文，不会自动覆盖已有章节内容。"
          />
        ) : (
          <div className="grid gap-3 lg:grid-cols-[280px_1fr]">
            <div className="space-y-2">
              <div className="rounded-md border border-border p-2 text-[11px]">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate font-medium">{document.title}</span>
                  <Badge variant="outline" className="font-normal">
                    {document.doc_type === 'worldbuilding' ? '世界观' : '剧集剧本'}
                  </Badge>
                </div>
                <p className="mt-1 text-muted-foreground">
                  当前版本：v{document.current_version?.version_no ?? '—'} · 生效版本：v
                  {document.active_version?.version_no ?? '—'}
                </p>
              </div>
              <VersionList
                document={document}
                selectedVersionId={selectedVersionId}
                onSelect={setSelectedVersionId}
                onActivate={(versionId) => {
                  void actions.activate.mutateAsync({
                    documentId: document.id,
                    versionId,
                  })
                }}
                activating={actions.activate.isPending}
              />
            </div>
            <div className={aside ? 'grid gap-3 xl:grid-cols-2' : 'space-y-2'}>
              <div className="space-y-2">
                <Warnings warnings={warnings} />
                <VersionPreview
                  documentId={document.id}
                  versionId={selectedVersionId}
                  highlightQuote={highlightQuote}
                />
                <p className="text-[10px] text-muted-foreground">
                  只读预览。正式章节正文只会在「启用版本」或审核确认后更新。
                </p>
              </div>
              {aside ? <div className="min-w-0">{aside(setHighlightQuote)}</div> : null}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

/**
 * 单集解析工作区：开始解析、轮询状态、统一审核与确认。
 *
 * 放在原文右侧，保持「左侧原文 / 右侧结构化结果」的审核布局；
 * 解析任务状态来自后端 run，不依赖前端本地计时。
 */
function EpisodeParseWorkspace({
  projectId,
  document,
  onConfirmed,
  onLocate,
}: {
  projectId: string
  document: ScriptDocumentRead
  onConfirmed: () => void
  onLocate: (quote: string) => void
}) {
  const runsQuery = useDocumentParseRuns(document.id)
  const actions = useScriptParseActions(projectId, document.id)
  const [runId, setRunId] = useState<string | null>(null)
  const [message, setMessage] = useState('')
  const runQuery = useScriptParseRun(runId)
  const run = runQuery.data
  const versionId = document.current_version_id ?? document.active_version_id

  useEffect(() => {
    const latest = runsQuery.data?.[0]
    if (latest && (!runId || !runsQuery.data?.some((item) => item.id === runId))) {
      setRunId(latest.id)
    }
  }, [runsQuery.data, runId])

  const running =
    run?.status === 'pending' || run?.status === 'running' || actions.start.isPending
  const isCandidate = Boolean(
    document.current_version_id && document.current_version_id !== document.active_version_id,
  )

  const startParse = (force = false) => {
    if (!versionId) return
    setMessage('')
    actions.start.mutate(
      { versionId, force },
      {
        onSuccess: (data) => {
          setRunId(data.run.id)
          setMessage(data.reused ? '已复用同一版本的解析任务' : '解析任务已提交，正在后台处理')
          void runsQuery.refetch()
        },
        onError: (error) =>
          setMessage(error instanceof Error ? error.message : '解析任务创建失败'),
      },
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="outline" className="font-normal">
          AI 结构化解析
        </Badge>
        <Button
          size="sm"
          className="h-8"
          onClick={() => startParse(false)}
          disabled={!versionId || running}
        >
          {running ? '解析中…' : run ? '重新解析本集' : '开始解析本集'}
        </Button>
        {run?.status === 'failed' ? (
          <Button
            size="sm"
            variant="outline"
            className="h-8"
            onClick={() => startParse(true)}
            disabled={running}
          >
            强制重试
          </Button>
        ) : null}
        {run ? (
          <Badge
            variant="outline"
            className={
              run.status === 'failed'
                ? 'border-ready-blocked/40 text-ready-blocked'
                : run.status === 'confirmed'
                  ? 'border-ready-complete/40 text-ready-complete'
                  : 'font-normal'
            }
          >
            {run.status === 'pending'
              ? '排队中'
              : run.status === 'running'
                ? '处理中'
                : run.status === 'completed'
                  ? '待审核'
                  : run.status === 'confirmed'
                    ? '已确认'
                    : '失败'}
          </Badge>
        ) : null}
        {runsQuery.data && runsQuery.data.length > 1 ? (
          <select
            className="ml-auto h-7 rounded-md border border-border bg-background px-2 text-[11px]"
            value={runId ?? ''}
            onChange={(event) => setRunId(event.target.value || null)}
            title="切换解析历史，人工修改仍保存在各自运行中"
          >
            {runsQuery.data.map((item) => {
              const version = (document.versions ?? []).find(
                (value) => value.id === item.version_id,
              )
              return (
                <option key={item.id} value={item.id}>
                  {version ? `v${version.version_no}` : item.version_id.slice(0, 8)} · {item.status} ·{' '}
                  {formatTime(item.created_at)}
                </option>
              )
            })}
          </select>
        ) : null}
      </div>

      {isCandidate ? (
        <p className="rounded-md border border-state-pending/40 bg-state-pending/10 p-2 text-[11px] text-state-pending">
          当前显示的是候选版本 v{document.current_version?.version_no}，解析确认后才会同步章节正文。
        </p>
      ) : null}
      {message ? <p className="text-[11px] text-muted-foreground">{message}</p> : null}

      {!versionId ? (
        <p className="text-xs text-muted-foreground">请先上传本集剧本，再开始解析。</p>
      ) : run ? (
        <div className="space-y-2">
          {run.status === 'pending' || run.status === 'running' ? (
            <div className="space-y-1">
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary transition-all"
                  style={{ width: `${Math.max(2, run.progress ?? 0)}%` }}
                />
              </div>
              <p className="text-[11px] text-muted-foreground">
                模型：{run.model_name || '—'} / {run.provider_name || '—'} · 分块 {run.chunk_count ?? 1}
                {run.failed_chunks?.length ? ` · 失败块 ${run.failed_chunks.join(',')}` : ''}
              </p>
            </div>
          ) : null}
          {run.status === 'failed' ? (
            <div className="rounded-md border border-ready-blocked/40 bg-ready-blocked/10 p-2 text-[11px] text-ready-blocked">
              {run.error || '解析失败，请重试。'}
            </div>
          ) : null}
          {run.status === 'completed' ||
          run.status === 'confirmed' ||
          (run.status === 'failed' && (run.candidates?.length ?? 0) > 0) ? (
            <ScriptReviewPanel
              projectId={projectId}
              run={run}
              onRefresh={() => void runQuery.refetch()}
              onLocate={onLocate}
              onConfirmed={() => {
                setMessage('解析结果已确认；章节正文与资产已更新，历史分镜/视频未删除。')
                void runsQuery.refetch()
                onConfirmed()
              }}
            />
          ) : null}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">
          点击「开始解析本集」后，系统会结合项目世界观、本集剧本和已有资产，一次性生成角色、场景、道具、服装变化、场次建议与对白候选。
        </p>
      )}
    </div>
  )
}

export function ScriptPanel({
  projectId,
  project,
  chapters,
  loading,
  chapterId,
  onNavigate,
}: {
  projectId: string
  project?: ProjectRead
  chapters: ChapterRead[]
  loading: boolean
  chapterId?: string
  onNavigate: (path: string) => void
}) {
  const documentsQuery = useWorkbenchScriptDocuments(projectId)
  const actions = useScriptDocumentActions(projectId)
  const [notice, setNotice] = useState<{ tone: 'ok' | 'error'; text: string } | null>(null)

  const ordered = useMemo(
    () => [...chapters].sort((a, b) => a.index - b.index),
    [chapters],
  )
  const documents = documentsQuery.data ?? []
  const worldbuilding = documents.find((item) => item.doc_type === 'worldbuilding')
  const chapter = chapterId ? ordered.find((item) => item.id === chapterId) : null

  if (loading || documentsQuery.isLoading) {
    return <PanelLoading lines={8} label="加载剧本文档" />
  }
  if (documentsQuery.isError) {
    return (
      <PanelError
        message={
          documentsQuery.error instanceof Error ? documentsQuery.error.message : '剧本文档加载失败'
        }
        onRetry={() => void documentsQuery.refetch()}
      />
    )
  }

  const noticeNode = notice ? (
    <div
      className={cn(
        'flex items-start gap-2 rounded-md border p-3 text-xs',
        notice.tone === 'ok'
          ? 'border-ready-complete/40 bg-ready-complete/10 text-ready-complete'
          : 'border-ready-blocked/40 bg-ready-blocked/10 text-ready-blocked',
      )}
    >
      {notice.tone === 'ok' ? (
        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
      ) : (
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
      )}
      {notice.text}
    </div>
  ) : null

  if (chapterId) {
    if (!chapter) {
      return (
        <PanelEmpty
          title="没有找到这一集"
          description={`章节 ${chapterId} 不在当前项目中，或已被删除。`}
          action={
            <Button size="sm" onClick={() => onNavigate(workbenchScriptPath(projectId))}>
              返回剧本列表
            </Button>
          }
        />
      )
    }
    const document = documents.find(
      (item) => item.doc_type === 'episode' && item.chapter_id === chapter.id,
    )
    return (
      <div className="space-y-4">
        <PanelHeader
          title={`第 ${chapter.index} 集 · ${chapter.title}`}
          description={chapter.summary || '本集剧本原文与版本'}
          actions={
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onNavigate(workbenchScriptPath(projectId))}
            >
              返回剧集列表
            </Button>
          }
        />
        {noticeNode}
        <StageNote stage="C6">
          上传剧本后可一次性解析角色、场景、道具、服装变化、场次建议与对白，并在右侧统一审核后确认落库。
        </StageNote>
        <DocumentSection
          document={document}
          title="本集剧本文件"
          description="上传完整剧本；新上传默认为候选版本，确认后才会同步到章节正文。"
          uploading={actions.uploadEpisode.isPending}
          legacyHref={`/projects/${projectId}?tab=chapters&edit=${chapter.id}`}
          aside={(locate) =>
            document ? (
              <EpisodeParseWorkspace
                projectId={projectId}
                document={document}
                onLocate={locate}
                onConfirmed={() => {
                  void documentsQuery.refetch()
                }}
              />
            ) : null
          }
          onUpload={async (file) => {
            setNotice(null)
            try {
              const result = await actions.uploadEpisode.mutateAsync({
                chapterId: chapter.id,
                file,
              })
              setNotice({
                tone: 'ok',
                text: result.created
                  ? `已保存 v${result.version.version_no} 候选版本`
                  : '相同内容已上传过，未创建重复版本',
              })
            } catch (error) {
              setNotice({
                tone: 'error',
                text: error instanceof Error ? error.message : '上传失败',
              })
            }
          }}
        />
        {document ? (
          <ScriptDiffPanel projectId={projectId} document={document} />
        ) : null}
        <p className="text-[11px] text-muted-foreground">
          当前章节正文：{(chapter.raw_text ?? '').length} 字。旧版编辑页仍可用于直接修改原文。
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <PanelHeader
        title="世界观与剧本"
        description={project?.description || '项目级设定与每集剧本文件'}
        actions={
          <LegacyLink href={`/projects/${projectId}?tab=chapters`}>
            <ExternalLink className="h-3.5 w-3.5" />
            旧版章节管理
          </LegacyLink>
        }
      />
      {noticeNode}
      <StageNote stage="C6">
        P3 已接入 AI 结构化解析、统一审核与版本差异。世界观文档会作为每集解析的上下文；确认解析后才写入正式资产。
      </StageNote>

      <DocumentSection
        document={worldbuilding}
        title="世界观与人物设定"
        description="项目级设定文件；解析时会与每集剧本一起作为上下文。"
        uploading={actions.uploadWorld.isPending}
        onUpload={async (file) => {
          setNotice(null)
          try {
            const result = await actions.uploadWorld.mutateAsync({ file })
            setNotice({
              tone: 'ok',
              text: result.created
                ? `已保存世界观 v${result.version.version_no}`
                : '相同内容已上传过，未创建重复版本',
            })
          } catch (error) {
            setNotice({
              tone: 'error',
              text: error instanceof Error ? error.message : '上传失败',
            })
          }
        }}
      />

      {worldbuilding ? (
        <ScriptDiffPanel projectId={projectId} document={worldbuilding} />
      ) : null}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">剧集剧本</CardTitle>
        </CardHeader>
        <CardContent>
          {ordered.length === 0 ? (
            <PanelEmpty
              title="还没有剧集"
              description="先在旧版项目页创建章节，再上传每集剧本。"
              action={
                <LegacyLink href={`/projects/${projectId}?tab=chapters&create=1`}>
                  去旧版创建剧集
                </LegacyLink>
              }
            />
          ) : (
            <ul className="divide-y divide-border rounded-md border border-border">
              {ordered.map((item) => {
                const doc = documents.find(
                  (value) => value.doc_type === 'episode' && value.chapter_id === item.id,
                )
                return (
                  <li key={item.id}>
                    <button
                      type="button"
                      className="flex w-full items-center gap-3 px-3 py-2.5 text-left transition-colors hover:bg-accent"
                      onClick={() => onNavigate(workbenchScriptPath(projectId, item.id))}
                    >
                      <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm">
                          第 {item.index} 集 · {item.title}
                        </span>
                        <span className="block truncate text-[11px] text-muted-foreground">
                          {doc
                            ? `文档 v${doc.current_version?.version_no ?? '—'} · 生效 v${doc.active_version?.version_no ?? '—'}`
                            : `${(item.raw_text ?? '').length} 字旧版原文 · 未上传文件`}
                        </span>
                      </span>
                      <Badge variant="outline" className="font-normal">
                        {doc ? '已上传' : '未上传'}
                      </Badge>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
