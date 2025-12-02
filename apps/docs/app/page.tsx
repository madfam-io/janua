import Link from 'next/link'
import { ArrowRight, Book, Code2, Zap, Shield, Globe, Layers } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function DocsHomePage() {
  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      {/* Hero Section */}
      <div className="py-16 sm:py-24">
        <div className="text-center">
          <h1 className="text-4xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-6xl">
            Janua Documentation
          </h1>
          <p className="mt-6 text-lg leading-8 text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
            Everything you need to integrate secure identity management into your application.
            From quick starts to advanced configurations.
          </p>
          <div className="mt-10 flex items-center justify-center gap-x-6">
            <Link href="/getting-started/quick-start">
              <Button size="lg" className="gap-2">
                Get Started <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link href="/api/authentication">
              <Button variant="outline" size="lg">
                API Reference
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Quick Links Grid */}
      <div className="py-12 border-t border-gray-200 dark:border-gray-800">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-8">
          Quick Links
        </h2>
        <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
          <QuickLinkCard
            icon={<Zap className="h-6 w-6" />}
            title="Quick Start"
            description="Get up and running with Janua in under 5 minutes"
            href="/getting-started/quick-start"
          />
          <QuickLinkCard
            icon={<Shield className="h-6 w-6" />}
            title="Authentication"
            description="Implement secure authentication with passkeys and more"
            href="/guides/authentication"
          />
          <QuickLinkCard
            icon={<Code2 className="h-6 w-6" />}
            title="SDKs"
            description="Official SDKs for JavaScript, Python, Go, and more"
            href="/sdks"
          />
          <QuickLinkCard
            icon={<Layers className="h-6 w-6" />}
            title="Organizations"
            description="Multi-tenant architecture with RBAC"
            href="/guides/organizations"
          />
          <QuickLinkCard
            icon={<Globe className="h-6 w-6" />}
            title="API Reference"
            description="Complete API documentation with examples"
            href="/api"
          />
          <QuickLinkCard
            icon={<Book className="h-6 w-6" />}
            title="Examples"
            description="Sample applications and code snippets"
            href="/examples"
          />
        </div>
      </div>

      {/* Popular Guides */}
      <div className="py-12 border-t border-gray-200 dark:border-gray-800">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-8">
          Popular Guides
        </h2>
        <div className="space-y-4">
          <GuideLink
            title="Implementing Passkeys/WebAuthn"
            description="Learn how to add passwordless authentication with passkeys"
            href="/guides/authentication/passkeys"
          />
          <GuideLink
            title="Session Management"
            description="Handle user sessions, refresh tokens, and device management"
            href="/guides/sessions/management"
          />
          <GuideLink
            title="Next.js Integration"
            description="Step-by-step guide for Next.js App Router and Pages Router"
            href="/guides/frameworks/nextjs"
          />
          <GuideLink
            title="Rate Limiting & Security"
            description="Best practices for securing your application"
            href="/guides/security/best-practices"
          />
        </div>
      </div>

      {/* Code Example Teaser */}
      <div className="py-12 border-t border-gray-200 dark:border-gray-800">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-8">
          Quick Example
        </h2>
        <div className="bg-gray-900 rounded-lg p-6 overflow-x-auto">
          <pre className="text-sm text-gray-300">
            <code>{`import { Janua } from '@janua/nextjs'

// Initialize Janua
const janua = new Janua({
  issuer: process.env.JANUA_ISSUER,
  audience: process.env.JANUA_AUDIENCE,
})

// Protect a route
export async function GET(request: Request) {
  const session = await janua.getSession(request)
  
  if (!session) {
    return new Response('Unauthorized', { status: 401 })
  }
  
  return Response.json({ 
    user: session.user,
    org: session.organization 
  })
}`}</code>
          </pre>
        </div>
        <div className="mt-4 text-center">
          <Link href="/getting-started/installation" className="text-blue-600 dark:text-blue-400 hover:underline">
            View full installation guide →
          </Link>
        </div>
      </div>

      {/* Latest Updates */}
      <div className="py-12 border-t border-gray-200 dark:border-gray-800">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-8">
          Latest Updates
        </h2>
        <div className="space-y-4">
          <UpdateItem
            date="2024-01-15"
            version="v1.2.0"
            title="Enhanced Passkey Support"
            description="Added conditional UI and cross-platform sync"
          />
          <UpdateItem
            date="2024-01-10"
            version="v1.1.5"
            title="New Python SDK"
            description="Official Python SDK with async support"
          />
          <UpdateItem
            date="2024-01-05"
            version="v1.1.0"
            title="SCIM 2.0 Support"
            description="Enterprise user provisioning via SCIM"
          />
        </div>
        <div className="mt-6">
          <Link href="/changelog" className="text-blue-600 dark:text-blue-400 hover:underline">
            View full changelog →
          </Link>
        </div>
      </div>
    </div>
  )
}

function QuickLinkCard({ icon, title, description, href }: {
  icon: React.ReactNode
  title: string
  description: string
  href: string
}) {
  return (
    <Link
      href={href}
      className="group relative rounded-lg border border-gray-200 dark:border-gray-800 p-6 hover:border-blue-600 dark:hover:border-blue-400 transition-colors"
    >
      <div className="flex items-start gap-4">
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
      <ArrowRight className="absolute top-6 right-6 h-4 w-4 text-gray-400 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors" />
    </Link>
  )
}

function GuideLink({ title, description, href }: {
  title: string
  description: string
  href: string
}) {
  return (
    <Link
      href={href}
      className="block group rounded-lg border border-gray-200 dark:border-gray-800 p-4 hover:border-blue-600 dark:hover:border-blue-400 transition-colors"
    >
      <h3 className="font-semibold text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
        {title}
      </h3>
      <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
        {description}
      </p>
    </Link>
  )
}

function UpdateItem({ date, version, title, description }: {
  date: string
  version: string
  title: string
  description: string
}) {
  return (
    <div className="flex gap-4">
      <div className="flex-shrink-0">
        <span className="text-sm text-gray-500 dark:text-gray-500">
          {date}
        </span>
      </div>
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center rounded-md bg-blue-50 dark:bg-blue-950 px-2 py-1 text-xs font-medium text-blue-700 dark:text-blue-300">
            {version}
          </span>
          <h3 className="font-semibold text-gray-900 dark:text-white">
            {title}
          </h3>
        </div>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          {description}
        </p>
      </div>
    </div>
  )
}