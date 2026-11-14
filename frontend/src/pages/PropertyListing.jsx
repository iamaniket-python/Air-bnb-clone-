import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { FiHome, FiSliders } from 'react-icons/fi'
import SearchBar from '../components/SearchBar'
import FilterPanel from '../components/FilterPanel'
import PropertyCard, { PropertyCardSkeleton } from '../components/PropertyCard'
import Pagination from '../components/Pagination'
import EmptyState from '../components/EmptyState'
import Alert from '../components/Alert'
import Button from '../components/Button'
import useApi from '../hooks/useApi'
import { SORT_OPTIONS } from '../utils/constants'

const PAGE_SIZE = 12
const SINGLE_KEYS = ['destination', 'check_in', 'check_out', 'guests', 'min_price', 'max_price', 'min_rating', 'search', 'ordering']
const MULTI_KEYS = ['property_type', 'amenities']

// URL (source of truth) -> API params
function buildParams(sp) {
  const params = {}
  SINGLE_KEYS.forEach((k) => {
    const v = sp.get(k)
    if (v) params[k] = v
  })
  MULTI_KEYS.forEach((k) => {
    const v = sp.getAll(k)
    if (v.length) params[k] = v
  })
  // Backend ko check_in + check_out dono saath chahiye
  if (!(params.check_in && params.check_out)) {
    delete params.check_in
    delete params.check_out
  }
  params.page = Number(sp.get('page')) || 1
  params.page_size = PAGE_SIZE
  return params
}

export default function PropertyListing({ mode = 'listing' }) {
  const [searchParams, setSearchParams] = useSearchParams()
  const [showFilters, setShowFilters] = useState(false)

  const params = buildParams(searchParams)
  const { data, loading, error, reload } = useApi('/properties/', params)
  const { data: amenities } = useApi('/amenities/')

  // patch ke keys URL mein replace hote hain; page reset ho jaata hai
  const applyPatch = (patch) => {
    const next = new URLSearchParams(searchParams)
    Object.entries(patch).forEach(([key, value]) => {
      next.delete(key)
      if (Array.isArray(value)) value.forEach((v) => next.append(key, v))
      else if (value !== '' && value != null) next.set(key, String(value))
    })
    next.delete('page')
    setSearchParams(next)
  }

  const goToPage = (page) => {
    const next = new URLSearchParams(searchParams)
    next.set('page', String(page))
    setSearchParams(next)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const clearFilters = () => {
    const next = new URLSearchParams()
    ;['destination', 'check_in', 'check_out', 'guests'].forEach((k) => {
      const v = searchParams.get(k)
      if (v) next.set(k, v)
    })
    setSearchParams(next)
  }

  const destination = searchParams.get('destination')
  const title = destination ? `Stays in ${destination}` : mode === 'search' ? 'Search results' : 'Explore stays'

  // Details page tak dates/guests le jaao taaki booking widget pre-filled ho
  const carry = new URLSearchParams()
  ;['check_in', 'check_out', 'guests'].forEach((k) => {
    if (params[k]) carry.set(k, params[k])
  })
  const linkSearch = carry.toString() ? `?${carry.toString()}` : ''

  const filterInitial = {
    min_price: searchParams.get('min_price') ?? '',
    max_price: searchParams.get('max_price') ?? '',
    min_rating: searchParams.get('min_rating') ?? '',
    property_type: searchParams.getAll('property_type'),
    amenities: searchParams.getAll('amenities'),
  }

  const searchKey = ['destination', 'check_in', 'check_out', 'guests'].map((k) => searchParams.get(k) ?? '').join('|')

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <SearchBar
        key={searchKey}
        initial={{
          destination: searchParams.get('destination') ?? '',
          checkIn: searchParams.get('check_in') ?? '',
          checkOut: searchParams.get('check_out') ?? '',
          guests: searchParams.get('guests') ?? 1,
        }}
        onSearch={(v) => applyPatch({ destination: v.destination, check_in: v.check_in, check_out: v.check_out, guests: v.guests > 1 ? v.guests : '' })}
      />

      <div className="mt-8 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">{title}</h1>
          {data && <p className="text-sm text-slate-500">{data.count} {data.count === 1 ? 'stay' : 'stays'} found</p>}
        </div>

        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" className="lg:hidden" onClick={() => setShowFilters((s) => !s)}>
            <FiSliders /> Filters
          </Button>
          <select
            value={searchParams.get('ordering') ?? ''}
            onChange={(e) => applyPatch({ ordering: e.target.value })}
            aria-label="Sort by"
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-600"
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-6 grid gap-8 lg:grid-cols-[18rem_1fr]">
        <aside className={`${showFilters ? 'block' : 'hidden'} lg:block`}>
          <FilterPanel
            key={searchParams.toString()}
            initial={filterInitial}
            amenities={Array.isArray(amenities) ? amenities : []}
            onApply={(v) => {
              applyPatch(v)
              setShowFilters(false)
            }}
            onClear={clearFilters}
          />
        </aside>

        <section>
          {error ? (
            <div className="space-y-3">
              <Alert message={error.message} />
              <Button variant="secondary" onClick={reload}>Retry</Button>
            </div>
          ) : loading ? (
            <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => <PropertyCardSkeleton key={i} />)}
            </div>
          ) : data.results.length === 0 ? (
            <EmptyState Icon={FiHome} title="No stays found" text="Try changing your dates, destination or filters.">
              <Button variant="secondary" onClick={clearFilters}>Clear filters</Button>
            </EmptyState>
          ) : (
            <>
              <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
                {data.results.map((p) => <PropertyCard key={p.id} property={p} linkSearch={linkSearch} />)}
              </div>
              <Pagination page={params.page} count={data.count} pageSize={PAGE_SIZE} onChange={goToPage} />
            </>
          )}
        </section>
      </div>
    </div>
  )
}