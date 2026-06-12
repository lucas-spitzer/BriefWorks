import type {
  Artifact,
  PipelineStep,
  ProductionRun,
  SkillRun,
  Source,
} from './workspaceApi'
import { documentTypeLabel, formatBytes, mimeLabel } from './consoleFormat'

function metadataRecord(value: unknown): Record<string, unknown> | null {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>
  }
  return null
}

function researchMetadata(source: Source): Record<string, unknown> | null {
  return metadataRecord(source.source_metadata.research)
}

function parseMetadata(source: Source): Record<string, unknown> | null {
  return metadataRecord(source.source_metadata.parse)
}

function metadataString(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const trimmed = value.trim()
  return trimmed || null
}

function filenameStem(filename: string): string {
  const dot = filename.lastIndexOf('.')
  return dot > 0 ? filename.slice(0, dot) : filename
}

export function sourceTitle(source: Source): string {
  const research = researchMetadata(source)
  const identifier = metadataString(research?.identifier)
  if (identifier) return identifier

  const researchedTitle = metadataString(research?.title)
  if (researchedTitle) return researchedTitle

  const meta = source.source_metadata
  const flatTitle = metadataString(meta.title)
  if (flatTitle) return flatTitle

  return filenameStem(source.filename)
}

export function sourceDocumentType(source: Source): string | null {
  const research = researchMetadata(source)
  const researchedType = metadataString(research?.document_type)
  if (researchedType) return documentTypeLabel(researchedType)

  const meta = source.source_metadata
  const flatType = metadataString(meta.document_type)
  return flatType ? documentTypeLabel(flatType) : null
}

export function sourceIssuingAuthority(source: Source): string | null {
  const research = researchMetadata(source)
  const researchedAuthority = metadataString(research?.issuing_authority)
  if (researchedAuthority) return researchedAuthority

  const meta = source.source_metadata
  return metadataString(meta.issuing_authority)
}

export function sourcePages(source: Source): number | null {
  const parse = parseMetadata(source)
  if (typeof parse?.page_count === 'number') return parse.page_count

  const meta = source.source_metadata
  if (typeof meta.pages === 'number') return meta.pages
  return null
}

export function sourceSegments(source: Source): number | null {
  const parse = parseMetadata(source)
  if (typeof parse?.segment_count === 'number') return parse.segment_count
  return null
}

export function sourceConfidence(source: Source): number | null {
  const research = researchMetadata(source)
  const confidence = metadataRecord(research?.confidence)
  if (!confidence) return null

  const values = Object.values(confidence).filter((value): value is number => typeof value === 'number')
  if (!values.length) return null
  return values.reduce((sum, value) => sum + value, 0) / values.length
}

export function productionRunLabel(run: ProductionRun, sources: Source[]): string {
  const titles = run.source_ids
    .map((id) => sources.find((s) => s.id === id))
    .filter((s): s is Source => Boolean(s))
    .map((s) => sourceTitle(s))

  const sourcePart = titles.length ? titles.join(', ') : `${run.source_ids.length} source(s)`
  const targetPart =
    run.target_artifacts.length > 0 ? run.target_artifacts.join(', ') : 'ingest only'
  return `${sourcePart} → ${targetPart}`
}

export function productionRunProgress(run: ProductionRun): number {
  const steps = run.pipeline
  if (!steps.length) return 0
  const completed = steps.filter((step) => step.status === 'completed').length
  return Math.round((completed / steps.length) * 100)
}

export function productionRunDurationSec(run: ProductionRun): number {
  const start = new Date(run.created_at).getTime()
  const end = run.completed_at
    ? new Date(run.completed_at).getTime()
    : new Date(run.updated_at).getTime()
  return Math.max(0, Math.round((end - start) / 1000))
}

export function skillRunDurationSec(skill: SkillRun): number {
  if (!skill.started_at) return 0
  const start = new Date(skill.started_at).getTime()
  const end = skill.completed_at ? new Date(skill.completed_at).getTime() : Date.now()
  return Math.max(0, Math.round((end - start) / 1000))
}

export function skillRunSummary(skill: SkillRun): string {
  if (skill.error) return skill.error
  if (skill.output && typeof skill.output.summary === 'string') {
    return skill.output.summary
  }
  if (skill.status === 'completed') return 'Completed successfully.'
  if (skill.status === 'running') return 'In progress…'
  if (skill.status === 'queued') return 'Queued.'
  return skill.status
}

export function skillRunTokens(skill: SkillRun): { in: number; out: number } {
  const usage = skill.token_usage
  if (!usage) return { in: 0, out: 0 }
  return {
    in: usage.input_tokens ?? usage.prompt_tokens ?? 0,
    out: usage.output_tokens ?? usage.completion_tokens ?? 0,
  }
}

export function skillRunDisplayName(skill: SkillRun): string {
  return skill.skill_id
    .split('-')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export function pipelineStepLabel(step: PipelineStep): string {
  return step.step
    .split('-')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export function artifactModule(artifact: Artifact): string {
  const manifest = artifact.manifest
  if (typeof manifest.module === 'string') return manifest.module
  if (
    artifact.artifact_type === 'eleven_reader_script' ||
    artifact.artifact_type === 'speechify_script' ||
    artifact.artifact_type === 'speechify_audio' ||
    artifact.artifact_type === 'elevenlabs_audio'
  ) {
    return 'mathesys'
  }
  return 'intellex'
}

export function artifactSummary(artifact: Artifact): string {
  const manifest = artifact.manifest
  if (typeof manifest.summary === 'string') return manifest.summary
  return `${artifact.format} · ${formatBytes(artifact.file_size_bytes)}`
}

export interface SourceDisplay {
  id: string
  filename: string
  title: string
  documentType: string | null
  issuingAuthority: string | null
  mimeLabel: string
  sizeLabel: string
  pages: number | null
  segments: number | null
  confidence: number | null
  status: string
  uploadedAt: string
}

export function mapSourceDisplay(source: Source): SourceDisplay {
  return {
    id: source.id,
    filename: source.filename,
    title: sourceTitle(source),
    documentType: sourceDocumentType(source),
    issuingAuthority: sourceIssuingAuthority(source),
    mimeLabel: mimeLabel(source.mime_type),
    sizeLabel: formatBytes(source.file_size_bytes),
    pages: sourcePages(source),
    segments: sourceSegments(source),
    confidence: sourceConfidence(source),
    status: source.status,
    uploadedAt: source.created_at,
  }
}

export interface SkillRunWithContext extends SkillRun {
  runId: string
  runLabel: string
}

export function flattenSkillRuns(
  runs: ProductionRun[],
  skillRunsByRunId: Record<string, SkillRun[]>,
  sources: Source[],
): SkillRunWithContext[] {
  return runs
    .flatMap((run) =>
      (skillRunsByRunId[run.id] ?? []).map((skill) => ({
        ...skill,
        runId: run.id,
        runLabel: productionRunLabel(run, sources),
      })),
    )
    .sort((a, b) => {
      const aTime = a.started_at ? new Date(a.started_at).getTime() : 0
      const bTime = b.started_at ? new Date(b.started_at).getTime() : 0
      return bTime - aTime
    })
}
