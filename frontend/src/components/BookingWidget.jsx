import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import DateRangeInput from './DateRangeInput'
import GuestSelector from './GuestSelector'
import Button from './Button'
import Alert from './Alert'
import Spinner from './Spinner'
import StarRating from './StarRating'
import useApi from '../hooks/useApi'
import useAuth from '../hooks/useAuth'
import { formatINR } from '../utils/format'

// initial: {checkIn, checkOut, guests} (search se aaye hue)
export default function BookingWidget({ property, initial = {} }) {
  const { isAuthenticated, role } = useAuth()
  const navigate = useNavigate()

  const [dates, setDates] = useState({ checkIn: initial.checkIn ?? '', checkOut: initial.checkOut ?? '' })
  const [guests, setGuests] = useState(Math.min(Number(initial.guests) || 1, property.max_guests))

  const ready = Boolean(dates.checkIn && dates.checkOut)
  const { data: quote, loading, error } = useApi(
    '/bookings/quote/',
    { property: property.id, check_in: dates.checkIn, check_out: dates.checkOut, guests },
    { enabled: ready },
  )

  const canBook = isAuthenticated ? role === 'guest' : true
  const available = Boolean(quote?.available)

  const reserve = () => {
    const qs = new URLSearchParams({
      property: String(property.id),
      check_in: dates.checkIn,
      check_out: dates.checkOut,
      guests: String(guests),
    })
    navigate(`/checkout?${qs.toString()}`)
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-lg">
      <div className="flex items-end justify-between">
        <p>
          <span className="text-2xl font-bold">{formatINR(property.price_per_night)}</span>
          <span className="text-slate-500"> / night</span>
        </p>
        <StarRating rating={property.average_rating} count={property.review_count} />
      </div>

      <div className="mt-4 space-y-3">
        <DateRangeInput checkIn={dates.checkIn} checkOut={dates.checkOut} onChange={setDates} idPrefix="book" />
        <GuestSelector value={guests} onChange={setGuests} max={property.max_guests} />
      </div>

      <div className="mt-4 space-y-3">
        {!ready && <p className="text-sm text-slate-500">Select your dates to see the total price.</p>}

        {ready && loading && (
          <p className="flex items-center gap-2 text-sm text-slate-500">
            <Spinner className="h-4 w-4" /> Checking availability...
          </p>
        )}

        {ready && error && <Alert message={error.message} />}

        {quote && !available && (
          <Alert
            message={
              quote.reasons?.length
                ? quote.reasons.join(' ')
                : 'These dates are not available. Try different dates.'
            }
          />
        )}

        {quote && available && (
          <div className="space-y-2 text-sm">
            <div className="flex justify-between text-slate-600">
              <span>
                {formatINR(quote.price_per_night)} × {quote.nights} {quote.nights === 1 ? 'night' : 'nights'}
              </span>
              <span>{formatINR(quote.total_price)}</span>
            </div>
            <div className="flex justify-between border-t border-slate-200 pt-2 text-base font-bold">
              <span>Total</span>
              <span>{formatINR(quote.total_price)}</span>
            </div>
          </div>
        )}

        {!canBook && <Alert type="info" message="Host and admin accounts cannot book stays. Use a guest account." />}

        <Button size="lg" className="w-full" disabled={!ready || !available || !canBook} onClick={reserve}>
          {isAuthenticated ? 'Reserve' : 'Log in to reserve'}
        </Button>

        <p className="text-center text-xs text-slate-500">
          You won&apos;t be charged yet. Payment opens after the host confirms your request.
        </p>
      </div>
    </div>
  )
}