/**
 * 工作台外壳布局。
 *
 * 结构（对齐 IDE 的资源管理体验）：
 *   顶部：返回项目列表 / 项目名称 / 制作进度 / 主题与账号
 *   左侧：项目资源树（可拖拽调宽；窄屏为抽屉）
 *   中央：当前节点面板（唯一滚动区）
 *   右侧：属性面板（可收起、可拖拽调宽；窄屏为抽屉）
 *   底部：任务中心（可收起、可拖拽调高）
 *
 * 旧版侧边栏在 `AppShell` 里对工作台路径直接关闭，因此不会出现双导航。
 */
import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import type { KeyboardEvent as ReactKeyboardEvent, PointerEvent as ReactPointerEvent, ReactNode } from 'react'
import {
  ArrowLeft,
  ChevronDown,
  ExternalLink,
  Languages,
  LogOut,
  Moon,
  PanelLeft,
  PanelRight,
  Settings2,
  Sun,
  User as UserIcon,
} from 'lucide-react'
import { Button } from '../../components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../../components/ui/dropdown-menu'
import { Tooltip, TooltipContent, TooltipTrigger } from '../../components/ui/tooltip'
import { cn } from '../../lib/utils'
import { useAuthStore } from '../../store/useAuthStore'
import { useAppStore } from '../../store/useAppStore'
import { useThemeStore } from '../../store/useThemeStore'
import { WorkbenchTaskDock } from './WorkbenchTaskDock'
import { useMediaQuery } from './useMediaQuery'
import { usePanelResize } from './usePanelResize'

interface WorkbenchLayoutProps {
  projectId: string
  projectName: string
  projectStyle?: string
  progress: number
  tree: ReactNode
  center: ReactNode
  inspector: ReactNode
}

const LEFT_STORAGE_KEY = 'dyeingtime_workbench_left_width_v1'
const RIGHT_STORAGE_KEY = 'dyeingtime_workbench_right_width_v1'
const DOCK_STORAGE_KEY = 'dyeingtime_workbench_dock_height_v1'

/** 分隔条：可拖拽 + 键盘可调，焦点态给出可见反馈。 */
function ResizeHandle({
  orientation,
  onPointerDown,
  onKeyDown,
  resizing,
  label,
}: {
  orientation: 'vertical' | 'horizontal'
  onPointerDown: (event: ReactPointerEvent<HTMLElement>) => void
  onKeyDown: (event: ReactKeyboardEvent<HTMLElement>) => void
  resizing: boolean
  label: string
}) {
  return (
    <div
      role="separator"
      aria-orientation={orientation}
      aria-label={label}
      tabIndex={0}
      onPointerDown={onPointerDown}
      onKeyDown={onKeyDown}
      className={cn(
        'group relative z-10 shrink-0 touch-none',
        orientation === 'vertical' ? 'w-1 cursor-col-resize' : 'h-1 cursor-row-resize',
        'hover:bg-primary/20 focus-visible:bg-primary/30 focus-visible:outline-none',
        resizing && 'bg-primary/30',
      )}
    >
      <span
        className={cn(
          'absolute bg-border transition-colors group-hover:bg-primary/50',
          orientation === 'vertical'
            ? 'inset-y-0 left-1/2 w-px -translate-x-1/2'
            : 'inset-x-0 top-1/2 h-px -translate-y-1/2',
        )}
      />
    </div>
  )
}

export function WorkbenchLayout({
  projectId,
  projectName,
  projectStyle,
  progress,
  tree,
  center,
  inspector,
}: WorkbenchLayoutProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const isDesktop = useMediaQuery('(min-width: 1024px)')
  const isWide = useMediaQuery('(min-width: 1280px)')

  const user = useAuthStore((state) => state.user)
  const clearSession = useAuthStore((state) => state.clearSession)
  const language = useAppStore((state) => state.language)
  const setLanguage = useAppStore((state) => state.setLanguage)
  const resolvedTheme = useThemeStore((state) => state.resolved)
  const toggleTheme = useThemeStore((state) => state.toggle)

  const left = usePanelResize({
    axis: 'x',
    initial: 280,
    min: 220,
    max: 420,
    storageKey: LEFT_STORAGE_KEY,
  })
  const right = usePanelResize({
    axis: 'x',
    initial: 300,
    min: 240,
    max: 420,
    invert: true,
    storageKey: RIGHT_STORAGE_KEY,
  })
  const dock = usePanelResize({
    axis: 'y',
    initial: 168,
    min: 120,
    max: 360,
    invert: true,
    storageKey: DOCK_STORAGE_KEY,
  })

  const [inspectorOpen, setInspectorOpen] = useState(true)
  const [dockOpen, setDockOpen] = useState(true)
  const [mobileTreeOpen, setMobileTreeOpen] = useState(false)

  /**
   * 节点切换后自动收起抽屉。
   *
   * 只对窄屏生效：桌面端属性面板是常驻的，不能因为切节点就被关掉。
   */
  useEffect(() => {
    setMobileTreeOpen(false)
    if (!isWide) setInspectorOpen(false)
  }, [location.pathname, isWide])

  const displayName = user?.display_name || user?.username || '未登录'
  const clampedProgress = Math.min(100, Math.max(0, progress))

  /** 退出登录：与 AppShell 行为一致，先尽力通知后端，再清本地会话。 */
  const logout = () => {
    void fetch('/api/v1/auth/logout', { method: 'POST' }).catch(() => undefined)
    clearSession()
    navigate('/login', { replace: true })
  }

  /** 语言切换：沿用全局偏好；工作台文案仍以中文为主。 */
  const changeLanguage = (value: string) => {
    setLanguage(value as typeof language)
    try {
      window.localStorage.setItem('dyeingtime_language', value)
    } catch {
      // ignore
    }
    document.documentElement.lang = value === 'en-US' ? 'en' : 'zh-CN'
  }

  const accountMenu = useMemo(
    () => (
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuLabel className="flex items-center gap-1.5">
          <UserIcon className="h-3.5 w-3.5" />
          {displayName}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => navigate('/projects')}>项目列表</DropdownMenuItem>
        <DropdownMenuItem onClick={() => navigate('/settings')}>
          <Settings2 className="h-4 w-4" />
          设置
        </DropdownMenuItem>
        <DropdownMenuItem onClick={logout}>
          <LogOut className="h-4 w-4" />
          退出登录
        </DropdownMenuItem>
      </DropdownMenuContent>
    ),
    // logout/changeLanguage 都是稳定的 store 方法或局部函数，只随显示名重建即可
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [displayName, navigate],
  )

  return (
    <div className="flex h-screen min-w-0 flex-col overflow-hidden bg-background">
      <header className="flex h-14 shrink-0 items-center gap-2 border-b border-border bg-card px-3">
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden"
          aria-label="打开资源树"
          onClick={() => setMobileTreeOpen(true)}
        >
          <PanelLeft className="h-4 w-4" />
        </Button>

        <Button variant="ghost" size="sm" asChild>
          <Link to="/projects" className="gap-1.5 px-2 text-xs">
            <ArrowLeft className="h-3.5 w-3.5" />
            项目列表
          </Link>
        </Button>

        <span className="hidden h-5 w-px bg-border sm:block" />

        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 items-center gap-2">
            <h1 className="truncate text-sm font-semibold">{projectName}</h1>
            {projectStyle ? (
              <span className="hidden shrink-0 rounded-full bg-secondary px-2 py-0.5 text-[10px] text-secondary-foreground sm:inline">
                {projectStyle}
              </span>
            ) : null}
          </div>
          <div className="mt-0.5 flex items-center gap-2">
            <div className="h-1 w-24 overflow-hidden rounded-full bg-muted sm:w-40">
              <div className="h-full rounded-full bg-primary" style={{ width: `${clampedProgress}%` }} />
            </div>
            <span className="text-[10px] tabular-nums text-muted-foreground">
              制作进度 {clampedProgress}%
            </span>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-0.5">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" asChild aria-label="打开旧版项目页">
                <Link to={`/projects/${projectId}?tab=dashboard`}>
                  <ExternalLink className="h-4 w-4" />
                </Link>
              </Button>
            </TooltipTrigger>
            <TooltipContent>旧版项目页（同一标签页）</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setInspectorOpen((value) => !value)}
                aria-label={inspectorOpen ? '收起属性面板' : '展开属性面板'}
              >
                <PanelRight className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>{inspectorOpen ? '收起属性面板' : '展开属性面板'}</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleTheme}
                aria-label={resolvedTheme === 'dark' ? '切换到浅色' : '切换到深色'}
              >
                {resolvedTheme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </Button>
            </TooltipTrigger>
            <TooltipContent>{resolvedTheme === 'dark' ? '切换到浅色' : '切换到深色'}</TooltipContent>
          </Tooltip>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="切换语言">
                <Languages className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>语言</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => changeLanguage('zh-CN')}>
                简体中文 {language === 'zh-CN' ? '✓' : ''}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => changeLanguage('en-US')}>
                English {language === 'en-US' ? '✓' : ''}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" className="gap-1.5 px-1.5">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-secondary text-[11px] font-medium">
                  {displayName.slice(0, 1).toUpperCase()}
                </span>
                <ChevronDown className="hidden h-3 w-3 text-muted-foreground md:block" />
              </Button>
            </DropdownMenuTrigger>
            {accountMenu}
          </DropdownMenu>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        {isDesktop ? (
          <>
            <div
              className="flex min-h-0 shrink-0 flex-col border-r border-border bg-card"
              style={{ width: left.size }}
            >
              {tree}
            </div>
            <ResizeHandle
              orientation="vertical"
              label="调整资源树宽度"
              onPointerDown={left.onPointerDown}
              onKeyDown={left.onKeyDown}
              resizing={left.resizing}
            />
          </>
        ) : null}

        <main className="min-w-0 flex-1 overflow-auto" aria-label="工作区">
          <div className="mx-auto w-full max-w-[1400px] p-4">{center}</div>
        </main>

        {isWide && inspectorOpen ? (
          <>
            <ResizeHandle
              orientation="vertical"
              label="调整属性面板宽度"
              onPointerDown={right.onPointerDown}
              onKeyDown={right.onKeyDown}
              resizing={right.resizing}
            />
            <div
              className="flex min-h-0 shrink-0 flex-col border-l border-border bg-card"
              style={{ width: right.size }}
            >
              {inspector}
            </div>
          </>
        ) : null}
      </div>

      <WorkbenchTaskDock
        open={dockOpen}
        height={dock.size}
        onToggle={() => setDockOpen((value) => !value)}
        onResizePointerDown={dock.onPointerDown}
        onResizeKeyDown={dock.onKeyDown}
        resizing={dock.resizing}
      />

      {/* 窄屏左树抽屉 */}
      {!isDesktop && mobileTreeOpen ? (
        <div className="fixed inset-0 z-50">
          <button
            type="button"
            aria-label="关闭资源树"
            className="absolute inset-0 bg-foreground/30"
            onClick={() => setMobileTreeOpen(false)}
          />
          <div className="absolute inset-y-0 left-0 flex w-[300px] max-w-[85vw] flex-col border-r border-border bg-card shadow-popover">
            <div className="flex h-10 items-center justify-between border-b border-border px-3">
              <span className="text-xs font-medium">项目资源</span>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                aria-label="关闭资源树"
                onClick={() => setMobileTreeOpen(false)}
              >
                <PanelLeft className="h-3.5 w-3.5" />
              </Button>
            </div>
            <div className="min-h-0 flex-1">{tree}</div>
          </div>
        </div>
      ) : null}

      {/* 窄屏属性抽屉：与桌面端互斥渲染，避免重复 DOM */}
      {!isWide && inspectorOpen ? (
        <div className="fixed inset-0 z-50">
          <button
            type="button"
            aria-label="关闭属性面板"
            className="absolute inset-0 bg-foreground/30"
            onClick={() => setInspectorOpen(false)}
          />
          <div className="absolute inset-y-0 right-0 flex w-[320px] max-w-[85vw] flex-col border-l border-border bg-card shadow-popover">
            {inspector}
          </div>
        </div>
      ) : null}
    </div>
  )
}
