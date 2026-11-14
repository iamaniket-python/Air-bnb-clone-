import { useState } from 'react'
import Modal from './Modal'
import Button from './Button'
import Alert from './Alert'
import { normalizeApiError } from '../utils/apiError'
import { errorText } from '../utils/errors'

// Parent isko `{target && <ConfirmModal key={target.id} ... />}` ki tarah render kare.
// onConfirm() promise return kare. Fail ho to error modal mein dikhta hai.
// Success par parent modal band karta hai (unmount), isliye yahan submitting reset nahi karte.
export default function ConfirmModal({
  title,
  description,
  confirmLabel = 'Confirm',
  danger = false,
  onClose,
  onConfirm,
}) {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    setSubmitting(true)
    setError('')
    try {
      await onConfirm()
    } catch (err) {
      setError(errorText(normalizeApiError(err)))
      setSubmitting(false)
    }
  }

  return (
    <Modal title={title} onClose={onClose}>
      <div className="space-y-4">
        {description && <p className="text-sm text-slate-600">{description}</p>}
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