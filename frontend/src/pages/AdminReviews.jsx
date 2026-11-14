import { useState } from 'react'
import { Link } from 'react-router-dom'
import { FiMessageSquare, FiTrash2 } from 'react-icons/fi'
import FilterSelect from '../components/FilterSelect'
import ConfirmModal from '../components/ConfirmModal'
import Pagination from '../components/Pagination'
import EmptyState from '../components/EmptyState'
import Alert from '../components/Alert'
import Button from '../components/Button'
import Spinner from '../components/Spinner'
import { Stars } from '../components/StarRating'
import useApi from '../hooks/useApi'
import useToast from '../hooks/useToast'
import { deleteReview } from '../api/admin'
import { cleanParams } from '../utils/params'
import { formatDate, fullName } from '../utils/format'

const PAGE_SIZE = 10
const RATING_OPTIONS = [
  { value: '', label: 'All ratings' },
  { value: '5', label: '5 stars' },
  { value: '4', label: '4 stars' },
  { value: '3', label: '3 stars' },
  { value: '2', label: '2 stars' },
  { value: '1', label: '1 star' },
]

export default function AdminReviews() {
  const toast = useToast()
  const [rating, setRating] = useState('')
  const [page, setPage] = useState(1)
  const [target, setTarget] = useState(null)

  const params = cleanParams({ page, page_size: PAGE_SIZE, rating })
  const { data, loading, error, reload } = useApi('/reviews/', params)

  const confirmDelete = async () => {
    await deleteReview(target.id)
    toast.success('Review deleted. Property rating updated.')
    setTarget(null)
    reload()
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-2xl font-bold">Reviews</h1>
        <div className="w-40">
          <FilterSelect
            id="review-rating"
            label="Rating"
            value={rating}
            onChange={(v) => { setRating(v); setPage(1) }}
            options={RATING_OPTIONS}
          />
        </div>
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
          <EmptyState Icon={FiMessageSquare} title="No reviews found" text="Reviews will show up here." />
        ) : (
          <>
            <p className="text-sm text-slate-500">{data.count} {data.count === 1 ? 'review' : 'reviews'}</p>
            {data.results.map((r) => (
              <div key={r.id} className="flex items-start justify-between gap-4 rounded-2xl border border-slate-200 p-4">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Stars value={r.rating} />
                    <Link to={`/properties/${r.property?.id}`} className="text-sm font-semibold hover:underline">
                      {r.property?.title}
                    </Link>
                  </div>
                  <p className="text-xs text-slate-500">
                    By {fullName(r.reviewer)} · {formatDate(r.created_at)} · Booking #{r.booking}
                  </p>
                  <p className="text-sm text-slate-700">{r.comment || <span className="text-slate-400">No comment</span>}</p>
                </div>
                <Button size="sm" variant="ghost" className="shrink-0 text-red-600 hover:bg-red-50" onClick={() => setTarget(r)}>
                  <FiTrash2 /> Delete
                </Button>
              </div>
            ))}
            <Pagination page={page} count={data.count} pageSize={PAGE_SIZE} onChange={setPage} />
          </>
        )}
      </div>

      {target && (
        <ConfirmModal
          key={target.id}
          title="Delete this review?"
          description="Moderation ke liye review permanently delete hoga, aur property ki rating dobara calculate hogi. Guest dobara review nahi likh payega."
          confirmLabel="Delete review"
          danger
          onClose={() => setTarget(null)}
          onConfirm={confirmDelete}
        />
      )}
    </div>
  )
}