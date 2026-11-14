import { describe, expect, it } from 'vitest'
import { Route, Routes } from 'react-router-dom'
import { screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import ProtectedRoute from '../routes/ProtectedRoute'
import { server } from './server'
import { API } from './handlers'
import { renderWithProviders, seedSession } from './utils'

function renderAt(route) {
  return renderWithProviders(
    <Routes>
      <Route path="/login" element={<div>LOGIN PAGE</div>} />
      <Route path="/403" element={<div>FORBIDDEN PAGE</div>} />
      <Route element={<ProtectedRoute roles={['host']} />}>
        <Route path="/host/dashboard" element={<div>HOST AREA</div>} />
      </Route>
    </Routes>,
    { route },
  )
}

const asUser = (role) => {
  const user = { id: 1, username: 'u', email: 'u@x.com', role, first_name: 'U', last_name: 'X' }
  seedSession({ user })
  // AuthProvider reload par profile verify karta hai
  server.use(http.get(`${API}/auth/profile/`, () => HttpResponse.json(user)))
}

describe('ProtectedRoute', () => {
  it('redirects anonymous users to /login', async () => {
    renderAt('/host/dashboard')
    expect(await screen.findByText('LOGIN PAGE')).toBeInTheDocument()
  })

  it('lets the right role in', async () => {
    asUser('host')
    renderAt('/host/dashboard')
    expect(await screen.findByText('HOST AREA')).toBeInTheDocument()
  })

  it('sends the wrong role to /403', async () => {
    asUser('guest')
    renderAt('/host/dashboard')
    expect(await screen.findByText('FORBIDDEN PAGE')).toBeInTheDocument()
  })
})