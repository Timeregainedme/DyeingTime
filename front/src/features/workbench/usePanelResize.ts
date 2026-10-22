/**
 * 可拖拽面板尺寸。
 *
 * 为什么不引第三方 split-pane：
 *   - 需求只有三个方向（左树宽度、右栏宽度、底栏高度）；
 *   - 自实现能严格控制「最小/最大、方向反转、localStorage 持久化」，
 *     也避免为一次 P1 骨架引入新的运行时依赖。
 *
 * 交互约定：
 *   - 指针拖拽实时改尺寸；
 *   - 分隔条可聚焦，方向键每次调整 16px（键盘用户不必精准拖拽）；
 *   - 拖拽期间禁用文本选择与光标闪烁。
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import type { PointerEvent as ReactPointerEvent } from 'react'

export interface PanelResizeOptions {
  axis: 'x' | 'y'
  initial: number
  min: number
  max: number
  /** true 时「指针向左/上」为增大（右栏与底栏常用）。 */
  invert?: boolean
  storageKey?: string
  step?: number
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

function readStoredSize(storageKey: string | undefined, fallback: number, min: number, max: number) {
  if (!storageKey || typeof window === 'undefined') return clamp(fallback, min, max)
  try {
    const raw = window.localStorage.getItem(storageKey)
    if (!raw) return clamp(fallback, min, max)
    const parsed = Number(raw)
    if (!Number.isFinite(parsed)) return clamp(fallback, min, max)
    return clamp(parsed, min, max)
  } catch {
    return clamp(fallback, min, max)
  }
}

export function usePanelResize({
  axis,
  initial,
  min,
  max,
  invert = false,
  storageKey,
  step = 16,
}: PanelResizeOptions) {
  const [size, setSize] = useState(() => readStoredSize(storageKey, initial, min, max))
  const [resizing, setResizing] = useState(false)
  const dragRef = useRef<{ pointer: number; size: number } | null>(null)
  const cleanupRef = useRef<(() => void) | null>(null)

  /** 写入本地偏好；隐私模式失败不影响本次会话。 */
  useEffect(() => {
    if (!storageKey || typeof window === 'undefined') return
    try {
      window.localStorage.setItem(storageKey, String(Math.round(size)))
    } catch {
      // ignore
    }
  }, [size, storageKey])

  /** 组件卸载时结束拖拽，避免事件监听泄漏到其他页面。 */
  useEffect(() => () => cleanupRef.current?.(), [])

  const setBoundedSize = useCallback(
    (next: number) => setSize(clamp(next, min, max)),
    [min, max],
  )

  const stopDrag = useCallback(() => {
    cleanupRef.current?.()
    cleanupRef.current = null
    dragRef.current = null
    setResizing(false)
  }, [])

  const onPointerDown = useCallback(
    (event: ReactPointerEvent<HTMLElement>) => {
      // 只响应主键；右键菜单不触发拖拽。
      if (event.button !== 0) return
      event.preventDefault()
      dragRef.current = {
        pointer: axis === 'x' ? event.clientX : event.clientY,
        size,
      }
      setResizing(true)

      const onMove = (moveEvent: PointerEvent) => {
        const drag = dragRef.current
        if (!drag) return
        const current = axis === 'x' ? moveEvent.clientX : moveEvent.clientY
        const delta = (current - drag.pointer) * (invert ? -1 : 1)
        setSize(clamp(drag.size + delta, min, max))
      }
      const onUp = () => stopDrag()

      window.addEventListener('pointermove', onMove)
      window.addEventListener('pointerup', onUp)
      window.addEventListener('pointercancel', onUp)
      document.body.style.userSelect = 'none'
      document.body.style.cursor = axis === 'x' ? 'col-resize' : 'row-resize'

      cleanupRef.current = () => {
        window.removeEventListener('pointermove', onMove)
        window.removeEventListener('pointerup', onUp)
        window.removeEventListener('pointercancel', onUp)
        document.body.style.userSelect = ''
        document.body.style.cursor = ''
      }
    },
    [axis, invert, max, min, size, stopDrag],
  )

  /** 键盘调整：方向键按 step 变化；Home/End 回到最小/最大。 */
  const onKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLElement>) => {
      const decreaseKey = invert ? (axis === 'x' ? 'ArrowRight' : 'ArrowDown') : axis === 'x' ? 'ArrowLeft' : 'ArrowUp'
      const increaseKey = invert ? (axis === 'x' ? 'ArrowLeft' : 'ArrowUp') : axis === 'x' ? 'ArrowRight' : 'ArrowDown'
      if (event.key === decreaseKey) {
        event.preventDefault()
        setBoundedSize(size - step)
      } else if (event.key === increaseKey) {
        event.preventDefault()
        setBoundedSize(size + step)
      } else if (event.key === 'Home') {
        event.preventDefault()
        setBoundedSize(min)
      } else if (event.key === 'End') {
        event.preventDefault()
        setBoundedSize(max)
      }
    },
    [axis, invert, max, min, setBoundedSize, size, step],
  )

  return { size, resizing, setSize: setBoundedSize, onPointerDown, onKeyDown }
}
