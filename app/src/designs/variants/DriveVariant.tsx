import { useMemo, useState } from 'react'
import {
  artifactKindLabels,
  artifacts,
  concepts,
  formatDate,
  formatDuration,
  metrics,
  moduleLabels,
  pipelineRuns,
  sources,
  statusLabel,
  WORKSPACE_NAME,
  type PipelineRun,
} from '../mockData'

type DrivePage = 'runs' | 'sources' | 'artifacts'
type ViewMode = 'grid' | 'list'

const navItems: { id: DrivePage; label: string; icon: string }[] = [
  { id: 'runs', label: 'Pipeline Runs', icon: '⛭' },
  { id: 'sources', label: 'Sources', icon: '▤' },
  { id: 'artifacts', label: 'Artifacts', icon: '◆' },
]

export function DriveVariant() {
  const [page, setPage] = useState<DrivePage>('runs')
  const [view, setView] = useState<ViewMode>('grid')
  const [openRun, setOpenRun] = useState<PipelineRun | null>(null)
  const [query, setQuery] = useState('')

  const crumbRoot = navItems.find((n) => n.id === page)?.label ?? 'Pipeline Runs'

  function selectPage(next: DrivePage) {
    setPage(next)
    setOpenRun(null)
    setQuery('')
  }

  return (
    <div className="bw-drive">
      <aside className="bw-drive__nav">
        <button className="bw-drive__new">
          <span className="bw-plus">+</span> New production run
        </button>
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`bw-drive__navitem${page === item.id ? ' is-active' : ''}`}
            onClick={() => selectPage(item.id)}
          >
            <span className="bw-ico">{item.icon}</span>
            {item.label}
          </button>
        ))}
        <div className="bw-drive__storage">
          <div>Token budget</div>
          <div className="bw-drive__bar">
            <span style={{ width: '46%' }} />
          </div>
          4.6M of 10M used this week
        </div>
      </aside>

      <div className="bw-drive__main">
        <div className="bw-drive__topbar">
          <label className="bw-drive__search">
            <span>⌕</span>
            <input
              placeholder={`Search ${crumbRoot.toLowerCase()} in ${WORKSPACE_NAME}`}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          <div className="bw-drive__viewtoggle">
            <button
              className={`bw-drive__viewbtn${view === 'grid' ? ' is-active' : ''}`}
              onClick={() => setView('grid')}
              aria-label="Grid view"
            >
              ▦
            </button>
            <button
              className={`bw-drive__viewbtn${view === 'list' ? ' is-active' : ''}`}
              onClick={() => setView('list')}
              aria-label="List view"
            >
              ☰
            </button>
          </div>
        </div>

        <div className="bw-drive__crumbs">
          <button onClick={() => setOpenRun(null)} className={openRun ? '' : 'is-current'}>
            {crumbRoot}
          </button>
          {openRun ? (
            <>
              <span className="bw-crumb-sep">/</span>
              <span className="is-current">{openRun.label}</span>
            </>
          ) : null}
        </div>

        <div className="bw-drive__body">
          {page === 'runs' && !openRun ? (
            <DriveRuns view={view} query={query} onOpen={setOpenRun} />
          ) : null}
          {page === 'runs' && openRun ? <DriveRunDetail run={openRun} /> : null}
          {page === 'sources' ? <DriveSources view={view} query={query} /> : null}
          {page === 'artifacts' ? <DriveArtifacts view={view} query={query} /> : null}
        </div>
      </div>
    </div>
  )
}

function DriveRuns({
  view,
  query,
  onOpen,
}: {
  onOpen: (run: PipelineRun) => void
  query: string
  view: ViewMode
}) {
  const filtered = useMemo(
    () => pipelineRuns.filter((run) => run.label.toLowerCase().includes(query.toLowerCase())),
    [query],
  )

  return (
    <>
      <div className="bw-drive__metrics">
        {metrics.slice(0, 4).map((metric) => (
          <div className="bw-drive__metric" key={metric.label}>
            <div className="v">{metric.value}</div>
            <div className="l">{metric.label}</div>
            <div className={`d bw-${metric.trend}`}>{metric.delta}</div>
          </div>
        ))}
      </div>

      <p className="bw-drive__section-label">Folders · {filtered.length} runs</p>
      {view === 'grid' ? (
        <div className="bw-drive__grid">
          {filtered.map((run) => (
            <button className="bw-drive__card" key={run.id} onClick={() => onOpen(run)}>
              <div className="bw-drive__card-head">
                <span className="bw-ico bw-ico--folder">▣</span>
                <span>{run.label}</span>
              </div>
              <div className="bw-drive__thumb">
                <span>⛭</span>
                <span className="bw-thumb-tag">{run.skillRuns.length} SKILL RUNS</span>
              </div>
              <div className="bw-drive__card-meta">
                <span className={`bw-dot bw-dot--${run.status}`} />
                {statusLabel(run.status)} · {formatDate(run.createdAt)}
              </div>
            </button>
          ))}
        </div>
      ) : (
        <table className="bw-drive__table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Status</th>
              <th>Target</th>
              <th>Skill runs</th>
              <th>Created</th>
              <th>Duration</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((run) => (
              <tr key={run.id} onClick={() => onOpen(run)}>
                <td>
                  <div className="bw-drive__name-cell">
                    <span className="bw-ico bw-ico--folder">▣</span>
                    {run.label}
                  </div>
                </td>
                <td>
                  <span className="bw-pill">
                    <span className={`bw-dot bw-dot--${run.status}`} />
                    {statusLabel(run.status)}
                  </span>
                </td>
                <td>{run.targetArtifacts.map((kind) => artifactKindLabels[kind]).join(', ')}</td>
                <td>{run.skillRuns.length}</td>
                <td>{formatDate(run.createdAt)}</td>
                <td>{formatDuration(run.durationSec)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  )
}

function DriveRunDetail({ run }: { run: PipelineRun }) {
  const runArtifacts = artifacts.filter((artifact) =>
    run.skillRuns.some((skill) => skill.artifactIds.includes(artifact.id)),
  )
  const totalConcepts = run.skillRuns.reduce((sum, skill) => sum + skill.conceptCount, 0)

  return (
    <>
      {run.error ? (
        <div
          className="bw-pill"
          style={{
            background: '#f7e3e3',
            borderColor: 'var(--color-scarlet)',
            color: 'var(--color-dark-scarlet)',
            marginTop: 'var(--space-4)',
          }}
        >
          Run failed — {run.error}
        </div>
      ) : null}

      <p className="bw-drive__section-label">Skill runs</p>
      <table className="bw-drive__table">
        <thead>
          <tr>
            <th>Skill</th>
            <th>Module</th>
            <th>Status</th>
            <th>Model</th>
            <th>Duration</th>
            <th>Tokens</th>
            <th>Output</th>
          </tr>
        </thead>
        <tbody>
          {run.skillRuns.map((skill) => (
            <tr key={skill.id}>
              <td>
                <div className="bw-drive__name-cell">
                  <span className="bw-ico">⚙</span>
                  {skill.skillName}
                </div>
              </td>
              <td>{moduleLabels[skill.module]}</td>
              <td>
                <span className="bw-pill">
                  <span className={`bw-dot bw-dot--${skill.status}`} />
                  {statusLabel(skill.status)}
                </span>
              </td>
              <td>{skill.model}</td>
              <td>{formatDuration(skill.durationSec)}</td>
              <td>{((skill.tokensIn + skill.tokensOut) / 1000).toFixed(1)}K</td>
              <td>{skill.outputSummary}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {runArtifacts.length ? (
        <>
          <p className="bw-drive__section-label">Generated artifacts</p>
          <div className="bw-drive__grid">
            {runArtifacts.map((artifact) => (
              <div className="bw-drive__card" key={artifact.id}>
                <div className="bw-drive__card-head">
                  <span className="bw-ico">◆</span>
                  <span>{artifact.title}</span>
                </div>
                <div className="bw-drive__thumb">
                  <span>{artifact.format}</span>
                  <span className="bw-thumb-tag">{artifactKindLabels[artifact.kind]}</span>
                </div>
                <div className="bw-drive__card-meta">{artifact.sizeLabel} · {formatDate(artifact.createdAt)}</div>
              </div>
            ))}
          </div>
        </>
      ) : null}

      {totalConcepts > 0 ? (
        <>
          <p className="bw-drive__section-label">Key terms &amp; concepts · {totalConcepts} extracted</p>
          <div className="bw-drive__grid">
            {concepts.slice(0, 6).map((concept) => (
              <div className="bw-drive__card" key={concept.term} style={{ padding: 'var(--space-4)' }}>
                <div style={{ fontWeight: 600, marginBottom: 6 }}>{concept.term}</div>
                <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.45 }}>
                  {concept.definition}
                </div>
                <div className="bw-drive__card-meta" style={{ padding: '12px 0 0' }}>
                  <span className="bw-pill">{concept.importance}</span> {concept.citations} citations
                </div>
              </div>
            ))}
          </div>
        </>
      ) : null}
    </>
  )
}

function DriveSources({ view, query }: { query: string; view: ViewMode }) {
  const filtered = useMemo(
    () =>
      sources.filter(
        (source) =>
          source.title.toLowerCase().includes(query.toLowerCase()) ||
          source.tags.some((tag) => tag.includes(query.toLowerCase())),
      ),
    [query],
  )

  return (
    <>
      <p className="bw-drive__section-label">Source library · {filtered.length} files</p>
      {view === 'grid' ? (
        <div className="bw-drive__grid">
          {filtered.map((source) => (
            <button className="bw-drive__card" key={source.id}>
              <div className="bw-drive__card-head">
                <span className="bw-ico">▤</span>
                <span>{source.title}</span>
              </div>
              <div className="bw-drive__thumb">
                <span>{source.mimeLabel}</span>
                <span className="bw-thumb-tag">{source.pages} PAGES</span>
              </div>
              <div className="bw-drive__card-meta">
                <span className={`bw-dot bw-dot--${source.status}`} />
                {statusLabel(source.status)} · {source.sizeLabel}
              </div>
            </button>
          ))}
        </div>
      ) : (
        <table className="bw-drive__table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Status</th>
              <th>Pages</th>
              <th>Segments</th>
              <th>Confidence</th>
              <th>Uploaded</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((source) => (
              <tr key={source.id}>
                <td>
                  <div className="bw-drive__name-cell">
                    <span className="bw-ico">▤</span>
                    {source.filename}
                  </div>
                </td>
                <td>{source.documentType}</td>
                <td>
                  <span className="bw-pill">
                    <span className={`bw-dot bw-dot--${source.status}`} />
                    {statusLabel(source.status)}
                  </span>
                </td>
                <td>{source.pages}</td>
                <td>{source.segments}</td>
                <td>{Math.round(source.confidence * 100)}%</td>
                <td>{formatDate(source.uploadedAt)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  )
}

function DriveArtifacts({ view, query }: { query: string; view: ViewMode }) {
  const filtered = useMemo(
    () => artifacts.filter((artifact) => artifact.title.toLowerCase().includes(query.toLowerCase())),
    [query],
  )

  return (
    <>
      <p className="bw-drive__section-label">Generated artifacts · {filtered.length} items</p>
      {view === 'grid' ? (
        <div className="bw-drive__grid">
          {filtered.map((artifact) => (
            <button className="bw-drive__card" key={artifact.id}>
              <div className="bw-drive__card-head">
                <span className="bw-ico">◆</span>
                <span>{artifact.title}</span>
              </div>
              <div className="bw-drive__thumb">
                <span>{artifact.format}</span>
                <span className="bw-thumb-tag">{artifactKindLabels[artifact.kind]}</span>
              </div>
              <div className="bw-drive__card-meta">
                <span className={`bw-dot bw-dot--${artifact.status}`} />
                {moduleLabels[artifact.module]} · {artifact.sizeLabel}
              </div>
            </button>
          ))}
        </div>
      ) : (
        <table className="bw-drive__table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Kind</th>
              <th>Module</th>
              <th>Format</th>
              <th>Status</th>
              <th>Size</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((artifact) => (
              <tr key={artifact.id}>
                <td>
                  <div className="bw-drive__name-cell">
                    <span className="bw-ico">◆</span>
                    {artifact.title}
                  </div>
                </td>
                <td>{artifactKindLabels[artifact.kind]}</td>
                <td>{moduleLabels[artifact.module]}</td>
                <td>{artifact.format}</td>
                <td>
                  <span className="bw-pill">
                    <span className={`bw-dot bw-dot--${artifact.status}`} />
                    {statusLabel(artifact.status)}
                  </span>
                </td>
                <td>{artifact.sizeLabel}</td>
                <td>{formatDate(artifact.createdAt)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  )
}
