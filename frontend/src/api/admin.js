import api from './axios'

export const setUserActive = (id, isActive) =>
  api.patch(`/admin/users/${id}/`, { is_active: isActive }).then((r) => r.data)

export const setPropertyActive = (id, isActive) =>
  api.patch(`/admin/properties/${id}/`, { is_active: isActive }).then((r) => r.data)

// Full delete properties.js ke deleteProperty se hota hai (/properties/{id}/)
export const deleteReview = (id) => api.delete(`/reviews/${id}/`)