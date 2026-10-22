/**
 * 章节制作阶段推导（工作台版本）。
 *
 * 语义与 `pages/aiStudio/project/ProjectWorkbench/chapterPreparation.tsx` 保持一致：
 * 录入原文 → 提取分镜 → 准备镜头 → 拍摄。
 *
 * 为什么不直接复用旧函数：旧函数返回 antd 图标节点，且依赖旧版 UI 的 Chapter 类型；
 * 工作台要求新代码不引入 antd。这里保留同一套判定顺序，P8 统一页面时再合并。
 */
import type { ChapterRead } from '../../services/generated'

export type ChapterStageKey = 'edit_raw' | 'extract_shots' | 'prepare_shots' | 'shoot'

export interface ChapterStage {
  key: ChapterStageKey
  label: string
  hint: string
}

export function deriveChapterStage(chapter: ChapterRead): ChapterStage {
  const hasRawText = Boolean((chapter.raw_text ?? '').trim())
  const shotCount = chapter.shot_count ?? chapter.storyboard_count ?? 0

  if (!hasRawText) {
    return {
      key: 'edit_raw',
      label: '待录入原文',
      hint: '先补章节原文，再进入分镜流程',
    }
  }
  if (shotCount === 0) {
    return {
      key: 'extract_shots',
      label: '待提取分镜',
      hint: '已有章节原文，下一步建议先提取分镜',
    }
  }
  if (chapter.status === 'shooting' || chapter.status === 'done') {
    return {
      key: 'shoot',
      label: '可进入拍摄',
      hint: '当前章节已具备分镜，可继续进入拍摄',
    }
  }
  return {
    key: 'prepare_shots',
    label: '待准备镜头',
    hint: '已有分镜，建议先补齐镜头的信息提取与确认',
  }
}

/**
 * 挑出「最该先处理」的一集。
 *
 * 顺序刻意固定为主流程的真实先后关系；全部完成时回落到集数最小的一集，
 * 保证页面永远有一个可执行的下一步，而不是显示空白。
 */
export function pickRecommendedChapter(chapters: ChapterRead[]): ChapterRead | null {
  const ordered = [...chapters].sort((a, b) => a.index - b.index)
  if (!ordered.length) return null
  const order: ChapterStageKey[] = ['edit_raw', 'extract_shots', 'prepare_shots', 'shoot']
  for (const key of order) {
    const found = ordered.find((chapter) => deriveChapterStage(chapter).key === key)
    if (found) return found
  }
  return ordered[0]
}
