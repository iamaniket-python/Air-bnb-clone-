import { useCallback, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { FiCalendar, FiChevronDown, FiGrid, FiHeart, FiLogOut, FiPlusCircle, FiUser } from 'react-icons/fi'
import Logo from './Logo'
import NavSearch from './NavSearch'
import Button from './Button'
import useAuth from '../hooks/useAuth'
import useToast from '../hooks/useToast'
import useClickOutside from '../hooks/useClickOutside'
import { fullName, initials } from '../utils/format'

// Role ke hisaab se dropdown menu
const MENU = {
  guest: [
    { to: '/bookings', label: 'My bookings', Icon: FiCalendar },
    { to: '/wishlist', label: 'Wishlist', Icon: FiHeart },
    { to: '/profile', label: 'Profile', Icon: FiUser },
  ],
  host: [
    { to: '/host/dashboard', label: 'Dashboard', Icon: FiGrid },
    { to: '/host/reservations', label: 'Reservations', Icon: FiCalendar },
    { to: '/host/properties/new', label: 'Add property', Icon: FiPlusCircle },
    { to: '/profile', label: 'Profile', Icon: FiUser },
  ],
  admin: [
    { to: '/admin/dashboard', label: 'Admin dashboard', Icon: FiGrid },
    { to: '/profile', label: 'Profile', Icon: FiUser },
  ],
}

export default function Navbar() {
  const { user, role, isAuthenticated, logout } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const menuRef = useRef(null)

  const close = useCallback(() => setOpen(false), [])
  useClickOutside(menuRef, close)

  const handleLogout = async () => {
    close()
    await logout()
    toast.info('You have been logged out.')
    navigate('/')
  }

  const items = MENU[role] ?? MENU.guest

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
        <Logo />

        <NavSearch className="hidden w-full max-w-md md:flex" />

        <nav className="flex items-center gap-2">
          {isAuthenticated ? (
            <div className="relative" ref={menuRef}>
              <button
                type="button"
                onClick={() => setOpen((o) => !o)}
                aria-haspopup="menu"
                aria-expanded={open}
                className="flex items-center gap-2 rounded-full border border-slate-300 py-1 pl-1 pr-3 hover:shadow-md"
              >
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-600 text-xs font-bold text-white">
                  {initials(user)}
                </span>
                <FiChevronDown className="h-4 w-4 text-slate-600" />
              </button>

              {open && (
                <div
                  role="menu"
                  className="absolute right-0 mt-2 w-60 overflow-hidden rounded-xl border border-slate-200 bg-white py-2 shadow-xl"
                >
                  <div className="border-b border-slate-100 px-4 pb-2">
                    <p className="truncate text-sm font-semibold">{fullName(user)}</p>
                    <p className="text-xs capitalize text-slate-500">{role}</p>
                  </div>
                  {items.map(({ to, label, Icon }) => (
                    <Link
                      key={to}
                      to={to}
                      role="menuitem"
                      onClick={close}
                      className="flex items-center gap-3 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
                    >
                      <Icon className="h-4 w-4" />
                      {label}
                    </Link>
                  ))}
                  <button
                    type="button"
                    role="menuitem"
                    onClick={handleLogout}
                    className="flex w-full items-center gap-3 border-t border-slate-100 px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50"
                  >
                    <FiLogOut className="h-4 w-4" />
                    Log out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <>
              <Link to="/login">
                <Button variant="ghost" size="sm">Log in</Button>
              </Link>
              <Link to="/register">
                <Button size="sm">Sign up</Button>
              </Link>
            </>
          )}
        </nav>
      </div>

      {/* Mobile par search neeche ek alag row mein */}
      <div className="px-4 pb-3 md:hidden">
        <NavSearch />
      </div>
    </header>
  )
}