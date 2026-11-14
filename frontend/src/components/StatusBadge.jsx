const STATUS = {
  pending: { label: 'Pending', cls: 'bg-amber-100 text-amber-800' },
  confirmed: { label: 'Confirmed', cls: 'bg-emerald-100 text-emerald-800' },
  rejected: { label: 'Rejected', cls: 'bg-red-100 text-red-800' },
  cancelled: { label: 'Cancelled', cls: 'bg-slate-200 text-slate-700' },
  completed: { label: 'Completed', cls: 'bg-sky-100 text-sky-800' },
}

export default function StatusBadge({ status }) {
  const s = STATUS[status] ?? { label: status, cls: 'bg-slate-100 text-slate-700' }
  return <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${s.cls}`}>{s.label}</span>
}