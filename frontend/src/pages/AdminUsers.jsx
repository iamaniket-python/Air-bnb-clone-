import { useState } from 'react'
import { FiUsers } from 'react-icons/fi'
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
import { setUserActive } from '../api/admin'
import { cleanParams } from '../utils/params'
import { formatDate, fullName } from '../utils/format'

const PAGE_SIZE = 15

const ROLE_OPTIONS = [
  { value: '', label: 'All roles' },
  { value: 'guest', label: 'Guest' },
  { value: 'host', label: 'Host' },
  { value: 'admin', label: 'Admin' },
]
const ACTIVE_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'true', label: 'Active' },
  { value: 'false', label: 'Inactive' },
]
const ORDER_OPTIONS = [
  { value: '-date_joined', label: 'Newest' },
  { value: 'date_joined', label: 'Oldest' },
  { value: 'username', label: 'Username A-Z' },
]

export default function AdminUsers() {
  const toast = useToast()
  const [search, setSearch] = useState('')
  const [role, setRole] = useState('')
  const [active, setActive] = useState('')
  const [ordering, setOrdering] = useState('-date_joined')
  const [page, setPage] = useState(1)
  const [target, setTarget] = useState(null)

  const debouncedSearch = useDebounce(search.trim(), 400)
  const params = cleanParams({ page, page_size: PAGE_SIZE, search: debouncedSearch, role, is_active: active, ordering })
  const { data, loading, error, reload } = useApi('/admin/users/', params)

  // Filter badalte hi page 1 par
  const withReset = (setter) => (value) => {
    setter(value)
    setPage(1)
  }

  const confirmToggle = async () => {
    await setUserActive(target.id, !target.is_active)
    toast.success(target.is_active ? 'User deactivated.' : 'User activated.')
    setTarget(null)
    reload()
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-bold">Users</h1>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <label htmlFor="user-search" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Search</label>
          <input
            id="user-search"
            type="search"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
            placeholder="Username, email, name"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-100"
          />
        </div>
        <FilterSelect id="user-role" label="Role" value={role} onChange={withReset(setRole)} options={ROLE_OPTIONS} />
        <FilterSelect id="user-active" label="Status" value={active} onChange={withReset(setActive)} options={ACTIVE_OPTIONS} />
        <FilterSelect id="user-order" label="Sort by" value={ordering} onChange={withReset(setOrdering)} options={ORDER_OPTIONS} />
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
          <EmptyState Icon={FiUsers} title="No users found" text="Try changing the filters." />
        ) : (
          <>
            <p className="mb-2 text-sm text-slate-500">{data.count} {data.count === 1 ? 'user' : 'users'}</p>
            <div className="overflow-x-auto rounded-2xl border border-slate-200">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-4 py-3">User</th>
                    <th className="px-4 py-3">Role</th>
                    <th className="px-4 py-3 text-right">Properties</th>
                    <th className="px-4 py-3 text-right">Bookings</th>
                    <th className="px-4 py-3">Joined</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.results.map((u) => (
                    <tr key={u.id}>
                      <td className="px-4 py-3">
                        <p className="font-medium">{fullName(u)}</p>
                        <p className="text-xs text-slate-500">@{u.username} · {u.email}</p>
                      </td>
                      <td className="px-4 py-3 capitalize">{u.role}</td>
                      <td className="px-4 py-3 text-right">{u.properties_count ?? 0}</td>
                      <td className="px-4 py-3 text-right">{u.bookings_count ?? 0}</td>
                      <td className="px-4 py-3 text-slate-600">{formatDate(u.date_joined)}</td>
                      <td className="px-4 py-3">
                        <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${u.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-700'}`}>
                          {u.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        {u.role === 'admin' ? (
                          <span className="text-xs text-slate-400">Protected</span>
                        ) : (
                          <Button
                            size="sm"
                            variant={u.is_active ? 'ghost' : 'secondary'}
                            className={u.is_active ? 'text-red-600 hover:bg-red-50' : ''}
                            onClick={() => setTarget(u)}
                          >
                            {u.is_active ? 'Deactivate' : 'Activate'}
                          </Button>
                        )}
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

      {target && (
        <ConfirmModal
          key={target.id}
          title={target.is_active ? 'Deactivate this user?' : 'Activate this user?'}
          description={
            target.is_active
              ? `@${target.username} login nahi kar paayega aur uske active sessions band ho jaayenge.`
              : `@${target.username} dobara login kar paayega.`
          }
          confirmLabel={target.is_active ? 'Deactivate' : 'Activate'}
          danger={target.is_active}
          onClose={() => setTarget(null)}
          onConfirm={confirmToggle}
        />
      )}
    </div>
  )
}