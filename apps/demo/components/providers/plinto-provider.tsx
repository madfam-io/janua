'use client'

/**
 * Plinto SDK Provider
 *
 * This component wraps the Next.js app and provides the Plinto SDK client
 * to all child components via React Context. It also handles authentication
 * state management and automatic token refresh.
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { plintoClient } from '@/lib/plinto-client'
import type { PlintoClient, User } from '@plinto/typescript-sdk'

interface PlintoContextValue {
  client: PlintoClient
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  refreshUser: () => Promise<void>
}

const PlintoContext = createContext<PlintoContextValue | undefined>(undefined)

export function PlintoProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const refreshUser = useCallback(async () => {
    try {
      const currentUser = await plintoClient.getCurrentUser()
      setUser(currentUser)
    } catch (error) {
      console.error('Failed to fetch user:', error)
      setUser(null)
    }
  }, [])

  useEffect(() => {
    // Initialize authentication state
    const initAuth = async () => {
      setIsLoading(true)
      await refreshUser()
      setIsLoading(false)
    }

    initAuth()

    // Set up event listeners for auth state changes
    const handleSignIn = (userData: User) => {
      setUser(userData)
    }

    const handleSignOut = () => {
      setUser(null)
    }

    const handleTokenRefresh = () => {
      refreshUser()
    }

    plintoClient.on('signIn', handleSignIn)
    plintoClient.on('signOut', handleSignOut)
    plintoClient.on('tokenRefreshed', handleTokenRefresh)

    return () => {
      plintoClient.off('signIn', handleSignIn)
      plintoClient.off('signOut', handleSignOut)
      plintoClient.off('tokenRefreshed', handleTokenRefresh)
    }
  }, [refreshUser])

  const value: PlintoContextValue = {
    client: plintoClient,
    user,
    isAuthenticated: !!user,
    isLoading,
    refreshUser,
  }

  return <PlintoContext.Provider value={value}>{children}</PlintoContext.Provider>
}

// Custom hook to use Plinto SDK
export function usePlinto() {
  const context = useContext(PlintoContext)
  if (context === undefined) {
    throw new Error('usePlinto must be used within a PlintoProvider')
  }
  return context
}

// Export auth-specific hook for convenience
export function useAuth() {
  const { user, isAuthenticated, isLoading, refreshUser } = usePlinto()
  return { user, isAuthenticated, isLoading, refreshUser }
}
