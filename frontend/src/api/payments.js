import api from './axios'

export const createPayment = (bookingId) => api.post('/payments/create/', { booking: bookingId }).then((r) => r.data)
export const mockCheckout = (payload) => api.post('/payments/mock-checkout/', payload).then((r) => r.data)
export const verifyPayment = (payload) => api.post('/payments/verify/', payload).then((r) => r.data)