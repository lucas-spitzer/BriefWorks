import { useCallback, useEffect, useRef, useState } from 'react'

const IDLE_MS = 3000
const MOVE_THROTTLE_MS = 100

// Fades the reader's app chrome (topline, player, footer) after a few seconds
// of inactivity so an idle reader is just the book. Any pointer movement,
// press, key, or focus within the reader reveals it again. `pinned` forces
// visibility (open overlays, a hovered control) and re-arms the idle window
// when it releases.
//
// Hiding is opacity-only (see academy.css) so the layout — and therefore the
// pagination — never reflows.
export function useIdleChrome({ pinned }: { pinned: boolean }) {
  const [idle, setIdle] = useState(false)
  const timeoutRef = useRef<number | null>(null)
  const lastMoveRef = useRef(0)

  const reveal = useCallback(() => {
    setIdle(false)
    if (timeoutRef.current != null) window.clearTimeout(timeoutRef.current)
    timeoutRef.current = window.setTimeout(() => setIdle(true), IDLE_MS)
  }, [])

  // Fresh idle window on mount and whenever the pin state changes. This only
  // re-arms the timer (never sets state synchronously); every real unpin is
  // accompanied by an interaction that reveals via the handlers below.
  useEffect(() => {
    if (timeoutRef.current != null) window.clearTimeout(timeoutRef.current)
    timeoutRef.current = window.setTimeout(() => setIdle(true), IDLE_MS)
    return () => {
      if (timeoutRef.current != null) window.clearTimeout(timeoutRef.current)
    }
  }, [pinned])

  // Keys reveal the chrome so keyboard users are never driving invisible
  // controls — except the arrow keys used to turn pages, which should let an
  // idle reader keep paging without the chrome flashing back in.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') return
      reveal()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [reveal])

  const onPointerMove = useCallback(() => {
    const now = Date.now()
    if (now - lastMoveRef.current < MOVE_THROTTLE_MS) return
    lastMoveRef.current = now
    reveal()
  }, [reveal])

  return {
    visible: pinned || !idle,
    bind: { onPointerMove, onPointerDown: reveal, onFocus: reveal },
  }
}
