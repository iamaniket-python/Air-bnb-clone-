import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { FiCheckCircle, FiInfo } from 'react-icons/fi'
import Button from '../components/Button'
import Alert from '../components/Alert'
import EmptyState from '../components/EmptyState'
import Spinner from '../components/Spinner'
import StatusBadge from '../components/StatusBadge'
import useApi from '../hooks/useApi'
import useToast from '../hooks/useToast'
import { createPayment, mockCheckout, verifyPayment } from '../api/payments'
import { normalizeApiError } from '../utils/apiError'
import { errorText } from '../utils/errors'
import { formatDate, formatINR } from '../utils/format'

export default function Payment() {
  const { bookingId } = useParams()
  const toast = useToast()

  const { data: booking, loading, error, reload } = useApi(`/bookings/${bookingId}/`)
  const { data: paidList, loading: paidLoading, reload: reloadPaid } = useApi('/payments/', {
    booking: bookingId,
    status: 'success',
  })

  const [processing, setProcessing] = useState(null) // 'success' | 'failure' | null
  const [payError, setPayError] = useState('')
  const [done, setDone] = useState(false)

  if (loading || paidLoading) {
    return (
      <div className="flex justify-center py-24 text-brand-600">
        <Spinner className="h-8 w-8" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="mx-auto max-w-2xl space-y-3 px-4 py-16">
        <Alert message={error.message} />
        <Button variant="secondary" onClick={reload}>Retry</Button>
      </div>
    )
  }

  const alreadyPaid = done || (paidList?.results?.length ?? 0) > 0

  // Mock flow: create -> mock-checkout -> verify (card details kabhi nahi jaati)
  const pay = async (outcome) => {
    setPayError('')
    setProcessing(outcome)
    try {
      const created = await createPayment(booking.id)
      const result = await mockCheckout({ transaction_id: created.payment.transaction_id, outcome })
      await verifyPayment({
        transaction_id: result.transaction_id,
        provider_payment_id: result.provider_payment_id,
        signature: result.signature,
      })
      setDone(true)
      toast.success('Payment successful!')
    } catch (err) {
      if (err.response?.status === 409) reloadPaid() // already paid
      const normalized = normalizeApiError(err)
      setPayError(
        err.response?.status === 402
          ? `Payment failed. ${errorText(normalized)} You can try again.`
          : errorText(normalized),
      )
    } finally {
      setProcessing(null)
    }
  }

  return (
    <div className="mx-auto max-w-xl px-4 py-10">
      <h1 className="text-2xl font-bold">Payment</h1>

      <div className="mt-6 space-y-2 rounded-2xl border border-slate-200 p-5 text-sm">
        <div className="flex items-center justify-between gap-2">
          <p className="font-semibold">{booking.property?.title}</p>
          <StatusBadge status={booking.status} />
        </div>
        <p className="text-slate-600">
          {formatDate(booking.check_in)} → {formatDate(booking.check_out)} · {booking.nights}{' '}
          {booking.nights === 1 ? 'night' : 'nights'}
        </p>
        <div className="flex justify-between border-t border-slate-200 pt-2 text-base font-bold">
          <span>Amount</span>
          <span>{formatINR(booking.total_price)}</span>
        </div>
      </div>

      <div className="mt-6">
        {alreadyPaid ? (
          <EmptyState Icon={FiCheckCircle} title="Payment complete" text="Your booking is paid. Have a great stay!">
            <Link to="/bookings"><Button>Go to my bookings</Button></Link>
          </EmptyState>
        ) : booking.status !== 'confirmed' ? (
          <div className="space-y-3">
            <Alert type="info" message="Payment is only available after the host confirms your booking." />
            <Link to="/bookings"><Button variant="secondary">Back to my bookings</Button></Link>
          </div>
        ) : (
          <div className="space-y-4">
            <Alert
              type="info"
              message="This is a demo payment. No real card or money is involved."
            />
            <Alert message={payError} />
            <div className="grid gap-3 sm:grid-cols-2">
              <Button size="lg" loading={processing === 'success'} disabled={processing !== null} onClick={() => pay('success')}>
                Pay (mock success)
              </Button>
              <Button size="lg" variant="secondary" loading={processing === 'failure'} disabled={processing !== null} onClick={() => pay('failure')}>
                Simulate failure
              </Button>
            </div>
            <p className="flex items-center gap-1 text-xs text-slate-500">
              <FiInfo /> Amount server decide karta hai, browser se nahi bheja jaata.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}