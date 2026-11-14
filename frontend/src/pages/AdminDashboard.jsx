import { FiCalendar, FiDollarSign, FiHome, FiStar, FiUserPlus, FiUsers } from 'react-icons/fi'
import StatCard from '../components/StatCard'
import BreakdownBars from '../components/BreakdownBars'
import Alert from '../components/Alert'
import Button from '../components/Button'
import Spinner from '../components/Spinner'
import useApi from '../hooks/useApi'
import { formatINR } from '../utils/format'

function Panel({ title, children }) {
  return (
    <section className="rounded-2xl border border-slate-200 p-5">
      <h2 className="mb-4 font-semibold">{title}</h2>
      {children}
    </section>
  )
}

export default function AdminDashboard() {
  const { data, loading, error, reload } = useApi('/admin/dashboard/')

  if (loading) {
    return <div className="flex justify-center py-24 text-brand-600"><Spinner className="h-8 w-8" /></div>
  }

  if (error) {
    return (
      <div className="mx-auto max-w-2xl space-y-3 px-4 py-16">
        <Alert message={error.message} />
        <Button variant="secondary" onClick={reload}>Retry</Button>
      </div>
    )
  }

  const { users, properties, bookings, reviews, payments } = data

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Admin dashboard</h1>
          {data.generated_at && (
            <p className="text-sm text-slate-500">Updated {new Date(data.generated_at).toLocaleString('en-IN')}</p>
          )}
        </div>
        <Button variant="secondary" size="sm" onClick={reload}>Refresh</Button>
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Users" value={users.total} Icon={FiUsers} hint={`${users.active} active · ${users.inactive} inactive`} />
        <StatCard label="New users (30 days)" value={users.new_last_30_days} Icon={FiUserPlus} />
        <StatCard label="Properties" value={properties.total} Icon={FiHome} hint={`${properties.active} active · ${properties.inactive} inactive`} />
        <StatCard label="Bookings" value={bookings.total} Icon={FiCalendar} hint={`${bookings.upcoming} upcoming · ${bookings.created_last_30_days} in 30 days`} />
        <StatCard label="Gross payments" value={formatINR(payments.gross)} Icon={FiDollarSign} />
        <StatCard label="Refunded" value={formatINR(payments.refunded)} Icon={FiDollarSign} />
        <StatCard label="Net revenue" value={formatINR(payments.net)} Icon={FiDollarSign} hint="Gross minus refunds" />
        <StatCard
          label="Reviews"
          value={reviews.count > 0 ? `${Number(reviews.average_rating).toFixed(1)} ★` : '—'}
          Icon={FiStar}
          hint={`${reviews.count} ${reviews.count === 1 ? 'review' : 'reviews'}`}
        />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <Panel title="Users by role"><BreakdownBars data={users.by_role} /></Panel>
        <Panel title="Bookings by status"><BreakdownBars data={bookings.by_status} /></Panel>
        <Panel title="Payments by status"><BreakdownBars data={payments.by_status} /></Panel>
      </div>
    </div>
  )
}