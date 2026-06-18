import { useState } from 'react'
import { useWorkspaceData } from '../../features/workspace/workspaceDataContext'
import { sourceTitle } from '../../lib/consoleMappers'
import {
  NARRATION_ARTIFACT_OPTIONS,
  REVIEW_ARTIFACT_VALUES,
  REVIEW_PURPOSES,
} from '../../lib/workspaceApi'
import { ErrorBanner } from './ErrorBanner'

interface NewRunPanelProps {
  onClose: () => void
  onCreated: () => void
}

export function NewRunPanel({ onClose, onCreated }: NewRunPanelProps) {
  const { sources, createProductionRun } = useWorkspaceData()
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([])
  const [narrationTarget, setNarrationTarget] = useState<string | null>(null)
  const [includeReview, setIncludeReview] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const toggleSource = (id: string) => {
    setSelectedSourceIds((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    )
  }

  const selectNarration = (value: string) => {
    setNarrationTarget((current) => (current === value ? null : value))
  }

  const handleSubmit = async () => {
    if (!selectedSourceIds.length) {
      setSubmitError('Select at least one source.')
      return
    }

    const targetArtifacts: string[] = []
    if (narrationTarget) {
      targetArtifacts.push(narrationTarget)
    }
    if (includeReview) {
      targetArtifacts.push(...REVIEW_ARTIFACT_VALUES)
    }

    setIsSubmitting(true)
    setSubmitError(null)

    try {
      await createProductionRun({
        source_ids: selectedSourceIds,
        target_artifacts: targetArtifacts,
      })
      onCreated()
      onClose()
    } catch (caught) {
      setSubmitError(caught instanceof Error ? caught.message : 'Failed to create production run.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="bw-console__panel" style={{ marginBottom: 'var(--space-5)' }}>
      <div className="bw-console__panel-head">
        <h3>New production run</h3>
        <button type="button" className="bw-console__cta bw-console__cta--ghost" onClick={onClose}>
          Cancel
        </button>
      </div>
      <div style={{ padding: '0 18px 18px' }}>
        {sources.length === 0 ? (
          <p className="bw-console__empty">Upload a source before starting a production run.</p>
        ) : (
          <>
            <p className="bw-console__field-label">Sources</p>
            <div className="bw-console__chips" style={{ marginBottom: 20 }}>
              {sources.map((source) => (
                <button
                  key={source.id}
                  type="button"
                  className={`bw-console__chip${selectedSourceIds.includes(source.id) ? ' is-active' : ''}`}
                  onClick={() => toggleSource(source.id)}
                >
                  {sourceTitle(source)}
                </button>
              ))}
            </div>

            <p className="bw-console__field-label">Narration output</p>
            <p className="bw-console__field-hint">Choose one. Leave unselected to run ingest only.</p>
            <div className="bw-console__chips" style={{ marginBottom: 20 }}>
              {NARRATION_ARTIFACT_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  className={`bw-console__chip${narrationTarget === option.value ? ' is-active' : ''}`}
                  onClick={() => selectNarration(option.value)}
                >
                  {option.label}
                </button>
              ))}
            </div>

            <p className="bw-console__field-label">Review material</p>
            <div className="bw-console__review-material">
              <button
                type="button"
                className={`bw-console__toggle${includeReview ? ' is-on' : ''}`}
                role="switch"
                aria-checked={includeReview}
                onClick={() => setIncludeReview((current) => !current)}
              >
                <span className="bw-console__toggle-track" aria-hidden="true">
                  <span className="bw-console__toggle-thumb" />
                </span>
                <span className="bw-console__toggle-label">
                  {includeReview ? 'Generating review material' : 'Generate review material'}
                </span>
              </button>
              <div className={`bw-console__purposes${includeReview ? ' is-on' : ''}`}>
                {REVIEW_PURPOSES.map((item) => (
                  <div key={item.label} className="bw-console__purpose">
                    <span className="bw-console__purpose-name">{item.label}</span>
                    <span className="bw-console__purpose-arrow" aria-hidden="true">→</span>
                    <span className="bw-console__purpose-goal">{item.purpose}</span>
                  </div>
                ))}
              </div>
            </div>
            {submitError ? <ErrorBanner message={submitError} /> : null}
            <button
              type="button"
              className="bw-console__cta bw-console__run-submit"
              disabled={isSubmitting}
              onClick={() => void handleSubmit()}
            >
              {isSubmitting ? 'Starting…' : 'Start run'}
            </button>
          </>
        )}
      </div>
    </section>
  )
}
