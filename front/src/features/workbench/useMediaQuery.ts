/**
 * 媒体查询 hook。
 *
 * 用途：左树 / 右栏在窄屏改为抽屉，而不是用 CSS 同时挂两份 DOM。
 * 同时挂两份会让树组件、滚动定位与键盘处理各跑一遍，长镜头列表时代价明显。
 */
import { useEffect, useState } from 'react'

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false
    return window.matchMedia(query).matches
  })

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return
    const media = window.matchMedia(query)
    const onChange = () => setMatches(media.matches)
    onChange()
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [query])

  return matches
}
