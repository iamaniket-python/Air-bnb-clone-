import { useState } from 'react'
import Modal from './Modal'
import Button from './Button'
import Alert from './Alert'
import useToast from '../hooks/useToast'
import { cancelBooking } from '../api/bookings'
import { normalizeApiError } from '../utils/apiError'
import { errorText } from '../utils/errors'

// Parent isko `{target && <CancelModal key={target.id} ... />}` ki tarah render karta hai
export default function CancelModal({ booking, onClose, onDone }) {
  const toast = useToast()
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    setSubmitting(true)
    setError('')
    try {
      const res = await cancelBooking(booking.id, reason.trim())
      const refund = res?.refund_percentage
      toast.success(
        refund !== undefined && refund !== null
          ? `Booking cancelled. Refund: ${refund}%.`
          : res?.message || 'Booking cancelled.',
      )
      onDone()
    } catch (err) {
      setError(errorText(normalizeApiError(err)))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal title="Cancel this booking?" onClose={onClose}>
      <div className="space-y-4">
        <p className="text-sm text-slate-600">
          <strong>{booking.property?.title}</strong> ki booking cancel hogi. Refund policy:
        </p>
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600">
          <li>Pending request: 100% refund</li>
          <li>Confirmed, check-in se 48+ ghante pehle: 100%</li>
          <li>24 se 48 ghante pehle: 50%</li>
          <li>24 ghante se kam: 0%</li>
        </ul>

        <div>
          <label htmlFor="cancel-reason" className="mb-1 block text-sm font-medium text-slate-700">
            Reason (optional)
          </label>
          <textarea
            id="cancel-reason"
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-100"
          />
        </div>

        <Alert message={error} />

        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose} disabled={submitting}>Keep booking</Button>
          <Button variant="danger" loading={submitting} onClick={submit}>Cancel booking</Button>
        </div>
      </div>
    </Modal>
  )
}