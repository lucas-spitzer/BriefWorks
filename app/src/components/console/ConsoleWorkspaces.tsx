import { Boxes } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useWorkspace } from '../../features/workspace/workspaceContext'
import { useWorkspaceData } from '../../features/workspace/workspaceDataContext'
import { formatDate, statusLabel } from '../../lib/consoleFormat'
import { ErrorBanner } from './ErrorBanner'

export function ConsoleWorkspaces() {
  const { activeWorkspace, workspaces, isLoading, error, selectWorkspace, createWorkspace } =
    useWorkspace()
  const {
    sources,
    artifacts,
    productionRuns,
    wikiEntries,
    flashcards,
    quizzes,
    scenarios,
    activeRunCount,
  } = useWorkspaceData()
  const [isCreating, setIsCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  const overview = useMemo(
    () => [
      { label: 'Sources', value: String(sources.length) },
      { label: 'Artifacts', value: String(artifacts.length) },
      { label: 'Wiki entries', value: String(wikiEntries.length) },
      { label: 'Pipeline runs', value: String(productionRuns.length) },
      { label: 'Active runs', value: String(activeRunCount) },
      {
        label: 'Assessments',
        value: String(flashcards.length + quizzes.length + scenarios.length),
      },
    ],
    [
      sources.length,
      artifacts.length,
      wikiEntries.length,
      productionRuns.length,
      activeRunCount,
      flashcards.length,
      quizzes.length,
      scenarios.length,
    ],
  )

  const handleCreate = async () => {
    const name = window.prompt('New workspace name')?.trim()
    if (!name) return
    setIsCreating(true)
    setCreateError(null)
    try {
      await createWorkspace(name)
    } catch (caught) {
      setCreateError(caught instanceof Error ? caught.message : 'Failed to create workspace.')
    } finally {
      setIsCreating(false)
    }
  }

  return (
    <>
      <header className="bw-console__header">
        <div>
          <div className="bw-console__eyebrow">Environment</div>
          <h2>Workspaces</h2>
        </div>
        <span className="bw-console__live">
          <span className="bw-live-dot" /> {workspaces.length} available
        </span>
        <button className="bw-console__cta" onClick={() => void handleCreate()} disabled={isCreating}>
          {isCreating ? 'Creating…' : '+ New workspace'}
        </button>
      </header>

      <div className="bw-console__scroll">
        {error ? <ErrorBanner message={error} /> : null}
        {createError ? <ErrorBanner message={createError} /> : null}

        {activeWorkspace ? (
          <div className="bw-console__metrics">
            {overview.map((metric) => (
              <div className="bw-console__metric" key={metric.label}>
                <div className="l">{metric.label}</div>
                <div className="v">{metric.value}</div>
                <div className="d bw-flat">{activeWorkspace.name}</div>
              </div>
            ))}
          </div>
        ) : null}

        {isLoading && workspaces.length === 0 ? (
          <div className="bw-console__empty">Loading workspaces…</div>
        ) : workspaces.length === 0 ? (
          <div className="bw-console__empty">
            No workspaces yet. Create one to begin production.
          </div>
        ) : (
          <div className="bw-console__sources">
            {workspaces.map((workspace) => {
              const isActive = workspace.id === activeWorkspace?.id
              return (
                <button
                  type="button"
                  key={workspace.id}
                  className={`bw-console__panel bw-console__ws-card${isActive ? ' is-active' : ''}`}
                  onClick={() => selectWorkspace(workspace.id)}
                  aria-pressed={isActive}
                >
                  <div className="bw-console__ws-card-head">
                    <span className="bw-console__ws-icon" aria-hidden="true">
                      <Boxes size={16} strokeWidth={1.75} />
                    </span>
                    <span className="bw-console__ws-title">{workspace.name}</span>
                    {isActive ? <span className="bw-console__ws-badge">Active</span> : null}
                  </div>
                  <p className="bw-console__ws-desc">
                    {workspace.description?.trim() || 'No description provided.'}
                  </p>
                  <div className="bw-console__card-fill" aria-hidden="true" />
                  <div className="bw-console__artifact-foot">
                    <span className="seg">{statusLabel(workspace.status)}</span>
                    <span className="seg">{formatDate(workspace.created_at)}</span>
                    <span className="seg">{isActive ? 'Selected' : 'Set active'}</span>
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </div>
    </>
  )
}
