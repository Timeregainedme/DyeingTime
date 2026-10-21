import { message } from 'antd'
import type { NavigateFunction } from 'react-router-dom'

import { getChapterShotsPath, getChapterStudioPath } from './routes'

export type EnsureHasShotsBeforeShootingArgs = {
  projectId: string | undefined
  chapterId: string | undefined
  storyboardCount: number | undefined | null
  navigate: NavigateFunction
}

const NO_SHOTS_TIP = '请进入分镜页面提取分镜后进行拍摄'

export function ensureHasShotsBeforeShooting(args: EnsureHasShotsBeforeShootingArgs) {
  const { projectId, chapterId, storyboardCount, navigate } = args
  if (!projectId || !chapterId) return

  const count = typeof storyboardCount === 'number' && Number.isFinite(storyboardCount) ? storyboardCount : 0
  if (count <= 0) {
    message.warning(NO_SHOTS_TIP)
    navigate(getChapterShotsPath(projectId, chapterId))
    return
  }

  navigate(getChapterStudioPath(projectId, chapterId))
}

