import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import FormField from '../components/FormField'
import Button from '../components/Button'
import Alert from '../components/Alert'
import useAuth from '../hooks/useAuth'
import useToast from '../hooks/useToast'
import { applyFieldErrors, normalizeApiError } from '../utils/apiError'
import { getDefaultRouteForRole } from '../utils/roles'

const FIELDS = ['username', 'email', 'first_name', 'last_name', 'phone_number', 'password', 'password2', 'role']

const ROLE_OPTIONS = [
  { value: 'guest', title: 'Guest', desc: 'I want to book stays' },
  { value: 'host', title: 'Host', desc: 'I want to list my property' },
]

export default function Register() {
  const { register: signUp } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const [formError, setFormError] = useState('')

  const {
    register,
    handleSubmit,
    setError,
    watch,
    formState: { errors, isSubmitting },
  } = useForm({
    defaultValues: {
      role: 'guest',
      first_name: '',
      last_name: '',
      username: '',
      email: '',
      phone_number: '',
      password: '',
      password2: '',
    },
  })

  const onSubmit = async (values) => {
    setFormError('')
    const payload = {
      role: values.role,
      first_name: values.first_name.trim(),
      last_name: values.last_name.trim(),
      username: values.username.trim(),
      email: values.email.trim(),
      password: values.password,
      password2: values.password2,
    }
    // Optional field khali ho to bhejna hi nahi
    if (values.phone_number.trim()) payload.phone_number = values.phone_number.trim()

    try {
      const user = await signUp(payload)
      toast.success('Account created. Welcome to StayNest!')
      navigate(getDefaultRouteForRole(user.role), { replace: true })
    } catch (err) {
      const normalized = normalizeApiError(err)
      const extra = applyFieldErrors(setError, normalized.fieldErrors, FIELDS)
      setFormError(extra ? `${normalized.message} ${extra}` : normalized.message)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold">Create your account</h1>
      <p className="mt-1 text-sm text-slate-500">Join StayNest as a guest or a host.</p>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-6 space-y-4">
        <Alert message={formError} />

        <fieldset>
          <legend className="mb-1 text-sm font-medium text-slate-700">I am a</legend>
          <div className="grid grid-cols-2 gap-3">
            {ROLE_OPTIONS.map((opt) => (
              <label key={opt.value} className="cursor-pointer">
                <input type="radio" value={opt.value} className="peer sr-only" {...register('role')} />
                <div className="rounded-xl border border-slate-300 p-3 text-sm transition peer-checked:border-brand-600 peer-checked:bg-brand-50 peer-focus-visible:ring-2 peer-focus-visible:ring-brand-200">
                  <p className="font-semibold">{opt.title}</p>
                  <p className="text-xs text-slate-500">{opt.desc}</p>
                </div>
              </label>
            ))}
          </div>
          {errors.role && <p className="mt-1 text-xs text-red-600">{errors.role.message}</p>}
        </fieldset>

        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            id="first_name"
            label="First name"
            autoComplete="given-name"
            error={errors.first_name?.message}
            {...register('first_name', { required: 'First name is required' })}
          />
          <FormField
            id="last_name"
            label="Last name"
            autoComplete="family-name"
            error={errors.last_name?.message}
            {...register('last_name', { required: 'Last name is required' })}
          />
        </div>

        <FormField
          id="username"
          label="Username"
          autoComplete="username"
          error={errors.username?.message}
          {...register('username', {
            required: 'Username is required',
            minLength: { value: 3, message: 'Username must be at least 3 characters' },
            pattern: { value: /^[\w.@+-]+$/, message: 'Only letters, numbers and @ . + - _ are allowed' },
          })}
        />

        <FormField
          id="email"
          type="email"
          label="Email"
          autoComplete="email"
          error={errors.email?.message}
          {...register('email', {
            required: 'Email is required',
            pattern: { value: /^\S+@\S+\.\S+$/, message: 'Enter a valid email address' },
          })}
        />

        <FormField
          id="phone_number"
          type="tel"
          label="Phone number (optional)"
          autoComplete="tel"
          error={errors.phone_number?.message}
          {...register('phone_number', {
            pattern: { value: /^\+?[0-9\s-]{7,15}$/, message: 'Enter a valid phone number' },
          })}
        />

        <FormField
          id="password"
          type="password"
          label="Password"
          autoComplete="new-password"
          hint="At least 8 characters."
          error={errors.password?.message}
          {...register('password', {
            required: 'Password is required',
            minLength: { value: 8, message: 'Password must be at least 8 characters' },
          })}
        />

        <FormField
          id="password2"
          type="password"
          label="Confirm password"
          autoComplete="new-password"
          error={errors.password2?.message}
          {...register('password2', {
            required: 'Please confirm your password',
            validate: (value) => value === watch('password') || 'Passwords do not match',
          })}
        />

        <Button type="submit" size="lg" loading={isSubmitting} className="w-full">
          Create account
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-600">
        Already have an account?{' '}
        <Link to="/login" className="font-semibold text-brand-700 hover:underline">
          Log in
        </Link>
      </p>
    </div>
  )
}