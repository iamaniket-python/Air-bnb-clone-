import { describe, expect, it } from 'vitest'
import { Route, Routes } from 'react-router-dom'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import Login from '../pages/Login'
import { server } from './server'
import { API, apiError, fakeJwt } from './handlers'
import { renderWithProviders } from './utils'

function renderLogin() {
  return renderWithProviders(
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<div>HOME PAGE</div>} />
      <Route path="/host/dashboard" element={<div>HOST DASHBOARD</div>} />
    </Routes>,
    { route: '/login' },
  )
}

describe('Login page', () => {
  it('shows validation errors when submitted empty', async () => {
    const user = userEvent.setup()
    renderLogin()
    await user.click(screen.getByRole('button', { name: /log in/i }))
    expect(await screen.findByText(/username or email is required/i)).toBeInTheDocument()
    expect(screen.getByText(/password is required/i)).toBeInTheDocument()
  })

  it('logs in a guest, stores tokens and redirects home', async () => {
    const user = userEvent.setup()
    server.use(
      http.post(`${API}/auth/login/`, () =>
        HttpResponse.json({
          access: fakeJwt({ role: 'guest', username: 'asha' }),
          refresh: 'refresh-1',
          user: { id: 1, username: 'asha', email: 'a@x.com', role: 'guest', first_name: 'Asha', last_name: 'Rao' },
        }),
      ),
    )
    renderLogin()
    await user.type(screen.getByLabelText(/username or email/i), 'asha')
    await user.type(screen.getByLabelText(/^password$/i), 'StrongPass@123')
    await user.click(screen.getByRole('button', { name: /log in/i }))

    expect(await screen.findByText('HOME PAGE')).toBeInTheDocument()
    expect(localStorage.getItem('staynest_refresh')).toBe('refresh-1')
  })

  it('redirects a host to the host dashboard', async () => {
    const user = userEvent.setup()
    server.use(
      http.post(`${API}/auth/login/`, () =>
        HttpResponse.json({
          access: fakeJwt({ role: 'host', username: 'hosty' }),
          refresh: 'r',
          user: { id: 2, username: 'hosty', email: 'h@x.com', role: 'host', first_name: 'Host', last_name: 'Y' },
        }),
      ),
    )
    renderLogin()
    await user.type(screen.getByLabelText(/username or email/i), 'hosty')
    await user.type(screen.getByLabelText(/^password$/i), 'StrongPass@123')
    await user.click(screen.getByRole('button', { name: /log in/i }))
    expect(await screen.findByText('HOST DASHBOARD')).toBeInTheDocument()
  })

  it('shows the server error for wrong credentials', async () => {
    const user = userEvent.setup()
    server.use(http.post(`${API}/auth/login/`, () => apiError(401, { detail: 'No active account found with the given credentials' })))
    renderLogin()
    await user.type(screen.getByLabelText(/username or email/i), 'asha')
    await user.type(screen.getByLabelText(/^password$/i), 'wrong')
    await user.click(screen.getByRole('button', { name: /log in/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/no active account/i)
    await waitFor(() => expect(localStorage.getItem('staynest_refresh')).toBeNull())
  })
})