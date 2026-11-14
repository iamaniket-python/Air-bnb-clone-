// data: {key: number} ya {key: {count: number}}. Horizontal bars, koi chart library nahi.
function toCount(v) {
  if (v && typeof v === 'object') return Number(v.count ?? 0)
  return Number(v) || 0
}

export default function BreakdownBars({ data = {}, labels = {} }) {
  const entries = Object.entries(data).map(([key, v]) => [key, toCount(v)])
  const max = Math.max(...entries.map(([, n]) => n), 0)

  if (entries.length === 0) return <p className="text-sm text-slate-500">No data.</p>

  return (
    <ul className="space-y-3">
      {entries.map(([key, n]) => (
        <li key={key}>
          <div className="mb-1 flex justify-between text-sm">
            <span className="capitalize text-slate-700">{labels[key] ?? key.replace(/_/g, ' ')}</span>
            <span className="font-semibold">{n}</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-brand-600 transition-all"
              style={{ width: `${max > 0 ? (n / max) * 100 : 0}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  )
}