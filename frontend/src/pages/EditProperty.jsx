import { Link, useParams } from 'react-router-dom'
import { FiArrowLeft, FiHome } from 'react-icons/fi'
import PropertyForm from '../components/PropertyForm'
import ImageManager from '../components/ImageManager'
import EmptyState from '../components/EmptyState'
import Alert from '../components/Alert'
import Button from '../components/Button'
import Spinner from '../components/Spinner'
import useApi from '../hooks/useApi'
import useToast from '../hooks/useToast'
import { updateProperty } from '../api/properties'

export default function EditProperty() {
  const { id } = useParams()
  const toast = useToast()
  const { data: property, loading, error, reload } = useApi(`/properties/${id}/`)
  const { data: amenities } = useApi('/amenities/')

  const onSubmit = async (payload) => {
    await updateProperty(id, payload)
    toast.success('Property updated.')
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <Link to="/host/properties" className="inline-flex items-center gap-1 text-sm text-slate-600 hover:underline">
        <FiArrowLeft /> My properties
      </Link>
      <h1 className="mt-3 text-2xl font-bold">Edit property</h1>

      <div className="mt-6 space-y-6">
        {loading ? (
          <div className="flex justify-center py-16 text-brand-600"><Spinner className="h-8 w-8" /></div>
        ) : error ? (
          error.status === 404 || error.status === 403 ? (
            <EmptyState Icon={FiHome} title="Property not available" text="It does not exist or you do not have access to it.">
              <Link to="/host/properties"><Button>Back to my properties</Button></Link>
            </EmptyState>
          ) : (
            <div className="space-y-3">
              <Alert message={error.message} />
              <Button variant="secondary" onClick={reload}>Retry</Button>
            </div>
          )
        ) : (
          <>
            <ImageManager propertyId={property.id} />
            <PropertyForm
              key={property.id}
              property={property}
              amenities={Array.isArray(amenities) ? amenities : []}
              onSubmit={onSubmit}
              submitLabel="Save changes"
              showActive
            />
          </>
        )}
      </div>
    </div>
  )
}