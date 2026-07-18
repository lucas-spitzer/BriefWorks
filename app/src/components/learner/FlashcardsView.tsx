import { ArrowLeft, ArrowRight, RotateCcw } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useWorkspaceData } from '../../features/workspace/workspaceDataContext'
import { filterAndSortRecords, useOutputs, type OutputSort } from '../../lib/learnerOutputs'
import { OutputFilterBar } from './OutputFilterBar'

export function FlashcardsView({
  sourceId: initialSource = null,
  targetId = null,
}: {
  sourceId?: string | null
  targetId?: string | null
}) {
  const { flashcards } = useWorkspaceData()
  const { sources } = useOutputs()

  const [sourceId, setSourceId] = useState<string | null>(initialSource)
  const [sort, setSort] = useState<OutputSort>('source')

  const cards = useMemo(
    () => filterAndSortRecords(flashcards, (c) => `${c.front} ${c.back}`, { search: '', sourceId, sort }),
    [flashcards, sourceId, sort],
  )

  // Workspace data is already loaded when the Library opens this view, so the
  // focus target resolves at first render — no effect needed.
  const [index, setIndex] = useState(() => {
    if (!targetId) return 0
    const idx = cards.findIndex((c) => c.id === targetId)
    return idx >= 0 ? idx : 0
  })
  const [flipped, setFlipped] = useState(false)

  const reset = () => {
    setIndex(0)
    setFlipped(false)
  }
  const onSource = (v: string | null) => {
    setSourceId(v)
    reset()
  }

  const safeIndex = Math.min(index, Math.max(cards.length - 1, 0))
  const card = cards[safeIndex]

  const go = (delta: number) => {
    if (cards.length === 0) return
    setFlipped(false)
    setIndex((i) => (Math.min(i, cards.length - 1) + delta + cards.length) % cards.length)
  }

  return (
    <section className="study">
      <header className="study__head">
        <h2 className="study__title">Flashcards</h2>
        <span className="study__count">
          {cards.length > 0 ? `Card ${safeIndex + 1} of ${cards.length}` : 'No cards'}
        </span>
      </header>

      <OutputFilterBar
        sourceId={sourceId}
        onSource={onSource}
        sort={sort}
        onSort={setSort}
        sources={sources}
        showTypes={false}
        showSearch={false}
      />

      {card && (
        <div className="study__meta">
          <span className={`pill pill--${card.difficulty}`}>{card.difficulty}</span>
        </div>
      )}

      {card ? (
        <>
          <button
            type="button"
            className={`flashcard${flipped ? ' is-flipped' : ''}`}
            onClick={() => setFlipped((f) => !f)}
          >
            <span className="flashcard__side">
              {flipped ? 'Back · tap to flip' : 'Front · tap to flip'}
            </span>
            <span className="flashcard__body">{flipped ? card.back : card.front}</span>
          </button>

          <div className="study__controls">
            <button type="button" className="study__btn" onClick={() => go(-1)}>
              <ArrowLeft size={16} /> Prev
            </button>
            <button type="button" className="study__btn" onClick={() => setFlipped((f) => !f)}>
              <RotateCcw size={16} /> Flip
            </button>
            <button type="button" className="study__btn" onClick={() => go(1)}>
              Next <ArrowRight size={16} />
            </button>
          </div>
        </>
      ) : (
        <div className="quiz quiz--result">
          <p className="quiz__score">No flashcards</p>
          <p className="quiz__score-note">
            Nothing matches the current filters. Adjust the source above.
          </p>
        </div>
      )}
    </section>
  )
}
