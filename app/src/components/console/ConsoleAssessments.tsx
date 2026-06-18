import { useMemo, useState } from 'react'
import { useWorkspaceData } from '../../features/workspace/workspaceDataContext'
import { formatDate } from '../../lib/consoleFormat'
import { ConsoleViewToggle } from './ConsoleViewToggle'
import { ErrorBanner } from './ErrorBanner'
import type { ConsoleView } from './types'

export function ConsoleAssessments() {
  const { assessmentSets, flashcards, quizzes, scenarios, isLoading, error } = useWorkspaceData()
  const [query, setQuery] = useState('')
  const [view, setView] = useState<ConsoleView>('grid')

  const totalCount = flashcards.length + quizzes.length + scenarios.length

  const filteredAssessmentSets = useMemo(() => {
    const q = query.toLowerCase()
    return assessmentSets.filter(
      (assessmentSet) =>
        assessmentSet.title.toLowerCase().includes(q) ||
        (assessmentSet.learning_goal ?? '').toLowerCase().includes(q),
    )
  }, [assessmentSets, query])

  const filteredFlashcards = useMemo(() => {
    const q = query.toLowerCase()
    return flashcards.filter(
      (card) => card.front.toLowerCase().includes(q) || card.back.toLowerCase().includes(q),
    )
  }, [flashcards, query])

  const filteredQuizzes = useMemo(() => {
    const q = query.toLowerCase()
    return quizzes.filter((quiz) => quiz.question.toLowerCase().includes(q))
  }, [quizzes, query])

  const filteredScenarios = useMemo(() => {
    const q = query.toLowerCase()
    return scenarios.filter(
      (scenario) =>
        scenario.title.toLowerCase().includes(q) || scenario.prompt.toLowerCase().includes(q),
    )
  }, [scenarios, query])

  const filteredCount =
    filteredFlashcards.length + filteredQuizzes.length + filteredScenarios.length

  return (
    <>
      <header className="bw-console__header">
        <div>
          <div className="bw-console__eyebrow">Assessment Bank</div>
          <h2>QnGen Outputs</h2>
        </div>
        <ConsoleViewToggle view={view} onChange={setView} />
      </header>
      <div className="bw-console__scroll">
        {error ? <ErrorBanner message={error} /> : null}
        <div className="bw-console__searchbar">
          <span style={{ color: '#6f828b' }}>⌕</span>
          <input
            placeholder="Search assessment sets, flashcards, quizzes, and scenarios…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <span className="bw-count">{filteredAssessmentSets.length} sets · {filteredCount} items</span>
        </div>
        {isLoading && totalCount === 0 && assessmentSets.length === 0 ? (
          <div className="bw-console__empty">Loading assessments…</div>
        ) : totalCount === 0 && assessmentSets.length === 0 ? (
          <div className="bw-console__empty">
            No assessments yet. Run a production pipeline with review targets after
            Extract Knowledge has produced canonical wiki entries.
          </div>
        ) : (
          <>
            {filteredAssessmentSets.length > 0 ? (
              <section className="bw-console__panel" style={{ marginBottom: 'var(--space-5)' }}>
                <div className="bw-console__panel-head">
                  <h3>Assessment Sets</h3>
                  <span className="bw-count">{filteredAssessmentSets.length}</span>
                </div>
                <div className="bw-console__sources">
                  {filteredAssessmentSets.map((assessmentSet) => (
                    <div
                      className="bw-console__panel bw-console__artifact-card"
                      key={assessmentSet.id}
                      style={{ padding: 18 }}
                    >
                      <div style={{ fontWeight: 600, color: '#fff' }}>{assessmentSet.title}</div>
                      <p style={{ fontSize: '0.84rem', color: '#b6c4cb', marginTop: 8 }}>
                        {assessmentSet.learning_goal ?? 'Canonical assessment set'}
                      </p>
                      <div className="bw-console__card-fill" aria-hidden="true" />
                      <div className="bw-console__artifact-foot">
                        <span className="seg">{assessmentSet.item_count} items</span>
                        <span className="seg">{assessmentSet.assessment_types.join(', ')}</span>
                        <span className="seg">{formatDate(assessmentSet.created_at)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            ) : null}

            {filteredFlashcards.length > 0 ? (
              <section className="bw-console__panel" style={{ marginBottom: 'var(--space-5)' }}>
                <div className="bw-console__panel-head">
                  <h3>Flashcards</h3>
                  <span className="bw-count">{filteredFlashcards.length}</span>
                </div>
                {view === 'list' ? (
                  <table className="bw-console__table">
                    <thead>
                      <tr>
                        <th>Front</th>
                        <th>Back</th>
                        <th>Subtype</th>
                        <th>Difficulty</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredFlashcards.map((card) => (
                        <tr key={card.id}>
                          <td>{card.front}</td>
                          <td>{card.back}</td>
                          <td>{card.subtype ?? 'basic'}</td>
                          <td>{card.difficulty}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="bw-console__sources">
                    {filteredFlashcards.map((card) => (
                      <div className="bw-console__panel bw-console__artifact-card" key={card.id} style={{ padding: 18 }}>
                        <div style={{ fontWeight: 600, color: '#fff' }}>{card.front}</div>
                        <p style={{ fontSize: '0.84rem', color: '#b6c4cb', marginTop: 8 }}>{card.back}</p>
                        <div className="bw-console__card-fill" aria-hidden="true" />
                        <div className="bw-console__artifact-foot">
                          {card.assessment_set_id ? (
                            <span className="seg">Set linked</span>
                          ) : null}
                          <span className="seg">{card.subtype ?? 'basic'}</span>
                          <span className="seg">{card.difficulty}</span>
                          <span className="seg">{formatDate(card.created_at)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            ) : null}

            {filteredQuizzes.length > 0 ? (
              <section className="bw-console__panel" style={{ marginBottom: 'var(--space-5)' }}>
                <div className="bw-console__panel-head">
                  <h3>Quizzes</h3>
                  <span className="bw-count">{filteredQuizzes.length}</span>
                </div>
                {view === 'list' ? (
                  <table className="bw-console__table">
                    <thead>
                      <tr>
                        <th>Question</th>
                        <th>Type</th>
                        <th>Difficulty</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredQuizzes.map((quiz) => (
                        <tr key={quiz.id}>
                          <td>{quiz.question}</td>
                          <td>{quiz.subtype ?? quiz.question_type}</td>
                          <td>{quiz.difficulty}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="bw-console__sources">
                    {filteredQuizzes.map((quiz) => (
                      <div className="bw-console__panel bw-console__artifact-card" key={quiz.id} style={{ padding: 18 }}>
                        <div style={{ fontWeight: 600, color: '#fff' }}>{quiz.question}</div>
                        <p style={{ fontSize: '0.84rem', color: '#b6c4cb', marginTop: 8 }}>
                          {quiz.explanation ?? quiz.correct_answer}
                        </p>
                        <div className="bw-console__card-fill" aria-hidden="true" />
                        <div className="bw-console__artifact-foot">
                          {quiz.assessment_set_id ? (
                            <span className="seg">Set linked</span>
                          ) : null}
                          <span className="seg">{quiz.subtype ?? quiz.question_type}</span>
                          <span className="seg">{quiz.difficulty}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            ) : null}

            {filteredScenarios.length > 0 ? (
              <section className="bw-console__panel">
                <div className="bw-console__panel-head">
                  <h3>Scenarios</h3>
                  <span className="bw-count">{filteredScenarios.length}</span>
                </div>
                {view === 'list' ? (
                  <table className="bw-console__table">
                    <thead>
                      <tr>
                        <th>Title</th>
                        <th>Prompt</th>
                        <th>Subtype</th>
                        <th>Difficulty</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredScenarios.map((scenario) => (
                        <tr key={scenario.id}>
                          <td>{scenario.title}</td>
                          <td>{scenario.prompt}</td>
                          <td>{scenario.subtype ?? 'decision_prompt'}</td>
                          <td>{scenario.difficulty}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="bw-console__sources">
                    {filteredScenarios.map((scenario) => (
                      <div className="bw-console__panel bw-console__artifact-card" key={scenario.id} style={{ padding: 18 }}>
                        <div style={{ fontWeight: 600, color: '#fff' }}>{scenario.title}</div>
                        <p style={{ fontSize: '0.84rem', color: '#b6c4cb', marginTop: 8 }}>{scenario.prompt}</p>
                        <div className="bw-console__card-fill" aria-hidden="true" />
                        <div className="bw-console__artifact-foot">
                          {scenario.assessment_set_id ? (
                            <span className="seg">Set linked</span>
                          ) : null}
                          <span className="seg">{scenario.subtype ?? 'decision_prompt'}</span>
                          <span className="seg">{scenario.difficulty}</span>
                          <span className="seg">{formatDate(scenario.created_at)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            ) : null}

            {filteredCount === 0 && filteredAssessmentSets.length === 0 && query ? (
              <div className="bw-console__empty">No assessments match your search.</div>
            ) : null}
          </>
        )}
      </div>
    </>
  )
}
