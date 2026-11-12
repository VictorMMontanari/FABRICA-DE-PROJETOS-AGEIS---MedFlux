import { Camera, CheckCircle2, Mail, MapPin, Save, ShieldCheck, Sparkles, Trash2, Upload, User, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, DragEvent, FormEvent } from 'react'
import { getErrorMessage, updateProfile } from '../services/api'
import { getStoredSession, updateStoredUser } from '../services/session'

/** Redimensiona e otimiza a imagem em canvas para WebP (máx 400x400) */
function processImageFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    if (!file.type.startsWith('image/')) {
      reject(new Error('O arquivo selecionado deve ser uma imagem (PNG, JPG ou WebP).'))
      return
    }

    if (file.size > 8 * 1024 * 1024) {
      reject(new Error('A imagem é muito grande. Escolha uma foto de até 8MB.'))
      return
    }

    const reader = new FileReader()
    reader.onerror = () => reject(new Error('Falha ao ler o arquivo de imagem.'))
    reader.onload = () => {
      const img = new Image()
      img.onerror = () => reject(new Error('Formato de imagem inválido ou corrompido.'))
      img.onload = () => {
        const maxSize = 400
        let { width, height } = img
        if (width > height && width > maxSize) {
          height = Math.round((height * maxSize) / width)
          width = maxSize
        } else if (height > maxSize) {
          width = Math.round((width * maxSize) / height)
          height = maxSize
        }

        const canvas = document.createElement('canvas')
        canvas.width = width
        canvas.height = height
        const ctx = canvas.getContext('2d')
        if (!ctx) {
          reject(new Error('Falha ao processar canvas da imagem.'))
          return
        }

        ctx.drawImage(img, 0, 0, width, height)
        const dataUrl = canvas.toDataURL('image/webp', 0.85)
        resolve(dataUrl)
      }
      img.src = String(reader.result)
    }
    reader.readAsDataURL(file)
  })
}

type ProfileModalProps = {
  isOpen: boolean
  onClose: () => void
}

export function ProfileModal({ isOpen, onClose }: ProfileModalProps) {
  const session = getStoredSession()
  const user = session?.user

  const [name, setName] = useState(user?.name ?? '')
  const [city, setCity] = useState(user?.city ?? 'Marília, SP')
  const [avatarUrl, setAvatarUrl] = useState<string | null>(user?.avatarUrl ?? null)
  const [isDragging, setIsDragging] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [success, setSuccess] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fileInputRef = useRef<HTMLInputElement | null>(null)

  // Quando o modal abre, resincroniza os estados com a sessão atual
  useEffect(() => {
    if (isOpen) {
      const current = getStoredSession()?.user
      setName(current?.name ?? '')
      setCity(current?.city ?? 'Marília, SP')
      setAvatarUrl(current?.avatarUrl ?? null)
      setSuccess(null)
      setError(null)
      setIsLoading(false)
    }
  }, [isOpen])

  // Fecha o modal ao pressionar Escape
  useEffect(() => {
    if (!isOpen) return

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen) {
    return null
  }

  const email = user?.email || 'paciente@medflux.com'
  const initials =
    user?.avatarInitials ||
    name
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map((p) => p[0].toUpperCase())
      .join('') ||
    'MF'

  async function handleFileSelected(file: File) {
    setError(null)
    setSuccess(null)
    try {
      const optimizedDataUri = await processImageFile(file)
      setAvatarUrl(optimizedDataUri)
    } catch (err) {
      setError(getErrorMessage(err, 'Não foi possível carregar a imagem.'))
    }
  }

  function handleFileInputChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (file) {
      void handleFileSelected(file)
    }
    event.target.value = ''
  }

  function handleDragOver(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setIsDragging(true)
  }

  function handleDragLeave(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setIsDragging(false)
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setIsDragging(false)
    const file = event.dataTransfer.files?.[0]
    if (file) {
      void handleFileSelected(file)
    }
  }

  function handleRemovePhoto() {
    setAvatarUrl(null)
    setError(null)
    setSuccess(null)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsLoading(true)
    setError(null)
    setSuccess(null)

    const trimmedName = name.trim()
    const trimmedCity = city.trim()

    if (!trimmedName || trimmedName.length < 2) {
      setError('O nome deve conter pelo menos 2 caracteres.')
      setIsLoading(false)
      return
    }

    try {
      try {
        await updateProfile({
          name: trimmedName,
          city: trimmedCity,
          avatar_url: avatarUrl,
        })
      } catch (apiErr) {
        console.warn('API de perfil indisponível ou em modo local:', apiErr)
      }

      const updatedInitials = trimmedName
        .split(' ')
        .filter(Boolean)
        .slice(0, 2)
        .map((p) => p[0].toUpperCase())
        .join('')

      updateStoredUser({
        name: trimmedName,
        city: trimmedCity,
        avatarUrl,
        avatarInitials: updatedInitials || initials,
      })

      setSuccess('Perfil e foto atualizados com sucesso!')
      setTimeout(() => {
        onClose()
      }, 1200)
    } catch (err) {
      setError(getErrorMessage(err, 'Não foi possível salvar as alterações. Tente novamente.'))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        className="profile-modal-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="profile-modal-title"
      >
        <header className="profile-modal-header">
          <div>
            <div className="profile-modal-badge">
              <Sparkles size={13} />
              Configurações de Conta
            </div>
            <h2 id="profile-modal-title" className="profile-modal-title">
              Meu Perfil
            </h2>
            <p className="profile-modal-subtitle">
              Altere sua foto de identificação e atualize seus dados de cadastro.
            </p>
          </div>
          <button
            type="button"
            className="icon-button profile-modal-close"
            onClick={onClose}
            aria-label="Fechar modal de perfil"
          >
            <X size={18} />
          </button>
        </header>

        <form onSubmit={handleSubmit} className="profile-modal-body">
          <div className="profile-modal-grid">
            {/* Seção da Foto */}
            <div className="profile-modal-avatar-section">
              <div
                className={`avatar-uploader avatar-uploader--modal${isDragging ? ' avatar-uploader--dragging' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    fileInputRef.current?.click()
                  }
                }}
                aria-label="Alterar foto de perfil"
                title="Clique ou arraste uma foto para cá"
              >
                <div className="avatar-uploader__preview avatar-uploader__preview--modal">
                  {avatarUrl ? (
                    <img src={avatarUrl} alt={name || 'Foto de perfil'} className="avatar-uploader__img" />
                  ) : (
                    <div className="avatar-uploader__initials avatar-uploader__initials--modal">{initials}</div>
                  )}
                  <div className="avatar-uploader__overlay">
                    <Camera size={22} />
                    <span>Alterar foto</span>
                  </div>
                </div>
              </div>

              <input
                ref={fileInputRef}
                type="file"
                accept="image/png, image/jpeg, image/webp"
                className="sr-only"
                onChange={handleFileInputChange}
                aria-label="Upload de foto de perfil"
              />

              <div className="avatar-actions avatar-actions--modal">
                <button
                  type="button"
                  className="primary-button avatar-actions__upload"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Upload size={14} />
                  {avatarUrl ? 'Substituir foto' : 'Carregar foto'}
                </button>

                {avatarUrl ? (
                  <button
                    type="button"
                    className="icon-button avatar-actions__remove"
                    onClick={handleRemovePhoto}
                    title="Remover foto"
                    aria-label="Remover foto"
                  >
                    <Trash2 size={15} />
                  </button>
                ) : null}
              </div>

              <p className="avatar-tip">Formatos: JPG, PNG ou WebP. Até 8MB.</p>

              <div className="profile-security-badge profile-security-badge--modal">
                <ShieldCheck size={14} />
                <span>Foto visível na barra e nos atendimentos.</span>
              </div>
            </div>

            {/* Seção dos Campos */}
            <div className="profile-modal-fields">
              <label className="input-group">
                <span>Nome completo</span>
                <div className="input-shell">
                  <User size={18} />
                  <input
                    id="modal-profile-name"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Seu nome completo"
                    autoComplete="name"
                    minLength={2}
                    maxLength={80}
                    required
                  />
                </div>
              </label>

              <label className="input-group">
                <span>Cidade de residência</span>
                <div className="input-shell">
                  <MapPin size={18} />
                  <input
                    id="modal-profile-city"
                    type="text"
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    placeholder="Ex: Marília, SP"
                    autoComplete="address-level2"
                    maxLength={80}
                    required
                  />
                </div>
              </label>

              <label className="input-group">
                <span>E-mail cadastrado</span>
                <div className="input-shell input-shell--disabled">
                  <Mail size={18} />
                  <input id="modal-profile-email" type="email" value={email} disabled readOnly />
                </div>
                <small className="input-hint">E-mail associado à sua conta de paciente.</small>
              </label>
            </div>
          </div>

          {success ? (
            <div className="info-banner profile-success-banner">
              <CheckCircle2 size={18} />
              <span>{success}</span>
            </div>
          ) : null}

          {error ? <div className="error-banner">{error}</div> : null}

          <footer className="profile-modal-footer">
            <button type="button" className="icon-button profile-modal-cancel" onClick={onClose} disabled={isLoading}>
              Cancelar
            </button>
            <button
              type="submit"
              id="modal-profile-save"
              className="primary-button profile-submit-button"
              disabled={isLoading}
            >
              <Save size={16} />
              {isLoading ? 'Salvando...' : 'Salvar alterações'}
            </button>
          </footer>
        </form>
      </div>
    </div>
  )
}
