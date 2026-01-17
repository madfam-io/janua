// Compliance types

export type DataSubjectRightType =
  | 'access'
  | 'erasure'
  | 'rectification'
  | 'restriction'
  | 'portability'
  | 'objection'

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

export interface ConsentRecord {
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

export interface PrivacyPreferences {
  analytics: boolean
  marketing: boolean
  third_party_sharing: boolean
  profile_visibility: 'public' | 'private' | 'organization'
  email_notifications: boolean
  activity_tracking: boolean
  data_retention_override?: number
  cookie_consent: boolean
}

export interface UserData {
  id: string
  email: string
}
