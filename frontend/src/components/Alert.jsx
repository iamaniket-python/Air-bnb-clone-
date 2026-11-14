import { FiAlertCircle, FiCheckCircle, FiInfo } from 'react-icons/fi'

const TYPES = {
  error: { box: 'border-red-200 bg-red-50 text-red-800', Icon: FiAlertCircle },
  success: { box: 'border-emerald-200 bg-emerald-50 text-emerald-800', Icon: FiCheckCircle },
  info: { box: 'border-sky-200 bg-sky-50 text-sky-800', Icon: FiInfo },
}

export default function Alert({ type = 'error', message, className = '' }) {
  if (!message) return null
  const { box, Icon } = TYPES[type] ?? TYPES.error
  return (
    <div role="alert" className={`flex items-start gap-2 rounded-lg border px-4 py-3 text-sm ${box} ${className}`}>
      <Icon className="mt-0.5 h-4 w-4 shrink-0" />
      <p>{message}</p>
    </div>
  )
}