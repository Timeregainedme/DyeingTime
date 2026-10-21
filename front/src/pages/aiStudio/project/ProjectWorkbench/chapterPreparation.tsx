import type { ReactNode } from 'react'
import {
  EditOutlined,
  FileSearchOutlined,
  ScissorOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons'
import type { Chapter } from './hooks/useProjectData'

export type ChapterPreparationState = {
  key: 'edit_raw' | 'extract_shots' | 'prepare_shots' | 'shoot'
  text: string
  color: string
  hint: string
  primaryAction: string
  primaryIcon: ReactNode
}

export function getChapterPreparationState(chapter: Chapter): ChapterPreparationState {
  const hasRawText = !!chapter.rawText?.trim()
  const hasShots = (chapter.storyboardCount ?? 0) > 0
  if (!hasRawText) {
    return {
      key: 'edit_raw',
      text: '待录入原文',
      color: 'default',
      hint: '先补章节原文，再进入分镜流程',
      primaryAction: '编辑原文',
      primaryIcon: <EditOutlined />,
    }
  }
  if (!hasShots) {
    return {
      key: 'extract_shots',
      text: '待提取分镜',
      color: 'gold',
      hint: '已有章节原文，下一步建议先提取分镜',
      primaryAction: '提取分镜',
      primaryIcon: <ScissorOutlined />,
    }
  }
  if (chapter.status === 'shooting' || chapter.status === 'done') {
    return {
      key: 'shoot',
      text: '可进入拍摄',
      color: 'green',
      hint: '当前章节已具备分镜，可继续进入拍摄',
      primaryAction: '进入拍摄',
      primaryIcon: <VideoCameraOutlined />,
    }
  }
  return {
    key: 'prepare_shots',
    text: '待准备镜头',
    color: 'blue',
    hint: '已有分镜，建议先进入分镜工作室补齐镜头准备',
    primaryAction: '进入分镜工作室',
    primaryIcon: <FileSearchOutlined />,
  }
}
