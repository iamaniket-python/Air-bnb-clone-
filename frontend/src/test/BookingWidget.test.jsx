import { describe, expect, it } from 'vitest'
import { screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import BookingWidget from '../components/BookingWidget'
import { server } from './server'
import { API } from './handlers'
import { addDaysISO, todayISO } from '../utils/dates'
import { renderWithProviders, seedSession } from './utils'

const property = { id: 7, price_per_night: '3000.00', max_guests: 4, average_rating: '4.50', review_count: 2 }

const checkIn = addDaysISO(todayISO(), 10)
const checkOut = addDaysISO(todayISO(), 13)

function loginAs(role) {
  const user = { id: 1, username: 'u', email: 'u@x.com', role, first_name: 'U', last_name: 'X' }
  seedSession({ user })
  server.use(http.get(`${API}/auth/profile/`, () => HttpResponse.json(user)))
}

describe('BookingWidget', () => {
  it('asks for dates first and disables Reserve', () => {
    renderWithProviders(<BookingWidget property={property} />)
    expect(screen.getByText(/select your dates/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /reserve/i })).toBeDisabled()
  })

  it('shows the server quote and enables Reserve when available', async () => {
    loginAs('guest')
    server.use(
      http.get(`${API}/bookings/quote/`, () =>
        HttpResponse.json({ available: true, reasons: [], nights: 3, price_per_night: '3000.00', total_price: '9000.00' }),
      ),
    )
    renderWithProviders(<BookingWidget property={property} initial={{ checkIn, checkOut, guests: 2 }} />)

    expect(await screen.findByText(/3 nights/i)).toBeInTheDocument()
    expect(screen.getAllByText(/9,000/).length).toBeGreaterThan(0)
    expect(await screen.findByRole('button', { name: /^reserve$/i })).toBeEnabled()
  })

  it('shows unavailable reasons and keeps Reserve disabled', async () => {
    loginAs('guest')
    server.use(
      http.get(`${API}/bookings/quote/`, () =>
        HttpResponse.json({ available: false, reasons: ['Selected dates are already booked.'] }),
      ),
    )
    renderWithProviders(<BookingWidget property={property} initial={{ checkIn, checkOut, guests: 2 }} />)

    expect(await screen.findByText(/already booked/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /reserve/i })).toBeDisabled()
  })

  it('blocks host accounts from booking', async () => {
    loginAs('host')
    server.use(
      http.get(`${API}/bookings/quote/`, () =>
        HttpResponse.json({ available: true, reasons: [], nights: 3, price_per_night: '3000.00', total_price: '9000.00' }),
      ),
    )
    renderWithProviders(<BookingWidget property={property} initial={{ checkIn, checkOut, guests: 2 }} />)

    expect(await screen.findByText(/cannot book stays/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /reserve/i })).toBeDisabled()
  })
})