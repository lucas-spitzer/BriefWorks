import { Check, RotateCcw, Send } from 'lucide-react'
import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { useWorkspace } from '../../features/workspace/workspaceContext'
import { useWorkspaceData } from '../../features/workspace/workspaceDataContext'
import { assistantChat } from '../../lib/assistantApi'
import { filterAndSortRecords, useOutputs } from '../../lib/learnerOutputs'
import {
  StudyHead,
  StudyPanel,
  StudySourceReference,
} from './StudySessionChrome'
import { useStudyFullscreen } from './useStudyFullscreen'

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
  const { fullscreen, toggle } = useStudyFullscreen()

  const items = useMemo(
    () =>
      filterAndSortRecords(scenarios, (s) => s.title, {
        search: '',
        sourceId: initialSource,
        sort: 'source',
      }),
    [scenarios, initialSource],
  )

  const [sIndex, setSIndex] = useState(0)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [passed, setPassed] = useState(false)
  const [done, setDone] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const logRef = useRef<HTMLDivElement | null>(null)
  const targetAppliedRef = useRef<string | null>(null)

  // Apply Library deep-link focus once the matching scenario is in the loaded list.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (!targetId || items.length === 0) return
    if (targetAppliedRef.current === targetId) return
    const idx = items.findIndex((s) => s.id === targetId)
    if (idx < 0) return
    setSIndex(idx)
    setPassed(false)
    setDone(false)
    setDraft('')
    setError(null)
    targetAppliedRef.current = targetId
  }, [targetId, items])
  /* eslint-enable react-hooks/set-state-in-effect */

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
    setDone(false)
    setDraft('')
    setError(null)
  }
  const send = async (e: FormEvent) => {
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
      if (verdict?.passed) setPassed(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      setSending(false)
    }
  }

  const goTo = (index: number) => {
    if (index < 0 || index >= items.length) return
    setSIndex(index)
    setPassed(false)
    setDraft('')
    setError(null)
  }

  const nextItem = () => {
    if (isLast) {
      setDone(true)
      return
    }
    goTo(safeIndex + 1)
  }

  const sourceName = scenario
    ? sources.find((s) => s.id === scenario.source_id)?.name ?? 'Unassigned'
    : 'Unassigned'

  const head = (
    <StudyHead
      eyebrow="Applied judgment"
      title="Scenario lab"
      description="Make a decision, explain your reasoning, and review it against doctrine."
      stats={[
        { value: items.length, label: 'scenarios' },
        { value: new Set(items.map((s) => s.source_id ?? '')).size, label: 'sources' },
      ]}
    />
  )

  if (done) {
    return (
      <section className="study-session">
        {head}
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
    <section className="study-session">
      {head}

      {scenario ? (
        <>
          <StudyPanel
            fullscreen={fullscreen}
            onToggleFullscreen={toggle}
            meta={
              <>
                <span className={`pill pill--${scenario.difficulty}`}>{scenario.difficulty}</span>
                <span className="study-session__panel-title">{scenario.title}</span>
              </>
            }
            progress={{ current: safeIndex + 1, total: items.length }}
            pager={{
              onPrev: () => goTo(safeIndex - 1),
              onNext: nextItem,
              prevDisabled: safeIndex <= 0,
              nextDisabled: false,
              label: isLast ? 'Next: finish set' : sourceName,
            }}
          >
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

              {passed && (
                <p className="chat__verdict">
                  <Check size={16} /> Response accepted — use Next item to continue
                </p>
              )}
            </div>
          </StudyPanel>

          <StudySourceReference sourceId={scenario.source_id ?? null} sourceName={sourceName} />
        </>
      ) : (
        <div className="quiz quiz--result">
          <p className="quiz__score">No scenarios</p>
          <p className="quiz__score-note">No scenarios are available for this scope.</p>
        </div>
      )}
    </section>
  )
}
