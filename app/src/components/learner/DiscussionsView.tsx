import { RotateCcw, Send } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWorkspace } from '../../features/workspace/workspaceContext'
import {
  assistantChat,
  type Citation,
  type DiscussionSubmode,
} from '../../lib/assistantApi'
import { useOutputs } from '../../lib/learnerOutputs'
import { DiscussionStarter } from './DiscussionStarter'

type ChatMessage = { role: 'ai' | 'user'; text: string; citations?: Citation[] }

export function DiscussionsView({ sourceId: initialSource = null }: { sourceId?: string | null }) {
  const { activeWorkspace } = useWorkspace()
  const { sources } = useOutputs()

  const [mode, setMode] = useState<DiscussionSubmode>('socratic')
  const [sourceId, setSourceId] = useState<string | null>(initialSource)
  const [started, setStarted] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const logRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [messages, sending])

  const runTurn = async (text: string, prior: ChatMessage[]) => {
    if (!activeWorkspace) return
    const next: ChatMessage[] = [...prior, { role: 'user', text }]
    setMessages(next)
    setError(null)
    setSending(true)
    try {
      const response = await assistantChat(activeWorkspace.id, {
        mode: 'discussion',
        submode: mode,
        source_ids: sourceId ? [sourceId] : undefined,
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

  const beginSession = (prompt: string) => {
    setStarted(true)
    setMessages([])
    void runTurn(prompt, [])
  }

  const newSession = () => {
    setStarted(false)
    setMessages([])
    setDraft('')
    setError(null)
  }

  const send = (e: React.FormEvent) => {
    e.preventDefault()
    const text = draft.trim()
    if (!text || sending) return
    setDraft('')
    void runTurn(text, messages)
  }

  if (!started) {
    return (
      <DiscussionStarter
        mode={mode}
        onMode={setMode}
        sourceId={sourceId}
        onSource={setSourceId}
        sources={sources}
        onStart={beginSession}
      />
    )
  }

  return (
    <section className="study">
      <header className="study__head study__head--discussions">
        <div>
          <h2 className="study__title">Discussions</h2>
          <p className="discussions__subtitle">
            {mode === 'socratic' ? 'Socratic' : 'Euclidean'} session
            {sourceId ? ` · ${sources.find((s) => s.id === sourceId)?.name ?? 'source'}` : ''}
          </p>
        </div>
        <button type="button" className="study__btn" onClick={newSession}>
          <RotateCcw size={16} /> New session
        </button>
      </header>

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
