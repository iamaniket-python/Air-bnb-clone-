import { useRef, useState } from 'react'
import { FiStar, FiTrash2, FiUploadCloud } from 'react-icons/fi'
import Button from './Button'
import Alert from './Alert'
import Spinner from './Spinner'
import useApi from '../hooks/useApi'
import useToast from '../hooks/useToast'
import { deleteImage, updateImage, uploadImages } from '../api/properties'
import { normalizeApiError } from '../utils/apiError'
import { errorText } from '../utils/errors'
import { mediaUrl } from '../utils/media'

const MAX_FILES = 15
const MAX_BYTES = 5 * 1024 * 1024

export default function ImageManager({ propertyId }) {
  const toast = useToast()
  const inputRef = useRef(null)
  // Apna alag fetch: upload ke baad sirf yehi reload hota hai, form ke unsaved edits safe rehte hain
  const { data: property, loading, error, reload } = useApi(`/properties/${propertyId}/`)
  const [busy, setBusy] = useState(false)
  const [formError, setFormError] = useState('')

  const images = [...(property?.images ?? [])].sort(
    (a, b) => Number(b.is_primary) - Number(a.is_primary) || (a.display_order ?? 0) - (b.display_order ?? 0),
  )

  const run = async (fn, successMsg) => {
    setBusy(true)
    setFormError('')
    try {
      await fn()
      if (successMsg) toast.success(successMsg)
      reload()
    } catch (err) {
      setFormError(errorText(normalizeApiError(err)))
    } finally {
      setBusy(false)
    }
  }

  const onPick = (e) => {
    const files = Array.from(e.target.files ?? [])
    e.target.value = '' // same file dobara chun sakein
    if (files.length === 0) return

    if (images.length + files.length > MAX_FILES) {
      setFormError(`You can have at most ${MAX_FILES} photos. You can add ${Math.max(0, MAX_FILES - images.length)} more.`)
      return
    }
    const bad = files.find((f) => !f.type.startsWith('image/'))
    if (bad) {
      setFormError(`"${bad.name}" is not an image.`)
      return
    }
    const big = files.find((f) => f.size > MAX_BYTES)
    if (big) {
      setFormError(`"${big.name}" is larger than 5 MB.`)
      return
    }
    run(() => uploadImages(propertyId, files), `${files.length} photo(s) uploaded.`)
  }

  const remove = (img) => {
    if (!window.confirm('Delete this photo?')) return
    run(() => deleteImage(propertyId, img.id), 'Photo deleted.')
  }

  return (
    <section className="rounded-2xl border border-slate-200 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-semibold">Photos</h2>
          <p className="text-xs text-slate-500">Up to {MAX_FILES} photos, 5 MB each. The starred photo is the cover.</p>
        </div>
        <div>
          <input ref={inputRef} type="file" accept="image/*" multiple hidden onChange={onPick} />
          <Button variant="secondary" size="sm" loading={busy} onClick={() => inputRef.current?.click()}>
            <FiUploadCloud /> Add photos
          </Button>
        </div>
      </div>

      <div className="mt-4 space-y-3">
        <Alert message={formError} />
        {error && <Alert message={error.message} />}

        {loading && !property ? (
          <div className="flex justify-center py-8 text-brand-600"><Spinner className="h-6 w-6" /></div>
        ) : images.length === 0 ? (
          <p className="rounded-lg border border-dashed border-slate-300 py-8 text-center text-sm text-slate-500">
            No photos yet. Listings with photos get far more bookings.
          </p>
        ) : (
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {images.map((img) => (
              <li key={img.id} className="relative overflow-hidden rounded-xl border border-slate-200">
                <img src={mediaUrl(img)} alt={img.caption || 'Property photo'} className="aspect-[4/3] w-full object-cover" />
                {img.is_primary && (
                  <span className="absolute left-2 top-2 rounded-full bg-brand-600 px-2 py-0.5 text-xs font-semibold text-white">Cover</span>
                )}
                <div className="flex items-center justify-between gap-1 p-2">
                  <button
                    type="button"
                    disabled={busy || img.is_primary}
                    onClick={() => run(() => updateImage(propertyId, img.id, { is_primary: true }), 'Cover photo updated.')}
                    className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-40"
                  >
                    <FiStar /> Set cover
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => remove(img)}
                    aria-label="Delete photo"
                    className="rounded p-1.5 text-red-600 hover:bg-red-50 disabled:opacity-40"
                  >
                    <FiTrash2 />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}