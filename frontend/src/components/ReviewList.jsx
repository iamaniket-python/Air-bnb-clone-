import { useState } from 'react'
import { FiMessageSquare } from 'react-icons/fi'
import Pagination from './Pagination'
import Spinner from './Spinner'
import Alert from './Alert'
import { Stars } from './StarRating'
import useApi from '../hooks/useApi'
import { formatDate, fullName, initials } from '../utils/format'

const PAGE_SIZE = 6

export default function ReviewList({ propertyId }) {
  const [page, setPage] = useState(1)
  const { data, loading, error } = useApi(`/properties/${propertyId}/reviews/`, { page, page_size: PAGE_SIZE })

  if (error) return <Alert message={error.message} />

  if (loading && !data) {
    return (
      <p className="flex items-center gap-2 text-sm text-slate-500">
        <Spinner className="h-4 w-4" /> Loading reviews...
      </p>
    )
  }

  if (!data || data.count === 0) {
    return (
      <p className="flex items-center gap-2 text-sm text-slate-500">
        <FiMessageSquare /> No reviews yet.
      </p>
    )
  }

  return (
    <div>
      <ul className="grid gap-6 md:grid-cols-2">
        {data.results.map((r) => (
          <li key={r.id}>
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-100 text-sm font-bold text-brand-700">
                {initials(r.reviewer)}
              </span>
              <div>
                <p className="text-sm font-semibold">{fullName(r.reviewer)}</p>
                <p className="text-xs text-slate-500">{formatDate(r.created_at)}</p>
              </div>
            </div>
            <div className="mt-2">
              <Stars value={r.rating} />
            </div>
            {r.comment && <p className="mt-2 text-sm text-slate-700">{r.comment}</p>}
          </li>
        ))}
      </ul>
      <Pagination page={page} count={data.count} pageSize={PAGE_SIZE} onChange={setPage} />
    </div>
  )
}