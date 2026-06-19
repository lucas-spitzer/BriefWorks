import { useMemo, useState } from 'react'
import { useWorkspaceData } from '../../features/workspace/workspaceDataContext'
import { useLiveTick } from '../../hooks/useLiveTick'
import { formatDate, formatDateTime, formatDuration, formatCostUsd, statusLabel } from '../../lib/consoleFormat'
import {
  flattenStageRuns,
  stageRunCostUsd,
  stageRunDisplayName,
  stageRunDurationSec,
  stageRunElevenLabsTokens,
  stageRunSummary,
  stageRunTokens,
} from '../../lib/consoleMappers'
import { ConsoleDialog } from './ConsoleDialog'
import { ConsoleViewToggle } from './ConsoleViewToggle'
import { ErrorBanner } from './ErrorBanner'
import { moduleLabel } from './moduleLabel'
import type { ConsoleView } from './types'

interface ConsoleStagesProps {
  onGoToOps: () => void
}

export function ConsoleStages({ onGoToOps }: ConsoleStagesProps) {
  const { productionRuns, stageRunsByRunId, sources, isLoading, error } = useWorkspaceData()
  const [query, setQuery] = useState('')
  const [view, setView] = useState<ConsoleView>('grid')
  const [errorStageId, setErrorStageId] = useState<string | null>(null)

  const stageRuns = useMemo(
    () => flattenStageRuns(productionRuns, stageRunsByRunId, sources),
    [productionRuns, stageRunsByRunId, sources],
  )

  const hasLiveDuration = stageRuns.some(
    (stageRun) => stageRun.status === 'queued' || stageRun.status === 'running',
  )
  useLiveTick(hasLiveDuration)

  const filtered = useMemo(() => {
    const q = query.toLowerCase()
    return stageRuns.filter(
      (stageRun) =>
        stageRunDisplayName(stageRun).toLowerCase().includes(q) ||
        stageRun.stage_id.includes(q) ||
        stageRun.runLabel.toLowerCase().includes(q) ||
        moduleLabel(stageRun.module).toLowerCase().includes(q),
    )
  }, [stageRuns, query])

  const errorStage = useMemo(
    () => (errorStageId ? stageRuns.find((stageRun) => stageRun.id === errorStageId) : undefined),
    [errorStageId, stageRuns],
  )

  return (
    <>
      <header className="bw-console__header">
        <div>
          <div className="bw-console__eyebrow">Execution Log</div>
          <h2>Stage Runs</h2>
        </div>
        <ConsoleViewToggle view={view} onChange={setView} />
        <button className="bw-console__cta" onClick={onGoToOps}>
          + New run
        </button>
      </header>
      <div className="bw-console__scroll">
        {error ? <ErrorBanner message={error} /> : null}
        <div className="bw-console__searchbar">
          <span style={{ color: '#6f828b' }}>⌕</span>
          <input
            placeholder="Search stage runs by name, module, or production run…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <span className="bw-count">{filtered.length} runs</span>
        </div>
        {isLoading && filtered.length === 0 ? (
          <div className="bw-console__empty">Loading stage runs…</div>
        ) : filtered.length === 0 ? (
          <div className="bw-console__empty">No stage runs yet. Start a production run from OPS.</div>
        ) : view === 'list' ? (
          <section className="bw-console__panel">
            <table className="bw-console__table">
              <thead>
                <tr>
                  <th>Stage</th>
                  <th>Module</th>
                  <th>Version</th>
                  <th>Model</th>
                  <th>Status</th>
                  <th>Duration</th>
                  <th>Tokens</th>
                  <th>Cost</th>
                  <th>Run</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((stageRun) => {
                  const tokens = stageRunTokens(stageRun)
                  const elevenlabsTokens = stageRunElevenLabsTokens(stageRun)
                  const costUsd = stageRunCostUsd(stageRun)
                  return (
                    <tr key={stageRun.id}>
                      <td>
                        <div className="bw-console__listname">
                          <span>
                            <div className="t">{stageRunDisplayName(stageRun)}</div>
                            <div className="s">
                              {stageRun.started_at ? formatDateTime(stageRun.started_at) : '—'}
                            </div>
                          </span>
                        </div>
                      </td>
                      <td>{moduleLabel(stageRun.module)}</td>
                      <td className="num">{stageRun.stage_version}</td>
                      <td className="num">{stageRun.model ?? '—'}</td>
                      <td>
                        <span className={`bw-console__statepill bw-state--${stageRun.status}`}>
                          {statusLabel(stageRun.status)}
                        </span>
                      </td>
                      <td className="num">{formatDuration(stageRunDurationSec(stageRun))}</td>
                      <td className="num">
                        {tokens.in + tokens.out > 0
                          ? `${((tokens.in + tokens.out) / 1000).toFixed(1)}K`
                          : elevenlabsTokens > 0
                            ? `${(elevenlabsTokens / 1000).toFixed(1)}K EL`
                            : '—'}
                      </td>
                      <td className="num">{formatCostUsd(costUsd)}</td>
                      <td>{stageRun.runId.slice(0, 8).toUpperCase()}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </section>
        ) : (
          <div className="bw-console__sources">
            {filtered.map((stageRun) => {
              const tokens = stageRunTokens(stageRun)
              const elevenlabsTokens = stageRunElevenLabsTokens(stageRun)
              const costUsd = stageRunCostUsd(stageRun)
              return (
                <div
                  className="bw-console__panel bw-console__artifact-card bw-console__stage-card"
                  key={stageRun.id}
                  style={{ padding: 18 }}
                >
                  <div>
                    <div style={{ fontFamily: 'var(--bw-grotesk)', fontWeight: 600, color: '#fff' }}>
                      {stageRunDisplayName(stageRun)}{' '}
                      <span className="bw-console__module-tag">{moduleLabel(stageRun.module)}</span>
                    </div>
                    <div
                      style={{
                        fontFamily: 'var(--bw-mono)',
                        fontSize: '0.7rem',
                        color: '#8aa1ab',
                        marginTop: 3,
                      }}
                    >
                      {stageRun.stage_id} · v{stageRun.stage_version}
                    </div>
                  </div>
                  <p style={{ fontSize: '0.84rem', color: '#b6c4cb', marginTop: 12, lineHeight: 1.5 }}>
                    {stageRunSummary(stageRun)}
                  </p>
                  <div className="stats">
                    {stageRun.model ? <span>{stageRun.model}</span> : null}
                    <span>{formatDuration(stageRunDurationSec(stageRun))}</span>
                    {tokens.in + tokens.out > 0 ? (
                      <span>{((tokens.in + tokens.out) / 1000).toFixed(1)}K tok</span>
                    ) : elevenlabsTokens > 0 ? (
                      <span>{(elevenlabsTokens / 1000).toFixed(1)}K EL tok</span>
                    ) : null}
                    {costUsd > 0 ? <span>{formatCostUsd(costUsd)}</span> : null}
                  </div>
                  {stageRun.error ? (
                    <button
                      type="button"
                      className="bw-console__error-trigger"
                      onClick={() => setErrorStageId(stageRun.id)}
                    >
                      Show error message
                    </button>
                  ) : null}
                  <div className="bw-console__card-fill" aria-hidden="true" />
                  <div className="bw-console__artifact-foot">
                    <span className="seg">
                      {stageRun.started_at ? formatDate(stageRun.started_at) : '—'}
                    </span>
                    <span className="seg">{stageRun.runId.slice(0, 8).toUpperCase()}</span>
                    <span className="seg">
                      <span className={`bw-console__statepill bw-state--${stageRun.status}`}>
                        {statusLabel(stageRun.status)}
                      </span>
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
      <ConsoleDialog
        title={errorStage ? `${stageRunDisplayName(errorStage)} error` : 'Stage run error'}
        open={errorStageId !== null && Boolean(errorStage?.error)}
        onClose={() => setErrorStageId(null)}
      >
        <pre className="bw-console__error-detail">{errorStage?.error}</pre>
      </ConsoleDialog>
    </>
  )
}
