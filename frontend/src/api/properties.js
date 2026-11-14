import api from './axios'

export const createProperty = (payload) => api.post('/properties/', payload).then((r) => r.data)
export const updateProperty = (id, payload) => api.patch(`/properties/${id}/`, payload).then((r) => r.data)
export const deleteProperty = (id) => api.delete(`/properties/${id}/`)

// Multipart: key "images" (max 15 files, 5MB each). Upload slow ho sakta hai, isliye bada timeout.
export const uploadImages = (id, files) => {
  const form = new FormData()
  files.forEach((file) => form.append('images', file))
  return api.post(`/properties/${id}/images/`, form, { timeout: 120000 }).then((r) => r.data)
}
export const updateImage = (propertyId, imageId, payload) =>
  api.patch(`/properties/${propertyId}/images/${imageId}/`, payload).then((r) => r.data)
export const deleteImage = (propertyId, imageId) => api.delete(`/properties/${propertyId}/images/${imageId}/`)