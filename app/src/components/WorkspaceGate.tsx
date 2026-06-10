import { useState, type ReactNode } from 'react'
import { useWorkspace } from '../features/workspace/workspaceContext'

interface WorkspaceGateProps {
  children: ReactNode
}

export function WorkspaceGate({ children }: WorkspaceGateProps) {
  const { activeWorkspace, workspaces, isLoading, error, createWorkspace } = useWorkspace()
  const [name, setName] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  if (isLoading) {
    return (
      <section className="empty-panel">
        <p>Loading workspaces…</p>
      </section>
    )
  }

  if (error) {
    return (
      <section className="empty-panel empty-panel--alert">
        <p>{error}</p>
      </section>
    )
  }

  if (!activeWorkspace) {
    return (
      <section className="workspace-create">
        <header className="page-header">
          <p className="eyebrow">Workspace</p>
          <h2>Create your first workspace</h2>
          <p>Workspaces isolate sources, wiki entries, artifacts, and production runs.</p>
        </header>

        <form
          className="workspace-create__form"
          onSubmit={async (event) => {
            event.preventDefault()
            if (!name.trim()) {
              return
            }

            setIsCreating(true)
            setCreateError(null)

            try {
              await createWorkspace(name.trim())
              setName('')
            } catch (submitError) {
              setCreateError(
                submitError instanceof Error ? submitError.message : 'Could not create workspace.',
              )
            } finally {
              setIsCreating(false)
            }
          }}
        >
          <label className="field-label" htmlFor="workspace-name">
            Workspace name
          </label>
          <input
            id="workspace-name"
            className="field-input"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Warfighting doctrine"
          />
          {createError ? <p className="field-error">{createError}</p> : null}
          <button type="submit" className="button-primary" disabled={isCreating || !name.trim()}>
            {isCreating ? 'Creating…' : 'Create workspace'}
          </button>
        </form>

        {workspaces.length > 0 ? (
          <p className="workspace-create__hint">Select an existing workspace from the sidebar.</p>
        ) : null}
      </section>
    )
  }

  return <>{children}</>
}
