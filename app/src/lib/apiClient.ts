import { getAccessToken } from '../features/auth/authService'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL as string | undefined

interface ApiRequestOptions extends RequestInit {
  requiresAuth?: boolean
}

export interface CurrentUserResponse {
  id: string
  email: string
  role: string
}

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function hasApiBaseUrl(): boolean {
  return Boolean(apiBaseUrl)
}

export async function apiRequest<TResponse>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<TResponse> {
  if (!apiBaseUrl) {
    throw new ApiError('Missing VITE_API_BASE_URL.', 0)
  }

  const { requiresAuth = true, headers, body, ...fetchOptions } = options
  const requestHeaders = new Headers(headers)

  if (body && !requestHeaders.has('Content-Type')) {
    requestHeaders.set('Content-Type', 'application/json')
  }

  if (requiresAuth) {
    const token = await getAccessToken()

    if (!token) {
      throw new ApiError('Missing access token.', 401)
    }

    requestHeaders.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...fetchOptions,
    body,
    headers: requestHeaders,
  })

  if (!response.ok) {
    const message = await response.text()
    throw new ApiError(message || `API request failed with status ${response.status}.`, response.status)
  }

  return response.json() as Promise<TResponse>
}

export async function getCurrentUser(): Promise<CurrentUserResponse> {
  return apiRequest<CurrentUserResponse>('/me')
}
