export function FeaturesGrid() {
  const features = [
    {
      id: 'signup',
      title: 'User Signup & Login',
      description: 'Email/password authentication with secure password hashing, email verification, and session management.',
      icon: '👤',
      testId: 'feature-signup'
    },
    {
      id: 'login',
      title: 'Session Management',
      description: 'JWT-based sessions with refresh tokens, automatic token rotation, and secure cookie handling.',
      icon: '🔐',
      testId: 'feature-login'
    },
    {
      id: 'mfa',
      title: 'Multi-Factor Authentication',
      description: 'TOTP-based MFA with QR code generation, backup codes, and SMS verification support.',
      icon: '📱',
      testId: 'feature-mfa'
    },
    {
      id: 'passkey',
      title: 'Passkeys (WebAuthn)',
      description: 'Passwordless authentication with FIDO2/WebAuthn passkeys for enhanced security and UX.',
      icon: '🔑',
      testId: 'feature-passkey'
    },
    {
      id: 'profile',
      title: 'Profile Management',
      description: 'User profile updates, email changes, password resets, and account deletion capabilities.',
      icon: '⚙️',
      testId: 'feature-profile'
    },
    {
      id: 'security',
      title: 'Security Dashboard',
      description: 'Centralized security status, active sessions, login history, and security recommendations.',
      icon: '🛡️',
      testId: 'feature-security'
    },
    {
      id: 'sso',
      title: 'Enterprise SSO',
      description: 'SAML 2.0 and OIDC support for seamless integration with enterprise identity providers.',
      icon: '🏢',
      testId: 'feature-sso'
    },
    {
      id: 'rbac',
      title: 'Role-Based Access Control',
      description: 'Flexible RBAC with custom roles, permissions, and policy-based access control.',
      icon: '👥',
      testId: 'feature-rbac'
    },
    {
      id: 'audit',
      title: 'Audit Logging',
      description: 'Comprehensive audit trails for compliance with detailed event tracking and reporting.',
      icon: '📊',
      testId: 'feature-audit'
    },
    {
      id: 'api',
      title: 'RESTful API',
      description: 'Complete REST API with OpenAPI documentation, rate limiting, and versioning.',
      icon: '🔌',
      testId: 'feature-api'
    },
    {
      id: 'sdk',
      title: 'Multiple SDKs',
      description: 'Official SDKs for TypeScript, Python, Go, React, Next.js, and Vue with full type safety.',
      icon: '📦',
      testId: 'feature-sdk'
    },
    {
      id: 'self-hosted',
      title: 'Self-Hosted Ready',
      description: 'Deploy on your infrastructure with Docker, Kubernetes, or cloud platforms for full control.',
      icon: '🚀',
      testId: 'feature-self-hosted'
    }
  ]

  return (
    <section className="py-24 bg-white" data-testid="features-section">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-extrabold text-gray-900 sm:text-4xl">
            Everything You Need for Authentication
          </h2>
          <p className="mt-4 text-xl text-gray-600">
            Production-ready features validated by comprehensive journey tests
          </p>
        </div>

        <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((feature) => (
            <div
              key={feature.id}
              className="relative p-6 bg-white border border-gray-200 rounded-lg hover:shadow-lg transition-shadow feature-card"
              data-testid={feature.testId}
            >
              <div className="text-4xl mb-4">{feature.icon}</div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                {feature.title}
              </h3>
              <p className="text-gray-600">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
