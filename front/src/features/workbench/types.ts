/**
 * 树状工作台的节点模型。
 *
 * 这里刻意把「节点类型」与「业务状态」分开：
 *   - kind 决定图标、路由与可展开行为；
 *   - status 只承载三类互不替代的状态摘要（信息确认 / 运行时 / 镜头计数），
 *     不引入新的状态机，也不修改后端字段语义。
 */
import type { ChapterRead, ShotRead } from '../../services/generated'
import type { WorkbenchAssetType } from './routes'

/**
 * 节点类型。
 *
 * `scene-group` 是给 P5「场次」预留的渲染分支；当前数据库没有场次实体，
 * 所以 buildTree 永远不会产出这种节点——预留类型不等于伪造数据。
 */
export type WorkbenchNodeKind =
  | 'root'
  | 'config'
  | 'script'
  | 'style'
  | 'assets-root'
  | 'asset-group'
  | 'character'
  | 'scene'
  | 'prop'
  | 'costume'
  | 'episode'
  | 'scene-group'
  | 'shot'
  | 'export'
  | 'loading'
  | 'error'

/** 树节点上的状态摘要。三组字段对应三种语义，渲染时必须使用不同颜色组。 */
export interface WorkbenchNodeStatus {
  /** `shot.status`：信息提取与确认状态。 */
  prep?: 'pending' | 'ready'
  /** 运行时任务：来自 GenerationTask / runtime summary，不写入 shot.status。 */
  activeTasks?: number
  /** 剧集节点聚合：本集待确认镜头数。 */
  pendingShots?: number
  /** 剧集节点聚合：本集已就绪镜头数。 */
  readyShots?: number
}

/** 节点的业务元信息，用于跳转与右侧属性面板定位。 */
export interface WorkbenchNodeMeta {
  chapterId?: string
  shotId?: string
  assetType?: WorkbenchAssetType
  assetId?: string
}

export interface WorkbenchTreeNode {
  /** 稳定 ID，只用业务 ID 拼接，不用数组下标。 */
  id: string
  kind: WorkbenchNodeKind
  label: string
  /** 省略时为纯分组节点：点击只展开/收起，不切换路由。 */
  to?: string
  /** 次要说明（标题、错误原因、空状态提示等）。 */
  hint?: string
  selectable: boolean
  expandable: boolean
  children: WorkbenchTreeNode[]
  status?: WorkbenchNodeStatus
  meta?: WorkbenchNodeMeta
}

/** 资产列表统一形状：后端实体接口返回 dict，这里只保留树与面板真正用到的字段。 */
export interface WorkbenchAssetItem {
  id: string
  name: string
  description?: string
  style?: string
  visualStyle?: string
  thumbnail?: string
}

/** 每集镜头的加载状态；只对「已展开」的剧集产生记录。 */
export type ChapterLoadState = 'loading' | 'error'

export interface BuildWorkbenchTreeInput {
  projectId: string
  projectName: string
  chapters: ChapterRead[]
  /** 已加载的镜头；key 为章节 ID。未加载的章节不放进 map，树里会显示加载占位。 */
  shotsByChapter: Record<string, ShotRead[]>
  /** 每集运行中任务摘要；key 为章节 ID。 */
  runtimeByChapter: Record<string, Record<string, number>>
  /** 已展开且尚未加载成功的章节状态。 */
  chapterLoadState: Record<string, ChapterLoadState>
  characters: WorkbenchAssetItem[]
  scenes: WorkbenchAssetItem[]
  props: WorkbenchAssetItem[]
  costumes: WorkbenchAssetItem[]
  projectNameFallback?: string
}
