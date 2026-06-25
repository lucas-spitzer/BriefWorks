import { useState } from 'react'
import { useWorkspaceData } from '../../features/workspace/workspaceDataContext'
import { sourceTitle } from '../../lib/consoleMappers'
import {
  ASSESSMENT_ARTIFACT_OPTIONS,
  NARRATION_ARTIFACT_OPTIONS,
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
  const [selectedAssessments, setSelectedAssessments] = useState<string[]>([])
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

  const toggleAssessment = (value: string) => {
    setSelectedAssessments((current) =>
      current.includes(value) ? current.filter((item) => item !== value) : [...current, value],
    )
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
    targetArtifacts.push(...selectedAssessments)

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

            <p className="bw-console__field-label">Artifacts</p>
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

            <p className="bw-console__field-label">Assessments</p>
            <div className="bw-console__chips" style={{ marginBottom: 20 }}>
              {ASSESSMENT_ARTIFACT_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  className={`bw-console__chip${selectedAssessments.includes(option.value) ? ' is-active' : ''}`}
                  onClick={() => toggleAssessment(option.value)}
                >
                  {option.label}
                </button>
              ))}
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
