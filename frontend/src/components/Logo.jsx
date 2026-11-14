import { Link } from 'react-router-dom'
import { FiHome } from 'react-icons/fi'

export default function Logo({ className = '' }) {
  return (
    <Link to="/" className={`inline-flex items-center gap-2 ${className}`}>
      <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white">
        <FiHome className="h-5 w-5" />
      </span>
      <span className="text-xl font-bold tracking-tight text-brand-700">StayNest</span>
    </Link>
  )
}