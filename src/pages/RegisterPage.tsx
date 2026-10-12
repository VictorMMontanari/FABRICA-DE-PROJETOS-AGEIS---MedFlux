import { Eye, EyeOff, Lock, Mail, MapPin, User } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { AuthVisual } from '../components/AuthVisual'
import { BrandMark } from '../components/BrandMark'
import { register } from '../services/api'
import { getStoredSession, saveStoredSession } from '../services/session'

const MIN_PASSWORD_LENGTH = 6

export function RegisterPage() {
  const navigate = useNavigate()
  const session = getStoredSession()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [city, setCity] = useState('Marília, SP')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (session) {
    return <Navigate to="/dashboard" replace />
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)

    if (password !== confirmPassword) {
      setError('As senhas não conferem.')
      return
    }

    setIsLoading(true)

    try {
      const response = await register({ name: name.trim(), email: email.trim(), password, city: city.trim() })

      saveStoredSession(response)

      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível criar sua conta agora.')
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
            <h2 className="login-card__title">Crie sua conta</h2>
            <p className="login-card__subtitle">Preencha seus dados para começar a usar o MedFlux</p>

            <form className="form-stack" onSubmit={handleSubmit}>
              <label className="input-group">
                <span>Nome completo</span>
                <div className="input-shell">
                  <User size={18} />
                  <input
                    type="text"
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    placeholder="Seu nome"
                    autoComplete="name"
                    required
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
                    placeholder="seuemail@exemplo.com"
                    autoComplete="email"
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
                    required
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
                    placeholder={`Mínimo de ${MIN_PASSWORD_LENGTH} caracteres`}
                    autoComplete="new-password"
                    minLength={MIN_PASSWORD_LENGTH}
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

              <label className="input-group">
                <span>Confirmar senha</span>
                <div className="input-shell">
                  <Lock size={18} />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    placeholder="Repita sua senha"
                    autoComplete="new-password"
                    minLength={MIN_PASSWORD_LENGTH}
                    required
                  />
                </div>
              </label>

              {error ? <div className="error-banner">{error}</div> : null}

              <button type="submit" className="primary-button" disabled={isLoading}>
                {isLoading ? 'Criando conta...' : 'Criar conta'}
              </button>

              <p className="secondary-copy">
                Já tem uma conta?{' '}
                <Link className="secondary-link" to="/login">
                  Entrar
                </Link>
              </p>
            </form>
          </div>
        </section>
      </div>
    </div>
  )
}
