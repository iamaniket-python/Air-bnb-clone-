import { useState } from 'react'
import { Link } from 'react-router-dom'
import { FiHeart } from 'react-icons/fi'
import PropertyCard, { PropertyCardSkeleton } from '../components/PropertyCard'
import Pagination from '../components/Pagination'
import EmptyState from '../components/EmptyState'
import Alert from '../components/Alert'
import Button from '../components/Button'
import useApi from '../hooks/useApi'
import useWishlist from '../hooks/useWishlist'

const PAGE_SIZE = 12

export default function Wishlist() {
  const [page, setPage] = useState(1)
  const { data, loading, error, reload } = useApi('/wishlist/', { page, page_size: PAGE_SIZE })
  const { isSaved, loaded } = useWishlist()

  // Heart se unsave karte hi card hat jaata hai (context ke ids se filter)
  const items = (data?.results ?? []).filter((item) => !loaded || isSaved(item.property.id))

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-bold">Wishlist</h1>

      <div className="mt-6">
        {error ? (
          <div className="space-y-3">
            <Alert message={error.message} />
            <Button variant="secondary" onClick={reload}>Retry</Button>
          </div>
        ) : loading ? (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => <PropertyCardSkeleton key={i} />)}
          </div>
        ) : items.length === 0 ? (
          <EmptyState Icon={FiHeart} title="No saved stays yet" text="Tap the heart on any stay to save it here.">
            <Link to="/properties"><Button>Explore stays</Button></Link>
          </EmptyState>
        ) : (
          <>
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {items.map((item) => <PropertyCard key={item.id} property={item.property} />)}
            </div>
            <Pagination page={page} count={data.count} pageSize={PAGE_SIZE} onChange={setPage} />
          </>
        )}
      </div>
    </div>
  )
}