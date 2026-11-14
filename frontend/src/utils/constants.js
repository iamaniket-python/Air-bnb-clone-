export const PROPERTY_TYPES = [
  { value: 'apartment', label: 'Apartment' },
  { value: 'house', label: 'House' },
  { value: 'villa', label: 'Villa' },
  { value: 'cottage', label: 'Cottage' },
  { value: 'guest_house', label: 'Guest house' },
  { value: 'hotel', label: 'Hotel' },
  { value: 'resort', label: 'Resort' },
]

export const PROPERTY_TYPE_LABELS = Object.fromEntries(PROPERTY_TYPES.map((t) => [t.value, t.label]))

export const SORT_OPTIONS = [
  { value: '', label: 'Recommended' },
  { value: 'price_per_night', label: 'Price: low to high' },
  { value: '-price_per_night', label: 'Price: high to low' },
  { value: '-average_rating', label: 'Top rated' },
  { value: '-created_at', label: 'Newest' },
]

export const RATING_OPTIONS = [
  { value: '', label: 'Any rating' },
  { value: '3', label: '3+ stars' },
  { value: '4', label: '4+ stars' },
  { value: '4.5', label: '4.5+ stars' },
]

export const MAX_GUESTS_SEARCH = 16
export const MAX_ADVANCE_DAYS = 365