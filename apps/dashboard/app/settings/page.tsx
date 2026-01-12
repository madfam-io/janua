'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@janua/ui'
import { Badge } from '@janua/ui'
import Link from 'next/link'
import {
  Settings,
  Shield,
  Users,
  Key,
  UserPlus,
  FileCheck,
  Lock,
  ChevronRight,
  ArrowLeft,
} from 'lucide-react'

interface SettingsSection {
  title: string
  description: string
  href: string
  icon: React.ReactNode
  badge?: string
  badgeVariant?: 'default' | 'secondary' | 'destructive' | 'outline'
}

const settingsSections: SettingsSection[] = [
  {
    title: 'Single Sign-On (SSO)',
    description: 'Configure SAML 2.0 or OIDC identity providers for your organization',
    href: '/settings/sso',
    icon: <Key className="h-5 w-5" />,
    badge: 'Enterprise',
    badgeVariant: 'secondary',
  },
  {
    title: 'SCIM Provisioning',
    description: 'Automate user provisioning from your identity provider',
    href: '/settings/scim',
    icon: <Users className="h-5 w-5" />,
    badge: 'Enterprise',
    badgeVariant: 'secondary',
  },
  {
    title: 'Team Invitations',
    description: 'Invite team members and manage pending invitations',
    href: '/settings/invitations',
    icon: <UserPlus className="h-5 w-5" />,
  },
  {
    title: 'Security Settings',
    description: 'Configure password policies, MFA requirements, and session settings',
    href: '/profile',
    icon: <Shield className="h-5 w-5" />,
  },
]

const complianceSections: SettingsSection[] = [
  {
    title: 'Privacy & Compliance',
    description: 'Manage data privacy settings, consent, and data subject requests',
    href: '/compliance',
    icon: <FileCheck className="h-5 w-5" />,
  },
  {
    title: 'Audit Logs',
    description: 'View security events and user activity logs',
    href: '/audit-logs',
    icon: <Lock className="h-5 w-5" />,
    badge: 'Admin',
    badgeVariant: 'outline',
  },
]

function SettingsCard({ section }: { section: SettingsSection }) {
  return (
    <Link href={section.href}>
      <Card className="hover:border-primary/50 hover:shadow-sm transition-all cursor-pointer">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-muted rounded-lg">{section.icon}</div>
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  {section.title}
                  {section.badge && (
                    <Badge variant={section.badgeVariant}>{section.badge}</Badge>
                  )}
                </CardTitle>
              </div>
            </div>
            <ChevronRight className="h-5 w-5 text-muted-foreground" />
          </div>
        </CardHeader>
        <CardContent>
          <CardDescription>{section.description}</CardDescription>
        </CardContent>
      </Card>
    </Link>
  )
}

export default function SettingsPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center space-x-4">
            <Link href="/" className="text-muted-foreground hover:text-foreground">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <Settings className="h-8 w-8 text-primary" />
            <div>
              <h1 className="text-2xl font-bold">Organization Settings</h1>
              <p className="text-sm text-muted-foreground">
                Configure authentication, security, and compliance settings
              </p>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8 space-y-8">
        {/* Authentication & Access */}
        <div>
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Shield className="h-5 w-5 text-muted-foreground" />
            Authentication & Access
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {settingsSections.map((section) => (
              <SettingsCard key={section.href} section={section} />
            ))}
          </div>
        </div>

        {/* Compliance & Audit */}
        <div>
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <FileCheck className="h-5 w-5 text-muted-foreground" />
            Compliance & Audit
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {complianceSections.map((section) => (
              <SettingsCard key={section.href} section={section} />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
