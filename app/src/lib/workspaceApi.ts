import { getAccessToken } from '../features/auth/authService'
import { apiRequest, hasApiBaseUrl, parseApiErrorMessage } from './apiClient'

export interface Workspace {
  id: string
  owner_id: string
  name: string
  description: string | null
  status: string
  created_at: string
  updated_at: string
}

export interface Source {
  id: string
  workspace_id: string
  filename: string
  mime_type: string
  storage_path: string
  file_hash: string
  file_size_bytes: number
  source_metadata: Record<string, unknown>
  status: string
  created_at: string
  updated_at: string
}

export interface WikiEntry {
  id: string
  workspace_id: string
  preferred_label: string
  definition: string
  entry_kind: string
  status: string
  canonical_slug: string
  aliases: string[]
  pronunciation: string | null
  created_at: string
}

export interface Artifact {
  id: string
  workspace_id: string
  source_id: string | null
  production_run_id: string | null
  artifact_type: string
  format: string
  filename: string
  storage_path: string
  file_size_bytes: number
  manifest: Record<string, unknown>
  created_at: string
}

export interface Flashcard {
  id: string
  assessment_set_id?: string | null
  item_id?: string | null
  subtype?: string | null
  front: string
  back: string
  difficulty: string
  tags: string[]
  created_at: string
}

export interface Quiz {
  id: string
  assessment_set_id?: string | null
  item_id?: string | null
  subtype?: string | null
  question: string
  question_type: string
  options: string[]
  correct_answer: string
  explanation: string | null
  difficulty: string
  created_at: string
}

export interface Scenario {
  id: string
  assessment_set_id?: string | null
  item_id?: string | null
  subtype?: string | null
  title: string
  prompt: string
  context: string | null
  evaluation_criteria: string[]
  difficulty: string
  created_at: string
}

export interface AssessmentSetSummary {
  id: string
  workspace_id: string
  source_id: string | null
  production_run_id: string | null
  title: string
  learning_goal: string | null
  assessment_types: string[]
  item_count: number
  created_at: string
}

export interface PipelineStep {
  step: string
  type: string
  status: string
  module?: string
  skill_id?: string
  skill_run_id?: string
  detail?: string
}

export interface ProductionRun {
  id: string
  workspace_id: string
  source_ids: string[]
  target_artifacts: string[]
  pipeline: PipelineStep[]
  status: string
  error: string | null
  created_at: string
  updated_at: string
  completed_at: string | null
  cost_usd: number
}

export interface SkillRun {
  id: string
  production_run_id: string
  workspace_id: string
  skill_id: string
  skill_version: string
  module: string
  status: string
  inputs: Record<string, unknown>
  output: Record<string, unknown> | null
  promoted: Record<string, unknown> | null
  model: string | null
  token_usage: Record<string, number> | null
  api_usage: Record<string, unknown> | null
  cost_usd: number
  error: string | null
  started_at: string | null
  completed_at: string | null
}

// A production run produces at most one narration artifact, chosen here.
export const NARRATION_ARTIFACT_OPTIONS = [
  { value: 'eleven_reader_script', label: 'ElevenReader EBook' },
  { value: 'speechify_audio', label: 'Speechify Audio' },
  { value: 'elevenlabs_audio', label: 'ElevenLabs Audio' },
] as const

// Review material is generated as a single bundle of all three assessment types.
export const REVIEW_ARTIFACT_VALUES = ['flashcards', 'quizzes', 'scenarios'] as const

export const REVIEW_PURPOSES = [
  { label: 'Flashcards', purpose: 'Memorization' },
  { label: 'Quizzes', purpose: 'Understanding' },
  { label: 'Scenarios', purpose: 'Application' },
] as const

export async function listWorkspaces(): Promise<Workspace[]> {
  return apiRequest<Workspace[]>('/workspaces')
}

export async function createWorkspace(name: string, description?: string): Promise<Workspace> {
  return apiRequest<Workspace>('/workspaces', {
    method: 'POST',
    body: JSON.stringify({ name, description }),
  })
}

export async function listSources(workspaceId: string): Promise<Source[]> {
  return apiRequest<Source[]>(`/workspaces/${workspaceId}/sources`)
}

export async function uploadSource(workspaceId: string, file: File): Promise<Source> {
  if (!hasApiBaseUrl()) {
    throw new Error('Missing VITE_API_BASE_URL.')
  }

  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL as string
  const token = await getAccessToken()

  if (!token) {
    throw new Error('Missing access token.')
  }

  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${apiBaseUrl}/workspaces/${workspaceId}/sources`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  })

  if (!response.ok) {
    const message = await parseApiErrorMessage(response)
    throw new Error(message)
  }

  return response.json() as Promise<Source>
}

export async function listWikiEntries(
  workspaceId: string,
  search?: string,
): Promise<WikiEntry[]> {
  const params = new URLSearchParams()
  if (search) {
    params.set('search', search)
  }
  const query = params.toString()
  return apiRequest<WikiEntry[]>(
    `/workspaces/${workspaceId}/wiki/entries${query ? `?${query}` : ''}`,
  )
}

export async function listArtifacts(workspaceId: string): Promise<Artifact[]> {
  return apiRequest<Artifact[]>(`/workspaces/${workspaceId}/artifacts`)
}

export async function getArtifactDownloadUrl(
  artifactId: string,
): Promise<{ download_url: string }> {
  return apiRequest<{ download_url: string; expires_in: number }>(
    `/artifacts/${artifactId}/download`,
  )
}

export async function listFlashcards(workspaceId: string): Promise<Flashcard[]> {
  return apiRequest<Flashcard[]>(`/workspaces/${workspaceId}/flashcards`)
}

export async function listQuizzes(workspaceId: string): Promise<Quiz[]> {
  return apiRequest<Quiz[]>(`/workspaces/${workspaceId}/quizzes`)
}

export async function listScenarios(workspaceId: string): Promise<Scenario[]> {
  return apiRequest<Scenario[]>(`/workspaces/${workspaceId}/scenarios`)
}

export async function listAssessmentSets(workspaceId: string): Promise<AssessmentSetSummary[]> {
  return apiRequest<AssessmentSetSummary[]>(`/workspaces/${workspaceId}/assessment-sets`)
}

export async function listProductionRuns(workspaceId: string): Promise<ProductionRun[]> {
  return apiRequest<ProductionRun[]>(`/workspaces/${workspaceId}/production-runs`)
}

export async function createProductionRun(
  workspaceId: string,
  payload: { source_ids: string[]; target_artifacts: string[] },
): Promise<ProductionRun> {
  return apiRequest<ProductionRun>(`/workspaces/${workspaceId}/production-runs`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function listSkillRuns(runId: string): Promise<SkillRun[]> {
  return apiRequest<SkillRun[]>(`/production-runs/${runId}/skill-runs`)
}
