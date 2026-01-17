'use client'

import { useState, useEffect } from 'react'
import { Loader2 } from 'lucide-react'

export function VaultSection() {
  // Dynamic import to avoid SSR issues with the vault component
  const [VaultComponent, setVaultComponent] = useState<React.ComponentType | null>(null)

  useEffect(() => {
    import('@/components/vault/ecosystem-vault').then((mod) => {
      setVaultComponent(() => mod.EcosystemVault)
    })
  }, [])

  if (!VaultComponent) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return <VaultComponent />
}
