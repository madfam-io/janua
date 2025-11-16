'use client'

import { PlintoProvider } from './providers/plinto-provider'

export function Providers({ children }: { children: React.ReactNode }) {
  return <PlintoProvider>{children}</PlintoProvider>
}