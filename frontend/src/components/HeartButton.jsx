import { FaHeart } from 'react-icons/fa'
import { FiHeart } from 'react-icons/fi'
import { useLocation, useNavigate } from 'react-router-dom'
import useAuth from '../hooks/useAuth'
import useToast from '../hooks/useToast'
import useWishlist from '../hooks/useWishlist'

export default function HeartButton({ propertyId, className = '' }) {
  const { isAuthenticated, role } = useAuth()
  const { isSaved, toggle } = useWishlist()
  const toast = useToast()
  const navigate = useNavigate()
  const location = useLocation()
  const saved = isSaved(propertyId)

  const onClick = (e) => {
    // Card Link ke andar hai, isliye navigation rokna zaroori hai
    e.preventDefault()
    e.stopPropagation()

    if (!isAuthenticated) {
      navigate('/login', { state: { from: location } })
      return
    }
    if (role !== 'guest') {
      toast.info('Only guest accounts can save stays to a wishlist.')
      return
    }
    toggle(propertyId)
  }

  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={saved}
      aria-label={saved ? 'Remove from wishlist' : 'Save to wishlist'}
      className={`flex h-9 w-9 items-center justify-center rounded-full bg-white/90 shadow transition hover:scale-110 ${className}`}
    >
      {saved ? <FaHeart className="h-4 w-4 text-red-500" /> : <FiHeart className="h-4 w-4 text-slate-700" />}
    </button>
  )
}