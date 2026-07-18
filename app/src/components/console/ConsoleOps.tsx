import { useEffect, useMemo, useState } from 'react'
import { useWorkspaceData } from '../../features/workspace/workspaceDataContext'
import { formatDateTime, formatDuration, formatCostUsd, statusLabel } from '../../lib/consoleFormat'
import {
  flattenApiRequests,
  productionRunCostUsd,
  productionRunDurationSec,
  productionRunLabel,
  productionRunProgress,
  stageRunTokens,
  sumWorkspaceCostUsd,
} from '../../lib/consoleMappers'
import { ConsoleDetail } from './ConsoleDetail'
import { ErrorBanner } from './ErrorBanner'
import { NewRunPanel } from './NewRunPanel'

interface ConsoleOpsProps {
  onGoToSources: () => void
}

export function ConsoleOps({ onGoToSources }: ConsoleOpsProps) {
  const {
    sources,
    productionRuns,
    stageRunsByRunId,
    activeRunCount,
    isLoading,
    error,
  } = useWorkspaceData()

  const sortedRuns = useMemo(
    () => [...productionRuns].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
    [productionRuns],
  )

  const [activeId, setActiveId] = useState<string | null>(null)
  const [showNewRun, setShowNewRun] = useState(false)

  useEffect(() => {
    if (!sortedRuns.length) {
      setActiveId(null)
      return
    }
    if (!activeId || !sortedRuns.some((run) => run.id === activeId)) {
      setActiveId(sortedRuns[0].id)
    }
  }, [sortedRuns, activeId])

  const active = sortedRuns.find((run) => run.id === activeId) ?? null

  const metrics = useMemo(() => {
    const completed = productionRuns.filter((run) => run.status === 'completed').length
    const failed = productionRuns.filter((run) => run.status === 'failed').length
    const finished = completed + failed
    const successRate = finished ? Math.round((completed / finished) * 100) : 0

    const durations = productionRuns
      .filter((run) => run.completed_at)
      .map((run) => productionRunDurationSec(run))
    const avgDuration =
      durations.length > 0
        ? formatDuration(Math.round(durations.reduce((sum, d) => sum + d, 0) / durations.length))
        : '—'

    let totalTokens = 0
    for (const runs of Object.values(stageRunsByRunId)) {
      for (const stageRun of runs) {
        const tokens = stageRunTokens(stageRun)
        totalTokens += tokens.in + tokens.out
      }
    }

    const totalCost = sumWorkspaceCostUsd(productionRuns, stageRunsByRunId)

    return [
      { label: 'Active runs', value: String(activeRunCount), delta: '', trend: 'flat' as const },
      { label: 'Pipeline runs', value: String(productionRuns.length), delta: '', trend: 'flat' as const },
      { label: 'Success rate', value: finished ? `${successRate}%` : '—', delta: '', trend: 'flat' as const },
      {
        label: 'Tokens used',
        value: totalTokens > 1_000_000 ? `${(totalTokens / 1_000_000).toFixed(1)}M` : `${Math.round(totalTokens / 1000)}K`,
        delta: '',
        trend: 'flat' as const,
      },
      {
        label: 'Total API cost',
        value: formatCostUsd(totalCost),
        delta: '',
        trend: 'flat' as const,
      },
      { label: 'Avg run time', value: avgDuration, delta: '', trend: 'flat' as const },
    ]
  }, [productionRuns, activeRunCount, stageRunsByRunId])

  return (
    <>
      <header className="bw-console__header">
        <div>
          <div className="bw-console__eyebrow">Mission Control</div>
          <h2>Production Operations</h2>
        </div>
        {activeRunCount > 0 ? (
          <span className="bw-console__live">
            <span className="bw-live-dot" /> Live · {activeRunCount} run{activeRunCount === 1 ? '' : 's'} active
          </span>
        ) : (
          <span className="bw-console__live" style={{ opacity: 0.6 }}>
            Idle
          </span>
        )}
        <button className="bw-console__cta" onClick={() => setShowNewRun(true)}>
          + New run
        </button>
      </header>

      <div className="bw-console__scroll">
        {error ? <ErrorBanner message={error} /> : null}
        {showNewRun ? (
          <NewRunPanel onClose={() => setShowNewRun(false)} onCreated={() => setShowNewRun(false)} />
        ) : null}

        <div className="bw-console__metrics">
          {metrics.map((metric) => (
            <div className="bw-console__metric" key={metric.label}>
              <div className="l">{metric.label}</div>
              <div className="v">{metric.value}</div>
              {metric.delta ? <div className={`d bw-${metric.trend}`}>{metric.delta}</div> : null}
            </div>
          ))}
        </div>

        {isLoading && sortedRuns.length === 0 ? (
          <div className="bw-console__empty">Loading production runs…</div>
        ) : sortedRuns.length === 0 ? (
          <div className="bw-console__empty">
            No production runs yet.{' '}
            {sources.length === 0 ? (
              <button type="button" className="bw-console__cta bw-console__cta--ghost" onClick={onGoToSources}>
                Upload a source
              </button>
            ) : (
              <button type="button" className="bw-console__cta bw-console__cta--ghost" onClick={() => setShowNewRun(true)}>
                Start your first run
              </button>
            )}
          </div>
        ) : (
          <div className="bw-console__split">
            <section className="bw-console__panel">
              <div className="bw-console__panel-head">
                <h3>Pipeline runs</h3>
                <span className="bw-count">{sortedRuns.length}</span>
              </div>
              {sortedRuns.map((run) => {
                const progress = productionRunProgress(run, stageRunsByRunId[run.id] ?? [])
                const apiRequestCount = flattenApiRequests([run], stageRunsByRunId, sources).length
                const runCost = productionRunCostUsd(run, stageRunsByRunId[run.id] ?? [])
                return (
                  <button
                    key={run.id}
                    className={`bw-console__runrow${run.id === activeId ? ' is-active' : ''}`}
                    onClick={() => setActiveId(run.id)}
                  >
                    <span className={`bw-dot bw-dot--${run.status}`} />
                    <span>
                      <div className="title">{productionRunLabel(run, sources)}</div>
                      <div className="sub">
                        {run.id.slice(0, 8).toUpperCase()} · {apiRequestCount} API requests
                        {runCost > 0 ? ` · ${formatCostUsd(runCost)}` : ''} ·{' '}
                        {formatDateTime(run.created_at)}
                      </div>
                      {run.status === 'running' || run.status === 'queued' ? (
                        <div className="bw-console__progress">
                          <span style={{ width: `${progress}%` }} />
                        </div>
                      ) : null}
                    </span>
                    <span className="right">
                      <span className={`bw-console__statepill bw-state--${run.status}`}>
                        {statusLabel(run.status)}
                      </span>
                    </span>
                  </button>
                )
              })}
            </section>

            {active ? (
              <ConsoleDetail run={active} />
            ) : (
              <section className="bw-console__panel">
                <div className="bw-console__empty">Select a run to view details.</div>
              </section>
            )}
          </div>
        )}
      </div>
    </>
  )
}
