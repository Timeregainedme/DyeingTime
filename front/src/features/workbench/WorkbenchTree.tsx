/**
 * 工作台左侧资源树。
 *
 * 交互目标对齐 IDE 的资源管理器：
 *   - 展开/收起；点击节点切换中央面板；
 *   - 搜索时自动展开命中路径；
 *   - 方向键上下移动、左右展开/收起；
 *   - 选中节点在 URL 变化（刷新/前进后退）后自动滚入视野。
 *
 * 树只渲染已装配好的节点，不在这里发请求；镜头按剧集懒加载，
 * 未展开的剧集不会产生镜头请求。
 */
import { useEffect, useMemo, useRef } from 'react'
import type { KeyboardEvent as ReactKeyboardEvent, MutableRefObject } from 'react'
import {
  AlertTriangle,
  BookOpen,
  Boxes,
  ChevronDown,
  ChevronRight,
  Clapperboard,
  Download,
  FolderTree,
  Loader2,
  Mountain,
  Package,
  Palette,
  RefreshCw,
  Search,
  Settings2,
  Shirt,
  Users,
  X,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { cn } from '../../lib/utils'
import type { WorkbenchNodeKind, WorkbenchTreeNode } from './types'
import { StatusDot } from './components/StatusBadges'
import { collectExpandableIds, filterWorkbenchTree } from './buildTree'

const NODE_ICONS: Record<WorkbenchNodeKind, LucideIcon> = {
  root: FolderTree,
  config: Settings2,
  script: BookOpen,
  style: Palette,
  'assets-root': Boxes,
  'asset-group': Boxes,
  character: Users,
  scene: Mountain,
  prop: Package,
  costume: Shirt,
  episode: Clapperboard,
  'scene-group': FolderTree,
  shot: Clapperboard,
  export: Download,
  loading: Loader2,
  error: AlertTriangle,
}

interface WorkbenchTreeProps {
  tree: WorkbenchTreeNode
  selectedNodeId: string | null
  expanded: Set<string>
  keyword: string
  onKeywordChange: (value: string) => void
  onToggle: (nodeId: string) => void
  onSetExpanded: (nodeIds: string[]) => void
  onSelect: (to: string) => void
  onRefresh: () => void
  refreshing?: boolean
}

/** 收集节点与父节点映射，供键盘左方向键回到父级。 */
function indexTree(root: WorkbenchTreeNode) {
  const nodes = new Map<string, WorkbenchTreeNode>()
  const parents = new Map<string, string>()
  const walk = (node: WorkbenchTreeNode, parentId?: string) => {
    nodes.set(node.id, node)
    if (parentId) parents.set(node.id, parentId)
    node.children.forEach((child) => walk(child, node.id))
  }
  walk(root)
  return { nodes, parents }
}

function statusTitle(node: WorkbenchTreeNode): string | undefined {
  const parts: string[] = []
  if (typeof node.status?.pendingShots === 'number' && node.status.pendingShots > 0) {
    parts.push(`${node.status.pendingShots} 个镜头待确认（shot.status）`)
  }
  if (typeof node.status?.readyShots === 'number' && node.status.readyShots > 0) {
    parts.push(`${node.status.readyShots} 个镜头已确认（shot.status）`)
  }
  if (node.status?.activeTasks) {
    parts.push(`${node.status.activeTasks} 个任务运行中（任务系统）`)
  }
  if (node.kind === 'shot' && node.status?.prep) {
    parts.push(node.status.prep === 'ready' ? '镜头信息已确认' : '镜头信息待确认')
  }
  return parts.length ? parts.join(' · ') : undefined
}

export function WorkbenchTree({
  tree,
  selectedNodeId,
  expanded,
  keyword,
  onKeywordChange,
  onToggle,
  onSetExpanded,
  onSelect,
  onRefresh,
  refreshing = false,
}: WorkbenchTreeProps) {
  const rowRefs = useRef(new Map<string, HTMLButtonElement>())
  const { nodes, parents } = useMemo(() => indexTree(tree), [tree])
  const filtered = useMemo(() => filterWorkbenchTree(tree, keyword), [tree, keyword])
  const searching = keyword.trim().length > 0

  /** URL 选中节点变化后滚到可见位置；用 ref 避免 ID 里的冒号干扰选择器。 */
  useEffect(() => {
    if (!selectedNodeId) return
    rowRefs.current.get(selectedNodeId)?.scrollIntoView({ block: 'nearest' })
  }, [selectedNodeId, expanded, keyword])

  if (!filtered) {
    return (
      <div className="flex h-full flex-col">
        <TreeToolbar
          keyword={keyword}
          onKeywordChange={onKeywordChange}
          onExpandAll={() => onSetExpanded(collectExpandableIds(tree))}
          onCollapseAll={() => onSetExpanded([])}
          onRefresh={onRefresh}
          refreshing={refreshing}
        />
        <p className="px-3 py-6 text-xs text-muted-foreground">没有匹配的节点，清空搜索词试试。</p>
      </div>
    )
  }

  /**
   * 键盘导航。
   *
   * 只在容器上挂一个监听：行本身是 button，保留 Tab/Enter 的原生行为。
   * ArrowDown/Up 在「当前可见行」之间移动，ArrowRight/Left 展开或回到父级。
   */
  const handleKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    const target = event.target as HTMLElement
    const row = target.closest<HTMLButtonElement>('[data-tree-row="true"]')
    if (!row) return
    const nodeId = row.dataset.nodeId ?? ''
    const node = nodes.get(nodeId)
    if (!node) return

    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      const rows = Array.from(
        event.currentTarget.querySelectorAll<HTMLButtonElement>('[data-tree-row="true"]'),
      )
      const index = rows.indexOf(row)
      const next = event.key === 'ArrowDown' ? rows[index + 1] : rows[index - 1]
      next?.focus()
      return
    }

    if (event.key === 'ArrowRight') {
      if (!node.expandable) return
      event.preventDefault()
      if (!expanded.has(nodeId) && !searching) onToggle(nodeId)
      return
    }

    if (event.key === 'ArrowLeft') {
      event.preventDefault()
      if (node.expandable && expanded.has(nodeId) && !searching) {
        onToggle(nodeId)
        return
      }
      const parentId = parents.get(nodeId)
      if (parentId) rowRefs.current.get(parentId)?.focus()
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <TreeToolbar
        keyword={keyword}
        onKeywordChange={onKeywordChange}
        onExpandAll={() => onSetExpanded(collectExpandableIds(tree))}
        onCollapseAll={() => onSetExpanded([])}
        onRefresh={onRefresh}
        refreshing={refreshing}
      />

      <div
        className="min-h-0 flex-1 overflow-auto py-1"
        role="tree"
        aria-label="项目资源树"
        onKeyDown={handleKeyDown}
      >
        <TreeRow
          node={filtered}
          depth={0}
          selectedNodeId={selectedNodeId}
          expanded={expanded}
          searching={searching}
          rowRefs={rowRefs}
          onToggle={onToggle}
          onSelect={onSelect}
        />
      </div>

      <p className="border-t border-border px-3 py-2 text-[10px] leading-4 text-muted-foreground">
        镜头在展开剧集时加载；搜索只覆盖已加载节点。
      </p>
    </div>
  )
}

function TreeToolbar({
  keyword,
  onKeywordChange,
  onExpandAll,
  onCollapseAll,
  onRefresh,
  refreshing,
}: {
  keyword: string
  onKeywordChange: (value: string) => void
  onExpandAll: () => void
  onCollapseAll: () => void
  onRefresh: () => void
  refreshing: boolean
}) {
  return (
    <div className="space-y-2 border-b border-border p-2.5">
      <div className="relative">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={keyword}
          onChange={(event) => onKeywordChange(event.target.value)}
          placeholder="搜索节点"
          aria-label="搜索项目资源"
          className="h-8 pl-8 pr-8 text-xs"
        />
        {keyword ? (
          <button
            type="button"
            aria-label="清空搜索"
            className="absolute right-1.5 top-1/2 flex h-5 w-5 -translate-y-1/2 items-center justify-center rounded text-muted-foreground hover:bg-accent"
            onClick={() => onKeywordChange('')}
          >
            <X className="h-3 w-3" />
          </button>
        ) : null}
      </div>
      <div className="flex items-center gap-1">
        <Button variant="ghost" size="sm" className="h-6 px-1.5 text-[11px]" onClick={onExpandAll}>
          全部展开
        </Button>
        <Button variant="ghost" size="sm" className="h-6 px-1.5 text-[11px]" onClick={onCollapseAll}>
          全部收起
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="ml-auto h-6 w-6"
          aria-label="刷新项目数据"
          onClick={onRefresh}
          disabled={refreshing}
        >
          <RefreshCw className={cn('h-3 w-3', refreshing && 'animate-spin')} />
        </Button>
      </div>
    </div>
  )
}

function TreeRow({
  node,
  depth,
  selectedNodeId,
  expanded,
  searching,
  rowRefs,
  onToggle,
  onSelect,
}: {
  node: WorkbenchTreeNode
  depth: number
  selectedNodeId: string | null
  expanded: Set<string>
  searching: boolean
  rowRefs: MutableRefObject<Map<string, HTMLButtonElement>>
  onToggle: (nodeId: string) => void
  onSelect: (to: string) => void
}) {
  const Icon = NODE_ICONS[node.kind]
  // 搜索时把所有命中节点的后代直接铺开，避免用户还要逐级展开找结果。
  const isExpanded = searching ? true : expanded.has(node.id)
  const hasChildren = node.children.length > 0
  const selected = selectedNodeId === node.id
  const isPlaceholder = node.kind === 'loading' || node.kind === 'error'

  const activate = () => {
    if (!node.selectable) {
      if (node.expandable && hasChildren) onToggle(node.id)
      return
    }
    if (node.to) onSelect(node.to)
  }

  return (
    <div role="none">
      <div
        role="treeitem"
        aria-level={depth + 1}
        aria-selected={selected}
        aria-expanded={node.expandable && hasChildren ? isExpanded : undefined}
        className={cn(
          'group flex items-center gap-1 rounded-sm pr-1.5',
          selected ? 'bg-primary/10 text-primary' : 'hover:bg-accent',
        )}
        style={{ paddingLeft: depth * 12 + 4 }}
      >
        {node.expandable && hasChildren ? (
          <button
            type="button"
            aria-label={isExpanded ? `收起 ${node.label}` : `展开 ${node.label}`}
            tabIndex={-1}
            className="flex h-6 w-5 shrink-0 items-center justify-center rounded text-muted-foreground hover:text-foreground"
            onClick={(event) => {
              event.stopPropagation()
              if (!searching) onToggle(node.id)
            }}
          >
            {isExpanded ? (
              <ChevronDown className="h-3.5 w-3.5" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" />
            )}
          </button>
        ) : (
          <span className="w-5 shrink-0" aria-hidden="true" />
        )}

        <button
          type="button"
          data-tree-row="true"
          data-node-id={node.id}
          disabled={isPlaceholder}
          ref={(element) => {
            if (element) rowRefs.current.set(node.id, element)
            else rowRefs.current.delete(node.id)
          }}
          onClick={activate}
          className={cn(
            'flex min-w-0 flex-1 items-center gap-1.5 rounded-sm py-1 text-left text-xs',
            isPlaceholder && 'cursor-default opacity-70',
            !node.selectable && !isPlaceholder && 'cursor-default',
          )}
          title={statusTitle(node) ?? node.hint}
        >
          <Icon
            className={cn(
              'h-3.5 w-3.5 shrink-0',
              isPlaceholder && node.kind === 'loading' && 'animate-spin',
              selected ? 'text-primary' : 'text-muted-foreground',
            )}
          />
          <span className="min-w-0 flex-1 truncate">{node.label}</span>

          {/* 三组状态点彼此独立：待确认 / 运行中 / 已确认不合并成一个图标。 */}
          <span className="flex shrink-0 items-center gap-0.5">
            {typeof node.status?.pendingShots === 'number' && node.status.pendingShots > 0 ? (
              <StatusDot group="state" active title={`${node.status.pendingShots} 个镜头待确认`} />
            ) : null}
            {node.status?.prep === 'pending' ? <StatusDot group="state" active title="待确认" /> : null}
            {node.status?.activeTasks ? (
              <StatusDot group="run" active title={`${node.status.activeTasks} 个任务运行中`} />
            ) : null}
          </span>

          {node.hint && node.kind !== 'shot' ? (
            <span className="hidden max-w-[45%] shrink-0 truncate text-[10px] text-muted-foreground xl:inline">
              {node.hint}
            </span>
          ) : null}
        </button>
      </div>

      {isExpanded && hasChildren
        ? node.children.map((child) => (
            <TreeRow
              key={child.id}
              node={child}
              depth={depth + 1}
              selectedNodeId={selectedNodeId}
              expanded={expanded}
              searching={searching}
              rowRefs={rowRefs}
              onToggle={onToggle}
              onSelect={onSelect}
            />
          ))
        : null}
    </div>
  )
}
