/**
 * 世界观与剧本面板。
 *
 * 当前数据事实：章节原文存于 `chapters.raw_text`，没有独立的剧本文档实体。
 * 因此 P1：
 *   - 项目级展示项目简介与剧集清单；
 *   - 单集展示真实原文（只读）；
 *   - 文件上传、Word/Markdown 解析、统一审核明确标注为 P3。
 *
 * 不在这里提供「上传」按钮——按钮必须真实可用，未开发的功能用阶段说明。
 */
import { BookOpen, ExternalLink, FileText } from 'lucide-react'
import type { ChapterRead, ProjectRead } from '../../../services/generated'
import { Button } from '../../../components/ui/button'
import { Card, CardContent } from '../../../components/ui/card'
import { ChapterStatusBadge } from '../components/StatusBadges'
import { LegacyLink, PanelHeader } from '../components/PanelHeader'
import { PanelEmpty, PanelLoading, StageNote } from '../components/PanelStates'
import { workbenchScriptPath } from '../routes'

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
  const ordered = [...chapters].sort((a, b) => a.index - b.index)

  if (loading) return <PanelLoading lines={6} label="加载剧本" />

  // 深链接指向一个不存在的章节：明确报错，不静默跳走。
  if (chapterId) {
    const chapter = ordered.find((item) => item.id === chapterId)
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
    return <ChapterScriptView projectId={projectId} chapter={chapter} onNavigate={onNavigate} />
  }

  return (
    <div className="space-y-4">
      <PanelHeader
        title="世界观与剧本"
        description={project?.description || '项目级设定与每集剧本原文'}
        actions={
          <LegacyLink href={`/projects/${projectId}?tab=chapters`}>
            <ExternalLink className="h-3.5 w-3.5" />
            旧版章节管理
          </LegacyLink>
        }
      />

      <StageNote stage="P3">
        项目级世界观文件与每集独立剧本文件（.docx / .md）的上传、异步解析与统一审核将在 P3
        提供。当前只能查看已录入的章节原文。
      </StageNote>

      <Card>
        <CardContent className="p-4">
          <h3 className="flex items-center gap-2 text-sm font-medium">
            <BookOpen className="h-4 w-4 text-muted-foreground" />
            剧集剧本
          </h3>
          <p className="mt-1 text-xs text-muted-foreground">
            选择一集查看原文。原文编辑仍走旧版章节页，改完刷新本节点即可看到最新内容。
          </p>

          {ordered.length === 0 ? (
            <div className="mt-3">
              <PanelEmpty
                title="还没有剧集"
                description="先在旧版项目页创建章节并录入原文，工作台会自动出现对应节点。"
                action={
                  <LegacyLink href={`/projects/${projectId}?tab=chapters&create=1`}>
                    去旧版创建剧集
                  </LegacyLink>
                }
              />
            </div>
          ) : (
            <ul className="mt-3 divide-y divide-border rounded-md border border-border">
              {ordered.map((chapter) => {
                const hasRaw = Boolean((chapter.raw_text ?? '').trim())
                return (
                  <li key={chapter.id}>
                    <button
                      type="button"
                      className="flex w-full items-center gap-3 px-3 py-2.5 text-left transition-colors hover:bg-accent"
                      onClick={() => onNavigate(workbenchScriptPath(projectId, chapter.id))}
                    >
                      <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm">
                          第 {chapter.index} 集 · {chapter.title}
                        </span>
                        <span className="block truncate text-[11px] text-muted-foreground">
                          {hasRaw
                            ? `${(chapter.raw_text ?? '').length} 字原文`
                            : '尚未录入原文'}
                          {' · '}
                          {chapter.shot_count ?? chapter.storyboard_count ?? 0} 个镜头
                        </span>
                      </span>
                      <ChapterStatusBadge status={chapter.status} />
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

function ChapterScriptView({
  projectId,
  chapter,
  onNavigate,
}: {
  projectId: string
  chapter: ChapterRead
  onNavigate: (path: string) => void
}) {
  const rawText = chapter.raw_text ?? ''
  return (
    <div className="space-y-4">
      <PanelHeader
        title={`第 ${chapter.index} 集 · ${chapter.title}`}
        description={chapter.summary || '本集剧本原文'}
        badge={<ChapterStatusBadge status={chapter.status} />}
        actions={
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onNavigate(workbenchScriptPath(projectId))}
            >
              返回剧集列表
            </Button>
            <LegacyLink href={`/projects/${projectId}?tab=chapters&edit=${chapter.id}`}>
              <ExternalLink className="h-3.5 w-3.5" />
              旧版编辑原文
            </LegacyLink>
          </>
        }
      />

      <StageNote stage="P3">
        本阶段原文只读。文件导入、原文与解析结果并排审核、修改后增量差异分析将在 P3 提供。
      </StageNote>

      {rawText.trim() ? (
        <Card>
          <CardContent className="p-4">
            <pre className="max-h-[60vh] overflow-auto whitespace-pre-wrap break-words text-sm leading-7 text-foreground">
              {rawText}
            </pre>
          </CardContent>
        </Card>
      ) : (
        <PanelEmpty
          title="这一集还没有原文"
          description="章节原文为空。请先在旧版章节页录入，或在 P3 使用剧本文件导入。"
          action={
            <LegacyLink href={`/projects/${projectId}?tab=chapters&edit=${chapter.id}`}>
              去旧版录入原文
            </LegacyLink>
          }
        />
      )}
    </div>
  )
}
