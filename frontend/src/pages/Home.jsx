import { Link, useNavigate } from 'react-router-dom'
import { FiHeart, FiHome, FiShield } from 'react-icons/fi'
import Button from '../components/Button'
import SearchBar from '../components/SearchBar'
import PropertyCard, { PropertyCardSkeleton } from '../components/PropertyCard'
import Alert from '../components/Alert'
import useApi from '../hooks/useApi'
import useAuth from '../hooks/useAuth'
import { PROPERTY_TYPES } from '../utils/constants'
import { buildSearchUrl } from '../utils/search'

const FEATURES = [
  { Icon: FiHome, title: 'Unique stays', text: 'Apartments, villas, cottages and more across India.' },
  { Icon: FiShield, title: 'Safe booking', text: 'Clear cancellation policy and secure payments.' },
  { Icon: FiHeart, title: 'Save favourites', text: 'Keep a wishlist of places you love.' },
]

export default function Home() {
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const { data, loading, error, reload } = useApi('/properties/', { ordering: '-average_rating', page_size: 8 })

  return (
    <div>
      <section className="bg-gradient-to-b from-brand-50 to-white">
        <div className="mx-auto max-w-5xl px-4 pb-16 pt-16 text-center sm:pt-24">
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Find your next <span className="text-brand-600">stay</span>
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-lg text-slate-600">
            Search homes, villas and getaways. Book in minutes, or become a host and earn from your space.
          </p>

          <SearchBar className="mx-auto mt-10 text-left" onSearch={(values) => navigate(buildSearchUrl(values))} />

          {!isAuthenticated && (
            <div className="mt-6">
              <Link to="/register">
                <Button variant="secondary">Become a host</Button>
              </Link>
            </div>
          )}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="flex items-end justify-between">
          <h2 className="text-2xl font-bold">Top rated stays</h2>
          <Link to="/properties" className="text-sm font-semibold text-brand-700 hover:underline">
            View all
          </Link>
        </div>

        {error ? (
          <div className="mt-6 space-y-3">
            <Alert message={error.message} />
            <Button variant="secondary" onClick={reload}>Retry</Button>
          </div>
        ) : (
          <div className="mt-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {loading && Array.from({ length: 4 }).map((_, i) => <PropertyCardSkeleton key={i} />)}
            {data?.results?.map((p) => <PropertyCard key={p.id} property={p} />)}
          </div>
        )}

        {data && data.results.length === 0 && (
          <p className="mt-6 text-sm text-slate-500">No properties listed yet. Check back soon!</p>
        )}
      </section>

      <section className="mx-auto max-w-7xl px-4 pb-12 sm:px-6 lg:px-8">
        <h2 className="text-2xl font-bold">Browse by type</h2>
        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
          {PROPERTY_TYPES.map((t) => (
            <Link
              key={t.value}
              to={`/properties?property_type=${t.value}`}
              className="rounded-xl border border-slate-200 px-4 py-5 text-center text-sm font-semibold transition hover:border-brand-600 hover:bg-brand-50"
            >
              {t.label}
            </Link>
          ))}
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-6 px-4 pb-16 sm:grid-cols-3 sm:px-6">
        {FEATURES.map(({ Icon, title, text }) => (
          <div key={title} className="rounded-2xl border border-slate-200 p-6">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
              <Icon className="h-5 w-5" />
            </span>
            <h3 className="mt-4 font-semibold">{title}</h3>
            <p className="mt-1 text-sm text-slate-500">{text}</p>
          </div>
        ))}
      </section>
    </div>
  )
}