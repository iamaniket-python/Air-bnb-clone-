import api from './axios'

export const login = (payload) => api.post('/auth/login/', payload).then((r) => r.data)
export const register = (payload) => api.post('/auth/register/', payload).then((r) => r.data)
export const logout = (refresh) => api.post('/auth/logout/', { refresh }).then((r) => r.data)
export const getProfile = () => api.get('/auth/profile/').then((r) => r.data)