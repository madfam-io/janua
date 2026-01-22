import * as React from 'react'
import { Button } from '../button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../card'
import { Input } from '../input'
import { Label } from '../label'
import { cn } from '../../lib/utils'

export type DataSubjectRightType =
  | 'access'
  | 'erasure'
  | 'rectification'
  | 'restriction'
  | 'portability'
  | 'objection'

export interface DataSubjectRequestCreate {
  user_id: string
  request_type: DataSubjectRightType
  reason?: string
  email?: string
  verification_method?: string
}

export interface DataSubjectRequest {
  id: string
  user_id: string
  request_type: DataSubjectRightType
  status: 'pending' | 'approved' | 'completed' | 'rejected'
  reason?: string
  requested_at: string
  processed_at?: string
  completed_at?: string
  response_message?: string
  data_export_url?: string
}

export interface DataSubjectRequestFormProps {
  className?: string
  userId: string
  userEmail?: string
  onSubmit?: (request: DataSubjectRequestCreate) => Promise<DataSubjectRequest>
  onSuccess?: (request: DataSubjectRequest) => void
  onCancel?: () => void
  onError?: (error: Error) => void
  januaClient?: any
  apiUrl?: string
  defaultRequestType?: DataSubjectRightType
  existingRequests?: DataSubjectRequest[]
}

/**
 * Validate email address using a safe regex pattern that avoids ReDoS.
 * This pattern is more restrictive but safe from catastrophic backtracking.
 */
function isValidEmail(email: string): boolean {
  // Simple email validation that avoids polynomial ReDoS
  // Validates: local-part@domain.tld format with reasonable restrictions
  if (!email || email.length > 254) return false

  const atIndex = email.indexOf('@')
  if (atIndex < 1 || atIndex > 64) return false

  const localPart = email.substring(0, atIndex)
  const domain = email.substring(atIndex + 1)

  if (!localPart || !domain || domain.length > 253) return false
  if (!domain.includes('.')) return false

  // Check for valid characters in local part (no consecutive dots, no leading/trailing dots)
  if (/^\.|\.$|\.\./.test(localPart)) return false

  // Check for valid characters in domain (letters, numbers, hyphens, dots)
  // Avoid complex nested quantifiers that cause ReDoS
  const domainParts = domain.split('.')
  for (const part of domainParts) {
    if (part.length === 0 || part.length > 63) return false
    if (/^-|-$/.test(part)) return false
    if (!/^[a-zA-Z0-9-]+$/.test(part)) return false
  }

  // Last domain part must be at least 2 characters (TLD)
  const tld = domainParts[domainParts.length - 1]
  if (tld.length < 2) return false

  return true
}

export function DataSubjectRequestForm({
  className,
  userId,
  userEmail,
  onSubmit,
  onSuccess,
  onCancel,
  onError,
  januaClient,
  apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  defaultRequestType = 'access',
  existingRequests = [],
}: DataSubjectRequestFormProps) {
  const [requestType, setRequestType] = React.useState<DataSubjectRightType>(defaultRequestType)
  const [reason, setReason] = React.useState('')
  const [email, setEmail] = React.useState(userEmail || '')
  const [isSubmitting, setIsSubmitting] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [success, setSuccess] = React.useState(false)
  const [createdRequest, setCreatedRequest] = React.useState<DataSubjectRequest | null>(null)

  const requestTypes: Array<{
    value: DataSubjectRightType
    label: string
    description: string
    gdprArticle: string
  }> = [
    {
      value: 'access',
      label: 'Access My Data',
      description: 'Request a copy of all personal data we hold about you',
      gdprArticle: 'GDPR Article 15',
    },
    {
      value: 'erasure',
      label: 'Delete My Data',
      description: 'Request deletion of your personal data (Right to be Forgotten)',
      gdprArticle: 'GDPR Article 17',
    },
    {
      value: 'rectification',
      label: 'Correct My Data',
      description: 'Request correction of inaccurate or incomplete personal data',
      gdprArticle: 'GDPR Article 16',
    },
    {
      value: 'restriction',
      label: 'Restrict Processing',
      description: 'Request restriction of processing of your personal data',
      gdprArticle: 'GDPR Article 18',
    },
    {
      value: 'portability',
      label: 'Data Portability',
      description: 'Request your data in a structured, machine-readable format',
      gdprArticle: 'GDPR Article 20',
    },
    {
      value: 'objection',
      label: 'Object to Processing',
      description: 'Object to processing of your personal data',
      gdprArticle: 'GDPR Article 21',
    },
  ]

  const selectedType = requestTypes.find((t) => t.value === requestType)!

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(false)

    // Validation using safe email validation function
    if (!email || !isValidEmail(email)) {
      setError('Please enter a valid email address')
      return
    }

    if (!reason.trim() && requestType !== 'access') {
      setError('Please provide a reason for your request')
      return
    }

    setIsSubmitting(true)

    try {
      const requestData: DataSubjectRequestCreate = {
        user_id: userId,
        request_type: requestType,
        reason: reason.trim() || undefined,
        email: email.trim(),
        verification_method: 'email',
      }

      let request: DataSubjectRequest

      if (januaClient) {
        request = await januaClient.compliance.createDataSubjectRequest(requestData)
      } else if (onSubmit) {
        request = await onSubmit(requestData)
      } else {
        const res = await fetch(`${apiUrl}/api/v1/compliance/data-subject-requests`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(requestData),
        })

        if (!res.ok) {
          const data = await res.json()
          throw new Error(data.detail || 'Failed to submit request')
        }

        request = await res.json()
      }

      setCreatedRequest(request)
      setSuccess(true)
      onSuccess?.(request)

      // Reset form
      setReason('')
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to submit request'
      setError(errorMessage)
      onError?.(err instanceof Error ? err : new Error(errorMessage))
    } finally {
      setIsSubmitting(false)
    }
  }

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-800',
      approved: 'bg-blue-100 text-blue-800',
      completed: 'bg-green-100 text-green-800',
      rejected: 'bg-red-100 text-red-800',
    }
    return colors[status] || 'bg-gray-100 text-gray-800'
  }

  return (
    <div className={cn('space-y-6', className)}>
      <Card>
        <CardHeader>
          <CardTitle>Exercise Your Data Rights</CardTitle>
          <CardDescription>
            Under GDPR and privacy regulations, you have the right to control your personal data.
            Select the action you'd like to take below.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {success && createdRequest ? (
            <div className="space-y-4">
              <div className="rounded-lg border border-green-200 bg-green-50 p-4">
                <h3 className="font-semibold text-green-800">Request Submitted Successfully</h3>
                <p className="mt-2 text-sm text-green-700">
                  Your {selectedType.label.toLowerCase()} request has been submitted. We will
                  respond within 30 days as required by GDPR.
                </p>
                <div className="mt-4 space-y-2 text-sm">
                  <p>
                    <strong>Request ID:</strong> {createdRequest.id}
                  </p>
                  <p>
                    <strong>Status:</strong>{' '}
                    <span className={cn('rounded-full px-2 py-1', getStatusColor(createdRequest.status))}>
                      {createdRequest.status}
                    </span>
                  </p>
                  <p>
                    <strong>Submitted:</strong>{' '}
                    {new Date(createdRequest.requested_at).toLocaleString()}
                  </p>
                </div>
              </div>
              <Button onClick={() => setSuccess(false)} variant="outline" className="w-full">
                Submit Another Request
              </Button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <Label>Request Type</Label>
                <div className="space-y-3">
                  {requestTypes.map((type) => (
                    <div
                      key={type.value}
                      className={cn(
                        'cursor-pointer rounded-lg border p-4 transition-colors',
                        requestType === type.value
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      )}
                      onClick={() => setRequestType(type.value)}
                    >
                      <Label className="flex cursor-pointer items-start space-x-3">
                        <input
                          type="radio"
                          name="requestType"
                          value={type.value}
                          checked={requestType === type.value}
                          onChange={(e) => setRequestType(e.target.value as DataSubjectRightType)}
                          className="mt-1 h-4 w-4"
                        />
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <span className="font-medium">{type.label}</span>
                            <span className="text-xs text-gray-500">{type.gdprArticle}</span>
                          </div>
                          <p className="mt-1 text-sm text-gray-600">{type.description}</p>
                        </div>
                      </Label>
                    </div>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">Email Address</Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your@email.com"
                  required
                  disabled={isSubmitting}
                />
                <p className="text-xs text-gray-500">
                  We'll send confirmation and updates to this email
                </p>
              </div>

              {requestType !== 'access' && (
                <div className="space-y-2">
                  <Label htmlFor="reason">Reason for Request</Label>
                  <textarea
                    id="reason"
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="Please provide details about your request..."
                    rows={4}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    disabled={isSubmitting}
                  />
                  <p className="text-xs text-gray-500">
                    Providing details helps us process your request more efficiently
                  </p>
                </div>
              )}

              {error && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-4">
                  <p className="text-sm text-red-800">{error}</p>
                </div>
              )}

              <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
                <h4 className="text-sm font-semibold text-blue-800">What happens next?</h4>
                <ul className="mt-2 space-y-1 text-sm text-blue-700">
                  <li>• We'll verify your identity via email</li>
                  <li>• Your request will be reviewed within 30 days (GDPR requirement)</li>
                  <li>• You'll receive email updates on the status</li>
                  {requestType === 'access' && (
                    <li>• If approved, you'll receive a secure download link for your data</li>
                  )}
                  {requestType === 'erasure' && (
                    <li>• If approved, your data will be permanently deleted</li>
                  )}
                </ul>
              </div>
            </form>
          )}
        </CardContent>
        {!success && (
          <CardFooter className="flex justify-between">
            {onCancel && (
              <Button type="button" variant="outline" onClick={onCancel}>
                Cancel
              </Button>
            )}
            <Button onClick={handleSubmit} disabled={isSubmitting} className="ml-auto">
              {isSubmitting ? 'Submitting...' : 'Submit Request'}
            </Button>
          </CardFooter>
        )}
      </Card>

      {existingRequests.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Your Request History</CardTitle>
            <CardDescription>Track the status of your previous requests</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {existingRequests.map((request) => {
                const type = requestTypes.find((t) => t.value === request.request_type)
                return (
                  <div key={request.id} className="rounded-lg border p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2">
                          <h4 className="font-medium">{type?.label || request.request_type}</h4>
                          <span className={cn('rounded-full px-2 py-1 text-xs', getStatusColor(request.status))}>
                            {request.status}
                          </span>
                        </div>
                        <p className="mt-1 text-sm text-gray-600">
                          Submitted: {new Date(request.requested_at).toLocaleDateString()}
                        </p>
                        {request.response_message && (
                          <p className="mt-2 text-sm text-gray-700">{request.response_message}</p>
                        )}
                        {request.data_export_url && request.status === 'completed' && (
                          <a
                            href={request.data_export_url}
                            className="mt-2 inline-block text-sm text-blue-600 hover:underline"
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            Download Your Data →
                          </a>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
