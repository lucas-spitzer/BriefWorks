import { useMemo, useState } from 'react'
import {
  artifactKindLabels,
  artifacts,
  concepts,
  formatDate,
  formatDateTime,
  formatDuration,
  metrics,
  moduleLabels,
  pipelineRuns,
  sources,
  statusLabel,
  type PipelineRun,
} from '../mockData'

type ConsolePage = 'ops' | 'sources' | 'artifacts'
type ConsoleView = 'grid' | 'list'

const railItems: { id: ConsolePage; label: string; icon: string }[] = [
  { id: 'ops', label: 'OPS', icon: '▥' },
  { id: 'sources', label: 'SRC', icon: '▤' },
  { id: 'artifacts', label: 'ART', icon: '◆' },
]

function ConsoleViewToggle({ view, onChange }: { onChange: (view: ConsoleView) => void; view: ConsoleView }) {
  return (
    <div className="bw-console__viewtoggle">
      <button
        className={`bw-console__viewbtn${view === 'grid' ? ' is-active' : ''}`}
        onClick={() => onChange('grid')}
        aria-label="Item view"
        aria-pressed={view === 'grid'}
      >
        ▦
      </button>
      <button
        className={`bw-console__viewbtn${view === 'list' ? ' is-active' : ''}`}
        onClick={() => onChange('list')}
        aria-label="List view"
        aria-pressed={view === 'list'}
      >
        ☰
      </button>
    </div>
  )
}

export function ConsoleVariant() {
  const [page, setPage] = useState<ConsolePage>('ops')

  return (
    <div className="bw-console">
      <nav className="bw-console__rail">
        <div className="bw-console__rail-mark">BW</div>
        {railItems.map((item) => (
          <button
            key={item.id}
            className={`bw-console__rail-btn${page === item.id ? ' is-active' : ''}`}
            onClick={() => setPage(item.id)}
          >
            <span style={{ fontSize: '1rem' }}>{item.icon}</span>
            {item.label}
          </button>
        ))}
      </nav>

      <div className="bw-console__main">
        {page === 'ops' ? <ConsoleOps /> : null}
        {page === 'sources' ? <ConsoleSources /> : null}
        {page === 'artifacts' ? <ConsoleArtifacts /> : null}
      </div>
    </div>
  )
}

function ConsoleOps() {
  const [activeId, setActiveId] = useState<string>(pipelineRuns[1].id)
  const active = pipelineRuns.find((run) => run.id === activeId) ?? pipelineRuns[0]

  return (
    <>
      <header className="bw-console__header">
        <div>
          <div className="bw-console__eyebrow">Mission Control</div>
          <h2>Production Operations</h2>
        </div>
        <span className="bw-console__live">
          <span className="bw-live-dot" /> Live · 1 run active
        </span>
        <button className="bw-console__cta">+ New run</button>
      </header>

      <div className="bw-console__scroll">
        <div className="bw-console__metrics">
          {metrics.map((metric) => (
            <div className="bw-console__metric" key={metric.label}>
              <div className="l">{metric.label}</div>
              <div className="v">{metric.value}</div>
              <div className={`d bw-${metric.trend}`}>{metric.delta} vs last week</div>
            </div>
          ))}
        </div>

        <div className="bw-console__split">
          <section className="bw-console__panel">
            <div className="bw-console__panel-head">
              <h3>Pipeline runs</h3>
              <span className="bw-count">{pipelineRuns.length}</span>
            </div>
            {pipelineRuns.map((run) => (
              <button
                key={run.id}
                className={`bw-console__runrow${run.id === activeId ? ' is-active' : ''}`}
                onClick={() => setActiveId(run.id)}
              >
                <span className={`bw-dot bw-dot--${run.status}`} />
                <span>
                  <div className="title">{run.label}</div>
                  <div className="sub">
                    {run.id.toUpperCase()} · {run.skillRuns.length} skill runs · {formatDateTime(run.createdAt)}
                  </div>
                  {run.status === 'running' ? (
                    <div className="bw-console__progress">
                      <span style={{ width: `${run.progress}%` }} />
                    </div>
                  ) : null}
                </span>
                <span className="right">
                  <span className={`bw-console__statepill bw-state--${run.status}`}>{statusLabel(run.status)}</span>
                </span>
              </button>
            ))}
          </section>

          <ConsoleDetail run={active} />
        </div>
      </div>
    </>
  )
}

function ConsoleDetail({ run }: { run: PipelineRun }) {
  const runArtifacts = artifacts.filter((artifact) =>
    run.skillRuns.some((skill) => skill.artifactIds.includes(artifact.id)),
  )
  const totalConcepts = run.skillRuns.reduce((sum, skill) => sum + skill.conceptCount, 0)

  return (
    <section className="bw-console__panel">
      <div className="bw-console__panel-head">
        <h3>Run detail</h3>
        <span className="bw-count">{run.id.toUpperCase()}</span>
      </div>
      <div className="bw-console__detail">
        <h4>{run.label}</h4>
        <div className="meta">
          {statusLabel(run.status)} · {formatDuration(run.durationSec)} · target{' '}
          {run.targetArtifacts.map((kind) => artifactKindLabels[kind]).join(', ')}
        </div>

        {run.error ? (
          <div className="bw-console__chip" style={{ borderColor: 'var(--color-scarlet)', color: '#ff8b8b', background: 'rgba(148,0,0,0.16)', marginTop: 14 }}>
            ⚠ {run.error}
          </div>
        ) : null}

        <div style={{ height: 18 }} />

        {run.skillRuns.map((skill) => (
          <div className="bw-console__step" key={skill.id}>
            <span className={`bw-console__step-dot bw-console__step-dot--${skill.status}`}>
              {skill.status === 'completed' ? '✓' : skill.status === 'failed' ? '✕' : '•'}
            </span>
            <div className="bw-console__step-body">
              <div className="name">
                {skill.skillName} <span className="bw-console__module-tag">{moduleLabels[skill.module]}</span>
              </div>
              <div className="desc">{skill.outputSummary}</div>
              <div className="stats">
                <span>{skill.model}</span>
                <span>{formatDuration(skill.durationSec)}</span>
                <span>{((skill.tokensIn + skill.tokensOut) / 1000).toFixed(1)}K tok</span>
                {skill.conceptCount ? <span>{skill.conceptCount} concepts</span> : null}
              </div>
            </div>
          </div>
        ))}

        {runArtifacts.length ? (
          <>
            <div className="bw-console__panel-head" style={{ padding: '4px 0', borderBottom: 0 }}>
              <h3 style={{ fontSize: '0.86rem' }}>Artifacts</h3>
            </div>
            {runArtifacts.map((artifact) => (
              <div className="bw-console__artifact" key={artifact.id}>
                <span className="ic">{artifact.format}</span>
                <span>
                  <div className="t">{artifact.title}</div>
                  <div className="s">
                    {artifactKindLabels[artifact.kind]} · {artifact.sizeLabel}
                  </div>
                </span>
              </div>
            ))}
          </>
        ) : null}

        {totalConcepts > 0 ? (
          <>
            <div className="bw-console__panel-head" style={{ padding: '14px 0 4px', borderBottom: 0 }}>
              <h3 style={{ fontSize: '0.86rem' }}>Key terms · {totalConcepts}</h3>
            </div>
            <div className="bw-console__chips">
              {concepts.slice(0, totalConcepts > 8 ? 8 : totalConcepts).map((concept) => (
                <span className="bw-console__chip" key={concept.term}>
                  {concept.term}
                </span>
              ))}
            </div>
          </>
        ) : null}
      </div>
    </section>
  )
}

function ConsoleSources() {
  const [query, setQuery] = useState('')
  const [view, setView] = useState<ConsoleView>('grid')
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
      <header className="bw-console__header">
        <div>
          <div className="bw-console__eyebrow">Knowledge Base</div>
          <h2>Source Intelligence</h2>
        </div>
        <ConsoleViewToggle view={view} onChange={setView} />
        <button className="bw-console__cta bw-console__cta--ghost">⇪ Upload source</button>
      </header>
      <div className="bw-console__scroll">
        <div className="bw-console__searchbar">
          <span style={{ color: '#6f828b' }}>⌕</span>
          <input
            placeholder="Search raw source files by title, authority, or tag…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <span className="bw-count">{filtered.length} files</span>
        </div>
        {view === 'list' ? (
          <section className="bw-console__panel">
            <table className="bw-console__table">
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Type</th>
                  <th>Format</th>
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
                      <div className="bw-console__listname">
                        <span>
                          <div className="t">{source.title}</div>
                          <div className="s">{source.issuingAuthority}</div>
                        </span>
                      </div>
                    </td>
                    <td>{source.documentType}</td>
                    <td className="num">{source.mimeLabel}</td>
                    <td>
                      <span className={`bw-console__statepill bw-state--${source.status}`}>
                        {statusLabel(source.status)}
                      </span>
                    </td>
                    <td className="num">{source.pages}</td>
                    <td className="num">{source.segments}</td>
                    <td className="num">{Math.round(source.confidence * 100)}%</td>
                    <td className="num">{formatDate(source.uploadedAt)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        ) : (
        <div className="bw-console__sources">
          {filtered.map((source) => (
            <div className="bw-console__panel bw-console__source-card" key={source.id} style={{ padding: 18 }}>
              <div>
                <div style={{ fontFamily: 'var(--bw-grotesk)', fontSize: '1.1rem', fontWeight: 600, color: '#fff' }}>
                  {source.title}
                </div>
                <div style={{ fontSize: '0.8rem', color: '#9fb2bb', marginTop: 6 }}>
                  {source.documentType} · {source.issuingAuthority}
                </div>
              </div>
              <div className="bw-console__step-body">
                <div className="stats" style={{ marginTop: 12 }}>
                  <span>{source.pages} pages</span>
                  <span>{source.segments} segments</span>
                  <span>conf {Math.round(source.confidence * 100)}%</span>
                </div>
              </div>
              <div className="bw-console__chips" style={{ marginTop: 12, marginBottom: 10 }}>
                {source.tags.map((tag) => (
                  <span className="bw-console__chip" key={tag} style={{ fontSize: '0.7rem' }}>
                    {tag}
                  </span>
                ))}
              </div>
              <div className="bw-console__artifact-foot">
                <span className="seg">{source.sizeLabel}</span>
                <span className="seg">{source.mimeLabel}</span>
                <span className="seg">
                  <span className={`bw-console__statepill bw-state--${source.status}`}>
                    {statusLabel(source.status)}
                  </span>
                </span>
              </div>
            </div>
          ))}
        </div>
        )}
      </div>
    </>
  )
}

function ConsoleArtifacts() {
  const [view, setView] = useState<ConsoleView>('grid')

  return (
    <>
      <header className="bw-console__header">
        <div>
          <div className="bw-console__eyebrow">Output Registry</div>
          <h2>Generated Artifacts</h2>
        </div>
        <ConsoleViewToggle view={view} onChange={setView} />
        <button className="bw-console__cta">+ Generate artifact</button>
      </header>
      <div className="bw-console__scroll">
        {view === 'list' ? (
          <section className="bw-console__panel">
            <table className="bw-console__table">
              <thead>
                <tr>
                  <th>Artifact</th>
                  <th>Type</th>
                  <th>Module</th>
                  <th>Format</th>
                  <th>Status</th>
                  <th>Size</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {artifacts.map((artifact) => (
                  <tr key={artifact.id}>
                    <td>
                      <div className="bw-console__listname">
                        <span>
                          <div className="t">{artifact.title}</div>
                          <div className="s">{formatDate(artifact.createdAt)}</div>
                        </span>
                      </div>
                    </td>
                    <td>{artifactKindLabels[artifact.kind]}</td>
                    <td>{moduleLabels[artifact.module]}</td>
                    <td className="num">{artifact.format}</td>
                    <td>
                      <span className={`bw-console__statepill bw-state--${artifact.status}`}>
                        {statusLabel(artifact.status)}
                      </span>
                    </td>
                    <td className="num">{artifact.sizeLabel}</td>
                    <td>{artifact.sourceTitle}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        ) : (
        <div className="bw-console__sources">
          {artifacts.map((artifact) => (
            <div className="bw-console__panel bw-console__artifact-card" key={artifact.id} style={{ padding: 18 }}>
              <div>
                <div style={{ fontFamily: 'var(--bw-grotesk)', fontWeight: 600, color: '#fff' }}>{artifact.title}</div>
                <div style={{ fontFamily: 'var(--bw-mono)', fontSize: '0.7rem', color: '#8aa1ab', marginTop: 3 }}>
                  {artifactKindLabels[artifact.kind]} · {moduleLabels[artifact.module]}
                </div>
              </div>
              <p style={{ fontSize: '0.84rem', color: '#b6c4cb', marginTop: 12, lineHeight: 1.5 }}>{artifact.summary}</p>
              <div className="bw-console__artifact-foot">
                <span className="seg">{artifact.sizeLabel}</span>
                <span className="seg">{artifact.format}</span>
                <span className="seg">
                  <span className={`bw-console__statepill bw-state--${artifact.status}`}>
                    {statusLabel(artifact.status)}
                  </span>
                </span>
              </div>
            </div>
          ))}
        </div>
        )}
      </div>
    </>
  )
}
