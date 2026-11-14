import { Link } from 'react-router-dom'
import { FiCalendar, FiClock, FiDollarSign, FiHome, FiPlusCircle, FiStar, FiTrendingUp } from 'react-icons/fi'
import StatCard from '../components/StatCard'
import EarningsChart from '../components/EarningsChart'
import StatusBadge from '../components/StatusBadge'
import Alert from '../components/Alert'
import Button from '../components/Button'
import Spinner from '../components/Spinner'
import useApi from '../hooks/useApi'
import { formatDate, formatINR, fullName } from '../utils/format'
import useAuth from '../hooks/useAuth'

export default function HostDashboard() {
  const { user } = useAuth()
  const { data, loading, error, reload } = useApi('/host/dashboard/')

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Host dashboard</h1>
          <p className="text-sm text-slate-500">Welcome back, {fullName(user)}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/host/reservations"><Button variant="secondary" size="sm"><FiCalendar /> Reservations</Button></Link>
          <Link to="/host/properties"><Button variant="secondary" size="sm"><FiHome /> My properties</Button></Link>
          <Link to="/host/properties/new"><Button size="sm"><FiPlusCircle /> Add property</Button></Link>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-24 text-brand-600"><Spinner className="h-8 w-8" /></div>
      ) : error ? (
        <div className="mt-6 space-y-3">
          <Alert message={error.message} />
          <Button variant="secondary" onClick={reload}>Retry</Button>
        </div>
      ) : (
        <>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Total earnings" value={formatINR(data.earnings.total)} Icon={FiDollarSign} hint="After refunds" />
            <StatCard label="This month" value={formatINR(data.earnings.this_month)} Icon={FiTrendingUp} />
            <StatCard
              label="Pending requests"
              value={data.bookings.pending_requests}
              Icon={FiClock}
              hint={data.bookings.pending_requests > 0 ? 'Waiting for your response' : 'All caught up'}
            />
            <StatCard label="Upcoming reservations" value={data.bookings.upcoming_reservations} Icon={FiCalendar} />
            <StatCard
              label="Properties"
              value={data.properties.total}
              Icon={FiHome}
              hint={`${data.properties.active} active · ${data.properties.inactive} inactive`}
            />
            <StatCard
              label="Reviews"
              value={data.reviews.count > 0 ? `${Number(data.reviews.average_rating).toFixed(1)} ★` : '—'}
              Icon={FiStar}
              hint={`${data.reviews.count} ${data.reviews.count === 1 ? 'review' : 'reviews'}`}
            />
            <StatCard label="Total bookings" value={data.bookings.total} Icon={FiCalendar} />
            <StatCard label="Completed stays" value={data.bookings.by_status?.completed ?? 0} Icon={FiHome} />
          </div>

          <div className="mt-8 grid gap-6 lg:grid-cols-[1.4fr_1fr]">
            <section className="rounded-2xl border border-slate-200 p-5">
              <h2 className="font-semibold">Earnings (last 6 months)</h2>
              <div className="mt-5">
                <EarningsChart data={data.earnings.monthly} />
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200 p-5">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold">Next reservations</h2>
                <Link to="/host/reservations" className="text-sm font-semibold text-brand-700 hover:underline">View all</Link>
              </div>
              {data.next_reservations.length === 0 ? (
                <p className="mt-4 text-sm text-slate-500">No upcoming reservations.</p>
              ) : (
                <ul className="mt-4 divide-y divide-slate-100">
                  {data.next_reservations.map((r) => (
                    <li key={r.id} className="py-3 text-sm">
                      <div className="flex items-center justify-between gap-2">
                        <p className="line-clamp-1 font-medium">{r.property?.title}</p>
                        <StatusBadge status={r.status} />
                      </div>
                      <p className="text-slate-500">
                        {r.guest} · {r.num_guests} {r.num_guests === 1 ? 'guest' : 'guests'}
                      </p>
                      <p className="text-slate-500">
                        {formatDate(r.check_in)} → {formatDate(r.check_out)} · {formatINR(r.total_price)}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </>
      )}
    </div>
  )
}