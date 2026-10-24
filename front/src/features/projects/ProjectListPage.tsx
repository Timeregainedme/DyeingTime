import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FolderPlus, RefreshCw, Search, X } from 'lucide-react'
import { Button } from '../../components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../../components/ui/dialog'
import { Input } from '../../components/ui/input'
import { Select } from '../../components/ui/select'
import { Skeleton } from '../../components/ui/skeleton'
import { cn } from '../../lib/utils'
import { useProjectStyleOptions } from '../../pages/aiStudio/project/useProjectStyleOptions'
import { useTaskUiStore } from '../../pages/aiStudio/components/taskUiStore'
import { ProjectCard } from '../../features/projects/ProjectCard'
import { ProjectFormDialog } from '../../features/projects/ProjectFormDialog'
import { useProjectList, type ProjectFormValues } from '../../features/projects/useProjectList'
import { useProjectDashboard, type ProjectSummary } from '../../features/projects/useProjectDashboard'
import {
  ContinueCreating,
  DashboardStats,
  PendingReviews,
  RecentTasks,
} from '../../features/projects/dashboard/DashboardSections'
import type { ProjectView } from '../../features/projects/types'
import type { DashboardProjectRead, DashboardReviewRead } from '../../services/generated'
import { workbenchEpisodePath, workbenchPath, workbenchScriptPath } from '../workbench/routes'

type FilterKey = 'all' | 'editRaw' | 'extractShots' | 'prepareShots' | 'generating' | 'review' | 'ready'
type SortKey = 'updatedAt' | 'name' | 'chapters'

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'editRaw', label: '待录入原文' },
  { key: 'extractShots', label: '待提取分镜' },
  { key: 'prepareShots', label: '待准备镜头' },
  { key: 'generating', label: '生成中' },
  { key: 'review', label: '待审核' },
  { key: 'ready', label: '可推进' },
]

/** 判断项目是否命中筛选条件：阶段看摘要，任务/审核看真实计数。 */
function matchesFilter(
  filter: FilterKey,
  summary: ProjectSummary | undefined,
  project: DashboardProjectRead,
): boolean {
  if (filter === 'all') return true
  if (filter === 'generating') return project.running_tasks > 0
  if (filter === 'review') return project.pending_review_shots > 0
  if (!summary) return false
  if (filter === 'editRaw') {
    return summary.stageKey === 'edit_raw' || summary.stageKey === 'create_first_chapter'
  }
  if (filter === 'extractShots') return summary.stageKey === 'extract_shots'
  if (filter === 'prepareShots') return summary.stageKey === 'prepare_shots'
  if (filter === 'ready') return project.ready_shots > 0
  return true
}

/** 把 dashboard 项目映射成卡片需要的视图模型；不使用任何推测字段。 */
function toProjectView(project: DashboardProjectRead): ProjectView {
  return {
    id: project.id,
    name: project.name,
    description: project.description,
    style: project.style,
    seed: 0,
    unifyStyle: true,
    progress: 0,
    stats: {
      chapters: project.chapter_count,
      roles: 0,
      scenes: 0,
      props: 0,
    },
    updatedAt: project.updated_at ?? '',
    visualStyle: project.visual_style,
    defaultVideoRatio: null,
  }
}

/**
 * 创作工作台首页。
 *
 * 与原版「项目管理列表」的区别：
 * - 顶部四张卡片直接回答「有多少项目、多少待审、多少在跑、多少已采纳」；
 * - 「继续创作」按最近编辑排序，主按钮直达下一步业务页面；
 * - 待审核与最近任务使用真实聚合数据，不再让用户自己判断该从哪进；
 * - 项目卡片保留搜索/筛选/排序/编辑/删除等既有能力，次要操作收进更多菜单。
 *
 * 数据来源只有 `/api/v1/studio/dashboard` 与项目 CRUD 接口，没有前端伪造指标。
 */
export function ProjectListPage() {
  const navigate = useNavigate()
  const setTaskCenterOpen = useTaskUiStore((state) => state.setOpen)
  const { createProject, updateProject, removeProject } = useProjectList({ autoLoad: false })
  const { data, summaries, loading, error, reload } = useProjectDashboard()
  const { options, videoRatioOptions, defaultVideoRatio } = useProjectStyleOptions()

  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<FilterKey>('all')
  const [sortKey, setSortKey] = useState<SortKey>('updatedAt')
  const [dialogMode, setDialogMode] = useState<'create' | 'edit' | null>(null)
  const [editingProject, setEditingProject] = useState<ProjectView | null>(null)
  const [pendingDelete, setPendingDelete] = useState<ProjectView | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const canEdit = data?.can_edit ?? false
  const dashboardProjects = data?.projects ?? []
  const viewProjects = useMemo(() => dashboardProjects.map(toProjectView), [dashboardProjects])

  const visibleProjects = useMemo(() => {
    const keyword = search.trim().toLowerCase()
    const filtered = dashboardProjects.filter((project) => {
      if (keyword) {
        const hit =
          project.name.toLowerCase().includes(keyword) ||
          project.description.toLowerCase().includes(keyword)
        if (!hit) return false
      }
      return matchesFilter(filter, summaries[project.id], project)
    })

    return [...filtered].sort((a, b) => {
      if (sortKey === 'name') return a.name.localeCompare(b.name)
      if (sortKey === 'chapters') return b.chapter_count - a.chapter_count
      return String(b.updated_at ?? '').localeCompare(String(a.updated_at ?? ''))
    })
  }, [dashboardProjects, search, filter, summaries, sortKey])

  /** 进入项目下一步：按章节准备态决定落点，与卡片按钮文案保持一致。 */
  const openProject = (project: DashboardProjectRead) => {
    const summary = summaries[project.id]
    if (!summary?.chapterId) {
      navigate(workbenchPath(project.id))
      return
    }
    if (summary.stageKey === 'edit_raw') {
      navigate(workbenchScriptPath(project.id, summary.chapterId))
      return
    }
    navigate(workbenchEpisodePath(project.id, summary.chapterId))
  }

  const openViewProject = (project: ProjectView) => {
    const dashboardProject = dashboardProjects.find((item) => item.id === project.id)
    if (dashboardProject) {
      openProject(dashboardProject)
      return
    }
    navigate(workbenchPath(project.id))
  }

  const openReview = (review: DashboardReviewRead) => {
    if (!review.project_id) return
    if (review.chapter_id) {
      navigate(workbenchEpisodePath(review.project_id, review.chapter_id))
      return
    }
    navigate(workbenchPath(review.project_id))
  }

  const submitForm = async (values: ProjectFormValues) => {
    if (dialogMode === 'edit' && editingProject) {
      await updateProject(editingProject.id, values)
      await reload()
      return
    }
    const created = await createProject(values)
    await reload()
    navigate(workbenchPath(created.id))
  }

  const confirmDelete = async () => {
    if (!pendingDelete) return
    setDeleteError(null)
    try {
      await removeProject(pendingDelete.id)
      setPendingDelete(null)
      await reload()
    } catch {
      setDeleteError('删除失败，请稍后重试')
    }
  }

  const openCreate = () => {
    setEditingProject(null)
    setDialogMode('create')
  }

  const openEdit = (project: ProjectView) => {
    setEditingProject(project)
    setDialogMode('edit')
  }

  const hasProjects = dashboardProjects.length > 0
  const isEmptyResult = hasProjects && visibleProjects.length === 0
  const stats = data?.stats

  return (
    <div className="flex h-full min-h-0 flex-col bg-background text-foreground">
      <div className="min-h-0 flex-1 overflow-auto">
        <div className="mx-auto w-full max-w-[1600px] space-y-5 px-4 py-5 sm:px-6 lg:px-8">
          <header className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h1 className="text-xl font-semibold tracking-tight">创作工作台</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                管理短剧项目、制作进度与生成任务。
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => void reload()} disabled={loading}>
                <RefreshCw className={cn('h-3.5 w-3.5', loading && 'animate-spin')} />
                刷新
              </Button>
              {canEdit ? (
                <Button onClick={openCreate}>
                  <FolderPlus className="h-4 w-4" />
                  新建项目
                </Button>
              ) : null}
            </div>
          </header>

          {error ? (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-md bg-destructive/10 px-4 py-3 text-sm text-destructive">
              <span>{error}</span>
              <Button variant="outline" size="sm" onClick={() => void reload()}>
                重试
              </Button>
            </div>
          ) : null}

          {loading && !data ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                {[0, 1, 2, 3].map((index) => (
                  <Skeleton key={index} className="h-[104px] w-full rounded-lg" />
                ))}
              </div>
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {[0, 1, 2].map((index) => (
                  <Skeleton key={index} className="h-40 w-full rounded-lg" />
                ))}
              </div>
            </div>
          ) : !hasProjects ? (
            <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border py-16 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
                <FolderPlus className="h-5 w-5 text-muted-foreground" />
              </div>
              <div>
                <p className="text-sm font-medium">还没有项目</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  新建项目后，从粘贴剧本开始，一步步走到成片
                </p>
              </div>
              {canEdit ? <Button onClick={openCreate}>新建第一个项目</Button> : null}
            </div>
          ) : (
            <>
              {stats ? <DashboardStats stats={stats} /> : null}

              <ContinueCreating
                projects={dashboardProjects}
                summaries={summaries}
                onOpen={openProject}
              />

              <div className="grid items-start gap-4 lg:grid-cols-2">
                <PendingReviews reviews={data?.pending_reviews ?? []} onOpen={openReview} />
                <RecentTasks
                  tasks={data?.recent_tasks ?? []}
                  onOpenTaskCenter={() => setTaskCenterOpen(true)}
                />
              </div>

              <section className="space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h2 className="text-sm font-semibold">全部项目</h2>
                  <span className="text-[11px] text-muted-foreground">
                    共 {dashboardProjects.length} 个项目
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <div className="relative w-full max-w-xs">
                    <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      value={search}
                      onChange={(event) => setSearch(event.target.value)}
                      placeholder="搜索项目名称或简介"
                      className="pl-8 pr-8"
                    />
                    {search ? (
                      <button
                        type="button"
                        aria-label="清空搜索"
                        className="absolute right-2 top-1/2 -translate-y-1/2 rounded-sm bg-transparent p-0.5 text-muted-foreground hover:text-foreground"
                        onClick={() => setSearch('')}
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    ) : null}
                  </div>

                  <div className="flex flex-wrap items-center gap-1">
                    {FILTERS.map((item) => (
                      <button
                        key={item.key}
                        type="button"
                        onClick={() => setFilter(item.key)}
                        className={cn(
                          'rounded-md bg-transparent px-2.5 py-1.5 text-xs transition-colors',
                          filter === item.key
                            ? 'bg-primary/10 font-medium text-primary'
                            : 'text-muted-foreground hover:bg-accent hover:text-foreground',
                        )}
                      >
                        {item.label}
                      </button>
                    ))}
                  </div>

                  <Select
                    value={sortKey}
                    onChange={(event) => setSortKey(event.target.value as SortKey)}
                    className="ml-auto w-36"
                    aria-label="排序方式"
                  >
                    <option value="updatedAt">最近更新</option>
                    <option value="name">按名称</option>
                    <option value="chapters">按章节数</option>
                  </Select>
                </div>

                {isEmptyResult ? (
                  <div className="flex h-40 flex-col items-center justify-center gap-2 text-sm text-muted-foreground">
                    <p>没有符合当前条件的项目</p>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setSearch('')
                        setFilter('all')
                      }}
                    >
                      清空筛选
                    </Button>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                    {visibleProjects.map((project) => {
                      const view = viewProjects.find((item) => item.id === project.id)
                      if (!view) return null
                      return (
                        <ProjectCard
                          key={project.id}
                          project={view}
                          summary={summaries[project.id]}
                          canEdit={canEdit}
                          onOpen={() => openViewProject(view)}
                          onOpenWorkbench={() => navigate(workbenchPath(project.id))}
                          onEdit={() => openEdit(view)}
                          onDelete={() => {
                            setDeleteError(null)
                            setPendingDelete(view)
                          }}
                        />
                      )
                    })}
                  </div>
                )}
              </section>
            </>
          )}
        </div>
      </div>

      <ProjectFormDialog
        open={dialogMode !== null}
        mode={dialogMode ?? 'create'}
        project={editingProject}
        styleOptions={{
          visualStyles: options.visualStyles,
          stylesByVisual: options.stylesByVisual,
          videoRatioOptions,
          defaultVideoRatio,
        }}
        onSubmit={submitForm}
        onOpenChange={(open) => {
          if (!open) setDialogMode(null)
        }}
      />

      <Dialog
        open={pendingDelete !== null}
        onOpenChange={(open) => {
          if (!open) setPendingDelete(null)
        }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>删除项目？</DialogTitle>
            <DialogDescription>
              「{pendingDelete?.name}」及其章节、镜头、生成记录都会被删除，且无法恢复。
            </DialogDescription>
          </DialogHeader>
          {deleteError ? (
            <p className="rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">
              {deleteError}
            </p>
          ) : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => setPendingDelete(null)}>
              取消
            </Button>
            <Button variant="destructive" onClick={confirmDelete}>
              确认删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default ProjectListPage
