import { useMemo, useRef, useState, type ChangeEvent } from 'react'
import { useWorkspaceData } from '../../features/workspace/workspaceDataContext'
import { formatDate, statusLabel } from '../../lib/consoleFormat'
import { mapSourceDisplay } from '../../lib/consoleMappers'
import { ConsoleViewToggle } from './ConsoleViewToggle'
import { ErrorBanner } from './ErrorBanner'
import type { ConsoleView } from './types'

export function ConsoleSources() {
  const { sources, isLoading, error, uploadSource } = useWorkspaceData()
  const [query, setQuery] = useState('')
  const [view, setView] = useState<ConsoleView>('grid')
  const [isUploading, setIsUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const displaySources = useMemo(() => sources.map(mapSourceDisplay), [sources])

  const filtered = useMemo(() => {
    const q = query.toLowerCase()
    return displaySources.filter(
      (source) =>
        source.title.toLowerCase().includes(q) ||
        source.filename.toLowerCase().includes(q) ||
        (source.bibliographicTitle?.toLowerCase().includes(q) ?? false) ||
        (source.identifier?.toLowerCase().includes(q) ?? false) ||
        (source.documentType?.toLowerCase().includes(q) ?? false) ||
        (source.issuingAuthority?.toLowerCase().includes(q) ?? false),
    )
  }, [displaySources, query])

  const handleUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return

    setIsUploading(true)
    setUploadError(null)

    try {
      await uploadSource(file)
    } catch (caught) {
      setUploadError(caught instanceof Error ? caught.message : 'Upload failed.')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <>
      <header className="bw-console__header">
        <div>
          <div className="bw-console__eyebrow">Knowledge Base</div>
          <h2>Source Intelligence</h2>
        </div>
        <ConsoleViewToggle view={view} onChange={setView} />
        <input
          ref={fileInputRef}
          type="file"
          hidden
          onChange={(event) => void handleUpload(event)}
        />
        <button
          className="bw-console__cta bw-console__cta--ghost"
          disabled={isUploading}
          onClick={() => fileInputRef.current?.click()}
        >
          {isUploading ? 'Uploading…' : '⇪ Upload source'}
        </button>
      </header>
      <div className="bw-console__scroll">
        {error ? <ErrorBanner message={error} /> : null}
        {uploadError ? <ErrorBanner message={uploadError} /> : null}
        <div className="bw-console__searchbar">
          <span style={{ color: '#6f828b' }}>⌕</span>
          <input
            placeholder="Search sources by name, filename, or research title…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <span className="bw-count">{filtered.length} files</span>
        </div>
        {isLoading && filtered.length === 0 ? (
          <div className="bw-console__empty">Loading sources…</div>
        ) : filtered.length === 0 ? (
          <div className="bw-console__empty">
            No sources yet. Upload a file to ingest it into the knowledge base.
          </div>
        ) : view === 'list' ? (
          <section className="bw-console__panel">
            <table className="bw-console__table">
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Type</th>
                  <th>Format</th>
                  <th>Status</th>
                  <th>Size</th>
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
                          <div className="s">
                            {[
                              source.bibliographicTitle &&
                              source.bibliographicTitle !== source.title
                                ? source.bibliographicTitle
                                : null,
                              source.identifier,
                              source.issuingAuthority,
                            ]
                              .filter(Boolean)
                              .join(' · ') || source.filename}
                          </div>
                        </span>
                      </div>
                    </td>
                    <td>{source.documentType ?? '—'}</td>
                    <td className="num">{source.mimeLabel}</td>
                    <td>
                      <span className={`bw-console__statepill bw-state--${source.status}`}>
                        {statusLabel(source.status)}
                      </span>
                    </td>
                    <td className="num">{source.sizeLabel}</td>
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
                  <div
                    style={{
                      fontFamily: 'var(--bw-grotesk)',
                      fontSize: '1.1rem',
                      fontWeight: 600,
                      color: '#fff',
                    }}
                  >
                    {source.title}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#9fb2bb', marginTop: 6 }}>
                    {source.purpose
                      ? `Purpose: ${source.purpose}`
                      : [source.documentType, source.issuingAuthority].filter(Boolean).join(' · ') ||
                        (source.status === 'stored' || source.status === 'processing'
                          ? 'Ingest in progress'
                          : source.filename)}
                  </div>
                </div>
                {source.pages !== null || source.segments !== null || source.confidence !== null ? (
                  <div className="bw-console__step-body">
                    <div className="stats" style={{ marginTop: 12 }}>
                      {source.pages !== null ? <span>{source.pages} pages</span> : null}
                      {source.segments !== null ? <span>{source.segments} segments</span> : null}
                      {source.confidence !== null ? (
                        <span>conf {Math.round(source.confidence * 100)}%</span>
                      ) : null}
                    </div>
                  </div>
                ) : null}
                <div className="bw-console__card-fill" aria-hidden="true" />
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
