'use client'

import { Badge } from '@janua/ui'
import type { UserRole } from './types'

const roleConfig = {
  owner: { className: 'badge-owner', label: 'Owner' },
  admin: { className: 'badge-admin', label: 'Admin' },
  member: { className: 'badge-member', label: 'Member' },
  viewer: { className: 'badge-viewer', label: 'Viewer' },
}

export function RoleBadge({ role }: { role: UserRole }) {
  const config = roleConfig[role]

  return (
    <Badge variant="outline" className={config.className}>
      {config.label}
    </Badge>
  )
}
