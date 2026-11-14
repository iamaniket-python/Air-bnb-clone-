import { Outlet } from 'react-router-dom'
import Logo from '../components/Logo'

export default function AuthLayout() {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="hidden flex-col justify-between bg-gradient-to-br from-brand-700 to-brand-900 p-12 text-white lg:flex">
        <div className="inline-flex items-center gap-2 text-xl font-bold">StayNest</div>
        <div>
          <h2 className="text-4xl font-bold leading-tight">Find a place that feels like yours.</h2>
          <p className="mt-4 max-w-md text-brand-100">
            Discover unique stays, book with confidence, or share your own space as a host.
          </p>
        </div>
        <p className="text-sm text-brand-200">© {new Date().getFullYear()} StayNest</p>
      </div>

      <div className="flex flex-col justify-center px-6 py-10 sm:px-12">
        <div className="mx-auto w-full max-w-md">
          <Logo className="mb-8 lg:hidden" />
          <Outlet />
        </div>
      </div>
    </div>
  )
}