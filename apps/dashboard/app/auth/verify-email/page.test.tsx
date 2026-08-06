import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'

const mockVerifyEmail = jest.fn()

// Mock next/navigation
const mockSearchParams = new URLSearchParams()
jest.mock('next/navigation', () => ({
  useSearchParams: () => mockSearchParams,
}))

jest.mock('next/link', () => {
  return ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  )
})

// Mock @janua/ui
jest.mock('@janua/ui', () => ({
  Card: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CardContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CardDescription: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CardHeader: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CardTitle: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Button: ({ children, asChild, ...props }: any) =>
    asChild ? children : <button {...props}>{children}</button>,
}))

jest.mock('@/lib/janua-client', () => ({
  januaClient: {
    auth: {
      verifyEmail: (...args: unknown[]) => mockVerifyEmail(...args),
    },
  },
}))

import VerifyEmailPage from './page'

describe('VerifyEmailPage', () => {
  beforeEach(() => {
    mockVerifyEmail.mockReset()
    mockSearchParams.forEach((_, key) => mockSearchParams.delete(key))
  })

  it('shows an error state when no token is present in the URL', async () => {
    render(<VerifyEmailPage />)

    expect(await screen.findByText('Verification failed')).toBeInTheDocument()
    expect(mockVerifyEmail).not.toHaveBeenCalled()
  })

  it('verifies the token from the URL and shows success', async () => {
    mockSearchParams.set('token', 'valid-token')
    mockVerifyEmail.mockResolvedValue({ message: 'Email successfully verified' })

    render(<VerifyEmailPage />)

    await waitFor(() => expect(mockVerifyEmail).toHaveBeenCalledWith('valid-token'))
    expect(await screen.findByText('Email verified')).toBeInTheDocument()
  })

  it('shows an error state when verification fails', async () => {
    mockSearchParams.set('token', 'expired-token')
    mockVerifyEmail.mockRejectedValue(new Error('Invalid or expired verification token'))

    render(<VerifyEmailPage />)

    expect(await screen.findByText('Invalid or expired verification token')).toBeInTheDocument()
  })
})
