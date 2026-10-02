import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { getStoredSession } from '../services/session'

export function ProtectedRoute() {
  const location = useLocation()
  const session = getStoredSession()

  if (!session) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return <Outlet />
}