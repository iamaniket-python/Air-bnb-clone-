import { FiChevronLeft, FiChevronRight } from 'react-icons/fi'
import Button from './Button'

export default function Pagination({ page, count, pageSize, onChange }) {
  const total = Math.max(1, Math.ceil(count / pageSize))
  if (total <= 1) return null

  return (
    <nav className="mt-8 flex items-center justify-center gap-3" aria-label="Pagination">
      <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        <FiChevronLeft /> Prev
      </Button>
      <span className="text-sm text-slate-600">
        Page {page} of {total}
      </span>
      <Button variant="secondary" size="sm" disabled={page >= total} onClick={() => onChange(page + 1)}>
        Next <FiChevronRight />
      </Button>
    </nav>
  )
}