import { Fragment, useState, type CSSProperties, type ReactNode } from 'react'
import { useWorkspace } from '../features/workspace/workspaceContext'
import '../gate.css'

interface WorkspaceGateProps {
  children: ReactNode
}

const pipelineStages = [
  { tag: 'Stage 01', name: 'Intellex', role: 'Deconstructs sources' },
  { tag: 'Stage 02', name: 'Mathesys', role: 'Generates artifacts' },
  { tag: 'Stage 03', name: 'QnGen', role: 'Builds assessments' },
]

const scopeItems = ['Sources', 'Wiki Entries', 'Artifacts', 'Production Runs']

export function WorkspaceGate({ children }: WorkspaceGateProps) {
  const { activeWorkspace, workspaces, isLoading, error, createWorkspace } = useWorkspace()
  const [name, setName] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  if (isLoading) {
    return (
      <main className="bw-gate" aria-live="polite">
        <section className="bw-gate__status">
          <div className="bw-gate__mark">BW</div>
          <p className="bw-gate__eyebrow">Workspace Registry</p>
          <p className="bw-gate__status-msg">Retrieving workspaces…</p>
          <div className="bw-gate__scanner" aria-hidden="true" />
        </section>
      </main>
    )
  }

  if (error) {
    return (
      <main className="bw-gate">
        <section className="bw-gate__status bw-gate__status--alert" role="alert">
          <div className="bw-gate__mark">BW</div>
          <p className="bw-gate__eyebrow">Workspace Registry</p>
          <p className="bw-gate__status-msg">{error}</p>
        </section>
      </main>
    )
  }

  if (!activeWorkspace) {
    return (
      <main className="bw-gate">
        <div className="bw-gate__provision">
          <header className="bw-gate__provision-head">
            <p className="bw-gate__eyebrow">Workspace Provisioning</p>
            <h1>Establish your first workspace</h1>
            <p className="bw-gate__copy">
              Each workspace is an isolated operating environment. Sources, wiki entries,
              artifacts, and production runs are scoped to the workspace they were created in.
            </p>
          </header>

          <div className="bw-gate__flow" aria-label="Production pipeline">
            {pipelineStages.map((stage, index) => (
              <Fragment key={stage.name}>
                {index > 0 ? <span className="bw-gate__flow-link" aria-hidden="true" /> : null}
                <div className="bw-gate__stage">
                  <div className="bw-gate__stage-tag">{stage.tag}</div>
                  <div className="bw-gate__stage-name">{stage.name}</div>
                  <div className="bw-gate__stage-role">{stage.role}</div>
                </div>
              </Fragment>
            ))}
          </div>

          <div className="bw-gate__scope" aria-label="Workspace contents">
            {scopeItems.map((item, index) => (
              <div
                key={item}
                className="bw-gate__scope-cell"
                style={{ '--i': index } as CSSProperties}
              >
                <div className="bw-gate__scope-value">0</div>
                <div className="bw-gate__scope-label">{item}</div>
              </div>
            ))}
          </div>

          <form
            className="bw-gate__form"
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
                  submitError instanceof Error
                    ? submitError.message
                    : 'Could not create workspace.',
                )
              } finally {
                setIsCreating(false)
              }
            }}
          >
            <label className="bw-gate__label" htmlFor="workspace-name">
              Workspace Designation
            </label>
            <input
              id="workspace-name"
              className="bw-gate__input"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Warfighting doctrine"
              autoComplete="off"
            />
            {createError ? (
              <div className="bw-gate__error" role="alert">
                <p>{createError}</p>
              </div>
            ) : null}
            <button type="submit" className="bw-gate__cta" disabled={isCreating || !name.trim()}>
              {isCreating ? 'Provisioning…' : 'Create Workspace'}
            </button>
          </form>

          {workspaces.length > 0 ? (
            <p className="bw-gate__hint">
              Existing workspaces are available from the console rail selector.
            </p>
          ) : null}
        </div>
      </main>
    )
  }

  return <>{children}</>
}
