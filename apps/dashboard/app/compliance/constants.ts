import { CheckCircle2, Clock, XCircle } from 'lucide-react'
import type { DataSubjectRightType } from './types'

export const REQUEST_TYPES: Array<{
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

export const STATUS_CONFIG = {
  pending: { icon: Clock, color: 'text-yellow-600 dark:text-yellow-400', badge: 'secondary' as const, label: 'Pending' },
  approved: { icon: CheckCircle2, color: 'text-primary', badge: 'default' as const, label: 'Approved' },
  completed: { icon: CheckCircle2, color: 'text-green-600 dark:text-green-400', badge: 'default' as const, label: 'Completed' },
  rejected: { icon: XCircle, color: 'text-destructive', badge: 'destructive' as const, label: 'Rejected' },
}

export const DEFAULT_PRIVACY_PREFERENCES = {
  analytics: false,
  marketing: false,
  third_party_sharing: false,
  profile_visibility: 'organization' as const,
  email_notifications: true,
  activity_tracking: false,
  cookie_consent: false,
}

export const PROFILE_VISIBILITY_OPTIONS = [
  { value: 'public', label: 'Public', description: 'Anyone can view' },
  { value: 'organization', label: 'Organization Only', description: 'Only org members' },
  { value: 'private', label: 'Private', description: 'Only you' },
]
