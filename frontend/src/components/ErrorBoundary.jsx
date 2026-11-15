import { Component } from 'react'

// Render ke dauran koi bhi JS error aaye to blank screen ki jagah ye fallback dikhta hai.
// resetKey badle (jaise route change) to error clear ho jaata hai.
export default class ErrorBoundary extends Component {
  state = { error: null }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    // Production mein yahan Sentry jaisa tool lagega (Phase 12)
    console.error('UI crashed:', error, info?.componentStack)
  }

  componentDidUpdate(prevProps) {
    if (this.state.error && prevProps.resetKey !== this.props.resetKey) {
      this.setState({ error: null })
    }
  }

  render() {
    if (!this.state.error) return this.props.children

    return (
      <div role="alert" className="mx-auto max-w-xl px-4 py-24 text-center">
        <p className="text-5xl font-bold text-brand-600">Oops</p>
        <h1 className="mt-4 text-2xl font-bold">Something went wrong</h1>
        <p className="mt-2 text-slate-500">This page hit an unexpected error. Please try again.</p>
        <div className="mt-6 flex justify-center gap-3">
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
          >
            Reload page
          </button>
          <a href="/" className="rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold hover:bg-slate-50">
            Go home
          </a>
        </div>
      </div>
    )
  }
}