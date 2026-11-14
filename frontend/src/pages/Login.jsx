import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import FormField from '../components/FormField'
import Button from '../components/Button'
import Alert from '../components/Alert'
import useAuth from '../hooks/useAuth'
import useToast from '../hooks/useToast'
import { applyFieldErrors, normalizeApiError } from '../utils/apiError'
import { getDefaultRouteForRole } from '../utils/roles'

const FIELDS = ['username', 'password']

export default function Login() {
  const { login } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const location = useLocation()
  const [formError, setFormError] = useState('')

  // ProtectedRoute se aaye the to login ke baad wahin wapas bhejo
  const from = location.state?.from
  const redirectTo = from ? `${from.pathname}${from.search || ''}` : null

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm({ defaultValues: { username: '', password: '' } })

  const onSubmit = async (values) => {
    setFormError('')
    try {
      const user = await login({ username: values.username.trim(), password: values.password })
      toast.success(`Welcome back, ${user.first_name || user.username}!`)
      navigate(redirectTo ?? getDefaultRouteForRole(user.role), { replace: true })
    } catch (err) {
      const normalized = normalizeApiError(err)
      const extra = applyFieldErrors(setError, normalized.fieldErrors, FIELDS)
      setFormError(extra ? `${normalized.message} ${extra}` : normalized.message)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold">Welcome back</h1>
      <p className="mt-1 text-sm text-slate-500">Log in to manage your bookings and listings.</p>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-6 space-y-4">
        <Alert message={formError} />

        <FormField
          id="username"
          label="Username or email"
          autoComplete="username"
          error={errors.username?.message}
          {...register('username', { required: 'Username or email is required' })}
        />

        <FormField
          id="password"
          type="password"
          label="Password"
          autoComplete="current-password"
          error={errors.password?.message}
          {...register('password', { required: 'Password is required' })}
        />

        <Button type="submit" size="lg" loading={isSubmitting} className="w-full">
          Log in
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-600">
        New to StayNest?{' '}
        <Link to="/register" className="font-semibold text-brand-700 hover:underline">
          Create an account
        </Link>
      </p>
    </div>
  )
}