'use client'

/**
 * Re-export StatusBadge from @janua/ui shared library
 * Customized for vault secrets with Solarpunk styling
 */

import { StatusBadge as SharedStatusBadge, type StatusConfigMap } from '@janua/ui'
import type { SecretStatus } from './types'

// Custom config for vault secret status
const vaultStatusConfig: StatusConfigMap<SecretStatus> = {
  active: { label: 'Active', variant: 'success' },
  rotating: { label: 'Rotating', variant: 'info' },
  expired: { label: 'Expired', variant: 'warning' },
  revoked: { label: 'Revoked', variant: 'error' },
}

export function VaultStatusBadge({ status }: { status: SecretStatus }) {
  return (
    <SharedStatusBadge
      status={status}
      config={vaultStatusConfig}
      showIcon={false}
      className="font-mono text-xs"
    />
  )
}
