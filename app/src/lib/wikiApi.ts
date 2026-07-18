import { apiRequest } from './apiClient'
import type { WikiEntry } from './workspaceApi'

// Wiki authoring: notes dump → structured draft batch → review → commit.
// Mirrors docs/internal/plans/wiki-authoring-contract.md.

export type WikiIngestResolution = 'new' | 'merge' | 'conflict'
export type WikiIngestEvidenceStatus = 'linked' | 'weak' | 'unlinked'
export type WikiIngestBatchStatus = 'draft' | 'committed' | 'discarded'

export interface WikiIngestEvidence {
  segment_id: string
  sequence_index: number | null
  page: number | null
  similarity: number | null
  preview: string | null
  reader_link: string | null
}

export interface WikiIngestSimilarEntry {
  id: string
  label: string
  similarity: number
}

export interface WikiIngestEntry {
  index: number
  label: string
  entry_kind: 'term' | 'concept' | 'insight'
  definition: string
  aliases: string[]
  pronunciation: string | null
  importance: 'essential' | 'supporting' | 'contextual'
  prerequisite_labels: string[]
  note_excerpt: string
  canonical_slug: string
  resolution: WikiIngestResolution
  existing_entry_id: string | null
  existing_definition: string | null
  similar_entries: WikiIngestSimilarEntry[]
  evidence_status: WikiIngestEvidenceStatus
  evidence: WikiIngestEvidence[]
  include: boolean
}

export interface WikiIngestChapter {
  chapter_id: string
  title: string
  sequence_index: number
}

export interface WikiIngestBatch {
  id: string
  workspace_id: string
  source_id: string | null
  title: string
  raw_notes: string
  chapter_hint: string | null
  chapter: WikiIngestChapter | null
  status: WikiIngestBatchStatus
  entries: WikiIngestEntry[]
  unparsed_fragments: string[]
  model: string | null
  cost_usd: number | null
  committed_entry_ids: string[]
  committed_at: string | null
  created_at: string
  updated_at: string
}

export interface WikiIngestCommitResponse {
  batch: WikiIngestBatch
  inserted_entry_ids: string[]
  updated_entry_ids: string[]
}

export async function createIngestBatch(
  workspaceId: string,
  payload: {
    notes: string
    source_id?: string | null
    chapter_hint?: string | null
    title?: string | null
  },
): Promise<WikiIngestBatch> {
  return apiRequest<WikiIngestBatch>(`/workspaces/${workspaceId}/wiki/ingest-batches`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function listIngestBatches(
  workspaceId: string,
  status?: WikiIngestBatchStatus,
): Promise<WikiIngestBatch[]> {
  const query = status ? `?status=${status}` : ''
  return apiRequest<WikiIngestBatch[]>(
    `/workspaces/${workspaceId}/wiki/ingest-batches${query}`,
  )
}

export async function getIngestBatch(
  workspaceId: string,
  batchId: string,
): Promise<WikiIngestBatch> {
  return apiRequest<WikiIngestBatch>(
    `/workspaces/${workspaceId}/wiki/ingest-batches/${batchId}`,
  )
}

export async function updateIngestBatch(
  workspaceId: string,
  batchId: string,
  payload: { title?: string; entries?: WikiIngestEntry[] },
): Promise<WikiIngestBatch> {
  return apiRequest<WikiIngestBatch>(
    `/workspaces/${workspaceId}/wiki/ingest-batches/${batchId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(payload),
    },
  )
}

export async function commitIngestBatch(
  workspaceId: string,
  batchId: string,
): Promise<WikiIngestCommitResponse> {
  return apiRequest<WikiIngestCommitResponse>(
    `/workspaces/${workspaceId}/wiki/ingest-batches/${batchId}/commit`,
    { method: 'POST' },
  )
}

export async function discardIngestBatch(
  workspaceId: string,
  batchId: string,
): Promise<WikiIngestBatch> {
  return apiRequest<WikiIngestBatch>(
    `/workspaces/${workspaceId}/wiki/ingest-batches/${batchId}/discard`,
    { method: 'POST' },
  )
}

export async function createWikiEntry(
  workspaceId: string,
  payload: {
    preferred_label: string
    definition: string
    entry_kind: string
    importance: string
    aliases?: string[]
    pronunciation?: string | null
  },
): Promise<WikiEntry> {
  return apiRequest<WikiEntry>(`/workspaces/${workspaceId}/wiki/entries`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function updateWikiEntry(
  workspaceId: string,
  entryId: string,
  payload: Partial<{
    preferred_label: string
    definition: string
    entry_kind: string
    importance: string
    aliases: string[]
    pronunciation: string | null
  }>,
): Promise<WikiEntry> {
  return apiRequest<WikiEntry>(`/workspaces/${workspaceId}/wiki/entries/${entryId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export async function deprecateWikiEntry(
  workspaceId: string,
  entryId: string,
): Promise<WikiEntry> {
  return apiRequest<WikiEntry>(`/workspaces/${workspaceId}/wiki/entries/${entryId}`, {
    method: 'DELETE',
  })
}
