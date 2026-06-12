import { useMemo, useState } from 'react'
import { useWorkspaceData } from '../../features/workspace/workspaceDataContext'
import { artifactKindLabel, formatBytes, formatDate } from '../../lib/consoleFormat'
import { artifactModule, artifactSummary, sourceTitle } from '../../lib/consoleMappers'
import { ConsoleViewToggle } from './ConsoleViewToggle'
import { ErrorBanner } from './ErrorBanner'
import { moduleLabel } from './moduleLabel'
import type { ConsoleView } from './types'

export function ConsoleArtifacts() {
  const { sources, artifacts, isLoading, error, downloadArtifact } = useWorkspaceData()
  const [query, setQuery] = useState('')
  const [view, setView] = useState<ConsoleView>('grid')
  const [downloadError, setDownloadError] = useState<string | null>(null)

  const sourceById = useMemo(() => new Map(sources.map((s) => [s.id, s])), [sources])

  const filtered = useMemo(() => {
    const q = query.toLowerCase()
    return artifacts.filter((artifact) => {
      const source = artifact.source_id ? sourceById.get(artifact.source_id) : undefined
      const sourceName = source ? sourceTitle(source) : ''
      return (
        artifact.filename.toLowerCase().includes(q) ||
        sourceName.toLowerCase().includes(q) ||
        artifactKindLabel(artifact.artifact_type).toLowerCase().includes(q) ||
        moduleLabel(artifactModule(artifact)).toLowerCase().includes(q)
      )
    })
  }, [artifacts, query, sourceById])

  const handleDownload = async (artifactId: string) => {
    setDownloadError(null)
    try {
      await downloadArtifact(artifactId)
    } catch (caught) {
      setDownloadError(caught instanceof Error ? caught.message : 'Download failed.')
    }
  }

  return (
    <>
      <header className="bw-console__header">
        <div>
          <div className="bw-console__eyebrow">Output Registry</div>
          <h2>Generated Artifacts</h2>
        </div>
        <ConsoleViewToggle view={view} onChange={setView} />
      </header>
      <div className="bw-console__scroll">
        {error ? <ErrorBanner message={error} /> : null}
        {downloadError ? <ErrorBanner message={downloadError} /> : null}
        <div className="bw-console__searchbar">
          <span style={{ color: '#6f828b' }}>⌕</span>
          <input
            placeholder="Search artifacts by title, type, module, or source…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <span className="bw-count">{filtered.length} artifacts</span>
        </div>
        {isLoading && filtered.length === 0 ? (
          <div className="bw-console__empty">Loading artifacts…</div>
        ) : filtered.length === 0 ? (
          <div className="bw-console__empty">No artifacts yet. Complete a production run to generate outputs.</div>
        ) : view === 'list' ? (
          <section className="bw-console__panel">
            <table className="bw-console__table">
              <thead>
                <tr>
                  <th>Artifact</th>
                  <th>Type</th>
                  <th>Module</th>
                  <th>Format</th>
                  <th>Size</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((artifact) => (
                  <tr key={artifact.id}>
                    <td>
                      <button
                        type="button"
                        className="bw-console__listname"
                        onClick={() => void handleDownload(artifact.id)}
                      >
                        <span>
                          <div className="t">{artifact.filename}</div>
                          <div className="s">{formatDate(artifact.created_at)}</div>
                        </span>
                      </button>
                    </td>
                    <td>{artifactKindLabel(artifact.artifact_type)}</td>
                    <td>{moduleLabel(artifactModule(artifact))}</td>
                    <td className="num">{artifact.format}</td>
                    <td className="num">{formatBytes(artifact.file_size_bytes)}</td>
                    <td>
                      {artifact.source_id && sourceById.get(artifact.source_id)
                        ? sourceTitle(sourceById.get(artifact.source_id)!)
                        : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        ) : (
          <div className="bw-console__sources">
            {filtered.map((artifact) => (
              <button
                type="button"
                className="bw-console__panel bw-console__artifact-card"
                key={artifact.id}
                style={{ padding: 18, textAlign: 'left', width: '100%' }}
                onClick={() => void handleDownload(artifact.id)}
              >
                <div>
                  <div style={{ fontFamily: 'var(--bw-grotesk)', fontWeight: 600, color: '#fff' }}>
                    {artifact.filename}
                  </div>
                  <div
                    style={{
                      fontFamily: 'var(--bw-mono)',
                      fontSize: '0.7rem',
                      color: '#8aa1ab',
                      marginTop: 3,
                    }}
                  >
                    {artifactKindLabel(artifact.artifact_type)} · {moduleLabel(artifactModule(artifact))}
                  </div>
                </div>
                <p style={{ fontSize: '0.84rem', color: '#b6c4cb', marginTop: 12, lineHeight: 1.5 }}>
                  {artifactSummary(artifact)}
                </p>
                <div className="bw-console__card-fill" aria-hidden="true" />
                <div className="bw-console__artifact-foot">
                  <span className="seg">{formatBytes(artifact.file_size_bytes)}</span>
                  <span className="seg">{artifact.format}</span>
                  <span className="seg">Download</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </>
  )
}
