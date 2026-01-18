'use client'

import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import {
  Users,
  Building2,
  Shield,
  Server,
  Activity,
  Settings,
  BarChart3,
  Loader2,
  KeyRound
} from 'lucide-react'
import { useAuth } from '@/lib/auth'
import {
  OverviewSection,
  TenantsSection,
  UsersSection,
  VaultSection,
  InfrastructureSection,
  ActivitySection,
  SecuritySection,
  SettingsSection,
} from '@/components/sections'

const sections = [
  { id: 'overview', label: 'Overview', icon: BarChart3 },
  { id: 'tenants', label: 'Tenants', icon: Building2 },
  { id: 'users', label: 'All Users', icon: Users },
  { id: 'vault', label: 'Ecosystem Vault', icon: KeyRound },
  { id: 'infrastructure', label: 'Infrastructure', icon: Server },
  { id: 'activity', label: 'Activity', icon: Activity },
  { id: 'security', label: 'Security', icon: Shield },
  { id: 'settings', label: 'Settings', icon: Settings },
]

function AdminPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { user, isAuthenticated, isLoading: authLoading, logout, checkSession } = useAuth()
  const [isCheckingSession, setIsCheckingSession] = useState(true)

  // Get section from URL or default to 'overview'
  const sectionFromUrl = searchParams.get('section') || 'overview'
  const validSections = sections.map(s => s.id)
  const activeSection = validSections.includes(sectionFromUrl) ? sectionFromUrl : 'overview'

  // Navigate to section by updating URL
  const setActiveSection = (sectionId: string) => {
    router.push(`/?section=${sectionId}`, { scroll: false })
  }

  // On mount, check for existing SSO session via cookies
  useEffect(() => {
    const checkExistingSession = async () => {
      if (checkSession) {
        try {
          const hasSession = await checkSession()
          if (hasSession) {
            setIsCheckingSession(false)
            return
          }
        } catch {
          // No valid session
        }
      }
      setIsCheckingSession(false)
    }
    checkExistingSession()
  }, [checkSession])

  // Redirect to /login if not authenticated (after loading completes)
  useEffect(() => {
    if (!authLoading && !isCheckingSession && !isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, authLoading, isCheckingSession, router])

  if (authLoading || isCheckingSession) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Checking session...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Redirecting to login...</p>
        </div>
      </div>
    )
  }

  const renderSection = () => {
    switch (activeSection) {
      case 'overview': return <OverviewSection />
      case 'tenants': return <TenantsSection />
      case 'users': return <UsersSection />
      case 'vault': return <VaultSection />
      case 'infrastructure': return <InfrastructureSection />
      case 'activity': return <ActivitySection />
      case 'security': return <SecuritySection />
      case 'settings': return <SettingsSection />
      default: return <OverviewSection />
    }
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-card border-b border-border">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="p-2 bg-destructive/10 rounded-lg">
                <Shield className="h-6 w-6 text-destructive" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-foreground">Janua Superadmin</h1>
                <p className="text-sm text-muted-foreground">Internal Platform Management</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <span className="px-3 py-1 bg-destructive/10 text-destructive text-xs font-medium rounded-full">
                INTERNAL ONLY
              </span>
              <div className="text-sm text-muted-foreground">
                {user?.email}
              </div>
              <button
                onClick={logout}
                className="text-sm text-muted-foreground hover:text-foreground"
              >
                Sign Out
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside className="w-64 bg-card border-r border-border min-h-screen">
          <nav className="p-4 space-y-1">
            {sections.map((section) => {
              const Icon = section.icon
              return (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors ${
                    activeSection === section.id
                      ? 'bg-primary/10 text-primary'
                      : 'text-muted-foreground hover:bg-muted'
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  <span className="text-sm font-medium">{section.label}</span>
                </button>
              )
            })}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6">
          {renderSection()}
        </main>
      </div>
    </div>
  )
}

export default function AdminPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    }>
      <AdminPageContent />
    </Suspense>
  )
}
