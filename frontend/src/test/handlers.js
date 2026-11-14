import { http, HttpResponse } from 'msw'

// vite.config.js ke test.env wale VITE_API_BASE_URL ke barabar (same-origin => CORS nahi)
export const API = 'http://localhost:3000/api'

// Default handlers (har test apne hisaab se server.use(...) se override kar sakta hai)
export const handlers = [
  http.get(`${API}/wishlist/ids/`, () => HttpResponse.json({ property_ids: [] })),
]

// Backend ka error format: {"success": false, "status_code": N, "errors": ...}
export function apiError(status, errors) {
  return HttpResponse.json({ success: false, status_code: status, errors }, { status })
}

// Test JWT: header.payload.signature (signature fake, kyunki frontend verify nahi karta)
export function fakeJwt(claims) {
  const b64 = (obj) => btoa(JSON.stringify(obj)).replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_')
  return `${b64({ alg: 'HS256', typ: 'JWT' })}.${b64(claims)}.sig`
}