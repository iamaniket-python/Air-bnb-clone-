import { Link } from 'react-router-dom'
import { FiHeart, FiHome, FiShield } from 'react-icons/fi'
import Button from '../components/Button'
import useAuth from '../hooks/useAuth'

const FEATURES = [
  { Icon: FiHome, title: 'Unique stays', text: 'Apartments, villas, cottages and more across India.' },
  { Icon: FiShield, title: 'Safe booking', text: 'Clear cancellation policy and secure payments.' },
  { Icon: FiHeart, title: 'Save favourites', text: 'Keep a wishlist of places you love.' },
]

// Real Home (featured properties, search bar) 10b mein banega
export default function Home() {
  const { isAuthenticated } = useAuth()

  return (
    <div>
      <section className="bg-gradient-to-b from-brand-50 to-white">
        <div className="mx-auto max-w-4xl px-4 py-20 text-center sm:py-28">
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Find your next <span className="text-brand-600">stay</span>
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-lg text-slate-600">
            Search homes, villas and getaways. Book in minutes, or become a host and earn from your space.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link to="/properties">
              <Button size="lg">Explore stays</Button>
            </Link>
            {!isAuthenticated && (
              <Link to="/register">
                <Button size="lg" variant="secondary">Become a host</Button>
              </Link>
            )}
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-6 px-4 py-16 sm:grid-cols-3 sm:px-6">
        {FEATURES.map(({ Icon, title, text }) => (
          <div key={title} className="rounded-2xl border border-slate-200 p-6">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
              <Icon className="h-5 w-5" />
            </span>
            <h3 className="mt-4 font-semibold">{title}</h3>
            <p className="mt-1 text-sm text-slate-500">{text}</p>
          </div>
        ))}
      </section>
    </div>
  )
}