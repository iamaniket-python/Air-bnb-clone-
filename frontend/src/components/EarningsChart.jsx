import { formatINR } from '../utils/format'

// "2026-05" -> "May"
function monthLabel(month) {
  const [y, m] = String(month).split('-').map(Number)
  if (!y || !m) return month
  return new Date(y, m - 1, 1).toLocaleString('en-IN', { month: 'short' })
}

// data: [{month: "YYYY-MM", amount: "1200.00"}] (6 points). Pure CSS bars, koi chart library nahi.
export default function EarningsChart({ data = [] }) {
  const values = data.map((d) => Number(d.amount) || 0)
  const max = Math.max(...values, 0)

  return (
    <div className="flex gap-3" role="img" aria-label="Monthly earnings for the last 6 months">
      {data.map((d, i) => {
        const pct = max > 0 ? (values[i] / max) * 100 : 0
        return (
          <div key={d.month} className="flex min-w-0 flex-1 flex-col items-center">
            <div className="flex h-40 w-full items-end">
              <div
                className="w-full rounded-t-md bg-brand-600 transition-all"
                style={{ height: `${values[i] > 0 ? Math.max(pct, 4) : 1}%`, opacity: values[i] > 0 ? 1 : 0.2 }}
                title={`${monthLabel(d.month)}: ${formatINR(values[i])}`}
              />
            </div>
            <p className="mt-2 w-full truncate text-center text-xs font-medium text-slate-700">
              {values[i] > 0 ? formatINR(values[i]) : '—'}
            </p>
            <p className="text-xs text-slate-500">{monthLabel(d.month)}</p>
          </div>
        )
      })}
    </div>
  )
}