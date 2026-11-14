import { Link } from 'react-router-dom'
import { FiImage } from 'react-icons/fi'
import HeartButton from './HeartButton'
import StarRating from './StarRating'
import { formatINR } from '../utils/format'
import { mediaUrl } from '../utils/media'
import { PROPERTY_TYPE_LABELS } from '../utils/constants'

// linkSearch: dates/guests ko details page tak le jaane ke liye ("?check_in=..")
export default function PropertyCard({ property, linkSearch = '' }) {
  const img = mediaUrl(property.cover_image)
  const place = [property.city, property.state].filter(Boolean).join(', ')

  return (
    <Link to={`/properties/${property.id}${linkSearch}`} className="group block">
      <div className="relative aspect-[4/3] overflow-hidden rounded-2xl bg-slate-100">
        {img ? (
          <img
            src={img}
            alt={property.title}
            loading="lazy"
            className="h-full w-full object-cover transition duration-300 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-slate-300">
            <FiImage className="h-10 w-10" />
          </div>
        )}
        <HeartButton propertyId={property.id} className="absolute right-3 top-3" />
      </div>

      <div className="mt-3 space-y-0.5">
        <div className="flex items-start justify-between gap-2">
          <h3 className="line-clamp-1 font-semibold">{property.title}</h3>
          <StarRating rating={property.average_rating} count={property.review_count} className="shrink-0" />
        </div>
        <p className="line-clamp-1 text-sm text-slate-500">
          {PROPERTY_TYPE_LABELS[property.property_type] ?? property.property_type} · {place}
        </p>
        <p className="text-sm">
          <span className="font-semibold">{formatINR(property.price_per_night)}</span>
          <span className="text-slate-500"> / night</span>
        </p>
      </div>
    </Link>
  )
}

export function PropertyCardSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="aspect-[4/3] rounded-2xl bg-slate-200" />
      <div className="mt-3 space-y-2">
        <div className="h-4 w-3/4 rounded bg-slate-200" />
        <div className="h-3 w-1/2 rounded bg-slate-200" />
        <div className="h-3 w-1/3 rounded bg-slate-200" />
      </div>
    </div>
  )
}