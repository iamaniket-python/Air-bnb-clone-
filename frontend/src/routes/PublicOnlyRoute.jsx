import { Navigate, Outlet } from 'react-router-dom'
import useAuth from '../hooks/useAuth'
import { FullPageLoader } from '../components/Spinner'
import { getDefaultRouteForRole } from '../utils/roles'

// Login/Register: logged-in user ko yahan se hata do
export default function PublicOnlyRoute() {
  const { isAuthenticated, bootstrapping, role } = useAuth()

  if (bootstrapping) return <FullPageLoader />
  if (isAuthenticated) return <Navigate to={getDefaultRouteForRole(role)} replace />

  return <Outlet />
}