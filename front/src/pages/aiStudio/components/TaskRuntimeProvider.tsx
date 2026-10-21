import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { FilmService } from '../../../services/generated'
import { useTaskUiStore } from './taskUiStore'

const TASK_POLL_INTERVAL_MS = 4000
const TASK_RECENT_SECONDS = 15
const TASK_PAGE_SIZE = 50

type TaskRuntimeProviderProps = {
  children: ReactNode
}

export function TaskRuntimeProvider({ children }: TaskRuntimeProviderProps) {
  const setServerTasks = useTaskUiStore((state) => state.setServerTasks)

  useEffect(() => {
    let cancelled = false
    let timer: number | null = null

    const load = async () => {
      try {
        const res = await FilmService.listTasksApiV1FilmTasksGet({
          recentSeconds: TASK_RECENT_SECONDS,
          page: 1,
          pageSize: TASK_PAGE_SIZE,
        })
        if (cancelled) return
        setServerTasks(res.data?.items ?? [])
      } catch {
        if (!cancelled) {
          setServerTasks([])
        }
      } finally {
        if (!cancelled) {
          timer = window.setTimeout(() => {
            void load()
          }, TASK_POLL_INTERVAL_MS)
        }
      }
    }

    void load()
    return () => {
      cancelled = true
      if (timer) window.clearTimeout(timer)
    }
  }, [setServerTasks])

  return <>{children}</>
}
