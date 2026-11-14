import { useCallback, useEffect, useMemo, useState } from 'react'
import { AuthContext } from './AuthContext'
import { setAuthFailureHandler } from '../api/axios'
import { tokenStorage } from '../api/tokenStorage'
import * as authApi from '../api/auth'
import { decodeJwt } from '../utils/jwt'

// Role/username agar user object mein na ho to JWT claims se le lo
function buildUser(user, access) {
  const claims = access ? decodeJwt(access) : null
  return {
    ...user,
    role: user?.role ?? claims?.role ?? 'guest',
    username: user?.username ?? claims?.username,
  }
}

export default function AuthProvider({ children }) {
  const [user, setUser] = useState(() => (tokenStorage.getRefresh() ? tokenStorage.getUser() : null))
  // Reload par token hai to pehle profile verify hone tak "bootstrapping" rahega
  const [bootstrapping, setBootstrapping] = useState(() => Boolean(tokenStorage.getRefresh()))

  // Refresh fail hone par axios interceptor isko call karta hai
  useEffect(() => {
    setAuthFailureHandler(() => setUser(null))
    return () => setAuthFailureHandler(null)
  }, [])

  // Page reload par session restore
  useEffect(() => {
    if (!tokenStorage.getRefresh()) return undefined
    let cancelled = false

    authApi
      .getProfile()
      .then((data) => {
        if (cancelled) return
        const fresh = data?.user ?? data
        if (fresh && typeof fresh === 'object') {
          const merged = buildUser({ ...(tokenStorage.getUser() || {}), ...fresh }, tokenStorage.getAccess())
          tokenStorage.setUser(merged)
          setUser(merged)
        }
      })
      .catch(() => {
        // 401 + refresh fail => interceptor already logout kar chuka hai.
        // Network error jaisi baaki cheezon par stored user ke saath chalte rehte hain.
      })
      .finally(() => {
        if (!cancelled) setBootstrapping(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (credentials) => {
    const data = await authApi.login(credentials)
    tokenStorage.setTokens({ access: data.access, refresh: data.refresh })
    const nextUser = buildUser(data.user, data.access)
    tokenStorage.setUser(nextUser)
    setUser(nextUser)
    return nextUser
  }, [])

  const register = useCallback(async (payload) => {
    const data = await authApi.register(payload)
    tokenStorage.setTokens({ access: data.tokens?.access, refresh: data.tokens?.refresh })
    const nextUser = buildUser(data.user, data.tokens?.access)
    tokenStorage.setUser(nextUser)
    setUser(nextUser)
    return nextUser
  }, [])

  const logout = useCallback(async () => {
    const refresh = tokenStorage.getRefresh()
    try {
      if (refresh) await authApi.logout(refresh)
    } catch {
      // Server side logout fail ho to bhi local session clear karna hai
    } finally {
      tokenStorage.clear()
      setUser(null)
    }
  }, [])

  // Profile update ke baad (10c) navbar/state sync ke liye
  const updateUser = useCallback((partial) => {
    setUser((prev) => {
      const next = { ...(prev || {}), ...partial }
      tokenStorage.setUser(next)
      return next
    })
  }, [])

  const value = useMemo(
    () => ({
      user,
      role: user?.role ?? null,
      isAuthenticated: Boolean(user),
      bootstrapping,
      login,
      register,
      logout,
      updateUser,
    }),
    [user, bootstrapping, login, register, logout, updateUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}