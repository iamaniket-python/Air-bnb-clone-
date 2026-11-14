import { describe, expect, it } from 'vitest'
import { addDaysISO, nightsBetween, toISODate } from '../utils/dates'

describe('dates utils', () => {
  it('toISODate uses local date parts', () => {
    expect(toISODate(new Date(2026, 0, 5))).toBe('2026-01-05')
  })
  it('addDaysISO crosses month and year boundaries', () => {
    expect(addDaysISO('2026-01-31', 1)).toBe('2026-02-01')
    expect(addDaysISO('2026-12-31', 1)).toBe('2027-01-01')
  })
  it('nightsBetween', () => {
    expect(nightsBetween('2026-03-01', '2026-03-04')).toBe(3)
    expect(nightsBetween('', '2026-03-04')).toBe(0)
  })
})