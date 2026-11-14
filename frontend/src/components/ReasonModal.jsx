import { useState } from 'react'
import Modal from './Modal'
import Button from './Button'
import Alert from './Alert'
import { normalizeApiError } from '../utils/apiError'
import { errorText } from '../utils/errors'

// Parent isko `{target && <ReasonModal key={target.id} ... />}` ki tarah render kare.
// onSubmit(reason) promise return kare; fail ho to error modal mein dikhta hai.
export default function ReasonModal({
  title,
  description,
  required = false,
  confirmLabel = 'Confirm',
  danger = false,
  onClose,
  onSubmit,
}) {
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    if (required && !reason.trim()) {
      setError('Please enter a reason.')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      await onSubmit(reason.trim())
    } catch (err) {
      setError(errorText(normalizeApiError(err)))
      setSubmitting(false)
    }
  }

  return (
    <Modal title={title} onClose={onClose}>
      <div className="space-y-4">
        {description && <p className="text-sm text-slate-600">{description}</p>}
        <div>
          <label htmlFor="reason-text" className="mb-1 block text-sm font-medium text-slate-700">
            Reason {required ? '' : '(optional)'}
          </label>
          <textarea
            id="reason-text"
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-100"
          />
        </div>
        <Alert message={error} />
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose} disabled={submitting}>Close</Button>
          <Button variant={danger ? 'danger' : 'primary'} loading={submitting} onClick={submit}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </Modal>
  )
}