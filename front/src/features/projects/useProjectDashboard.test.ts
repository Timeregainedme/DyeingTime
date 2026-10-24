import { describe, expect, it } from 'vitest'
import { summarizeProject } from './useProjectDashboard'
import type { DashboardProjectRead } from '../../services/generated'

/**
 * 首页阶段摘要的回归测试。
 *
 * 这里锁住的是「用户点继续创作会落到哪一步」：
 * 只要章节准备态规则不变，摘要就必须按 录入原文 → 提取分镜 → 准备镜头 的顺序
 * 选第一个未完成的章节，而不能被「最近修改」带偏。
 */
function project(overrides: Partial<DashboardProjectRead> = {}): DashboardProjectRead {
  return {
    id: 'p1',
    name: '测试项目',
    description: '',
    style: '真人都市',
    visual_style: '现实',
    updated_at: '2026-10-24T00:00:00',
    chapter_count: 1,
    chapters: [],
    total_shots: 0,
    pending_shots: 0,
    ready_shots: 0,
    pending_review_shots: 0,
    adopted_videos: 0,
    running_tasks: 0,
    ...overrides,
  }
}

function chapter(id: string, index: number, hasRawText: boolean, storyboardCount: number) {
  return {
    id,
    index,
    title: `第${index}章`,
    has_raw_text: hasRawText,
    storyboard_count: storyboardCount,
    status: 'draft',
  }
}

describe('summarizeProject', () => {
  it('没有章节时提示创建第一章', () => {
    const summary = summarizeProject(project())
    expect(summary.stageKey).toBe('create_first_chapter')
    expect(summary.chapterCount).toBe(0)
  })

  it('有原文但无分镜时建议提取分镜', () => {
    const summary = summarizeProject(
      project({ chapters: [chapter('c1', 1, true, 0)], chapter_count: 1 }),
    )
    expect(summary.stageKey).toBe('extract_shots')
    expect(summary.actionLabel).toBe('提取分镜')
    expect(summary.chapterId).toBe('c1')
  })

  it('优先返回最靠前的未完成章节，而不是最后一章', () => {
    const summary = summarizeProject(
      project({
        chapter_count: 2,
        chapters: [chapter('c1', 1, false, 0), chapter('c2', 2, true, 0)],
      }),
    )
    expect(summary.stageKey).toBe('edit_raw')
    expect(summary.chapterId).toBe('c1')
  })

  it('章节都有分镜时进入准备镜头阶段', () => {
    const summary = summarizeProject(
      project({
        chapter_count: 1,
        chapters: [chapter('c1', 1, true, 8)],
        total_shots: 8,
        pending_shots: 2,
        ready_shots: 6,
      }),
    )
    expect(summary.stageKey).toBe('prepare_shots')
    expect(summary.actionLabel).toBe('查看镜头看板')
    expect(summary.flow?.readyShots).toBe(6)
  })
})
