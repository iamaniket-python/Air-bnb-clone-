import { Link } from 'react-router-dom'
import Button from '../components/Button'

export default function Forbidden() {
  return (
    <div className="mx-auto max-w-xl px-4 py-24 text-center">
      <p className="text-6xl font-bold text-brand-600">403</p>
      <h1 className="mt-4 text-2xl font-bold">You don&apos;t have access to this page</h1>
      <p className="mt-2 text-slate-500">Your account role does not allow viewing this section.</p>
      <Link to="/" className="mt-6 inline-block">
        <Button>Back to home</Button>
      </Link>
    </div>
  )
}