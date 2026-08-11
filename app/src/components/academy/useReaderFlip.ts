import { useCallback, useLayoutEffect, useRef, useState } from 'react'

// Duration must match the reader-turn-line keyframes in academy.css.
const FLIP_MS = 320

type FlipRequest = { dir: 1 | -1; fromSpread: number }

// Draw a lightweight moving page edge after the multi-column flow snaps to its
// next spread. It uses the same hairline as the fixed center divider, keeping
// the turn legible without introducing a second paper surface or book shadow.
export function useReaderFlip({
  viewportRef,
  reducedMotion,
}: {
  viewportRef: React.RefObject<HTMLDivElement | null>
  reducedMotion: boolean
}) {
  const [request, setRequest] = useState<FlipRequest | null>(null)
  const overlayRef = useRef<HTMLDivElement | null>(null)
  const timeoutRef = useRef<number | null>(null)

  const removeOverlay = useCallback(() => {
    if (timeoutRef.current != null) {
      window.clearTimeout(timeoutRef.current)
      timeoutRef.current = null
    }
    overlayRef.current?.remove()
    overlayRef.current = null
  }, [])

  const cancel = useCallback(() => {
    removeOverlay()
    setRequest(null)
  }, [removeOverlay])

  const flipTo = useCallback(
    (dir: 1 | -1, fromSpread: number) => {
      if (reducedMotion) return
      setRequest({ dir, fromSpread })
    },
    [reducedMotion],
  )

  const isFlipping = useCallback(() => overlayRef.current != null, [])

  useLayoutEffect(() => {
    if (!request) return
    const vp = viewportRef.current
    if (!vp) return

    const overlay = document.createElement('div')
    overlay.className = `reader__turn-line reader__turn-line--${request.dir === 1 ? 'next' : 'prev'}`
    overlay.setAttribute('aria-hidden', 'true')
    overlay.setAttribute('inert', '')
    vp.appendChild(overlay)
    overlayRef.current = overlay

    const finish = () => {
      removeOverlay()
      setRequest(null)
    }
    overlay.addEventListener('animationend', finish)
    // Safety net in case animationend never fires (e.g. the tab was hidden).
    timeoutRef.current = window.setTimeout(finish, FLIP_MS + 80)

    return () => removeOverlay()
  }, [request, viewportRef, removeOverlay])

  return { flipTo, cancel, isFlipping }
}
