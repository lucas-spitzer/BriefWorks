import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useWorkspace } from '../features/workspace/workspaceContext'
import {
  TARGET_ARTIFACT_OPTIONS,
  createProductionRun,
  getArtifactDownloadUrl,
  getProductionRun,
  getSkillRun,
  listArtifacts,
  listFlashcards,
  listProductionRuns,
  listQuizzes,
  listScenarios,
  listSkillRuns,
  listSources,
  listWikiDisputes,
  listWikiEntries,
  uploadSource,
  type Artifact,
  type Flashcard,
  type ProductionRun,
  type Quiz,
  type Scenario,
  type SkillRun,
  type Source,
  type WikiEntry,
} from '../lib/workspaceApi'

function PageHeader({
  eyebrow,
  title,
  children,
}: {
  children: string
  eyebrow: string
  title: string
}) {
  return (
    <header className="page-header">
      <p className="eyebrow">{eyebrow}</p>
      <h2>{title}</h2>
      <p>{children}</p>
    </header>
  )
}

function StatusBadge({ status }: { status: string }) {
  return <span className={`status-badge status-badge--${status}`}>{status}</span>
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return '—'
  }

  return new Date(value).toLocaleString()
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function useWorkspaceId(): string | null {
  const { activeWorkspace } = useWorkspace()
  return activeWorkspace?.id ?? null
}

export function DashboardPage() {
  const workspaceId = useWorkspaceId()
  const [counts, setCounts] = useState({
    sources: 0,
    wiki: 0,
    artifacts: 0,
    runs: 0,
    flashcards: 0,
  })

  useEffect(() => {
    if (!workspaceId) {
      return
    }

    void Promise.all([
      listSources(workspaceId),
      listWikiEntries(workspaceId),
      listArtifacts(workspaceId),
      listProductionRuns(workspaceId),
      listFlashcards(workspaceId),
    ]).then(([sources, wiki, artifacts, runs, flashcards]) => {
      setCounts({
        sources: sources.length,
        wiki: wiki.length,
        artifacts: artifacts.length,
        runs: runs.length,
        flashcards: flashcards.length,
      })
    })
  }, [workspaceId])

  const moduleCards = [
    {
      description: 'Browse wiki entries, disputes, and extracted concepts.',
      label: 'Intellex',
      path: '/app/intellex',
      status: `${counts.wiki} wiki entries`,
    },
    {
      description: 'Download ElevenReader EPUB scripts generated from sources.',
      label: 'Mathesys',
      path: '/app/mathesys',
      status: `${counts.artifacts} artifacts`,
    },
    {
      description: 'Review flashcards, quizzes, and application scenarios.',
      label: 'QnGen',
      path: '/app/qngen',
      status: `${counts.flashcards} flashcards`,
    },
  ]

  return (
    <>
      <PageHeader eyebrow="Command Overview" title="BriefWorks Workspace">
        Monitor sources, production runs, and generated outputs for the active workspace.
      </PageHeader>

      <section className="metric-grid" aria-label="Workspace metrics">
        <div className="metric-card">
          <p className="metric-card__label">Sources</p>
          <p className="metric-card__value">{counts.sources}</p>
        </div>
        <div className="metric-card">
          <p className="metric-card__label">Wiki entries</p>
          <p className="metric-card__value">{counts.wiki}</p>
        </div>
        <div className="metric-card">
          <p className="metric-card__label">Artifacts</p>
          <p className="metric-card__value">{counts.artifacts}</p>
        </div>
        <div className="metric-card">
          <p className="metric-card__label">Production runs</p>
          <p className="metric-card__value">{counts.runs}</p>
        </div>
      </section>

      <section className="module-grid" aria-label="BriefWorks modules">
        {moduleCards.map((module) => (
          <Link className="module-card" to={module.path} key={module.label}>
            <p className="module-card__status">{module.status}</p>
            <h3>{module.label}</h3>
            <p>{module.description}</p>
          </Link>
        ))}
      </section>
    </>
  )
}

export function ProjectsPage() {
  const workspaceId = useWorkspaceId()
  const [runs, setRuns] = useState<ProductionRun[]>([])
  const [sources, setSources] = useState<Source[]>([])
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const [skillRuns, setSkillRuns] = useState<SkillRun[]>([])
  const [selectedSkillRun, setSelectedSkillRun] = useState<SkillRun | null>(null)
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([])
  const [selectedTargets, setSelectedTargets] = useState<string[]>(['eleven_reader_script'])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const selectedRun = useMemo(
    () => runs.find((run) => run.id === selectedRunId) ?? runs[0] ?? null,
    [runs, selectedRunId],
  )

  async function refreshRuns() {
    if (!workspaceId) {
      return
    }

    const [runRows, sourceRows] = await Promise.all([
      listProductionRuns(workspaceId),
      listSources(workspaceId),
    ])
    setRuns(runRows)
    setSources(sourceRows)

    if (!selectedRunId && runRows[0]) {
      setSelectedRunId(runRows[0].id)
    }
  }

  useEffect(() => {
    void refreshRuns()
  }, [workspaceId])

  useEffect(() => {
    if (!selectedRun) {
      setSkillRuns([])
      return
    }

    void listSkillRuns(selectedRun.id).then(setSkillRuns)
  }, [selectedRun?.id])

  useEffect(() => {
    if (!workspaceId || !selectedRun || !['queued', 'running'].includes(selectedRun.status)) {
      return
    }

    const interval = window.setInterval(() => {
      void getProductionRun(selectedRun.id).then((run) => {
        setRuns((current) => current.map((row) => (row.id === run.id ? run : row)))
      })
    }, 4000)

    return () => window.clearInterval(interval)
  }, [workspaceId, selectedRun?.id, selectedRun?.status])

  return (
    <>
      <PageHeader eyebrow="Production" title="Production Runs">
        Queue ingest and generation pipelines for selected sources and target artifacts.
      </PageHeader>

      <div className="split-layout">
        <section className="data-panel">
          <div className="data-panel__head">
            <h3>Runs</h3>
            <button type="button" className="button-secondary" onClick={() => void refreshRuns()}>
              Refresh
            </button>
          </div>

          {runs.length === 0 ? (
            <p className="data-panel__empty">No production runs yet.</p>
          ) : (
            <ul className="data-list">
              {runs.map((run) => (
                <li key={run.id}>
                  <button
                    type="button"
                    className={`data-list__item${selectedRun?.id === run.id ? ' is-active' : ''}`}
                    onClick={() => setSelectedRunId(run.id)}
                  >
                    <span className="data-list__title">{run.id.slice(0, 8)}</span>
                    <span className="data-list__meta">
                      <StatusBadge status={run.status} /> · {formatDate(run.created_at)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="data-panel">
          {selectedRun ? (
            <>
              <div className="data-panel__head">
                <h3>Run detail</h3>
                <StatusBadge status={selectedRun.status} />
              </div>

              {selectedRun.error ? <p className="field-error">{selectedRun.error}</p> : null}

              <div className="pipeline-steps">
                {selectedRun.pipeline.map((step) => (
                  <div className="pipeline-step" key={step.step}>
                    <span className={`pipeline-step__dot pipeline-step__dot--${step.status}`} />
                    <div>
                      <p className="pipeline-step__name">{step.step}</p>
                      <p className="pipeline-step__meta">
                        {step.type}
                        {step.detail ? ` · ${step.detail}` : ''}
                      </p>
                    </div>
                    <StatusBadge status={step.status} />
                  </div>
                ))}
              </div>

              <h4 className="section-title">Skill runs</h4>
              {skillRuns.length === 0 ? (
                <p className="data-panel__empty">No skill runs recorded yet.</p>
              ) : (
                <ul className="data-list">
                  {skillRuns.map((skillRun) => (
                    <li key={skillRun.id}>
                      <button
                        type="button"
                        className={`data-list__item${
                          selectedSkillRun?.id === skillRun.id ? ' is-active' : ''
                        }`}
                        onClick={() => {
                          void getSkillRun(skillRun.id).then(setSelectedSkillRun)
                        }}
                      >
                        <span className="data-list__title">{skillRun.skill_id}</span>
                        <span className="data-list__meta">
                          <StatusBadge status={skillRun.status} />
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}

              {selectedSkillRun ? (
                <pre className="code-block">{JSON.stringify(selectedSkillRun.output, null, 2)}</pre>
              ) : null}
            </>
          ) : (
            <p className="data-panel__empty">Select a production run to inspect pipeline progress.</p>
          )}
        </section>
      </div>

      <section className="data-panel data-panel--form">
        <h3>Start new run</h3>

        <div className="checkbox-grid">
          <p className="field-label">Sources</p>
          {sources.map((source) => (
            <label className="checkbox-row" key={source.id}>
              <input
                type="checkbox"
                checked={selectedSourceIds.includes(source.id)}
                onChange={(event) => {
                  setSelectedSourceIds((current) =>
                    event.target.checked
                      ? [...current, source.id]
                      : current.filter((id) => id !== source.id),
                  )
                }}
              />
              <span>
                {source.filename} <StatusBadge status={source.status} />
              </span>
            </label>
          ))}
        </div>

        <div className="checkbox-grid">
          <p className="field-label">Target artifacts</p>
          {TARGET_ARTIFACT_OPTIONS.map((option) => (
            <label className="checkbox-row" key={option.value}>
              <input
                type="checkbox"
                checked={selectedTargets.includes(option.value)}
                onChange={(event) => {
                  setSelectedTargets((current) =>
                    event.target.checked
                      ? [...current, option.value]
                      : current.filter((value) => value !== option.value),
                  )
                }}
              />
              <span>{option.label}</span>
            </label>
          ))}
        </div>

        {error ? <p className="field-error">{error}</p> : null}

        <button
          type="button"
          className="button-primary"
          disabled={isSubmitting || !workspaceId || selectedSourceIds.length === 0}
          onClick={async () => {
            if (!workspaceId) {
              return
            }

            setIsSubmitting(true)
            setError(null)

            try {
              const run = await createProductionRun(workspaceId, {
                source_ids: selectedSourceIds,
                target_artifacts: selectedTargets,
              })
              setSelectedRunId(run.id)
              await refreshRuns()
            } catch (submitError) {
              setError(
                submitError instanceof Error ? submitError.message : 'Could not start production run.',
              )
            } finally {
              setIsSubmitting(false)
            }
          }}
        >
          {isSubmitting ? 'Queueing…' : 'Queue production run'}
        </button>
      </section>
    </>
  )
}

export function SourcesPage() {
  const workspaceId = useWorkspaceId()
  const [sources, setSources] = useState<Source[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function refreshSources() {
    if (!workspaceId) {
      return
    }

    setSources(await listSources(workspaceId))
  }

  useEffect(() => {
    void refreshSources()
  }, [workspaceId])

  return (
    <>
      <PageHeader eyebrow="Sources" title="Trusted Source Library">
        Upload PDF sources and track ingest status before running production pipelines.
      </PageHeader>

      <section className="data-panel data-panel--form">
        <label className="button-primary file-upload" htmlFor="source-upload">
          {isUploading ? 'Uploading…' : 'Upload source PDF'}
        </label>
        <input
          id="source-upload"
          type="file"
          accept="application/pdf,.pdf"
          hidden
          disabled={isUploading || !workspaceId}
          onChange={async (event) => {
            const file = event.target.files?.[0]
            if (!file || !workspaceId) {
              return
            }

            setIsUploading(true)
            setError(null)

            try {
              await uploadSource(workspaceId, file)
              await refreshSources()
            } catch (uploadError) {
              setError(uploadError instanceof Error ? uploadError.message : 'Upload failed.')
            } finally {
              setIsUploading(false)
              event.target.value = ''
            }
          }}
        />
        {error ? <p className="field-error">{error}</p> : null}
      </section>

      <section className="data-panel">
        <div className="data-panel__head">
          <h3>Sources</h3>
          <button type="button" className="button-secondary" onClick={() => void refreshSources()}>
            Refresh
          </button>
        </div>

        {sources.length === 0 ? (
          <p className="data-panel__empty">No sources uploaded yet.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Filename</th>
                <th>Status</th>
                <th>Size</th>
                <th>Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((source) => (
                <tr key={source.id}>
                  <td>{source.filename}</td>
                  <td>
                    <StatusBadge status={source.status} />
                  </td>
                  <td>{formatBytes(source.file_size_bytes)}</td>
                  <td>{formatDate(source.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </>
  )
}

export function IntellexPage() {
  const workspaceId = useWorkspaceId()
  const [search, setSearch] = useState('')
  const [entries, setEntries] = useState<WikiEntry[]>([])
  const [disputeCount, setDisputeCount] = useState(0)

  useEffect(() => {
    if (!workspaceId) {
      return
    }

    void Promise.all([
      listWikiEntries(workspaceId, search || undefined),
      listWikiDisputes(workspaceId),
    ]).then(([wikiRows, disputeRows]) => {
      setEntries(wikiRows)
      setDisputeCount(disputeRows.length)
    })
  }, [workspaceId, search])

  return (
    <>
      <PageHeader eyebrow="Intellex" title="Knowledge Base">
        Search canonical wiki entries promoted from document deconstruction.
      </PageHeader>

      <section className="data-panel data-panel--form">
        <label className="field-label" htmlFor="wiki-search">
          Search wiki
        </label>
        <input
          id="wiki-search"
          className="field-input"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search terms and definitions"
        />
        <p className="data-panel__meta">{disputeCount} open disputes logged</p>
      </section>

      <section className="data-panel">
        {entries.length === 0 ? (
          <p className="data-panel__empty">No wiki entries yet. Run a production pipeline first.</p>
        ) : (
          <ul className="wiki-list">
            {entries.map((entry) => (
              <li className="wiki-list__item" key={entry.id}>
                <div className="wiki-list__head">
                  <h3>{entry.preferred_label}</h3>
                  <StatusBadge status={entry.status} />
                </div>
                <p>{entry.definition}</p>
                {entry.aliases.length > 0 ? (
                  <p className="wiki-list__aliases">Aliases: {entry.aliases.join(', ')}</p>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  )
}

export function MathesysPage() {
  const workspaceId = useWorkspaceId()
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!workspaceId) {
      return
    }

    void listArtifacts(workspaceId).then(setArtifacts)
  }, [workspaceId])

  return (
    <>
      <PageHeader eyebrow="Mathesys" title="Generated Artifacts">
        Download ElevenReader-ready EPUB scripts produced by production runs.
      </PageHeader>

      <section className="data-panel">
        {artifacts.length === 0 ? (
          <p className="data-panel__empty">No artifacts yet. Queue a run with ElevenReader EPUB selected.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Filename</th>
                <th>Type</th>
                <th>Size</th>
                <th>Created</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {artifacts.map((artifact) => (
                <tr key={artifact.id}>
                  <td>{artifact.filename}</td>
                  <td>{artifact.artifact_type}</td>
                  <td>{formatBytes(artifact.file_size_bytes)}</td>
                  <td>{formatDate(artifact.created_at)}</td>
                  <td>
                    <button
                      type="button"
                      className="button-secondary"
                      onClick={async () => {
                        setError(null)

                        try {
                          const { download_url } = await getArtifactDownloadUrl(artifact.id)
                          window.open(download_url, '_blank', 'noopener,noreferrer')
                        } catch (downloadError) {
                          setError(
                            downloadError instanceof Error
                              ? downloadError.message
                              : 'Download failed.',
                          )
                        }
                      }}
                    >
                      Download
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {error ? <p className="field-error">{error}</p> : null}
      </section>
    </>
  )
}

type AssessmentTab = 'flashcards' | 'quizzes' | 'scenarios'

export function QnGenPage() {
  const workspaceId = useWorkspaceId()
  const [tab, setTab] = useState<AssessmentTab>('flashcards')
  const [flashcards, setFlashcards] = useState<Flashcard[]>([])
  const [quizzes, setQuizzes] = useState<Quiz[]>([])
  const [scenarios, setScenarios] = useState<Scenario[]>([])

  useEffect(() => {
    if (!workspaceId) {
      return
    }

    void Promise.all([
      listFlashcards(workspaceId),
      listQuizzes(workspaceId),
      listScenarios(workspaceId),
    ]).then(([flashcardRows, quizRows, scenarioRows]) => {
      setFlashcards(flashcardRows)
      setQuizzes(quizRows)
      setScenarios(scenarioRows)
    })
  }, [workspaceId])

  return (
    <>
      <PageHeader eyebrow="QnGen" title="Assessment Bank">
        Browse flashcards, quizzes, and scenarios promoted from QnGen skills.
      </PageHeader>

      <div className="tab-row">
        {(['flashcards', 'quizzes', 'scenarios'] as AssessmentTab[]).map((value) => (
          <button
            key={value}
            type="button"
            className={`tab-row__button${tab === value ? ' is-active' : ''}`}
            onClick={() => setTab(value)}
          >
            {value}
          </button>
        ))}
      </div>

      <section className="data-panel">
        {tab === 'flashcards' ? (
          flashcards.length === 0 ? (
            <p className="data-panel__empty">No flashcards yet.</p>
          ) : (
            <ul className="wiki-list">
              {flashcards.map((card) => (
                <li className="wiki-list__item" key={card.id}>
                  <div className="wiki-list__head">
                    <h3>{card.front}</h3>
                    <StatusBadge status={card.difficulty} />
                  </div>
                  <p>{card.back}</p>
                </li>
              ))}
            </ul>
          )
        ) : null}

        {tab === 'quizzes' ? (
          quizzes.length === 0 ? (
            <p className="data-panel__empty">No quiz questions yet.</p>
          ) : (
            <ul className="wiki-list">
              {quizzes.map((quiz) => (
                <li className="wiki-list__item" key={quiz.id}>
                  <div className="wiki-list__head">
                    <h3>{quiz.question}</h3>
                    <StatusBadge status={quiz.difficulty} />
                  </div>
                  {quiz.options.length > 0 ? (
                    <ul>
                      {quiz.options.map((option) => (
                        <li key={option}>{option}</li>
                      ))}
                    </ul>
                  ) : null}
                  <p>
                    <strong>Answer:</strong> {quiz.correct_answer}
                  </p>
                  {quiz.explanation ? <p>{quiz.explanation}</p> : null}
                </li>
              ))}
            </ul>
          )
        ) : null}

        {tab === 'scenarios' ? (
          scenarios.length === 0 ? (
            <p className="data-panel__empty">No scenarios yet.</p>
          ) : (
            <ul className="wiki-list">
              {scenarios.map((scenario) => (
                <li className="wiki-list__item" key={scenario.id}>
                  <div className="wiki-list__head">
                    <h3>{scenario.title}</h3>
                    <StatusBadge status={scenario.difficulty} />
                  </div>
                  <p>{scenario.prompt}</p>
                  {scenario.context ? <p>{scenario.context}</p> : null}
                </li>
              ))}
            </ul>
          )
        ) : null}
      </section>
    </>
  )
}
