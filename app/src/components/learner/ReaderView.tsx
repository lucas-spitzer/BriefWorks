import {
  AlertTriangle,
  Bookmark,
  BookmarkCheck,
  ChevronLeft,
  ChevronRight,
  Clock,
  Coffee,
  List,
  Maximize2,
  Minimize2,
  Pause,
  Play,
  RotateCcw,
  Volume2,
  X,
} from 'lucide-react'
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { useWorkspace } from '../../features/workspace/workspaceContext'
import { useWorkspaceData } from '../../features/workspace/workspaceDataContext'
import {
  MOCK_BLOCKS,
  buildBlocks,
  buildNarration,
  matchWikiTerms,
  type Block,
  type SpokenWord,
} from '../../lib/readerContent'
import type { LearnerPage, LearnerScope } from './types'
import { useIdleChrome } from './useIdleChrome'
import { useReaderFlip } from './useReaderFlip'
import {
  getNarrationAudioUrl,
  listAllSourceSegments,
  listSourceChapters,
  listSourceNarration,
  type NarrationSegment,
} from '../../lib/sourcesApi'

const SESSION_SECONDS = 25 * 60
// Gap between the two pages of a spread (and between overflow columns). Must
// match the value used in the translate math; we feed it to CSS as a var.
const GAP = 48
// Simulated narration cadence, used when no synthesized audio exists yet.
// Base words-per-minute at 1× playback speed.
const BASE_WPM = 165
// Above this multiplier we warn that comprehension drops off.
const SPEED_WARN_ABOVE = 1.5
const SPEEDS = [0.75, 1, 1.25, 1.5, 1.75, 2] as const

type TocEntry = { title: string; seq: number; sections: { title: string; seq: number }[] }

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}:${s < 10 ? '0' : ''}${s}`
}

function isEveningNow(): boolean {
  const h = new Date().getHours()
  return h >= 20 || h < 6
}

function isBrowserFullscreen(): boolean {
  return document.fullscreenElement != null
}

type LiveContent = {
  blocks: Block[]
  narration: Map<string, NarrationSegment>
  loading: boolean
  error: string | null
}

const NO_NARRATION = new Map<string, NarrationSegment>()

// One playable unit: a narrated paragraph. `base` is the block's first word's
// global index, so timing index i maps to spoken word `base + i`.
type NarrationTrack = {
  segmentId: string
  base: number
  count: number
  timings: { s: number; e: number }[]
}

// Deep links land here as /app/reader/:sourceId?seg=N where `seg` is the
// segment's stable sequence_index (see api build_reader_link) — never a page
// number, since pages reflow but segment order is immutable.
export function ReaderView({
  sourceId = null,
  seg = null,
  onOpen,
}: {
  sourceId?: string | null
  seg?: number | null
  onOpen?: (page: LearnerPage, scope: LearnerScope) => void
}) {
  const { activeWorkspace } = useWorkspace()
  const { sources, wikiEntries } = useWorkspaceData()
  const workspaceId = activeWorkspace?.id ?? null
  const activeSource = sources.find((source) => source.id === sourceId)
  const metadataTitle = activeSource?.source_metadata.title
  const ebookTitle =
    (typeof metadataTitle === 'string' && metadataTitle.trim()) ||
    activeSource?.filename.replace(/\.[^./\\]+$/, '') ||
    'Ebook'

  const [live, setLive] = useState<LiveContent>({
    blocks: [],
    narration: NO_NARRATION,
    loading: false,
    error: null,
  })

  // Fetch is keyed on (workspace, source); the sync setLive puts the viewport
  // into its loading state for the whole request, same pattern as the
  // measurement effect below. Narration is optional — a failure there never
  // blocks reading, it just falls back to the simulated cadence.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (!sourceId || !workspaceId) return
    let cancelled = false
    setLive({ blocks: [], narration: NO_NARRATION, loading: true, error: null })
    Promise.all([
      listAllSourceSegments(workspaceId, sourceId),
      listSourceChapters(workspaceId, sourceId),
      listSourceNarration(workspaceId, sourceId).catch(() => [] as NarrationSegment[]),
    ])
      .then(([segments, chapters, narrationRows]) => {
        if (cancelled) return
        const narration = new Map<string, NarrationSegment>()
        for (const row of narrationRows) {
          if (row.words.length > 0) narration.set(row.segment_id, row)
        }
        setLive({
          blocks: buildBlocks(segments, chapters),
          narration,
          loading: false,
          error: null,
        })
      })
      .catch((err: unknown) => {
        if (cancelled) return
        const message = err instanceof Error ? err.message : 'Failed to load the source.'
        setLive({ blocks: [], narration: NO_NARRATION, loading: false, error: message })
      })
    return () => {
      cancelled = true
    }
  }, [sourceId, workspaceId])
  /* eslint-enable react-hooks/set-state-in-effect */

  const isLive = sourceId != null
  const blocks = isLive ? live.blocks : MOCK_BLOCKS
  const { wordBlocks, total } = useMemo(() => buildNarration(blocks), [blocks])

  const [spread, setSpread] = useState(0)
  const [spreadCount, setSpreadCount] = useState(1)
  const [pageCount, setPageCount] = useState(1)
  const [colStride, setColStride] = useState(0)
  const [chapterCols, setChapterCols] = useState<{ col: number; title: string }[]>([])
  const [tocOpen, setTocOpen] = useState(false)
  const [viewportTick, setViewportTick] = useState(0)

  // Persistent bookmark: remembers the reader's spread across sessions, keyed
  // by source. `bookmarkSpread` mirrors the stored value for the button state.
  const bookmarkKey = sourceId ? `briefworks:reader-bookmark:${sourceId}` : null
  const [bookmarkSpread, setBookmarkSpread] = useState<number | null>(null)
  const bookmarkRestoredRef = useRef(false)

  // Narration / audio state. `spoken` is the global index of the word currently
  // being read (-1 = not started). Playback is a simulated cadence until the
  // narration stage's synthesized audio is wired in; speed scales the WPM.
  const [playing, setPlaying] = useState(false)
  const [spoken, setSpoken] = useState(-1)
  const [speed, setSpeed] = useState<(typeof SPEEDS)[number]>(1)

  const [remaining, setRemaining] = useState(SESSION_SECONDS)
  const [timerRunning, setTimerRunning] = useState(false)
  const [showBreak, setShowBreak] = useState(false)
  const chimeCtxRef = useRef<AudioContext | null>(null)
  const [fullscreen, setFullscreen] = useState(false)
  const evening = useMemo(() => isEveningNow(), [])

  // App chrome fades out while reading. Open overlays and a hovered control
  // pin it visible; the printed page furniture (running head, folios, spine)
  // never hides.
  const [hoverChrome, setHoverChrome] = useState(false)

  // Deep-link target. Applied once layout has been measured; highlighted
  // briefly so the reader can see what the link pointed at.
  const [targetSeq, setTargetSeq] = useState<number | null>(null)
  const pendingTargetRef = useRef<number | null>(seg)

  const viewportRef = useRef<HTMLDivElement | null>(null)
  const flowRef = useRef<HTMLDivElement | null>(null)
  const blockRefs = useRef<Map<number, HTMLElement>>(new Map())

  // Mirror of the (clamped) spread for event handlers, so rapid successive
  // turns in the same frame never read a stale value.
  const spreadRef = useRef(0)

  const [reducedMotion, setReducedMotion] = useState(
    () => window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  )
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const onChange = () => setReducedMotion(mq.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  const {
    flipTo,
    cancel: cancelFlip,
    isFlipping,
  } = useReaderFlip({ viewportRef, reducedMotion })

  // Reset reading position when switching sources or receiving a new target.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    pendingTargetRef.current = seg
    cancelFlip()
    spreadRef.current = 0
    setSpread(0)
    setPlaying(false)
    setSpoken(-1)
    setTargetSeq(null)
    bookmarkRestoredRef.current = false
  }, [sourceId, seg, cancelFlip])
  /* eslint-enable react-hooks/set-state-in-effect */

  // Load the stored bookmark for the current source (button-state mirror).
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (!bookmarkKey) {
      setBookmarkSpread(null)
      return
    }
    const raw = window.localStorage.getItem(bookmarkKey)
    const val = raw != null ? Number(raw) : NaN
    setBookmarkSpread(Number.isFinite(val) ? val : null)
  }, [bookmarkKey])
  /* eslint-enable react-hooks/set-state-in-effect */

  // --- Wiki term links ------------------------------------------------------
  // Match canonical wiki entry labels/aliases against the word stream; matched
  // words become tappable links that open a definition popover.
  const termByWord = useMemo(
    () => matchWikiTerms(wordBlocks, wikiEntries),
    [wordBlocks, wikiEntries],
  )
  const entryById = useMemo(
    () => new Map(wikiEntries.map((entry) => [entry.id, entry])),
    [wikiEntries],
  )
  const [termPop, setTermPop] = useState<{ entryId: string; left: number; top: number } | null>(
    null,
  )

  const onTermClick = useCallback((entryId: string, target: HTMLElement) => {
    const vp = viewportRef.current
    if (!vp) return
    const vpRect = vp.getBoundingClientRect()
    const rect = target.getBoundingClientRect()
    const width = 320
    const left = Math.max(0, Math.min(rect.left - vpRect.left, vp.clientWidth - width))
    const top = Math.min(rect.bottom - vpRect.top + 8, vp.clientHeight - 40)
    setTermPop({ entryId, left, top })
  }, [])

  const termEntry = termPop ? entryById.get(termPop.entryId) : undefined

  const { visible: chromeVisible, bind: idleBind } = useIdleChrome({
    pinned: tocOpen || termPop != null || showBreak || hoverChrome,
  })
  const chromeHover = {
    onMouseEnter: () => setHoverChrome(true),
    onMouseLeave: () => setHoverChrome(false),
  }

  const toc = useMemo<TocEntry[]>(() => {
    const entries: TocEntry[] = []
    for (const b of blocks) {
      if (b.kind === 'heading' && b.level === 1) {
        entries.push({ title: b.text, seq: b.seq, sections: [] })
      } else if (b.kind === 'heading' && b.level === 2 && entries.length) {
        entries[entries.length - 1].sections.push({ title: b.text, seq: b.seq })
      }
    }
    return entries
  }, [blocks])

  // --- Pagination measurement ---------------------------------------------
  // The browser lays the stream into fixed-height columns (two visible per
  // spread); we only measure how many columns/spreads exist and where chapter
  // starts land, for nav + the running header. Recomputed on resize.
  /* eslint-disable react-hooks/set-state-in-effect */
  useLayoutEffect(() => {
    if (blocks.length === 0) {
      setSpreadCount(1)
      setPageCount(1)
      setColStride(0)
      setChapterCols([])
      return
    }
    const vp = viewportRef.current
    const flow = flowRef.current
    if (!vp || !flow) return
    const width = vp.clientWidth
    if (width <= 0) return

    // column-width only accepts lengths (percentage calc() is invalid CSS and
    // gets dropped), so the two-page column width must be set in pixels here,
    // before the column extent below is measured.
    flow.style.columnWidth = `${(width - GAP) / 2}px`

    const stride = (width + GAP) / 2 // one column + one gap
    const lastEl = blockRefs.current.get(blocks[blocks.length - 1].seq)
    const lastRight = lastEl ? lastEl.offsetLeft + lastEl.offsetWidth : 0
    const extent = Math.max(flow.scrollWidth, lastRight)
    const totalColumns = Math.max(1, Math.round((extent + GAP) / stride))
    const spreads = Math.max(1, Math.ceil(totalColumns / 2))

    const cols: { col: number; title: string }[] = []
    for (const b of blocks) {
      if (!b.isChapterStart) continue
      const el = blockRefs.current.get(b.seq)
      if (!el) continue
      cols.push({ col: Math.round(el.offsetLeft / stride), title: b.chapterTitle })
    }

    setColStride(stride)
    setPageCount(totalColumns)
    setSpreadCount(spreads)
    setChapterCols(cols)
  }, [blocks, viewportTick])
  /* eslint-enable react-hooks/set-state-in-effect */

  useEffect(() => {
    const vp = viewportRef.current
    if (!vp) return
    const ro = new ResizeObserver(() => {
      // Reflow invalidates the flip overlay's frozen page clones.
      cancelFlip()
      setViewportTick((t) => t + 1)
    })
    ro.observe(vp)
    return () => ro.disconnect()
  }, [cancelFlip])

  const lastSpread = Math.max(spreadCount - 1, 0)
  const safeSpread = Math.min(spread, lastSpread)

  useEffect(() => {
    spreadRef.current = safeSpread
  })

  // Every spread change funnels through here; `mode` picks the motion.
  // 'flip' is only honest for single-page turns — jumps use 'fade' (a short
  // opacity dip) or 'none' (instant snap). Reduced motion always snaps.
  const goToSpread = useCallback(
    (target: number, mode: 'flip' | 'fade' | 'none') => {
      const clamped = Math.min(Math.max(target, 0), lastSpread)
      const current = spreadRef.current
      if (clamped === current) return
      spreadRef.current = clamped
      setSpread(clamped)
      if (reducedMotion || mode === 'none') {
        cancelFlip()
        return
      }
      if (mode === 'flip') {
        flipTo(clamped > current ? 1 : -1, current)
      } else {
        cancelFlip()
        viewportRef.current?.animate({ opacity: [0.25, 1] }, { duration: 180, easing: 'ease-out' })
      }
    },
    [lastSpread, reducedMotion, cancelFlip, flipTo],
  )

  // Land on the deep-link target once columns have been measured.
  useEffect(() => {
    const target = pendingTargetRef.current
    if (target == null || colStride <= 0 || blocks.length === 0) return
    const el = blockRefs.current.get(target)
    pendingTargetRef.current = null
    if (!el) return
    const col = Math.round(el.offsetLeft / colStride)
    goToSpread(Math.floor(col / 2), 'none')
    setTargetSeq(target)
  }, [colStride, blocks, goToSpread])

  // Restore the saved bookmark once columns are measured. A deep-link target
  // (opening to a specific segment) always takes precedence. Reads storage
  // directly to avoid racing the async bookmark-state load.
  useEffect(() => {
    if (bookmarkRestoredRef.current) return
    if (colStride <= 0 || blocks.length === 0) return
    bookmarkRestoredRef.current = true
    if (seg != null || !bookmarkKey) return
    const raw = window.localStorage.getItem(bookmarkKey)
    const val = raw != null ? Number(raw) : NaN
    if (Number.isFinite(val)) goToSpread(val, 'none')
  }, [colStride, blocks, seg, bookmarkKey, goToSpread])

  useEffect(() => {
    if (targetSeq == null) return
    const timeout = window.setTimeout(() => setTargetSeq(null), 4000)
    return () => window.clearTimeout(timeout)
  }, [targetSeq])

  // --- Navigation ---------------------------------------------------------
  const turn = useCallback(
    (delta: 1 | -1) => {
      setTermPop(null)
      goToSpread(spreadRef.current + delta, 'flip')
    },
    [goToSpread],
  )

  const jumpToSeq = useCallback(
    (target: number) => {
      const el = blockRefs.current.get(target)
      if (el && colStride > 0) {
        const col = Math.round(el.offsetLeft / colStride)
        goToSpread(Math.floor(col / 2), 'fade')
      }
      setTocOpen(false)
      setTermPop(null)
    },
    [colStride, goToSpread],
  )

  // Toggle a bookmark at the current spread. Saving again on the bookmarked
  // page removes it; otherwise the bookmark moves to the current page.
  const toggleBookmark = useCallback(() => {
    if (!bookmarkKey) return
    setBookmarkSpread((prev) => {
      if (prev === safeSpread) {
        window.localStorage.removeItem(bookmarkKey)
        return null
      }
      window.localStorage.setItem(bookmarkKey, String(safeSpread))
      return safeSpread
    })
  }, [bookmarkKey, safeSpread])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA') return
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return
      // Drop focus off any lingering chrome control (e.g. a footer turn button
      // clicked earlier). Otherwise pressing an arrow flips the page AND enters
      // keyboard modality, so that focused button matches :focus-visible and
      // pins the chrome back open. Blurring keeps an idle reader's chrome hidden.
      const active = document.activeElement as HTMLElement | null
      if (active && active !== document.body) active.blur()
      if (e.key === 'ArrowRight') turn(1)
      else turn(-1)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [turn])

  // --- Narration playback -------------------------------------------------
  // Two engines share the `spoken` index. When synthesized audio exists
  // (narration_segments rows), an HTMLAudioElement plays each narrated
  // paragraph and word timings drive the highlight. Otherwise a simulated
  // WPM cadence walks the words (reader-recommendations §6 fallback).
  const tracks = useMemo<NarrationTrack[]>(() => {
    if (live.narration.size === 0) return []
    const out: NarrationTrack[] = []
    for (const wb of wordBlocks) {
      if (wb.words.length === 0) continue
      const row = live.narration.get(wb.block.id)
      if (!row) continue
      out.push({
        segmentId: wb.block.id,
        base: wb.words[0].global,
        count: wb.words.length,
        timings: row.words.map((w) => ({ s: w.s, e: w.e })),
      })
    }
    return out
  }, [live.narration, wordBlocks])
  const hasAudio = isLive && tracks.length > 0

  const spokenRef = useRef(spoken)
  useEffect(() => {
    spokenRef.current = spoken
  }, [spoken])
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const speedRef = useRef<number>(speed)
  useEffect(() => {
    speedRef.current = speed
  }, [speed])
  const urlCacheRef = useRef(new Map<string, string>())

  useEffect(() => {
    urlCacheRef.current = new Map()
  }, [sourceId])

  // Simulated cadence (no synthesized audio).
  useEffect(() => {
    if (!playing || hasAudio) return
    const msPerWord = 60000 / (BASE_WPM * speed)
    const tick = window.setInterval(() => {
      setSpoken((i) => {
        if (i + 1 >= total) {
          setPlaying(false)
          return total - 1
        }
        return i + 1
      })
    }, msPerWord)
    return () => window.clearInterval(tick)
  }, [playing, speed, total, hasAudio])

  // Synthesized audio playback. The effect owns the audio element for the
  // whole play session; pausing or switching sources tears it down.
  useEffect(() => {
    if (!playing || !hasAudio || !workspaceId || !sourceId) return

    let disposed = false
    const audio = new Audio()
    audio.playbackRate = speedRef.current
    audioRef.current = audio
    let trackIndex = 0

    const fetchUrl = async (segmentId: string): Promise<string> => {
      const cached = urlCacheRef.current.get(segmentId)
      if (cached) return cached
      const res = await getNarrationAudioUrl(workspaceId, sourceId, segmentId)
      urlCacheRef.current.set(segmentId, res.audio_url)
      return res.audio_url
    }

    const playIndex = async (index: number) => {
      const track = tracks[index]
      if (!track || disposed) {
        if (!disposed) setPlaying(false)
        return
      }
      trackIndex = index
      try {
        const url = await fetchUrl(track.segmentId)
        if (disposed) return
        audio.src = url
        audio.playbackRate = speedRef.current
        setSpoken(track.base)
        await audio.play()
        if (tracks[index + 1]) void fetchUrl(tracks[index + 1].segmentId).catch(() => undefined)
      } catch {
        if (!disposed) setPlaying(false)
      }
    }

    audio.ontimeupdate = () => {
      const track = tracks[trackIndex]
      if (!track) return
      const t = audio.currentTime
      let idx = 0
      for (let i = 0; i < track.timings.length; i += 1) {
        if (track.timings[i].s <= t) idx = i
        else break
      }
      setSpoken(track.base + Math.min(idx, track.count - 1))
    }
    audio.onended = () => {
      void playIndex(trackIndex + 1)
    }

    // Resume from the track holding the current word; otherwise the next
    // narrated track after it; from the top when finished or not started.
    const resumeAt = spokenRef.current
    let start = tracks.findIndex((tr) => resumeAt >= tr.base && resumeAt < tr.base + tr.count)
    if (start < 0) start = tracks.findIndex((tr) => tr.base > resumeAt)
    if (start < 0) start = 0
    void playIndex(start)

    return () => {
      disposed = true
      audio.pause()
      audio.removeAttribute('src')
      audioRef.current = null
    }
  }, [playing, hasAudio, tracks, workspaceId, sourceId])

  // Speed changes apply to the live audio element without restarting it.
  useEffect(() => {
    if (audioRef.current) audioRef.current.playbackRate = speed
  }, [speed])

  // Keep the spoken word on screen: when narration crosses into a column beyond
  // the current spread, turn the page to follow it.
  useEffect(() => {
    if (!playing || spoken < 0 || colStride <= 0) return
    let seq = -1
    for (const wb of wordBlocks) {
      const hit = wb.words.find((w) => w.global === spoken)
      if (hit) {
        seq = hit.seq
        break
      }
    }
    if (seq < 0) return
    const el = blockRefs.current.get(seq)
    if (!el) return
    const targetSpread = Math.floor(Math.round(el.offsetLeft / colStride) / 2)
    if (targetSpread > spreadRef.current) {
      // Turn the page like the user would, but never cut short a flip the
      // user started, and don't fake a flip across a multi-spread jump.
      const single = targetSpread === spreadRef.current + 1
      goToSpread(targetSpread, single && !isFlipping() ? 'flip' : 'none')
    }
  }, [spoken, playing, colStride, wordBlocks, goToSpread, isFlipping])

  const togglePlay = useCallback(() => {
    setPlaying((p) => {
      const next = !p
      if (next && spoken + 1 >= total) setSpoken(-1) // restart from top at the end
      return next
    })
  }, [spoken, total])

  const restartNarration = useCallback(() => {
    setPlaying(false)
    setSpoken(-1)
  }, [])

  // The active sentence, used to draw the soft "reading band" ahead of the word.
  const speakingSentence = useMemo(() => {
    if (spoken < 0) return -1
    for (const wb of wordBlocks) {
      const hit = wb.words.find((w) => w.global === spoken)
      if (hit) return hit.sentence
    }
    return -1
  }, [spoken, wordBlocks])

  // --- Fullscreen ---------------------------------------------------------
  const toggleFullscreen = useCallback(async () => {
    if (fullscreen || isBrowserFullscreen()) {
      if (isBrowserFullscreen()) await document.exitFullscreen()
      else setFullscreen(false)
      return
    }
    try {
      await document.documentElement.requestFullscreen()
    } catch {
      setFullscreen(true)
    }
  }, [fullscreen])

  useEffect(() => {
    const onFullscreenChange = () => setFullscreen(isBrowserFullscreen())
    document.addEventListener('fullscreenchange', onFullscreenChange)
    return () => document.removeEventListener('fullscreenchange', onFullscreenChange)
  }, [])

  useEffect(() => {
    return () => {
      if (document.fullscreenElement) void document.exitFullscreen()
    }
  }, [])

  // A soft two-note chime when the session timer completes. Uses Web Audio so
  // there's no asset to ship; a gentle gain envelope keeps it pleasant.
  const playChime = useCallback(() => {
    try {
      const Ctx =
        window.AudioContext ??
        (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
      if (!Ctx) return
      const ctx = chimeCtxRef.current ?? new Ctx()
      chimeCtxRef.current = ctx
      if (ctx.state === 'suspended') void ctx.resume()
      const now = ctx.currentTime
      // Two ascending notes (E5 → A5), each a short sine with a soft fade.
      ;[
        { freq: 659.25, at: 0 },
        { freq: 880.0, at: 0.18 },
      ].forEach(({ freq, at }) => {
        const osc = ctx.createOscillator()
        const gain = ctx.createGain()
        osc.type = 'sine'
        osc.frequency.value = freq
        const start = now + at
        gain.gain.setValueAtTime(0.0001, start)
        gain.gain.exponentialRampToValueAtTime(0.12, start + 0.03)
        gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.9)
        osc.connect(gain).connect(ctx.destination)
        osc.start(start)
        osc.stop(start + 0.95)
      })
    } catch {
      // Audio is a nicety; ignore environments that block it.
    }
  }, [])

  // --- Session timer ------------------------------------------------------
  useEffect(() => {
    if (showBreak || !timerRunning) return
    const tick = window.setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) {
          playChime()
          setShowBreak(true)
          return 0
        }
        return r - 1
      })
    }, 1000)
    return () => window.clearInterval(tick)
  }, [showBreak, timerRunning, playChime])

  const dismissBreak = (reset: boolean) => {
    setShowBreak(false)
    if (reset) setRemaining(SESSION_SECONDS)
  }

  // --- Render -------------------------------------------------------------
  let runningChapter = ''
  const leftCol = safeSpread * 2
  for (const c of chapterCols) {
    if (c.col <= leftCol) runningChapter = c.title
    else break
  }

  const leftNum = safeSpread * 2 + 1
  const rightNum = Math.min(safeSpread * 2 + 2, pageCount)

  const emptyState = isLive && !live.loading && !live.error && blocks.length === 0
  const showBook = !(isLive && (live.loading || live.error != null)) && !emptyState
  const progressPct = pageCount > 0 ? Math.round((rightNum / pageCount) * 100) : 0

  return (
    <section
      className={`reader${evening ? ' reader--warm' : ''}${fullscreen ? ' reader--fullscreen' : ''}${chromeVisible ? '' : ' reader--chrome-hidden'}`}
      {...idleBind}
    >
      <div className="reader__topline" {...chromeHover}>
        <div className="reader__topline-left">
          <button
            type="button"
            className="reader__timer-btn"
            onClick={() => setTocOpen((o) => !o)}
            aria-expanded={tocOpen}
            aria-label="Table of contents"
            title="Contents"
          >
            <List size={14} />
          </button>
          <button
            type="button"
            className={`reader__timer-btn${
              bookmarkSpread === safeSpread ? ' is-active' : ''
            }`}
            onClick={toggleBookmark}
            disabled={!bookmarkKey}
            aria-pressed={bookmarkSpread === safeSpread}
            aria-label={
              bookmarkSpread === safeSpread ? 'Remove bookmark' : 'Bookmark this page'
            }
            title={bookmarkSpread === safeSpread ? 'Remove bookmark' : 'Bookmark this page'}
          >
            {bookmarkSpread === safeSpread ? (
              <BookmarkCheck size={14} />
            ) : (
              <Bookmark size={14} />
            )}
          </button>
        </div>
        <div className="reader__session">
          <button
            type="button"
            className="reader__timer-btn"
            onClick={() => void toggleFullscreen()}
            aria-pressed={fullscreen}
            aria-label={fullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
          >
            {fullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>
          <span className="reader__timer" aria-label="Session time remaining">
            <Clock size={14} aria-hidden="true" />
            {formatTime(remaining)}
          </span>
          <button
            type="button"
            className="reader__timer-btn"
            onClick={() => setTimerRunning((r) => !r)}
            aria-label={timerRunning ? 'Pause session timer' : 'Start session timer'}
          >
            {timerRunning ? <Pause size={14} /> : <Play size={14} />}
          </button>
          <button
            type="button"
            className="reader__timer-btn"
            onClick={() => {
              setRemaining(SESSION_SECONDS)
              setTimerRunning(false)
            }}
            aria-label="Reset session timer"
          >
            <RotateCcw size={14} />
          </button>
        </div>
      </div>

      <div className="reader__stage">
        <div
          className="reader__book"
          style={{ '--reader-gap': `${GAP}px` } as React.CSSProperties}
        >
        {showBook && (
          <div className="reader__running-head" aria-hidden="true">
            {runningChapter}
          </div>
        )}
        <div className="reader__viewport" ref={viewportRef}>
          {live.loading && isLive ? (
            <div className="reader__empty reader__opening" role="status">
              <div className="reader__opening-book" aria-hidden="true">
                <span className="reader__opening-cover" />
                <span className="reader__opening-page reader__opening-page--left" />
                <span className="reader__opening-page reader__opening-page--right" />
                <span className="reader__opening-leaf reader__opening-leaf--one" />
                <span className="reader__opening-leaf reader__opening-leaf--two" />
                <span className="reader__opening-spine" />
              </div>
              <p className="reader__empty-title reader__opening-title">{ebookTitle}</p>
              <div className="reader__opening-dots" aria-hidden="true">
                <span />
                <span />
                <span />
              </div>
            </div>
          ) : live.error && isLive ? (
            <div className="reader__empty" role="alert">
              <p className="reader__empty-title">Couldn't open this source.</p>
              <p className="reader__empty-copy">{live.error}</p>
            </div>
          ) : emptyState ? (
            <div className="reader__empty">
              <p className="reader__empty-title">Nothing to read yet.</p>
              <p className="reader__empty-copy">
                This source hasn't been structured into readable text. Run the production
                pipeline on it from the console, then come back.
              </p>
            </div>
          ) : (
            <div
              className="reader__flow"
              ref={flowRef}
              style={
                {
                  '--reader-spread': safeSpread,
                  '--reader-gap': `${GAP}px`,
                } as React.CSSProperties
              }
            >
              {wordBlocks.map(({ block, words }, i) => (
                <ReaderBlock
                  key={block.id}
                  block={block}
                  words={words}
                  spoken={spoken}
                  speakingSentence={speakingSentence}
                  chapterStart={block.isChapterStart && i > 0}
                  isTarget={targetSeq != null && block.seq === targetSeq}
                  termByWord={termByWord}
                  onTermClick={onTermClick}
                  registerRef={(el) => {
                    if (el) blockRefs.current.set(block.seq, el)
                    else blockRefs.current.delete(block.seq)
                  }}
                />
              ))}
            </div>
          )}

          {showBook && <div className="reader__spine" aria-hidden="true" />}

          {termPop && termEntry && (
            <>
              <div
                className="reader__term-backdrop"
                onClick={() => setTermPop(null)}
                aria-hidden="true"
              />
              <aside
                className="reader__term-pop"
                style={{ left: termPop.left, top: termPop.top }}
                role="dialog"
                aria-label={`Definition of ${termEntry.preferred_label}`}
              >
                <div className="reader__term-head">
                  <span className="reader__term-label">{termEntry.preferred_label}</span>
                  <button
                    type="button"
                    className="reader__toc-close"
                    onClick={() => setTermPop(null)}
                    aria-label="Close definition"
                  >
                    <X size={14} />
                  </button>
                </div>
                <p className="reader__term-definition">{termEntry.definition}</p>
                {onOpen && sourceId && (
                  <button
                    type="button"
                    className="reader__term-discuss"
                    onClick={() => {
                      setTermPop(null)
                      onOpen('discussions', { sourceId, targetId: null })
                    }}
                  >
                    Discuss with assistant
                  </button>
                )}
              </aside>
            </>
          )}

          {tocOpen && (
            <>
              <div
                className="reader__toc-backdrop"
                onClick={() => setTocOpen(false)}
                aria-hidden="true"
              />
              <nav className="reader__toc" aria-label="Table of contents">
                <div className="reader__toc-head">
                  <span>Contents</span>
                  <button
                    type="button"
                    className="reader__toc-close"
                    onClick={() => setTocOpen(false)}
                    aria-label="Close contents"
                  >
                    <X size={14} />
                  </button>
                </div>
                {toc.length === 0 && <p className="reader__toc-empty">No chapters.</p>}
                {toc.map((ch) => (
                  <div key={ch.seq} className="reader__toc-chapter-group">
                    <button
                      type="button"
                      className="reader__toc-chapter"
                      onClick={() => jumpToSeq(ch.seq)}
                    >
                      {ch.title}
                    </button>
                    {ch.sections.map((s) => (
                      <button
                        key={s.seq}
                        type="button"
                        className="reader__toc-section"
                        onClick={() => jumpToSeq(s.seq)}
                      >
                        {s.title}
                      </button>
                    ))}
                  </div>
                ))}
              </nav>
            </>
          )}
        </div>
        {showBook && (
          <>
            <span className="reader__folio reader__folio--left" aria-hidden="true">
              {leftNum}
            </span>
            {rightNum > leftNum && (
              <span className="reader__folio reader__folio--right" aria-hidden="true">
                {rightNum}
              </span>
            )}
          </>
        )}
        </div>
        <button
          type="button"
          className="reader__zone reader__zone--prev"
          onClick={() => turn(-1)}
          disabled={safeSpread === 0}
          aria-label="Previous page"
        >
          <ChevronLeft size={22} aria-hidden="true" />
        </button>
        <button
          type="button"
          className="reader__zone reader__zone--next"
          onClick={() => turn(1)}
          disabled={safeSpread >= lastSpread}
          aria-label="Next page"
        >
          <ChevronRight size={22} aria-hidden="true" />
        </button>
      </div>

      <div className="reader__footer" {...chromeHover}>
        <div className="reader__player">
          <button
            type="button"
            className="reader__turn"
            onClick={togglePlay}
            aria-label={playing ? 'Pause narration' : 'Play narration'}
          >
            {playing ? <Pause size={20} /> : <Play size={20} />}
          </button>
          <button
            type="button"
            className="reader__timer-btn"
            onClick={restartNarration}
            aria-label="Restart narration"
            title="Restart narration"
          >
            <RotateCcw size={14} />
          </button>
          <span className="reader__timer" aria-label="Narration">
            <Volume2 size={14} aria-hidden="true" />
            {spoken < 0
              ? hasAudio
                ? 'Audio narration'
                : 'Narration'
              : `${Math.min(spoken + 1, total)} / ${total} words`}
          </span>
          <label className="reader__speed">
            <span className="reader__speed-label">Speed</span>
            <select
              className="reader__speed-select"
              value={speed}
              onChange={(e) => setSpeed(Number(e.target.value) as (typeof SPEEDS)[number])}
              aria-label="Narration speed"
            >
              {SPEEDS.map((s) => (
                <option key={s} value={s}>
                  {s}×
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="reader__pager">
          <button
            type="button"
            className="reader__turn"
            onClick={() => turn(-1)}
            disabled={safeSpread === 0}
            aria-label="Previous pages"
          >
            <ChevronLeft size={22} />
          </button>
          <span className="reader__pageinfo" aria-label="Progress through the book">
            {pageCount > 0 ? `${progressPct}% · ${pageCount} pages` : 'No content'}
          </span>
          <button
            type="button"
            className="reader__turn"
            onClick={() => turn(1)}
            disabled={safeSpread >= lastSpread}
            aria-label="Next pages"
          >
            <ChevronRight size={22} />
          </button>
        </div>
        {speed > SPEED_WARN_ABOVE && (
          <p className="reader__speed-warn" role="status">
            <AlertTriangle size={14} aria-hidden="true" />
            High speeds boost coverage but reduce retention — slow down for material you need to
            remember.
          </p>
        )}
      </div>

      {showBreak && (
        <div className="reader__break" role="dialog" aria-label="Break reminder">
          <div className="reader__break-card">
            <Coffee size={28} aria-hidden="true" />
            <h3 className="reader__break-title">Nice work.</h3>
            <p className="reader__break-copy">
              Take a 5-minute break away from the screen. Stepping away helps your memory
              consolidate what you just read.
            </p>
            <div className="reader__break-actions">
              <button
                type="button"
                className="reader__break-btn reader__break-btn--primary"
                onClick={() => dismissBreak(false)}
              >
                Start break
              </button>
              <button type="button" className="reader__break-btn" onClick={() => dismissBreak(true)}>
                Keep reading
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

function ReaderBlock({
  block,
  words,
  spoken,
  speakingSentence,
  chapterStart,
  isTarget,
  termByWord,
  onTermClick,
  registerRef,
}: {
  block: Block
  words: SpokenWord[]
  spoken: number
  speakingSentence: number
  chapterStart: boolean
  isTarget: boolean
  termByWord: Map<number, string>
  onTermClick: (entryId: string, target: HTMLElement) => void
  registerRef: (el: HTMLElement | null) => void
}) {
  const cls = `${chapterStart ? ' reader__chapter-start' : ''}${isTarget ? ' is-target' : ''}`
  if (block.kind === 'heading') {
    if (block.level === 1)
      return (
        <h1 ref={registerRef} className={`reader__h1${cls}`} data-segment-id={block.id}>
          {block.text}
        </h1>
      )
    return (
      <h2 ref={registerRef} className={`reader__h2${cls}`} data-segment-id={block.id}>
        {block.text}
      </h2>
    )
  }
  const variantCls = block.variant ? ` reader__para--${block.variant}` : ''
  return (
    <p ref={registerRef} className={`reader__para${variantCls}${cls}`} data-segment-id={block.id}>
      {words.map((w) => {
        const state =
          w.global === spoken
            ? ' is-speaking'
            : w.global < spoken
              ? ' is-read'
              : w.sentence === speakingSentence
                ? ' is-band'
                : ''
        const style = `${w.em ? ' is-em' : ''}${w.strong ? ' is-strong' : ''}`
        const termId = termByWord.get(w.global)
        if (termId) {
          return (
            <span key={w.global} className={`reader__word${state}${style}`}>
              <button
                type="button"
                className="reader__term"
                onClick={(e) => onTermClick(termId, e.currentTarget)}
              >
                {w.text}
              </button>{' '}
            </span>
          )
        }
        return (
          <span key={w.global} className={`reader__word${state}${style}`}>
            {w.text}{' '}
          </span>
        )
      })}
    </p>
  )
}
