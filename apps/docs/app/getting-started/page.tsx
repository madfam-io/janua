import Link from 'next/link'
import { ArrowRight, Download, Zap, Shield, Code, Check } from 'lucide-react'
import { Button } from '@plinto/ui'

export default function GettingStartedPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 py-12">
      {/* Header */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-5xl">
          Getting Started with Plinto
        </h1>
        <p className="mt-6 text-xl leading-8 text-gray-600 dark:text-gray-400 max-w-3xl mx-auto">
          Integrate secure identity management into your application in under 5 minutes. 
          From installation to your first authenticated user.
        </p>
      </div>

      {/* Quick Path Options */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 mb-12">
        <QuickPathCard
          icon={<Zap className="h-8 w-8" />}
          title="Quick Start"
          description="Get up and running in 5 minutes"
          href="/getting-started/quick-start"
          time="5 min"
          primary
        />
        <QuickPathCard
          icon={<Download className="h-8 w-8" />}
          title="Installation"
          description="Detailed installation guide"
          href="/getting-started/installation"
          time="10 min"
        />
        <QuickPathCard
          icon={<Code className="h-8 w-8" />}
          title="First App"
          description="Build your first authenticated app"
          href="/getting-started/first-app"
          time="15 min"
        />
      </div>

      {/* What You'll Learn */}
      <div className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
          What You'll Learn
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <LearningOutcome
            icon={<Shield className="h-6 w-6" />}
            title="Authentication Setup"
            items={[
              "Configure Plinto in your project",
              "Set up environment variables",
              "Initialize the authentication system"
            ]}
          />
          <LearningOutcome
            icon={<Code className="h-6 w-6" />}
            title="Integration Patterns"
            items={[
              "Protect routes and API endpoints",
              "Handle user sessions",
              "Implement sign-in/sign-up flows"
            ]}
          />
        </div>
      </div>

      {/* Prerequisites */}
      <div className="mb-12 bg-blue-50 dark:bg-blue-950 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-4">
          Prerequisites
        </h3>
        <div className="space-y-2">
          <PrerequisiteItem text="Node.js 16.8 or later" />
          <PrerequisiteItem text="A JavaScript/TypeScript project (React, Next.js, Vue, etc.)" />
          <PrerequisiteItem text="Basic knowledge of your chosen framework" />
          <PrerequisiteItem text="A Plinto account (sign up at app.plinto.dev)" />
        </div>
      </div>

      {/* Framework Support */}
      <div className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
          Supported Frameworks
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <FrameworkCard name="Next.js" version="13+ App Router" supported />
          <FrameworkCard name="React" version="18+" supported />
          <FrameworkCard name="Vue" version="3+" supported />
          <FrameworkCard name="Nuxt" version="3+" supported />
          <FrameworkCard name="Express" version="4+" supported />
          <FrameworkCard name="FastAPI" version="0.68+" supported />
          <FrameworkCard name="Django" version="4+" supported />
          <FrameworkCard name="Go" version="1.19+" supported />
        </div>
      </div>

      {/* Next Steps */}
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
          Ready to Start?
        </h2>
        <div className="space-y-4 sm:space-y-0 sm:space-x-4 sm:flex sm:justify-center">
          <Link href="/getting-started/quick-start">
            <Button size="lg" className="gap-2">
              Start Quick Guide <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
          <Link href="/getting-started/installation">
            <Button variant="outline" size="lg">
              Read Installation Guide
            </Button>
          </Link>
        </div>
      </div>
    </div>
  )
}

function QuickPathCard({ icon, title, description, href, time, primary = false }: {
  icon: React.ReactNode
  title: string
  description: string
  href: string
  time: string
  primary?: boolean
}) {
  return (
    <Link
      href={href}
      className={`group relative rounded-lg border p-6 hover:border-blue-600 dark:hover:border-blue-400 transition-colors ${
        primary 
          ? 'border-blue-600 dark:border-blue-400 bg-blue-50 dark:bg-blue-950' 
          : 'border-gray-200 dark:border-gray-800'
      }`}
    >
      <div className="flex items-start gap-4">
        <div className={`flex h-12 w-12 items-center justify-center rounded-lg transition-colors ${
          primary
            ? 'bg-blue-600 text-white'
            : 'bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-400 group-hover:bg-blue-100 dark:group-hover:bg-blue-900'
        }`}>
          {icon}
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <h3 className={`font-semibold transition-colors ${
              primary 
                ? 'text-blue-900 dark:text-blue-100'
                : 'text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400'
            }`}>
              {title}
            </h3>
            <span className="text-sm text-gray-500 dark:text-gray-500">
              {time}
            </span>
          </div>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            {description}
          </p>
        </div>
      </div>
      <ArrowRight className="absolute top-6 right-6 h-4 w-4 text-gray-400 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors" />
    </Link>
  )
}

function LearningOutcome({ icon, title, items }: {
  icon: React.ReactNode
  title: string
  items: string[]
}) {
  return (
    <div className="border border-gray-200 dark:border-gray-800 rounded-lg p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-400">
          {icon}
        </div>
        <h3 className="font-semibold text-gray-900 dark:text-white">
          {title}
        </h3>
      </div>
      <ul className="space-y-2">
        {items.map((item, index) => (
          <li key={index} className="flex items-start gap-2">
            <Check className="h-4 w-4 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
            <span className="text-sm text-gray-600 dark:text-gray-400">{item}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function PrerequisiteItem({ text }: { text: string }) {
  return (
    <div className="flex items-center gap-2">
      <Check className="h-4 w-4 text-blue-600 dark:text-blue-400" />
      <span className="text-blue-800 dark:text-blue-200">{text}</span>
    </div>
  )
}

function FrameworkCard({ name, version, supported }: {
  name: string
  version: string
  supported: boolean
}) {
  return (
    <div className={`text-center p-4 rounded-lg border ${
      supported 
        ? 'border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950'
        : 'border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900'
    }`}>
      <div className={`text-sm font-medium ${
        supported 
          ? 'text-green-900 dark:text-green-100'
          : 'text-gray-500 dark:text-gray-500'
      }`}>
        {name}
      </div>
      <div className={`text-xs ${
        supported 
          ? 'text-green-600 dark:text-green-400'
          : 'text-gray-400 dark:text-gray-600'
      }`}>
        {version}
      </div>
    </div>
  )
}