import { StudioShotsService } from '../../../../services/generated'
import type { ShotRead, ShotRuntimeSummaryRead } from '../../../../services/generated'

type ChapterLike = {
  id: string
  index?: number
  title?: string
}

export type ProjectFlowStats = {
  totalShots: number
  pendingConfirmShots: number
  readyShots: number
  generatingShots: number
}

export type ChapterFlowStats = ProjectFlowStats & {
  chapterId: string
  chapterIndex?: number
  chapterTitle?: string
}

async function loadFlowStatsForChapter(chapter: ChapterLike): Promise<ChapterFlowStats> {
  const [shotsRes, runtimeRes] = await Promise.all([
    StudioShotsService.listShotsApiV1StudioShotsGet({
      chapterId: chapter.id,
      page: 1,
      pageSize: 100,
      order: 'index',
      isDesc: false,
    }),
    StudioShotsService.listShotRuntimeSummaryApiV1StudioShotsRuntimeSummaryGet({
      chapterId: chapter.id,
    }),
  ])
  const shots: ShotRead[] = shotsRes.data?.items ?? []
  const runtimeRows: ShotRuntimeSummaryRead[] = runtimeRes.data ?? []
  const runtimeMap = Object.fromEntries(runtimeRows.map((row) => [row.shot_id, row]))

  const totalShots = shots.length
  const generatingShots = shots.filter((shot) => Boolean(runtimeMap[shot.id]?.has_active_tasks)).length
  const readyShots = shots.filter((shot) => shot.status === 'ready' && !runtimeMap[shot.id]?.has_active_tasks).length
  const pendingConfirmShots = shots.filter((shot) => shot.status !== 'ready' && !runtimeMap[shot.id]?.has_active_tasks).length

  return {
    chapterId: chapter.id,
    chapterIndex: chapter.index,
    chapterTitle: chapter.title,
    totalShots,
    pendingConfirmShots,
    readyShots,
    generatingShots,
  }
}

export async function loadChapterFlowStats(
  chapters: ChapterLike[],
): Promise<ChapterFlowStats[]> {
  if (!chapters.length) return []
  return Promise.all(chapters.map((chapter) => loadFlowStatsForChapter(chapter)))
}

export async function loadProjectFlowStatsForChapters(
  chapters: ChapterLike[],
): Promise<ProjectFlowStats> {
  if (!chapters.length) {
    return {
      totalShots: 0,
      pendingConfirmShots: 0,
      readyShots: 0,
      generatingShots: 0,
    }
  }

  const chapterResults = await loadChapterFlowStats(chapters)

  return chapterResults.reduce<ProjectFlowStats>(
    (acc, item) => ({
      totalShots: acc.totalShots + item.totalShots,
      pendingConfirmShots: acc.pendingConfirmShots + item.pendingConfirmShots,
      readyShots: acc.readyShots + item.readyShots,
      generatingShots: acc.generatingShots + item.generatingShots,
    }),
    {
      totalShots: 0,
      pendingConfirmShots: 0,
      readyShots: 0,
      generatingShots: 0,
    },
  )
}
