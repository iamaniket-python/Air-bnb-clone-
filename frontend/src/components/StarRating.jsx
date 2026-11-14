import { FaStar } from 'react-icons/fa'

// Review nahi hain to "New" dikhata hai
export default function StarRating({ rating, count, className = '' }) {
  if (!count) {
    return <span className={`text-xs font-medium text-slate-500 ${className}`}>New</span>
  }
  return (
    <span className={`inline-flex items-center gap-1 text-sm ${className}`}>
      <FaStar className="h-3.5 w-3.5 text-amber-500" />
      <span className="font-semibold">{Number(rating).toFixed(1)}</span>
      <span className="text-slate-500">({count})</span>
    </span>
  )
}

// Review ke andar fixed stars (1-5)
export function Stars({ value }) {
  return (
    <span className="inline-flex" aria-label={`${value} out of 5`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <FaStar key={n} className={`h-3.5 w-3.5 ${n <= value ? 'text-amber-500' : 'text-slate-200'}`} />
      ))}
    </span>
  )
}