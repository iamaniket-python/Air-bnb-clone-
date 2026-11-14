import { useState } from 'react'
import { useForm } from 'react-hook-form'
import FormField from './FormField'
import Button from './Button'
import Alert from './Alert'
import { applyFieldErrors, normalizeApiError } from '../utils/apiError'
import { PROPERTY_TYPES } from '../utils/constants'

const FIELDS = [
  'title', 'description', 'property_type', 'address', 'city', 'state', 'country', 'postal_code',
  'latitude', 'longitude', 'price_per_night', 'max_guests', 'bedrooms', 'beds', 'bathrooms', 'amenities', 'is_active',
]

const inputCls =
  'w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-100'

function Section({ title, children }) {
  return (
    <section className="space-y-4 rounded-2xl border border-slate-200 p-5">
      <h2 className="font-semibold">{title}</h2>
      {children}
    </section>
  )
}

const str = (v, fallback = '') => (v === null || v === undefined ? fallback : String(v))

// property = null => Add mode. amenities = [{id, name}] (sab available). onSubmit(payload) promise return kare.
export default function PropertyForm({ property, amenities = [], onSubmit, submitLabel, showActive = false }) {
  const [formError, setFormError] = useState('')

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm({
    defaultValues: {
      title: str(property?.title),
      description: str(property?.description),
      property_type: str(property?.property_type, 'apartment'),
      address: str(property?.address),
      city: str(property?.city),
      state: str(property?.state),
      country: str(property?.country, 'India'),
      postal_code: str(property?.postal_code),
      latitude: str(property?.latitude),
      longitude: str(property?.longitude),
      price_per_night: str(property?.price_per_night ? Number(property.price_per_night) : ''),
      max_guests: str(property?.max_guests, '2'),
      bedrooms: str(property?.bedrooms, '1'),
      beds: str(property?.beds, '1'),
      bathrooms: str(property?.bathrooms ? Number(property.bathrooms) : '', '1'),
      amenities: (property?.amenities ?? []).map((a) => String(a.id)),
      is_active: property?.is_active ?? true,
    },
  })

  const submit = async (v) => {
    setFormError('')
    const payload = {
      title: v.title.trim(),
      description: v.description.trim(),
      property_type: v.property_type,
      address: v.address.trim(),
      city: v.city.trim(),
      state: v.state.trim(),
      country: v.country.trim(),
      postal_code: v.postal_code.trim(),
      price_per_night: v.price_per_night,
      max_guests: Number(v.max_guests),
      bedrooms: Number(v.bedrooms),
      beds: Number(v.beds),
      bathrooms: v.bathrooms,
      amenities: (Array.isArray(v.amenities) ? v.amenities : []).map(Number),
    }
    // Optional: khali ho to bhejna hi nahi
    if (v.latitude !== '') payload.latitude = v.latitude
    if (v.longitude !== '') payload.longitude = v.longitude
    if (showActive) payload.is_active = Boolean(v.is_active)

    try {
      await onSubmit(payload)
    } catch (err) {
      const normalized = normalizeApiError(err)
      const extra = applyFieldErrors(setError, normalized.fieldErrors, FIELDS)
      setFormError(extra ? `${normalized.message} ${extra}` : normalized.message)
    }
  }

  const num = (label, name, rules = {}, extra = {}) => (
    <FormField
      id={name}
      type="number"
      label={label}
      error={errors[name]?.message}
      {...extra}
      {...register(name, { required: `${label} is required`, ...rules })}
    />
  )

  return (
    <form onSubmit={handleSubmit(submit)} noValidate className="space-y-6">
      <Alert message={formError} />

      <Section title="Basics">
        <FormField
          id="title"
          label="Title"
          error={errors.title?.message}
          {...register('title', { required: 'Title is required' })}
        />
        <div>
          <label htmlFor="description" className="mb-1 block text-sm font-medium text-slate-700">Description</label>
          <textarea
            id="description"
            rows={5}
            className={inputCls}
            {...register('description', { required: 'Description is required' })}
          />
          {errors.description && <p className="mt-1 text-xs text-red-600">{errors.description.message}</p>}
        </div>
        <div>
          <label htmlFor="property_type" className="mb-1 block text-sm font-medium text-slate-700">Property type</label>
          <select id="property_type" className={inputCls} {...register('property_type', { required: true })}>
            {PROPERTY_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
          {errors.property_type && <p className="mt-1 text-xs text-red-600">{errors.property_type.message}</p>}
        </div>
      </Section>

      <Section title="Location">
        <FormField id="address" label="Address" error={errors.address?.message} {...register('address', { required: 'Address is required' })} />
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField id="city" label="City" error={errors.city?.message} {...register('city', { required: 'City is required' })} />
          <FormField id="state" label="State" error={errors.state?.message} {...register('state', { required: 'State is required' })} />
          <FormField id="country" label="Country" error={errors.country?.message} {...register('country', { required: 'Country is required' })} />
          <FormField id="postal_code" label="Postal code" error={errors.postal_code?.message} {...register('postal_code', { required: 'Postal code is required' })} />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            id="latitude"
            type="number"
            step="any"
            label="Latitude (optional)"
            error={errors.latitude?.message}
            {...register('latitude', {
              validate: (x) => x === '' || (Number(x) >= -90 && Number(x) <= 90) || 'Latitude must be between -90 and 90',
            })}
          />
          <FormField
            id="longitude"
            type="number"
            step="any"
            label="Longitude (optional)"
            error={errors.longitude?.message}
            {...register('longitude', {
              validate: (x) => x === '' || (Number(x) >= -180 && Number(x) <= 180) || 'Longitude must be between -180 and 180',
            })}
          />
        </div>
      </Section>

      <Section title="Pricing and capacity">
        <div className="grid gap-4 sm:grid-cols-2">
          {num('Price per night (₹)', 'price_per_night', { min: { value: 1, message: 'Price must be at least 1' } }, { step: '0.01' })}
          {num('Max guests', 'max_guests', { min: { value: 1, message: 'At least 1 guest' } })}
          {num('Bedrooms', 'bedrooms', { min: { value: 0, message: 'Cannot be negative' } })}
          {num('Beds', 'beds', { min: { value: 1, message: 'At least 1 bed' } })}
          {num('Bathrooms', 'bathrooms', { min: { value: 0.5, message: 'At least 0.5' } }, { step: '0.5' })}
        </div>
      </Section>

      {amenities.length > 0 && (
        <Section title="Amenities">
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {amenities.map((a) => (
              <label key={a.id} className="flex cursor-pointer items-center gap-2 text-sm">
                <input type="checkbox" value={String(a.id)} className="h-4 w-4 accent-brand-600" {...register('amenities')} />
                {a.name}
              </label>
            ))}
          </div>
          {errors.amenities && <p className="text-xs text-red-600">{errors.amenities.message}</p>}
        </Section>
      )}

      {showActive && (
        <Section title="Visibility">
          <label className="flex cursor-pointer items-center gap-2 text-sm">
            <input type="checkbox" className="h-4 w-4 accent-brand-600" {...register('is_active')} />
            Listing is active (visible to guests)
          </label>
        </Section>
      )}

      <Button type="submit" size="lg" loading={isSubmitting}>{submitLabel}</Button>
    </form>
  )
}