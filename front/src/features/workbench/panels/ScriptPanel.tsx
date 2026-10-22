/**
 * 世界观与剧本面板（P3 / C5）。
 *
 * C5 负责：上传 .docx/.md、保存原始文件与版本、提取原文、预览、显式启用版本。
 * C6 会在同一面板上增加 AI 解析、审核与差异；这里不伪造解析按钮。
 */
import { useEffect, useMemo, useRef, useState } from 'react'
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
  useScriptDocumentActions,
  useWorkbenchScriptDocuments,
  useWorkbenchScriptVersion,
} from '../useWorkbenchQueries'
import { workbenchScriptPath } from '../routes'

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
}: {
  documentId: string
  versionId: string | null
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
  return (
    <ScrollArea className="h-[48vh] rounded-md border border-border bg-muted/20">
      <pre className="whitespace-pre-wrap break-words p-3 text-xs leading-6">
        {query.data?.raw_text || '（空文档）'}
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
}: {
  document?: ScriptDocumentRead
  title: string
  description: string
  onUpload: (file: File) => Promise<void>
  uploading: boolean
  legacyHref?: string
}) {
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null)
  const actions = useScriptDocumentActions(document?.project_id ?? '')

  useEffect(() => {
    setSelectedVersionId(document?.current_version_id ?? document?.active_version_id ?? null)
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
            <div className="space-y-2">
              <Warnings warnings={warnings} />
              <VersionPreview documentId={document.id} versionId={selectedVersionId} />
              <p className="text-[10px] text-muted-foreground">
                只读预览。正式章节正文只会在「启用版本」或后续审核确认后更新。
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
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
        <StageNote stage="C5">
          已支持 DOCX/Markdown 上传、原始文件保存、原文提取与版本启用。AI 结构化解析与统一审核将在下一阶段接入。
        </StageNote>
        <DocumentSection
          document={document}
          title="本集剧本文件"
          description="上传完整剧本；新上传默认为候选版本，确认后才会同步到章节正文。"
          uploading={actions.uploadEpisode.isPending}
          legacyHref={`/projects/${projectId}?tab=chapters&edit=${chapter.id}`}
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
      <StageNote stage="C5">
        P3 正在实现剧本文档导入与解析。本阶段先完成原始文件、版本与原文预览；AI 解析和统一审核随后接入。
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
