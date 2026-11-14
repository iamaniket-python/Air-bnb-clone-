export const ROLES = {
  GUEST: 'guest',
  HOST: 'host',
  ADMIN: 'admin',
}

// Login/register ke baad role ke hisaab se kahan bhejna hai
export function getDefaultRouteForRole(role) {
  if (role === ROLES.ADMIN) return '/admin/dashboard'
  if (role === ROLES.HOST) return '/host/dashboard'
  return '/'
}