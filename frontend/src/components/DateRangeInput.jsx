import { addDaysISO, todayISO } from '../utils/dates'
import { MAX_ADVANCE_DAYS } from '../utils/constants'

const labelCls = 'mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500'
const inputCls =
  'w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-100'

// Native date inputs: mobile par best picker milta hai
export default function DateRangeInput({ checkIn, checkOut, onChange, idPrefix = 'dates', className = '' }) {
  const today = todayISO()
  const maxDate = addDaysISO(today, MAX_ADVANCE_DAYS)
  const minCheckOut = addDaysISO(checkIn || today, 1)

  const handleCheckIn = (value) => {
    // check-out check-in se pehle/barabar ho gaya to clear
    const nextOut = value && checkOut && checkOut <= value ? '' : checkOut
    onChange({ checkIn: value, checkOut: nextOut })
  }

  return (
    <div className={`grid grid-cols-2 gap-2 ${className}`}>
      <div>
        <label htmlFor={`${idPrefix}-in`} className={labelCls}>Check-in</label>
        <input
          id={`${idPrefix}-in`}
          type="date"
          value={checkIn}
          min={today}
          max={maxDate}
          onChange={(e) => handleCheckIn(e.target.value)}
          className={inputCls}
        />
      </div>
      <div>
        <label htmlFor={`${idPrefix}-out`} className={labelCls}>Check-out</label>
        <input
          id={`${idPrefix}-out`}
          type="date"
          value={checkOut}
          min={minCheckOut}
          max={addDaysISO(maxDate, 1)}
          onChange={(e) => onChange({ checkIn, checkOut: e.target.value })}
          className={inputCls}
        />
      </div>
    </div>
  )
}