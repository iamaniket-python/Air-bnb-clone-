import { describe, expect, it } from 'vitest'
import { decodeJwt } from '../utils/jwt'
import { fakeJwt } from './handlers'

describe('decodeJwt', () => {
  it('reads claims', () => {
    const token = fakeJwt({ role: 'host', username: 'asha' })
    expect(decodeJwt(token)).toMatchObject({ role: 'host', username: 'asha' })
  })
  it('returns null for garbage', () => {
    expect(decodeJwt('not-a-token')).toBeNull()
  })
})