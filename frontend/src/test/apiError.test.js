import { describe, expect, it, vi } from 'vitest'
import { applyFieldErrors, normalizeApiError } from '../utils/apiError'

const resp = (status, data) => ({ response: { status, data } })

describe('normalizeApiError', () => {
  it('network error (no response)', () => {
    const r = normalizeApiError(new Error('boom'))
    expect(r.status).toBe(0)
    expect(r.message).toMatch(/cannot reach the server/i)
  })

  it('timeout', () => {
    const r = normalizeApiError({ code: 'ECONNABORTED' })
    expect(r.message).toMatch(/timed out/i)
  })

  it('detail error becomes message', () => {
    const r = normalizeApiError(resp(403, { errors: { detail: 'Not allowed.' } }))
    expect(r.status).toBe(403)
    expect(r.message).toBe('Not allowed.')
    expect(r.fieldErrors).toEqual({})
  })

  it('field errors are split out and arrays joined', () => {
    const r = normalizeApiError(resp(400, { errors: { email: ['Invalid.', 'Taken.'], username: ['Required.'] } }))
    expect(r.fieldErrors).toEqual({ email: 'Invalid. Taken.', username: 'Required.' })
    expect(r.message).toBe('Please fix the highlighted fields.')
  })

  it('non_field_errors goes to message', () => {
    const r = normalizeApiError(resp(400, { errors: { non_field_errors: ['Passwords differ.'] } }))
    expect(r.message).toBe('Passwords differ.')
  })

  it('5xx gets a server error message', () => {
    const r = normalizeApiError(resp(500, {}))
    expect(r.message).toMatch(/server error/i)
  })
})

describe('applyFieldErrors', () => {
  it('sets known fields and returns unknown ones as text', () => {
    const setError = vi.fn()
    const extra = applyFieldErrors(setError, { email: 'Bad', mystery: 'Oops' }, ['email'])
    expect(setError).toHaveBeenCalledWith('email', { type: 'server', message: 'Bad' })
    expect(extra).toBe('mystery: Oops')
  })
})