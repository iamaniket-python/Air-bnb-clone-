import { Link } from 'react-router-dom'
import { FiImage } from 'react-icons/fi'
import StatusBadge from './StatusBadge'
import Button from './Button'
import { formatDate, formatINR } from '../utils/format'
import { mediaUrl } from '../utils/media'

export default function BookingCard({ booking, paid, reviewed, onCancel, onReview }) {
  const p = booking.property
  const img = mediaUrl(p?.cover_image)
  const actions = booking.available_actions ?? []

  const canCancel = actions.includes('cancel')
  const canPay = booking.status === 'confirmed' && !paid
  const canReview = booking.status === 'completed' && !reviewed
  const showReason = ['cancelled', 'rejected'].includes(booking.status) && booking.cancellation_reason

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 p-4 sm:flex-row">
      <Link to={`/properties/${p?.id}`} className="block h-32 w-full shrink-0 overflow-hidden rounded-xl bg-slate-100 sm:w-48">
        {img ? (
          <img src={img} alt={p?.title} loading="lazy" className="h-full w-full object-cover" />
        ) : (
          <span className="flex h-full w-full items-center justify-center text-slate-300">
            <FiImage className="h-8 w-8" />
          </span>
        )}
      </Link>

      <div className="flex-1 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <Link to={`/properties/${p?.id}`} className="font-semibold hover:underline">
            {p?.title}
          </Link>
          <StatusBadge status={booking.status} />
          {paid && booking.status !== 'cancelled' && (
            <span className="rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">Paid</span>
          )}
        </div>
        <p className="text-sm text-slate-500">{[p?.city, p?.state].filter(Boolean).join(', ')}</p>
        <p className="text-sm text-slate-700">
          {formatDate(booking.check_in)} → {formatDate(booking.check_out)} · {booking.nights}{' '}
          {booking.nights === 1 ? 'night' : 'nights'} · {booking.num_guests} {booking.num_guests === 1 ? 'guest' : 'guests'}
        </p>
        <p className="text-sm font-semibold">{formatINR(booking.total_price)}</p>
        {showReason && <p className="text-xs text-slate-500">Reason: {booking.cancellation_reason}</p>}
      </div>

      {(canPay || canCancel || canReview) && (
        <div className="flex flex-row gap-2 sm:flex-col sm:justify-center">
          {canPay && (
            <Link to={`/payment/${booking.id}`}>
              <Button size="sm" className="w-full">Pay now</Button>
            </Link>
          )}
          {canReview && (
            <Button size="sm" variant="secondary" onClick={() => onReview(booking)}>
              Write a review
            </Button>
          )}
          {canCancel && (
            <Button size="sm" variant="ghost" className="text-red-600 hover:bg-red-50" onClick={() => onCancel(booking)}>
              Cancel
            </Button>
          )}
        </div>
      )}
    </div>
  )
}