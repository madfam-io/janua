import * as React from 'react'
import { Button } from '../button'
import { cn } from '../../lib/utils'

export interface InvitationValidateResponse {
  valid: boolean
  reason?: string
  email?: string
  organization_id?: string
  organization_name?: string
  role?: string
  expires_at?: string
  message?: string
}

export interface InvitationAcceptRequest {
  token: string
  user_id?: string
  name?: string
  password?: string
}

export interface InvitationAcceptResponse {
  success: boolean
  user_id: string
  organization_id: string
  message: string
  is_new_user: boolean
}

export interface InvitationAcceptProps {
  className?: string
  token: string
  onValidateToken?: (token: string) => Promise<InvitationValidateResponse>
  onAccept?: (request: InvitationAcceptRequest) => Promise<InvitationAcceptResponse>
  onSuccess?: (response: InvitationAcceptResponse) => void
  onError?: (error: Error) => void
  januaClient?: any
  apiUrl?: string
  redirectUrl?: string
  currentUserId?: string
}

/**
 * Generate a cryptographically secure random string for security-sensitive operations
 * Uses crypto.getRandomValues for browser compatibility
 */
function generateSecureToken(): string {
  const array = new Uint8Array(16);
  crypto.getRandomValues(array);
  return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
}

export function InvitationAccept({
  className,
  token,
  onValidateToken,
  onAccept,
  onSuccess,
  onError,
  januaClient,
  apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  redirectUrl = '/dashboard',
  currentUserId,
}: InvitationAcceptProps) {
  const [isValidating, setIsValidating] = React.useState(true)
  const [isSubmitting, setIsSubmitting] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [validationData, setValidationData] = React.useState<InvitationValidateResponse | null>(null)
  const [isNewUser, setIsNewUser] = React.useState(!currentUserId)
  const [name, setName] = React.useState('')
  const [password, setPassword] = React.useState('')
  const [confirmPassword, setConfirmPassword] = React.useState('')
  // Generate a secure request ID for tracking
  const [_requestId] = React.useState(() => generateSecureToken())

  // Validate token on mount
  React.useEffect(() => {
    const validate = async () => {
      setIsValidating(true)
      setError(null)

      try {
        let response: InvitationValidateResponse

        if (januaClient) {
          response = await januaClient.invitations.validateToken(token)
        } else if (onValidateToken) {
          response = await onValidateToken(token)
        } else {
          const res = await fetch(`${apiUrl}/api/v1/invitations/validate/${token}`, {
            credentials: 'include',
          })

          if (!res.ok) {
            throw new Error('Failed to validate invitation token')
          }

          response = await res.json()
        }

        setValidationData(response)

        if (!response.valid) {
          setError(response.reason || 'This invitation is not valid')
        }
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to validate invitation')
        setError(error.message)
        onError?.(error)
      } finally {
        setIsValidating(false)
      }
    }

    validate()
  }, [token, januaClient, onValidateToken, apiUrl, onError])

  // Handle accept
  const handleAccept = async (e: React.FormEvent) => {
    e.preventDefault()

    // Validation for new users
    if (isNewUser) {
      if (!name || name.trim().length === 0) {
        setError('Please enter your name')
        return
      }

      if (!password || password.length < 8) {
        setError('Password must be at least 8 characters')
        return
      }

      if (password !== confirmPassword) {
        setError('Passwords do not match')
        return
      }
    }

    setIsSubmitting(true)
    setError(null)

    try {
      const acceptData: InvitationAcceptRequest = {
        token,
        user_id: currentUserId,
      }

      if (isNewUser) {
        acceptData.name = name.trim()
        acceptData.password = password
      }

      let response: InvitationAcceptResponse

      if (januaClient) {
        response = await januaClient.invitations.acceptInvitation(acceptData)
      } else if (onAccept) {
        response = await onAccept(acceptData)
      } else {
        const res = await fetch(`${apiUrl}/api/v1/invitations/accept`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(acceptData),
        })

        if (!res.ok) {
          const errorData = await res.json().catch(() => ({}))
          throw new Error(errorData.detail || 'Failed to accept invitation')
        }

        response = await res.json()
      }

      onSuccess?.(response)

      // Redirect after success
      if (redirectUrl) {
        window.location.href = redirectUrl
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to accept invitation')
      setError(error.message)
      onError?.(error)
    } finally {
      setIsSubmitting(false)
    }
  }

  if (isValidating) {
    return (
      <div className={cn('p-8 text-center', className)}>
        <div className="animate-spin mx-auto w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full" />
        <p className="mt-4 text-muted-foreground">Validating invitation...</p>
      </div>
    )
  }

  if (!validationData?.valid) {
    return (
      <div className={cn('p-8 space-y-4', className)}>
        <div className="mx-auto w-16 h-16 rounded-full bg-red-100 dark:bg-red-900/20 flex items-center justify-center">
          <svg className="w-8 h-8 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
        <div className="text-center">
          <h3 className="text-lg font-semibold mb-2">Invalid Invitation</h3>
          <p className="text-muted-foreground">{error || 'This invitation link is not valid.'}</p>
        </div>
      </div>
    )
  }

  return (
    <div className={cn('max-w-md mx-auto space-y-6', className)}>
      {/* Invitation Details */}
      <div className="text-center space-y-2">
        <div className="mx-auto w-16 h-16 rounded-full bg-blue-100 dark:bg-blue-900/20 flex items-center justify-center">
          <svg className="w-8 h-8 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 19v-8.93a2 2 0 01.89-1.664l7-4.666a2 2 0 012.22 0l7 4.666A2 2 0 0121 10.07V19M3 19a2 2 0 002 2h14a2 2 0 002-2M3 19l6.75-4.5M21 19l-6.75-4.5M3 10l6.75 4.5M21 10l-6.75 4.5m0 0l-1.14.76a2 2 0 01-2.22 0l-1.14-.76" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold">You're Invited!</h2>
        <p className="text-muted-foreground">
          You've been invited to join <strong>{validationData.organization_name}</strong>
        </p>
      </div>

      {/* Invitation Info */}
      <div className="p-4 border rounded-lg space-y-2 bg-gray-50 dark:bg-gray-900">
        <div className="text-sm">
          <span className="font-medium">Email:</span> {validationData.email}
        </div>
        <div className="text-sm">
          <span className="font-medium">Role:</span>{' '}
          <span className="capitalize">{validationData.role}</span>
        </div>
        <div className="text-sm">
          <span className="font-medium">Expires:</span>{' '}
          {validationData.expires_at && new Date(validationData.expires_at).toLocaleDateString()}
        </div>
        {validationData.message && (
          <div className="text-sm pt-2 border-t">
            <span className="font-medium">Message:</span>
            <p className="mt-1 text-muted-foreground italic">"{validationData.message}"</p>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 border border-red-200 bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200 rounded-md text-sm">
          {error}
        </div>
      )}

      {/* Accept Form */}
      <form onSubmit={handleAccept} className="space-y-4">
        {/* User Type Toggle */}
        {!currentUserId && (
          <div className="flex gap-2 p-1 bg-gray-100 dark:bg-gray-800 rounded-lg">
            <button
              type="button"
              onClick={() => setIsNewUser(true)}
              className={cn(
                'flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors',
                isNewUser
                  ? 'bg-white dark:bg-gray-900 shadow'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              Create Account
            </button>
            <button
              type="button"
              onClick={() => setIsNewUser(false)}
              className={cn(
                'flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors',
                !isNewUser
                  ? 'bg-white dark:bg-gray-900 shadow'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              Sign In
            </button>
          </div>
        )}

        {/* New User Fields */}
        {isNewUser ? (
          <>
            <div className="space-y-2">
              <label htmlFor="name" className="block text-sm font-medium">
                Full Name <span className="text-red-500">*</span>
              </label>
              <input
                id="name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="John Doe"
                required
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="password" className="block text-sm font-medium">
                Password <span className="text-red-500">*</span>
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Minimum 8 characters"
                required
                minLength={8}
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="confirmPassword" className="block text-sm font-medium">
                Confirm Password <span className="text-red-500">*</span>
              </label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter password"
                required
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>

            <Button type="submit" disabled={isSubmitting} className="w-full">
              {isSubmitting ? 'Creating Account...' : 'Accept & Create Account'}
            </Button>
          </>
        ) : (
          <>
            <p className="text-sm text-muted-foreground">
              {currentUserId
                ? 'Click below to accept this invitation and join the organization.'
                : 'Please sign in to your existing account to accept this invitation.'}
            </p>

            {currentUserId ? (
              <Button type="submit" disabled={isSubmitting} className="w-full">
                {isSubmitting ? 'Accepting...' : 'Accept Invitation'}
              </Button>
            ) : (
              <Button
                type="button"
                onClick={() => (window.location.href = `/auth/signin?redirect=/accept-invitation?token=${token}`)}
                className="w-full"
              >
                Sign In to Accept
              </Button>
            )}
          </>
        )}
      </form>
    </div>
  )
}
