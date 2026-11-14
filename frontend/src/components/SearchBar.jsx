import { useState } from 'react'
import { FiMapPin, FiSearch } from 'react-icons/fi'
import DateRangeInput from './DateRangeInput'
import GuestSelector from './GuestSelector'
import Button from './Button'
import Alert from './Alert'
import useApi from '../hooks/useApi'
import useDebounce from '../hooks/useDebounce'
import { MAX_GUESTS_SEARCH } from '../utils/constants'

// Destinations API array of strings ya objects de sakti hai, dono chalenge
function toSuggestions(data) {
  const list = Array.isArray(data) ? data : data?.results ?? []
  const names = list
    .map((i) => (typeof i === 'string' ? i : i?.label ?? i?.name ?? i?.destination ?? i?.city ?? ''))
    .filter(Boolean)
  return [...new Set(names)].slice(0, 6)
}

// initial: {destination, checkIn, checkOut, guests}
// onSearch({destination, check_in, check_out, guests})
export default function SearchBar({ initial = {}, onSearch, className = '' }) {
  const [destination, setDestination] = useState(initial.destination ?? '')
  const [dates, setDates] = useState({ checkIn: initial.checkIn ?? '', checkOut: initial.checkOut ?? '' })
  const [guests, setGuests] = useState(Number(initial.guests) || 1)
  const [focused, setFocused] = useState(false)
  const [error, setError] = useState('')

  const debounced = useDebounce(destination.trim(), 300)
  const { data } = useApi('/properties/destinations/', { q: debounced }, { enabled: focused && debounced.length >= 2 })
  const suggestions = toSuggestions(data)

  const submit = (e) => {
    e.preventDefault()
    if (Boolean(dates.checkIn) !== Boolean(dates.checkOut)) {
      setError('Select both check-in and check-out dates, or clear both.')
      return
    }
    setError('')
    setFocused(false)
    onSearch({
      destination: destination.trim(),
      check_in: dates.checkIn,
      check_out: dates.checkOut,
      guests,
    })
  }

  return (
    <form onSubmit={submit} className={`rounded-2xl border border-slate-200 bg-white p-3 shadow-lg ${className}`}>
      {error && <Alert message={error} className="mb-3" />}
      <div className="grid gap-3 md:grid-cols-[1.3fr_1.7fr_1fr_auto] md:items-end">
        <div className="relative">
          <label htmlFor="search-destination" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
            Where
          </label>
          <div className="relative">
            <FiMapPin className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              id="search-destination"
              type="text"
              autoComplete="off"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              onFocus={() => setFocused(true)}
              onBlur={() => setFocused(false)}
              placeholder="City, state or area"
              className="w-full rounded-lg border border-slate-300 py-2.5 pl-9 pr-3 text-sm outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-100"
            />
          </div>
          {focused && suggestions.length > 0 && (
            <ul className="absolute z-30 mt-1 w-full overflow-hidden rounded-xl border border-slate-200 bg-white py-1 shadow-xl">
              {suggestions.map((s) => (
                <li key={s}>
                  <button
                    type="button"
                    // mousedown: blur se pehle chalta hai, warna list band ho jaati
                    onMouseDown={(e) => {
                      e.preventDefault()
                      setDestination(s)
                      setFocused(false)
                    }}
                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-slate-50"
                  >
                    <FiMapPin className="h-4 w-4 text-slate-400" />
                    {s}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <DateRangeInput checkIn={dates.checkIn} checkOut={dates.checkOut} onChange={setDates} idPrefix="search" />

        <GuestSelector value={guests} onChange={setGuests} max={MAX_GUESTS_SEARCH} />

        <Button type="submit" size="lg" className="w-full md:w-auto">
          <FiSearch className="h-4 w-4" />
          Search
        </Button>
      </div>
    </form>
  )
}