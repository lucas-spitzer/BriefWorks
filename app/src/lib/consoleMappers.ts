import type {
  Artifact,
  PipelineStep,
  ProductionRun,
  StageRun,
  Source,
} from './workspaceApi'
import {
  artifactKindLabel,
  artifactKindShortLabel,
  documentTypeLabel,
  formatBytes,
  mimeLabel,
} from './consoleFormat'

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

export function sourceAbstract(source: Source): string | null {
  const research = researchMetadata(source)
  const researchedAbstract = metadataString(research?.abstract)
  if (researchedAbstract) return researchedAbstract

  const meta = source.source_metadata
  return metadataString(meta.abstract)
}

export function sourcePurpose(source: Source): string | null {
  const research = researchMetadata(source)
  return metadataString(research?.purpose)
}

export function sourceAudience(source: Source): string | null {
  const research = researchMetadata(source)
  return metadataString(research?.target_audience)
}

export function sourceResearchTitle(source: Source): string {
  const research = researchMetadata(source)
  const researchedTitle = metadataString(research?.title)
  if (researchedTitle) return researchedTitle

  const identifier = metadataString(research?.identifier)
  if (identifier) return identifier

  const meta = source.source_metadata
  const flatTitle = metadataString(meta.title)
  if (flatTitle) return flatTitle

  return filenameStem(source.filename)
}

export function artifactCardTitle(artifact: Artifact, source: Source | undefined): string {
  const name = source ? sourceResearchTitle(source) : filenameStem(artifact.filename)
  return `${name} ${artifactKindShortLabel(artifact.artifact_type)}`
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
    run.target_artifacts.length > 0
      ? run.target_artifacts.map((artifact) => artifactKindLabel(artifact)).join(', ')
      : 'Upload'
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
  const end = run.completed_at ? new Date(run.completed_at).getTime() : Date.now()
  return Math.max(0, Math.round((end - start) / 1000))
}

export function stageRunDurationSec(stageRun: StageRun): number {
  if (!stageRun.started_at) return 0
  const start = new Date(stageRun.started_at).getTime()
  const end = stageRun.completed_at ? new Date(stageRun.completed_at).getTime() : Date.now()
  return Math.max(0, Math.round((end - start) / 1000))
}

export function stageRunSummary(stageRun: StageRun): string {
  if (stageRun.error) return 'Execution failed.'
  if (stageRun.output && typeof stageRun.output.summary === 'string') {
    return stageRun.output.summary
  }
  if (stageRun.status === 'completed') return 'Completed successfully.'
  if (stageRun.status === 'running') return 'In progress…'
  if (stageRun.status === 'queued') return 'Queued.'
  return stageRun.status
}

export function stageRunTokens(stageRun: StageRun): { in: number; out: number } {
  const usage = stageRun.token_usage
  if (!usage) return { in: 0, out: 0 }
  return {
    in: usage.input_tokens ?? usage.prompt_tokens ?? 0,
    out: usage.output_tokens ?? usage.completion_tokens ?? 0,
  }
}

export function stageRunApiUsageTotals(
  stageRun: StageRun,
): { costUsd: number; elevenlabsTokens: number } {
  const usage = stageRun.api_usage

  if (!usage || typeof usage !== 'object' || Array.isArray(usage)) {
    return { costUsd: 0, elevenlabsTokens: 0 }
  }

  const totals = (usage as { totals?: Record<string, unknown> }).totals

  if (!totals || typeof totals !== 'object') {
    return { costUsd: 0, elevenlabsTokens: 0 }
  }

  const costUsd = typeof totals.cost_usd === 'number' ? totals.cost_usd : 0
  const elevenlabsTokens =
    typeof totals.elevenlabs_tokens === 'number'
      ? totals.elevenlabs_tokens
      : typeof totals.character_count === 'number'
        ? totals.character_count
        : 0

  return { costUsd, elevenlabsTokens }
}

export function stageRunCostUsd(stageRun: StageRun): number {
  const stored = typeof stageRun.cost_usd === 'number' ? stageRun.cost_usd : 0

  if (stored > 0) {
    return stored
  }

  return stageRunApiUsageTotals(stageRun).costUsd
}

export function stageRunElevenLabsTokens(stageRun: StageRun): number {
  return stageRunApiUsageTotals(stageRun).elevenlabsTokens
}

export function productionRunCostUsd(
  run: ProductionRun,
  stageRuns: StageRun[] = [],
): number {
  const rolledUp = typeof run.cost_usd === 'number' ? run.cost_usd : 0
  const fromStages = stageRuns.reduce((total, stageRun) => total + stageRunCostUsd(stageRun), 0)
  return Math.max(rolledUp, fromStages)
}

export function sumWorkspaceCostUsd(
  productionRuns: ProductionRun[],
  stageRunsByRunId: Record<string, StageRun[]>,
): number {
  return productionRuns.reduce(
    (total, run) => total + productionRunCostUsd(run, stageRunsByRunId[run.id] ?? []),
    0,
  )
}

export function stageRunDisplayName(stageRun: StageRun): string {
  return apiRequestStageLabel(stageRun.stage_id) ?? stageRun.stage_id
    .split('-')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

const API_REQUEST_STAGES: Record<string, { label: string; tool: string }> = {
  parse: { label: 'Parse', tool: 'LlamaParse' },
  'normalize-document': { label: 'Normalize', tool: 'Local' },
  'trim-document-boundaries': { label: 'Trim', tool: 'Local' },
  'structure-document': { label: 'Structure', tool: 'Local' },
  'validate-structure': { label: 'Validate', tool: 'Local' },
  'source-research': { label: 'Source Research', tool: 'OpenAI' },
  'extract-knowledge': { label: 'Extract Knowledge', tool: 'Claude' },
  'create-ebook': { label: 'Create EBook', tool: 'Local' },
  'generate-flashcards': { label: 'Generate Flashcards', tool: 'Claude' },
  'generate-questions': { label: 'Generate Questions', tool: 'Claude' },
  'generate-scenarios': { label: 'Generate Scenarios', tool: 'Claude' },
}

const API_PROVIDER_LABELS: Record<string, string> = {
  tavily: 'Tavily',
  llamaparse: 'LlamaParse',
  openai: 'OpenAI',
  anthropic: 'Claude',
  elevenlabs: 'ElevenLabs',
  speechify: 'Speechify',
}

function apiUsageRecord(stageRun: StageRun): Record<string, unknown> | null {
  const usage = stageRun.api_usage
  if (!usage || typeof usage !== 'object' || Array.isArray(usage)) return null
  return usage as Record<string, unknown>
}

export function stageRunApiCalls(stageRun: StageRun): Record<string, unknown>[] {
  const usage = apiUsageRecord(stageRun)
  const calls = usage?.calls
  if (!Array.isArray(calls)) return []
  return calls.filter((call): call is Record<string, unknown> => Boolean(call) && typeof call === 'object')
}

function providerToolLabel(provider: unknown): string | null {
  if (typeof provider !== 'string' || !provider.trim()) return null
  return API_PROVIDER_LABELS[provider.trim().toLowerCase()] ?? provider
}

export function apiRequestStageLabel(stageId: string): string | null {
  return API_REQUEST_STAGES[stageId]?.label ?? null
}

export function stageRunApiToolLabel(stageRun: StageRun): string {
  const configuredTool = API_REQUEST_STAGES[stageRun.stage_id]?.tool
  if (configuredTool) return configuredTool

  const labels = new Set<string>()

  for (const call of stageRunApiCalls(stageRun)) {
    const label = providerToolLabel(call.provider)
    if (label) labels.add(label)
  }

  const model = (stageRun.model ?? '').trim().toLowerCase()
  if (model === 'llamaparse') labels.add('LlamaParse')
  if (model.includes('claude') || model.includes('anthropic')) labels.add('Claude')
  if (model.includes('gpt') || model.includes('openai')) labels.add('OpenAI')

  if (labels.size > 0) {
    return [...labels].join(' · ')
  }

  return stageRun.model ?? '—'
}

export function stageRunCredits(stageRun: StageRun): number {
  const usage = apiUsageRecord(stageRun)
  const totals = usage?.totals
  if (totals && typeof totals === 'object' && !Array.isArray(totals)) {
    const creditCount = (totals as Record<string, unknown>).credit_count
    if (typeof creditCount === 'number' && creditCount > 0) return creditCount
  }

  let credits = 0
  for (const call of stageRunApiCalls(stageRun)) {
    const creditCount = call.credit_count
    if (typeof creditCount === 'number') credits += creditCount
  }

  if (credits > 0) return credits

  if (stageRun.stage_id === 'parse') {
    const pageCount = stageRun.output?.page_count
    if (typeof pageCount === 'number' && pageCount > 0) return pageCount
  }

  return 0
}

export function isApiRequestStageRun(stageRun: StageRun): boolean {
  if (!API_REQUEST_STAGES[stageRun.stage_id]) return false
  if (stageRun.model === 'deterministic-passthrough') return false

  const tokens = stageRunTokens(stageRun)
  if (tokens.in + tokens.out > 0) return true
  if (stageRunApiCalls(stageRun).length > 0) return true
  if (stageRunCredits(stageRun) > 0) return true
  if (stageRunElevenLabsTokens(stageRun) > 0) return true

  const model = (stageRun.model ?? '').trim().toLowerCase()
  if (model && model !== 'unknown') return true

  return false
}

export function flattenApiRequests(
  runs: ProductionRun[],
  stageRunsByRunId: Record<string, StageRun[]>,
  sources: Source[],
): StageRunWithContext[] {
  return flattenStageRuns(runs, stageRunsByRunId, sources).filter(isApiRequestStageRun)
}

export function pipelineStepLabel(step: PipelineStep): string {
  return step.step
    .split('-')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export type PipelineStepDisplayStatus = 'completed' | 'running' | 'failed' | 'queued'

export function pipelineStepDisplayStatus(
  step: PipelineStep,
  pipeline: PipelineStep[],
  stageRuns: StageRun[],
  runStatus: string,
): PipelineStepDisplayStatus {
  if (step.status === 'completed') return 'completed'
  if (step.status === 'failed') return 'failed'

  if (step.stage_id) {
    const activeStageRun = stageRuns.find(
      (stageRun) =>
        stageRun.stage_id === step.stage_id &&
        (stageRun.status === 'running' || stageRun.status === 'queued'),
    )
    if (activeStageRun) {
      return activeStageRun.status === 'running' ? 'running' : 'queued'
    }

    const failedStageRun = stageRuns.find(
      (stageRun) => stageRun.stage_id === step.stage_id && stageRun.status === 'failed',
    )
    if (failedStageRun) return 'failed'
  }

  if (runStatus === 'running' || runStatus === 'queued') {
    const currentStep = pipeline.find(
      (pipelineStep) => pipelineStep.status !== 'completed' && pipelineStep.status !== 'failed',
    )
    if (currentStep?.step === step.step) {
      return runStatus === 'running' ? 'running' : 'queued'
    }
  }

  return 'queued'
}

export function pipelineStepDetail(
  step: PipelineStep,
  pipeline: PipelineStep[],
  stageRuns: StageRun[],
  runStatus: string,
): string {
  if (step.detail) return step.detail

  if (step.stage_id) {
    const activeStageRun = stageRuns.find(
      (stageRun) =>
        stageRun.stage_id === step.stage_id &&
        (stageRun.status === 'running' || stageRun.status === 'queued'),
    )
    if (activeStageRun) return stageRunSummary(activeStageRun)
  }

  const displayStatus = pipelineStepDisplayStatus(step, pipeline, stageRuns, runStatus)
  if (displayStatus === 'running') return 'In progress…'
  if (displayStatus === 'queued') return 'Queued.'
  return displayStatus.charAt(0).toUpperCase() + displayStatus.slice(1)
}

export function artifactModule(artifact: Artifact): string {
  const manifest = artifact.manifest
  if (typeof manifest.module === 'string') return manifest.module
  if (
    artifact.artifact_type === 'eleven_reader_script' ||
    artifact.artifact_type === 'speechify_script' ||
    artifact.artifact_type === 'speechify_audio' ||
    artifact.artifact_type === 'elevenlabs_audio' ||
    artifact.artifact_type === 'uploaded'
  ) {
    return 'mathesys'
  }
  return 'intellex'
}

export interface SourceDisplay {
  id: string
  filename: string
  title: string
  documentType: string | null
  issuingAuthority: string | null
  purpose: string | null
  audience: string | null
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
    purpose: sourcePurpose(source),
    audience: sourceAudience(source),
    mimeLabel: mimeLabel(source.mime_type),
    sizeLabel: formatBytes(source.file_size_bytes),
    pages: sourcePages(source),
    segments: sourceSegments(source),
    confidence: sourceConfidence(source),
    status: source.status,
    uploadedAt: source.created_at,
  }
}

export interface StageRunWithContext extends StageRun {
  runId: string
  runLabel: string
}

export function flattenStageRuns(
  runs: ProductionRun[],
  stageRunsByRunId: Record<string, StageRun[]>,
  sources: Source[],
): StageRunWithContext[] {
  return runs
    .flatMap((run) =>
      (stageRunsByRunId[run.id] ?? []).map((stageRun) => ({
        ...stageRun,
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
