import { useState } from 'react'
import { FiCalendar } from 'react-icons/fi'
import StatusBadge from '../components/StatusBadge'
import ReasonModal from '../components/ReasonModal'
import Pagination from '../components/Pagination'
import EmptyState from '../components/EmptyState'
import Alert from '../components/Alert'
import Button from '../components/Button'
import Spinner from '../components/Spinner'
import useApi from '../hooks/useApi'
import useDebounce from '../hooks/useDebounce'
import useToast from '../hooks/useToast'
import { cancelBooking } from '../api/bookings'
import { updateBookingStatus } from '../api/hostBookings'
import { normalizeApiError } from '../utils/apiError'
import { errorText } from '../utils/errors'
import { cleanParams } from '../utils/params'
import { formatDate, formatINR, fullName } from '../utils/format'

const PAGE_SIZE = 12
const TABS = [
  { key: 'all', label: 'All', status: [] },
  { key: 'pending', label: 'Pending', status: ['pending'] },
  { key: 'confirmed', label: 'Confirmed', status: ['confirmed'] },
  { key: 'completed', label: 'Completed', status: ['completed'] },
  { key: 'cancelled', label: 'Cancelled / rejected', status: ['cancelled', 'rejected'] },
]

export default function AdminBookings() {
  const toast = useToast()
  const [tab, setTab] = useState('all')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [busyId, setBusyId] = useState(null)
  const [modal, setModal] = useState(null) // {type: 'reject' | 'cancel', booking}

  const debouncedSearch = useDebounce(search.trim(), 400)
  const statuses = TABS.find((t) => t.key === tab).status
  const params = cleanParams({ page, page_size: PAGE_SIZE, ordering: '-created_at', search: debouncedSearch })
  if (statuses.length) params.status = statuses

  const { data, loading, error, reload } = useApi('/bookings/', params)

  const changeTab = (key) => {
    setTab(key)
    setPage(1)
  }

  const quickStatus = async (booking, status, successMsg) => {
    setBusyId(booking.id)
    try {
      await updateBookingStatus(booking.id, status)
      toast.success(successMsg)
      reload()
    } catch (err) {
      toast.error(errorText(normalizeApiError(err)))
    } finally {
      setBusyId(null)
    }
  }

  const submitModal = async (reason) => {
    const { type, booking } = modal
    if (type === 'reject') await updateBookingStatus(booking.id, 'rejected', reason)
    else await cancelBooking(booking.id, reason)
    toast.success(type === 'reject' ? 'Request rejected.' : 'Booking cancelled. Refund processed as per policy.')
    setModal(null)
    reload()
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-bold">Bookings</h1>

      <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2" role="tablist">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              role="tab"
              aria-selected={tab === t.key}
              onClick={() => changeTab(t.key)}
              className={`rounded-full border px-4 py-1.5 text-sm font-medium transition ${
                tab === t.key ? 'border-brand-600 bg-brand-600 text-white' : 'border-slate-300 hover:bg-slate-50'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <input
          type="search"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
          placeholder="Search bookings"
          aria-label="Search bookings"
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-100 sm:w-64"
        />
      </div>

      <div className="mt-6 space-y-4">
        {error ? (
          <div className="space-y-3">
            <Alert message={error.message} />
            <Button variant="secondary" onClick={reload}>Retry</Button>
          </div>
        ) : loading ? (
          <div className="flex justify-center py-16 text-brand-600"><Spinner className="h-8 w-8" /></div>
        ) : data.results.length === 0 ? (
          <EmptyState Icon={FiCalendar} title="No bookings found" text="Try a different tab or search." />
        ) : (
          <>
            <p className="text-sm text-slate-500">{data.count} {data.count === 1 ? 'booking' : 'bookings'}</p>
            {data.results.map((b) => {
              const actions = b.available_actions ?? []
              const busy = busyId === b.id
              const host = b.property?.host
              return (
                <div key={b.id} className="flex flex-col gap-4 rounded-2xl border border-slate-200 p-4 sm:flex-row sm:items-center">
                  <div className="flex-1 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-semibold">{b.property?.title}</p>
                      <StatusBadge status={b.status} />
                      <span className="text-xs text-slate-400">#{b.id}</span>
                    </div>
                    <p className="text-sm text-slate-700">
                      Guest: {fullName(b.guest)}
                      {host && typeof host === 'object' ? ` · Host: ${fullName(host)}` : ''}
                    </p>
                    <p className="text-sm text-slate-600">
                      {formatDate(b.check_in)} → {formatDate(b.check_out)} · {b.nights} {b.nights === 1 ? 'night' : 'nights'} · {b.num_guests} {b.num_guests === 1 ? 'guest' : 'guests'}
                    </p>
                    <p className="text-sm font-semibold">{formatINR(b.total_price)}</p>
                    {b.cancellation_reason && <p className="text-xs text-slate-500">Reason: {b.cancellation_reason}</p>}
                  </div>

                  {actions.length > 0 && (
                    <div className="flex flex-wrap gap-2 sm:flex-col">
                      {actions.includes('confirm') && (
                        <Button size="sm" disabled={busy} onClick={() => quickStatus(b, 'confirmed', 'Booking confirmed.')}>Confirm</Button>
                      )}
                      {actions.includes('reject') && (
                        <Button size="sm" variant="secondary" disabled={busy} onClick={() => setModal({ type: 'reject', booking: b })}>Reject</Button>
                      )}
                      {actions.includes('complete') && (
                        <Button size="sm" variant="secondary" disabled={busy} onClick={() => quickStatus(b, 'completed', 'Marked as completed.')}>Mark completed</Button>
                      )}
                      {actions.includes('cancel') && (
                        <Button size="sm" variant="ghost" className="text-red-600 hover:bg-red-50" disabled={busy} onClick={() => setModal({ type: 'cancel', booking: b })}>Cancel</Button>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
            <Pagination page={page} count={data.count} pageSize={PAGE_SIZE} onChange={setPage} />
          </>
        )}
      </div>

      {modal && (
        <ReasonModal
          key={`${modal.type}-${modal.booking.id}`}
          title={modal.type === 'reject' ? 'Reject this request?' : 'Cancel this booking?'}
          description={
            modal.type === 'reject'
              ? 'Pending request reject hogi.'
              : 'Admin ke cancel karne par refund policy ke hisaab se process hota hai. Reason dena zaroori hai.'
          }
          required={modal.type === 'cancel'}
          danger
          confirmLabel={modal.type === 'reject' ? 'Reject request' : 'Cancel booking'}
          onClose={() => setModal(null)}
          onSubmit={submitModal}
        />
      )}
    </div>
  )
}