import { Eye, EyeOff, Lock } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { BrandMark } from '../components/BrandMark'
import { getErrorMessage, resetPassword } from '../services/api'

/** O link do e-mail do Supabase chega como /redefinir-senha#access_token=...&type=recovery */
function readRecoveryToken(): string | null {
  const params = new URLSearchParams(window.location.hash.replace(/^#/, ''))
  return params.get('access_token')
}

export function ResetPasswordPage() {
  const [token] = useState(readRecoveryToken)
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)

    if (password !== confirm) {
      setError('As senhas não conferem.')
      return
    }
    if (!token) {
      setError('Link inválido. Peça um novo e-mail de recuperação.')
      return
    }

    setIsLoading(true)
    try {
      const response = await resetPassword(token, password)
      setDone(response.message)
      window.history.replaceState(null, '', window.location.pathname) // remove o token da URL
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="login-shell reset-shell">
      <section className="login-panel">
        <div className="login-card">
          <div className="login-card__brand login-card__brand--login">
            <BrandMark compact />
          </div>
          <h1 className="login-card__title">Nova senha</h1>
          <p className="login-card__subtitle">Escolha uma nova senha para acessar o MedFlux.</p>

          {done ? (
            <div className="form-stack">
              <div className="info-banner">{done}</div>
              <Link to="/login" className="primary-button reset-shell__link">
                Ir para o login
              </Link>
            </div>
          ) : (
            <form className="form-stack" onSubmit={handleSubmit}>
              {!token ? (
                <div className="error-banner">
                  Link inválido ou incompleto. Volte ao login e use “Esqueceu a senha?” novamente.
                </div>
              ) : null}
              {[
                { id: 'reset-password', label: 'Nova senha', value: password, set: setPassword },
                { id: 'reset-confirm', label: 'Confirme a senha', value: confirm, set: setConfirm },
              ].map((field) => (
                <label key={field.id} className="input-group">
                  <span>{field.label}</span>
                  <div className="input-shell input-shell--password">
                    <Lock size={18} />
                    <input
                      id={field.id}
                      type={showPassword ? 'text' : 'password'}
                      value={field.value}
                      onChange={(event) => field.set(event.target.value)}
                      autoComplete="new-password"
                      minLength={6}
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
              ))}

              {error ? <div className="error-banner">{error}</div> : null}

              <button type="submit" id="reset-submit" className="primary-button" disabled={isLoading || !token}>
                {isLoading ? 'Salvando...' : 'Salvar nova senha'}
              </button>
              <p className="secondary-copy">
                <Link className="secondary-link" to="/login">
                  Voltar ao login
                </Link>
              </p>
            </form>
          )}
        </div>
      </section>
    </div>
  )
}
