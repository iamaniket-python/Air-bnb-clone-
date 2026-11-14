import { useState } from 'react'
import { useForm } from 'react-hook-form'
import FormField from '../components/FormField'
import Button from '../components/Button'
import Alert from '../components/Alert'
import Spinner from '../components/Spinner'
import useApi from '../hooks/useApi'
import useAuth from '../hooks/useAuth'
import useToast from '../hooks/useToast'
import { updateProfile } from '../api/profile'
import { applyFieldErrors, normalizeApiError } from '../utils/apiError'

const USER_FIELDS = ['first_name', 'last_name', 'phone_number']
const PROFILE_FIELDS = ['bio', 'date_of_birth', 'city', 'state', 'country']
const ALL_FIELDS = [...USER_FIELDS, ...PROFILE_FIELDS]

// Response flat ho ya {profile: {...}} nested, dono padh leta hai
function readShape(data) {
  const base = data?.user ?? data ?? {}
  const profile = base.profile ?? data?.profile ?? null
  const get = (key) => base[key] ?? profile?.[key] ?? ''
  return { base, nested: Boolean(profile && typeof profile === 'object'), get }
}

const inputCls =
  'w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-100'

function ProfileForm({ data }) {
  const { updateUser } = useAuth()
  const toast = useToast()
  const [formError, setFormError] = useState('')
  const { base, nested, get } = readShape(data)

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting, isDirty },
  } = useForm({
    defaultValues: Object.fromEntries(ALL_FIELDS.map((f) => [f, String(get(f) ?? '')])),
  })

  const onSubmit = async (values) => {
    setFormError('')
    const userPart = {
      first_name: values.first_name.trim(),
      last_name: values.last_name.trim(),
      phone_number: values.phone_number.trim(),
    }
    const profilePart = {
      bio: values.bio.trim(),
      date_of_birth: values.date_of_birth || null,
      city: values.city.trim(),
      state: values.state.trim(),
      country: values.country.trim(),
    }
    const payload = nested ? { ...userPart, profile: profilePart } : { ...userPart, ...profilePart }

    try {
      await updateProfile(payload)
      updateUser(userPart)
      toast.success('Profile updated.')
    } catch (err) {
      const normalized = normalizeApiError(err)
      const extra = applyFieldErrors(setError, normalized.fieldErrors, ALL_FIELDS)
      setFormError(extra ? `${normalized.message} ${extra}` : normalized.message)
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-6 space-y-4">
      <Alert message={formError} />

      <div className="grid gap-4 sm:grid-cols-2">
        <FormField id="username" label="Username" value={base.username ?? ''} readOnly disabled onChange={() => {}} />
        <FormField id="email" label="Email" value={base.email ?? ''} readOnly disabled onChange={() => {}} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <FormField
          id="first_name"
          label="First name"
          error={errors.first_name?.message}
          {...register('first_name', { required: 'First name is required' })}
        />
        <FormField
          id="last_name"
          label="Last name"
          error={errors.last_name?.message}
          {...register('last_name', { required: 'Last name is required' })}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <FormField
          id="phone_number"
          type="tel"
          label="Phone number"
          error={errors.phone_number?.message}
          {...register('phone_number', {
            pattern: { value: /^(\+?[0-9\s-]{7,15})?$/, message: 'Enter a valid phone number' },
          })}
        />
        <FormField
          id="date_of_birth"
          type="date"
          label="Date of birth"
          error={errors.date_of_birth?.message}
          {...register('date_of_birth')}
        />
      </div>

      <div>
        <label htmlFor="bio" className="mb-1 block text-sm font-medium text-slate-700">Bio</label>
        <textarea id="bio" rows={3} className={inputCls} {...register('bio')} />
        {errors.bio && <p className="mt-1 text-xs text-red-600">{errors.bio.message}</p>}
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <FormField id="city" label="City" error={errors.city?.message} {...register('city')} />
        <FormField id="state" label="State" error={errors.state?.message} {...register('state')} />
        <FormField id="country" label="Country" error={errors.country?.message} {...register('country')} />
      </div>

      <Button type="submit" size="lg" loading={isSubmitting} disabled={!isDirty}>
        Save changes
      </Button>
    </form>
  )
}

export default function Profile() {
  const { role } = useAuth()
  const { data, loading, error, reload } = useApi('/auth/profile/')

  return (
    <div className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-bold">Your profile</h1>
      <p className="mt-1 text-sm capitalize text-slate-500">{role} account</p>

      {loading ? (
        <div className="flex justify-center py-16 text-brand-600">
          <Spinner className="h-8 w-8" />
        </div>
      ) : error ? (
        <div className="mt-6 space-y-3">
          <Alert message={error.message} />
          <Button variant="secondary" onClick={reload}>Retry</Button>
        </div>
      ) : (
        <ProfileForm data={data} />
      )}
    </div>
  )
}