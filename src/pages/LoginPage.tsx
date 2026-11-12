import { Eye, EyeOff, Lock, Mail, MapPin, User } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { BrandMark } from '../components/BrandMark'
import { forgotPassword, getErrorMessage, login, register } from '../services/api'
import { getStoredSession, saveStoredSession } from '../services/session'
import { MapContainer, TileLayer } from 'react-leaflet'

const LOGIN_MAP_CENTER: [number, number] = [-22.2167, -49.9501]

type Mode = 'login' | 'register' | 'forgot'

const COPY: Record<Mode, { title: string; subtitle: string; submit: string; loading: string }> = {
  login: {
    title: 'Bem Vindo',
    subtitle: 'Digite suas credenciais para poder acessar sua conta',
    submit: 'Entrar na conta',
    loading: 'Entrando...',
  },
  register: {
    title: 'Crie sua conta',
    subtitle: 'Leva menos de um minuto para começar a usar o MedFlux',
    submit: 'Criar conta',
    loading: 'Criando conta...',
  },
  forgot: {
    title: 'Recuperar senha',
    subtitle: 'Informe seu e-mail e enviaremos um link para criar uma nova senha',
    submit: 'Enviar link',
    loading: 'Enviando...',
  },
}

export function LoginPage() {
  const navigate = useNavigate()
  const session = getStoredSession()
  const [mode, setMode] = useState<Mode>('login')
  const [name, setName] = useState('')
  const [city, setCity] = useState('Marília, SP')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [remember, setRemember] = useState(true)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [info, setInfo] = useState<string | null>(null)

  if (session) {
    return <Navigate to="/dashboard" replace />
  }

  function switchMode(next: Mode) {
    setMode(next)
    setError(null)
    setInfo(null)
    setConfirmPassword('')
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsLoading(true)
    setError(null)
    setInfo(null)

    if (mode === 'register' && password !== confirmPassword) {
      setError('As senhas não coincidem. Digite a mesma senha nos dois campos.')
      setIsLoading(false)
      return
    }

    try {
      if (mode === 'forgot') {
        const response = await forgotPassword(email)
        setInfo(response.message)
        return
      }

      const response =
        mode === 'register' ? await register({ name, city, email, password }) : await login(email, password)

      saveStoredSession(response, remember)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(getErrorMessage(err, 'Não foi possível autenticar agora. Tente novamente.'))
    } finally {
      setIsLoading(false)
    }
  }

  const copy = COPY[mode]

  return (
    <div className="login-shell">
      <div className="login-grid">
        <section className="login-visual" aria-hidden="true">
          <div className="login-visual__map-frame">
            <MapContainer
              center={LOGIN_MAP_CENTER}
              zoom={13}
              scrollWheelZoom={false}
              dragging={false}
              doubleClickZoom={false}
              zoomControl={false}
              attributionControl={false}
              className="login-visual__map"
            >
              <TileLayer
                attribution='&copy; OpenStreetMap contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
            </MapContainer>
          </div>
          <div className="login-visual__overlay">
            <div className="login-visual__chip">Marília / SP</div>
            <div className="login-visual__chip login-visual__chip--soft">Mapa de atendimento</div>
          </div>
        </section>

        <section className="login-panel">
          <div className="login-card">
            <div className="login-card__brand login-card__brand--login">
              <BrandMark compact />
            </div>
            <h1 className="login-card__title">{copy.title}</h1>
            <p className="login-card__subtitle">{copy.subtitle}</p>

            <form className="form-stack" onSubmit={handleSubmit}>
              {mode === 'register' ? (
                <>
                  <label className="input-group">
                    <span>Nome completo</span>
                    <div className="input-shell">
                      <User size={18} />
                      <input
                        id="register-name"
                        type="text"
                        value={name}
                        onChange={(event) => setName(event.target.value)}
                        placeholder="Seu nome"
                        autoComplete="name"
                        minLength={2}
                        required
                      />
                    </div>
                  </label>
                  <label className="input-group">
                    <span>Cidade</span>
                    <div className="input-shell">
                      <MapPin size={18} />
                      <input
                        id="register-city"
                        type="text"
                        value={city}
                        onChange={(event) => setCity(event.target.value)}
                        placeholder="Cidade, UF"
                        autoComplete="address-level2"
                      />
                    </div>
                  </label>
                </>
              ) : null}

              <label className="input-group">
                <span>Email</span>
                <div className="input-shell">
                  <Mail size={18} />
                  <input
                    id="login-email"
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="seuemail@exemplo.com"
                    autoComplete="email"
                    required
                  />
                </div>
              </label>

              {mode !== 'forgot' ? (
                <label className="input-group">
                  <span>Senha</span>
                  <div className="input-shell input-shell--password">
                    <Lock size={18} />
                    <input
                      id="login-password"
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      placeholder={mode === 'register' ? 'Mínimo de 6 caracteres' : 'Digite sua senha'}
                      autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
                      minLength={mode === 'register' ? 6 : undefined}
                      required
                    />
                    <button
                      type="button"
                      className="input-shell__toggle"
                      aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
                      onClick={() => setShowPassword((current) => !current)}
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </label>
              ) : null}

              {mode === 'register' ? (
                <label className="input-group">
                  <span>Confirme sua senha</span>
                  <div className="input-shell input-shell--password">
                    <Lock size={18} />
                    <input
                      id="register-confirm-password"
                      type={showConfirmPassword ? 'text' : 'password'}
                      value={confirmPassword}
                      onChange={(event) => setConfirmPassword(event.target.value)}
                      placeholder="Repita sua senha"
                      autoComplete="new-password"
                      minLength={6}
                      required
                    />
                    <button
                      type="button"
                      className="input-shell__toggle"
                      aria-label={showConfirmPassword ? 'Ocultar confirmação de senha' : 'Mostrar confirmação de senha'}
                      onClick={() => setShowConfirmPassword((current) => !current)}
                    >
                      {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </label>
              ) : null}

              {mode !== 'forgot' ? (
                <div className="form-meta">
                  <label className="form-meta__remember">
                    <input
                      type="checkbox"
                      checked={remember}
                      onChange={(event) => setRemember(event.target.checked)}
                    />
                    Lembre-se
                  </label>
                  {mode === 'login' ? (
                    <button type="button" id="forgot-password-link" className="link-button" onClick={() => switchMode('forgot')}>
                      Esqueceu a senha?
                    </button>
                  ) : null}
                </div>
              ) : null}

              {error ? <div className="error-banner">{error}</div> : null}
              {info ? <div className="info-banner">{info}</div> : null}

              <button type="submit" id="auth-submit" className="primary-button" disabled={isLoading}>
                {isLoading ? copy.loading : copy.submit}
              </button>

              <p className="secondary-copy">
                {mode === 'login' ? (
                  <>
                    Ainda não é cadastrado?{' '}
                    <button type="button" id="register-link" className="secondary-link link-button" onClick={() => switchMode('register')}>
                      Crie sua Conta
                    </button>
                  </>
                ) : (
                  <>
                    {mode === 'register' ? 'Já tem conta?' : 'Lembrou a senha?'}{' '}
                    <button type="button" id="back-to-login" className="secondary-link link-button" onClick={() => switchMode('login')}>
                      Entrar
                    </button>
                  </>
                )}
              </p>
            </form>
          </div>
        </section>
      </div>
    </div>
  )
}