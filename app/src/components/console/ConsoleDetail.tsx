import { useWorkspaceData } from '../../features/workspace/workspaceDataContext'
import { useLiveTick } from '../../hooks/useLiveTick'
import {
  artifactFormatLabel,
  artifactKindLabel,
  formatBytes,
  formatCostUsd,
  formatDuration,
  statusLabel,
} from '../../lib/consoleFormat'
import {
  pipelineStepLabel,
  productionRunCostUsd,
  productionRunDurationSec,
  productionRunLabel,
  productionRunProgress,
  skillRunCostUsd,
  skillRunDisplayName,
  skillRunDurationSec,
  skillRunElevenLabsTokens,
  skillRunSummary,
  skillRunTokens,
} from '../../lib/consoleMappers'
import type { ProductionRun } from '../../lib/workspaceApi'
import { moduleLabel, pipelineStepModuleLabel } from './moduleLabel'

interface ConsoleDetailProps {
  run: ProductionRun
}

export function ConsoleDetail({ run }: ConsoleDetailProps) {
  const { sources, skillRunsByRunId, artifacts, wikiEntries, downloadArtifact } = useWorkspaceData()
  const skillRuns = skillRunsByRunId[run.id] ?? []
  const runArtifacts = artifacts.filter((artifact) => artifact.production_run_id === run.id)
  const hasLiveDuration =
    run.status === 'queued' ||
    run.status === 'running' ||
    skillRuns.some((skill) => skill.status === 'queued' || skill.status === 'running')
  useLiveTick(hasLiveDuration)
  const progress = productionRunProgress(run)
  const durationSec = productionRunDurationSec(run)
  const runCost = productionRunCostUsd(run, skillRuns)

  return (
    <section className="bw-console__panel">
      <div className="bw-console__panel-head">
        <h3>Run detail</h3>
        <span className="bw-count">{run.id.slice(0, 8).toUpperCase()}</span>
      </div>
      <div className="bw-console__detail">
        <h4>{productionRunLabel(run, sources)}</h4>
        <div className="meta">
          {statusLabel(run.status)} · {formatDuration(durationSec)} · {progress}% complete
          {runCost > 0 ? ` · ${formatCostUsd(runCost)}` : ''}
          {run.target_artifacts.length
            ? ` · target ${run.target_artifacts.map((kind) => artifactKindLabel(kind)).join(', ')}`
            : ' · ingest only'}
        </div>

        {run.error ? (
          <div
            className="bw-console__chip"
            style={{
              borderColor: 'var(--color-scarlet)',
              color: '#ff8b8b',
              background: 'rgba(148,0,0,0.16)',
              marginTop: 14,
            }}
          >
            ⚠ {run.error}
          </div>
        ) : null}

        <div style={{ height: 18 }} />

        {run.pipeline.map((step) => (
          <div className="bw-console__step" key={step.step}>
            <span className={`bw-console__step-dot bw-console__step-dot--${step.status}`}>
              {step.status === 'completed' ? '✓' : step.status === 'failed' ? '✕' : '•'}
            </span>
            <div className="bw-console__step-body">
              <div className="name">
                {pipelineStepLabel(step)}{' '}
                {step.module ? (
                  <span className="bw-console__module-tag">{pipelineStepModuleLabel(step)}</span>
                ) : null}
              </div>
              <div className="desc">{step.detail ?? statusLabel(step.status)}</div>
            </div>
          </div>
        ))}

        {skillRuns.length > 0 ? (
          <>
            <div className="bw-console__panel-head" style={{ padding: '14px 0 4px', borderBottom: 0 }}>
              <h3 style={{ fontSize: '0.86rem' }}>Skill runs</h3>
            </div>
            {skillRuns.map((skill) => {
              const tokens = skillRunTokens(skill)
              const elevenlabsTokens = skillRunElevenLabsTokens(skill)
              const costUsd = skillRunCostUsd(skill)
              return (
                <div className="bw-console__step" key={skill.id}>
                  <span className={`bw-console__step-dot bw-console__step-dot--${skill.status}`}>
                    {skill.status === 'completed' ? '✓' : skill.status === 'failed' ? '✕' : '•'}
                  </span>
                  <div className="bw-console__step-body">
                    <div className="name">
                      {skillRunDisplayName(skill)}{' '}
                      <span className="bw-console__module-tag">{moduleLabel(skill.module)}</span>
                    </div>
                    <div className="desc">{skillRunSummary(skill)}</div>
                    <div className="stats">
                      {skill.model ? <span>{skill.model}</span> : null}
                      <span>{formatDuration(skillRunDurationSec(skill))}</span>
                      {tokens.in + tokens.out > 0 ? (
                        <span>{((tokens.in + tokens.out) / 1000).toFixed(1)}K tok</span>
                      ) : elevenlabsTokens > 0 ? (
                        <span>{(elevenlabsTokens / 1000).toFixed(1)}K EL tok</span>
                      ) : null}
                      {costUsd > 0 ? <span>{formatCostUsd(costUsd)}</span> : null}
                    </div>
                  </div>
                </div>
              )
            })}
          </>
        ) : null}

        {runArtifacts.length > 0 ? (
          <>
            <div className="bw-console__panel-head" style={{ padding: '4px 0', borderBottom: 0 }}>
              <h3 style={{ fontSize: '0.86rem' }}>Artifacts</h3>
            </div>
            {runArtifacts.map((artifact) => (
              <button
                type="button"
                className="bw-console__artifact"
                key={artifact.id}
                onClick={() => void downloadArtifact(artifact.id)}
              >
                <span className="ic">{artifactFormatLabel(artifact.format)}</span>
                <span>
                  <div className="t">{artifact.filename}</div>
                  <div className="s">
                    {artifactKindLabel(artifact.artifact_type)} · {formatBytes(artifact.file_size_bytes)}
                  </div>
                </span>
              </button>
            ))}
          </>
        ) : null}

        {wikiEntries.length > 0 ? (
          <>
            <div className="bw-console__panel-head" style={{ padding: '14px 0 4px', borderBottom: 0 }}>
              <h3 style={{ fontSize: '0.86rem' }}>Wiki entries · {wikiEntries.length}</h3>
            </div>
            <div className="bw-console__chips">
              {wikiEntries.slice(0, 8).map((entry) => (
                <span className="bw-console__chip" key={entry.id}>
                  {entry.preferred_label}
                  <span style={{ opacity: 0.65, marginLeft: 6 }}>{entry.entry_kind}</span>
                </span>
              ))}
            </div>
          </>
        ) : null}
      </div>
    </section>
  )
}
