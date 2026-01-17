'use client'

/**
 * Re-export RoleBadge from @janua/ui shared library
 * This file exists for backward compatibility with existing imports
 */

import { RoleBadge as SharedRoleBadge } from '@janua/ui'
import type { UserRole } from './types'

export function RoleBadge({ role }: { role: UserRole }) {
  return <SharedRoleBadge role={role} />
}
