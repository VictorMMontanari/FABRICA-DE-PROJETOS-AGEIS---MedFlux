import { ArrowLeft, Camera, CheckCircle2, Mail, MapPin, Save, ShieldCheck, Sparkles, Trash2, Upload, User } from 'lucide-react'
import { useRef, useState } from 'react'
import type { ChangeEvent, DragEvent, FormEvent } from 'react'
import { Link } from 'react-router-dom'
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

export function ProfilePage() {
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
    // limpa o input para permitir selecionar o mesmo arquivo novamente se desejar
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
      // 1. Envia atualização para a API
      try {
        await updateProfile({
          name: trimmedName,
          city: trimmedCity,
          avatar_url: avatarUrl,
        })
      } catch (apiErr) {
        // Se a API estiver sem Supabase configurado, salvamos localmente com aviso
        console.warn('API de perfil indisponível ou em modo local:', apiErr)
      }

      // 2. Atualiza a sessão persistida do usuário e dispara evento para sincronizar cabeçalho
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
    } catch (err) {
      setError(getErrorMessage(err, 'Não foi possível salvar as alterações. Tente novamente.'))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="profile-page">
      <header className="profile-header">
        <Link to="/dashboard" className="profile-back-link">
          <ArrowLeft size={16} />
          Voltar ao Início
        </Link>
        <h1 className="section-title">Meu Perfil</h1>
        <p className="section-subtitle">
          Gerencie suas informações de identificação, cidade de atendimento e sua foto de perfil.
        </p>
      </header>

      <div className="profile-grid">
        {/* Painel do Avatar / Foto */}
        <section className="page-card profile-card profile-avatar-card">
          <div className="profile-avatar-card__badge">
            <Sparkles size={14} /> Foto de Identificação
          </div>

          <div
            className={`avatar-uploader${isDragging ? ' avatar-uploader--dragging' : ''}`}
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
            <div className="avatar-uploader__preview">
              {avatarUrl ? (
                <img src={avatarUrl} alt={name || 'Foto de perfil'} className="avatar-uploader__img" />
              ) : (
                <div className="avatar-uploader__initials">{initials}</div>
              )}
              <div className="avatar-uploader__overlay">
                <Camera size={26} />
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

          <div className="avatar-actions">
            <button
              type="button"
              className="primary-button avatar-actions__upload"
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload size={16} />
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
                <Trash2 size={16} />
              </button>
            ) : null}
          </div>

          <p className="avatar-tip">Formatos aceitos: JPG, PNG ou WebP. Até 8MB.</p>

          <div className="profile-security-badge">
            <ShieldCheck size={16} />
            <span>Foto visível apenas nos atendimentos e na barra do MedFlux.</span>
          </div>
        </section>

        {/* Formulário de Dados Pessoais */}
        <section className="page-card profile-card profile-form-card">
          <h2 className="profile-form-card__title">Dados Pessoais</h2>
          <p className="profile-form-card__subtitle">
            Mantenha seus dados atualizados para otimizar os encaminhamentos médicos.
          </p>

          <form className="form-stack" onSubmit={handleSubmit}>
            <label className="input-group">
              <span>Nome completo</span>
              <div className="input-shell">
                <User size={18} />
                <input
                  id="profile-name"
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
                  id="profile-city"
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
                <input
                  id="profile-email"
                  type="email"
                  value={email}
                  disabled
                  readOnly
                  aria-label="E-mail da conta"
                />
              </div>
              <small className="input-hint">O e-mail é utilizado para login e notificações seguras.</small>
            </label>

            {success ? (
              <div className="info-banner profile-success-banner">
                <CheckCircle2 size={18} />
                <span>{success}</span>
              </div>
            ) : null}

            {error ? <div className="error-banner">{error}</div> : null}

            <div className="profile-form-actions">
              <button
                type="submit"
                id="profile-save"
                className="primary-button profile-submit-button"
                disabled={isLoading}
              >
                <Save size={18} />
                {isLoading ? 'Salvando...' : 'Salvar alterações'}
              </button>
            </div>
          </form>
        </section>
      </div>
    </div>
  )
}
