import { ArrowRightLeft, HelpCircle, ListChecks, MessageCircle, Play, Target } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useWorkspace } from '../../features/workspace/workspaceContext'
import { useWorkspaceData } from '../../features/workspace/workspaceDataContext'
import { listSourceChapters, type DocumentChapter } from '../../lib/sourcesApi'
import type { DiscussionSubmode } from '../../lib/assistantApi'

const GENERIC: { prompt: string; icon: typeof ListChecks }[] = [
  { prompt: 'Summarize the key ideas of this material.', icon: ListChecks },
  { prompt: 'Test my understanding with questions.', icon: Target },
  { prompt: 'Explain a point I find confusing.', icon: HelpCircle },
]

type Props = {
  mode: DiscussionSubmode
  onMode: (mode: DiscussionSubmode) => void
  sourceId: string | null
  onSource: (id: string | null) => void
  sources: { id: string; name: string }[]
  onStart: (prompt: string) => void
}

export function DiscussionStarter({ mode, onMode, sourceId, onSource, sources, onStart }: Props) {
  const { activeWorkspace } = useWorkspace()
  const { wikiEntries } = useWorkspaceData()
  const [chapters, setChapters] = useState<DocumentChapter[]>([])
  const [draft, setDraft] = useState('')

  // Chapter-derived prompts need the selected source's chapters.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (!sourceId || !activeWorkspace) {
      setChapters([])
      return
    }
    let cancelled = false
    listSourceChapters(activeWorkspace.id, sourceId)
      .then((rows) => !cancelled && setChapters(rows))
      .catch(() => !cancelled && setChapters([]))
    return () => {
      cancelled = true
    }
  }, [sourceId, activeWorkspace])
  /* eslint-enable react-hooks/set-state-in-effect */

  const sourcePrompts = useMemo(() => {
    const out: { prompt: string; compare?: boolean }[] = []
    const concepts = wikiEntries.filter((w) => w.status === 'canonical').slice(0, 4)
    concepts.forEach((w) =>
      out.push({ prompt: `Explain the concept of ${w.preferred_label} and why it matters.` }),
    )
    if (concepts.length >= 2) {
      out.push({
        prompt: `Compare ${concepts[0].preferred_label} and ${concepts[1].preferred_label}.`,
        compare: true,
      })
    }
    chapters.slice(0, 3).forEach((c) => out.push({ prompt: `Walk me through ${c.title}.` }))
    return out.slice(0, 6)
  }, [wikiEntries, chapters])

  const startOwn = () => {
    const text = draft.trim()
    if (text) onStart(text)
  }

  return (
    <section className="study disc">
      <header className="study__head">
        <div>
          <h2 className="study__title">Discussions</h2>
          <p className="disc__sub">
            Pick a starter to prefill your prompt, edit it if you like, then start the session.
            Each session is grounded in your sources.
          </p>
        </div>
      </header>

      <div className="disc__controls">
        <label className="lib__select">
          <span className="lib__select-label">Source</span>
          <select
            value={sourceId ?? ''}
            onChange={(e) => onSource(e.target.value || null)}
            aria-label="Source scope"
          >
            <option value="">All sources</option>
            {sources.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <div className="disc__seg" role="group" aria-label="Discussion style">
          <button
            type="button"
            className={`disc__seg-btn${mode === 'socratic' ? ' is-active' : ''}`}
            onClick={() => onMode('socratic')}
            aria-pressed={mode === 'socratic'}
          >
            Socratic
          </button>
          <button
            type="button"
            className={`disc__seg-btn${mode === 'euclidean' ? ' is-active' : ''}`}
            onClick={() => onMode('euclidean')}
            aria-pressed={mode === 'euclidean'}
          >
            Euclidean
          </button>
        </div>
      </div>

      {sourcePrompts.length > 0 && (
        <>
          <div className="disc__label">
            <h3>From your sources</h3>
            <span className="disc__label-line" />
          </div>
          <div className="disc__grid">
            {sourcePrompts.map((p) => {
              const Icon = p.compare ? ArrowRightLeft : MessageCircle
              return (
                <button key={p.prompt} type="button" className="disc__prompt" onClick={() => setDraft(p.prompt)}>
                  <Icon size={16} aria-hidden="true" />
                  <span>{p.prompt}</span>
                </button>
              )
            })}
          </div>
        </>
      )}

      <div className="disc__label">
        <h3>Starters</h3>
        <span className="disc__label-line" />
      </div>
      <div className="disc__grid">
        {GENERIC.map(({ prompt, icon: Icon }) => (
          <button key={prompt} type="button" className="disc__prompt disc__prompt--gen" onClick={() => setDraft(prompt)}>
            <Icon size={16} aria-hidden="true" />
            <span>{prompt}</span>
          </button>
        ))}
      </div>

      <div className="disc__own">
        <div className="disc__label" style={{ marginTop: 0 }}>
          <h3>Or start your own</h3>
          <span className="disc__label-line" />
        </div>
        <form
          className="disc__field"
          onSubmit={(e) => {
            e.preventDefault()
            startOwn()
          }}
        >
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Ask anything about your sources…"
            aria-label="Start your own discussion"
          />
          <button type="submit" className="disc__start" disabled={!draft.trim()}>
            <Play size={15} /> Start session
          </button>
        </form>
      </div>
    </section>
  )
}
