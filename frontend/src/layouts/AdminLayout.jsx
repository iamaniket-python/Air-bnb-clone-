import { NavLink, Outlet } from 'react-router-dom'

const LINKS = [
  { to: '/admin/dashboard', label: 'Dashboard' },
  { to: '/admin/users', label: 'Users' },
  { to: '/admin/properties', label: 'Properties' },
  { to: '/admin/bookings', label: 'Bookings' },
  { to: '/admin/reviews', label: 'Reviews' },
]

// Admin pages ke upar tab bar. Role check ProtectedRoute karta hai.
export default function AdminLayout() {
  return (
    <div>
      <div className="border-b border-slate-200 bg-slate-50">
        <nav className="mx-auto flex max-w-7xl gap-1 overflow-x-auto px-4 sm:px-6 lg:px-8" aria-label="Admin sections">
          {LINKS.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              className={({ isActive }) =>
                `whitespace-nowrap border-b-2 px-4 py-3 text-sm font-medium transition ${
                  isActive
                    ? 'border-brand-600 text-brand-700'
                    : 'border-transparent text-slate-600 hover:text-slate-900'
                }`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
      </div>
      <Outlet />
    </div>
  )
}