import { describe, expect, it } from 'vitest'
import { cleanParams } from '../utils/params'
import { buildSearchUrl } from '../utils/search'

describe('cleanParams', () => {
  it('drops empty values but keeps 0 and false', () => {
    expect(cleanParams({ a: '', b: null, c: undefined, d: 0, e: false, f: 'x' })).toEqual({ d: 0, e: false, f: 'x' })
  })
})

describe('buildSearchUrl', () => {
  it('returns /properties when nothing is set', () => {
    expect(buildSearchUrl({})).toBe('/properties')
  })
  it('includes dates only when both are present', () => {
    expect(buildSearchUrl({ destination: 'Goa', check_in: '2026-03-01' })).toBe('/search?destination=Goa')
    const url = buildSearchUrl({ destination: 'Goa', check_in: '2026-03-01', check_out: '2026-03-03', guests: 3 })
    expect(url).toContain('check_in=2026-03-01')
    expect(url).toContain('check_out=2026-03-03')
    expect(url).toContain('guests=3')
  })
})