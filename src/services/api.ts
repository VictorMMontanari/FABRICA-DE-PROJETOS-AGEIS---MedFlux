import { clearStoredSession, getStoredSession } from './session'

// ---------------------------------------------------------------------------
// Tipos — espelham 1:1 os modelos Pydantic de medflux-backend/app/schemas.py
// ---------------------------------------------------------------------------

export type UnitLevel = 'UBS' | 'UPA' | 'EMERGENCIA'
export type UnitType = 'UBS' | 'UPA'

export type UserProfile = {
  id?: string
  email?: string
  name: string
  city: string
  avatarInitials?: string
  avatarUrl?: string | null
}

export type LoginResponse = {
  token: string
  user: UserProfile
}

export type TriageHistoryItem = {
  id: string
  title: string
  description: string
  timestamp: string
  status: string
  route: string
}

export type TriageRecommendation = {
  required: boolean
  unit_type: UnitLevel
  urgency_label: string
  title: string
  description: string
  warning: string
}

export type TriageMessageRequest = {
  /** `null` inicia uma conversa nova; depois reenvie o valor devolvido pela API. */
  session_id: string | null
  message: string
}

export type TriageMessageResponse = {
  session_id: string
  reply: string
  timestamp: string
  triage_recommendation: TriageRecommendation | null
}

export type ConversationMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  triage_recommendation: TriageRecommendation | null
}

export type Conversation = {
  id: string
  title: string
  status: string
  messages: ConversationMessage[]
}

export type HealthUnit = {
  id: string
  name: string
  type: UnitType
  address: string
  phone: string | null
  position: [number, number]
  distance_km: number
}

export type HealthUnitsQuery = {
  lat: number
  lng: number
  type?: UnitLevel | null
  limit?: number
}

// ---------------------------------------------------------------------------
// Cliente HTTP
// ---------------------------------------------------------------------------

export const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:5000/api').replace(/\/+$/, '')

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

type RequestOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  body?: unknown
  query?: Record<string, string | number | null | undefined>
  /** Envia o Bearer token da sessão (padrão: true). */
  auth?: boolean
}

const NETWORK_ERROR = 'Não foi possível conectar ao servidor do MedFlux. Verifique se o backend está rodando.'

function buildUrl(path: string, query?: RequestOptions['query']) {
  const url = new URL(`${API_BASE_URL}${path}`, window.location.origin)
  Object.entries(query ?? {}).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      url.searchParams.set(key, String(value))
    }
  })
  return url.toString()
}

/** FastAPI devolve `detail` como string (HTTPException) ou lista (erros 422 de validação). */
function extractDetail(payload: unknown, status: number): string {
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = (payload as { detail: unknown }).detail
    if (typeof detail === 'string') {
      return detail
    }
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string; loc?: unknown[] }
      const field = Array.isArray(first.loc) ? first.loc.slice(1).join('.') : ''
      return `Dados inválidos${field ? ` em "${field}"` : ''}: ${first.msg ?? 'verifique os campos.'}`
    }
  }
  return `Erro inesperado (${status}). Tente novamente.`
}

function handleUnauthorized() {
  clearStoredSession()
  if (window.location.pathname !== '/login') {
    window.location.assign('/login')
  }
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, query, auth = true } = options
  const headers: Record<string, string> = { Accept: 'application/json' }

  if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }

  if (auth) {
    const token = getStoredSession()?.token
    if (token) {
      headers.Authorization = `Bearer ${token}`
    }
  }

  let response: Response
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError(0, NETWORK_ERROR)
  }

  if (response.status === 204) {
    return undefined as T
  }

  const payload: unknown = await response.json().catch(() => null)

  if (!response.ok) {
    if (response.status === 401 && auth) {
      handleUnauthorized()
    }
    throw new ApiError(response.status, extractDetail(payload, response.status))
  }

  return payload as T
}

export function getErrorMessage(error: unknown, fallback = 'Algo deu errado. Tente novamente.') {
  return error instanceof Error && error.message ? error.message : fallback
}

// ---------------------------------------------------------------------------
// Endpoints
// ---------------------------------------------------------------------------

/** POST /api/auth/login */
export function login(email: string, password: string) {
  return request<LoginResponse>('/auth/login', { method: 'POST', body: { email, password }, auth: false })
}

export type RegisterRequest = {
  name: string
  city: string
  email: string
  password: string
}

/** POST /api/auth/register — cria a conta e já devolve o token (mesmo formato do login) */
export function register(payload: RegisterRequest) {
  return request<LoginResponse>('/auth/register', { method: 'POST', body: payload, auth: false })
}

/** POST /api/auth/forgot-password */
export function forgotPassword(email: string) {
  return request<{ message: string }>('/auth/forgot-password', {
    method: 'POST',
    body: { email, redirect_to: `${window.location.origin}/redefinir-senha` },
    auth: false,
  })
}

/** POST /api/auth/reset-password */
export function resetPassword(token: string, password: string) {
  return request<{ message: string }>('/auth/reset-password', {
    method: 'POST',
    body: { token, password },
    auth: false,
  })
}

/** GET /api/auth/me */
export function getCurrentUser() {
  return request<UserProfile>('/auth/me')
}

export type UpdateProfileRequest = {
  name?: string
  city?: string
  avatar_url?: string | null
}

/** PUT /api/auth/profile */
export function updateProfile(payload: UpdateProfileRequest) {
  return request<UserProfile>('/auth/profile', { method: 'PUT', body: payload })
}

/** GET /api/triage/history */
export function getTriageHistory() {
  return request<TriageHistoryItem[]>('/triage/history')
}

/** POST /api/triage/message */
export function sendTriageMessage(payload: TriageMessageRequest) {
  return request<TriageMessageResponse>('/triage/message', { method: 'POST', body: payload })
}

/** GET /api/triage/conversations/{id} */
export function getConversation(conversationId: string) {
  return request<Conversation>(`/triage/conversations/${encodeURIComponent(conversationId)}`)
}

/** DELETE /api/triage/conversations/{id} */
export function deleteConversation(conversationId: string) {
  return request<void>(`/triage/conversations/${encodeURIComponent(conversationId)}`, { method: 'DELETE' })
}

/** GET /api/health/units?lat&lng&type (rota pública) */
export function getHealthUnits({ lat, lng, type, limit }: HealthUnitsQuery) {
  return request<HealthUnit[]>('/health/units', { query: { lat, lng, type, limit }, auth: false })
}

/** GET /api/status */
export function getApiStatus() {
  return request<{ ok: boolean; version: string }>('/status', { auth: false })
}