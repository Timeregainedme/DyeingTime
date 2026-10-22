import { describe, expect, it } from 'vitest'
import {
  isWorkbenchPath,
  parseWorkbenchSelection,
  workbenchAssetDetailPath,
  workbenchAssetGroupPath,
  workbenchConfigPath,
  workbenchEpisodePath,
  workbenchExportPath,
  workbenchOverviewPath,
  workbenchScriptPath,
  workbenchShotPath,
  workbenchStylePath,
} from './routes'

const PID = 'project-1'

describe('isWorkbenchPath', () => {
  it('识别工作台根路径与子路径', () => {
    expect(isWorkbenchPath('/projects/p1/workbench')).toBe(true)
    expect(isWorkbenchPath('/projects/p1/workbench/episodes/c1')).toBe(true)
    expect(isWorkbenchPath('/projects/p1/workbenchish')).toBe(false)
    expect(isWorkbenchPath('/projects/p1')).toBe(false)
  })
})

describe('parseWorkbenchSelection', () => {
  it('根路径与 overview 都解析为项目总览', () => {
    expect(parseWorkbenchSelection(`/projects/${PID}/workbench`, PID)).toEqual({ kind: 'overview' })
    expect(parseWorkbenchSelection(`/projects/${PID}/workbench/overview`, PID)).toEqual({
      kind: 'overview',
    })
    expect(parseWorkbenchSelection(`/projects/${PID}/workbench/`, PID)).toEqual({ kind: 'overview' })
  })

  it('解析静态节点', () => {
    expect(parseWorkbenchSelection(`/projects/${PID}/workbench/config`, PID)).toEqual({
      kind: 'config',
    })
    expect(parseWorkbenchSelection(`/projects/${PID}/workbench/style`, PID)).toEqual({
      kind: 'style',
    })
    expect(parseWorkbenchSelection(`/projects/${PID}/workbench/export`, PID)).toEqual({
      kind: 'export',
    })
  })

  it('解析剧本：项目级与单集', () => {
    expect(parseWorkbenchSelection(`/projects/${PID}/workbench/script`, PID)).toEqual({
      kind: 'script',
    })
    expect(
      parseWorkbenchSelection(`/projects/${PID}/workbench/script/chapter%201`, PID),
    ).toEqual({ kind: 'script', chapterId: 'chapter 1' })
  })

  it('解析资产列表与详情', () => {
    expect(
      parseWorkbenchSelection(`/projects/${PID}/workbench/assets/scene`, PID),
    ).toEqual({ kind: 'assets', assetType: 'scene', assetId: undefined })
    expect(
      parseWorkbenchSelection(`/projects/${PID}/workbench/assets/character/c-1`, PID),
    ).toEqual({ kind: 'assets', assetType: 'character', assetId: 'c-1' })
  })

  it('非法资产类型与未知路径不静默回退', () => {
    expect(
      parseWorkbenchSelection(`/projects/${PID}/workbench/assets/actor`, PID).kind,
    ).toBe('unknown')
    expect(
      parseWorkbenchSelection(`/projects/${PID}/workbench/episodes`, PID).kind,
    ).toBe('unknown')
    expect(
      parseWorkbenchSelection(`/projects/${PID}/workbench/nope/deep`, PID).kind,
    ).toBe('unknown')
  })

  it('解析剧集与镜头', () => {
    expect(parseWorkbenchSelection(`/projects/${PID}/workbench/episodes/c-1`, PID)).toEqual({
      kind: 'episode',
      chapterId: 'c-1',
    })
    expect(
      parseWorkbenchSelection(`/projects/${PID}/workbench/episodes/c-1/shots/s-9`, PID),
    ).toEqual({ kind: 'shot', chapterId: 'c-1', shotId: 's-9' })
  })

  it('支持未编码的项目 ID（手输地址）', () => {
    expect(parseWorkbenchSelection('/projects/p 1/workbench/config', 'p 1')).toEqual({
      kind: 'config',
    })
  })

  it('项目 ID 不匹配时返回 unknown', () => {
    expect(parseWorkbenchSelection('/projects/other/workbench/config', PID).kind).toBe('unknown')
  })
})

describe('路径构造与解析可往返', () => {
  const cases = [
    workbenchOverviewPath(PID),
    workbenchConfigPath(PID),
    workbenchScriptPath(PID),
    workbenchScriptPath(PID, 'c 1'),
    workbenchStylePath(PID),
    workbenchAssetGroupPath(PID, 'prop'),
    workbenchAssetDetailPath(PID, 'prop', 'p 1'),
    workbenchEpisodePath(PID, 'c/1'),
    workbenchShotPath(PID, 'c/1', 's/1'),
    workbenchExportPath(PID),
  ]

  it.each(cases)('%s 能被解析', (path) => {
    expect(parseWorkbenchSelection(path, PID).kind).not.toBe('unknown')
  })
})
