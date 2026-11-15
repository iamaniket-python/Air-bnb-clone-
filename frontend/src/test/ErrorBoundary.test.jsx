import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import ErrorBoundary from '../components/ErrorBoundary'

function Bomb({ explode }) {
  if (explode) throw new Error('boom')
  return <p>All good</p>
}

describe('ErrorBoundary', () => {
  it('renders children when nothing breaks', () => {
    render(
      <ErrorBoundary>
        <Bomb explode={false} />
      </ErrorBoundary>,
    )
    expect(screen.getByText('All good')).toBeInTheDocument()
  })

  it('shows a fallback instead of a blank screen, and resets when resetKey changes', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const { rerender } = render(
      <ErrorBoundary resetKey="a">
        <Bomb explode />
      </ErrorBoundary>,
    )
    expect(screen.getByRole('alert')).toHaveTextContent(/something went wrong/i)

    rerender(
      <ErrorBoundary resetKey="b">
        <Bomb explode={false} />
      </ErrorBoundary>,
    )
    expect(screen.getByText('All good')).toBeInTheDocument()

    spy.mockRestore()
  })
})