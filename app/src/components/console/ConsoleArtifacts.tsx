import { useMemo, useState } from 'react'
import { useWorkspaceData } from '../../features/workspace/workspaceDataContext'
import { artifactFormatLabel, artifactKindShortLabel, formatBytes } from '../../lib/consoleFormat'
import {
  artifactCardTitle,
  artifactModule,
  sourceResearchTitle,
  sourceTitle,
} from '../../lib/consoleMappers'
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
      const sourceName = source ? sourceResearchTitle(source) : ''
      return (
        artifact.filename.toLowerCase().includes(q) ||
        artifactCardTitle(artifact, source).toLowerCase().includes(q) ||
        sourceName.toLowerCase().includes(q) ||
        artifactKindShortLabel(artifact.artifact_type).toLowerCase().includes(q) ||
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
                {filtered.map((artifact) => {
                  const source = artifact.source_id
                    ? sourceById.get(artifact.source_id)
                    : undefined

                  return (
                  <tr key={artifact.id}>
                    <td>
                      <button
                        type="button"
                        className="bw-console__listname"
                        onClick={() => void handleDownload(artifact.id)}
                      >
                        <span>
                          <div className="t">{artifactCardTitle(artifact, source)}</div>
                          <div className="s">{artifact.filename}</div>
                        </span>
                      </button>
                    </td>
                    <td>{artifactKindShortLabel(artifact.artifact_type)}</td>
                    <td>{moduleLabel(artifactModule(artifact))}</td>
                    <td className="num">{artifactFormatLabel(artifact.format)}</td>
                    <td className="num">{formatBytes(artifact.file_size_bytes)}</td>
                    <td>{source ? sourceTitle(source) : '—'}</td>
                  </tr>
                  )
                })}
              </tbody>
            </table>
          </section>
        ) : (
          <div className="bw-console__sources">
            {filtered.map((artifact) => {
              const source = artifact.source_id ? sourceById.get(artifact.source_id) : undefined

              return (
                <div
                  className="bw-console__panel bw-console__artifact-card"
                  key={artifact.id}
                  style={{ padding: 18 }}
                >
                  <div>
                    <div style={{ fontFamily: 'var(--bw-grotesk)', fontWeight: 600, color: '#fff' }}>
                      {artifactCardTitle(artifact, source)}
                    </div>
                  </div>
                  <p className="bw-console__card-desc">{artifact.filename}</p>
                  <div className="bw-console__card-fill" aria-hidden="true" />
                  <div className="bw-console__artifact-foot">
                    <span className="seg">{formatBytes(artifact.file_size_bytes)}</span>
                    <span className="seg">{artifactFormatLabel(artifact.format)}</span>
                    <span className="seg">
                      <button
                        type="button"
                        className="bw-console__statepill bw-state--download"
                        onClick={() => void handleDownload(artifact.id)}
                      >
                        Download
                      </button>
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </>
  )
}
