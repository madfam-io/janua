'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Sidebar } from './sidebar'
import { getAuthToken, clearAuthCookie, USER_KEY } from '@/lib/auth-storage'

interface DashboardLayoutProps {
  children: React.ReactNode
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const router = useRouter()
  const [user, setUser] = useState<{ name?: string; email?: string } | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const token = getAuthToken()
        if (!token) {
          router.push('/login')
          return
        }

        const storedUser = localStorage.getItem(USER_KEY)
        if (storedUser) {
          setUser(JSON.parse(storedUser))
        }

        setIsLoading(false)
      } catch (error) {
        console.error('Failed to initialize auth:', error)
        router.push('/login')
      }
    }

    initializeAuth()
  }, [router])


  const handleLogout = () => {
    clearAuthCookie()
    localStorage.removeItem(USER_KEY)
    router.push('/login')
  }

  if (isLoading) {
    return (
      <div className="bg-background flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="border-primary mx-auto mb-4 size-8 animate-spin rounded-full border-b-2"></div>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-background flex h-screen overflow-hidden">
      <Sidebar user={user || undefined} onLogout={handleLogout} />
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  )
}
