import { Eye, EyeOff, Lock, Mail } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { AuthVisual } from '../components/AuthVisual'
import { BrandMark } from '../components/BrandMark'
import { login } from '../services/api'
import { getStoredSession, saveStoredSession } from '../services/session'

export function LoginPage() {
  const navigate = useNavigate()
  const session = getStoredSession()
  const [email, setEmail] = useState('marina.santos@medflux.com')
  const [password, setPassword] = useState('123456')
  const [remember, setRemember] = useState(true)
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (session) {
    return <Navigate to="/dashboard" replace />
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsLoading(true)
    setError(null)

    try {
      const response = await login(email, password)

      saveStoredSession(response, remember)

      navigate('/dashboard', { replace: true })
    } catch {
      setError('Não foi possível autenticar agora. Tente novamente.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="login-shell">
      <div className="login-grid">
        <AuthVisual />

        <section className="login-panel">
          <div className="login-card">
            <div className="login-card__brand login-card__brand--login">
              <BrandMark compact />
            </div>
            <h2 className="login-card__title">Bem Vindo</h2>
            <p className="login-card__subtitle">Digite suas credenciais para poder acessar sua conta</p>

            <form className="form-stack" onSubmit={handleSubmit}>
              <label className="input-group">
                <span>Email</span>
                <div className="input-shell">
                  <Mail size={18} />
                  <input
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="seuemail@exemplo.com"
                    autoComplete="email"
                  />
                </div>
              </label>

              <label className="input-group">
                <span>Senha</span>
                <div className="input-shell input-shell--password">
                  <Lock size={18} />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="Digite sua senha"
                    autoComplete="current-password"
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

              <div className="form-meta">
                <label className="form-meta__remember">
                  <input
                    type="checkbox"
                    checked={remember}
                    onChange={(event) => setRemember(event.target.checked)}
                  />
                  Lembre-se
                </label>
                <a href="/login" onClick={(event) => event.preventDefault()}>
                  Esqueceu a senha?
                </a>
              </div>

              {error ? <div className="error-banner">{error}</div> : null}

              <button type="submit" className="primary-button" disabled={isLoading}>
                {isLoading ? 'Entrando...' : 'Entrar na conta'}
              </button>

              <p className="secondary-copy">
                Ainda não é cadastrado?{' '}
                <Link className="secondary-link" to="/cadastro">
                  Crie sua Conta
                </Link>
              </p>
            </form>
          </div>
        </section>
      </div>
    </div>
  )
}