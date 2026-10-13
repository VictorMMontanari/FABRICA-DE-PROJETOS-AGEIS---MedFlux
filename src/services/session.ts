import type { UserProfile } from './api'

const STORAGE_KEY = 'medflux.session'

export type StoredSession = {
  token: string
  user: UserProfile
}

function canUseStorage() {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined'
}

export function getStoredSession(): StoredSession | null {
  if (!canUseStorage()) {
    return null
  }

  const rawSession = window.localStorage.getItem(STORAGE_KEY) ?? window.sessionStorage.getItem(STORAGE_KEY)

  if (!rawSession) {
    return null
  }

  try {
    return JSON.parse(rawSession) as StoredSession
  } catch {
    return null
  }
}

export function saveStoredSession(session: StoredSession, persist = true) {
  if (!canUseStorage()) {
    return
  }

  const storage = persist ? window.localStorage : window.sessionStorage
  storage.setItem(STORAGE_KEY, JSON.stringify(session))
}

export function clearStoredSession() {
  if (!canUseStorage()) {
    return
  }

  window.localStorage.removeItem(STORAGE_KEY)
  window.sessionStorage.removeItem(STORAGE_KEY)
}

const SESSION_EVENT = 'medflux:session'

/** Atualiza o usuário salvo na sessão (mantém o token e o local de armazenamento escolhido no login). */
export function updateStoredUser(user: UserProfile) {
  const session = getStoredSession()
  if (!session || !canUseStorage()) {
    return
  }

  const persisted = window.localStorage.getItem(STORAGE_KEY) !== null
  saveStoredSession({ ...session, user: { ...session.user, ...user } }, persisted)
  window.dispatchEvent(new Event(SESSION_EVENT))
}

/** Avisa quando o usuário salvo muda (ex.: perfil editado), para o cabeçalho se atualizar. */
export function onStoredUserChange(callback: () => void) {
  window.addEventListener(SESSION_EVENT, callback)
  return () => window.removeEventListener(SESSION_EVENT, callback)
}
