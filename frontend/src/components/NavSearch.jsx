import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FiSearch } from 'react-icons/fi'

// 10a mein sirf destination search. Dates + guests 10b mein add honge.
export default function NavSearch({ className = '' }) {
  const [destination, setDestination] = useState('')
  const navigate = useNavigate()

  const onSubmit = (e) => {
    e.preventDefault()
    const q = destination.trim()
    navigate(q ? `/search?destination=${encodeURIComponent(q)}` : '/properties')
  }

  return (
    <form
      onSubmit={onSubmit}
      role="search"
      className={`flex items-center rounded-full border border-slate-300 bg-white py-1 pl-4 pr-1 shadow-sm transition focus-within:shadow-md ${className}`}
    >
      <input
        type="text"
        value={destination}
        onChange={(e) => setDestination(e.target.value)}
        placeholder="Search destinations"
        aria-label="Search destinations"
        className="w-full min-w-0 bg-transparent text-sm outline-none placeholder:text-slate-500"
      />
      <button
        type="submit"
        aria-label="Search"
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-600 text-white hover:bg-brand-700"
      >
        <FiSearch className="h-4 w-4" />
      </button>
    </form>
  )
}