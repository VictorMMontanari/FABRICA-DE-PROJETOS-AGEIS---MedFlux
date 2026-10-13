import { Camera, Mail, MapPin, User } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { UserAvatar } from '../components/UserAvatar'
import { getMyProfile, updateMyProfile, uploadAvatar, type UserProfile } from '../services/api'
import { getStoredSession, updateStoredUser } from '../services/session'

const AVATAR_MAX_BYTES = 5 * 1024 * 1024
const AVATAR_TYPES = ['image/jpeg', 'image/png', 'image/webp']

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : 'Não foi possível concluir a ação agora.'
}

export function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | undefined>(() => getStoredSession()?.user)
  const [name, setName] = useState(profile?.name ?? '')
  const [email, setEmail] = useState(profile?.email ?? '')
  const [city, setCity] = useState(profile?.city ?? '')
  const [isLoaded, setIsLoaded] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  function applyProfile(next: UserProfile) {
    setProfile(next)
    setName(next.name)
    setEmail(next.email ?? '')
    setCity(next.city)
    updateStoredUser(next)
  }

  useEffect(() => {
    // Busca o perfil atualizado: traz o email e uma URL nova da foto (a anterior expira).
    getMyProfile()
      .then((next) => {
        setProfile(next)
        setName(next.name)
        setEmail(next.email ?? '')
        setCity(next.city)
        updateStoredUser(next)
      })
      .catch((err: unknown) => setError(errorMessage(err)))
      .finally(() => setIsLoaded(true))
  }, [])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSuccess(null)
    setIsSaving(true)

    try {
      applyProfile(await updateMyProfile({ name: name.trim(), email: email.trim(), city: city.trim() }))
      setSuccess('Perfil atualizado.')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setIsSaving(false)
    }
  }

  async function handleAvatarChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) {
      return
    }

    setError(null)
    setSuccess(null)

    if (!AVATAR_TYPES.includes(file.type)) {
      setError('Formato inválido. Envie uma imagem JPEG, PNG ou WEBP.')
      return
    }
    if (file.size > AVATAR_MAX_BYTES) {
      setError('A foto deve ter no máximo 5 MB.')
      return
    }

    setIsUploading(true)
    try {
      await uploadAvatar(file)
      applyProfile(await getMyProfile())
      setSuccess('Foto atualizada.')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="profile-page">
      <section className="section-title-row">
        <div>
          <h1 className="section-title">Meu Perfil</h1>
          <p className="section-subtitle">Atualize seus dados e sua foto.</p>
        </div>
      </section>

      <section className="page-card profile-card">
        <div className="profile-card__photo">
          <UserAvatar user={profile} className="profile-card__avatar" />
          <input
            ref={fileInputRef}
            type="file"
            accept={AVATAR_TYPES.join(',')}
            hidden
            onChange={handleAvatarChange}
          />
          <button
            type="button"
            className="profile-card__photo-button"
            onClick={() => fileInputRef.current?.click()}
            disabled={!isLoaded || isUploading}
          >
            <Camera size={16} />
            {isUploading ? 'Enviando...' : 'Trocar foto'}
          </button>
          <span className="profile-card__hint">JPEG, PNG ou WEBP até 5 MB</span>
        </div>

        <form className="form-stack profile-card__form" onSubmit={handleSubmit}>
          <label className="input-group">
            <span>Nome completo</span>
            <div className="input-shell">
              <User size={18} />
              <input
                type="text"
                value={name}
                onChange={(event) => setName(event.target.value)}
                autoComplete="name"
                disabled={!isLoaded}
                required
                minLength={2}
              />
            </div>
          </label>

          <label className="input-group">
            <span>Email</span>
            <div className="input-shell">
              <Mail size={18} />
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="email"
                disabled={!isLoaded}
                required
              />
            </div>
          </label>

          <label className="input-group">
            <span>Cidade</span>
            <div className="input-shell">
              <MapPin size={18} />
              <input
                type="text"
                value={city}
                onChange={(event) => setCity(event.target.value)}
                placeholder="Cidade, UF"
                autoComplete="address-level2"
                disabled={!isLoaded}
              />
            </div>
          </label>

          {error ? <div className="error-banner">{error}</div> : null}
          {success ? (
            <div className="success-banner" role="status">
              {success}
            </div>
          ) : null}

          <button type="submit" className="primary-button" disabled={!isLoaded || isSaving}>
            {!isLoaded ? 'Carregando...' : isSaving ? 'Salvando...' : 'Salvar alterações'}
          </button>
        </form>
      </section>
    </div>
  )
}
