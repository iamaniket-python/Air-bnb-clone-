import { Link, useNavigate } from 'react-router-dom'
import { FiArrowLeft } from 'react-icons/fi'
import PropertyForm from '../components/PropertyForm'
import Spinner from '../components/Spinner'
import useApi from '../hooks/useApi'
import useToast from '../hooks/useToast'
import { createProperty } from '../api/properties'

export default function AddProperty() {
  const navigate = useNavigate()
  const toast = useToast()
  const { data: amenities, loading } = useApi('/amenities/')

  const onSubmit = async (payload) => {
    const created = await createProperty(payload)
    toast.success('Property created. Now add some photos.')
    // Photos Edit page par upload hoti hain (ImageManager)
    navigate(`/host/properties/${created.id}/edit`, { replace: true })
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <Link to="/host/properties" className="inline-flex items-center gap-1 text-sm text-slate-600 hover:underline">
        <FiArrowLeft /> My properties
      </Link>
      <h1 className="mt-3 text-2xl font-bold">Add a property</h1>
      <p className="mt-1 text-sm text-slate-500">Fill in the details. You can add photos in the next step.</p>

      <div className="mt-6">
        {loading ? (
          <div className="flex justify-center py-16 text-brand-600"><Spinner className="h-8 w-8" /></div>
        ) : (
          <PropertyForm
            amenities={Array.isArray(amenities) ? amenities : []}
            onSubmit={onSubmit}
            submitLabel="Create property"
          />
        )}
      </div>
    </div>
  )
}