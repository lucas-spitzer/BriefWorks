import { Send } from 'lucide-react'
import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWorkspace } from '../../features/workspace/workspaceContext'
import {
  assistantChat,
  type Citation,
  type DiscussionSubmode,
} from '../../lib/assistantApi'
import { useWorkspaceData } from '../../features/workspace/workspaceDataContext'
import { useOutputs } from '../../lib/learnerOutputs'
import {
  StudyHead,
  StudyPanel,
  StudySourceReference,
} from './StudySessionChrome'
import { useStudyFullscreen } from './useStudyFullscreen'

type ChatMessage = { role: 'ai' | 'user'; text: string; citations?: Citation[] }

type DiscussionItem = {
  id: string
  source_id: string | null
  title: string
  prompt: string
}

/* Discussions mirror the Scenario lab structure: an itemized set of
   source-grounded prompts worked one at a time. Prompts are derived from the
   workspace's canonical knowledge-base entries. */

export function DiscussionsView({ sourceId: initialSource = null }: { sourceId?: string | null }) {
  const { activeWorkspace } = useWorkspace()
  const { wikiEntries } = useWorkspaceData()
  const { sources } = useOutputs()
  const { fullscreen, toggle } = useStudyFullscreen()

  const [mode, setMode] = useState<DiscussionSubmode>('socratic')

  const items = useMemo<DiscussionItem[]>(() => {
    const derived = wikiEntries
      .filter((entry) => entry.status === 'canonical')
      .map((entry) => ({
        id: entry.id,
        source_id: entry.evidence.find((e) => e.source_id)?.source_id ?? null,
        title: `Explain ${entry.preferred_label}.`,
        prompt: `Explain the concept of ${entry.preferred_label} and why it matters. Ground your answer in the source.`,
      }))
      .filter((item) => !initialSource || item.source_id === initialSource)
    return derived.sort(
      (a, b) => (a.source_id ?? '').localeCompare(b.source_id ?? '') || a.title.localeCompare(b.title),
    )
  }, [wikiEntries, initialSource])

  const [dIndex, setDIndex] = useState(0)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const logRef = useRef<HTMLDivElement | null>(null)

  const safeIndex = Math.min(dIndex, Math.max(items.length - 1, 0))
  const item = items[safeIndex]

  // Reseed the opening prompt whenever the active item changes (covers filter
  // and sort changes as well as paging). Intentional state sync.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (item) setMessages([{ role: 'ai', text: item.prompt }])
  }, [item])
  /* eslint-enable react-hooks/set-state-in-effect */

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [messages, sending])

  const resetItemState = () => {
    setDraft('')
    setError(null)
  }

  const goTo = (index: number) => {
    if (index < 0 || index >= items.length) return
    setDIndex(index)
    resetItemState()
  }

  const send = async (e: FormEvent) => {
    e.preventDefault()
    const text = draft.trim()
    if (!text || sending || !item || !activeWorkspace) return

    const next: ChatMessage[] = [...messages, { role: 'user', text }]
    setMessages(next)
    setDraft('')
    setError(null)
    setSending(true)
    try {
      const response = await assistantChat(activeWorkspace.id, {
        mode: 'discussion',
        submode: mode,
        source_ids: item.source_id ? [item.source_id] : undefined,
        messages: next.map((m) => ({
          role: m.role === 'ai' ? 'assistant' : 'user',
          content: m.text,
        })),
      })
      setMessages((m) => [...m, { role: 'ai', text: response.answer, citations: response.citations }])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      setSending(false)
    }
  }

  const sourceName = item
    ? sources.find((s) => s.id === item.source_id)?.name ?? 'Unassigned'
    : 'Unassigned'
  const isLast = safeIndex === items.length - 1

  return (
    <section className="study-session">
      <StudyHead
        eyebrow="Guided inquiry"
        title="Discussion room"
        description="Develop an argument through source-grounded questions."
        stats={[
          { value: items.length, label: 'prompts' },
          { value: new Set(items.map((d) => d.source_id ?? '')).size, label: 'sources' },
        ]}
      />

      {item ? (
        <>
          <StudyPanel
            fullscreen={fullscreen}
            onToggleFullscreen={toggle}
            meta={<span className="study-session__panel-title">{item.title}</span>}
            center={
              <div className="disc__seg" role="group" aria-label="Discussion style">
                <button
                  type="button"
                  className={`disc__seg-btn${mode === 'socratic' ? ' is-active' : ''}`}
                  onClick={() => setMode('socratic')}
                  aria-pressed={mode === 'socratic'}
                >
                  Socratic
                </button>
                <button
                  type="button"
                  className={`disc__seg-btn${mode === 'euclidean' ? ' is-active' : ''}`}
                  onClick={() => setMode('euclidean')}
                  aria-pressed={mode === 'euclidean'}
                >
                  Euclidean
                </button>
              </div>
            }
            pager={{
              onPrev: () => goTo(safeIndex - 1),
              onNext: () => goTo(safeIndex + 1),
              prevDisabled: safeIndex <= 0,
              nextDisabled: isLast,
              label: sourceName,
            }}
          >
            <div className="chat">
              <div className="chat__log" ref={logRef}>
                {messages.map((m, i) => (
                  <div key={i} className={`chat__msg chat__msg--${m.role}`}>
                    <span className="chat__role">{m.role === 'ai' ? 'Tutor' : 'You'}</span>
                    <p className="chat__text">{m.text}</p>
                    {m.citations && m.citations.length > 0 && <Citations citations={m.citations} />}
                  </div>
                ))}
                {sending && (
                  <div className="chat__msg chat__msg--ai">
                    <span className="chat__role">Tutor</span>
                    <p className="chat__text chat__text--typing">Thinking…</p>
                  </div>
                )}
              </div>

              {error && <p className="chat__error">{error}</p>}

              <form className="chat__compose" onSubmit={send}>
                <input
                  className="chat__input"
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder={mode === 'socratic' ? 'Share your thinking…' : 'Ask a question…'}
                  aria-label="Your message"
                  disabled={sending}
                />
                <button type="submit" className="chat__send" disabled={!draft.trim() || sending}>
                  <Send size={16} /> Send
                </button>
              </form>
            </div>
          </StudyPanel>

          <StudySourceReference sourceId={item.source_id} sourceName={sourceName} />
        </>
      ) : (
        <div className="quiz quiz--result">
          <p className="quiz__score">No discussion prompts</p>
          <p className="quiz__score-note">
            Prompts are generated from the knowledge base. Ingest a source to begin.
          </p>
        </div>
      )}
    </section>
  )
}

function Citations({ citations }: { citations: Citation[] }) {
  const navigate = useNavigate()
  return (
    <div className="chat__cites">
      {citations.map((c, i) => (
        <button
          key={i}
          type="button"
          className="chat__cite"
          title={c.snippet}
          disabled={!c.reader_link}
          onClick={() => c.reader_link && navigate(c.reader_link)}
        >
          [{i + 1}] {c.label}
        </button>
      ))}
    </div>
  )
}
