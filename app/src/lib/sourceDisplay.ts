import type { Source } from './workspaceApi'

/** Filename without its final extension — stable source display identity. */
export function filenameStem(filename: string): string {
  const dot = filename.lastIndexOf('.')
  return dot > 0 ? filename.slice(0, dot) : filename
}

/**
 * Canonical label for a source across console, learner, and run UI.
 * Always derived from the uploaded filename (minus extension).
 */
export function sourceDisplayName(source: Pick<Source, 'filename'>): string {
  return filenameStem(source.filename)
}

function metadataRecord(value: unknown): Record<string, unknown> | null {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>
  }
  return null
}

function metadataString(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const trimmed = value.trim()
  return trimmed || null
}

/**
 * LLM-extracted bibliographic title from source-research.
 * Used for EPUB/narration metadata and detail surfaces — not as the primary UI label.
 */
export function sourceBibliographicTitle(
  source: Pick<Source, 'source_metadata'>,
): string | null {
  const research = metadataRecord(source.source_metadata.research)
  return metadataString(research?.title)
}
