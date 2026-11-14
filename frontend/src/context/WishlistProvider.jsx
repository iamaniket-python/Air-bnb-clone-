import { useCallback, useEffect, useMemo, useState } from 'react'
import { WishlistContext } from './WishlistContext'
import useAuth from '../hooks/useAuth'
import useToast from '../hooks/useToast'
import { addToWishlist, getWishlistIds, removeFromWishlist } from '../api/wishlist'
import { normalizeApiError } from '../utils/apiError'

export default function WishlistProvider({ children }) {
  const { user, role, isAuthenticated } = useAuth()
  const toast = useToast()

  const isGuest = isAuthenticated && role === 'guest'
  const userKey = user?.id ?? user?.username ?? null

  // userKey saath mein rakha: user badle to purane user ke ids kabhi dikhte nahi
  const [state, setState] = useState({ userKey: null, ids: [] })

  useEffect(() => {
    if (!isGuest) return undefined
    let cancelled = false
    getWishlistIds()
      .then((ids) => {
        if (!cancelled) setState({ userKey, ids })
      })
      .catch(() => {
        // wishlist load fail hua to hearts khali rahenge, app nahi tootega
      })
    return () => {
      cancelled = true
    }
  }, [isGuest, userKey])

  // loaded: current guest ki ids aa chuki hain (Wishlist page isse flicker rokta hai)
  const loaded = isGuest && state.userKey === userKey

  const ids = useMemo(() => new Set(loaded ? state.ids : []), [loaded, state])

  const setSaved = useCallback(
    (propertyId, shouldBeSaved) => {
      setState((prev) => {
        const base = prev.userKey === userKey ? prev.ids : []
        const without = base.filter((i) => i !== propertyId)
        return { userKey, ids: shouldBeSaved ? [...without, propertyId] : without }
      })
    },
    [userKey],
  )

  const toggle = useCallback(
    async (propertyId) => {
      const wasSaved = ids.has(propertyId)
      setSaved(propertyId, !wasSaved) // optimistic
      try {
        if (wasSaved) {
          try {
            await removeFromWishlist(propertyId)
          } catch (err) {
            if (err.response?.status !== 404) throw err // 404 = pehle hi hata hua
          }
          toast.info('Removed from wishlist')
        } else {
          await addToWishlist(propertyId)
          toast.success('Saved to wishlist')
        }
      } catch (err) {
        setSaved(propertyId, wasSaved) // revert
        toast.error(normalizeApiError(err).message)
      }
    },
    [ids, setSaved, toast],
  )

  const value = useMemo(() => ({ ids, loaded, isSaved: (id) => ids.has(id), toggle }), [ids, loaded, toggle])

  return <WishlistContext.Provider value={value}>{children}</WishlistContext.Provider>
}