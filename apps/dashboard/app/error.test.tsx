import React from 'react'
import { render, screen } from '@testing-library/react'
import ErrorComponent from './error'

// Mock window.Sentry
global.window.Sentry = {
  captureException: jest.fn()
}

describe('Error', () => {
  it('should render without crashing', () => {
    const mockError = new Error('Test error')
    const mockReset = jest.fn()

    render(<ErrorComponent error={mockError} reset={mockReset} />)
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
  })

  it('should render authentication error', () => {
    const mockError = new Error('Unauthorized access')
    const mockReset = jest.fn()

    render(<ErrorComponent error={mockError} reset={mockReset} />)
    expect(screen.getByText('Authentication Error')).toBeInTheDocument()
    expect(screen.getByText('Sign In Again')).toBeInTheDocument()
  })

  it('should log error to Sentry with dashboard tag', () => {
    const mockError = new Error('Test error for Sentry')
    const mockReset = jest.fn()

    render(<ErrorComponent error={mockError} reset={mockReset} />)
    expect(window.Sentry.captureException).toHaveBeenCalledWith(mockError, {
      tags: { app: 'dashboard' }
    })
  })

  it('should call reset when Try Again is clicked', () => {
    const mockError = new Error('Test error')
    const mockReset = jest.fn()

    render(<ErrorComponent error={mockError} reset={mockReset} />)
    const tryAgainButton = screen.getByText('Try Again')
    tryAgainButton.click()
    expect(mockReset).toHaveBeenCalled()
  })

  // TODO(janua-tests): STALE TEST (environment drift). Stubbing navigation via
  // `delete window.location` stopped working when jest 30 brought jsdom 26,
  // where window.location is non-configurable. The assertion is sound; the
  // technique is not. Rewrite against a navigation seam the test can observe.
  it.skip('should navigate to sign-in for auth errors', () => {
    const mockError = new Error('unauthorized')
    const mockReset = jest.fn()
    const originalLocation = window.location

    delete window.location
    window.location = { href: '' } as any

    render(<ErrorComponent error={mockError} reset={mockReset} />)
    const signInButton = screen.getByText('Sign In Again')
    signInButton.click()
    expect(window.location.href).toBe('/sign-in')

    window.location = originalLocation
  })

  // TODO(janua-tests): STALE TEST (environment drift). Same jsdom 26
  // non-configurable window.location problem as the test above.
  it.skip('should navigate to dashboard for non-auth errors', () => {
    const mockError = new Error('General error')
    const mockReset = jest.fn()
    const originalLocation = window.location

    delete window.location
    window.location = { href: '' } as any

    render(<ErrorComponent error={mockError} reset={mockReset} />)
    const goToDashboardButton = screen.getByText('Go to Dashboard')
    goToDashboardButton.click()
    expect(window.location.href).toBe('/')

    window.location = originalLocation
  })

  it('should display error message in development mode', () => {
    const originalEnv = process.env.NODE_ENV
    process.env.NODE_ENV = 'development'
    const mockError = new Error('Development error message')
    mockError.digest = 'error-digest-123'
    const mockReset = jest.fn()

    render(<ErrorComponent error={mockError} reset={mockReset} />)
    expect(screen.getByText('Development error message')).toBeInTheDocument()
    expect(screen.getByText(/Error ID: error-digest-123/)).toBeInTheDocument()

    process.env.NODE_ENV = originalEnv
  })
})
