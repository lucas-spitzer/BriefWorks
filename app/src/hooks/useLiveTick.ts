import { useEffect, useState } from 'react'

/** Re-renders every second while enabled so live durations can tick smoothly. */
export function useLiveTick(enabled: boolean): void {
  const [, setTick] = useState(0)

  useEffect(() => {
    if (!enabled) {
      return
    }

    const intervalId = window.setInterval(() => {
      setTick((tick) => tick + 1)
    }, 1000)

    return () => window.clearInterval(intervalId)
  }, [enabled])
}
