import { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Documentation - Plinto',
  description: 'Complete documentation for integrating Plinto authentication into your application.',
}

export default function DocsPage() {
  return (
    <div className="prose prose-lg max-w-none">
      <h1>Documentation</h1>
      
      <p className="lead">
        Welcome to the Plinto documentation. Learn how to integrate enterprise-grade 
        authentication into your application in minutes.
      </p>

      <h2>What is Plinto?</h2>
      <p>
        Plinto is an open-source authentication and user management platform that provides:
      </p>
      <ul>
        <li>Email/password authentication with secure bcrypt hashing</li>
        <li>Multi-factor authentication (TOTP, SMS)</li>
        <li>Passwordless authentication with passkeys (WebAuthn/FIDO2)</li>
        <li>Enterprise SSO (SAML 2.0, OpenID Connect)</li>
        <li>Role-based access control (RBAC)</li>
        <li>Comprehensive audit logging for compliance</li>
        <li>Self-hosted or cloud-managed deployment</li>
      </ul>

      <h2>Quick Links</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 not-prose">
        <Link href="/docs/quickstart" className="block p-6 border border-gray-200 rounded-lg hover:border-primary-600 hover:shadow-md transition-all">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Quickstart Guide</h3>
          <p className="text-gray-600">Get up and running with Plinto in 5 minutes</p>
        </Link>
        
        <Link href="/docs/installation" className="block p-6 border border-gray-200 rounded-lg hover:border-primary-600 hover:shadow-md transition-all">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Installation</h3>
          <p className="text-gray-600">Install and configure Plinto for your environment</p>
        </Link>
        
        <Link href="/docs/sdk/typescript" className="block p-6 border border-gray-200 rounded-lg hover:border-primary-600 hover:shadow-md transition-all">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">TypeScript SDK</h3>
          <p className="text-gray-600">Integrate with Node.js and TypeScript applications</p>
        </Link>
        
        <Link href="/docs/sdk/react" className="block p-6 border border-gray-200 rounded-lg hover:border-primary-600 hover:shadow-md transition-all">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">React SDK</h3>
          <p className="text-gray-600">Add authentication to React applications</p>
        </Link>
      </div>

      <h2>Core Concepts</h2>
      
      <h3>Authentication Flow</h3>
      <p>
        Plinto uses JWT-based authentication with refresh token rotation for enhanced security. 
        The basic flow is:
      </p>
      <ol>
        <li>User signs up or logs in with credentials</li>
        <li>Server issues access token (short-lived) and refresh token (long-lived)</li>
        <li>Client includes access token in API requests</li>
        <li>When access token expires, use refresh token to get new tokens</li>
      </ol>

      <h3>Multi-Factor Authentication</h3>
      <p>
        MFA adds an extra layer of security by requiring users to provide a second factor 
        (TOTP code, SMS code) in addition to their password. Plinto supports:
      </p>
      <ul>
        <li>Time-based One-Time Passwords (TOTP) via authenticator apps</li>
        <li>SMS verification codes</li>
        <li>Backup codes for account recovery</li>
      </ul>

      <h3>Passkeys (WebAuthn)</h3>
      <p>
        Passkeys provide passwordless authentication using biometrics (Face ID, Touch ID) 
        or hardware security keys. Benefits include:
      </p>
      <ul>
        <li>Stronger security than passwords</li>
        <li>Better user experience (no passwords to remember)</li>
        <li>Phishing-resistant authentication</li>
      </ul>

      <h2>Architecture</h2>
      <p>
        Plinto is built with a modular architecture:
      </p>
      <ul>
        <li><strong>API Server</strong>: FastAPI backend with PostgreSQL</li>
        <li><strong>SDKs</strong>: Official client libraries for 6 languages/frameworks</li>
        <li><strong>Admin Dashboard</strong>: Next.js application for management</li>
        <li><strong>Database</strong>: PostgreSQL with row-level security</li>
        <li><strong>Cache</strong>: Redis for session storage and rate limiting</li>
      </ul>

      <h2>Next Steps</h2>
      <ul>
        <li>
          <Link href="/docs/quickstart">Follow the quickstart guide</Link> to build your first integration
        </li>
        <li>
          <Link href="/docs/authentication">Learn about authentication</Link> concepts and best practices
        </li>
        <li>
          <Link href="/docs/api/auth">Explore the API reference</Link> for detailed endpoint documentation
        </li>
      </ul>
    </div>
  )
}
