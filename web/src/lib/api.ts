const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/+$/, '')

const UNREACHABLE_MESSAGE =
  'Could not reach the MarketMesh API. Make sure it is running (npm run dev:api) on port 8000.'

type ValidationIssue = { loc?: (string | number)[]; msg?: string }

export class ApiError extends Error {
  readonly status: number
  readonly detail: unknown

  constructor(message: string, status: number, detail: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function describeValidationIssue(issue: ValidationIssue) {
  const field = (issue.loc ?? []).filter((part) => part !== 'body').join('.')
  const message = issue.msg ?? 'Invalid value'
  return field ? `${field}: ${message}` : message
}

export function messageFromErrorBody(body: unknown, status: number, fallback: string) {
  const detail = isRecord(body) ? body.detail : undefined

  if (typeof detail === 'string' && detail) return detail
  if (isRecord(detail) && typeof detail.message === 'string') return detail.message
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((issue) => describeValidationIssue(issue as ValidationIssue)).join('; ')
  }
  if (body === null && status >= 500) return UNREACHABLE_MESSAGE
  return `${fallback} (HTTP ${status})`
}

export function apiUrl(path: string) {
  return `${API_BASE_URL}${path}`
}

type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export async function apiFetch(
  path: string,
  { method = 'GET', body, signal, accept = 'application/json' }: {
    method?: Method
    body?: unknown
    signal?: AbortSignal
    accept?: string
  } = {},
): Promise<Response> {
  try {
    return await fetch(apiUrl(path), {
      method,
      headers: {
        Accept: accept,
        ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    })
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err
    throw new ApiError(UNREACHABLE_MESSAGE, 0, null)
  }
}

export async function errorFromResponse(response: Response, fallbackError: string) {
  const body: unknown = await response.json().catch(() => null)
  return new ApiError(
    messageFromErrorBody(body, response.status, fallbackError),
    response.status,
    isRecord(body) ? body.detail : null,
  )
}

export async function apiRequest<T>(
  method: Method,
  path: string,
  fallbackError: string,
  body?: unknown,
): Promise<T> {
  const response = await apiFetch(path, { method, body })
  if (!response.ok) throw await errorFromResponse(response, fallbackError)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const getJson = <T>(path: string, fallbackError: string) => apiRequest<T>('GET', path, fallbackError)

export const postJson = <T>(path: string, payload: unknown, fallbackError: string) =>
  apiRequest<T>('POST', path, fallbackError, payload)

export const patchJson = <T>(path: string, payload: unknown, fallbackError: string) =>
  apiRequest<T>('PATCH', path, fallbackError, payload)

export const putJson = <T>(path: string, payload: unknown, fallbackError: string) =>
  apiRequest<T>('PUT', path, fallbackError, payload)

export const deleteJson = <T>(path: string, fallbackError: string, payload?: unknown) =>
  apiRequest<T>('DELETE', path, fallbackError, payload)

export function errorMessage(err: unknown, fallback: string) {
  return err instanceof Error && err.message ? err.message : fallback
}

/** Fired on window when conversation history changes outside the chat view (e.g. deleted from Settings). */
export const CONVERSATIONS_CHANGED_EVENT = 'marketmesh:conversations-changed'

/** Start a browser download of an API export (the response sets Content-Disposition). */
export function downloadExport(path: string) {
  const link = document.createElement('a')
  link.href = apiUrl(path)
  link.rel = 'noopener'
  document.body.append(link)
  link.click()
  link.remove()
}
