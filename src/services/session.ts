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
  window.dispatchEvent(new CustomEvent('medflux:session-updated', { detail: null }))
}

export function updateStoredUser(updatedFields: Partial<UserProfile>): StoredSession | null {
  if (!canUseStorage()) {
    return null
  }

  const current = getStoredSession()
  if (!current) {
    return null
  }

  const isLocal = Boolean(window.localStorage.getItem(STORAGE_KEY))
  const newSession: StoredSession = {
    ...current,
    user: {
      ...current.user,
      ...updatedFields,
    },
  }

  saveStoredSession(newSession, isLocal)
  window.dispatchEvent(new CustomEvent('medflux:session-updated', { detail: newSession }))
  return newSession
}