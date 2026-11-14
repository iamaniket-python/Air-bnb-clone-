import { API_BASE_URL } from '../api/axios'

// API base se backend origin nikalta hai (http://127.0.0.1:8000)
let ORIGIN = ''
try {
  ORIGIN = new URL(API_BASE_URL).origin
} catch {
  ORIGIN = ''
}

// Image value string ho ya object ({image|url}), dono se usable URL banata hai
export function mediaUrl(value) {
  if (!value) return null
  const src = typeof value === 'string' ? value : value.image || value.url || value.secure_url
  if (!src) return null
  if (/^(https?:)?\/\//.test(src) || src.startsWith('data:')) return src
  return `${ORIGIN}${src.startsWith('/') ? '' : '/'}${src}`
}