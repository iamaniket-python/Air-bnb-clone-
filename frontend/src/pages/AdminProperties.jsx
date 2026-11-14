import { useState } from 'react'
import { Link } from 'react-router-dom'
import { FiHome } from 'react-icons/fi'
import FilterSelect from '../components/FilterSelect'
import ConfirmModal from '../components/ConfirmModal'
import Pagination from '../components/Pagination'
import EmptyState from '../components/EmptyState'
import Alert from '../components/Alert'
import Button from '../components/Button'
import Spinner from '../components/Spinner'
import useApi from '../hooks/useApi'
import useDebounce from '../hooks/useDebounce'
import useToast from '../hooks/useToast'
import { setPropertyActive } from '../api/admin'
import { deleteProperty } from '../api/properties'
import { cleanParams } from '../utils/params'
import { formatINR, fullName } from '../utils/format'
import { PROPERTY_TYPES, PROPERTY_TYPE_LABELS } from '../utils/constants'

const PAGE_SIZE = 15

const ACTIVE_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'true', label: 'Active' },
  { value: 'false', label: 'Inactive' },
]
const TYPE_OPTIONS = [{ value: '', label: 'All types' }, ...PROPERTY_TYPES]
const ORDER_OPTIONS = [
  { value: '-created_at', label: 'Newest' },
  { value: 'created_at', label: 'Oldest' },
  { value: 'price_per_night', label: 'Price: low to high' },
  { value: '-price_per_night', label: 'Price: high to low' },
]

// host object, string ya sirf id ho sakta hai
function hostLabel(host) {
  if (!host) return '—'
  if (typeof host === 'object') return fullName(host) || `#${host.id}`
  return typeof host === 'number' ? `#${host}` : String(host)
}

const inputCls =
  'w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-100'

export default function AdminProperties() {
  const toast = useToast()
  const [search, setSearch] = useState('')
  const [city, setCity] = useState('')
  const [active, setActive] = useState('')
  const [type, setType] = useState('')
  const [ordering, setOrdering] = useState('-created_at')
  const [page, setPage] = useState(1)
  const [modal, setModal] = useState(null) // {type: 'toggle' | 'delete', property}

  const debouncedSearch = useDebounce(search.trim(), 400)
  const debouncedCity = useDebounce(city.trim(), 400)
  const params = cleanParams({
    page,
    page_size: PAGE_SIZE,
    search: debouncedSearch,
    city: debouncedCity,
    is_active: active,
    property_type: type,
    ordering,
  })
  const { data, loading, error, reload } = useApi('/admin/properties/', params)

  const withReset = (setter) => (value) => {
    setter(value)
    setPage(1)
  }

  const confirm = async () => {
    const { type: kind, property } = modal
    if (kind === 'toggle') {
      await setPropertyActive(property.id, !property.is_active)
      toast.success(property.is_active ? 'Listing deactivated.' : 'Listing activated.')
    } else {
      // Upcoming booking ho to backend 400 deta hai, error modal mein dikhta hai
      await deleteProperty(property.id)
      toast.success('Property deleted.')
    }
    setModal(null)
    reload()
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-bold">Properties</h1>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <div>
          <label htmlFor="prop-search" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Search</label>
          <input id="prop-search" type="search" value={search} placeholder="Title, description"
            onChange={(e) => { setSearch(e.target.value); setPage(1) }} className={inputCls} />
        </div>
        <div>
          <label htmlFor="prop-city" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">City</label>
          <input id="prop-city" type="search" value={city} placeholder="e.g. Goa"
            onChange={(e) => { setCity(e.target.value); setPage(1) }} className={inputCls} />
        </div>
        <FilterSelect id="prop-active" label="Status" value={active} onChange={withReset(setActive)} options={ACTIVE_OPTIONS} />
        <FilterSelect id="prop-type" label="Type" value={type} onChange={withReset(setType)} options={TYPE_OPTIONS} />
        <FilterSelect id="prop-order" label="Sort by" value={ordering} onChange={withReset(setOrdering)} options={ORDER_OPTIONS} />
      </div>

      <div className="mt-6">
        {error ? (
          <div className="space-y-3">
            <Alert message={error.message} />
            <Button variant="secondary" onClick={reload}>Retry</Button>
          </div>
        ) : loading ? (
          <div className="flex justify-center py-16 text-brand-600"><Spinner className="h-8 w-8" /></div>
        ) : data.results.length === 0 ? (
          <EmptyState Icon={FiHome} title="No properties found" text="Try changing the filters." />
        ) : (
          <>
            <p className="mb-2 text-sm text-slate-500">{data.count} {data.count === 1 ? 'property' : 'properties'}</p>
            <div className="overflow-x-auto rounded-2xl border border-slate-200">
              <table className="w-full min-w-[800px] text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-4 py-3">Property</th>
                    <th className="px-4 py-3">Host</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3 text-right">Price</th>
                    <th className="px-4 py-3 text-right">Bookings</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.results.map((p) => (
                    <tr key={p.id}>
                      <td className="px-4 py-3">
                        <Link to={`/properties/${p.id}`} className="font-medium hover:underline">{p.title}</Link>
                        <p className="text-xs text-slate-500">{[p.city, p.state].filter(Boolean).join(', ')}</p>
                      </td>
                      <td className="px-4 py-3 text-slate-700">{hostLabel(p.host)}</td>
                      <td className="px-4 py-3 text-slate-600">{PROPERTY_TYPE_LABELS[p.property_type] ?? p.property_type}</td>
                      <td className="px-4 py-3 text-right">{formatINR(p.price_per_night)}</td>
                      <td className="px-4 py-3 text-right">{p.bookings_count ?? 0}</td>
                      <td className="px-4 py-3">
                        <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${p.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-700'}`}>
                          {p.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-1">
                          <Button size="sm" variant="ghost" onClick={() => setModal({ type: 'toggle', property: p })}>
                            {p.is_active ? 'Deactivate' : 'Activate'}
                          </Button>
                          <Button size="sm" variant="ghost" className="text-red-600 hover:bg-red-50" onClick={() => setModal({ type: 'delete', property: p })}>
                            Delete
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={page} count={data.count} pageSize={PAGE_SIZE} onChange={setPage} />
          </>
        )}
      </div>

      {modal && (
        <ConfirmModal
          key={`${modal.type}-${modal.property.id}`}
          title={
            modal.type === 'delete'
              ? 'Delete this property?'
              : modal.property.is_active
                ? 'Deactivate this listing?'
                : 'Activate this listing?'
          }
          description={
            modal.type === 'delete'
              ? `"${modal.property.title}" permanently delete hogi. Upcoming booking ho to delete nahi hoga.`
              : modal.property.is_active
                ? `"${modal.property.title}" guests ko dikhna band ho jaayegi.`
                : `"${modal.property.title}" guests ko dobara dikhegi.`
          }
          confirmLabel={modal.type === 'delete' ? 'Delete' : modal.property.is_active ? 'Deactivate' : 'Activate'}
          danger={modal.type === 'delete' || modal.property.is_active}
          onClose={() => setModal(null)}
          onConfirm={confirm}
        />
      )}
    </div>
  )
}