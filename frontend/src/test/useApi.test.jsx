import { describe, expect, it } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import useApi from '../hooks/useApi'
import { server } from './server'
import { API, apiError } from './handlers'

describe('useApi', () => {
  it('loads data and clears loading', async () => {
    server.use(http.get(`${API}/things/`, () => HttpResponse.json({ count: 1 })))
    const { result } = renderHook(() => useApi('/things/'))

    expect(result.current.loading).toBe(true)
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.data).toEqual({ count: 1 })
    expect(result.current.error).toBeNull()
  })

  it('exposes a normalized error', async () => {
    server.use(http.get(`${API}/things/`, () => apiError(404, { detail: 'Not found.' })))
    const { result } = renderHook(() => useApi('/things/'))

    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.data).toBeNull()
    expect(result.current.error).toMatchObject({ status: 404, message: 'Not found.' })
  })

  it('does not request when enabled=false', async () => {
    let calls = 0
    server.use(
      http.get(`${API}/things/`, () => {
        calls += 1
        return HttpResponse.json({})
      }),
    )
    const { result } = renderHook(() => useApi('/things/', {}, { enabled: false }))
    expect(result.current.loading).toBe(false)
    await new Promise((r) => setTimeout(r, 50))
    expect(calls).toBe(0)
  })

  it('sends array params as repeated keys (no [] suffix)', async () => {
    let url = null
    server.use(
      http.get(`${API}/properties/`, ({ request }) => {
        url = new URL(request.url)
        return HttpResponse.json({ results: [] })
      }),
    )
    const { result } = renderHook(() => useApi('/properties/', { property_type: ['villa', 'house'] }))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(url.searchParams.getAll('property_type')).toEqual(['villa', 'house'])
  })
})