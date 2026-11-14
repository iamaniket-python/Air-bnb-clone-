const inrFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
})

// Backend money strings deta hai ("7500.00") -> "₹7,500"
export function formatINR(value) {
  const num = Number(value)
  if (Number.isNaN(num)) return '—'
  return inrFormatter.format(num)
}

// "YYYY-MM-DD" ko local date banata hai (timezone shift se bachne ke liye manually parse)
export function formatDate(value) {
  if (!value) return '—'
  const [y, m, d] = String(value).slice(0, 10).split('-').map(Number)
  if (!y || !m || !d) return '—'
  return new Date(y, m - 1, d).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

export function fullName(user) {
  if (!user) return ''
  const name = [user.first_name, user.last_name].filter(Boolean).join(' ')
  return name || user.username || ''
}

export function initials(user) {
  if (!user) return '?'
  const a = user.first_name?.[0] ?? user.username?.[0] ?? '?'
  const b = user.last_name?.[0] ?? ''
  return (a + b).toUpperCase()
}