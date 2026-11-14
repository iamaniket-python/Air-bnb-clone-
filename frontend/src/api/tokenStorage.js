const ACCESS_KEY = 'staynest_access'
const REFRESH_KEY = 'staynest_refresh'
const USER_KEY = 'staynest_user'

// localStorage kabhi-kabhi block hota hai (private mode etc.), isliye safe wrapper
function safe(fn) {
  try {
    return fn()
  } catch {
    return null
  }
}

export const tokenStorage = {
  getAccess: () => safe(() => localStorage.getItem(ACCESS_KEY)),
  getRefresh: () => safe(() => localStorage.getItem(REFRESH_KEY)),
  setTokens: ({ access, refresh }) =>
    safe(() => {
      if (access) localStorage.setItem(ACCESS_KEY, access)
      if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
    }),
  getUser: () => safe(() => JSON.parse(localStorage.getItem(USER_KEY))),
  setUser: (user) => safe(() => localStorage.setItem(USER_KEY, JSON.stringify(user))),
  clear: () =>
    safe(() => {
      localStorage.removeItem(ACCESS_KEY)
      localStorage.removeItem(REFRESH_KEY)
      localStorage.removeItem(USER_KEY)
    }),
}