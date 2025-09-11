import Link from 'next/link'
import { Shield, Key, Users, Lock, Zap, Settings, Globe, Database } from 'lucide-react'

export default function GuidesPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 py-12">
      {/* Header */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-5xl">
          Plinto Guides
        </h1>
        <p className="mt-6 text-xl leading-8 text-gray-600 dark:text-gray-400 max-w-3xl mx-auto">
          Comprehensive guides covering every aspect of Plinto identity management.
          From basic authentication to advanced enterprise features.
        </p>
      </div>

      {/* Core Concepts */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
          Core Concepts
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <GuideCard
            icon={<Shield className="h-6 w-6" />}
            title="Authentication"
            description="Learn about different authentication methods, from traditional email/password to modern passkeys and social login."
            href="/guides/authentication"
            topics={["Email/Password", "Passkeys", "Social Login", "Multi-factor Auth"]}
          />
          <GuideCard
            icon={<Key className="h-6 w-6" />}
            title="Session Management"
            description="Handle user sessions, refresh tokens, device management, and secure session storage."
            href="/guides/sessions"
            topics={["JWT Tokens", "Refresh Tokens", "Device Tracking", "Session Security"]}
          />
          <GuideCard
            icon={<Users className="h-6 w-6" />}
            title="User Management"
            description="Complete user lifecycle management from registration to account deletion."
            href="/guides/users"
            topics={["User Profiles", "Account Verification", "Password Reset", "User Metadata"]}
          />
          <GuideCard
            icon={<Lock className="h-6 w-6" />}
            title="Security"
            description="Best practices for securing your application and protecting user data."
            href="/guides/security"
            topics={["Rate Limiting", "CSRF Protection", "Content Security", "Audit Logging"]}
          />
        </div>
      </section>

      {/* Advanced Features */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
          Advanced Features
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <GuideCard
            icon={<Globe className="h-6 w-6" />}
            title="Organizations"
            description="Multi-tenant architecture with role-based access control and organization management."
            href="/guides/organizations"
            topics={["Multi-tenancy", "RBAC", "Team Management", "Organization Settings"]}
          />
          <GuideCard
            icon={<Database className="h-6 w-6" />}
            title="Data & Privacy"
            description="GDPR compliance, data export, user privacy controls, and data retention policies."
            href="/guides/privacy"
            topics={["GDPR Compliance", "Data Export", "Right to Deletion", "Privacy Controls"]}
          />
          <GuideCard
            icon={<Zap className="h-6 w-6" />}
            title="Performance"
            description="Optimize authentication performance, caching strategies, and scalability patterns."
            href="/guides/performance"
            topics={["Caching", "Load Balancing", "Database Optimization", "CDN Integration"]}
          />
          <GuideCard
            icon={<Settings className="h-6 w-6" />}
            title="Configuration"
            description="Environment setup, custom domains, webhooks, and advanced configuration options."
            href="/guides/configuration"
            topics={["Environment Variables", "Custom Domains", "Webhooks", "Feature Flags"]}
          />
        </div>
      </section>

      {/* Framework-Specific Guides */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
          Framework Integration
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <FrameworkGuide
            name="Next.js"
            description="App Router & Pages Router"
            href="/guides/frameworks/nextjs"
          />
          <FrameworkGuide
            name="React"
            description="SPA & Server Components"
            href="/guides/frameworks/react"
          />
          <FrameworkGuide
            name="Vue"
            description="Vue 3 & Nuxt 3"
            href="/guides/frameworks/vue"
          />
          <FrameworkGuide
            name="Express"
            description="Node.js Backend"
            href="/guides/frameworks/express"
          />
          <FrameworkGuide
            name="FastAPI"
            description="Python Backend"
            href="/guides/frameworks/fastapi"
          />
          <FrameworkGuide
            name="Django"
            description="Python Full-Stack"
            href="/guides/frameworks/django"
          />
          <FrameworkGuide
            name="Go"
            description="Gin & Standard Library"
            href="/guides/frameworks/go"
          />
          <FrameworkGuide
            name="Mobile"
            description="React Native & Flutter"
            href="/guides/frameworks/mobile"
          />
        </div>
      </section>

      {/* Popular Guides */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
          Popular Guides
        </h2>
        <div className="space-y-4">
          <PopularGuideLink
            title="Implementing Passkeys/WebAuthn"
            description="Step-by-step guide to passwordless authentication"
            href="/guides/authentication/passkeys"
            difficulty="Intermediate"
            time="30 min"
          />
          <PopularGuideLink
            title="Next.js App Router Integration"
            description="Complete integration with Next.js 13+ App Router"
            href="/guides/frameworks/nextjs"
            difficulty="Beginner"
            time="20 min"
          />
          <PopularGuideLink
            title="Multi-tenant Organization Setup"
            description="Build SaaS applications with organization support"
            href="/guides/organizations/multi-tenant"
            difficulty="Advanced"
            time="45 min"
          />
          <PopularGuideLink
            title="Rate Limiting & Security Hardening"
            description="Protect your application from attacks"
            href="/guides/security/rate-limiting"
            difficulty="Intermediate"
            time="25 min"
          />
        </div>
      </section>

      {/* Migration Guides */}
      <section>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
          Migration Guides
        </h2>
        <div className="bg-blue-50 dark:bg-blue-950 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-4">
            Migrating from Other Providers
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <MigrationLink
              from="Auth0"
              href="/guides/migration/auth0"
              description="Step-by-step migration from Auth0"
            />
            <MigrationLink
              from="Firebase Auth"
              href="/guides/migration/firebase"
              description="Migrate from Firebase Authentication"
            />
            <MigrationLink
              from="Clerk"
              href="/guides/migration/clerk"
              description="Switch from Clerk to Plinto"
            />
            <MigrationLink
              from="Supabase Auth"
              href="/guides/migration/supabase"
              description="Move from Supabase Authentication"
            />
          </div>
        </div>
      </section>
    </div>
  )
}

function GuideCard({ icon, title, description, href, topics }: {
  icon: React.ReactNode
  title: string
  description: string
  href: string
  topics: string[]
}) {
  return (
    <Link
      href={href}
      className="group block rounded-lg border border-gray-200 dark:border-gray-800 p-6 hover:border-blue-600 dark:hover:border-blue-400 transition-colors"
    >
      <div className="flex items-start gap-4 mb-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-400 group-hover:bg-blue-100 dark:group-hover:bg-blue-900 transition-colors">
          {icon}
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
            {title}
          </h3>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            {description}
          </p>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {topics.map((topic, index) => (
          <span
            key={index}
            className="inline-flex items-center rounded-md bg-gray-50 dark:bg-gray-900 px-2 py-1 text-xs font-medium text-gray-600 dark:text-gray-400"
          >
            {topic}
          </span>
        ))}
      </div>
    </Link>
  )
}

function FrameworkGuide({ name, description, href }: {
  name: string
  description: string
  href: string
}) {
  return (
    <Link
      href={href}
      className="group text-center p-4 rounded-lg border border-gray-200 dark:border-gray-800 hover:border-blue-600 dark:hover:border-blue-400 transition-colors"
    >
      <div className="font-medium text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
        {name}
      </div>
      <div className="text-xs text-gray-500 dark:text-gray-500">
        {description}
      </div>
    </Link>
  )
}

function PopularGuideLink({ title, description, href, difficulty, time }: {
  title: string
  description: string
  href: string
  difficulty: string
  time: string
}) {
  return (
    <Link
      href={href}
      className="group flex items-center justify-between p-4 rounded-lg border border-gray-200 dark:border-gray-800 hover:border-blue-600 dark:hover:border-blue-400 transition-colors"
    >
      <div className="flex-1">
        <h3 className="font-semibold text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
          {title}
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          {description}
        </p>
      </div>
      <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-500">
        <span className={`px-2 py-1 rounded-md text-xs font-medium ${
          difficulty === 'Beginner' ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300' :
          difficulty === 'Intermediate' ? 'bg-yellow-100 dark:bg-yellow-900 text-yellow-700 dark:text-yellow-300' :
          'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300'
        }`}>
          {difficulty}
        </span>
        <span>{time}</span>
      </div>
    </Link>
  )
}

function MigrationLink({ from, href, description }: {
  from: string
  href: string
  description: string
}) {
  return (
    <Link
      href={href}
      className="block p-3 rounded-md border border-blue-200 dark:border-blue-800 hover:bg-blue-100 dark:hover:bg-blue-900 transition-colors"
    >
      <div className="font-medium text-blue-900 dark:text-blue-100">
        From {from}
      </div>
      <div className="text-sm text-blue-700 dark:text-blue-300">
        {description}
      </div>
    </Link>
  )
}