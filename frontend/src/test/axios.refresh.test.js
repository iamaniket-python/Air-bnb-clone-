import { describe, expect, it } from 'vitest'
import { http, HttpResponse } from 'msw'
import api, { setAuthFailureHandler } from '../api/axios'
import { tokenStorage } from '../api/tokenStorage'
import { server } from './server'
import { API, apiError } from './handlers'

describe('axios interceptors', () => {
  it('attaches the Bearer token', async () => {
    tokenStorage.setTokens({ access: 'A1', refresh: 'R1' })
    let header = null
    server.use(
      http.get(`${API}/ping/`, ({ request }) => {
        header = request.headers.get('authorization')
        return HttpResponse.json({ ok: true })
      }),
    )
    await api.get('/ping/')
    expect(header).toBe('Bearer A1')
  })

  it('refreshes on 401, saves the ROTATED refresh token and retries', async () => {
    tokenStorage.setTokens({ access: 'old-access', refresh: 'old-refresh' })
    let refreshBody = null

    server.use(
      http.get(`${API}/secret/`, ({ request }) => {
        if (request.headers.get('authorization') === 'Bearer new-access') return HttpResponse.json({ ok: true })
        return apiError(401, { detail: 'Token expired' })
      }),
      http.post(`${API}/auth/refresh/`, async ({ request }) => {
        refreshBody = await request.json()
        return HttpResponse.json({ access: 'new-access', refresh: 'new-refresh' })
      }),
    )

    const res = await api.get('/secret/')
    expect(res.data).toEqual({ ok: true })
    expect(refreshBody).toEqual({ refresh: 'old-refresh' })
    expect(tokenStorage.getAccess()).toBe('new-access')
    expect(tokenStorage.getRefresh()).toBe('new-refresh') // rotation
  })

  it('single-flight: parallel 401s trigger only ONE refresh call', async () => {
    tokenStorage.setTokens({ access: 'old', refresh: 'r1' })
    let refreshCalls = 0

    server.use(
      http.get(`${API}/data/:n/`, ({ request }) => {
        if (request.headers.get('authorization') === 'Bearer fresh') return HttpResponse.json({ ok: true })
        return apiError(401, { detail: 'expired' })
      }),
      http.post(`${API}/auth/refresh/`, async () => {
        refreshCalls += 1
        await new Promise((r) => setTimeout(r, 30)) // overlap ka mauka do
        return HttpResponse.json({ access: 'fresh', refresh: 'r2' })
      }),
    )

    const results = await Promise.all([api.get('/data/1/'), api.get('/data/2/'), api.get('/data/3/')])
    expect(results.every((r) => r.data.ok)).toBe(true)
    expect(refreshCalls).toBe(1)
  })

  it('clears session and calls the failure handler when refresh fails', async () => {
    tokenStorage.setTokens({ access: 'old', refresh: 'dead' })
    tokenStorage.setUser({ username: 'asha' })
    let failed = false
    setAuthFailureHandler(() => {
      failed = true
    })

    server.use(
      http.get(`${API}/secret/`, () => apiError(401, { detail: 'expired' })),
      http.post(`${API}/auth/refresh/`, () => apiError(401, { detail: 'Token is blacklisted' })),
    )

    await expect(api.get('/secret/')).rejects.toBeDefined()
    expect(failed).toBe(true)
    expect(tokenStorage.getAccess()).toBeNull()
    expect(tokenStorage.getRefresh()).toBeNull()
    setAuthFailureHandler(null)
  })

  it('does NOT try to refresh on a failed login (401 = wrong credentials)', async () => {
    tokenStorage.setTokens({ access: 'a', refresh: 'r' })
    let refreshCalls = 0
    server.use(
      http.post(`${API}/auth/login/`, () => apiError(401, { detail: 'No active account found' })),
      http.post(`${API}/auth/refresh/`, () => {
        refreshCalls += 1
        return HttpResponse.json({ access: 'x', refresh: 'y' })
      }),
    )
    await expect(api.post('/auth/login/', { username: 'u', password: 'p' })).rejects.toBeDefined()
    expect(refreshCalls).toBe(0)
  })
})