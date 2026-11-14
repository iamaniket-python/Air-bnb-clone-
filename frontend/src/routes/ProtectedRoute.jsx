import { Navigate, Outlet, useLocation } from 'react-router-dom'
import useAuth from '../hooks/useAuth'
import { FullPageLoader } from '../components/Spinner'

// <ProtectedRoute /> => sirf login chahiye
// <ProtectedRoute roles={['host']} /> => login + role match
export default function ProtectedRoute({ roles }) {
  const { isAuthenticated, bootstrapping, role } = useAuth()
  const location = useLocation()

  if (bootstrapping) return <FullPageLoader label="Checking your session..." />

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  if (roles && !roles.includes(role)) {
    return <Navigate to="/403" replace />
  }

  return <Outlet />
}