import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import type { Citation } from '../../lib/assistantApi'

/* Lightweight renderer for assistant chat text. Supports the emphasis subset
   the tutor actually emits (**bold**, *italic*) plus inline [n] citation
   markers resolved against the message's citations array. Optionally reveals
   the text with a typewriter animation for freshly received replies. */

type TextToken = {
  kind: 'text'
  text: string
  bold: boolean
  italic: boolean
}
type CitationToken = { kind: 'cite'; citationNumber: number }
type RichTextToken = TextToken | CitationToken

const INLINE_PATTERN = /(\*\*[^*]+\*\*|\*[^*\n]+\*|\[\d+\])/g

function tokenize(text: string, bold = false, italic = false): RichTextToken[] {
  const tokens: RichTextToken[] = []
  let lastIndex = 0
  for (const match of text.matchAll(INLINE_PATTERN)) {
    const raw = match[0]
    const start = match.index ?? 0
    if (start > lastIndex) {
      tokens.push({ kind: 'text', text: text.slice(lastIndex, start), bold, italic })
    }
    if (raw.startsWith('**')) {
      tokens.push(...tokenize(raw.slice(2, -2), true, italic))
    } else if (raw.startsWith('*')) {
      tokens.push(...tokenize(raw.slice(1, -1), bold, true))
    } else {
      tokens.push({ kind: 'cite', citationNumber: Number(raw.slice(1, -1)) })
    }
    lastIndex = start + raw.length
  }
  if (lastIndex < text.length) {
    tokens.push({ kind: 'text', text: text.slice(lastIndex), bold, italic })
  }
  return tokens
}

function tokenLength(token: RichTextToken): number {
  return token.kind === 'text' ? token.text.length : 1
}

/** Truncate the token list to a character budget (citations count as one). */
function sliceTokens(tokens: RichTextToken[], budget: number): RichTextToken[] {
  const visible: RichTextToken[] = []
  let used = 0
  for (const token of tokens) {
    const length = tokenLength(token)
    if (used + length <= budget) {
      visible.push(token)
      used += length
      continue
    }
    if (token.kind === 'text' && budget > used) {
      visible.push({ ...token, text: token.text.slice(0, budget - used) })
    }
    break
  }
  return visible
}

const REVEAL_CHARS_PER_TICK = 3
const REVEAL_TICK_MS = 16

export function ChatRichText({
  text,
  citations = [],
  animate = false,
  onProgress,
  onDone,
}: {
  text: string
  citations?: Citation[]
  animate?: boolean
  /** Called on each reveal tick, e.g. to keep the log scrolled to bottom. */
  onProgress?: () => void
  onDone?: () => void
}) {
  const tokens = useMemo(() => tokenize(text), [text])
  const totalChars = useMemo(
    () => tokens.reduce((sum, token) => sum + tokenLength(token), 0),
    [tokens],
  )

  const reducedMotion =
    typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  const shouldAnimate = animate && !reducedMotion

  const [revealedChars, setRevealedChars] = useState(shouldAnimate ? 0 : totalChars)
  const onProgressRef = useRef(onProgress)
  const onDoneRef = useRef(onDone)
  useEffect(() => {
    onProgressRef.current = onProgress
    onDoneRef.current = onDone
  })

  useEffect(() => {
    if (!shouldAnimate) return
    const timer = window.setInterval(() => {
      setRevealedChars((current) => {
        const next = Math.min(current + REVEAL_CHARS_PER_TICK, totalChars)
        onProgressRef.current?.()
        if (next >= totalChars) {
          window.clearInterval(timer)
          onDoneRef.current?.()
        }
        return next
      })
    }, REVEAL_TICK_MS)
    return () => window.clearInterval(timer)
  }, [shouldAnimate, totalChars])

  const visible = shouldAnimate ? sliceTokens(tokens, revealedChars) : tokens

  return (
    <p className="chat__text">
      {visible.map((token, index) =>
        token.kind === 'cite' ? (
          <InlineCitation
            key={index}
            citationNumber={token.citationNumber}
            citation={citations[token.citationNumber - 1]}
          />
        ) : (
          <EmphasizedText key={index} token={token} />
        ),
      )}
    </p>
  )
}

function EmphasizedText({ token }: { token: TextToken }) {
  let node: ReactNode = token.text
  if (token.italic) node = <em>{node}</em>
  if (token.bold) node = <strong>{node}</strong>
  return <>{node}</>
}

function InlineCitation({
  citationNumber,
  citation,
}: {
  citationNumber: number
  citation?: Citation
}) {
  const navigate = useNavigate()
  if (!citation) return <>[{citationNumber}]</>
  const tooltip = citation.snippet
    ? `${citation.label}\n\n${citation.snippet}`
    : citation.label
  return (
    <button
      type="button"
      className="chat__inline-cite"
      title={tooltip}
      aria-label={`Citation ${citationNumber}: ${citation.label}`}
      disabled={!citation.reader_link}
      onClick={() => citation.reader_link && navigate(citation.reader_link)}
    >
      {citationNumber}
    </button>
  )
}
