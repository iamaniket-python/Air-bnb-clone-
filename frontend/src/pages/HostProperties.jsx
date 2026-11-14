import { useState } from 'react'
import { Link } from 'react-router-dom'
import { FiEdit2, FiHome, FiImage, FiPlusCircle, FiTrash2 } from 'react-icons/fi'
import Button from '../components/Button'
import Alert from '../components/Alert'
import EmptyState from '../components/EmptyState'
import Pagination from '../components/Pagination'
import Spinner from '../components/Spinner'
import useApi from '../hooks/useApi'
import useToast from '../hooks/useToast'
import { deleteProperty, updateProperty } from '../api/properties'
import { normalizeApiError } from '../utils/apiError'
import { errorText } from '../utils/errors'
import { formatINR } from '../utils/format'
import { mediaUrl } from '../utils/media'
import { PROPERTY_TYPE_LABELS } from '../utils/constants'

const PAGE_SIZE = 12

export default function HostProperties() {
  const toast = useToast()
  const [page, setPage] = useState(1)
  const [busyId, setBusyId] = useState(null)
  const { data, loading, error, reload } = useApi('/properties/my/', { page, page_size: PAGE_SIZE })

  // Paginated ya plain array, dono chalega
  const list = Array.isArray(data) ? data : data?.results ?? []
  const count = Array.isArray(data) ? data.length : data?.count ?? 0

  const toggleActive = async (p) => {
    setBusyId(p.id)
    try {
      await updateProperty(p.id, { is_active: !p.is_active })
      toast.success(p.is_active ? 'Listing deactivated.' : 'Listing activated.')
      reload()
    } catch (err) {
      toast.error(errorText(normalizeApiError(err)))
    } finally {
      setBusyId(null)
    }
  }

  const remove = async (p) => {
    if (!window.confirm(`Delete "${p.title}"? This cannot be undone.`)) return
    setBusyId(p.id)
    try {
      await deleteProperty(p.id)
      toast.success('Property deleted.')
      reload()
    } catch (err) {
      // Upcoming booking ho to backend 400 deta hai
      toast.error(errorText(normalizeApiError(err)))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">My properties</h1>
        <Link to="/host/properties/new"><Button size="sm"><FiPlusCircle /> Add property</Button></Link>
      </div>

      <div className="mt-6 space-y-4">
        {error ? (
          <div className="space-y-3">
            <Alert message={error.message} />
            <Button variant="secondary" onClick={reload}>Retry</Button>
          </div>
        ) : loading ? (
          <div className="flex justify-center py-16 text-brand-600"><Spinner className="h-8 w-8" /></div>
        ) : list.length === 0 ? (
          <EmptyState Icon={FiHome} title="No properties yet" text="List your first property and start hosting.">
            <Link to="/host/properties/new"><Button>Add property</Button></Link>
          </EmptyState>
        ) : (
          <>
            {list.map((p) => {
              const img = mediaUrl(p.cover_image)
              return (
                <div key={p.id} className="flex flex-col gap-4 rounded-2xl border border-slate-200 p-4 sm:flex-row sm:items-center">
                  <div className="h-28 w-full shrink-0 overflow-hidden rounded-xl bg-slate-100 sm:w-44">
                    {img ? (
                      <img src={img} alt={p.title} loading="lazy" className="h-full w-full object-cover" />
                    ) : (
                      <span className="flex h-full items-center justify-center text-slate-300"><FiImage className="h-8 w-8" /></span>
                    )}
                  </div>

                  <div className="flex-1 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Link to={`/properties/${p.id}`} className="font-semibold hover:underline">{p.title}</Link>
                      <span
                        className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                          p.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-700'
                        }`}
                      >
                        {p.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    <p className="text-sm text-slate-500">
                      {PROPERTY_TYPE_LABELS[p.property_type] ?? p.property_type} · {[p.city, p.state].filter(Boolean).join(', ')}
                    </p>
                    <p className="text-sm font-semibold">{formatINR(p.price_per_night)} <span className="font-normal text-slate-500">/ night</span></p>
                  </div>

                  <div className="flex flex-wrap gap-2 sm:flex-col">
                    <Link to={`/host/properties/${p.id}/edit`}>
                      <Button size="sm" variant="secondary" className="w-full"><FiEdit2 /> Edit</Button>
                    </Link>
                    <Button size="sm" variant="ghost" disabled={busyId === p.id} onClick={() => toggleActive(p)}>
                      {p.is_active ? 'Deactivate' : 'Activate'}
                    </Button>
                    <Button size="sm" variant="ghost" className="text-red-600 hover:bg-red-50" disabled={busyId === p.id} onClick={() => remove(p)}>
                      <FiTrash2 /> Delete
                    </Button>
                  </div>
                </div>
              )
            })}
            {!Array.isArray(data) && <Pagination page={page} count={count} pageSize={PAGE_SIZE} onChange={setPage} />}
          </>
        )}
      </div>
    </div>
  )
}