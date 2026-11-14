import api from './axios'

export const getWishlistIds = () => api.get('/wishlist/ids/').then((r) => r.data.property_ids ?? [])
export const addToWishlist = (propertyId) => api.post('/wishlist/', { property: propertyId }).then((r) => r.data)
export const removeFromWishlist = (propertyId) => api.delete(`/wishlist/property/${propertyId}/`)