import Link from 'next/link'

export default function DocsLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const navigation = [
    {
      title: 'Getting Started',
      links: [
        { title: 'Introduction', href: '/docs' },
        { title: 'Quickstart', href: '/docs/quickstart' },
        { title: 'Installation', href: '/docs/installation' },
      ],
    },
    {
      title: 'Core Features',
      links: [
        { title: 'Authentication', href: '/docs/authentication' },
        { title: 'Multi-Factor Auth', href: '/docs/mfa' },
        { title: 'Passkeys', href: '/docs/passkeys' },
        { title: 'Session Management', href: '/docs/sessions' },
      ],
    },
    {
      title: 'Enterprise',
      links: [
        { title: 'SAML SSO', href: '/docs/saml' },
        { title: 'OIDC SSO', href: '/docs/oidc' },
        { title: 'SCIM Provisioning', href: '/docs/scim' },
        { title: 'RBAC', href: '/docs/rbac' },
      ],
    },
    {
      title: 'SDKs',
      links: [
        { title: 'TypeScript', href: '/docs/sdk/typescript' },
        { title: 'React', href: '/docs/sdk/react' },
        { title: 'Next.js', href: '/docs/sdk/nextjs' },
        { title: 'Vue', href: '/docs/sdk/vue' },
        { title: 'Python', href: '/docs/sdk/python' },
        { title: 'Go', href: '/docs/sdk/go' },
      ],
    },
    {
      title: 'API Reference',
      links: [
        { title: 'Authentication', href: '/docs/api/auth' },
        { title: 'Users', href: '/docs/api/users' },
        { title: 'SSO', href: '/docs/api/sso' },
        { title: 'RBAC', href: '/docs/api/rbac' },
      ],
    },
  ]

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-50 border-r border-gray-200 p-6 hidden lg:block">
        <nav className="space-y-8">
          {navigation.map((section) => (
            <div key={section.title}>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">
                {section.title}
              </h3>
              <ul className="space-y-2">
                {section.links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="block text-sm text-gray-600 hover:text-primary-600 transition-colors"
                    >
                      {link.title}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {children}
      </main>
    </div>
  )
}
