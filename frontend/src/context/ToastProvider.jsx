import { useCallback, useMemo, useState } from 'react'
import { FiAlertCircle, FiCheckCircle, FiInfo, FiX } from 'react-icons/fi'
import { ToastContext } from './ToastContext'

const STYLES = {
  success: { box: 'border-emerald-200 bg-emerald-50 text-emerald-800', Icon: FiCheckCircle },
  error: { box: 'border-red-200 bg-red-50 text-red-800', Icon: FiAlertCircle },
  info: { box: 'border-sky-200 bg-sky-50 text-sky-800', Icon: FiInfo },
}

export default function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const remove = useCallback((id) => {
    setToasts((list) => list.filter((t) => t.id !== id))
  }, [])

  const push = useCallback(
    (type, message, duration = 4000) => {
      const id = `${Date.now()}-${Math.random()}`
      setToasts((list) => [...list, { id, type, message }])
      setTimeout(() => remove(id), duration)
    },
    [remove],
  )

  const value = useMemo(
    () => ({
      success: (message) => push('success', message),
      error: (message) => push('error', message),
      info: (message) => push('info', message),
    }),
    [push],
  )

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed right-4 top-4 z-50 flex w-full max-w-sm flex-col gap-2">
        {toasts.map((t) => {
          const { box, Icon } = STYLES[t.type]
          return (
            <div
              key={t.id}
              role="status"
              className={`pointer-events-auto flex items-start gap-3 rounded-xl border px-4 py-3 text-sm shadow-lg ${box}`}
            >
              <Icon className="mt-0.5 h-5 w-5 shrink-0" />
              <p className="flex-1">{t.message}</p>
              <button type="button" onClick={() => remove(t.id)} aria-label="Dismiss" className="opacity-60 hover:opacity-100">
                <FiX />
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}