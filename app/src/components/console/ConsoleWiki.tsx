import { useCallback, useEffect, useMemo, useState } from 'react'
import { useWorkspace } from '../../features/workspace/workspaceContext'
import { useWorkspaceData } from '../../features/workspace/workspaceDataContext'
import { ApiError } from '../../lib/apiClient'
import { formatDate } from '../../lib/consoleFormat'
import { sourceTitle } from '../../lib/consoleMappers'
import {
  commitIngestBatch,
  createIngestBatch,
  deprecateWikiEntry,
  discardIngestBatch,
  getIngestBatch,
  listIngestBatches,
  updateIngestBatch,
  updateWikiEntry,
  type WikiIngestBatch,
  type WikiIngestEntry,
} from '../../lib/wikiApi'
import type { WikiEntry } from '../../lib/workspaceApi'
import { ErrorBanner } from './ErrorBanner'

const ENTRY_KINDS = ['term', 'concept', 'insight'] as const
const IMPORTANCE_LEVELS = ['essential', 'supporting', 'contextual'] as const

const RESOLUTION_HINTS: Record<string, string> = {
  new: 'New entry',
  merge: 'Merges into an existing entry',
  conflict: 'Conflicts with an existing definition — your definition wins on commit',
}

function KindPill({ value }: { value: string }) {
  return <span className={`bw-wiki__pill bw-wiki__pill--${value}`}>{value}</span>
}

function EvidencePill({ status }: { status: string }) {
  return <span className={`bw-wiki__pill bw-wiki__pill--ev-${status}`}>{status}</span>
}

// ---------------------------------------------------------------------------
// Add knowledge: notes dump form
// ---------------------------------------------------------------------------

function AddKnowledgePanel({
  onClose,
  onCreated,
}: {
  onClose: () => void
  onCreated: (batch: WikiIngestBatch) => void
}) {
  const { activeWorkspace } = useWorkspace()
  const { sources } = useWorkspaceData()
  const [notes, setNotes] = useState('')
  const [sourceId, setSourceId] = useState<string | null>(null)
  const [chapterHint, setChapterHint] = useState('')
  const [title, setTitle] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async () => {
    if (!activeWorkspace) return
    if (!notes.trim()) {
      setError('Paste some notes first.')
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      const batch = await createIngestBatch(activeWorkspace.id, {
        notes,
        source_id: sourceId,
        chapter_hint: chapterHint.trim() || null,
        title: title.trim() || null,
      })
      onCreated(batch)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Failed to structure notes.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="bw-console__panel" style={{ marginBottom: 'var(--space-5)' }}>
      <div className="bw-console__panel-head">
        <h3>Add knowledge</h3>
        <button type="button" className="bw-console__cta bw-console__cta--ghost" onClick={onClose}>
          Cancel
        </button>
      </div>
      <div style={{ padding: '0 18px 18px' }}>
        <p className="bw-console__field-hint" style={{ marginBottom: 14 }}>
          Paste your reading notes — terminology, concepts, and insights in any shape.
          One structuring pass turns them into proposed wiki entries for review;
          nothing is saved to the wiki until you commit.
        </p>

        <p className="bw-console__field-label">Source (enables evidence linking)</p>
        <div className="bw-console__chips" style={{ marginBottom: 16 }}>
          {sources.map((source) => (
            <button
              key={source.id}
              type="button"
              className={`bw-console__chip${sourceId === source.id ? ' is-active' : ''}`}
              onClick={() => setSourceId((current) => (current === source.id ? null : source.id))}
            >
              {sourceTitle(source)}
            </button>
          ))}
        </div>

        <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          <label style={{ flex: '1 1 220px' }}>
            <p className="bw-console__field-label">Batch title (optional)</p>
            <input
              className="bw-wiki__input"
              placeholder="Ch. 3 reading notes"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
            />
          </label>
          <label style={{ flex: '0 1 220px' }}>
            <p className="bw-console__field-label">Chapter hint (optional)</p>
            <input
              className="bw-wiki__input"
              placeholder="3 or a title fragment"
              value={chapterHint}
              onChange={(event) => setChapterHint(event.target.value)}
              disabled={!sourceId}
            />
          </label>
        </div>

        <p className="bw-console__field-label">Notes</p>
        <textarea
          className="bw-wiki__textarea"
          rows={10}
          placeholder={
            'Enemy system — Warden: the enemy is a system of interdependent parts…\n\ninsight: strategic paralysis beats attrition…'
          }
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
        />

        {error ? <ErrorBanner message={error} /> : null}
        <button
          type="button"
          className="bw-console__cta bw-console__run-submit"
          disabled={isSubmitting}
          onClick={() => void handleSubmit()}
        >
          {isSubmitting ? 'Structuring…' : 'Structure notes'}
        </button>
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Review: draft batch editor
// ---------------------------------------------------------------------------

function ReviewBatchPanel({
  batch,
  onBatchChange,
  onDone,
}: {
  batch: WikiIngestBatch
  onBatchChange: (batch: WikiIngestBatch) => void
  onDone: () => void
}) {
  const { activeWorkspace } = useWorkspace()
  const { refresh } = useWorkspaceData()
  const [entries, setEntries] = useState<WikiIngestEntry[]>(batch.entries)
  const [isBusy, setIsBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const includedCount = entries.filter((entry) => entry.include).length

  const patchEntry = (index: number, patch: Partial<WikiIngestEntry>) => {
    setEntries((current) =>
      current.map((entry) => (entry.index === index ? { ...entry, ...patch } : entry)),
    )
  }

  const saveDraft = async (): Promise<WikiIngestBatch | null> => {
    if (!activeWorkspace) return null
    const updated = await updateIngestBatch(activeWorkspace.id, batch.id, { entries })
    onBatchChange(updated)
    setEntries(updated.entries)
    return updated
  }

  const handleSave = async () => {
    setIsBusy(true)
    setError(null)
    setNotice(null)
    try {
      await saveDraft()
      setNotice('Draft saved.')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Failed to save draft.')
    } finally {
      setIsBusy(false)
    }
  }

  const handleCommit = async () => {
    if (!activeWorkspace) return
    setIsBusy(true)
    setError(null)
    setNotice(null)
    try {
      await saveDraft()
      const result = await commitIngestBatch(activeWorkspace.id, batch.id)
      onBatchChange(result.batch)
      await refresh()
      setNotice(
        `Committed: ${result.inserted_entry_ids.length} new, ${result.updated_entry_ids.length} merged.`,
      )
      onDone()
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 409) {
        // The wiki changed since review; the server refreshed the batch.
        const refreshed = await getIngestBatch(activeWorkspace.id, batch.id)
        onBatchChange(refreshed)
        setEntries(refreshed.entries)
        setError(
          'The wiki changed since this batch was structured. Resolutions were refreshed — review the highlighted entries and commit again.',
        )
      } else {
        setError(caught instanceof Error ? caught.message : 'Failed to commit batch.')
      }
    } finally {
      setIsBusy(false)
    }
  }

  const handleDiscard = async () => {
    if (!activeWorkspace) return
    setIsBusy(true)
    setError(null)
    try {
      await discardIngestBatch(activeWorkspace.id, batch.id)
      onDone()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Failed to discard batch.')
    } finally {
      setIsBusy(false)
    }
  }

  return (
    <section className="bw-console__panel" style={{ marginBottom: 'var(--space-5)' }}>
      <div className="bw-console__panel-head">
        <h3>Review — {batch.title}</h3>
        <span className="bw-count">
          {includedCount}/{entries.length} included
          {batch.chapter ? ` · ${batch.chapter.title}` : ''}
        </span>
      </div>
      <div style={{ padding: '0 18px 18px' }}>
        {entries.map((entry) => (
          <div
            key={entry.index}
            className={`bw-wiki__review-row${entry.include ? '' : ' is-excluded'}`}
          >
            <div className="bw-wiki__review-head">
              <label className="bw-wiki__include">
                <input
                  type="checkbox"
                  checked={entry.include}
                  onChange={(event) => patchEntry(entry.index, { include: event.target.checked })}
                />
              </label>
              <input
                className="bw-wiki__input bw-wiki__input--label"
                value={entry.label}
                onChange={(event) => patchEntry(entry.index, { label: event.target.value })}
              />
              <select
                className="bw-console__select bw-console__select--sm bw-wiki__select"
                value={entry.entry_kind}
                onChange={(event) =>
                  patchEntry(entry.index, {
                    entry_kind: event.target.value as WikiIngestEntry['entry_kind'],
                  })
                }
              >
                {ENTRY_KINDS.map((kind) => (
                  <option key={kind} value={kind}>
                    {kind}
                  </option>
                ))}
              </select>
              <select
                className="bw-console__select bw-console__select--sm bw-wiki__select"
                value={entry.importance}
                onChange={(event) =>
                  patchEntry(entry.index, {
                    importance: event.target.value as WikiIngestEntry['importance'],
                  })
                }
              >
                {IMPORTANCE_LEVELS.map((level) => (
                  <option key={level} value={level}>
                    {level}
                  </option>
                ))}
              </select>
              <span
                className={`bw-wiki__pill bw-wiki__pill--${entry.resolution}`}
                title={RESOLUTION_HINTS[entry.resolution]}
              >
                {entry.resolution}
              </span>
              <EvidencePill status={entry.evidence_status} />
            </div>

            <textarea
              className="bw-wiki__textarea bw-wiki__textarea--definition"
              rows={2}
              value={entry.definition}
              onChange={(event) => patchEntry(entry.index, { definition: event.target.value })}
            />

            {entry.resolution === 'conflict' && entry.existing_definition ? (
              <p className="bw-wiki__meta bw-wiki__meta--conflict">
                Existing definition: “{entry.existing_definition}” — committing replaces it with
                yours.
              </p>
            ) : null}

            {entry.similar_entries.length > 0 ? (
              <p className="bw-wiki__meta">
                Possibly duplicates:{' '}
                {entry.similar_entries.map((similar) => similar.label).join(', ')}
              </p>
            ) : null}

            {entry.evidence.length > 0 ? (
              <p className="bw-wiki__meta">
                Evidence:{' '}
                {entry.evidence.map((record, position) => (
                  <span key={record.segment_id}>
                    {position > 0 ? ' · ' : ''}
                    {record.reader_link ? (
                      <a href={record.reader_link} target="_blank" rel="noreferrer">
                        p.{record.page ?? '?'} ({Math.round((record.similarity ?? 0) * 100)}%)
                      </a>
                    ) : (
                      `p.${record.page ?? '?'}`
                    )}
                  </span>
                ))}
              </p>
            ) : null}

            {entry.note_excerpt ? (
              <p className="bw-wiki__meta bw-wiki__meta--excerpt">“{entry.note_excerpt}”</p>
            ) : null}
          </div>
        ))}

        {batch.unparsed_fragments.length > 0 ? (
          <div className="bw-wiki__fragments">
            <p className="bw-console__field-label">Unstructured leftovers (nothing was dropped silently)</p>
            {batch.unparsed_fragments.map((fragment) => (
              <p key={fragment} className="bw-wiki__meta">
                “{fragment}”
              </p>
            ))}
          </div>
        ) : null}

        {error ? <ErrorBanner message={error} /> : null}
        {notice ? <p className="bw-wiki__notice">{notice}</p> : null}

        <div style={{ display: 'flex', gap: 10, marginTop: 14 }}>
          <button
            type="button"
            className="bw-console__cta"
            disabled={isBusy || includedCount === 0}
            onClick={() => void handleCommit()}
          >
            {isBusy ? 'Working…' : `Commit ${includedCount} to wiki`}
          </button>
          <button
            type="button"
            className="bw-console__cta bw-console__cta--ghost"
            disabled={isBusy}
            onClick={() => void handleSave()}
          >
            Save draft
          </button>
          <button
            type="button"
            className="bw-console__cta bw-console__cta--ghost"
            disabled={isBusy}
            onClick={() => void handleDiscard()}
          >
            Discard batch
          </button>
        </div>
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Entry browser with inline editing
// ---------------------------------------------------------------------------

function EntryRow({
  entry,
  onChanged,
}: {
  entry: WikiEntry
  onChanged: () => Promise<void>
}) {
  const { activeWorkspace } = useWorkspace()
  const [isEditing, setIsEditing] = useState(false)
  const [label, setLabel] = useState(entry.preferred_label)
  const [definition, setDefinition] = useState(entry.definition)
  const [kind, setKind] = useState(entry.entry_kind)
  const [importance, setImportance] = useState(entry.importance)
  const [isBusy, setIsBusy] = useState(false)

  const save = async () => {
    if (!activeWorkspace) return
    setIsBusy(true)
    try {
      await updateWikiEntry(activeWorkspace.id, entry.id, {
        preferred_label: label,
        definition,
        entry_kind: kind,
        importance,
      })
      await onChanged()
      setIsEditing(false)
    } finally {
      setIsBusy(false)
    }
  }

  const deprecate = async () => {
    if (!activeWorkspace) return
    setIsBusy(true)
    try {
      await deprecateWikiEntry(activeWorkspace.id, entry.id)
      await onChanged()
    } finally {
      setIsBusy(false)
    }
  }

  if (isEditing) {
    return (
      <tr>
        <td>
          <input
            className="bw-wiki__input bw-wiki__input--label"
            value={label}
            onChange={(event) => setLabel(event.target.value)}
          />
        </td>
        <td colSpan={2}>
          <textarea
            className="bw-wiki__textarea bw-wiki__textarea--definition"
            rows={2}
            value={definition}
            onChange={(event) => setDefinition(event.target.value)}
          />
        </td>
        <td>
          <select
            className="bw-console__select bw-console__select--sm bw-wiki__select"
            value={kind}
            onChange={(event) => setKind(event.target.value)}
          >
            {ENTRY_KINDS.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </td>
        <td>
          <select
            className="bw-console__select bw-console__select--sm bw-wiki__select"
            value={importance}
            onChange={(event) => setImportance(event.target.value)}
          >
            {IMPORTANCE_LEVELS.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </td>
        <td>
          <div className="bw-wiki__actions">
            <button
              type="button"
              className="bw-wiki__action bw-wiki__action--save"
              disabled={isBusy}
              onClick={() => void save()}
            >
              Save
            </button>
            <button
              type="button"
              className="bw-wiki__action bw-wiki__action--cancel"
              disabled={isBusy}
              onClick={() => setIsEditing(false)}
            >
              Cancel
            </button>
          </div>
        </td>
      </tr>
    )
  }

  // Committed evidence keeps a reader deep link (source + segment sequence
  // index) when the entry was linked against a source during authoring.
  const readerLink = entry.evidence.find((record) => record.reader_link)?.reader_link ?? null

  return (
    <tr className={entry.status !== 'canonical' ? 'bw-wiki__row--muted' : undefined}>
      <td style={{ fontWeight: 600, color: '#fff' }}>
        {entry.preferred_label}
        {readerLink ? (
          <>
            {' '}
            <a
              href={readerLink}
              target="_blank"
              rel="noreferrer"
              className="bw-wiki__reader-link"
              title="Open the cited passage in the Reader"
            >
              ↗
            </a>
          </>
        ) : null}
      </td>
      <td colSpan={2}>{entry.definition}</td>
      <td>
        <KindPill value={entry.entry_kind} />
      </td>
      <td>{entry.importance}</td>
      <td>
        <div className="bw-wiki__actions">
          <button
            type="button"
            className="bw-wiki__action bw-wiki__action--edit"
            disabled={isBusy}
            onClick={() => setIsEditing(true)}
          >
            Edit
          </button>
          {entry.status === 'canonical' ? (
            <button
              type="button"
              className="bw-wiki__action bw-wiki__action--deprecate"
              disabled={isBusy}
              onClick={() => void deprecate()}
              title="Soft delete: the entry stops feeding assessments and the assistant"
            >
              Deprecate
            </button>
          ) : (
            <span className="bw-wiki__pill">{entry.status}</span>
          )}
        </div>
      </td>
    </tr>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export function ConsoleWiki() {
  const { activeWorkspace } = useWorkspace()
  const { wikiEntries, isLoading, error, refresh } = useWorkspaceData()
  const [query, setQuery] = useState('')
  const [showAdd, setShowAdd] = useState(false)
  const [activeBatch, setActiveBatch] = useState<WikiIngestBatch | null>(null)
  const [draftBatches, setDraftBatches] = useState<WikiIngestBatch[]>([])

  const loadDrafts = useCallback(async () => {
    if (!activeWorkspace) return
    const batches = await listIngestBatches(activeWorkspace.id, 'draft')
    setDraftBatches(batches)
  }, [activeWorkspace])

  useEffect(() => {
    void loadDrafts()
  }, [loadDrafts])

  const visibleEntries = useMemo(() => {
    const q = query.toLowerCase()
    return wikiEntries.filter(
      (entry) =>
        entry.status !== 'deprecated' &&
        (entry.preferred_label.toLowerCase().includes(q) ||
          entry.definition.toLowerCase().includes(q)),
    )
  }, [wikiEntries, query])

  const closeReview = () => {
    setActiveBatch(null)
    void loadDrafts()
  }

  return (
    <>
      <header className="bw-console__header">
        <div>
          <div className="bw-console__eyebrow">Knowledge Wiki</div>
          <h2>Curated Entries</h2>
        </div>
        <button
          type="button"
          className="bw-console__cta"
          onClick={() => {
            setShowAdd((current) => !current)
            setActiveBatch(null)
          }}
        >
          Add knowledge
        </button>
      </header>
      <div className="bw-console__scroll">
        {error ? <ErrorBanner message={error} /> : null}

        {showAdd ? (
          <AddKnowledgePanel
            onClose={() => setShowAdd(false)}
            onCreated={(batch) => {
              setShowAdd(false)
              setActiveBatch(batch)
              void loadDrafts()
            }}
          />
        ) : null}

        {activeBatch && activeBatch.status === 'draft' ? (
          <ReviewBatchPanel
            batch={activeBatch}
            onBatchChange={setActiveBatch}
            onDone={closeReview}
          />
        ) : null}

        {!activeBatch && draftBatches.length > 0 ? (
          <section className="bw-console__panel" style={{ marginBottom: 'var(--space-5)' }}>
            <div className="bw-console__panel-head">
              <h3>Draft batches</h3>
              <span className="bw-count">{draftBatches.length}</span>
            </div>
            <table className="bw-console__table">
              <tbody>
                {draftBatches.map((batch) => (
                  <tr key={batch.id}>
                    <td style={{ fontWeight: 600, color: '#fff' }}>{batch.title}</td>
                    <td>{batch.entries.length} entries</td>
                    <td>{formatDate(batch.created_at)}</td>
                    <td>
                      <button
                        type="button"
                        className="bw-console__statepill bw-state--download"
                        onClick={() => setActiveBatch(batch)}
                      >
                        Review
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        ) : null}

        <div className="bw-console__searchbar">
          <span style={{ color: '#6f828b' }}>⌕</span>
          <input
            placeholder="Search wiki entries…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <span className="bw-count">{visibleEntries.length} entries</span>
        </div>

        {isLoading && wikiEntries.length === 0 ? (
          <div className="bw-console__empty">Loading wiki…</div>
        ) : visibleEntries.length === 0 ? (
          <div className="bw-console__empty">
            {query
              ? 'No entries match your search.'
              : 'No wiki entries yet. Read the generated ebook, then paste your notes via “Add knowledge” to curate the wiki that feeds flashcards, quizzes, and scenarios.'}
          </div>
        ) : (
          <section className="bw-console__panel">
            <div className="bw-console__panel-head">
              <h3>Entries</h3>
              <span className="bw-count">{visibleEntries.length}</span>
            </div>
            <table className="bw-console__table">
              <thead>
                <tr>
                  <th>Label</th>
                  <th colSpan={2}>Definition</th>
                  <th>Kind</th>
                  <th>Importance</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {visibleEntries.map((entry) => (
                  <EntryRow key={entry.id} entry={entry} onChanged={refresh} />
                ))}
              </tbody>
            </table>
          </section>
        )}
      </div>
    </>
  )
}
