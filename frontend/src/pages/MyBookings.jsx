import { useState } from 'react'
import { Link } from 'react-router-dom'
import { FiCalendar } from 'react-icons/fi'
import BookingCard from '../components/BookingCard'
import CancelModal from '../components/CancelModal'
import ReviewModal from '../components/ReviewModal'
import Pagination from '../components/Pagination'
import EmptyState from '../components/EmptyState'
import Alert from '../components/Alert'
import Button from '../components/Button'
import Spinner from '../components/Spinner'
import useApi from '../hooks/useApi'

const PAGE_SIZE = 10
const TABS = [
  { key: 'all', label: 'All', status: [] },
  { key: 'pending', label: 'Pending', status: ['pending'] },
  { key: 'confirmed', label: 'Confirmed', status: ['confirmed'] },
  { key: 'completed', label: 'Completed', status: ['completed'] },
  { key: 'cancelled', label: 'Cancelled', status: ['cancelled', 'rejected'] },
]

export default function MyBookings() {
  const [tab, setTab] = useState('all')
  const [page, setPage] = useState(1)
  const [cancelTarget, setCancelTarget] = useState(null)
  const [reviewTarget, setReviewTarget] = useState(null)

  const statuses = TABS.find((t) => t.key === tab).status
  const params = { page, page_size: PAGE_SIZE, ordering: '-created_at' }
  if (statuses.length) params.status = statuses

  const { data, loading, error, reload } = useApi('/bookings/', params)
  const { data: payments } = useApi('/payments/', { status: 'success', page_size: 50 })
  const { data: reviews, reload: reloadReviews } = useApi('/reviews/', { page_size: 50 })

  const paidIds = new Set((payments?.results ?? []).map((p) => p.booking))
  const reviewedIds = new Set((reviews?.results ?? []).map((r) => r.booking))

  const changeTab = (key) => {
    setTab(key)
    setPage(1)
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-bold">My bookings</h1>

      <div className="mt-5 flex flex-wrap gap-2" role="tablist">
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

      <div className="mt-6 space-y-4">
        {error ? (
          <div className="space-y-3">
            <Alert message={error.message} />
            <Button variant="secondary" onClick={reload}>Retry</Button>
          </div>
        ) : loading ? (
          <div className="flex justify-center py-16 text-brand-600">
            <Spinner className="h-8 w-8" />
          </div>
        ) : data.results.length === 0 ? (
          <EmptyState Icon={FiCalendar} title="No bookings here" text="Your bookings will show up here.">
            <Link to="/properties"><Button>Find a stay</Button></Link>
          </EmptyState>
        ) : (
          <>
            {data.results.map((b) => (
              <BookingCard
                key={b.id}
                booking={b}
                paid={paidIds.has(b.id)}
                reviewed={reviewedIds.has(b.id)}
                onCancel={setCancelTarget}
                onReview={setReviewTarget}
              />
            ))}
            <Pagination page={page} count={data.count} pageSize={PAGE_SIZE} onChange={setPage} />
          </>
        )}
      </div>

      {cancelTarget && (
        <CancelModal
          key={cancelTarget.id}
          booking={cancelTarget}
          onClose={() => setCancelTarget(null)}
          onDone={() => {
            setCancelTarget(null)
            reload()
          }}
        />
      )}

      {reviewTarget && (
        <ReviewModal
          key={reviewTarget.id}
          booking={reviewTarget}
          onClose={() => setReviewTarget(null)}
          onDone={() => {
            setReviewTarget(null)
            reloadReviews()
          }}
        />
      )}
    </div>
  )
}