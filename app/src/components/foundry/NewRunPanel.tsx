import { useState } from 'react'
import { useWorkspaceData } from '../../features/workspace/workspaceDataContext'
import { sourceTitle } from '../../lib/foundryMappers'
import {
  ARTIFACT_OPTIONS,
  ASSESSMENT_ARTIFACT_OPTIONS,
} from '../../lib/workspaceApi'
import { ErrorBanner } from './ErrorBanner'

interface NewRunPanelProps {
  onClose: () => void
  onCreated: () => void
}

export function NewRunPanel({ onClose, onCreated }: NewRunPanelProps) {
  const { sources, createProductionRun } = useWorkspaceData()
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([])
  const [selectedArtifacts, setSelectedArtifacts] = useState<string[]>([])
  const [selectedAssessments, setSelectedAssessments] = useState<string[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const toggleSource = (id: string) => {
    setSelectedSourceIds((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    )
  }

  const toggleArtifact = (value: string) => {
    setSelectedArtifacts((current) =>
      current.includes(value) ? current.filter((item) => item !== value) : [...current, value],
    )
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
    targetArtifacts.push(...selectedArtifacts)
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
    <section className="as-console__panel" style={{ marginBottom: 'var(--space-5)' }}>
      <div className="as-console__panel-head">
        <h3>New production run</h3>
        <button type="button" className="as-console__cta as-console__cta--ghost" onClick={onClose}>
          Cancel
        </button>
      </div>
      <div style={{ padding: '0 18px 18px' }}>
        {sources.length === 0 ? (
          <p className="as-console__empty">Upload a source before starting a production run.</p>
        ) : (
          <>
            <p className="as-console__field-label">Sources</p>
            <div className="as-console__chips" style={{ marginBottom: 20 }}>
              {sources.map((source) => (
                <button
                  key={source.id}
                  type="button"
                  className={`as-console__chip${selectedSourceIds.includes(source.id) ? ' is-active' : ''}`}
                  onClick={() => toggleSource(source.id)}
                >
                  {sourceTitle(source)}
                </button>
              ))}
            </div>

            <p className="as-console__field-label">Artifacts</p>
            <div className="as-console__chips" style={{ marginBottom: 20 }}>
              {ARTIFACT_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  className={`as-console__chip${selectedArtifacts.includes(option.value) ? ' is-active' : ''}`}
                  onClick={() => toggleArtifact(option.value)}
                >
                  {option.label}
                </button>
              ))}
            </div>

            <p className="as-console__field-label">Assessments</p>
            <div className="as-console__chips" style={{ marginBottom: 20 }}>
              {ASSESSMENT_ARTIFACT_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  className={`as-console__chip${selectedAssessments.includes(option.value) ? ' is-active' : ''}`}
                  onClick={() => toggleAssessment(option.value)}
                >
                  {option.label}
                </button>
              ))}
            </div>
            {submitError ? <ErrorBanner message={submitError} /> : null}
            <button
              type="button"
              className="as-console__cta as-console__run-submit"
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
