export type UserProfile = {
  name: string
  city: string
  avatarInitials?: string
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

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

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

async function requestJson<T>(path: string, options: RequestOptions, fallback: () => T): Promise<T> {
  try {
    const response = await fetch(buildUrl(path), {
      method: options.method ?? 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      body: options.body ? JSON.stringify(options.body) : undefined,
    })

    if (!response.ok) {
      throw new Error(`Request failed with ${response.status}`)
    }

    return (await response.json()) as T
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
  return requestJson<LoginResponse>(
    '/auth/login',
    {
      method: 'POST',
      body: { email, password },
    },
    () => ({
      token: 'mock-medflux-token',
      user: MOCK_USER,
    }),
  )
}

// Sem fallback mock: um cadastro falso enganaria o usuário. Erros do servidor viram mensagem na tela.
export async function register(payload: RegisterRequest): Promise<LoginResponse> {
  let response: Response

  try {
    response = await fetch(buildUrl('/auth/register'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })
  } catch {
    throw new Error('Não foi possível conectar ao servidor. Tente novamente.')
  }

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    throw new Error(data?.message ?? 'Não foi possível criar sua conta agora.')
  }

  return data as LoginResponse
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

export function getMockUserProfile() {
  return MOCK_USER
}