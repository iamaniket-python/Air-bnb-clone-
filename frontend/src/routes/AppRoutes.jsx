import { Route, Routes } from 'react-router-dom'
import AuthLayout from '../layouts/AuthLayout'
import MainLayout from '../layouts/MainLayout'
import ProtectedRoute from './ProtectedRoute'
import PublicOnlyRoute from './PublicOnlyRoute'
import Home from '../pages/Home'
import Login from '../pages/Login'
import Register from '../pages/Register'
import PropertyListing from '../pages/PropertyListing'
import PropertyDetails from '../pages/PropertyDetails'
import ComingSoon from '../pages/ComingSoon'
import Forbidden from '../pages/Forbidden'
import NotFound from '../pages/NotFound'

// Aage ke phases mein ComingSoon ki jagah asli page element lagega
export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<AuthLayout />}>
        <Route element={<PublicOnlyRoute />}>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
        </Route>
      </Route>

      <Route element={<MainLayout />}>
        <Route index element={<Home />} />

        {/* Public (10b) */}
        <Route path="/properties" element={<PropertyListing mode="listing" />} />
        <Route path="/search" element={<PropertyListing mode="search" />} />
        <Route path="/properties/:id" element={<PropertyDetails />} />

        {/* Guest (10c) */}
        <Route element={<ProtectedRoute roles={['guest']} />}>
          <Route path="/checkout" element={<ComingSoon title="Booking checkout" phase="10c" />} />
          <Route path="/payment/:bookingId" element={<ComingSoon title="Payment" phase="10c" />} />
          <Route path="/bookings" element={<ComingSoon title="My bookings" phase="10c" />} />
          <Route path="/wishlist" element={<ComingSoon title="Wishlist" phase="10c" />} />
        </Route>

        {/* Kisi bhi logged-in role ke liye (10c) */}
        <Route element={<ProtectedRoute />}>
          <Route path="/profile" element={<ComingSoon title="Profile" phase="10c" />} />
        </Route>

        {/* Host (10d) */}
        <Route element={<ProtectedRoute roles={['host']} />}>
          <Route path="/host/dashboard" element={<ComingSoon title="Host dashboard" phase="10d" />} />
          <Route path="/host/properties/new" element={<ComingSoon title="Add property" phase="10d" />} />
          <Route path="/host/properties/:id/edit" element={<ComingSoon title="Edit property" phase="10d" />} />
          <Route path="/host/reservations" element={<ComingSoon title="Host reservations" phase="10d" />} />
        </Route>

        {/* Admin (10e) */}
        <Route element={<ProtectedRoute roles={['admin']} />}>
          <Route path="/admin/dashboard" element={<ComingSoon title="Admin dashboard" phase="10e" />} />
        </Route>

        <Route path="/403" element={<Forbidden />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}