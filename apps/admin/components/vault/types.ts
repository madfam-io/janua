// Vault types

export type SecretCategory = 'authentication' | 'payment' | 'infrastructure' | 'email'
export type SecretStatus = 'active' | 'rotating' | 'expired' | 'revoked'

export interface MaskedSecret {
  id: string
  name: string
  maskedValue: string
  fullValue?: string // Only populated when revealed
  category: SecretCategory
  status: SecretStatus
  lastRotated: Date
  nextRotation: Date
  dependentServices: string[]
  description?: string
}
