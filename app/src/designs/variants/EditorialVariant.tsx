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
  type PipelineRun,
} from '../mockData'

type EditorialPage = 'review' | 'sources' | 'library'

const pages: { id: EditorialPage; label: string }[] = [
  { id: 'review', label: 'The Review' },
  { id: 'sources', label: 'Sources' },
  { id: 'library', label: 'Library' },
]

const today = new Date().toLocaleDateString('en-US', {
  weekday: 'long',
  month: 'long',
  day: 'numeric',
  year: 'numeric',
})

export function EditorialVariant() {
  const [page, setPage] = useState<EditorialPage>('review')
  const [openRun, setOpenRun] = useState<PipelineRun | null>(null)

  function selectPage(next: EditorialPage) {
    setPage(next)
    setOpenRun(null)
  }

  return (
    <div className="bw-editorial">
      <div className="bw-editorial__wrap">
        <div className="bw-editorial__masthead">
          <h1>BriefWorks</h1>
          <div className="date">
            USMC Doctrine Lab
            <br />
            {today}
          </div>
        </div>
        <div className="bw-editorial__rule" />

        <nav className="bw-editorial__pagenav">
          {pages.map((item) => (
            <button
              key={item.id}
              className={page === item.id ? 'is-active' : ''}
              onClick={() => selectPage(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>

        {page === 'review' && !openRun ? <EditorialReview onOpen={setOpenRun} /> : null}
        {page === 'review' && openRun ? (
          <EditorialArticle run={openRun} onBack={() => setOpenRun(null)} />
        ) : null}
        {page === 'sources' ? <EditorialSources /> : null}
        {page === 'library' ? <EditorialLibrary /> : null}
      </div>
    </div>
  )
}

function EditorialReview({ onOpen }: { onOpen: (run: PipelineRun) => void }) {
  return (
    <>
      <p className="bw-editorial__lede">
        A standing record of every production run in the workspace — what was built, from which doctrine, and how
        much it cost to generate. Select an edition to read the full breakdown.
      </p>

      <div className="bw-editorial__stats">
        {metrics.map((metric) => (
          <div className="bw-editorial__stat" key={metric.label}>
            <div className="v">{metric.value}</div>
            <div className="l">{metric.label}</div>
            <div className={`d bw-${metric.trend}`}>{metric.delta}</div>
          </div>
        ))}
      </div>

      <div className="bw-editorial__section-title">Latest editions</div>
      {pipelineRuns.map((run, index) => (
        <button className="bw-editorial__run" key={run.id} onClick={() => onOpen(run)}>
          <span className="num">{String(index + 1).padStart(2, '0')}</span>
          <span>
            <h3>{run.label}</h3>
            <span className="byline">
              <span>{run.sourceTitles.join(', ')}</span>
              <span>{run.skillRuns.length} skill runs</span>
              <span>{formatDuration(run.durationSec)}</span>
              <span>{formatDate(run.createdAt)}</span>
            </span>
          </span>
          <span className="status-col">
            <span className={`bw-editorial__statusword is-${run.status}`}>
              <span className={`bw-dot bw-dot--${run.status}`} />
              {statusLabel(run.status)}
            </span>
          </span>
        </button>
      ))}
    </>
  )
}

function EditorialArticle({ run, onBack }: { onBack: () => void; run: PipelineRun }) {
  const runArtifacts = artifacts.filter((artifact) =>
    run.skillRuns.some((skill) => skill.artifactIds.includes(artifact.id)),
  )
  const totalConcepts = run.skillRuns.reduce((sum, skill) => sum + skill.conceptCount, 0)

  return (
    <article className="bw-editorial__article">
      <button className="bw-editorial__back" onClick={onBack}>
        ← Back to the review
      </button>
      <h2>{run.label}</h2>
      <div className="bw-editorial__deck">
        <span>{statusLabel(run.status)}</span>
        <span>{run.sourceTitles.join(', ')}</span>
        <span>{formatDuration(run.durationSec)}</span>
        <span>Target — {run.targetArtifacts.map((kind) => artifactKindLabels[kind]).join(', ')}</span>
      </div>

      {run.error ? (
        <p style={{ color: 'var(--color-dark-scarlet)', fontWeight: 600, marginBottom: 'var(--space-5)' }}>
          This run did not complete. {run.error}
        </p>
      ) : null}

      <div className="bw-editorial__section-title">The pipeline, step by step</div>
      {run.skillRuns.map((skill) => (
        <div className="bw-editorial__skill" key={skill.id}>
          <div className="head">
            <h4>{skill.skillName}</h4>
            <span className="mod">{moduleLabels[skill.module]}</span>
            <span className={`bw-editorial__statusword is-${skill.status}`} style={{ marginLeft: 'auto' }}>
              <span className={`bw-dot bw-dot--${skill.status}`} />
              {statusLabel(skill.status)}
            </span>
          </div>
          <p>{skill.outputSummary}</p>
          <div className="stats">
            <span>{skill.model}</span>
            <span>{formatDuration(skill.durationSec)}</span>
            <span>{((skill.tokensIn + skill.tokensOut) / 1000).toFixed(1)}K tokens</span>
            {skill.conceptCount ? <span>{skill.conceptCount} concepts extracted</span> : null}
          </div>
        </div>
      ))}

      {runArtifacts.length ? (
        <>
          <div className="bw-editorial__section-title" style={{ marginTop: 'var(--space-7)' }}>
            What it produced
          </div>
          <div className="bw-editorial__library">
            {runArtifacts.map((artifact) => (
              <div className="bw-editorial__pub" key={artifact.id}>
                <div className="bw-editorial__pub-cover">
                  <span className="kind">{artifactKindLabels[artifact.kind]}</span>
                  <span className="fmt">{artifact.format}</span>
                </div>
                <div className="bw-editorial__pub-body">
                  <h4>{artifact.title}</h4>
                  <div className="ft">
                    <span>{artifact.sizeLabel}</span>
                    <span>{statusLabel(artifact.status)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      ) : null}

      {totalConcepts > 0 ? (
        <>
          <div className="bw-editorial__section-title" style={{ marginTop: 'var(--space-7)' }}>
            Key terms &amp; concepts · {totalConcepts}
          </div>
          <dl className="bw-editorial__concepts">
            {concepts.map((concept) => (
              <div className="bw-editorial__concept" key={concept.term}>
                <dt>
                  {concept.term}
                  <span className={`imp imp--${concept.importance}`}>{concept.importance}</span>
                </dt>
                <dd>{concept.definition}</dd>
              </div>
            ))}
          </dl>
        </>
      ) : null}
    </article>
  )
}

function EditorialSources() {
  const [query, setQuery] = useState('')
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
      <p className="bw-editorial__lede">
        The trusted reading list. Every raw source vetted before it enters the pipeline, with parse confidence and
        coverage at a glance.
      </p>
      <div className="bw-editorial__searchline">
        <span style={{ color: 'var(--color-light-gray)', fontSize: '1.4rem' }}>⌕</span>
        <input
          placeholder="Search the source library…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </div>
      <div className="bw-editorial__section-title">{filtered.length} sources</div>
      {filtered.map((source) => (
        <div className="bw-editorial__source" key={source.id}>
          <div>
            <h3>{source.title}</h3>
            <div className="meta">
              <span>{source.documentType}</span>
              <span>{source.issuingAuthority}</span>
              <span>
                {source.mimeLabel} · {source.sizeLabel} · {source.pages} pp
              </span>
              <span>
                <span className={`bw-dot bw-dot--${source.status}`} /> {statusLabel(source.status)}
              </span>
            </div>
            <div className="tags">
              {source.tags.map((tag) => (
                <span className="bw-editorial__tag" key={tag}>
                  {tag}
                </span>
              ))}
            </div>
          </div>
          <div className="conf">
            <div className="v">{Math.round(source.confidence * 100)}%</div>
            <div className="l">Confidence</div>
          </div>
        </div>
      ))}
    </>
  )
}

function EditorialLibrary() {
  return (
    <>
      <div className="bw-editorial__generate">
        <div className="txt">
          <h3>Generate a new artifact</h3>
          <p>Select approved sources, choose a target — listenable brief, lesson, assessment, or concept map — and queue a production run.</p>
        </div>
        <button className="bw-editorial__genbtn">Start production</button>
      </div>

      <div className="bw-editorial__section-title">Published artifacts</div>
      <div className="bw-editorial__library">
        {artifacts.map((artifact) => (
          <button className="bw-editorial__pub" key={artifact.id}>
            <div className="bw-editorial__pub-cover">
              <span className="kind">{artifactKindLabels[artifact.kind]}</span>
              <span className="fmt">{artifact.format}</span>
            </div>
            <div className="bw-editorial__pub-body">
              <h4>{artifact.title}</h4>
              <p>{artifact.summary}</p>
              <div className="ft">
                <span>{moduleLabels[artifact.module]}</span>
                <span>{formatDate(artifact.createdAt)}</span>
              </div>
            </div>
          </button>
        ))}
      </div>
    </>
  )
}
