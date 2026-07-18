import { ArrowRight, Check, Info, RotateCcw, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useWorkspaceData } from '../../features/workspace/workspaceDataContext'
import { filterAndSortRecords, useOutputs, type OutputSort } from '../../lib/learnerOutputs'
import type { Quiz } from '../../lib/workspaceApi'
import { OutputFilterBar } from './OutputFilterBar'

// Quiz options are plain strings; correct_answer may be the option text, a
// letter (A/B/C), or a numeric index — handle each.
function optionIsCorrect(quiz: Quiz, option: string, index: number): boolean {
  const answer = (quiz.correct_answer ?? '').trim()
  if (!answer) return false
  if (answer === option) return true
  if (/^[A-Za-z]$/.test(answer) && answer.toUpperCase().charCodeAt(0) - 65 === index) return true
  if (/^\d+$/.test(answer) && Number(answer) === index) return true
  return false
}

export function QuizView({ sourceId: initialSource = null }: { sourceId?: string | null }) {
  const { quizzes } = useWorkspaceData()
  const { sources } = useOutputs()

  const [sourceId, setSourceId] = useState<string | null>(initialSource)
  const [sort, setSort] = useState<OutputSort>('source')

  const items = useMemo(
    () => filterAndSortRecords(quizzes, (q) => q.question, { search: '', sourceId, sort }),
    [quizzes, sourceId, sort],
  )

  const [qIndex, setQIndex] = useState(0)
  const [selected, setSelected] = useState<number | null>(null)
  const [score, setScore] = useState(0)
  const [finished, setFinished] = useState(false)

  const resetRun = () => {
    setQIndex(0)
    setSelected(null)
    setScore(0)
    setFinished(false)
  }
  const onSource = (v: string | null) => {
    setSourceId(v)
    resetRun()
  }
  const onSort = (v: OutputSort) => {
    setSort(v)
    resetRun()
  }

  const safeIndex = Math.min(qIndex, Math.max(items.length - 1, 0))
  const quiz = items[safeIndex]
  const revealed = selected !== null
  const isLast = safeIndex === items.length - 1

  const choose = (i: number) => {
    if (selected !== null || !quiz) return
    setSelected(i)
    if (optionIsCorrect(quiz, quiz.options[i], i)) setScore((s) => s + 1)
  }

  const next = () => {
    if (isLast) {
      setFinished(true)
      return
    }
    setQIndex((i) => i + 1)
    setSelected(null)
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

  if (finished) {
    return (
      <section className="study">
        <header className="study__head">
          <h2 className="study__title">Quiz</h2>
          <span className="study__count">Complete</span>
        </header>
        {filterBar}
        <div className="quiz quiz--result">
          <p className="quiz__score">
            {score} of {items.length} correct
          </p>
          <p className="quiz__score-note">
            Review the source for any items you missed, then run the quiz again.
          </p>
          <button type="button" className="study__btn" onClick={resetRun}>
            <RotateCcw size={16} /> Restart quiz
          </button>
        </div>
      </section>
    )
  }

  return (
    <section className="study">
      <header className="study__head">
        <h2 className="study__title">Quiz</h2>
        <span className="study__count">
          {items.length > 0 ? `Question ${safeIndex + 1} of ${items.length}` : 'No questions'}
        </span>
      </header>

      {filterBar}

      {quiz && (
        <div className="study__meta">
          <span className={`pill pill--${quiz.difficulty}`}>{quiz.difficulty}</span>
        </div>
      )}

      {quiz ? (
        <div className="quiz">
          <p className="quiz__question">{quiz.question}</p>
          <div className="quiz__options">
            {quiz.options.map((opt, i) => {
              let cls = 'quiz__option'
              const correct = optionIsCorrect(quiz, opt, i)
              const showCorrect = revealed && correct
              const showWrong = revealed && i === selected && !correct
              if (showCorrect) cls += ' is-correct'
              else if (showWrong) cls += ' is-wrong'
              return (
                <button
                  key={i}
                  type="button"
                  className={cls}
                  disabled={revealed}
                  onClick={() => choose(i)}
                >
                  <span className="quiz__option-text">{opt}</span>
                  {showCorrect && (
                    <span className="quiz__option-status">
                      <Check size={16} /> Correct
                    </span>
                  )}
                  {showWrong && (
                    <span className="quiz__option-status">
                      <X size={16} /> Incorrect
                    </span>
                  )}
                </button>
              )
            })}
          </div>
          {revealed && (
            <>
              {quiz.explanation && (
                <p className="quiz__explain">
                  <Info size={15} /> {quiz.explanation}
                </p>
              )}
              <div className="study__controls study__controls--end">
                <button type="button" className="study__btn study__btn--primary" onClick={next}>
                  {isLast ? 'See results' : 'Next question'} <ArrowRight size={16} />
                </button>
              </div>
            </>
          )}
        </div>
      ) : (
        <div className="quiz quiz--result">
          <p className="quiz__score">No questions</p>
          <p className="quiz__score-note">
            Nothing matches the current filters. Adjust the source above.
          </p>
        </div>
      )}
    </section>
  )
}
