import api from './axios'

export const createBooking = (payload) => api.post('/bookings/', payload).then((r) => r.data)
export const cancelBooking = (id, reason) =>
  api.post(`/bookings/${id}/cancel/`, { reason: reason || '' }).then((r) => r.data)