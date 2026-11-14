import { useState } from 'react'
import Button from './Button'
import { PROPERTY_TYPES, RATING_OPTIONS } from '../utils/constants'

const inputCls =
  'w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-100'

// initial: {min_price, max_price, min_rating, property_type: [], amenities: []}
// Page isko key={searchParams} ke saath mount karta hai, isliye URL badle to draft reset hota hai
export default function FilterPanel({ initial, amenities = [], onApply, onClear }) {
  const [draft, setDraft] = useState(initial)
  const [error, setError] = useState('')

  const set = (key, value) => setDraft((d) => ({ ...d, [key]: value }))
  const toggleIn = (key, value) =>
    setDraft((d) => ({
      ...d,
      [key]: d[key].includes(value) ? d[key].filter((v) => v !== value) : [...d[key], value],
    }))

  const apply = () => {
    if (draft.min_price && draft.max_price && Number(draft.min_price) > Number(draft.max_price)) {
      setError('Min price cannot be greater than max price.')
      return
    }
    setError('')
    onApply(draft)
  }

  return (
    <div className="space-y-6 rounded-2xl border border-slate-200 p-5">
      <div>
        <h3 className="mb-2 text-sm font-semibold">Price per night (₹)</h3>
        <div className="grid grid-cols-2 gap-2">
          <input type="number" min="0" placeholder="Min" aria-label="Minimum price" value={draft.min_price} onChange={(e) => set('min_price', e.target.value)} className={inputCls} />
          <input type="number" min="0" placeholder="Max" aria-label="Maximum price" value={draft.max_price} onChange={(e) => set('max_price', e.target.value)} className={inputCls} />
        </div>
        {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold">Property type</h3>
        <div className="space-y-2">
          {PROPERTY_TYPES.map((t) => (
            <label key={t.value} className="flex cursor-pointer items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={draft.property_type.includes(t.value)}
                onChange={() => toggleIn('property_type', t.value)}
                className="h-4 w-4 accent-brand-600"
              />
              {t.label}
            </label>
          ))}
        </div>
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold">Minimum rating</h3>
        <select value={draft.min_rating} onChange={(e) => set('min_rating', e.target.value)} className={inputCls} aria-label="Minimum rating">
          {RATING_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {amenities.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-semibold">Amenities</h3>
          <div className="max-h-48 space-y-2 overflow-y-auto pr-1">
            {amenities.map((a) => (
              <label key={a.id} className="flex cursor-pointer items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={draft.amenities.includes(String(a.id))}
                  onChange={() => toggleIn('amenities', String(a.id))}
                  className="h-4 w-4 accent-brand-600"
                />
                {a.name}
              </label>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-2">
        <Button className="flex-1" onClick={apply}>Apply</Button>
        <Button variant="secondary" onClick={onClear}>Clear</Button>
      </div>
    </div>
  )
}