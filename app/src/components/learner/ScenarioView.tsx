import { ArrowRight, Check, RotateCcw, Send } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useWorkspace } from '../../features/workspace/workspaceContext'
import { useWorkspaceData } from '../../features/workspace/workspaceDataContext'
import { assistantChat } from '../../lib/assistantApi'
import { filterAndSortRecords, useOutputs, type OutputSort } from '../../lib/learnerOutputs'
import { OutputFilterBar } from './OutputFilterBar'

type ChatMessage = { role: 'ai' | 'user'; text: string }

function openingMessage(prompt: string): ChatMessage {
  return { role: 'ai', text: prompt }
}

export function ScenarioView({
  sourceId: initialSource = null,
  targetId = null,
}: {
  sourceId?: string | null
  targetId?: string | null
}) {
  const { activeWorkspace } = useWorkspace()
  const { scenarios } = useWorkspaceData()
  const { sources } = useOutputs()

  const [sourceId, setSourceId] = useState<string | null>(initialSource)
  const [sort, setSort] = useState<OutputSort>('source')

  const items = useMemo(
    () => filterAndSortRecords(scenarios, (s) => s.title, { search: '', sourceId, sort }),
    [scenarios, sourceId, sort],
  )

  const [sIndex, setSIndex] = useState(() => {
    if (!targetId) return 0
    const idx = items.findIndex((s) => s.id === targetId)
    return idx >= 0 ? idx : 0
  })
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [passed, setPassed] = useState(false)
  const [hasFeedback, setHasFeedback] = useState(false)
  const [done, setDone] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const logRef = useRef<HTMLDivElement | null>(null)

  const safeIndex = Math.min(sIndex, Math.max(items.length - 1, 0))
  const scenario = items[safeIndex]
  const isLast = safeIndex === items.length - 1

  // Reseed the opening prompt whenever the active scenario changes (covers async
  // data load, navigation, and filter changes). Intentional state sync.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (scenario) setMessages([openingMessage(scenario.prompt)])
  }, [scenario])
  /* eslint-enable react-hooks/set-state-in-effect */

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [messages, sending])

  const resetRun = () => {
    setSIndex(0)
    setPassed(false)
    setHasFeedback(false)
    setDone(false)
    setDraft('')
    setError(null)
  }
  const onSource = (v: string | null) => {
    setSourceId(v)
    resetRun()
  }
  const onSort = (v: OutputSort) => {
    setSort(v)
    resetRun()
  }

  const send = async (e: React.FormEvent) => {
    e.preventDefault()
    const text = draft.trim()
    if (!text || sending || !scenario || !activeWorkspace) return

    const nextMessages: ChatMessage[] = [...messages, { role: 'user', text }]
    setMessages(nextMessages)
    setDraft('')
    setError(null)
    setSending(true)

    try {
      const response = await assistantChat(activeWorkspace.id, {
        mode: 'scenario',
        scenario_id: scenario.id,
        messages: nextMessages.map((m) => ({
          role: m.role === 'ai' ? 'assistant' : 'user',
          content: m.text,
        })),
      })
      const verdict = response.evaluation
      const feedback = verdict?.feedback || response.answer
      setMessages((m) => [...m, { role: 'ai', text: feedback }])
      setHasFeedback(true)
      if (verdict?.passed) setPassed(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      setSending(false)
    }
  }

  const moveOn = () => {
    if (safeIndex + 1 >= items.length) {
      setDone(true)
      return
    }
    setSIndex(safeIndex + 1)
    setPassed(false)
    setHasFeedback(false)
    setDraft('')
    setError(null)
  }

  const filterBar = (
    <OutputFilterBar
      sourceId={sourceId}
      onSource={onSource}
      sort={sort}
      onSort={onSort}
      sources={sources}
      showTypes={false}
      showSearch={false}
    />
  )

  if (done) {
    return (
      <section className="study">
        <header className="study__head">
          <h2 className="study__title">Scenarios</h2>
          <span className="study__count">Complete</span>
        </header>
        {filterBar}
        <div className="quiz quiz--result">
          <p className="quiz__score">All scenarios reviewed</p>
          <p className="quiz__score-note">
            You worked through every scenario in this set. Restart to practise again.
          </p>
          <button type="button" className="study__btn" onClick={resetRun}>
            <RotateCcw size={16} /> Restart scenarios
          </button>
        </div>
      </section>
    )
  }

  return (
    <section className="study">
      <header className="study__head">
        <h2 className="study__title">Scenarios</h2>
        <span className="study__count">
          {items.length > 0 ? `Scenario ${safeIndex + 1} of ${items.length}` : 'No scenarios'}
        </span>
      </header>

      {filterBar}

      {scenario && (
        <div className="study__meta scenario__heading">
          <span className={`pill pill--${scenario.difficulty}`}>{scenario.difficulty}</span>
          {scenario.title}
        </div>
      )}

      {scenario ? (
        <div className="chat">
          <div className="chat__log" ref={logRef}>
            {messages.map((m, i) => (
              <div key={i} className={`chat__msg chat__msg--${m.role}`}>
                <span className="chat__role">{m.role === 'ai' ? 'Grader' : 'You'}</span>
                <p className="chat__text">{m.text}</p>
              </div>
            ))}
            {sending && (
              <div className="chat__msg chat__msg--ai">
                <span className="chat__role">Grader</span>
                <p className="chat__text chat__text--typing">Assessing…</p>
              </div>
            )}
          </div>

          {error && <p className="chat__error">{error}</p>}

          <form className="chat__compose" onSubmit={send}>
            <input
              className="chat__input"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Type your response…"
              aria-label="Your response"
              disabled={sending}
            />
            <button type="submit" className="chat__send" disabled={!draft.trim() || sending}>
              <Send size={16} /> Send
            </button>
          </form>

          {passed ? (
            <div className="chat__actions">
              <p className="chat__verdict">
                <Check size={16} /> Response accepted
              </p>
              <button type="button" className="study__btn study__btn--primary" onClick={moveOn}>
                {isLast ? 'Finish scenarios' : 'Continue to next scenario'} <ArrowRight size={16} />
              </button>
            </div>
          ) : (
            hasFeedback && (
              <div className="chat__actions">
                <button type="button" className="study__btn" onClick={moveOn}>
                  Move on without finishing <ArrowRight size={16} />
                </button>
              </div>
            )
          )}
        </div>
      ) : (
        <div className="quiz quiz--result">
          <p className="quiz__score">No scenarios</p>
          <p className="quiz__score-note">
            Nothing matches the current filters, or none have been generated yet.
          </p>
        </div>
      )}
    </section>
  )
}
