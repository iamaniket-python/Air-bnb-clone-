import { forwardRef, useState } from 'react'
import { FiEye, FiEyeOff } from 'react-icons/fi'

// react-hook-form ke register() ke saath kaam karta hai (ref forward hota hai)
const FormField = forwardRef(function FormField(
  { label, id, error, hint, type = 'text', className = '', ...inputProps },
  ref,
) {
  const [show, setShow] = useState(false)
  const isPassword = type === 'password'
  const inputType = isPassword && show ? 'text' : type

  return (
    <div className={className}>
      {label && (
        <label htmlFor={id} className="mb-1 block text-sm font-medium text-slate-700">
          {label}
        </label>
      )}
      <div className="relative">
        <input
          id={id}
          ref={ref}
          type={inputType}
          aria-invalid={error ? 'true' : 'false'}
          className={`w-full rounded-lg border px-3 py-2.5 text-sm outline-none transition placeholder:text-slate-400 focus:ring-2 ${
            error
              ? 'border-red-400 focus:border-red-500 focus:ring-red-100'
              : 'border-slate-300 focus:border-brand-600 focus:ring-brand-100'
          } ${isPassword ? 'pr-10' : ''}`}
          {...inputProps}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShow((s) => !s)}
            aria-label={show ? 'Hide password' : 'Show password'}
            className="absolute inset-y-0 right-0 flex items-center px-3 text-slate-500 hover:text-slate-700"
          >
            {show ? <FiEyeOff /> : <FiEye />}
          </button>
        )}
      </div>
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
      {!error && hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  )
})

export default FormField