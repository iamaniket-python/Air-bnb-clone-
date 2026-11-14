import { Route, Routes } from 'react-router-dom'
import AuthLayout from '../layouts/AuthLayout'
import MainLayout from '../layouts/MainLayout'
import AdminLayout from '../layouts/AdminLayout'
import ProtectedRoute from './ProtectedRoute'
import PublicOnlyRoute from './PublicOnlyRoute'
import Home from '../pages/Home'
import Login from '../pages/Login'
import Register from '../pages/Register'
import PropertyListing from '../pages/PropertyListing'
import PropertyDetails from '../pages/PropertyDetails'
import Checkout from '../pages/Checkout'
import Payment from '../pages/Payment'
import MyBookings from '../pages/MyBookings'
import Wishlist from '../pages/Wishlist'
import Profile from '../pages/Profile'
import HostDashboard from '../pages/HostDashboard'
import HostProperties from '../pages/HostProperties'
import AddProperty from '../pages/AddProperty'
import EditProperty from '../pages/EditProperty'
import HostReservations from '../pages/HostReservations'
import AdminDashboard from '../pages/AdminDashboard'
import AdminUsers from '../pages/AdminUsers'
import AdminProperties from '../pages/AdminProperties'
import AdminBookings from '../pages/AdminBookings'
import AdminReviews from '../pages/AdminReviews'
import Forbidden from '../pages/Forbidden'
import NotFound from '../pages/NotFound'

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
          <Route path="/checkout" element={<Checkout />} />
          <Route path="/payment/:bookingId" element={<Payment />} />
          <Route path="/bookings" element={<MyBookings />} />
          <Route path="/wishlist" element={<Wishlist />} />
        </Route>

        {/* Kisi bhi logged-in role ke liye (10c) */}
        <Route element={<ProtectedRoute />}>
          <Route path="/profile" element={<Profile />} />
        </Route>

        {/* Host (10d) */}
        <Route element={<ProtectedRoute roles={['host']} />}>
          <Route path="/host/dashboard" element={<HostDashboard />} />
          <Route path="/host/properties" element={<HostProperties />} />
          <Route path="/host/properties/new" element={<AddProperty />} />
          <Route path="/host/properties/:id/edit" element={<EditProperty />} />
          <Route path="/host/reservations" element={<HostReservations />} />
        </Route>

        {/* Admin (10e): AdminLayout tab bar deta hai */}
        <Route element={<ProtectedRoute roles={['admin']} />}>
          <Route element={<AdminLayout />}>
            <Route path="/admin/dashboard" element={<AdminDashboard />} />
            <Route path="/admin/users" element={<AdminUsers />} />
            <Route path="/admin/properties" element={<AdminProperties />} />
            <Route path="/admin/bookings" element={<AdminBookings />} />
            <Route path="/admin/reviews" element={<AdminReviews />} />
          </Route>
        </Route>

        <Route path="/403" element={<Forbidden />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}