import api from './axios'

// status: "confirmed" | "rejected" | "completed". Cancel ke liye bookings.js ka cancelBooking use hota hai.
export const updateBookingStatus = (id, status, reason) => {
  const payload = { status }
  if (reason) payload.reason = reason
  return api.patch(`/bookings/${id}/status/`, payload).then((r) => r.data)
}