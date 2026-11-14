import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import ToastProvider from '../context/ToastProvider'
import AuthProvider from '../context/AuthProvider'
import WishlistProvider from '../context/WishlistProvider'

// Real providers + MemoryRouter. route = starting URL.
export function renderWithProviders(ui, { route = '/' } = {}) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <ToastProvider>
        <AuthProvider>
          <WishlistProvider>{ui}</WishlistProvider>
        </AuthProvider>
      </ToastProvider>
    </MemoryRouter>,
  )
}

// Logged-in state seed karne ke liye (AuthProvider reload par ye padhta hai)
export function seedSession({ user, access = 'access-token', refresh = 'refresh-token' }) {
  localStorage.setItem('staynest_access', access)
  localStorage.setItem('staynest_refresh', refresh)
  localStorage.setItem('staynest_user', JSON.stringify(user))
}