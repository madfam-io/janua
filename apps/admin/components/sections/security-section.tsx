'use client'

import { useState } from 'react'
import { adminAPI } from '@/lib/admin-api'

export function SecuritySection() {
  const [revoking, setRevoking] = useState(false)

  const handleRevokeAllSessions = async () => {
    if (!confirm('Are you sure you want to revoke ALL user sessions? This will log out everyone.')) {
      return
    }
    setRevoking(true)
    try {
      await adminAPI.revokeAllSessions()
      alert('All sessions revoked successfully')
    } catch (err) {
      alert('Failed to revoke sessions')
    } finally {
      setRevoking(false)
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-foreground">Security & Compliance</h2>

      <div className="bg-card p-6 rounded-lg border border-border">
        <h3 className="text-lg font-semibold mb-4 text-foreground">Emergency Actions</h3>
        <div className="space-y-4">
          <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
            <h4 className="font-medium text-destructive">Revoke All Sessions</h4>
            <p className="text-sm text-destructive/80 mt-1">
              This will immediately log out all users from the platform.
            </p>
            <button
              onClick={handleRevokeAllSessions}
              disabled={revoking}
              className="mt-3 px-4 py-2 bg-destructive text-destructive-foreground rounded-lg hover:bg-destructive/90 disabled:opacity-50"
            >
              {revoking ? 'Revoking...' : 'Revoke All Sessions'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
