import { describe, expect, it } from 'vitest'
import { Route, Routes } from 'react-router-dom'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import Register from '../pages/Register'
import { server } from './server'
import { API, apiError, fakeJwt } from './handlers'
import { renderWithProviders } from './utils'

// Typing aur assertion dono isi se lete hain, isliye kabhi mismatch nahi hoga
const FORM = {
  first_name: 'Aniket',
  last_name: 'Shrivastava',
  username: 'ani',
  email: 'asha@example.com',
  password: 'StrongPass@123',
}

function renderRegister() {
  return renderWithProviders(
    <Routes>
      <Route path="/register" element={<Register />} />
      <Route path="/" element={<div>HOME PAGE</div>} />
    </Routes>,
    { route: '/register' },
  )
}

async function fillForm(user, { password2 = FORM.password } = {}) {
  await user.type(screen.getByLabelText(/first name/i), FORM.first_name)
  await user.type(screen.getByLabelText(/last name/i), FORM.last_name)
  await user.type(screen.getByLabelText(/^username$/i), FORM.username)
  await user.type(screen.getByLabelText(/^email$/i), FORM.email)
  await user.type(screen.getByLabelText(/^password$/i), FORM.password)
  await user.type(screen.getByLabelText(/confirm password/i), password2)
}

describe('Register page', () => {
  it('validates required fields', async () => {
    const user = userEvent.setup()
    renderRegister()
    await user.click(screen.getByRole('button', { name: /create account/i }))
    expect(await screen.findByText(/first name is required/i)).toBeInTheDocument()
    expect(screen.getByText(/username is required/i)).toBeInTheDocument()
    expect(screen.getByText(/email is required/i)).toBeInTheDocument()
  })

  it('shows an error when passwords do not match', async () => {
    const user = userEvent.setup()
    renderRegister()
    await fillForm(user, { password2: 'Different@123' })
    await user.click(screen.getByRole('button', { name: /create account/i }))
    expect(await screen.findByText(/passwords do not match/i)).toBeInTheDocument()
  })

  it('submits the expected payload and redirects on success', async () => {
    const user = userEvent.setup()
    let body = null
    server.use(
      http.post(`${API}/auth/register/`, async ({ request }) => {
        body = await request.json()
        return HttpResponse.json(
          {
            user: {
              id: 5,
              username: FORM.username,
              email: FORM.email,
              role: 'guest',
              first_name: FORM.first_name,
              last_name: FORM.last_name,
            },
            tokens: { access: fakeJwt({ role: 'guest', username: FORM.username }), refresh: 'r-new' },
          },
          { status: 201 },
        )
      }),
    )
    renderRegister()
    await fillForm(user)
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByText('HOME PAGE')).toBeInTheDocument()
    expect(body).toMatchObject({
      role: 'guest',
      first_name: FORM.first_name,
      last_name: FORM.last_name,
      username: FORM.username,
      email: FORM.email,
      password: FORM.password,
      password2: FORM.password,
    })
    expect(body).not.toHaveProperty('phone_number') // optional khali => bheja nahi
  })

  it('maps a server field error under the field', async () => {
    const user = userEvent.setup()
    server.use(http.post(`${API}/auth/register/`, () => apiError(400, { email: ['A user with this email already exists.'] })))
    renderRegister()
    await fillForm(user)
    await user.click(screen.getByRole('button', { name: /create account/i }))
    expect(await screen.findByText(/already exists/i)).toBeInTheDocument()
  })
})