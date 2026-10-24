import { useCallback, useEffect, useMemo, useState } from 'react'
import { StudioDashboardService } from '../../services/generated'
import type {
  DashboardProjectRead,
  DashboardRead,
  DashboardReviewRead,
  DashboardTaskRead,
} from '../../services/generated'
import { getChapterPreparationState } from '../../pages/aiStudio/project/ProjectWorkbench/chapterPreparation'
import type { Chapter } from '../../pages/aiStudio/project/ProjectWorkbench/hooks/useProjectData'

/**
 * 首页摘要：将后端一次性返回的章节字段交给既有阶段状态机计算。
 *
 * 这里刻意不复制 `getChapterPreparationState` 的规则：
 * 后端只提供 raw_text/storyboard_count/status，阶段文案与主操作仍由前端唯一实现决定，
 * 避免「列表页说待提取、工作台说待准备」这类前后端漂移。
 */
export interface ProjectSummary {
  stageKey: string
  stageText: string
  actionLabel: string
  hint: string
  chapterId?: string
  storyboardCount?: number
  chapterCount: number
  flow: {
    totalShots: number
    pendingConfirmShots: number
    readyShots: number
    generatingShots: number
  } | null
}

/** 把 dashboard 章节映射成阶段判断函数所需的最小结构。 */
function toStageChapter(project: DashboardProjectRead, chapter: NonNullable<DashboardProjectRead['chapters']>[number]): Chapter {
  return {
    id: chapter.id,
    projectId: project.id,
    index: chapter.index,
    title: chapter.title,
    summary: '',
    // 阶段判断只关心「是否有非空原文」；用占位字符避免把真实长文本搬进列表页。
    rawText: chapter.has_raw_text ? '原文已录入' : '',
    storyboardCount: chapter.storyboard_count,
    status: chapter.status as Chapter['status'],
    updatedAt: new Date().toISOString(),
  }
}

/**
 * 从项目快照里挑出「最该先处理的那一章」。
 *
 * 顺序与工作台总览一致：录入原文 → 提取分镜 → 准备镜头 → 拍摄。
 * 取第一个未完成阶段，而不是最后修改的章节，才能让「继续创作」真的指向下一步。
 */
export function summarizeProject(project: DashboardProjectRead): ProjectSummary {
  const ordered = [...(project.chapters ?? [])].sort((a, b) => a.index - b.index)
  if (!ordered.length) {
    return {
      stageKey: 'create_first_chapter',
      stageText: '待创建章节',
      actionLabel: '创建第一章',
      hint: '项目还没有章节，先建第一章再拆镜头',
      chapterCount: 0,
      flow: {
        totalShots: project.total_shots,
        pendingConfirmShots: project.pending_shots,
        readyShots: project.ready_shots,
        generatingShots: 0,
      },
    }
  }

  const find = (key: string) =>
    ordered.find((chapter) => getChapterPreparationState(toStageChapter(project, chapter)).key === key)

  const target = find('edit_raw') ?? find('extract_shots') ?? find('prepare_shots') ?? find('shoot') ?? ordered[0]
  const state = getChapterPreparationState(toStageChapter(project, target))

  return {
    stageKey: state.key,
    stageText: state.text,
    actionLabel: state.key === 'prepare_shots' ? '查看镜头看板' : state.primaryAction,
    hint: `第${target.index}章 · ${state.hint}`,
    chapterId: target.id,
    storyboardCount: target.storyboard_count,
    chapterCount: ordered.length,
    flow: {
      totalShots: project.total_shots,
      pendingConfirmShots: project.pending_shots,
      readyShots: project.ready_shots,
      generatingShots: 0,
    },
  }
}

/** 首页数据装载状态：真实接口、真实错误、可重试。 */
export interface ProjectDashboardState {
  data: DashboardRead | null
  summaries: Record<string, ProjectSummary>
  loading: boolean
  error: string | null
  reload: () => Promise<void>
}

export const EMPTY_DASHBOARD: DashboardRead = {
  can_edit: false,
  stats: {
    project_count: 0,
    pending_review_shots: 0,
    running_tasks: 0,
    adopted_videos: 0,
  },
  projects: [],
  recent_tasks: [],
  pending_reviews: [],
}

export function useProjectDashboard(): ProjectDashboardState {
  const [data, setData] = useState<DashboardRead | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await StudioDashboardService.getDashboardApiApiV1StudioDashboardGet()
      setData(response.data ?? EMPTY_DASHBOARD)
    } catch (err) {
      setError(err instanceof Error ? err.message : '工作台数据加载失败')
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  const summaries = useMemo(() => {
    if (!data) return {}
    return Object.fromEntries((data.projects ?? []).map((project) => [project.id, summarizeProject(project)]))
  }, [data])

  return { data, summaries, loading, error, reload }
}

export type { DashboardProjectRead, DashboardRead, DashboardReviewRead, DashboardTaskRead }
