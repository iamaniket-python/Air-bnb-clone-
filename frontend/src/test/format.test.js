import { describe, expect, it } from 'vitest'
import { formatDate, formatINR, fullName, initials } from '../utils/format'

describe('formatINR', () => {
  it('formats money strings in INR', () => {
    const out = formatINR('7500.00')
    expect(out).toContain('₹')
    expect(out).toContain('7,500')
  })
  it('returns a dash for invalid input', () => {
    expect(formatINR('abc')).toBe('—')
  })
})

describe('formatDate', () => {
  it('formats YYYY-MM-DD without timezone shift', () => {
    expect(formatDate('2026-03-05')).toMatch(/5/)
    expect(formatDate('2026-03-05')).toMatch(/2026/)
  })
  it('handles empty values', () => {
    expect(formatDate('')).toBe('—')
    expect(formatDate(null)).toBe('—')
  })
})

describe('names', () => {
  it('fullName prefers first+last, falls back to username', () => {
    expect(fullName({ first_name: 'Asha', last_name: 'Rao', username: 'asha' })).toBe('Asha Rao')
    expect(fullName({ username: 'asha' })).toBe('asha')
    expect(fullName(null)).toBe('')
  })
  it('initials', () => {
    expect(initials({ first_name: 'Asha', last_name: 'Rao' })).toBe('AR')
    expect(initials({ username: 'zed' })).toBe('Z')
    expect(initials(null)).toBe('?')
  })
})