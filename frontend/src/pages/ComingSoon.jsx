import useAuth from '../hooks/useAuth'

// Placeholder page: auth/role routing test karne mein bhi kaam aata hai
export default function ComingSoon({ title, phase }) {
  const { user, role, isAuthenticated } = useAuth()

  return (
    <div className="mx-auto max-w-3xl px-4 py-20 text-center">
      <p className="text-sm font-semibold uppercase tracking-wide text-brand-600">Phase {phase}</p>
      <h1 className="mt-2 text-3xl font-bold">{title}</h1>
      <p className="mt-3 text-slate-500">Ye page abhi bana nahi hai, agle sub-phase mein aayega.</p>
      <p className="mt-6 text-sm text-slate-400">
        {isAuthenticated ? `Signed in as ${user?.username} (${role})` : 'Not signed in'}
      </p>
    </div>
  )
}