import { apiRequest } from './apiClient'

export type AssistantMode = 'discussion' | 'scenario'
export type DiscussionSubmode = 'socratic' | 'euclidean'

export interface AssistantMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface Citation {
  kind: 'segment' | 'wiki'
  label: string
  snippet: string
  similarity: number
  reader_link: string | null
  locator: Record<string, unknown>
}

export interface ScenarioEvaluation {
  passed: boolean
  score: number | null
  feedback: string
  met_criteria: string[]
  missed_criteria: string[]
}

export interface AssistantChatResponse {
  answer: string
  grounded: boolean
  citations: Citation[]
  evaluation: ScenarioEvaluation | null
}

export interface AssistantChatRequest {
  mode: AssistantMode
  submode?: DiscussionSubmode
  messages: AssistantMessage[]
  source_ids?: string[]
  scenario_id?: string
}

export async function assistantChat(
  workspaceId: string,
  request: AssistantChatRequest,
): Promise<AssistantChatResponse> {
  return apiRequest<AssistantChatResponse>(
    `/workspaces/${workspaceId}/assistant/chat`,
    { method: 'POST', body: JSON.stringify(request) },
  )
}
