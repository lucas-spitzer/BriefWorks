import { useMemo, useState } from 'react'
import { useWorkspaceData } from '../../features/workspace/workspaceDataContext'
import { formatDate, formatDateTime, formatDuration, statusLabel } from '../../lib/consoleFormat'
import {
  flattenSkillRuns,
  skillRunDisplayName,
  skillRunDurationSec,
  skillRunSummary,
  skillRunTokens,
} from '../../lib/consoleMappers'
import { ConsoleViewToggle } from './ConsoleViewToggle'
import { ErrorBanner } from './ErrorBanner'
import { moduleLabel } from './moduleLabel'
import type { ConsoleView } from './types'

interface ConsoleSkillsProps {
  onGoToOps: () => void
}

export function ConsoleSkills({ onGoToOps }: ConsoleSkillsProps) {
  const { productionRuns, skillRunsByRunId, sources, isLoading, error } = useWorkspaceData()
  const [query, setQuery] = useState('')
  const [view, setView] = useState<ConsoleView>('grid')

  const skillRuns = useMemo(
    () => flattenSkillRuns(productionRuns, skillRunsByRunId, sources),
    [productionRuns, skillRunsByRunId, sources],
  )

  const filtered = useMemo(() => {
    const q = query.toLowerCase()
    return skillRuns.filter(
      (skill) =>
        skillRunDisplayName(skill).toLowerCase().includes(q) ||
        skill.skill_id.includes(q) ||
        skill.runLabel.toLowerCase().includes(q) ||
        moduleLabel(skill.module).toLowerCase().includes(q),
    )
  }, [skillRuns, query])

  return (
    <>
      <header className="bw-console__header">
        <div>
          <div className="bw-console__eyebrow">Execution Log</div>
          <h2>Skill Runs</h2>
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
            placeholder="Search skill runs by name, module, or production run…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <span className="bw-count">{filtered.length} runs</span>
        </div>
        {isLoading && filtered.length === 0 ? (
          <div className="bw-console__empty">Loading skill runs…</div>
        ) : filtered.length === 0 ? (
          <div className="bw-console__empty">No skill runs yet. Start a production run from OPS.</div>
        ) : view === 'list' ? (
          <section className="bw-console__panel">
            <table className="bw-console__table">
              <thead>
                <tr>
                  <th>Skill</th>
                  <th>Module</th>
                  <th>Version</th>
                  <th>Model</th>
                  <th>Status</th>
                  <th>Duration</th>
                  <th>Tokens</th>
                  <th>Run</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((skill) => {
                  const tokens = skillRunTokens(skill)
                  return (
                    <tr key={skill.id}>
                      <td>
                        <div className="bw-console__listname">
                          <span>
                            <div className="t">{skillRunDisplayName(skill)}</div>
                            <div className="s">
                              {skill.started_at ? formatDateTime(skill.started_at) : '—'}
                            </div>
                          </span>
                        </div>
                      </td>
                      <td>{moduleLabel(skill.module)}</td>
                      <td className="num">{skill.skill_version}</td>
                      <td className="num">{skill.model ?? '—'}</td>
                      <td>
                        <span className={`bw-console__statepill bw-state--${skill.status}`}>
                          {statusLabel(skill.status)}
                        </span>
                      </td>
                      <td className="num">{formatDuration(skillRunDurationSec(skill))}</td>
                      <td className="num">
                        {tokens.in + tokens.out > 0
                          ? `${((tokens.in + tokens.out) / 1000).toFixed(1)}K`
                          : '—'}
                      </td>
                      <td>{skill.runId.slice(0, 8).toUpperCase()}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </section>
        ) : (
          <div className="bw-console__sources">
            {filtered.map((skill) => {
              const tokens = skillRunTokens(skill)
              return (
                <div
                  className="bw-console__panel bw-console__artifact-card bw-console__skill-card"
                  key={skill.id}
                  style={{ padding: 18 }}
                >
                  <div>
                    <div style={{ fontFamily: 'var(--bw-grotesk)', fontWeight: 600, color: '#fff' }}>
                      {skillRunDisplayName(skill)}{' '}
                      <span className="bw-console__module-tag">{moduleLabel(skill.module)}</span>
                    </div>
                    <div
                      style={{
                        fontFamily: 'var(--bw-mono)',
                        fontSize: '0.7rem',
                        color: '#8aa1ab',
                        marginTop: 3,
                      }}
                    >
                      {skill.skill_id} · v{skill.skill_version}
                    </div>
                  </div>
                  <p style={{ fontSize: '0.84rem', color: '#b6c4cb', marginTop: 12, lineHeight: 1.5 }}>
                    {skillRunSummary(skill)}
                  </p>
                  <div className="stats">
                    {skill.model ? <span>{skill.model}</span> : null}
                    <span>{formatDuration(skillRunDurationSec(skill))}</span>
                    {tokens.in + tokens.out > 0 ? (
                      <span>{((tokens.in + tokens.out) / 1000).toFixed(1)}K tok</span>
                    ) : null}
                  </div>
                  <div className="bw-console__card-fill" aria-hidden="true" />
                  <div className="bw-console__artifact-foot">
                    <span className="seg">{skill.runId.slice(0, 8).toUpperCase()}</span>
                    <span className="seg">
                      {skill.started_at ? formatDate(skill.started_at) : '—'}
                    </span>
                    <span className="seg">
                      <span className={`bw-console__statepill bw-state--${skill.status}`}>
                        {statusLabel(skill.status)}
                      </span>
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
