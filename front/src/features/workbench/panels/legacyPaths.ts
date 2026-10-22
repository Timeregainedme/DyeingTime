/**
 * 旧版页面入口路径。
 *
 * P1 不重写资产生成、镜头准备与工作室，只提供明确的业务跳转。
 * 路径拼接集中在这里，避免各面板手写字符串导致参数漏编码或路由漂移。
 * 章节 / 镜头 / 工作室的路径直接复用旧版路由工具，保持单一来源。
 */
import type { WorkbenchAssetType } from '../routes'
import {
  getChapterShotEditPath,
  getChapterShotsPath,
  getChapterStudioPath,
  getProjectEditorPath,
} from '../../../pages/aiStudio/project/ProjectWorkbench/routes'

/** 旧版项目页的 tab 入口（settings / chapters / roles 等由旧页解析）。 */
export function legacyProjectTabPath(projectId: string, tab: string): string {
  return `/projects/${encodeURIComponent(projectId)}?tab=${encodeURIComponent(tab)}`
}

export function legacyChapterListPath(projectId: string): string {
  return legacyProjectTabPath(projectId, 'chapters')
}

export function legacyShotListPath(projectId: string, chapterId: string): string {
  return getChapterShotsPath(projectId, chapterId)
}

export function legacyShotEditPath(projectId: string, chapterId: string, shotId: string): string {
  return getChapterShotEditPath(projectId, chapterId, shotId)
}

export function legacyStudioPath(projectId: string, chapterId: string): string {
  return getChapterStudioPath(projectId, chapterId)
}

export function legacyEditorPath(projectId: string): string {
  return getProjectEditorPath(projectId)
}

/** 资产列表：角色在项目页的 roles tab，其余在工作区资产库。 */
export function legacyAssetListPath(projectId: string, assetType: WorkbenchAssetType): string {
  return assetType === 'character' ? legacyProjectTabPath(projectId, 'roles') : '/assets'
}

const LEGACY_ASSET_SEGMENTS: Record<Exclude<WorkbenchAssetType, 'character'>, string> = {
  scene: 'scenes',
  prop: 'props',
  costume: 'costumes',
}

/** 单个资产的旧版编辑页。 */
export function legacyAssetEditPath(
  projectId: string,
  assetType: WorkbenchAssetType,
  assetId: string,
): string {
  if (assetType === 'character') {
    return `/projects/${encodeURIComponent(projectId)}/roles/${encodeURIComponent(assetId)}/edit`
  }
  return `/assets/${LEGACY_ASSET_SEGMENTS[assetType]}/${encodeURIComponent(assetId)}/edit`
}
