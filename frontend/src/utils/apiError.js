const GENERIC = 'Something went wrong. Please try again.'

function toText(value) {
  if (Array.isArray(value)) return value.map(toText).join(' ')
  if (value && typeof value === 'object') return Object.values(value).map(toText).join(' ')
  return String(value ?? '')
}

/**
 * Backend ka error format:
 *   {"success": false, "status_code": N, "errors": {field: [..]} ya {"detail": ".."}}
 * Isko {status, message, fieldErrors} mein normalize karta hai.
 */
export function normalizeApiError(error) {
  if (!error?.response) {
    if (error?.code === 'ECONNABORTED') {
      return { status: 0, message: 'The request timed out. Please try again.', fieldErrors: {} }
    }
    return {
      status: 0,
      message: 'Cannot reach the server. Check your connection and try again.',
      fieldErrors: {},
    }
  }

  const { status, data } = error.response
  const errors = data?.errors
  const fieldErrors = {}
  let message = ''

  if (errors && typeof errors === 'object' && !Array.isArray(errors)) {
    for (const [key, value] of Object.entries(errors)) {
      const text = toText(value)
      if (key === 'detail' || key === 'non_field_errors') {
        message = message ? `${message} ${text}` : text
      } else {
        fieldErrors[key] = text
      }
    }
  } else if (Array.isArray(errors) || typeof errors === 'string') {
    message = toText(errors)
  } else if (typeof data?.detail === 'string') {
    message = data.detail
  }

  if (!message) {
    if (Object.keys(fieldErrors).length > 0) message = 'Please fix the highlighted fields.'
    else if (status >= 500) message = 'Server error. Please try again in a moment.'
    else message = GENERIC
  }

  return { status, message, fieldErrors }
}

/**
 * Server ke field errors ko react-hook-form mein set karta hai.
 * Jo field form mein nahi hai uske errors ek string mein wapas deta hai (Alert mein dikhane ke liye).
 */
export function applyFieldErrors(setError, fieldErrors, knownFields) {
  const unknown = []
  Object.entries(fieldErrors).forEach(([field, msg]) => {
    if (knownFields.includes(field)) {
      setError(field, { type: 'server', message: msg })
    } else {
      unknown.push(`${field}: ${msg}`)
    }
  })
  return unknown.join(' | ')
}