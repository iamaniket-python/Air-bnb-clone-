import { BrowserRouter, useLocation } from 'react-router-dom'
import AuthProvider from './context/AuthProvider'
import ToastProvider from './context/ToastProvider'
import WishlistProvider from './context/WishlistProvider'
import ErrorBoundary from './components/ErrorBoundary'
import AppRoutes from './routes/AppRoutes'

// Router ke andar hai taaki route badalne par boundary reset ho sake
function Shell() {
  const { pathname } = useLocation()
  return (
    <ErrorBoundary resetKey={pathname}>
      <AppRoutes />
    </ErrorBoundary>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <WishlistProvider>
            <Shell />
          </WishlistProvider>
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  )
}