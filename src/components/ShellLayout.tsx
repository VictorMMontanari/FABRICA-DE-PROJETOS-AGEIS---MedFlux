import { Bell, LogOut, Menu, Search, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { BrandMark } from './BrandMark'
import { ProfileModal } from './ProfileModal'
import { SiteFooter } from './SiteFooter'
import { clearStoredSession, getStoredSession } from '../services/session'

const NAV_ITEMS = [
  { label: 'Início', to: '/dashboard', end: true },
  { label: 'Minha Saúde', to: '/dashboard#my-health' },
  { label: 'Clínicas', to: '/map' },
  { label: 'Histórico de Sintomas', to: '/dashboard#history' },
]

export function ShellLayout() {
  const location = useLocation()
  const [session, setSession] = useState(getStoredSession)
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false)
  const user = session?.user

  useEffect(() => {
    function handleSessionUpdate() {
      setSession(getStoredSession())
    }
    window.addEventListener('medflux:session-updated', handleSessionUpdate)
    return () => {
      window.removeEventListener('medflux:session-updated', handleSessionUpdate)
    }
  }, [])

  // o menu fica aberto apenas na rota em que foi aberto: navegar o fecha automaticamente
  const currentLocation = `${location.pathname}${location.hash}`
  const [menuOpenedAt, setMenuOpenedAt] = useState<string | null>(null)
  const mobileMenuOpen = menuOpenedAt === currentLocation

  function toggleMobileMenu() {
    setMenuOpenedAt(mobileMenuOpen ? null : currentLocation)
  }

  function handleLogout() {
    clearStoredSession()
    window.location.assign('/login')
  }

  return (
    <div className="app-shell">
      <header className="header-shell">
        <div className="header-shell__bar">
          <BrandMark />

          <nav className="main-nav" aria-label="Navegação principal">
            {NAV_ITEMS.map((item) => {
              const isActive =
                item.to === '/dashboard'
                  ? location.pathname === '/dashboard'
                  : location.pathname === item.to.split('#')[0]

              const className = `main-nav__link${isActive && !item.to.includes('#') ? ' main-nav__link--active' : ''}`

              if (item.to.includes('#')) {
                return (
                  <Link key={item.label} to={item.to} className={className}>
                    {item.label}
                  </Link>
                )
              }

              return (
                <NavLink key={item.label} to={item.to} end={item.end} className={className}>
                  {item.label}
                </NavLink>
              )
            })}
          </nav>

          <div className="header-actions">
            <button type="button" className="icon-button header-actions__desktop-only" aria-label="Buscar">
              <Search size={18} />
            </button>
            <button type="button" className="icon-button header-actions__desktop-only" aria-label="Notificações">
              <Bell size={18} />
            </button>
            <button
              type="button"
              className="profile-chip profile-chip--clickable header-actions__desktop-only"
              onClick={() => setIsProfileModalOpen(true)}
              title="Meu Perfil"
              aria-label="Abrir meu perfil"
            >
              <div className="profile-chip__avatar">
                {user?.avatarUrl ? (
                  <img src={user.avatarUrl} alt={user.name} className="profile-chip__img" />
                ) : (
                  user?.avatarInitials ?? 'MS'
                )}
              </div>
              <div className="profile-chip__meta">
                <strong>{user?.name ?? 'Marina Santos'}</strong>
                <span>{user?.city ?? 'Marília, SP'}</span>
              </div>
            </button>
            <button
              type="button"
              className="icon-button header-actions__desktop-only"
              aria-label="Sair"
              onClick={handleLogout}
            >
              <LogOut size={18} />
            </button>
            <button
              type="button"
              className="icon-button header-actions__mobile-toggle"
              aria-label={mobileMenuOpen ? 'Fechar menu' : 'Abrir menu'}
              aria-expanded={mobileMenuOpen}
              aria-controls="mobile-menu-panel"
              onClick={toggleMobileMenu}
            >
              {mobileMenuOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
          </div>
        </div>

        {mobileMenuOpen ? (
          <div className="mobile-menu-panel" id="mobile-menu-panel">
            <nav className="mobile-menu-panel__nav" aria-label="Navegação móvel">
              {NAV_ITEMS.map((item) => {
                const isActive =
                  item.to === '/dashboard'
                    ? location.pathname === '/dashboard'
                    : location.pathname === item.to.split('#')[0]

                const className = `mobile-menu-panel__link${isActive && !item.to.includes('#') ? ' mobile-menu-panel__link--active' : ''}`

                if (item.to.includes('#')) {
                  return (
                    <Link key={item.label} to={item.to} className={className}>
                      {item.label}
                    </Link>
                  )
                }

                return (
                  <NavLink key={item.label} to={item.to} end={item.end} className={className}>
                    {item.label}
                  </NavLink>
                )
              })}
            </nav>

            <div className="mobile-menu-panel__actions">
              <button type="button" className="mobile-menu-panel__action" aria-label="Buscar">
                <Search size={16} />
                Buscar
              </button>
              <button type="button" className="mobile-menu-panel__action" aria-label="Notificações">
                <Bell size={16} />
                Notificações
              </button>
              <button
                type="button"
                className="mobile-menu-panel__profile profile-chip--clickable"
                onClick={() => {
                  setMenuOpenedAt(null)
                  setIsProfileModalOpen(true)
                }}
                title="Meu Perfil"
              >
                <div className="profile-chip__avatar">
                  {user?.avatarUrl ? (
                    <img src={user.avatarUrl} alt={user.name} className="profile-chip__img" />
                  ) : (
                    user?.avatarInitials ?? 'MS'
                  )}
                </div>
                <div className="profile-chip__meta">
                  <strong>{user?.name ?? 'Marina Santos'}</strong>
                  <span>{user?.city ?? 'Marília, SP'}</span>
                </div>
              </button>
              <button
                type="button"
                className="mobile-menu-panel__action mobile-menu-panel__action--danger"
                onClick={handleLogout}
              >
                <LogOut size={16} />
                Sair
              </button>
            </div>
          </div>
        ) : null}
      </header>

      <main className="content-frame page-shell">
        <Outlet />
      </main>

      <ProfileModal isOpen={isProfileModalOpen} onClose={() => setIsProfileModalOpen(false)} />

      <SiteFooter />
    </div>
  )
}