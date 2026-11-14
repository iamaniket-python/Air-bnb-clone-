import { Link, useParams, useSearchParams } from 'react-router-dom'
import { FiHome, FiMapPin } from 'react-icons/fi'
import ImageGallery from '../components/ImageGallery'
import BookingWidget from '../components/BookingWidget'
import ReviewList from '../components/ReviewList'
import AmenityIcon from '../components/AmenityIcon'
import StarRating from '../components/StarRating'
import HeartButton from '../components/HeartButton'
import EmptyState from '../components/EmptyState'
import Alert from '../components/Alert'
import Button from '../components/Button'
import useApi from '../hooks/useApi'
import { fullName, initials } from '../utils/format'
import { PROPERTY_TYPE_LABELS } from '../utils/constants'

function DetailsSkeleton() {
  return (
    <div className="mx-auto max-w-7xl animate-pulse px-4 py-8 sm:px-6 lg:px-8">
      <div className="h-8 w-1/2 rounded bg-slate-200" />
      <div className="mt-6 aspect-[16/7] rounded-2xl bg-slate-200" />
      <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_24rem]">
        <div className="space-y-3">
          <div className="h-5 w-1/3 rounded bg-slate-200" />
          <div className="h-4 w-full rounded bg-slate-200" />
          <div className="h-4 w-5/6 rounded bg-slate-200" />
        </div>
        <div className="h-72 rounded-2xl bg-slate-200" />
      </div>
    </div>
  )
}

export default function PropertyDetails() {
  const { id } = useParams()
  const [searchParams] = useSearchParams()
  const { data: property, loading, error, reload } = useApi(`/properties/${id}/`)

  if (loading) return <DetailsSkeleton />

  if (error) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16">
        {error.status === 404 ? (
          <EmptyState Icon={FiHome} title="Property not found" text="This listing does not exist or is no longer available.">
            <Link to="/properties"><Button>Browse stays</Button></Link>
          </EmptyState>
        ) : (
          <div className="space-y-3">
            <Alert message={error.message} />
            <Button variant="secondary" onClick={reload}>Retry</Button>
          </div>
        )}
      </div>
    )
  }

  const place = [property.city, property.state, property.country].filter(Boolean).join(', ')
  const stats = [
    `${property.max_guests} guests`,
    `${property.bedrooms} ${property.bedrooms === 1 ? 'bedroom' : 'bedrooms'}`,
    `${property.beds} ${property.beds === 1 ? 'bed' : 'beds'}`,
    `${property.bathrooms} ${Number(property.bathrooms) === 1 ? 'bathroom' : 'bathrooms'}`,
  ]

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold sm:text-3xl">{property.title}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-slate-600">
            <StarRating rating={property.average_rating} count={property.review_count} />
            <span className="inline-flex items-center gap-1"><FiMapPin /> {place}</span>
          </div>
        </div>
        <HeartButton propertyId={property.id} className="border border-slate-200" />
      </div>

      <div className="mt-6">
        <ImageGallery images={property.images} title={property.title} />
      </div>

      <div className="mt-8 grid gap-10 lg:grid-cols-[1fr_24rem]">
        <div className="space-y-8">
          <div className="border-b border-slate-200 pb-6">
            <h2 className="text-xl font-semibold">
              {PROPERTY_TYPE_LABELS[property.property_type] ?? property.property_type} in {property.city}
            </h2>
            <p className="mt-1 text-sm text-slate-600">{stats.join(' · ')}</p>

            {property.host && (
              <div className="mt-4 flex items-center gap-3">
                <span className="flex h-11 w-11 items-center justify-center rounded-full bg-brand-600 text-sm font-bold text-white">
                  {initials(property.host)}
                </span>
                <div>
                  <p className="text-sm font-semibold">Hosted by {fullName(property.host)}</p>
                </div>
              </div>
            )}
          </div>

          <div className="border-b border-slate-200 pb-6">
            <h2 className="text-xl font-semibold">About this place</h2>
            <p className="mt-3 whitespace-pre-line text-slate-700">{property.description}</p>
          </div>

          {property.amenities?.length > 0 && (
            <div className="border-b border-slate-200 pb-6">
              <h2 className="text-xl font-semibold">What this place offers</h2>
              <ul className="mt-4 grid gap-3 sm:grid-cols-2">
                {property.amenities.map((a) => (
                  <li key={a.id} className="flex items-center gap-3 text-sm text-slate-700">
                    <AmenityIcon name={a.icon} className="h-5 w-5 text-slate-500" />
                    {a.name}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="border-b border-slate-200 pb-6">
            <h2 className="text-xl font-semibold">Where you&apos;ll be</h2>
            <p className="mt-2 text-sm text-slate-700">
              {[property.address, property.city, property.state, property.postal_code].filter(Boolean).join(', ')}
            </p>
          </div>

          <div>
            <h2 className="mb-4 text-xl font-semibold">
              Reviews {property.review_count > 0 && <span className="text-slate-500">({property.review_count})</span>}
            </h2>
            <ReviewList propertyId={property.id} />
          </div>
        </div>

        <aside>
          <div className="lg:sticky lg:top-24">
            <BookingWidget
              key={property.id}
              property={property}
              initial={{
                checkIn: searchParams.get('check_in') ?? '',
                checkOut: searchParams.get('check_out') ?? '',
                guests: searchParams.get('guests') ?? 1,
              }}
            />
          </div>
        </aside>
      </div>
    </div>
  )
}