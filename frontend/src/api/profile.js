import api from './axios'

export const updateProfile = (payload) => api.patch('/auth/profile/', payload).then((r) => r.data)