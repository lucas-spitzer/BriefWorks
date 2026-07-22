import { apiRequest } from './apiClient'

export type ReaderDefineMode = 'contextual' | 'general'

export interface ReaderDefineRequest {
  term: string
  mode: ReaderDefineMode
  source_id?: string | null
  sentence?: string | null
  prev_paragraph?: string | null
  current_paragraph?: string | null
  next_paragraph?: string | null
}

export interface ReaderDefineResponse {
  term: string
  definition: string
  mode: ReaderDefineMode
  provenance: ReaderDefineMode
}

export async function defineReaderTerm(
  workspaceId: string,
  request: ReaderDefineRequest,
): Promise<ReaderDefineResponse> {
  return apiRequest<ReaderDefineResponse>(`/workspaces/${workspaceId}/reader/define`, {
    method: 'POST',
    body: JSON.stringify(request),
  })
}
