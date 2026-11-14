import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { FiAlertTriangle, FiArrowLeft } from 'react-icons/fi'
import Button from '../components/Button'
import Alert from '../components/Alert'
import EmptyState from '../components/EmptyState'
import Spinner from '../components/Spinner'
import useApi from '../hooks/useApi'
import useToast from '../hooks/useToast'
import { createBooking } from '../api/bookings'
import { normalizeApiError } from '../utils/apiError'
import { errorText } from '../utils/errors'
import { formatDate, formatINR } from '../utils/format'
import { mediaUrl } from '../utils/media'

export default function Checkout() {
  const [sp] = useSearchParams()
  const navigate = useNavigate()
  const toast = useToast()

  const propertyId = sp.get('property')
  const checkIn = sp.get('check_in')
  const checkOut = sp.get('check_out')
  const guests = Number(sp.get('guests')) || 1
  const valid = Boolean(propertyId && checkIn && checkOut)

  const { data: property, loading: propLoading, error: propError } = useApi(`/properties/${propertyId}/`, {}, { enabled: valid })
  const {
    data: quote,
    loading: quoteLoading,
    error: quoteError,
  } = useApi('/bookings/quote/', { property: propertyId, check_in: checkIn, check_out: checkOut, guests }, { enabled: valid })

  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState('')

  if (!valid) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16">
        <EmptyState Icon={FiAlertTriangle} title="Booking details missing" text="Pick a property and dates first.">
          <Link to="/properties"><Button>Browse stays</Button></Link>
        </EmptyState>
      </div>
    )
  }

  const backUrl = `/properties/${propertyId}?${new URLSearchParams({ check_in: checkIn, check_out: checkOut, guests: String(guests) })}`

  if (propLoading || quoteLoading) {
    return (
      <div className="flex justify-center py-24 text-brand-600">
        <Spinner className="h-8 w-8" />
      </div>
    )
  }

  const loadError = propError || quoteError
  if (loadError) {
    return (
      <div className="mx-auto max-w-2xl space-y-3 px-4 py-16">
        <Alert message={loadError.message} />
        <Link to={backUrl}><Button variant="secondary">Back to property</Button></Link>
      </div>
    )
  }

  const available = Boolean(quote?.available)
  const img = mediaUrl(property.cover_image) ?? mediaUrl(property.images?.[0])

  const submit = async () => {
    setSubmitting(true)
    setFormError('')
    try {
      await createBooking({
        property: Number(propertyId),
        check_in: checkIn,
        check_out: checkOut,
        num_guests: guests,
      })
      toast.success('Request sent! You can pay once the host confirms.')
      navigate('/bookings', { replace: true })
    } catch (err) {
      setFormError(errorText(normalizeApiError(err)))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <Link to={backUrl} className="inline-flex items-center gap-1 text-sm text-slate-600 hover:underline">
        <FiArrowLeft /> Back to property
      </Link>
      <h1 className="mt-3 text-2xl font-bold">Confirm your request</h1>

      <div className="mt-6 grid gap-8 lg:grid-cols-[1fr_22rem]">
        <div className="space-y-6">
          <section className="rounded-2xl border border-slate-200 p-5">
            <h2 className="font-semibold">Your trip</h2>
            <dl className="mt-3 space-y-2 text-sm">
              <div className="flex justify-between"><dt className="text-slate-500">Check-in</dt><dd>{formatDate(checkIn)} (from 2:00 PM)</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Check-out</dt><dd>{formatDate(checkOut)}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Guests</dt><dd>{guests}</dd></div>
            </dl>
          </section>

          <section className="rounded-2xl border border-slate-200 p-5">
            <h2 className="font-semibold">How it works</h2>
            <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-slate-600">
              <li>Aap request bhejte hain. Abhi koi payment nahi hoti.</li>
              <li>Host request confirm ya reject karta hai.</li>
              <li>Confirm hone par My bookings se payment karein.</li>
            </ol>
          </section>

          <section className="rounded-2xl border border-slate-200 p-5">
            <h2 className="font-semibold">Cancellation policy</h2>
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-600">
              <li>Pending request cancel karne par 100% refund</li>
              <li>Confirmed booking: check-in se 48+ ghante pehle 100%</li>
              <li>24 se 48 ghante pehle 50%</li>
              <li>24 ghante se kam 0%</li>
            </ul>
          </section>
        </div>

        <aside>
          <div className="rounded-2xl border border-slate-200 p-5 shadow-lg lg:sticky lg:top-24">
            <div className="flex gap-3">
              {img && <img src={img} alt="" className="h-20 w-24 rounded-lg object-cover" />}
              <div>
                <p className="line-clamp-2 font-semibold">{property.title}</p>
                <p className="text-sm text-slate-500">{[property.city, property.state].filter(Boolean).join(', ')}</p>
              </div>
            </div>

            <div className="mt-4 space-y-2 border-t border-slate-200 pt-4 text-sm">
              {available ? (
                <>
                  <div className="flex justify-between text-slate-600">
                    <span>{formatINR(quote.price_per_night)} × {quote.nights} {quote.nights === 1 ? 'night' : 'nights'}</span>
                    <span>{formatINR(quote.total_price)}</span>
                  </div>
                  <div className="flex justify-between border-t border-slate-200 pt-2 text-base font-bold">
                    <span>Total</span>
                    <span>{formatINR(quote.total_price)}</span>
                  </div>
                </>
              ) : (
                <Alert message={quote?.reasons?.length ? quote.reasons.join(' ') : 'These dates are not available.'} />
              )}
            </div>

            <div className="mt-4 space-y-3">
              <Alert message={formError} />
              <Button size="lg" className="w-full" disabled={!available} loading={submitting} onClick={submit}>
                Request to book
              </Button>
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}