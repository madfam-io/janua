import { Shield, CreditCard, Server, Mail } from 'lucide-react'
import type { SecretCategory } from './types'

export const CATEGORY_ICONS: Record<SecretCategory, React.ReactNode> = {
  authentication: <Shield className="h-4 w-4" />,
  payment: <CreditCard className="h-4 w-4" />,
  infrastructure: <Server className="h-4 w-4" />,
  email: <Mail className="h-4 w-4" />,
}

export const CATEGORY_LABELS: Record<SecretCategory, string> = {
  authentication: 'Authentication',
  payment: 'Payment',
  infrastructure: 'Infrastructure',
  email: 'Email',
}
