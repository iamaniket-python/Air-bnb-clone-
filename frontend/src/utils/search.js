// Search form values se URL banata hai. Kuch filter nahi hai to /properties.
export function buildSearchUrl({ destination, check_in, check_out, guests } = {}) {
  const params = new URLSearchParams()
  if (destination) params.set('destination', destination)
  if (check_in && check_out) {
    params.set('check_in', check_in)
    params.set('check_out', check_out)
  }
  if (guests && Number(guests) > 1) params.set('guests', String(guests))
  const qs = params.toString()
  return qs ? `/search?${qs}` : '/properties'
}