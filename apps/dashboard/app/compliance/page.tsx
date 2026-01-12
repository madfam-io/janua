'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@janua/ui'
import { Button } from '@janua/ui'
import { Badge } from '@janua/ui'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@janua/ui'
import Link from 'next/link'
import {
  FileCheck,
  ArrowLeft,
  Shield,
  Download,
  FileText,
  Settings,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Clock,
  XCircle,
  RefreshCw,
} from 'lucide-react'
import { apiCall } from '../../lib/auth'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.janua.dev'

type DataSubjectRightType =
  | 'access'
  | 'erasure'
  | 'rectification'
  | 'restriction'
  | 'portability'
  | 'objection'

interface DataSubjectRequest {
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

interface ConsentRecord {
  id: string
  user_id: string
  purpose: string
  granted: boolean
  legal_basis: string
  purpose_description: string
  consent_method: string
  granted_at?: string
  withdrawn_at?: string
  version: string
}

interface PrivacyPreferences {
  analytics: boolean
  marketing: boolean
  third_party_sharing: boolean
  profile_visibility: 'public' | 'private' | 'organization'
  email_notifications: boolean
  activity_tracking: boolean
  data_retention_override?: number
  cookie_consent: boolean
}

interface UserData {
  id: string
  email: string
}

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

const statusConfig = {
  pending: { icon: Clock, color: 'text-yellow-500', badge: 'secondary' as const, label: 'Pending' },
  approved: { icon: CheckCircle2, color: 'text-blue-500', badge: 'default' as const, label: 'Approved' },
  completed: { icon: CheckCircle2, color: 'text-green-500', badge: 'default' as const, label: 'Completed' },
  rejected: { icon: XCircle, color: 'text-red-500', badge: 'destructive' as const, label: 'Rejected' },
}

export default function CompliancePage() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [user, setUser] = useState<UserData | null>(null)
  const [requests, setRequests] = useState<DataSubjectRequest[]>([])
  const [consents, setConsents] = useState<ConsentRecord[]>([])
  const [preferences, setPreferences] = useState<Partial<PrivacyPreferences>>({})
  const [submitting, setSubmitting] = useState(false)
  const [activeTab, setActiveTab] = useState('privacy')

  // DSR Form State
  const [dsrType, setDsrType] = useState<DataSubjectRightType>('access')
  const [dsrReason, setDsrReason] = useState('')

  // Privacy Settings State
  const [localPrefs, setLocalPrefs] = useState<PrivacyPreferences>({
    analytics: false,
    marketing: false,
    third_party_sharing: false,
    profile_visibility: 'organization',
    email_notifications: true,
    activity_tracking: false,
    cookie_consent: false,
  })

  useEffect(() => {
    fetchData()
  }, [])

  useEffect(() => {
    if (preferences) {
      setLocalPrefs({
        analytics: preferences.analytics ?? false,
        marketing: preferences.marketing ?? false,
        third_party_sharing: preferences.third_party_sharing ?? false,
        profile_visibility: preferences.profile_visibility ?? 'organization',
        email_notifications: preferences.email_notifications ?? true,
        activity_tracking: preferences.activity_tracking ?? false,
        data_retention_override: preferences.data_retention_override,
        cookie_consent: preferences.cookie_consent ?? false,
      })
    }
  }, [preferences])

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)

      // Fetch current user
      const meResponse = await apiCall(`${API_BASE_URL}/api/v1/auth/me`)
      if (!meResponse.ok) throw new Error('Failed to fetch user info')
      const userData = await meResponse.json()
      setUser(userData)

      // Fetch DSR requests
      try {
        const requestsResponse = await apiCall(`${API_BASE_URL}/api/v1/compliance/data-subject-requests`)
        if (requestsResponse.ok) {
          const requestsData = await requestsResponse.json()
          setRequests(Array.isArray(requestsData) ? requestsData : requestsData.requests || [])
        }
      } catch {
        // API might not exist yet
        setRequests([])
      }

      // Fetch consent records
      try {
        const consentsResponse = await apiCall(`${API_BASE_URL}/api/v1/compliance/consent`)
        if (consentsResponse.ok) {
          const consentsData = await consentsResponse.json()
          setConsents(Array.isArray(consentsData) ? consentsData : consentsData.consents || [])
        }
      } catch {
        setConsents([])
      }

      // Fetch privacy preferences
      try {
        const prefsResponse = await apiCall(`${API_BASE_URL}/api/v1/compliance/privacy-settings`)
        if (prefsResponse.ok) {
          const prefsData = await prefsResponse.json()
          setPreferences(prefsData.preferences || prefsData || {})
        }
      } catch {
        setPreferences({})
      }
    } catch (err) {
      console.error('Failed to fetch compliance data:', err)
      setError(err instanceof Error ? err.message : 'Failed to load compliance data')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmitDSR = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!user) return

    setSubmitting(true)
    try {
      const response = await apiCall(`${API_BASE_URL}/api/v1/compliance/data-subject-requests`, {
        method: 'POST',
        body: JSON.stringify({
          user_id: user.id,
          request_type: dsrType,
          reason: dsrReason || undefined,
          email: user.email,
          verification_method: 'email',
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to submit request')
      }

      setDsrReason('')
      fetchData()
      alert('Your request has been submitted. We will respond within 30 days as required by GDPR.')
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to submit request')
    } finally {
      setSubmitting(false)
    }
  }

  const handleSavePrivacySettings = async () => {
    if (!user) return

    setSubmitting(true)
    try {
      const response = await apiCall(`${API_BASE_URL}/api/v1/compliance/privacy-settings`, {
        method: 'PUT',
        body: JSON.stringify({
          user_id: user.id,
          preferences: localPrefs,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to save settings')
      }

      setPreferences(localPrefs)
      alert('Privacy settings saved successfully')
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to save settings')
    } finally {
      setSubmitting(false)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-muted-foreground" />
          <p className="mt-2 text-sm text-muted-foreground">Loading compliance data...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Link href="/settings" className="text-muted-foreground hover:text-foreground">
                <ArrowLeft className="h-5 w-5" />
              </Link>
              <FileCheck className="h-8 w-8 text-primary" />
              <div>
                <h1 className="text-2xl font-bold">Privacy & Compliance</h1>
                <p className="text-sm text-muted-foreground">
                  Manage your privacy settings and exercise your data rights
                </p>
              </div>
            </div>
            <Badge variant="secondary">GDPR Compliant</Badge>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {error && (
          <Card className="border-destructive mb-6">
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 text-destructive">
                <AlertCircle className="h-5 w-5" />
                <span>{error}</span>
              </div>
            </CardContent>
          </Card>
        )}

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="privacy" className="flex items-center gap-2">
              <Settings className="h-4 w-4" />
              Privacy Settings
            </TabsTrigger>
            <TabsTrigger value="requests" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Data Requests
            </TabsTrigger>
            <TabsTrigger value="consent" className="flex items-center gap-2">
              <Shield className="h-4 w-4" />
              Consent Management
            </TabsTrigger>
          </TabsList>

          {/* Privacy Settings Tab */}
          <TabsContent value="privacy" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Privacy Settings</CardTitle>
                <CardDescription>
                  Control how your data is collected, used, and shared
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Data Collection */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold">Data Collection & Analytics</h3>

                  <div className="flex items-start justify-between space-x-4 rounded-lg border p-4">
                    <div className="flex-1">
                      <label className="font-medium">Analytics & Performance</label>
                      <p className="mt-1 text-sm text-muted-foreground">
                        Allow us to collect anonymous usage data to improve the product
                      </p>
                    </div>
                    <label className="relative inline-flex cursor-pointer items-center">
                      <input
                        type="checkbox"
                        checked={localPrefs.analytics}
                        onChange={(e) => setLocalPrefs({ ...localPrefs, analytics: e.target.checked })}
                        className="peer sr-only"
                      />
                      <div className="peer h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:bg-primary peer-checked:after:translate-x-full peer-checked:after:border-white"></div>
                    </label>
                  </div>

                  <div className="flex items-start justify-between space-x-4 rounded-lg border p-4">
                    <div className="flex-1">
                      <label className="font-medium">Activity Tracking</label>
                      <p className="mt-1 text-sm text-muted-foreground">
                        Track your activity for personalized recommendations
                      </p>
                    </div>
                    <label className="relative inline-flex cursor-pointer items-center">
                      <input
                        type="checkbox"
                        checked={localPrefs.activity_tracking}
                        onChange={(e) => setLocalPrefs({ ...localPrefs, activity_tracking: e.target.checked })}
                        className="peer sr-only"
                      />
                      <div className="peer h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:bg-primary peer-checked:after:translate-x-full peer-checked:after:border-white"></div>
                    </label>
                  </div>
                </div>

                {/* Marketing */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold">Marketing & Communications</h3>

                  <div className="flex items-start justify-between space-x-4 rounded-lg border p-4">
                    <div className="flex-1">
                      <label className="font-medium">Marketing Emails</label>
                      <p className="mt-1 text-sm text-muted-foreground">
                        Receive promotional emails and product updates
                      </p>
                    </div>
                    <label className="relative inline-flex cursor-pointer items-center">
                      <input
                        type="checkbox"
                        checked={localPrefs.marketing}
                        onChange={(e) => setLocalPrefs({ ...localPrefs, marketing: e.target.checked })}
                        className="peer sr-only"
                      />
                      <div className="peer h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:bg-primary peer-checked:after:translate-x-full peer-checked:after:border-white"></div>
                    </label>
                  </div>

                  <div className="flex items-start justify-between space-x-4 rounded-lg border p-4">
                    <div className="flex-1">
                      <label className="font-medium">Email Notifications</label>
                      <p className="mt-1 text-sm text-muted-foreground">
                        Receive important account and security notifications
                      </p>
                    </div>
                    <label className="relative inline-flex cursor-pointer items-center">
                      <input
                        type="checkbox"
                        checked={localPrefs.email_notifications}
                        onChange={(e) => setLocalPrefs({ ...localPrefs, email_notifications: e.target.checked })}
                        className="peer sr-only"
                      />
                      <div className="peer h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:bg-primary peer-checked:after:translate-x-full peer-checked:after:border-white"></div>
                    </label>
                  </div>
                </div>

                {/* Data Sharing */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold">Data Sharing</h3>

                  <div className="flex items-start justify-between space-x-4 rounded-lg border p-4">
                    <div className="flex-1">
                      <label className="font-medium">Third-Party Sharing</label>
                      <p className="mt-1 text-sm text-muted-foreground">
                        Allow sharing anonymized data with trusted partners
                      </p>
                    </div>
                    <label className="relative inline-flex cursor-pointer items-center">
                      <input
                        type="checkbox"
                        checked={localPrefs.third_party_sharing}
                        onChange={(e) => setLocalPrefs({ ...localPrefs, third_party_sharing: e.target.checked })}
                        className="peer sr-only"
                      />
                      <div className="peer h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:bg-primary peer-checked:after:translate-x-full peer-checked:after:border-white"></div>
                    </label>
                  </div>

                  <div className="space-y-2 rounded-lg border p-4">
                    <label className="font-medium">Profile Visibility</label>
                    <p className="text-sm text-muted-foreground">Control who can see your profile</p>
                    <div className="mt-3 space-y-2">
                      {[
                        { value: 'public', label: 'Public', description: 'Anyone can view' },
                        { value: 'organization', label: 'Organization Only', description: 'Only org members' },
                        { value: 'private', label: 'Private', description: 'Only you' },
                      ].map((option) => (
                        <label
                          key={option.value}
                          className={`flex cursor-pointer items-start space-x-3 rounded-lg border p-3 ${
                            localPrefs.profile_visibility === option.value
                              ? 'border-primary bg-primary/5'
                              : 'border-border hover:border-primary/50'
                          }`}
                        >
                          <input
                            type="radio"
                            name="profile_visibility"
                            value={option.value}
                            checked={localPrefs.profile_visibility === option.value}
                            onChange={(e) =>
                              setLocalPrefs({
                                ...localPrefs,
                                profile_visibility: e.target.value as 'public' | 'private' | 'organization',
                              })
                            }
                            className="mt-1 h-4 w-4"
                          />
                          <div>
                            <p className="font-medium">{option.label}</p>
                            <p className="text-sm text-muted-foreground">{option.description}</p>
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="flex justify-end border-t pt-4">
                  <Button onClick={handleSavePrivacySettings} disabled={submitting}>
                    {submitting ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      'Save Settings'
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Data Requests Tab */}
          <TabsContent value="requests" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Exercise Your Data Rights</CardTitle>
                <CardDescription>
                  Under GDPR and privacy regulations, you have the right to control your personal data
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmitDSR} className="space-y-6">
                  <div className="space-y-2">
                    <label className="font-medium">Request Type</label>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {requestTypes.map((type) => (
                        <div
                          key={type.value}
                          className={`cursor-pointer rounded-lg border p-4 transition-colors ${
                            dsrType === type.value
                              ? 'border-primary bg-primary/5'
                              : 'border-border hover:border-primary/50'
                          }`}
                          onClick={() => setDsrType(type.value)}
                        >
                          <label className="flex cursor-pointer items-start space-x-3">
                            <input
                              type="radio"
                              name="requestType"
                              value={type.value}
                              checked={dsrType === type.value}
                              onChange={(e) => setDsrType(e.target.value as DataSubjectRightType)}
                              className="mt-1 h-4 w-4"
                            />
                            <div className="flex-1">
                              <div className="flex items-center justify-between">
                                <span className="font-medium">{type.label}</span>
                                <span className="text-xs text-muted-foreground">{type.gdprArticle}</span>
                              </div>
                              <p className="mt-1 text-sm text-muted-foreground">{type.description}</p>
                            </div>
                          </label>
                        </div>
                      ))}
                    </div>
                  </div>

                  {dsrType !== 'access' && (
                    <div className="space-y-2">
                      <label className="font-medium">Reason for Request</label>
                      <textarea
                        value={dsrReason}
                        onChange={(e) => setDsrReason(e.target.value)}
                        placeholder="Please provide details about your request..."
                        rows={4}
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                    </div>
                  )}

                  <div className="rounded-lg border border-blue-200 bg-blue-50 dark:bg-blue-950 dark:border-blue-800 p-4">
                    <h4 className="text-sm font-semibold text-blue-800 dark:text-blue-200">What happens next?</h4>
                    <ul className="mt-2 space-y-1 text-sm text-blue-700 dark:text-blue-300">
                      <li>• We'll verify your identity via email</li>
                      <li>• Your request will be reviewed within 30 days (GDPR requirement)</li>
                      <li>• You'll receive email updates on the status</li>
                    </ul>
                  </div>

                  <div className="flex justify-end">
                    <Button type="submit" disabled={submitting}>
                      {submitting ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Submitting...
                        </>
                      ) : (
                        <>
                          <FileText className="h-4 w-4 mr-2" />
                          Submit Request
                        </>
                      )}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>

            {/* Request History */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Request History</CardTitle>
                    <CardDescription>Track the status of your data requests</CardDescription>
                  </div>
                  <Button variant="outline" size="sm" onClick={fetchData}>
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {requests.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No data requests submitted yet</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {requests.map((request) => {
                      const config = statusConfig[request.status]
                      const StatusIcon = config.icon
                      const type = requestTypes.find((t) => t.value === request.request_type)

                      return (
                        <div key={request.id} className="flex items-center justify-between p-4 border rounded-lg">
                          <div className="flex items-center gap-4">
                            <div className={`p-2 rounded-full bg-muted`}>
                              <StatusIcon className={`h-4 w-4 ${config.color}`} />
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="font-medium">{type?.label || request.request_type}</span>
                                <Badge variant={config.badge}>{config.label}</Badge>
                              </div>
                              <div className="text-sm text-muted-foreground">
                                Submitted {formatDate(request.requested_at)}
                                {request.completed_at && (
                                  <> &bull; Completed {formatDate(request.completed_at)}</>
                                )}
                              </div>
                              {request.response_message && (
                                <p className="mt-1 text-sm">{request.response_message}</p>
                              )}
                            </div>
                          </div>
                          {request.data_export_url && request.status === 'completed' && (
                            <Button variant="outline" size="sm" asChild>
                              <a href={request.data_export_url} target="_blank" rel="noopener noreferrer">
                                <Download className="h-4 w-4 mr-1" />
                                Download
                              </a>
                            </Button>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Consent Management Tab */}
          <TabsContent value="consent" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Consent Records</CardTitle>
                <CardDescription>
                  View and manage your consent preferences for data processing purposes
                </CardDescription>
              </CardHeader>
              <CardContent>
                {consents.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Shield className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No consent records found</p>
                    <p className="text-sm mt-2">
                      Your consent preferences will appear here once you interact with consent prompts
                    </p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {consents.map((consent) => (
                      <div
                        key={consent.id}
                        className={`flex items-center justify-between p-4 border rounded-lg ${
                          consent.granted ? 'border-green-200 bg-green-50 dark:bg-green-950 dark:border-green-800' : 'border-border'
                        }`}
                      >
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{consent.purpose_description || consent.purpose}</span>
                            <Badge variant={consent.granted ? 'default' : 'outline'}>
                              {consent.granted ? 'Granted' : 'Withdrawn'}
                            </Badge>
                          </div>
                          <div className="text-sm text-muted-foreground mt-1">
                            Legal basis: {consent.legal_basis}
                            {consent.granted && consent.granted_at && (
                              <> &bull; Granted {formatDate(consent.granted_at)}</>
                            )}
                            {!consent.granted && consent.withdrawn_at && (
                              <> &bull; Withdrawn {formatDate(consent.withdrawn_at)}</>
                            )}
                          </div>
                        </div>
                        {consent.granted && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={async () => {
                              try {
                                const response = await apiCall(
                                  `${API_BASE_URL}/api/v1/compliance/consent/${consent.purpose}`,
                                  {
                                    method: 'DELETE',
                                    body: JSON.stringify({ user_id: user?.id }),
                                  }
                                )
                                if (!response.ok) throw new Error('Failed to withdraw consent')
                                fetchData()
                              } catch (err) {
                                alert(err instanceof Error ? err.message : 'Failed to withdraw consent')
                              }
                            }}
                          >
                            Withdraw
                          </Button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Your Rights */}
            <Card>
              <CardHeader>
                <CardTitle>Your Privacy Rights</CardTitle>
                <CardDescription>Understanding your rights under GDPR and privacy laws</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div className="flex items-start space-x-2">
                    <span className="text-primary font-bold">•</span>
                    <p>
                      <strong>Right to Access:</strong> Request a copy of all data we hold about you
                    </p>
                  </div>
                  <div className="flex items-start space-x-2">
                    <span className="text-primary font-bold">•</span>
                    <p>
                      <strong>Right to Erasure:</strong> Request deletion of your personal data
                    </p>
                  </div>
                  <div className="flex items-start space-x-2">
                    <span className="text-primary font-bold">•</span>
                    <p>
                      <strong>Right to Portability:</strong> Export your data in a machine-readable format
                    </p>
                  </div>
                  <div className="flex items-start space-x-2">
                    <span className="text-primary font-bold">•</span>
                    <p>
                      <strong>Right to Rectification:</strong> Request correction of inaccurate data
                    </p>
                  </div>
                  <div className="flex items-start space-x-2">
                    <span className="text-primary font-bold">•</span>
                    <p>
                      <strong>Right to Object:</strong> Object to processing of your data
                    </p>
                  </div>
                  <div className="flex items-start space-x-2">
                    <span className="text-primary font-bold">•</span>
                    <p>
                      <strong>Right to Restriction:</strong> Restrict processing of your data
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
