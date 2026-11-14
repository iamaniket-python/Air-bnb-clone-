import { useState } from 'react'
import { FaStar } from 'react-icons/fa'
import Modal from './Modal'
import Button from './Button'
import Alert from './Alert'
import useToast from '../hooks/useToast'
import { createReview } from '../api/reviews'
import { normalizeApiError } from '../utils/apiError'
import { errorText } from '../utils/errors'

export default function ReviewModal({ booking, onClose, onDone }) {
  const toast = useToast()
  const [rating, setRating] = useState(0)
  const [comment, setComment] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    if (rating < 1) {
      setError('Please select a rating from 1 to 5.')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      const payload = { booking: booking.id, rating }
      if (comment.trim()) payload.comment = comment.trim()
      await createReview(payload)
      toast.success('Thanks! Your review has been posted.')
      onDone()
    } catch (err) {
      setError(errorText(normalizeApiError(err)))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal title={`Review ${booking.property?.title ?? 'your stay'}`} onClose={onClose}>
      <div className="space-y-4">
        <div>
          <p className="mb-1 text-sm font-medium text-slate-700">Your rating</p>
          <div className="flex gap-1" role="radiogroup" aria-label="Rating">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                role="radio"
                aria-checked={rating === n}
                aria-label={`${n} star${n > 1 ? 's' : ''}`}
                onClick={() => setRating(n)}
                className="rounded p-1"
              >
                <FaStar className={`h-7 w-7 ${n <= rating ? 'text-amber-500' : 'text-slate-200'}`} />
              </button>
            ))}
          </div>
        </div>

        <div>
          <label htmlFor="review-comment" className="mb-1 block text-sm font-medium text-slate-700">
            Comment (optional)
          </label>
          <textarea
            id="review-comment"
            rows={4}
            maxLength={2000}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-100"
          />
          <p className="mt-1 text-right text-xs text-slate-400">{comment.length}/2000</p>
        </div>

        <Alert message={error} />

        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose} disabled={submitting}>Close</Button>
          <Button loading={submitting} onClick={submit}>Submit review</Button>
        </div>
      </div>
    </Modal>
  )
}