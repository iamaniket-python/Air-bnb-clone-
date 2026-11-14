import { useCallback, useRef, useState } from 'react'
import { FiChevronDown, FiMinus, FiPlus, FiUsers } from 'react-icons/fi'
import useClickOutside from '../hooks/useClickOutside'

export default function GuestSelector({ value, onChange, min = 1, max = 16, label = 'Guests', className = '' }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const close = useCallback(() => setOpen(false), [])
  useClickOutside(ref, close)

  const stepBtn =
    'flex h-8 w-8 items-center justify-center rounded-full border border-slate-300 text-slate-700 hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-40'

  return (
    <div className={`relative ${className}`} ref={ref}>
      <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</span>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between rounded-lg border border-slate-300 px-3 py-2.5 text-sm hover:border-slate-400"
      >
        <span className="flex items-center gap-2">
          <FiUsers className="h-4 w-4 text-slate-500" />
          {value} {value === 1 ? 'guest' : 'guests'}
        </span>
        <FiChevronDown className="h-4 w-4 text-slate-500" />
      </button>

      {open && (
        <div className="absolute z-30 mt-2 w-full min-w-56 rounded-xl border border-slate-200 bg-white p-4 shadow-xl">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Guests</p>
              <p className="text-xs text-slate-500">Max {max}</p>
            </div>
            <div className="flex items-center gap-3">
              <button type="button" className={stepBtn} disabled={value <= min} onClick={() => onChange(value - 1)} aria-label="Fewer guests">
                <FiMinus />
              </button>
              <span className="w-5 text-center text-sm font-semibold">{value}</span>
              <button type="button" className={stepBtn} disabled={value >= max} onClick={() => onChange(value + 1)} aria-label="More guests">
                <FiPlus />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}