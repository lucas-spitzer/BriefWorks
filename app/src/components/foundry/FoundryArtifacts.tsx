import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWorkspaceData } from '../../features/workspace/workspaceDataContext'
import { artifactFormatLabel, artifactKindShortLabel, formatBytes } from '../../lib/foundryFormat'
import {
  artifactCardTitle,
  artifactModule,
  sourceTitle,
} from '../../lib/foundryMappers'
import { sourceBibliographicTitle, sourceDisplayName } from '../../lib/sourceDisplay'
import type { Artifact } from '../../lib/workspaceApi'
import { FoundryViewToggle } from './FoundryViewToggle'
import { ErrorBanner } from './ErrorBanner'
import { moduleLabel } from './moduleLabel'
import type { FoundryView } from './types'

const AUDIO_FORMATS = new Set(['mp3', 'wav', 'm4a', 'ogg'])

/** Raw audio files download; narration manifests and ebooks open in the academy reader. */
function isRawAudioArtifact(artifact: Artifact): boolean {
  const format = (artifact.format || '').toLowerCase()
  const isNarrationManifest = artifact.artifact_type === 'narration_audio'
  return (
    !isNarrationManifest &&
    (artifact.artifact_type.includes('audio') || AUDIO_FORMATS.has(format))
  )
}

function isStudySheetArtifact(artifact: Artifact): boolean {
  return artifact.artifact_type === 'study_sheet'
}

function artifactOpenLabel(artifact: Artifact): string {
  if (isRawAudioArtifact(artifact) || isStudySheetArtifact(artifact)) return 'Download'
  return 'Open'
}

function canOpenArtifact(artifact: Artifact): boolean {
  return (
    isRawAudioArtifact(artifact) ||
    isStudySheetArtifact(artifact) ||
    Boolean(artifact.source_id)
  )
}

export function FoundryArtifacts() {
  const {
    sources,
    artifacts,
    studySheetJobs,
    isLoading,
    error,
    downloadArtifact,
  } = useWorkspaceData()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [view, setView] = useState<FoundryView>('grid')
  const [downloadError, setDownloadError] = useState<string | null>(null)
  const [dismissedJobIds, setDismissedJobIds] = useState<string[]>([])
  const [workspaceErrorHidden, setWorkspaceErrorHidden] = useState(false)

  const sourceById = useMemo(() => new Map(sources.map((s) => [s.id, s])), [sources])
  const pendingJobs = useMemo(
    () => studySheetJobs.filter((job) => job.status === 'queued' || job.status === 'running'),
    [studySheetJobs],
  )
  const latestFailedJob = useMemo(() => {
    const open = studySheetJobs.filter(
      (job) => job.status === 'failed' && !dismissedJobIds.includes(job.id),
    )
    open.sort((left, right) => {
      const leftAt = left.completed_at || left.updated_at || left.created_at
      const rightAt = right.completed_at || right.updated_at || right.created_at
      return rightAt.localeCompare(leftAt)
    })
    return open[0] ?? null
  }, [studySheetJobs, dismissedJobIds])

  const logMessage = downloadError
    ?? (workspaceErrorHidden ? null : error)
    ?? (latestFailedJob
      ? `Study sheet failed for ${latestFailedJob.input_filename}: ${latestFailedJob.error || 'generation failed.'}`
      : null)

  const dismissLogs = () => {
    setDownloadError(null)
    setWorkspaceErrorHidden(true)
    setDismissedJobIds(
      studySheetJobs.filter((job) => job.status === 'failed').map((job) => job.id),
    )
  }

  const filtered = useMemo(() => {
    const q = query.toLowerCase()
    return artifacts.filter((artifact) => {
      const source = artifact.source_id ? sourceById.get(artifact.source_id) : undefined
      const displayName = source ? sourceDisplayName(source) : ''
      const bibliographic = source ? (sourceBibliographicTitle(source) ?? '') : ''
      return (
        artifact.filename.toLowerCase().includes(q) ||
        artifactCardTitle(artifact, source).toLowerCase().includes(q) ||
        displayName.toLowerCase().includes(q) ||
        bibliographic.toLowerCase().includes(q) ||
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

  const handleOpen = (artifact: Artifact) => {
    if (isRawAudioArtifact(artifact) || isStudySheetArtifact(artifact)) {
      void handleDownload(artifact.id)
      return
    }
    if (artifact.source_id) {
      navigate(`/app/reader/${artifact.source_id}`)
    }
  }

  return (
    <>
      <header className="as-console__header">
        <div>
          <div className="as-console__eyebrow">Output Registry</div>
          <h2>Generated Artifacts</h2>
        </div>
        <FoundryViewToggle view={view} onChange={setView} />
      </header>
      <div className="as-console__scroll">
        {logMessage ? <ErrorBanner message={logMessage} onDismiss={dismissLogs} /> : null}
        {pendingJobs.length > 0 ? (
          <div className="as-console__empty">
            Generating {pendingJobs.length === 1 ? 'a study sheet' : `${pendingJobs.length} study sheets`}
            {pendingJobs[0] ? ` from ${pendingJobs[0].input_filename}` : ''}…
          </div>
        ) : null}
        <div className="as-console__searchbar">
          <span style={{ color: '#6f828b' }}>⌕</span>
          <input
            placeholder="Search artifacts by title, type, module, or source…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <span className="as-count">{filtered.length} artifacts</span>
        </div>
        {isLoading && filtered.length === 0 ? (
          <div className="as-console__empty">Loading artifacts…</div>
        ) : filtered.length === 0 ? (
          <div className="as-console__empty">
            No artifacts yet. Complete a production run.
          </div>
        ) : view === 'list' ? (
          <section className="as-console__panel">
            <table className="as-console__table">
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
                      <div className="as-console__listname">
                        <span>
                          <div className="t">{artifactCardTitle(artifact, source)}</div>
                          <button
                            type="button"
                            className="as-console__card-filename as-console__card-filename--list"
                            onClick={() => void handleDownload(artifact.id)}
                          >
                            {artifact.filename}
                          </button>
                        </span>
                      </div>
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
          <div className="as-console__sources">
            {filtered.map((artifact) => {
              const source = artifact.source_id ? sourceById.get(artifact.source_id) : undefined

              return (
                <div
                  className="as-console__panel as-console__artifact-card"
                  key={artifact.id}
                  style={{ padding: 18 }}
                >
                  <div>
                    <div style={{ fontFamily: 'var(--as-grotesk)', fontWeight: 600, color: '#fff' }}>
                      {artifactCardTitle(artifact, source)}
                    </div>
                  </div>
                  <button
                    type="button"
                    className="as-console__card-filename"
                    onClick={() => void handleDownload(artifact.id)}
                  >
                    {artifact.filename}
                  </button>
                  <div className="as-console__card-fill" aria-hidden="true" />
                  <div className="as-console__artifact-foot">
                    <span className="seg">{formatBytes(artifact.file_size_bytes)}</span>
                    <span className="seg">{artifactFormatLabel(artifact.format)}</span>
                    <span className="seg">
                      <button
                        type="button"
                        className="as-console__statepill as-state--download"
                        onClick={() => handleOpen(artifact)}
                        disabled={!canOpenArtifact(artifact)}
                      >
                        {artifactOpenLabel(artifact)}
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
