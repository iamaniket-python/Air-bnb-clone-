import { describe, expect, it } from 'vitest'
import { Route, Routes } from 'react-router-dom'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import HeartButton from '../components/HeartButton'
import { server } from './server'
import { API, apiError } from './handlers'
import { renderWithProviders, seedSession } from './utils'

const guest = { id: 1, username: 'g', email: 'g@x.com', role: 'guest', first_name: 'G', last_name: 'X' }

function loginAsGuest(ids = []) {
  seedSession({ user: guest })
  server.use(
    http.get(`${API}/auth/profile/`, () => HttpResponse.json(guest)),
    http.get(`${API}/wishlist/ids/`, () => HttpResponse.json({ property_ids: ids })),
  )
}

const ui = (
  <Routes>
    <Route path="/" element={<HeartButton propertyId={5} />} />
    <Route path="/login" element={<div>LOGIN PAGE</div>} />
  </Routes>
)

describe('HeartButton', () => {
  it('sends anonymous users to login', async () => {
    const user = userEvent.setup()
    renderWithProviders(ui)
    await user.click(screen.getByRole('button', { name: /save to wishlist/i }))
    expect(await screen.findByText('LOGIN PAGE')).toBeInTheDocument()
  })

  it('shows saved state from /wishlist/ids/', async () => {
    loginAsGuest([5])
    renderWithProviders(ui)
    expect(await screen.findByRole('button', { name: /remove from wishlist/i })).toBeInTheDocument()
  })

  it('saves optimistically and calls the API', async () => {
    const user = userEvent.setup()
    loginAsGuest([])
    let body = null
    server.use(
      http.post(`${API}/wishlist/`, async ({ request }) => {
        body = await request.json()
        return HttpResponse.json({ id: 1 }, { status: 201 })
      }),
    )
    renderWithProviders(ui)
    const btn = await screen.findByRole('button', { name: /save to wishlist/i })
    await user.click(btn)

    expect(await screen.findByRole('button', { name: /remove from wishlist/i })).toBeInTheDocument()
    expect(body).toEqual({ property: 5 })
  })

  it('reverts when the API fails', async () => {
    const user = userEvent.setup()
    loginAsGuest([])
    server.use(http.post(`${API}/wishlist/`, () => apiError(400, { detail: 'Property is not available.' })))
    renderWithProviders(ui)
    await user.click(await screen.findByRole('button', { name: /save to wishlist/i }))

    await waitFor(() => expect(screen.getByRole('button', { name: /save to wishlist/i })).toBeInTheDocument())
    expect(await screen.findByText(/not available/i)).toBeInTheDocument() // error toast
  })
})