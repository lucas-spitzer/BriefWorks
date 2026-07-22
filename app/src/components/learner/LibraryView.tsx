import { Headphones, HelpCircle, Layers, Lightbulb } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWorkspaceData } from '../../features/workspace/workspaceDataContext'
import {
  filterOutputs,
  sortOutputs,
  useOutputs,
  type OutputItem,
  type OutputSort,
  type OutputType,
} from '../../lib/learnerOutputs'
import { OutputFilterBar } from './OutputFilterBar'
import { StudyHead } from './StudySessionChrome'
import type { LearnerPage, LearnerScope } from './types'

const KIND_META: Record<
  OutputItem['kind'],
  { label: string; cls: string; icon: typeof Layers }
> = {
  artifact: { label: 'Artifact', cls: 'lib__tchip--art', icon: Headphones },
  flashcard: { label: 'Flashcard', cls: 'lib__tchip--flash', icon: Layers },
  question: { label: 'Question', cls: 'lib__tchip--q', icon: HelpCircle },
  scenario: { label: 'Scenario', cls: 'lib__tchip--scn', icon: Lightbulb },
}

function openLabel(item: OutputItem): string {
  if (item.kind === 'artifact') return item.isAudio ? 'Download' : 'Open'
  if (item.kind === 'flashcard') return 'Study'
  return 'Open'
}

export function LibraryView({
  onOpen,
}: {
  onOpen: (page: LearnerPage, scope: LearnerScope) => void
}) {
  const { items, sources } = useOutputs()
  const { downloadArtifact } = useWorkspaceData()
  const navigate = useNavigate()

  const [search, setSearch] = useState('')
  const [type, setType] = useState<OutputType>('all')
  const [sourceId, setSourceId] = useState<string | null>(null)
  const [sort, setSort] = useState<OutputSort>('source')

  const filtered = useMemo(
    () => sortOutputs(filterOutputs(items, { search, type, sourceId }), sort),
    [items, search, type, sourceId, sort],
  )

  const groups = useMemo(() => {
    if (sort !== 'source') return null
    const map = new Map<string, OutputItem[]>()
    for (const item of filtered) {
      const list = map.get(item.sourceName) ?? []
      list.push(item)
      map.set(item.sourceName, list)
    }
    return [...map.entries()]
  }, [filtered, sort])

  const handleOpen = (item: OutputItem) => {
    if (item.kind === 'artifact') {
      if (item.isAudio) void downloadArtifact(item.id)
      else if (item.sourceId) navigate(`/app/reader/${item.sourceId}`)
      return
    }
    if (item.runnerPage) onOpen(item.runnerPage, { sourceId: item.sourceId, targetId: item.id })
  }

  return (
    <section className="lib study-session">
      <StudyHead
        eyebrow="Workspace catalog"
        title="Library"
        description="Search, filter, and open every artifact, flashcard, question, and scenario in this workspace."
        stats={[
          { value: filtered.length, label: 'outputs' },
          { value: sources.length, label: 'sources' },
        ]}
      />

      <OutputFilterBar
        search={search}
        onSearch={setSearch}
        type={type}
        onType={setType}
        sourceId={sourceId}
        onSource={setSourceId}
        sort={sort}
        onSort={setSort}
        sources={sources}
        searchPlaceholder="Search flashcards, questions, scenarios, artifacts…"
      />

      {filtered.length === 0 ? (
        <div className="lib__empty">
          <p className="lib__empty-title">No matching outputs</p>
          <p className="lib__empty-copy">
            Adjust the filters, or generate material for a source in the console.
          </p>
        </div>
      ) : groups ? (
        groups.map(([sourceName, list]) => (
          <div key={sourceName}>
            <div className="lib__band">
              <h3 className="lib__band-title">{sourceName}</h3>
              <span className="lib__band-line" />
              <span className="lib__band-count">{list.length} outputs</span>
            </div>
            <CardGrid items={list} onOpen={handleOpen} />
          </div>
        ))
      ) : (
        <CardGrid items={filtered} onOpen={handleOpen} />
      )}
    </section>
  )
}

function CardGrid({ items, onOpen }: { items: OutputItem[]; onOpen: (item: OutputItem) => void }) {
  return (
    <div className="lib__grid">
      {items.map((item) => {
        const meta = KIND_META[item.kind]
        const Icon = meta.icon
        return (
          <article key={`${item.kind}-${item.id}`} className="lib__card">
            <span className={`lib__tchip ${meta.cls}`}>
              <Icon size={12} aria-hidden="true" />
              {meta.label}
            </span>
            <p className="lib__pv">{item.title}</p>
            <div className="lib__fill" />
            <div className="lib__foot">
              <div className="lib__meta">
                <span>{item.sourceName}</span>
              </div>
              <button type="button" className="lib__open" onClick={() => onOpen(item)}>
                {openLabel(item)}
              </button>
            </div>
          </article>
        )
      })}
    </div>
  )
}
