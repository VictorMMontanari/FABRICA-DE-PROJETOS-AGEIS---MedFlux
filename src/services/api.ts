import { clearStoredSession, getStoredSession } from './session'

export type UserProfile = {
  id?: string
  name: string
  email?: string
  city: string
  avatarInitials?: string
  avatar_url?: string | null
}

export type UserUpdateRequest = {
  name?: string
  email?: string
  city?: string
}

export type LoginResponse = {
  token: string
  user: UserProfile
}

export type RegisterRequest = {
  name: string
  email: string
  password: string
  city: string
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
  unit_type: 'UPA' | 'UBS'
  urgency_label: string
  title: string
  description: string
  warning: string
}

export type TriageMessageResponse = {
  reply: string
  timestamp: string
  triage_recommendation: TriageRecommendation | null
}

export type TriageMessageRequest = {
  session_id: string
  message: string
}

export type HealthUnit = {
  id: string
  name: string
  type: 'UPA' | 'UBS'
  address: string
  position: [number, number]
}

type RequestOptions = {
  method?: string
  body?: unknown
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api/v1'

const MOCK_USER: UserProfile = {
  name: 'Marina Santos',
  city: 'Marília, SP',
  avatarInitials: 'MS',
}

const MOCK_HISTORY: TriageHistoryItem[] = [
  {
    id: 'history-1',
    title: 'Dor abdominal',
    description: 'Triagem concluída • Ontem, 14:30',
    timestamp: 'Ontem, 14:30',
    status: 'Triagem concluída',
    route: '/chat',
  },
  {
    id: 'history-2',
    title: 'Febre e tosse',
    description: 'Orientação para UBS • 02 out, 09:10',
    timestamp: '02 out, 09:10',
    status: 'Encaminhado para UBS',
    route: '/chat',
  },
  {
    id: 'history-3',
    title: 'Dor de cabeça',
    description: 'Monitoramento preventivo • 30 set, 18:05',
    timestamp: '30 set, 18:05',
    status: 'Acompanhamento',
    route: '/chat',
  },
]

const MOCK_HEALTH_UNITS: HealthUnit[] = [
  {
    id: 'upa-central',
    name: 'UPA Zona Norte',
    type: 'UPA',
    address: 'Av. das Hortênsias, 245 - Marília/SP',
    position: [-22.2183, -49.9505],
  },
  {
    id: 'upa-sul',
    name: 'UPA Sul',
    type: 'UPA',
    address: 'R. João Ramalho, 889 - Marília/SP',
    position: [-22.2244, -49.9549],
  },
  {
    id: 'ubs-1',
    name: 'UBS Santa Antonieta',
    type: 'UBS',
    address: 'Av. Mem de Sá, 112 - Marília/SP',
    position: [-22.2143, -49.9441],
  },
  {
    id: 'ubs-2',
    name: 'UBS Cascata',
    type: 'UBS',
    address: 'R. Benedito Mendes Faria, 1020 - Marília/SP',
    position: [-22.2281, -49.9632],
  },
]

function getCurrentTime() {
  return new Intl.DateTimeFormat('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date())
}

function buildUrl(path: string) {
  return `${API_BASE_URL}${path}`
}

/** Erro devolvido pela API (`status` 0 = servidor inacessível). `message` já vem pronta para a tela. */
export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

const OFFLINE_MESSAGE = 'Não foi possível conectar ao servidor. Tente novamente.'

async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getStoredSession()?.token
  const headers = new Headers(init.headers)
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  if (typeof init.body === 'string') {
    headers.set('Content-Type', 'application/json')
  }

  let response: Response
  try {
    response = await fetch(buildUrl(path), { ...init, headers })
  } catch {
    throw new ApiError(0, OFFLINE_MESSAGE)
  }

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    // Token expirado ou inválido: encerra a sessão e volta para o login.
    if (response.status === 401 && token) {
      clearStoredSession()
      window.location.assign('/login')
    }
    throw new ApiError(response.status, data?.message ?? 'Não foi possível concluir a ação agora.')
  }

  return data as T
}

async function requestJson<T>(path: string, options: RequestOptions, fallback: () => T): Promise<T> {
  try {
    return await apiFetch<T>(path, {
      method: options.method ?? 'GET',
      body: options.body ? JSON.stringify(options.body) : undefined,
    })
  } catch {
    return fallback()
  }
}

function buildFallbackRecommendation(message: string): TriageRecommendation | null {
  const normalizedMessage = message.toLowerCase()
  const isUrgent =
    normalizedMessage.includes('desmaio') ||
    normalizedMessage.includes('vômit') ||
    normalizedMessage.includes('vomit') ||
    normalizedMessage.includes('febre') ||
    normalizedMessage.includes('dor forte') ||
    normalizedMessage.includes('insuportável') ||
    normalizedMessage.includes('falta de ar') ||
    normalizedMessage.includes('sangue')

  if (isUrgent) {
    return {
      required: true,
      unit_type: 'UPA',
      urgency_label: 'UPA - Atendimento Hoje',
      title: 'Procure uma UPA ainda hoje',
      description:
        'Os sintomas indicam necessidade de avaliação presencial para descartar condições que exigem cuidado imediato.',
      warning:
        'Se a dor ficar insuportável, houver desmaio ou vômito contínuo, ligue 192.',
    }
  }

  return {
    required: true,
    unit_type: 'UBS',
    urgency_label: 'UBS - Atendimento Básico',
    title: 'Procure uma UBS nas próximas horas',
    description:
      'O quadro descrito parece estável, mas merece acompanhamento clínico para orientar o cuidado inicial com segurança.',
    warning:
      'Se houver piora súbita, febre alta persistente ou dor intensa, procure atendimento de urgência.',
  }
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  try {
    return await apiFetch<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  } catch (error) {
    // Modo demonstração apenas com o backend desligado. Senha errada (401) e demais erros vão para a tela.
    if (error instanceof ApiError && error.status === 0) {
      return { token: 'mock-medflux-token', user: MOCK_USER }
    }
    throw error
  }
}

// Sem fallback mock: um cadastro falso enganaria o usuário. Erros do servidor viram mensagem na tela.
export async function register(payload: RegisterRequest): Promise<LoginResponse> {
  return apiFetch<LoginResponse>('/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function getMyProfile(): Promise<UserProfile> {
  return apiFetch<UserProfile>('/users/me')
}

export async function updateMyProfile(payload: UserUpdateRequest): Promise<UserProfile> {
  return apiFetch<UserProfile>('/users/me', {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export async function uploadAvatar(file: File): Promise<void> {
  const form = new FormData()
  form.append('file', file)
  await apiFetch('/users/me/avatar', { method: 'POST', body: form })
}

export async function getTriageHistory(): Promise<TriageHistoryItem[]> {
  return requestJson<TriageHistoryItem[]>('/triage/history', { method: 'GET' }, () => MOCK_HISTORY)
}

export async function sendTriageMessage(
  payload: TriageMessageRequest,
): Promise<TriageMessageResponse> {
  return requestJson<TriageMessageResponse>(
    '/triage/message',
    {
      method: 'POST',
      body: payload,
    },
    () => {
      const recommendation = buildFallbackRecommendation(payload.message)

      return {
        reply: recommendation
          ? 'Entendi o que você descreveu. Vou organizar a orientação mais adequada com base nos sinais informados.'
          : 'Entendi sua mensagem. Vou continuar acompanhando os sinais e te orientar da melhor forma.',
        timestamp: getCurrentTime(),
        triage_recommendation: recommendation,
      }
    },
  )
}

export async function getHealthUnits(): Promise<HealthUnit[]> {
  return requestJson<HealthUnit[]>('/health/units', { method: 'GET' }, () => MOCK_HEALTH_UNITS)
}