import { Check, Info, RotateCcw, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useWorkspaceData } from '../../features/workspace/workspaceDataContext'
import { filterAndSortRecords, useOutputs } from '../../lib/academyOutputs'
import type { Quiz } from '../../lib/workspaceApi'
import {
  StudyHead,
  StudyPanel,
  StudySourceReference,
} from './StudySessionChrome'
import { useStudyFullscreen } from './useStudyFullscreen'

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

export function QuizView({
  sourceId: initialSource = null,
  targetId = null,
}: {
  sourceId?: string | null
  targetId?: string | null
}) {
  const { quizzes } = useWorkspaceData()
  const { sources } = useOutputs()
  const { fullscreen, toggle } = useStudyFullscreen()

  const items = useMemo(
    () =>
      filterAndSortRecords(quizzes, (q) => q.question, {
        search: '',
        sourceId: initialSource,
        sort: 'source',
      }),
    [quizzes, initialSource],
  )

  const [qIndex, setQIndex] = useState(0)
  const [selected, setSelected] = useState<number | null>(null)
  const [score, setScore] = useState(0)
  const [finished, setFinished] = useState(false)
  const targetAppliedRef = useRef<string | null>(null)

  // Apply Library / console deep-link focus once the matching question is loaded.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (!targetId || items.length === 0) return
    if (targetAppliedRef.current === targetId) return
    const idx = items.findIndex((q) => q.id === targetId)
    if (idx < 0) return
    setQIndex(idx)
    setSelected(null)
    setScore(0)
    setFinished(false)
    targetAppliedRef.current = targetId
  }, [targetId, items])
  /* eslint-enable react-hooks/set-state-in-effect */

  const resetRun = () => {
    setQIndex(0)
    setSelected(null)
    setScore(0)
    setFinished(false)
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

  const prev = () => {
    if (safeIndex === 0) return
    setQIndex((i) => i - 1)
    setSelected(null)
  }

  const sourceName = quiz
    ? sources.find((s) => s.id === quiz.source_id)?.name ?? 'Unassigned'
    : 'Unassigned'

  const head = (
    <StudyHead
      eyebrow="Knowledge check"
      title="Quiz"
      description="Answer, review the rationale, and trace each item to its source."
      stats={[
        { value: items.length, label: 'questions' },
        { value: new Set(items.map((q) => q.source_id ?? '')).size, label: 'sources' },
      ]}
    />
  )

  if (finished) {
    return (
      <section className="study-session">
        {head}
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
    <section className="study-session">
      {head}

      {quiz ? (
        <>
          <StudyPanel
            fullscreen={fullscreen}
            onToggleFullscreen={toggle}
            meta={<span className={`pill pill--${quiz.difficulty}`}>{quiz.difficulty}</span>}
            progress={{ current: safeIndex + 1, total: items.length }}
            pager={{
              onPrev: prev,
              onNext: next,
              prevDisabled: safeIndex <= 0,
              // Require an answer before moving forward; the last item leads to results.
              nextDisabled: !revealed,
              label: isLast && revealed ? 'Next: results' : sourceName,
            }}
          >
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
              {revealed && quiz.explanation && (
                <p className="quiz__explain">
                  <Info size={15} /> {quiz.explanation}
                </p>
              )}
            </div>
          </StudyPanel>

          <StudySourceReference sourceId={quiz.source_id ?? null} sourceName={sourceName} />
        </>
      ) : (
        <div className="quiz quiz--result">
          <p className="quiz__score">No questions</p>
          <p className="quiz__score-note">No questions are available for this scope.</p>
        </div>
      )}
    </section>
  )
}
