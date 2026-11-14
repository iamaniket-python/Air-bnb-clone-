import api from './axios'

export const createReview = (payload) => api.post('/reviews/', payload).then((r) => r.data)