import { useCallback, useEffect, useState } from 'react'

function isBrowserFullscreen(): boolean {
  return document.fullscreenElement != null
}

/* Same approach as the reader: prefer real browser fullscreen, fall back to a
   fixed-position takeover class when the Fullscreen API is unavailable. */
export function useStudyFullscreen(): { fullscreen: boolean; toggle: () => void } {
  const [fullscreen, setFullscreen] = useState(false)

  const toggle = useCallback(() => {
    if (fullscreen || isBrowserFullscreen()) {
      if (isBrowserFullscreen()) void document.exitFullscreen()
      else setFullscreen(false)
      return
    }
    document.documentElement.requestFullscreen().catch(() => setFullscreen(true))
  }, [fullscreen])

  useEffect(() => {
    const onChange = () => setFullscreen(isBrowserFullscreen())
    document.addEventListener('fullscreenchange', onChange)
    return () => document.removeEventListener('fullscreenchange', onChange)
  }, [])

  useEffect(() => {
    return () => {
      if (document.fullscreenElement) void document.exitFullscreen()
    }
  }, [])

  return { fullscreen, toggle }
}
